# Deployment Guide — Satellite Project Successor Tool

This document gives you the exact steps to run and deploy the app.

---

## 1) Local run

### Install dependencies
```bash
pip install -r requirements.txt
```

### Start the app
```bash
streamlit run app.py
```

### What opens
A local URL like:
- `http://localhost:8501`

---

## 2) Recommended project structure

```text
app.py
requirements.txt
README.md
DEPLOY_GUIDE.md
GOOGLE_SHEETS_SETUP.md
GITHUB_PUSH_STEPS.md
launch_vehicle_reference.csv
sample_satellite_input.csv
.streamlit/
  config.toml
  secrets.toml.example
satellite_app/
  __init__.py
  constants.py
  helpers.py
  sources.py
  scoring.py
  gsheets.py
  pipeline.py
```

---

## 3) Deploy to Streamlit Cloud

### Step 1: Push project to GitHub
Follow `GITHUB_PUSH_STEPS.md`

### Step 2: Go to Streamlit Cloud
- https://share.streamlit.io/
- Sign in with GitHub

### Step 3: Create app
- Click **New app**
- Select your repo
- Branch: `main`
- Main file path: `app.py`

### Step 4: Add secrets if needed
If you want Google Sheets read/write without uploading JSON every time:

App settings → Secrets

Paste:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = '''
{ ... full service account json ... }
'''
```

### Step 5: Deploy
Click **Deploy**

---

## 4) Streamlit Cloud troubleshooting

### If deploy fails on packages
Check `requirements.txt`

### If app loads but Google Sheets fails
Check:
- secret added correctly
- service account email shared with sheet
- Drive + Sheets APIs enabled

### If app works locally but not on cloud
Check:
- local hidden files not missing from repo
- correct main file path
- credentials not dependent on local path

---

## 5) How to use in production flow

### Option A — Local file workflow
1. Upload CSV/XLSX input
2. Upload UCS DB
3. Run processing
4. Review Data tab + GPT tab
5. Download workbook

### Option B — Google Sheet workflow
1. Upload or configure service-account JSON
2. Load input sheet URL + worksheet
3. Run processing
4. Review outputs
5. Push Data/GPT/Numeric/Evidence sheets back

---

## 6) Best practice for your internship

Use this workflow:

1. Keep the master Google Sheet clean
2. Run a smaller pilot batch first
3. Review low-confidence rows
4. Export reviewed outputs only
5. Then upload final reviewed tables to the team sheet

---

## 7) Suggested Streamlit Cloud settings

- Public app if team only needs access via link and data is non-sensitive
- Otherwise keep repo private and invite collaborators

---

## 8) Final caution
This app is a strong workflow tool, but still verify:
- cost fields
- frugal classifications
- missing purpose labels
- any row marked `Needs manual review`
