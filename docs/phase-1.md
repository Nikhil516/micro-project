# Phase 1 — completed

College mini-project. JavaScript frontend. Not production-grade.

## Decisions (defaults, no extra approval needed)

| Topic | Choice |
| --- | --- |
| UI language | JavaScript (no TypeScript) |
| State | Context API |
| Charts | Recharts |
| Auth | JWT + hashed passwords |
| DB driver | Motor (async) + indexes on startup |
| Images | Local uploads; Cloudinary optional |
| ML | Offline `ml/` pipeline; API loads joblib |
| Image CNN | TensorFlow/Keras ResNet-50 only (no PyTorch) |
| Split | Two phases: setup now, training + app behaviour next |

## Delivered in Phase 1

- Repository folders: `frontend/`, `backend/`, `ml/`, `docs/`, `tests/`
- `.gitignore` (no `.env`, no raw datasets)
- `.env.example` placeholders (you fill secrets)
- Architecture, MongoDB, and report outline docs
- Root `README.md`
- Vite + React in **JavaScript**
- FastAPI package layout and health route
- Planned MongoDB collections and indexes

## Explicitly not done in Phase 1

- Downloading datasets  
- Running ResNet-50 / XGBoost training  
- Publishing evaluation metrics  
- End-to-end demo of forecasts  

## Phase 2 (next, when you ask)

1. Dataset acquisition + preprocessing  
2. ResNet-50 embeddings  
3. XGBoost train/eval + save `ml/models/xgboost_weekly_demand.joblib`  
4. FastAPI prediction + CRUD wired to MongoDB  
5. React dashboards using APIs  
6. Tests and a short run-through  
