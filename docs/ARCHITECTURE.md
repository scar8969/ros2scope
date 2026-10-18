# Architecture -- ros2-dash

A ROS2 telemetry dashboard built on Flask. It subscribes to a rosbridge server,

This document explains how the service is put together, why the seams sit where
they do, and what breaks first under load.

---

## 1. Context

ros2scope is a single-process Flask service. It owns its own database (SQLite by
default, any SQLAlchemy-supported backend via `DATABASE_URL`) and is deployed
behind a reverse proxy or an orchestrator.

```mermaid
flowchart LR
    op["Operator / integrator"] --> svc["ros2-dash"]
    svc --> runtime["Python 3.11+ runtime"]
    svc --> state[("SQLite / DATA_DIR")]
    obs["Prometheus scraper"] --> svc
    svc --> log["stdout access + app log (JSON)"]
```

There is no message broker, no cache tier and no second service. Every scaling
decision below follows from that: the unit of scale is a process, and shared
state lives in the database.

---

## 2. Container view

```mermaid
flowchart TB
    subgraph proc["One OS process (gunicorn worker)"]
        wsgi["ros2_dashboard.wsgi:app"] --> appmod["app.create_app()"]
        appmod --> http["ros2_dashboard.http (ops blueprint, middleware)"]
        appmod --> errs["ros2_dashboard.errors (envelope handlers)"]
        appmod --> cfg["ros2_dashboard.config.Settings"]
        appmod --> pathm["ros2_dashboard.paths"]
        appmod --> logm["ros2_dashboard.observability"]
        appmod --> legacy["ros2_dashboard._app (domain routes)"]
        legacy --> core["ros2_dashboard.models / feature packages"]
    end
    cfg --> env["process environment"]
    pathm --> disk[("DATA_DIR")]
```

| Component                 | Responsibility                                                |
| ------------------------- | ------------------------------------------------------------- |
| `wsgi.py` / gunicorn      | Process entry point, worker lifecycle, healthcheck target     |
| `ros2_dashboard.app`             | App factory: config, directories, logging, middleware, ops endpoints |
| `ros2_dashboard.config`          | Environment parsing and validation; the only place the environment is read |
| `ros2_dashboard.paths`           | Filesystem layout; the only place runtime paths are decided   |
| `ros2_dashboard.observability`   | Structured logging, request-scoped correlation ids            |
| `ros2_dashboard.http`            | Middleware, error envelopes, hand-rolled Prometheus exposition |
| `ros2_dashboard.errors`          | Typed exception hierarchy that maps to HTTP status codes      |
| `ros2_dashboard.<feature>`       | The service's own domain modules (see below)                  |

---

## 3. Domain modules

| Module | Kind |
| --- | --- |
| `bridge/__init__.py` | module |
| `bridge/api.py` | module |
| `bridge/record.py` | module |
| `bridge/ros_bridge.py` | module |
| `bridge/topics.py` | module |
| `cli.py` | module |
| `models.py` | module |
| `static/app.js` | asset |
| `templates/base.html` | asset |
| `templates/index.html` | asset |
| `templates/map.html` | asset |
| `tests/test_ros2scope.py` | module |
| `_app.py` | asset |
| `ws.py` | module |

---

## 4. Request lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant W as gunicorn worker
    participant R as app.create_app()
    participant H as http module
    participant D as domain blueprint
    C->>W: GET /some/route
    W->>R: before_request
    R->>H: assign / echo ros2-dash
    H->>D: dispatch
    D-->>H: response
    H-->>C: response + security headers + ros2-dash
```

Step by step:

1. gunicorn accepts the connection and hands it to a worker process.
2. Flask builds the request. The `before_request` hook reads `X-Request-ID`
   or generates one, stores it in a `ContextVar`, and starts a monotonic timer.
3. The matching view runs. Domain code may raise an `AppError` subclass; a
   registered error handler renders it to the standard JSON envelope.
4. The `after_request` hook stamps security headers, echoes the request id,
   and increments RED counters (rate, errors, duration) per route and status class.
5. An access record is emitted as one JSON line. `/metrics`, `/healthz`,
   `/livez` and `/readyz` are excluded so probes do not drown the log.

Because the request id lives in a `ContextVar` rather than a thread local, it
propagates correctly through gunicorn's threaded workers, and it stays correct if
the worker model later becomes async.

---

## 5. Configuration and startup

Configuration is parsed once, when the factory imports, into a frozen dataclass.
`Settings.validate()` runs inside `from_env()`, so an invalid manifest
fails at boot instead of at the first request. Startup order is deliberate:

1. Parse and validate the environment.
2. `ensure_runtime_dirs()` creates `var/`, `var/instance`, `var/log`.
3. `configure_logging()`, before any other code can log.
4. Import the project's Flask app and apply the platform configuration.
5. Re-point `instance_path` at `var/instance` so a relative SQLite URI
   resolves under the writable data directory rather than inside the source tree.
6. Install middleware, error handlers and the ops blueprint.

Step 5 is what makes the image work with a read-only root filesystem: nothing
writable lives under `/app`.

---

## 6. Data

| Table | Owner |
| --- | --- |
| `topics` | owned by `ros2scope` |
| `recordings` | owned by `ros2scope` |

Tables are created by the application's own bootstrap on first use. No migration
tool is wired in; the schema is additive, and the service tolerates a missing or
empty database by creating what it needs.

---

## 7. Failure modes

| Failure                         | Behaviour                                                   |
| ------------------------------- | ----------------------------------------------------------- |
| Database unreachable            | Requests needing it return `503`; `/readyz` reports the failure |
| Database empty or never migrated | The schema is created on demand; no manual step required   |
| Downstream service unreachable  | Route-specific behaviour, documented in the route table     |
| Oversized request body          | `413` with the standard envelope (`MAX_CONTENT_LENGTH`)      |
| Unhandled exception             | `500` with the envelope; the traceback goes to the log, never the body |
| Worker OOM-killed               | The orchestrator restarts it on the failed `/healthz` probe   |

Failures are collected through `errors.AppError`. Anything raised that is not
an `AppError` is treated as a bug: it is logged with a full traceback and
reported to the client as a bare `500`.

---

## 8. Scaling

The service is stateless apart from the database, so the scale-out story is "add
workers, add replicas":

- **Vertically:** raise `--workers`. A reasonable starting point is
  `2 * CPU + 1` for request-bound work; measure before trusting that rule.
- **Horizontally:** run N replicas behind a load balancer. Nothing is sticky.
- **SQLite is the ceiling.** Its single-writer lock makes multi-replica writes
  unsafe on a shared filesystem. Move `DATABASE_URL` to Postgres before
  scaling past one writer, and use `/readyz` as the traffic gate.
- **Metrics** are per-process and in memory. Aggregating across replicas is the
  scrape layer's job, which is why every counter is labelled with the route
  template rather than the raw path.

---

## 9. Security posture

- Secrets come from the environment only. `Settings.as_dict()` redacts them
  and `/version` therefore cannot leak one.
- Security headers are applied centrally, so a new route cannot forget them.
- The container drops all Linux capabilities, runs as an unprivileged uid, and
  mounts a read-only root filesystem.
- The threat model -- what is defended and what is explicitly not -- is in
  [SECURITY.md](../SECURITY.md). It states plainly that this service has no
  authentication layer unless the route table says otherwise.

---

## 10. Decisions

Architecture decisions are recorded as ADRs in [docs/adr/](adr/). The first one
explains why the source layout is `src/` and why runtime state lives under
`var/`.
