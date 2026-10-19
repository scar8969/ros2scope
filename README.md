<p align="center">
  <img src="docs/assets/screens/root.png" alt="ros2scope running" width="900">
</p>

<h1 align="center">ros2scope</h1>

<p align="center"><b>ROS 2 telemetry in a browser, with recording and replay.</b></p>

<p align="center">
  <a href="https://github.com/scar8969/ros2scope/actions/workflows/ci.yml"><img src="https://github.com/scar8969/ros2scope/actions/workflows/ci.yml/badge.svg" alt="ci"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/tests-23%20passed-2ea44f" alt="tests: 23 passed"></a> <a href="#quality-gates"><img src="https://img.shields.io/badge/coverage-58.2%-yellow" alt="coverage: 58.2%"></a> <a href="#api"><img src="https://img.shields.io/badge/routes-13%20live-0969da" alt="routes: 13 live"></a> <a href="#requirements"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="python: 3.11+"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2ea44f" alt="license: MIT"></a>
</p>

ros2scope subscribes to a rosbridge server, shows topic rates and message counts, records selected topics to disk and replays them without a robot attached.

---

**Contents** &nbsp;·&nbsp; [Why](#why-this-exists) &nbsp;·&nbsp; [What it does](#what-it-does) &nbsp;·&nbsp; [Quickstart](#quickstart) &nbsp;·&nbsp; [Screenshots](#screenshots) &nbsp;·&nbsp; [API](#api) &nbsp;·&nbsp; [CLI](#cli) &nbsp;·&nbsp; [Configuration](#configuration) &nbsp;·&nbsp; [Measured](#measured-not-estimated) &nbsp;·&nbsp; [How a request flows](#how-a-request-flows) &nbsp;·&nbsp; [Architecture](#architecture) &nbsp;·&nbsp; [Quality gates](#quality-gates) &nbsp;·&nbsp; [Development](#development) &nbsp;·&nbsp; [Deploy](#deploy) &nbsp;·&nbsp; [Limits](#limits-stated-rather-than-hidden)

## Why this exists

Reading ROS 2 topics usually means a terminal per topic. A small dashboard that speaks rosbridge over WebSocket gives the same numbers to anyone on the network — and recording makes a field session reproducible on a desk.

## What it does

| Capability | How it works |
| --- | --- |
| **rosbridge subscription** | A WebSocket client subscribes by topic name and tracks message rates. |
| **Recording** | Selected topics are appended to a JSONL file; stop and start are explicit. |
| **Replay** | A recorded file can be fed back through the same pipeline. |
| **WebSocket endpoint** | The dashboard's own /ws route serves the live handshake. |
| **CLI** | topics, record, replay and serve. |

## Quickstart

```sh
git clone https://github.com/scar8969/ros2scope.git
cd ros2scope
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python wsgi.py                                 # http://127.0.0.1:8000
```

It is up when this answers:

```sh
curl -s http://127.0.0.1:8000/api/topics
```

## Screenshots

Captured from the running service with headless Chromium at 1440×900, one image per page, committed under [`docs/assets/screens/`](docs/assets/screens/).

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/map.png" alt="/map" width="100%"><br><sub><code>/map</code> &middot; 29.0 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/healthz.png" alt="/healthz" width="100%"><br><sub><code>/healthz</code> &middot; 8.3 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/livez.png" alt="/livez" width="100%"><br><sub><code>/livez</code> &middot; 7.3 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/metrics.png" alt="/metrics" width="100%"><br><sub><code>/metrics</code> &middot; 16.2 KB</sub></td>
</tr>
</table>

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/readyz.png" alt="/readyz" width="100%"><br><sub><code>/readyz</code> &middot; 7.7 KB</sub></td>
<td width="50%"><img src="docs/assets/screens/version.png" alt="/version" width="100%"><br><sub><code>/version</code> &middot; 27.6 KB</sub></td>
</tr>
</table>

## API

Every route below is declared in [`openapi/ros2scope.yaml`](openapi/ros2scope.yaml) and exercised by the live probe recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/api/topics` | topics |
| `POST` | `/api/record` | start record |
| `POST` | `/api/recordings/<id>/stop` | stop |
| `GET` | `/api/recordings` | list |
| `GET` | `/ws` | rosbridge relay handshake; the socket itself runs as python -m web.ws |

## CLI

The same operations without an HTTP client. Installed as `ros2scope`, and runnable from a checkout with no install:

```sh
python -m ros2_dashboard.cli --help
```

```text
usage: ros2-dash [-h] [--version] {topics,record,replay,serve} ...

ROS2 telemetry dashboard: topics, recordings, replay.

positional arguments:
  {topics,record,replay,serve}
    topics              list the topics the dashboard subscribes to
    record              record topic messages to a JSONL bag
    replay              print the messages stored in a JSONL bag
    serve               run the Flask telemetry dashboard

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

## Configuration

Environment only — there is no config file. Copy `.env.example` to `.env` and edit; `APP_ENV=production` refuses to start without `SECRET_KEY`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_ENV` | `development` | development \| staging \| production; production enforces the secret. |
| `SECRET_KEY` | `change-me-in-production` | Session/CSRF signing key. Required when APP_ENV=production. |
| `HOST` | `0.0.0.0` | Interface the dev server binds. |
| `PORT` | `8000` | Port the dev server and the container listen on. |
| `DEBUG` | `false` | Flask debug mode. Never true in production. |
| `MAX_CONTENT_LENGTH` | `8388608` | Largest accepted request body, in bytes. |
| `DATA_DIR` | `(empty)` | Where uploaded and generated files live. |
| `INSTANCE_DIR` | `(empty)` | Where the SQLite file and instance state live. |
| `LOG_DIR` | `(empty)` | Where rotated log files are written, if file logging is on. |
| `LOG_LEVEL` | `INFO` | DEBUG \| INFO \| WARNING \| ERROR. |
| `LOG_JSON` | `true` | true emits one JSON object per line; false is human-readable. |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header echoed on every response and stamped on every log line. |
| `ROSBRIDGE_URL` | `ws://127.0.0.1:9090` | rosbridge WebSocket the dashboard subscribes to. |
| `ROSBRIDGE_RELAY_LISTEN` | `127.0.0.1:9091` | Address the dashboard's own /ws relay binds. |
| `ROSBRIDGE_ID` | `ros2scope` | Client id sent to rosbridge. |
| `ROS2DASH_OUTPUT_DIR` | `(empty)` | Where recorded topic files are written; defaults under the data dir. |
| `ROS2DASH_SECRET` | `(empty)` | Flask session key. |

## Measured, not estimated

Produced on this checkout by `pytest --cov` and by booting `wsgi.py` and issuing one real GET per documented path. The commands are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

| Signal | Value |
| --- | --- |
| Tests | **23 / 23 passed** (2.0 s, exit 0) |
| Line coverage | **58.2%** — 459 of 748 statements |
| Source | 16 files / 1,664 lines |
| Test code | 4 files / 233 lines |
| Documented paths | 5 in the spec, 3 GET |
| Live probe | 13 GET requests to the booted app, **13 answered 200** |
| Median latency | **9.7 ms** (single uncached request, dev server) |
| Slowest / fastest | 117.1 ms `/` / 5.0 ms `/ws` |
| Bytes served | 15.8 KB across 13 responses |
| Screenshots | 7 captured |

## How a request flows

```text
client
  │  HTTP
  ▼
wsgi.py ──▶ ros2_dashboard/app.py:get_app()
                │  reads config once (ros2_dashboard/config.py)
                │  registers the `bridge` blueprint
                ▼
           route handler
             ├──▶ ros2_dashboard/models.py        tables, via Flask-SQLAlchemy
             ├──▶ ros2_dashboard/errors.py        raises typed errors → one JSON envelope
             └──▶ ros2_dashboard/observability.py JSON log line + X-Request-ID
```

Every response carries `X-Request-ID`, and the matching log line is written once at the end of the request with the status and duration, so a report of "it failed" is one `grep` away from the traceback.

## Architecture

```
ros2scope/
├── src/ros2_dashboard/
│   ├── http.py                         379  HTTP plumbing for ros2_dashboard: correlation ids, a
│   ├── _app.py                         183  
│   ├── config.py                       175  Environment-driven configuration for ros2_dashboard
│   ├── cli.py                          170  ros2-dash CLI - topic inspection, rosbridge recordin
│   ├── observability.py                169  Structured logging and request correlation for ros2_
│   ├── app.py                          119  Application factory for ros2_dashboard
│   ├── errors.py                       108  Typed application errors and their HTTP mapping for 
│   ├── ws.py                           106  rosbridge relay: the socket half of the /ws endpoint
│   ├── bridge/api.py                    75  
│   ├── paths.py                         52  Filesystem layout for ros2_dashboard
│   ├── bridge/ros_bridge.py             46  
│   ├── bridge/record.py                 32  
├── openapi/ros2scope.yaml                 the contract of record
├── schema/ros2scope.sql                   the DDL
├── tests/                       the suite that has to stay green
├── docs/EVIDENCE.md             the recorded live route walk
├── Dockerfile                   multi-stage build
└── wsgi.py                      entry point
```

The package keeps one shape across the service: `config.py` reads the environment once, `observability.py` emits structured JSON logs carrying a request id, `errors.py` turns exceptions into a single JSON envelope, `models.py` holds the tables, and the `bridge/` package holds the routes.

## Quality gates

| Gate | Command | Threshold |
| --- | --- | --- |
| Suite | `pytest -q` | all green |
| Coverage | `pytest --cov` | floor in `pyproject.toml`, set below the measured value |
| Lint | `ruff check src tests` | zero findings |
| Format | `ruff format --check src tests` | zero reformats |
| Types | `mypy src` | zero errors |
| Security | `bandit -c pyproject.toml -r src` | reviewed skip list, no unreviewed finding |
| Live routes | boot `wsgi.py`, one GET per documented path | no 5xx, no undocumented guard |

CI runs the first six on Python 3.11, 3.12 and 3.13 on every push to `main`, plus a container build — [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Development

```sh
pip install -e ".[dev]"
python -m pytest -q                      # the suite
python -m pytest --cov                   # with the coverage floor
python -m ruff check src tests           # lint
python -m ruff format --check src tests  # formatting
python -m mypy src                       # types
python -m bandit -c pyproject.toml -r src  # security
pre-commit install                       # the same checks on commit
```

Dependabot opens grouped PRs for the dev tooling weekly and for actions and the base image monthly.

## Deploy

```sh
docker build -t ros2scope .
docker run --rm -p 8000:8000 --env-file .env.example ros2scope
```

A `docker-compose.yml` is included for a local run with a volume for the SQLite file. The image runs as a non-root user and serves through gunicorn.

## Limits, stated rather than hidden

- Requires a rosbridge server; without one the dashboard reports zero topics rather than inventing data.
- Message decoding is generic JSON, not typed by .msg definitions.

## License

MIT — see [LICENSE](LICENSE).
