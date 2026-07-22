# Google Sheets Setup Guide

This app can read input from Google Sheets and write outputs back to Google Sheets.

---

## Method A — easiest in the app
Upload a **service-account JSON** file in the app UI.

---

## Method B — Streamlit Cloud secret
Add the full JSON inside Streamlit Cloud secrets as:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = '''
{ ... full service account JSON ... }
'''
```

---

## Full setup steps

### 1) Open Google Cloud Console
- Go to: https://console.cloud.google.com/
- Create a new project, or use an existing one.

### 2) Enable APIs
Enable these APIs:
- Google Sheets API
- Google Drive API

### 3) Create service account
- IAM & Admin → Service Accounts
- Create service account
- Give any name, for example:
  - `satellite-sheet-bot`

### 4) Create key
- Open the service account
- Keys → Add Key → Create new key → JSON
- Download the JSON file

### 5) Share your Google Sheet with the service account email
Very important.

Example service account email looks like:

- `satellite-sheet-bot@your-project-id.iam.gserviceaccount.com`

Open your Google Sheet → Share → paste this email → give **Editor** access.

Without this step, reading/writing will fail.

---

## Common errors

### Error: Spreadsheet not found
Possible reasons:
- wrong Google Sheet URL
- sheet not shared with service account email
- wrong worksheet name

### Error: Permission denied
Possible reasons:
- Drive API not enabled
- Sheet not shared with service account
- invalid JSON credentials

### Error: Could not fetch worksheets
Possible reasons:
- bad URL
- missing credentials
- sheet is private and not shared

---

## Security note
Never commit your real service-account JSON file to GitHub.
Use:
- Streamlit secrets
- or upload JSON directly in app at runtime
