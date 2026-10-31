# API plan (implemented in Phase 2)

Base URL: `http://localhost:8000`

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | no | Process + model load status |
| POST | `/auth/register` | no | Create user |
| POST | `/auth/login` | no | JWT |
| POST | `/auth/logout` | yes | Blocklist token |
| GET | `/auth/me` | yes | Current user |
| CRUD | `/products` | yes | Catalog + image upload |
| CRUD | `/sales` | yes | History + CSV + weekly agg |
| POST | `/forecasts` | yes | Weekly demand (single/batch) |
| GET | `/forecasts` | yes | History |
| GET | `/analytics/*` | yes | Trends, category, inventory flags |
| GET | `/model` | yes | Version, date, **real** metrics |
| GET | `/reports/*` | yes | CSV / PDF |

All JSON bodies validated with Pydantic. Errors return `{ "detail": "..." }`.
