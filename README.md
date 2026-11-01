# Multi-Modal Fashion Demand Forecasting

College mini-project: predict **next week’s units sold** for fashion products using historical sales, product attributes, calendar/season signals, optional weather, and **ResNet-50 image embeddings**, with **XGBoost** as the forecaster.

This is **not** a production SaaS. Scope is a working demo: React dashboard, FastAPI APIs, MongoDB, and an offline ML pipeline.

---

## Implementation status

| Phase | Status | What it covers |
| --- | --- | --- |
| **Phase 1** | Complete | Architecture, folders, env templates, docs, JavaScript frontend stack |
| **Phase 2** | Complete | Dataset acquisition, preprocessing, ResNet-50 embeddings, XGBoost training, FastAPI integration, dashboards, and tests |

Do not treat later folders as “already trained / already deployed.” Phase 2 trains the model and wires live predictions.

---

## Problem

Retail demand is usually forecast from sales history only. Fashion demand also depends on **how a product looks**, **season and festivals**, and **external interest** (weather, search trends when available). This project fuses those signals for a weekly unit forecast.

## Objectives (mini-project)

1. Store products, sales, users, and forecast history in MongoDB.
2. Extract image features with pretrained ResNet-50 (TensorFlow/Keras, no PyTorch).
3. Train XGBoost offline; the API only **loads** saved artifacts.
4. Show forecasts, simple analytics, and actual evaluation metrics (never invented).
5. Support a **cold-start** fallback when a product has little or no sales history.

---

## Architecture (Phase 1)

```
Browser (React + Vite, JavaScript)
        |  JWT + REST (Axios)
        v
FastAPI (Python)
        |-- MongoDB (Atlas or local)
        |-- Optional Cloudinary (else local /uploads)
        +-- joblib model files under ml/models/   (created in Phase 2)
```

Training lives in `ml/` and is **offline**. The server does not retrain on each request.

**Frontend language:** JavaScript only (no TypeScript).

**State:** React Context for auth and toasts (no Redux).

**Charts:** Recharts.

---

## Repository layout

```
fashion-demand-forecasting/
  frontend/          React + Vite + Tailwind (JavaScript)
  backend/           FastAPI app
  ml/                Offline pipeline (data, ResNet, XGBoost)
  docs/              Architecture and college report outline
  tests/             Pytest (Phase 2)
  README.md
  .env.example
```

---

## Technology stack

| Layer | Choice |
| --- | --- |
| UI | React, Vite, JavaScript, Tailwind CSS, Recharts, Axios, React Router, Context API |
| API | FastAPI, Pydantic, JWT |
| DB | MongoDB (`DATABASE_NAME=fashion_forecasting`) |
| ML | NumPy, Pandas, scikit-learn, TensorFlow/Keras (ResNet-50), XGBoost, Joblib |

---

## Environment variables

Copy `.env.example` to `.env` at the repo root (and optionally `backend/.env`, `frontend/.env`). **Never commit real secrets.**

You will fill in:

- `MONGODB_URI` — Atlas or `mongodb://localhost:27017`
- `DATABASE_NAME=fashion_forecasting`
- `JWT_SECRET`
- Cloudinary keys (optional)
- `WEATHER_API_KEY` (optional; Open-Meteo needs none)
- `FRONTEND_URL`

See [docs/mongodb.md](docs/mongodb.md).

---

## Local run (after Phase 2 wiring)

These commands are the intended workflow. Phase 1 only establishes folders and config.

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # then edit MONGODB_URI
uvicorn app.main:app --reload --app-dir .
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

API docs (when the server is up): `http://localhost:8000/docs`

---

## Model training

The checked-in artifacts were generated from the public datasets described in [ml/datasets/README.md](ml/datasets/README.md). To retrain from scratch:

```bash
SSL_CERT_FILE=.venv/lib/python3.10/site-packages/certifi/cacert.pem \
DYLD_LIBRARY_PATH=/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/sklearn/.dylibs \
./.venv/bin/python -m ml.training.pipeline --image-limit 60
```

On macOS, install an OpenMP runtime such as `libomp` for XGBoost. The Colab notebook under `ml/notebooks/` provides a GPU-compatible alternative.

The verified chronological hold-out results for the current artifact are:

| Model | MAE | RMSE | WAPE |
| --- | ---: | ---: | ---: |
| XGBoost | 44.17 | 85.62 | 0.6407 |
| Lag-1 baseline | 44.47 | 86.04 | 0.6451 |

Artifacts are stored under `ml/models/`, including `xgboost_weekly_demand.joblib`, preprocessing objects, ResNet-50 metadata/embeddings, and evaluation reports. The API loads these files; it does not retrain during requests.

---

## Documentation

- [Architecture](docs/architecture.md)
- [MongoDB setup](docs/mongodb.md)
- [Academic report outline](docs/academic-report.md)
- [Phase 1 checklist](docs/phase-1.md)

---

## Limitations (honest)

- Public fashion **photos** and public **sales** rarely share the same SKU; alignment is by category, documented in `ml/datasets/README.md`.
- Google Trends may be unavailable without a working unofficial client.
- Cold-start forecasts are weaker than history-based forecasts.
- Feature importance is not causation.
- College demo: no production hardening, no claim of inventory “guarantees.”
