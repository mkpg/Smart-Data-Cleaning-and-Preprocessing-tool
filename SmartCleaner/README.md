# Medicl — Smart Healthcare Data Cleaner

> An intelligent, HIPAA-aware data preprocessing platform for clinical datasets.  
> Upload CSV, Excel, JSON, or XML patient records and clean them in one click — entirely locally, zero cloud upload.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🏥 **Medical-aware cleaning** | ICD-10 mapping, medical abbreviation expansion, clinical spell correction |
| 🔒 **PHI Redaction** | Names, emails, phone numbers, IDs — HIPAA/GDPR compliant |
| 📊 **Quality Scoring** | 5-dimension report: completeness, consistency, validity, uniqueness, accuracy |
| 🧠 **ML Imputation** | Random Forest missing-value imputation (requires scikit-learn) |
| 📁 **Multi-format** | CSV, Excel (.xlsx/.xls), JSON, XML, TXT, PDF, LOG |
| 💻 **100% Local** | No cloud upload — data never leaves your machine |
| 🌙 **Dark UI** | Premium glassmorphic interface |

---

## 🚀 Quick Start (Local Python)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# 2. Create a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
cd SmartCleaner/web
python server.py

# 5. Open in browser
# → http://localhost:5000
```

> **Windows users:** Double-click `RUN_APP.bat` to start the app instantly.

---

## 🐳 Quick Start (Docker)

```bash
docker-compose up -d
# Open http://localhost:5000
```

---

## 📁 Project Structure

```
.
├── SmartCleaner/
│   ├── web/
│   │   ├── server.py                  ← Flask backend (all API routes)
│   │   ├── unstructured_processor.py  ← PDF / TXT clinical note parser
│   │   ├── review_workflow.py         ← Human-in-the-loop review module
│   │   ├── static/
│   │   │   ├── app.js                 ← Frontend logic
│   │   │   └── styles.css             ← Dark theme UI
│   │   ├── templates/
│   │   │   ├── landing.html           ← Landing / home page
│   │   │   ├── index.html             ← Main cleaning app
│   │   │   └── docs.html              ← API documentation
│   │   └── uploads/                   ← Runtime upload dir (gitignored)
│   └── inputs/                        ← Sample demo datasets
├── requirements.txt                   ← Python dependencies
├── Dockerfile
├── docker-compose.yml
├── RUN_APP.bat                        ← One-click Windows launcher
└── .env.example                       ← Environment variable template
```

---

## 🧹 Cleaning Operations

The `/api/execute` endpoint supports **13 operations**:

| Key | What it does |
|-----|-------------|
| `smart_type_conversion` | Auto-fixes type mismatches |
| `handle_missing` | Fill or drop missing values |
| `remove_duplicates` | Remove duplicate rows |
| `handle_outliers` | Cap or remove statistical outliers |
| `redact_phi` | HIPAA-compliant name/ID/email redaction |
| `standardize_codes` | Map diagnoses → ICD-10, validate LOINC |
| `validate_clinical` | Check values against medical ranges |
| `validate_ranges` | Check numeric columns |
| `normalize_clinical_text` | Expand abbrevs, fix medical misspellings |
| `clean_text` | Strip special chars, normalize whitespace |
| `remove_high_missing` | Drop columns above missing threshold |
| `feature_engineering` | Derive new features automatically |
| `ml_impute_missing` | Random Forest imputation |

---

## 🔌 API Reference

### Upload a file
```
POST /api/upload
Content-Type: multipart/form-data
Field: file (CSV, XLSX, JSON, XML, TXT, PDF — max 50 MB)
```

### Run cleaning
```
POST /api/execute
Content-Type: application/json

{
  "session_id": "uuid-from-upload",
  "operations": {
    "redact_phi":        { "checked": true },
    "remove_duplicates": { "checked": true },
    "handle_missing":    { "checked": true, "method": "auto" }
  }
}
```

### Export cleaned data
```
GET /api/export/{session_id}
→ Returns cleaned_data.csv
```

See [docs.html](SmartCleaner/web/templates/docs.html) or visit `/docs` in the running app for the full API reference.

---

## ⚙️ System Requirements

- **Python** 3.10 or higher
- **RAM** 2 GB minimum (4 GB recommended for large files)
- Any modern browser (Chrome, Firefox, Edge, Safari)

---

## 🔒 Privacy

All data is processed **100% in-memory, on your machine**. No data is uploaded to any server. Sessions are cleared when you close the browser or restart the app.

---

## 📋 License

MIT License — feel free to use, modify, and distribute.
