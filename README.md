# PricePulse

Cloud-based e-commerce price monitoring SaaS.

Users submit product URLs, the platform periodically scrapes prices, persists the full
price history, and triggers in-app alerts when user-defined rules fire (target price,
percentage drop). Built around a modular monolith plus an ARQ worker, with a stealth
scraping engine that handles JavaScript-rendered, Cloudflare-protected pages.


## Submission

| | |
|---|---|
| **Student** | Sarper Avcı |
| **Student No.** | 22050111044 |
| **Course** | Cloud Computing — Final Project |
| **Demo video** | https://youtu.be/en66dJYaiNM |
| **Live system** | https://pricepulse.hackmap.win |
| **Project report** | [`docs/PROJECT_REPORT.pdf`](docs/PROJECT_REPORT.pdf) |


## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (async) · Python 3.12 |
| ORM / Migrations | SQLAlchemy 2.0 + asyncpg · Alembic |
| Worker / Queue | ARQ (Redis) |
| Scraping | Patchright (stealth Playwright) + BrowserForge · BeautifulSoup4 + httpx |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Frontend | React 19 + Vite + TypeScript · Tailwind v4 · Recharts |
| Containerization | Docker + docker-compose |
| CI/CD | GitHub Actions → GHCR (`api`, `frontend` images) |
| Auth | JWT (access + refresh) · API keys |


## Run locally

```bash
docker compose up -d
docker compose exec api alembic -c backend/alembic.ini upgrade head
```

- Frontend → http://localhost:5173
- API → http://localhost:8000

Seed an admin user, then add any product URL from the dashboard. The scheduler picks
it up within a minute and runs the first scrape.


## CI

Every push to `main` runs four jobs:

1. **lint** — ruff
2. **test-backend** — pytest, against real Postgres + Redis service containers
3. **test-frontend** — `tsc` + `vite build`
4. **docker-build** — pushes `api` and `frontend` images to GHCR (only on `main`)
