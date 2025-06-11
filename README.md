# 📦 trading-36 — Production Branch

This branch contains **production-ready code** and **final published outputs** for the LeanTech trading pipeline. It is managed directly by automation scripts running on the `vm01-prod` EC2 instance.

---

## ✅ Purpose

- Centralize HTML and CSV reports generated daily
- Track only stable modules, final strategies, and configurations
- Avoid including experimental notebooks, raw datasets, or logs

---

## 📁 Contents

| Directory | Purpose |
|----------|---------|
| `scripts/` | Core production scripts (e.g., `pub_1.py`, ingestion tools) |
| `my_modules/` | Strategy modules, email integration, and helpers |
| `web/templates/` | HTML templates for S3 publishing |
| `reports/senales_heuristicas/diarias/` | Final heuristic signals |
| `config/` | Symbol groups and system status configs |

---

## 🔄 Maintained By

This branch is updated by the production instance only:

```bash
vm01-prod → git add + commit + push to production
```

You should **not develop or test directly** in this branch.

---

## 🚫 Not Included

The following are excluded via `.gitignore`:

- `data/`, `logs/`, `.env`, `.keys.sh`
- Raw CSV, Parquet or HTML exports already published to S3
- Notebooks or dev/test config files
- Debug logs or temporary files

---

## ✅ Branch Model

- `production` → live output pushed from `vm01-prod`
- `staging` → reviewed updates promoted by the maintainer
- `exploration` → R&D, notebook-based experimentation

---

## 📬 Reports and Alerts

Final signals and daily reports are generated using:

- `pub_1.py` → formats Top 50 heuristic signals into HTML, sends email and uploads to S3
- `alc_v1.py` → aggregates buy/sell strategy signals, sends daily alerts
- `shu_dia.py` → generates daily heuristic signals from recent market data
- `recuperar_historico.py` → fetches missing historical data via Twelve Data
- `ingest_TwelveData.py` → AWS Lambda for rotating symbol ingestion into S3

---

🛠 Maintainer: [@apariciodevcom](https://github.com/apariciodevcom)
