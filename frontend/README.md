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
npm run e2e:app:local
npm run e2e:map:local
```
