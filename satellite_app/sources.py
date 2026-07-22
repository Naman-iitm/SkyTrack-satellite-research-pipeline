import io
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import pandas as pd
import requests
import urllib3
from rapidfuzz import fuzz, process

from .constants import CELESTRAK_SATCAT_CSV, UCS_DB_LINK, WIKI_SEARCH_URL, WIKI_SUMMARY_URL
from .helpers import get_col, normalize_name, safe_str, to_int_str


def read_table_from_upload(uploaded_file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()
    bio = io.BytesIO(file_bytes)
    if file_name.endswith(".csv"):
        return pd.read_csv(bio)
    if file_name.endswith(".xlsx"):
        return pd.read_excel(bio, sheet_name=sheet_name or 0)
    if file_name.endswith(".xls"):
        return pd.read_excel(bio, sheet_name=sheet_name or 0, engine="xlrd")
    raise ValueError("Unsupported file format.")


def get_sheet_names(uploaded_file) -> List[str]:
    file_name = uploaded_file.name.lower()
    if file_name.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(io.BytesIO(uploaded_file.getvalue()))
        return xls.sheet_names
    return ["CSV"]


def prepare_ucs_dataframe_from_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    bio = io.BytesIO(file_bytes)
    if file_name.endswith(".csv"):
        df = pd.read_csv(bio)
    elif file_name.endswith(".xlsx"):
        df = pd.read_excel(bio)
    elif file_name.endswith(".xls"):
        df = pd.read_excel(bio, engine="xlrd")
    else:
        raise ValueError("Unsupported UCS DB format.")

    sat_col = get_col(df, "SATNAME") or df.columns[0]
    norad_col = get_col(df, "NORAD_ CAT_ID")
    intldes_col = get_col(df, "INTLDES")
    df = df.copy()
    df["__norm_satname__"] = df[sat_col].apply(normalize_name)
    df["__norm_norad__"] = df[norad_col].apply(to_int_str) if norad_col else ""
    df["__norm_intldes__"] = df[intldes_col].astype(str).str.upper().str.strip() if intldes_col else ""
    return df


def find_ucs_match(
    satellite_name: str,
    norad: str,
    intldes: str,
    ucs_df: Optional[pd.DataFrame],
) -> Tuple[Optional[pd.Series], str, float, str]:
    if ucs_df is None or ucs_df.empty:
        return None, "No UCS DB", 0.0, UCS_DB_LINK

    norm_name = normalize_name(satellite_name)
    norm_norad = to_int_str(norad)
    norm_intldes = safe_str(intldes).upper().strip()

    if norm_norad:
        exact_norad = ucs_df[ucs_df["__norm_norad__"] == norm_norad]
        if not exact_norad.empty:
            return exact_norad.iloc[0], "Exact NORAD", 1.0, UCS_DB_LINK

    if norm_intldes:
        exact_id = ucs_df[ucs_df["__norm_intldes__"] == norm_intldes]
        if not exact_id.empty:
            return exact_id.iloc[0], "Exact INTLDES", 0.99, UCS_DB_LINK

    if norm_name:
        exact_name = ucs_df[ucs_df["__norm_satname__"] == norm_name]
        if not exact_name.empty:
            return exact_name.iloc[0], "Exact Name", 0.98, UCS_DB_LINK

        choices = ucs_df["__norm_satname__"].dropna().tolist()
        if choices:
            best = process.extractOne(norm_name, choices, scorer=fuzz.token_set_ratio)
            if best:
                _, score, idx = best
                if score >= 75:
                    return ucs_df.iloc[idx], "Fuzzy Name", round(score / 100.0, 2), UCS_DB_LINK

    return None, "No Match", 0.0, UCS_DB_LINK


def load_celestrak_satcat() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0 (Satellite-Project-Successor-Tool)"}

    try:
        response = requests.get(CELESTRAK_SATCAT_CSV, timeout=60, headers=headers)
        response.raise_for_status()
        csv_text = response.text
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(CELESTRAK_SATCAT_CSV, timeout=60, headers=headers, verify=False)
        response.raise_for_status()
        csv_text = response.text

    df = pd.read_csv(io.StringIO(csv_text))
    df = df.copy()
    df["__norm_satname__"] = df["OBJECT_NAME"].apply(normalize_name)
    df["__norm_norad__"] = df["NORAD_CAT_ID"].apply(to_int_str)
    df["__norm_intldes__"] = df["OBJECT_ID"].astype(str).str.upper().str.strip()
    return df


def find_celestrak_match(
    satellite_name: str,
    norad: str,
    intldes: str,
    satcat_df: Optional[pd.DataFrame],
) -> Tuple[Optional[pd.Series], str, float, str]:
    url = CELESTRAK_SATCAT_CSV
    if satcat_df is None or satcat_df.empty:
        return None, "No CelesTrak DB", 0.0, url

    norm_name = normalize_name(satellite_name)
    norm_norad = to_int_str(norad)
    norm_intldes = safe_str(intldes).upper().strip()

    if norm_norad:
        exact_norad = satcat_df[satcat_df["__norm_norad__"] == norm_norad]
        if not exact_norad.empty:
            row = exact_norad.iloc[0]
            return row, "Exact NORAD", 1.0, f"https://celestrak.org/satcat/search.php?CATNR={norm_norad}"

    if norm_intldes:
        exact_id = satcat_df[satcat_df["__norm_intldes__"] == norm_intldes]
        if not exact_id.empty:
            return exact_id.iloc[0], "Exact INTLDES", 0.99, f"https://celestrak.org/satcat/search.php?INTDES={quote(norm_intldes)}"

    if norm_name:
        exact_name = satcat_df[satcat_df["__norm_satname__"] == norm_name]
        if not exact_name.empty:
            return exact_name.iloc[0], "Exact Name", 0.98, f"https://celestrak.org/satcat/search.php?NAME={quote(satellite_name)}"

        choices = satcat_df["__norm_satname__"].dropna().tolist()
        if choices:
            best = process.extractOne(norm_name, choices, scorer=fuzz.token_set_ratio)
            if best:
                _, score, idx = best
                if score >= 75:
                    return satcat_df.iloc[idx], "Fuzzy Name", round(score / 100.0, 2), f"https://celestrak.org/satcat/search.php?NAME={quote(satellite_name)}"

    return None, "No Match", 0.0, url


def wikipedia_lookup(query: str) -> Dict[str, str]:
    query = safe_str(query)
    if not query:
        return {}
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 1,
        }
        r = requests.get(WIKI_SEARCH_URL, params=params, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
        if not hits:
            return {}
        title = hits[0]["title"]
        page_url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

        sr = requests.get(WIKI_SUMMARY_URL.format(quote(title.replace(' ', '_'))), timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        summary = ""
        if sr.ok:
            payload = sr.json()
            summary = payload.get("extract", "")
        return {"title": title, "url": page_url, "summary": summary}
    except Exception:
        return {}
