# Backend API

FastAPI runtime API for accessibility and path queries using precomputed offline artifacts.

## Requirements
- Python 3.13+

## Endpoints
- `GET /health`
- `GET /metadata`
- `POST /multi_isochrones` (requires `city` in JSON body)
- `POST /multi_path` (requires `city` in JSON body)
- `GET /geocode` (requires `city` query param)
- `GET /reverse_geocode` (requires `city` query param)

Removed endpoints:
- `POST /heatmap`
- `POST /isochrones`
- `POST /path`

## Commands
```bash
make setup
make lint
make test
BASELINE_CITY=paris make baseline
make run
```

`make run` starts `uvicorn` with hot reload on `127.0.0.1:8000` by default.
By default it also allows frontend dev origins on `http://localhost:3xxx` and `http://127.0.0.1:3xxx`.
Override host/port with `HOST` and `PORT`, or set `CORS_ALLOW_ORIGIN` / `CORS_ALLOW_ORIGIN_REGEX` explicitly.

For local browser checks against the frontend running on `http://127.0.0.1:3010`, use:

```bash
make run-browser-check
```

That starts the backend on `http://127.0.0.1:8001` with `CORS_ALLOW_ORIGIN=http://127.0.0.1:3010`.
