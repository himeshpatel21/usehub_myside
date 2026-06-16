# Install script — full autostart

## Goal

`install.sh` should perform the full local dev setup end-to-end: build Docker images, start infrastructure and app servers, and open the browser — no manual terminal steps.

## Approach

- **Docker:** `docker compose build` for `backend` and `frontend` images; `up` for `db`, `redis`, `minio`, plus `minio-init` one-shot.
- **App servers:** Native `uvicorn` and `npm run dev` (matches README and `backend/.env` localhost URLs), run in background with PIDs/logs under `.dev/`.
- **Browser:** `wslview` / `xdg-open` / `open` / `cmd.exe` for WSL/Linux/macOS.

## Steps

- [x] `install.sh` — build, migrate, seed, start servers, health wait, open browser
- [ ] Optional: `scripts/stop-dev.sh` if users want a dedicated stop command

## Decisions

- Keep native dev servers rather than `docker compose up backend frontend` — compose frontend image is production-oriented; native dev has hot reload aligned with README.
- Re-run stops prior PIDs from `.dev/` before starting new processes.
