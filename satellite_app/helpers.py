import io
import math
import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .constants import COUNTRY_OWNER_MAP, COUNTRY_REGION_MAP, KNOWN_COL_ALIASES


def safe_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def is_blank(value) -> bool:
    s = safe_str(value).strip().lower()
    return s in {"", "na", "n/a", "none", "nan", "null", "not available", "unknown"}


def normalize_name(value: str) -> str:
    value = safe_str(value).upper()
    value = re.sub(r"\(.*?\)", " ", value)
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def to_float(value) -> Optional[float]:
    if is_blank(value):
        return None
    s = safe_str(value).replace(",", "")
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if not nums:
        return None
    try:
        return float(nums[0])
    except Exception:
        return None


def to_int_str(value) -> str:
    number = to_float(value)
    if number is None:
        return ""
    return str(int(number)) if float(number).is_integer() else str(number)


def multi_join(parts: Iterable[str], sep: str = " | ") -> str:
    cleaned = [safe_str(p) for p in parts if not is_blank(p)]
    return sep.join(cleaned)


def first_existing_col(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    lower_map = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias.strip().lower() in lower_map:
            return lower_map[alias.strip().lower()]
    return None


def get_col(df: pd.DataFrame, canonical: str) -> Optional[str]:
    return first_existing_col(df, KNOWN_COL_ALIASES.get(canonical, [canonical]))


def pick_first_from_row(row: pd.Series, canonical: str, default: str = "") -> str:
    for key in KNOWN_COL_ALIASES.get(canonical, [canonical]):
        if key in row and not is_blank(row[key]):
            return safe_str(row[key])
    return default


def pick_first_value(*values: str, default: str = "") -> str:
    for value in values:
        if not is_blank(value):
            return safe_str(value)
    return default


def excel_export_available() -> bool:
    try:
        import openpyxl  # noqa: F401
        return True
    except Exception:
        return False


def dataframe_to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    if not excel_export_available():
        raise ModuleNotFoundError(
            "openpyxl is not installed. Install it with: pip install openpyxl or pip install -r requirements.txt"
        )

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output.getvalue()


def parse_intldes_parts(intldes: str) -> Tuple[str, str, str]:
    intldes = safe_str(intldes).upper().replace(" ", "")
    match = re.match(r"^(\d{4})-(\d{3})([A-Z0-9]+)$", intldes)
    if not match:
        return "", "", ""
    return match.group(1), match.group(2), match.group(3)


def parse_date(value: str):
    s = safe_str(value)
    if not s:
        return None
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(s[:10], fmt)
        except Exception:
            pass
    try:
        return pd.to_datetime(s, errors="coerce")
    except Exception:
        return None


def year_from_date(value: str) -> str:
    dt = parse_date(value)
    if dt is None or pd.isna(dt):
        return ""
    return str(int(dt.year))


def years_between(start_date: str, end_date: str) -> str:
    s = parse_date(start_date)
    e = parse_date(end_date)
    if s is None or e is None or pd.isna(s) or pd.isna(e):
        return ""
    years = round((e - s).days / 365.25, 2)
    return str(years) if years >= 0 else ""


def average_altitude(apogee, perigee) -> str:
    a = to_float(apogee)
    p = to_float(perigee)
    if a is None and p is None:
        return ""
    if a is None:
        return str(p)
    if p is None:
        return str(a)
    return str(round((a + p) / 2, 2))


def classify_isro_orbit(class_of_orbit: str, type_of_orbit: str, apogee, perigee, inclination) -> str:
    blob = multi_join([class_of_orbit, type_of_orbit]).lower()
    apo = to_float(apogee)
    per = to_float(perigee)
    inc = to_float(inclination)

    if "geo" in blob or "gto" in blob:
        return "GTO"
    avg_alt = None if apo is None and per is None else ((apo or 0) + (per or 0)) / (2 if apo is not None and per is not None else 1)
    if avg_alt is not None:
        if 300 <= avg_alt <= 1200 and inc is not None and 96 <= inc <= 99.5:
            return "SSO"
        if avg_alt <= 2000:
            return "LEO"
        if apo is not None and apo > 30000 and per is not None and per < 5000:
            return "GTO"
    return ""


def standardize_country(value: str) -> str:
    value = safe_str(value)
    if not value:
        return ""
    return COUNTRY_OWNER_MAP.get(value.upper(), value)


def infer_region_from_country(country: str) -> str:
    country = safe_str(country)
    if not country:
        return ""
    return COUNTRY_REGION_MAP.get(country, "")


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    out = df.copy()
    for c in columns:
        if c not in out.columns:
            out[c] = ""
    return out[columns]


def best_text_snippet(text: str, max_len: int = 260) -> str:
    s = safe_str(text)
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."
