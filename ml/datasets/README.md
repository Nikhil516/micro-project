# Datasets

This project aligns **three public sources** rather than inventing SKU-level fashion POS data (which is rarely published with matching product photos).

## 1. Product images and categories

**Source:** [clothing-dataset-small](https://github.com/alexeygrigorev/clothing-dataset-small)  
**License:** MIT  
**What we use:** JPEG product photos grouped into categories (`dress`, `hat`, `longsleeve`, `outwear`, `pants`, `shirt`, `shoes`, `shorts`, `skirt`, `t-shirt`).

Each image becomes one catalog SKU. Colour / pattern / sleeve are derived from filename heuristics plus category defaults and are stored as **catalog attributes**, not as ground-truth manufacturer labels.

## 2. Historical weekly sales

**Source:** [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) (Chen, Saniie, 2015)  
**License:** CC BY 4.0  
**What we use:** Invoice line items (`StockCode`, `Description`, `Quantity`, `InvoiceDate`) from a UK retailer.

Clothing-related stock codes are kept when the description matches fashion keywords. Weekly net quantity is aggregated. Those **real weekly series** are then joined onto catalog SKUs **by category keyword**, not by claiming that a GitHub photo is the same physical SKU as a UCI stock code.

If a category has more images than UCI series, leftover products are treated as **cold-start** items (no history). If UCI has more series than images, unused series are dropped.

## 3. External covariates

| Signal | Source | Auth |
| --- | --- | --- |
| Weather (temp, precipitation, humidity) | [Open-Meteo Historical API](https://open-meteo.com/) for London (UCI market) | None |
| Festivals / holidays | Python `holidays` (United Kingdom) | None |
| Search interest | Optional `pytrends` pull for category keywords; cached CSV | Unofficial; may fail |

Weather and holidays are **real**. Google Trends is used only when the pull succeeds; otherwise the model trains **without** trend features and the app labels that channel as unavailable.

## Alignment key

`product_id` (catalog) ↔ `stock_code` (UCI) ↔ `iso_week` (Monday week start).

No future week’s sales enter feature columns. Calendar features for the *target* week are allowed (they are known ahead of time). Weather and trends are lagged by one week.

## Local cache

Downloads land in `ml/datasets/raw/` (gitignored). Processed tables land in `ml/datasets/processed/`.
