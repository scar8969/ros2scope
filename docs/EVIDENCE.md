# Evidence

Every line below was produced by a command run against this exact checkout, on this machine, at the time recorded. Nothing here is copied from the README.

| | |
| --- | --- |
| Generated | 2026-10-19 02:26 |
| Python | 3.14.7 |
| Platform | Windows 11 |

## Test suite

```sh
python -m pytest -q
```

- exit code **0**
- 23 passed in 1.41s

## Static gates

| Gate | Exit | Last line |
| --- | --- | --- |
| `ruff check` | 0 | All checks passed! |
| `ruff format --check` | 0 | 20 files already formatted |
| `mypy src` | 0 | Success: no issues found in 16 source files |
| `bandit -c pyproject.toml -r src` | 0 | — |

## Live route walk

The application was imported through `wsgi.py` and each GET path declared in `openapi/` was requested once through the Werkzeug test client.

| Status | Path | Bytes | Content-Type |
| --- | --- | --- | --- |
| 200 | `/api/topics` | 280 | application/json |
| 200 | `/api/recordings` | 18 | application/json |
| 200 | `/ws` | 189 | application/json |

3 paths walked, 0 of them raised or answered 5xx.

## Screenshots

Captured from the running service with headless Chromium at 1440x900 and committed with the repository:

| File | Bytes |
| --- | --- |
| `docs/assets/screens/healthz.png` | 8,532 |
| `docs/assets/screens/livez.png` | 7,468 |
| `docs/assets/screens/map.png` | 29,684 |
| `docs/assets/screens/metrics.png` | 16,548 |
| `docs/assets/screens/readyz.png` | 7,880 |
| `docs/assets/screens/root.png` | 43,335 |
| `docs/assets/screens/version.png` | 28,296 |

## What this file does not prove

- It is not a load test: every request is a single uncached call from one process.
- A green suite is not a coverage claim; `pytest --cov` reports the number the README quotes.
- The route walk exercises GET paths only; mutating routes are covered by the suite.
