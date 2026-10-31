# Architecture — college mini-project

## Why this design

The assignment needs **multimodal ML** plus a **demo app**. For a college project we keep one FastAPI process, one MongoDB database, and a JavaScript Vite app. We do **not** add microservices, Redis, Kubernetes, or TypeScript.

## High-level flow

```
React (Vite, JavaScript)
   REST + JWT
FastAPI
   ├── Motor → MongoDB (users, products, sales, forecasts, …)
   ├── Static /uploads or Cloudinary URLs
   └── Load ml/models/*.joblib  (trained offline)
```

```
ml/preprocessing  →  ResNet-50 embeddings  →  feature fusion  →  XGBoost
                                                              →  metrics JSON
```

## Frontend (JavaScript)

| Item | Decision |
| --- | --- |
| Language | JavaScript only (`.jsx` / `.js`) |
| Routing | React Router |
| Auth session | Context API + `localStorage` token |
| HTTP | Axios instance in `frontend/src/api/client.js` |
| Charts | Recharts |
| Styling | Tailwind CSS, light theme |

Planned pages: Login, Register, Dashboard, Products, Forecasting, Analytics, Sales, Model performance, Reports.

## Backend

Modular FastAPI under `backend/app/`:

- `config.py` — env via pydantic-settings
- `database.py` — Motor client + indexes
- `routes/` — auth, products, sales, forecasts, analytics, model, reports
- `ml/predictor.py` — load artifacts, predict (no training on request)
- `middleware/auth.py` — JWT

Health check: `GET /health`.

## MongoDB collections

| Collection | Role |
| --- | --- |
| `users` | Register/login (hashed password) |
| `products` | Catalog + attributes + image URL |
| `sales` | Daily or invoice-level lines |
| `forecasts` | Saved weekly predictions |
| `inventory` | Simple on-hand qty for risk flags |
| `model_metrics` | MAE / RMSE / WAPE from **actual** training |
| `trends_data` | Cached search interest if available |
| `weather_data` | Cached weekly weather |
| `festivals` | Holiday calendar rows |
| `token_blocklist` | Logout / invalid JWTs |

Indexes are created on connect (`email` unique, `product_id` unique, sales `(product_id, date)`).

## ML (offline)

1. **Images** — pretrained ResNet-50 (ImageNet), no classification head, GAP embeddings, saved to disk.
2. **Tabular** — lags, rolling means, category/colour/pattern/sleeve, week/month/season, festival proximity, lagged weather/trends.
3. **Model** — XGBoost, chronological split, baseline (e.g. last-week / seasonal naive).
4. **Target** — units in the **next** week.
5. **Cold start** — similar products by category + image embedding distance; UI must label these as lower confidence.

No future sales in features. Calendar of the target week is allowed (known in advance). Weather/trends lagged one week.

## Deployment (optional for viva)

- Frontend: Vercel  
- Backend: Render  
- DB: MongoDB Atlas  
- Large artifacts: Git LFS or Render disk — **do not** assume a huge file fits in Git.

College demo can stay fully local.

## What Phase 1 does **not** include

- Dataset download and training runs  
- Claiming MAE/RMSE/WAPE  
- Live forecast accuracy  
- Production security review  

Those belong to **Phase 2**.
