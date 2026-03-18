# Frontend (Next.js)

Interactive map client for travel-time heatmaps.

## Commands

```bash
make setup
make dev
make test
make e2e
npm run e2e:local
```

For this machine, the most reliable end-to-end launcher is the local helper script. It starts the backend on `127.0.0.1:8000`, the frontend on `127.0.0.1:3002`, waits for both to be ready, runs Playwright with `PW_SKIP_WEBSERVER=1`, then shuts both servers down.

Useful variants:

```bash
npm run e2e:local
npm run e2e:headed:local
npm run e2e:app:local
npm run e2e:map:local
```

Use Node 24 for frontend and Playwright commands in this repo (`nvm use 24` if needed). If the local helper reports that `127.0.0.1:8000` or `127.0.0.1:3002` is already in use, stop the competing process first or override `E2E_BACKEND_PORT` / `E2E_FRONTEND_PORT`.

If your environment blocks the helper from opening local ports itself, run the stack separately and point Playwright at it:

```bash
cd backend
CORS_ALLOW_ORIGIN_REGEX='^http://127\.0\.0\.1:3002$' PYTHONPATH=src:shared/src UV_CACHE_DIR=.uv-cache uv run uvicorn transit_backend.api.server:app --host 127.0.0.1 --port 8012
```

```bash
cd frontend
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8012 npm run dev -- --hostname 127.0.0.1 --port 3002
```

```bash
cd frontend
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3002 npm run e2e:headed:existing
```

That full headed workflow was verified locally with `27` Playwright tests passing against the live backend on `127.0.0.1:8012` and frontend on `127.0.0.1:3002`.
