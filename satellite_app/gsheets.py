import json
import os
from io import StringIO
from typing import List, Optional

import pandas as pd

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


def _get_creds_info(service_account_json_text: Optional[str] = None):
    if service_account_json_text:
        return json.loads(service_account_json_text)
    env_value = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if env_value:
        return json.loads(env_value)
    return None


def get_gspread_client(service_account_json_text: Optional[str] = None):
    if gspread is None or Credentials is None:
        raise RuntimeError("gspread/google-auth not installed.")
    info = _get_creds_info(service_account_json_text)
    if not info:
        raise RuntimeError("Google credentials not provided. Upload service-account JSON or set GOOGLE_SERVICE_ACCOUNT_JSON.")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)


def list_worksheets(sheet_url: str, service_account_json_text: Optional[str] = None) -> List[str]:
    client = get_gspread_client(service_account_json_text)
    sh = client.open_by_url(sheet_url)
    return [ws.title for ws in sh.worksheets()]


def read_worksheet_as_df(sheet_url: str, worksheet_name: str, service_account_json_text: Optional[str] = None) -> pd.DataFrame:
    client = get_gspread_client(service_account_json_text)
    sh = client.open_by_url(sheet_url)
    ws = sh.worksheet(worksheet_name)
    rows = ws.get_all_values()
    if not rows:
        return pd.DataFrame()
    header, data = rows[0], rows[1:]
    return pd.DataFrame(data, columns=header)


def write_df_to_worksheet(
    sheet_url: str,
    worksheet_name: str,
    df: pd.DataFrame,
    mode: str = "overwrite",
    service_account_json_text: Optional[str] = None,
):
    client = get_gspread_client(service_account_json_text)
    sh = client.open_by_url(sheet_url)
    try:
        ws = sh.worksheet(worksheet_name)
    except Exception:
        ws = sh.add_worksheet(title=worksheet_name, rows=max(1000, len(df) + 50), cols=max(30, len(df.columns) + 5))

    values = [df.columns.astype(str).tolist()] + df.fillna("").astype(str).values.tolist()
    if mode == "overwrite":
        ws.clear()
        ws.update(values)
    elif mode == "append":
        existing = ws.get_all_values()
        if not existing:
            ws.update(values)
        else:
            ws.append_rows(values[1:])
    else:
        raise ValueError("mode must be overwrite or append")


def credentials_json_text_from_upload(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue().decode("utf-8")
    json.loads(raw)
    return raw
