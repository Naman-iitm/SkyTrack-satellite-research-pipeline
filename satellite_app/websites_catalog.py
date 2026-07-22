from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

from .helpers import safe_str


def _extract_urls(values) -> List[str]:
    urls = []
    for value in values:
        s = safe_str(value)
        if s.startswith("http") or s.startswith("www.") or "https://" in s or "http://" in s:
            parts = [p.strip() for p in s.replace("\n", ",").split(",")]
            for p in parts:
                if p.startswith("http") or p.startswith("www."):
                    urls.append(p)
    deduped = []
    for u in urls:
        if u and u not in deduped:
            deduped.append(u)
    return deduped


def parse_websites_catalog(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=["RA NAME", "URLS"]), pd.DataFrame(columns=["Acronym", "Country/Organization", "RA NAME", "URLS"])

    df = raw_df.fillna("").copy()
    first_col = df.columns[0]

    generic_rows = []
    country_rows = []
    mode = None
    for _, row in df.iterrows():
        head = safe_str(row[first_col])
        if head == "RA NAME":
            mode = "generic"
            continue
        if head == "COUNTRY":
            mode = "country-header"
            continue
        if head == "Acronym":
            mode = "country"
            continue
        if not head:
            continue

        if mode == "generic":
            ra_name = head
            urls = _extract_urls(row.values[1:])
            if ra_name and urls:
                generic_rows.append({"RA NAME": ra_name, "URLS": urls})
        elif mode == "country":
            acronym = head
            country = safe_str(row.values[1]) if len(row.values) > 1 else ""
            ra_name = safe_str(row.values[2]) if len(row.values) > 2 else ""
            urls = _extract_urls(row.values[3:])
            if acronym or country:
                country_rows.append(
                    {
                        "Acronym": acronym,
                        "Country/Organization": country,
                        "RA NAME": ra_name,
                        "URLS": urls,
                    }
                )

    return pd.DataFrame(generic_rows), pd.DataFrame(country_rows)


def websites_for_country(country_df: pd.DataFrame, acronym: str) -> List[str]:
    if country_df is None or country_df.empty:
        return []
    row = country_df[country_df["Acronym"] == acronym]
    if row.empty:
        return []
    urls = row.iloc[0]["URLS"]
    return urls if isinstance(urls, list) else []
