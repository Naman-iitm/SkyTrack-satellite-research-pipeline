from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .constants import DATA_COLUMNS, GPT_COLUMNS
from .helpers import ensure_columns, is_blank, normalize_name, safe_str


RAW_DATA_TO_CANONICAL = {
    "RA NAME": "RA NAME",
    "INTLDES": "INTLDES",
    "SATELLITE CODE": "SATELLITE CODE",
    "OBJECT_ TYPE": "OBJECT_ TYPE",
    "SATNAME": "SATNAME",
    "MISSION NAME": "MISSION NAME",
    "VEHICLE TYPE NAME": "VEHICLE TYPE NAME",
    "REGION": "REGION",
    "COUNTRY": "COUNTRY",
    "LAUNCH DATE": "LAUNCH DATE",
    "LAUNCH_ YEAR": "LAUNCH_ YEAR",
    "LAUNCH_ NUM": "LAUNCH_ NUM",
    "LAUNCH_ PIECE": "LAUNCH_ PIECE",
    "SITE": "SITE",
    "DECAY": "DECAY",
    "PERIOD": "PERIOD",
    "INCLINATION": "INCLINATION",
    "APOGEE": "APOGEE",
    "PERIGEE": "PERIGEE",
    "RCS_SIZE": "RCS_SIZE",
    "ALTITUDE": "ALTITUDE",
    "ORBITAL LIFE YEARS (right in numbers, no need to write any text- in yrs)": "ORBITAL LIFE YEARS (right in numbers, no need to write any text- in yrs)",
    "Launch Orbit Classification (ISRO)\n(GTO, LEO, SSO)": "Launch Orbit Classification (ISRO)",
    "No. of payloads": "No. of payloads",
    "Type of Satellite (Communication/ Earth Observation / Experimental / Navigation / Science & Exploration)": "Type of Satellite (Communication/ Earth Observation / Experimental / Navigation / Science & Exploration)",
    "Satellite Application Description": "Satellite Application Description",
    "Satellite Application Source": "Satellite Application Source",
    "Sensor Specifications (if applicable)": "Sensor Specifications (if applicable)",
    "Spectral Bands": "Spectral Bands",
    "Spatial Resolution": "Spatial Resolution",
    "Technological breakthroughs": "Technological breakthroughs",
    "Technological Breakthroughs Source": "Technological Breakthroughs Source",
    "Max Launch Mass of Vehicle to LEO (Kg) ": "Max Launch Mass of Vehicle to LEO (Kg)",
    "Max Launch Mass  Reference": "Max Launch Mass Reference",
    "Actual Launch Mass Carried by the Vehicle (Kg)": "Actual Launch Mass Carried by the Vehicle (Kg)",
    "Actual Launch Mass  Reference": "Actual Launch Mass Reference",
    "LAUNCH SUCCESS (1) / FAILURE (0)": "LAUNCH SUCCESS (1) / FAILURE (0)",
    "VEHICLE RESUABILITY (0/1)": "VEHICLE RESUABILITY (0/1)",
    "Vehicle Resubaility Details (First stage/ second stage/ or more)": "Vehicle Resubaility Details (First stage/ second stage/ or more)",
    "Vehicle Resuability Source": "Vehicle Resuability Source",
    "MISSION COST (Overall Mission Cost, Vehicle (Launch) Cost, Development Cost, Approved Cost, Operational Cost) by Official instutiuons or Space Agencies ": "MISSION COST (Overall Mission Cost, Vehicle (Launch) Cost, Development Cost, Approved Cost, Operational Cost) by Official instutiuons or Space Agencies",
    "Mission Cost Source": "Mission Cost Source",
    "SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year: https://nextspaceflight.com/launches/ ": "SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year",
    "Launch Vehicle Cost Source": "Launch Vehicle Cost Source",
    " SATELLITE Cost by Govt/ Parliament/ Space Agency (in $ million) in launch year": "SATELLITE Cost by Govt/ Parliament/ Space Agency (in $ million) in launch year",
    "Satellite Development Cost Source": "Satellite Development Cost Source",
    "MISSION/SATELLITE Cost by Other / News/ Wiklipedia sources (in $ million) in launch year": "MISSION/SATELLITE Cost by Other / News/ Wiklipedia sources (in $ million) in launch year",
    "Other Reported Cost Source": "Other Reported Cost Source",
    "COST Reference": "COST Reference",
    "Other Insights/ Comments": "Other Insights/ Comments",
}

RAW_GPT_TO_CANONICAL = {
    "RA Name ": "RA Name",
    "INTLDES": "INTLDES",
    "NORAD_ CAT_ID": "NORAD_ CAT_ID",
    "OBJECT_ TYPE": "OBJECT_ TYPE",
    "SATNAME": "SATNAME",
    "MISSION NAME": "MISSION NAME",
    "VEHICLE TYPE NAME": "VEHICLE TYPE NAME",
    "REGION": "REGION",
    "COUNTRY": "COUNTRY",
    "LAUNCH DATE": "LAUNCH DATE",
    "USER": "USER",
    "USER CATEGORY NUMBER\n(1: Military\n2: Civil\n3: Commercial\n4: Government\n5: Mix (if multiple users are involved)": "USER CATEGORY NUMBER",
    "USER DESCRIPTION": "USER DESCRIPTION",
    "USER SOURCE LINK": "USER SOURCE LINK",
    "PURPOSE\n(1: Communications\n2: Earth Observation\n3: Navigation\n4: Space Science\n5: Technology Development)": "PURPOSE",
    "PURPOSE CATEGORY NUMBER": "PURPOSE CATEGORY NUMBER",
    "PURPOSE DESCRIPTION": "PURPOSE DESCRIPTION",
    "PURPOSE SOURCE LINK": "PURPOSE SOURCE LINK",
    "SDG CATEGORY\n(1: Economic if SDG= No Poverty, Zero Hunger, Decent Work and Economic Growth, Reduced Inequalities\n2: Social if SDG= Good Health and Well-being, Quality Education, Gender Equality, Responsible Consumption and Production, Partnerships for the Goals, Peace, Justice, and Strong Institutions\n3: Environmental if SDG= Clean Water and Sanitation, Affordable and Clean Energy, Sustainable Cities and Communities, Climate Action, Life Below Water,  Life on Land.\n4: Innovation if SDG= Industry, Innovation, and Infrastructure)": "SDG CATEGORY",
    "SDG CATEGORY IDENTIFICATION NUMBERS": "SDG CATEGORY IDENTIFICATION NUMBERS",
    "SDG DESCRIPTION": "SDG DESCRIPTION",
    "SDG SOURCE LINK": "SDG SOURCE LINK",
    "FRUGAL (YES/ NO)": "FRUGAL (YES/ NO)",
    "Development Cost Efficiency (0/1)": "Development Cost Efficiency (0/1)",
    "Development Cost Efficiency Description ": "Development Cost Efficiency Description",
    "Dev cost efficiency source": "Dev cost efficiency source",
    "Operational Cost Efficiency (0/1)": "Operational Cost Efficiency (0/1)",
    "Operational Cost Efficiency Description ": "Operational Cost Efficiency Description",
    "ops cost efficiency source": "ops cost efficiency source",
    "Labour Cost Efficiency (0/1)": "Labour Cost Efficiency (0/1)",
    "Labour Cost Efficiency Description ": "Labour Cost Efficiency Description",
    "Labour cost efficiency source": "Labour cost efficiency source",
    "Frugal Innovation Design (0/1)": "Frugal Innovation Design (0/1)",
    "Frugal Innovation Design Description ": "Frugal Innovation Design Description",
    "frugal innovation design source\n\n": "frugal innovation design source",
    "Return on Investment ": "Return on Investment",
    "Data of Revenue from Satellite Launch ($ million) ": "Data of Revenue from Satellite Launch ($ million)",
    "Return on Investment Description": "Return on Investment Description",
    "Source": "Source",
}

CANONICAL_TO_RAW_DATA = {v: k for k, v in RAW_DATA_TO_CANONICAL.items()}
CANONICAL_TO_RAW_GPT = {v: k for k, v in RAW_GPT_TO_CANONICAL.items()}

DATA_ESSENTIALS = [
    "SATNAME",
    "LAUNCH DATE",
    "COUNTRY",
    "OBJECT_ TYPE",
    "VEHICLE TYPE NAME",
    "Type of Satellite (Communication/ Earth Observation / Experimental / Navigation / Science & Exploration)",
    "Satellite Application Description",
]

GPT_ESSENTIALS = [
    "USER",
    "USER CATEGORY NUMBER",
    "PURPOSE",
    "PURPOSE CATEGORY NUMBER",
    "SDG CATEGORY",
    "SDG DESCRIPTION",
    "FRUGAL (YES/ NO)",
]

PLACEHOLDER_TOKENS = {"na", "n/a", "nil", "none", "unknown", "not available", "tbd"}


@dataclass
class ProjectContext:
    raw_data_df: Optional[pd.DataFrame] = None
    raw_gpt_df: Optional[pd.DataFrame] = None
    data_df: Optional[pd.DataFrame] = None
    gpt_df: Optional[pd.DataFrame] = None
    audit_df: Optional[pd.DataFrame] = None


def _canonicalize(raw_df: pd.DataFrame, mapping: Dict[str, str], target_columns: List[str]) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return ensure_columns(pd.DataFrame(), target_columns)
    out = raw_df.copy()
    rename_map = {col: mapping[col] for col in out.columns if col in mapping}
    out = out.rename(columns=rename_map)
    unnamed_cols = [c for c in out.columns if safe_str(c).lower().startswith("unnamed:")]
    if unnamed_cols:
        out = out.drop(columns=unnamed_cols)
    out = ensure_columns(out, target_columns)
    return out


def canonicalize_existing_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    return _canonicalize(raw_df, RAW_DATA_TO_CANONICAL, DATA_COLUMNS)


def canonicalize_existing_gpt(raw_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = [c for c in GPT_COLUMNS if c not in {"TIP", "TIP Description", "TIP Source", "NIS", "NIS Description", "NIS Source", "MATCH TYPE", "MATCH SCORE", "CONFIDENCE", "REVIEW STATUS", "EXTRACTION DATE"}]
    return _canonicalize(raw_df, RAW_GPT_TO_CANONICAL, base_cols)


def _norm_cell(value) -> str:
    return safe_str(value).strip()


def _is_placeholder(value) -> bool:
    s = safe_str(value).strip().lower()
    return s in PLACEHOLDER_TOKENS


def _make_row_key(intldes, norad, satname) -> str:
    if not is_blank(intldes):
        return f"INTLDES::{safe_str(intldes).upper().strip()}"
    if not is_blank(norad):
        return f"NORAD::{safe_str(norad).strip()}"
    if not is_blank(satname):
        return f"SATNAME::{normalize_name(satname)}"
    return ""


def _add_key(df: pd.DataFrame, norad_col: str) -> pd.DataFrame:
    out = df.copy()
    out["ROW_KEY"] = [
        _make_row_key(r.get("INTLDES", ""), r.get(norad_col, ""), r.get("SATNAME", ""))
        for _, r in out.iterrows()
    ]
    return out


def _first_nonblank(series: pd.Series):
    for v in series:
        if not is_blank(v):
            return v
    return ""


def _collapse_by_key(df: pd.DataFrame, norad_col: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    keyed = _add_key(df, norad_col)
    keyed = keyed[keyed["ROW_KEY"] != ""].copy()
    if keyed.empty:
        return keyed
    agg = {}
    for col in keyed.columns:
        if col == "ROW_KEY":
            continue
        agg[col] = _first_nonblank
    collapsed = keyed.groupby("ROW_KEY", as_index=False).agg(agg)
    counts = keyed.groupby("ROW_KEY").size().reset_index(name="DUPLICATE_COUNT")
    collapsed = collapsed.merge(counts, on="ROW_KEY", how="left")
    return collapsed


def _completeness(row: pd.Series, columns: List[str]) -> Tuple[int, int, float, List[str]]:
    missing = []
    filled = 0
    for col in columns:
        value = row.get(col, "")
        if is_blank(value) or _is_placeholder(value):
            missing.append(col)
        else:
            filled += 1
    total = len(columns)
    pct = round(filled / total, 2) if total else 0.0
    return filled, total, pct, missing


def _has_leftovers(row: pd.Series) -> bool:
    for value in row.values:
        s = safe_str(value).upper()
        if "LEFTOVERS:" in s:
            return True
    return False


def _placeholder_count(row: pd.Series) -> int:
    count = 0
    for value in row.values:
        if _is_placeholder(value):
            count += 1
    return count


def analyze_existing_project(raw_data_df: pd.DataFrame, raw_gpt_df: pd.DataFrame) -> ProjectContext:
    data_df = canonicalize_existing_data(raw_data_df)
    gpt_df = canonicalize_existing_gpt(raw_gpt_df)

    data_grouped = _collapse_by_key(data_df, "SATELLITE CODE")
    gpt_grouped = _collapse_by_key(gpt_df, "NORAD_ CAT_ID")

    merged = pd.merge(data_grouped, gpt_grouped, on="ROW_KEY", how="outer", suffixes=("__DATA", "__GPT"))
    rows = []
    for _, row in merged.iterrows():
        satname = _first_nonblank(pd.Series([row.get("SATNAME__DATA", ""), row.get("SATNAME__GPT", "")]))
        intldes = _first_nonblank(pd.Series([row.get("INTLDES__DATA", ""), row.get("INTLDES__GPT", "")]))
        norad = _first_nonblank(pd.Series([row.get("SATELLITE CODE", ""), row.get("NORAD_ CAT_ID", "")]))
        country = _first_nonblank(pd.Series([row.get("COUNTRY__DATA", ""), row.get("COUNTRY__GPT", "")]))
        region = _first_nonblank(pd.Series([row.get("REGION__DATA", ""), row.get("REGION__GPT", "")]))
        ra_data = safe_str(row.get("RA NAME", ""))
        ra_gpt = safe_str(row.get("RA Name", ""))
        assigned_ra = " | ".join([x for x in [ra_data, ra_gpt] if not is_blank(x)])

        data_exists = not is_blank(row.get("SATNAME__DATA", "")) or not is_blank(row.get("INTLDES__DATA", ""))
        gpt_exists = not is_blank(row.get("SATNAME__GPT", "")) or not is_blank(row.get("INTLDES__GPT", ""))

        data_row = {
            c: row.get(f"{c}__DATA", row.get(c, ""))
            for c in DATA_COLUMNS
        }
        gpt_row = {
            c: row.get(f"{c}__GPT", row.get(c, ""))
            for c in [c for c in GPT_COLUMNS if c in gpt_df.columns]
        }
        data_filled, data_total, data_pct, data_missing = _completeness(pd.Series(data_row), DATA_ESSENTIALS)
        gpt_filled, gpt_total, gpt_pct, gpt_missing = _completeness(pd.Series(gpt_row), GPT_ESSENTIALS)

        has_leftovers = _has_leftovers(pd.Series(list(data_row.values()) + list(gpt_row.values())))
        placeholder_count = _placeholder_count(pd.Series(list(data_row.values()) + list(gpt_row.values())))
        has_source_gap = False
        if gpt_exists:
            for source_col in ["USER SOURCE LINK", "PURPOSE SOURCE LINK", "SDG SOURCE LINK", "Source"]:
                if source_col in gpt_row and is_blank(gpt_row[source_col]):
                    has_source_gap = True
                    break

        if data_exists and not gpt_exists:
            status = "Missing GPT row"
        elif gpt_exists and not data_exists:
            status = "Missing DATA row"
        elif data_pct >= 0.86 and gpt_pct >= 0.86 and not has_leftovers and not has_source_gap and placeholder_count <= 2:
            status = "Complete"
        elif gpt_pct < 0.40 and data_pct >= 0.40:
            status = "Needs GPT fill"
        elif data_pct < 0.40 and gpt_pct >= 0.40:
            status = "Needs DATA fill"
        else:
            status = "Partial / Review"

        if not assigned_ra:
            owner_state = "Unassigned"
        else:
            owner_state = "Assigned"

        priority_score = 0
        priority_score += len(data_missing) + len(gpt_missing)
        priority_score += 3 if not assigned_ra else 0
        priority_score += 2 if has_leftovers else 0
        priority_score += 2 if has_source_gap else 0
        priority_score += min(placeholder_count, 5)
        if status == "Missing GPT row":
            priority_score += 4
        elif status == "Needs GPT fill":
            priority_score += 3
        elif status == "Missing DATA row":
            priority_score += 3

        rows.append(
            {
                "ROW_KEY": row["ROW_KEY"],
                "INTLDES": intldes,
                "NORAD_ CAT_ID": norad,
                "SATNAME": satname,
                "COUNTRY": country,
                "REGION": region,
                "RA_DATA": ra_data,
                "RA_GPT": ra_gpt,
                "ASSIGNED_RA": assigned_ra,
                "OWNER_STATE": owner_state,
                "DATA_ROW_EXISTS": data_exists,
                "GPT_ROW_EXISTS": gpt_exists,
                "DATA_COMPLETENESS_PCT": data_pct,
                "GPT_COMPLETENESS_PCT": gpt_pct,
                "DATA_MISSING_FIELDS": ", ".join(data_missing),
                "GPT_MISSING_FIELDS": ", ".join(gpt_missing),
                "PLACEHOLDER_COUNT": placeholder_count,
                "HAS_LEFTOVERS": has_leftovers,
                "HAS_SOURCE_GAP": has_source_gap,
                "STATUS": status,
                "PRIORITY_SCORE": priority_score,
                "DATA_DUPLICATE_COUNT": row.get("DUPLICATE_COUNT__DATA", row.get("DUPLICATE_COUNT_x", row.get("DUPLICATE_COUNT", 0))),
                "GPT_DUPLICATE_COUNT": row.get("DUPLICATE_COUNT__GPT", row.get("DUPLICATE_COUNT_y", row.get("DUPLICATE_COUNT", 0))),
            }
        )

    audit_df = pd.DataFrame(rows).sort_values(["PRIORITY_SCORE", "STATUS", "COUNTRY", "SATNAME"], ascending=[False, True, True, True]).reset_index(drop=True)
    return ProjectContext(raw_data_df=raw_data_df, raw_gpt_df=raw_gpt_df, data_df=data_df, gpt_df=gpt_df, audit_df=audit_df)


def build_processing_input_from_audit_selection(
    selected_audit_df: pd.DataFrame,
    existing_data_df: pd.DataFrame,
    existing_gpt_df: pd.DataFrame,
) -> pd.DataFrame:
    data_keyed = _collapse_by_key(existing_data_df, "SATELLITE CODE") if existing_data_df is not None else pd.DataFrame()
    gpt_keyed = _collapse_by_key(existing_gpt_df, "NORAD_ CAT_ID") if existing_gpt_df is not None else pd.DataFrame()
    data_map = {r["ROW_KEY"]: r for _, r in data_keyed.iterrows()} if not data_keyed.empty else {}
    gpt_map = {r["ROW_KEY"]: r for _, r in gpt_keyed.iterrows()} if not gpt_keyed.empty else {}

    rows = []
    for _, audit_row in selected_audit_df.iterrows():
        key = audit_row["ROW_KEY"]
        d = data_map.get(key)
        g = gpt_map.get(key)
        comments_value = safe_str(d.get("Other Insights/ Comments", "")) if d is not None else ""
        if "LEFTOVERS:" in comments_value.upper():
            comments_value = ""
        row = {
            "RA NAME": safe_str(audit_row.get("ASSIGNED_RA", "")) or safe_str(audit_row.get("RA_DATA", "")) or safe_str(audit_row.get("RA_GPT", "")),
            "SATNAME": safe_str(audit_row.get("SATNAME", "")),
            "NORAD_ CAT_ID": safe_str(audit_row.get("NORAD_ CAT_ID", "")),
            "INTLDES": safe_str(audit_row.get("INTLDES", "")),
            "COUNTRY": safe_str(audit_row.get("COUNTRY", "")),
            "REGION": safe_str(audit_row.get("REGION", "")),
            "VEHICLE TYPE NAME": safe_str(d.get("VEHICLE TYPE NAME", "")) if d is not None else safe_str(g.get("VEHICLE TYPE NAME", "")) if g is not None else "",
            "LAUNCH DATE": safe_str(d.get("LAUNCH DATE", "")) if d is not None else safe_str(g.get("LAUNCH DATE", "")) if g is not None else "",
            "OBJECT_ TYPE": safe_str(d.get("OBJECT_ TYPE", "")) if d is not None else safe_str(g.get("OBJECT_ TYPE", "")) if g is not None else "",
            "Operator/Owner": safe_str(g.get("USER DESCRIPTION", "")) if g is not None else "",
            "Users": safe_str(g.get("USER", "")) if g is not None else "",
            "Purpose": safe_str(g.get("PURPOSE", "")) if g is not None else safe_str(d.get("Type of Satellite (Communication/ Earth Observation / Experimental / Navigation / Science & Exploration)", "")) if d is not None else "",
            "Detailed Purpose": safe_str(g.get("PURPOSE DESCRIPTION", "")) if g is not None else safe_str(d.get("Satellite Application Description", "")) if d is not None else "",
            "Comments": comments_value,
            "Sensor Specifications (if applicable)": safe_str(d.get("Sensor Specifications (if applicable)", "")) if d is not None else "",
            "Spectral Bands": safe_str(d.get("Spectral Bands", "")) if d is not None else "",
            "Spatial Resolution": safe_str(d.get("Spatial Resolution", "")) if d is not None else "",
            "Technological breakthroughs": safe_str(d.get("Technological breakthroughs", "")) if d is not None else "",
            "Launch Mass (kg.)": safe_str(d.get("Actual Launch Mass Carried by the Vehicle (Kg)", "")) if d is not None else "",
            "Expected Lifetime (yrs.)": safe_str(d.get("ORBITAL LIFE YEARS (right in numbers, no need to write any text- in yrs)", "")) if d is not None else "",
            "Class of Orbit": safe_str(d.get("Launch Orbit Classification (ISRO)", "")) if d is not None else "",
            "SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year": safe_str(d.get("SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year", "")) if d is not None else "",
            "Actual Launch Mass Carried by the Vehicle (Kg)": safe_str(d.get("Actual Launch Mass Carried by the Vehicle (Kg)", "")) if d is not None else "",
        }
        rows.append(row)
    return pd.DataFrame(rows)


def filter_work_queue(
    audit_df: pd.DataFrame,
    statuses: Optional[List[str]] = None,
    country: Optional[str] = None,
    only_unassigned: bool = False,
    max_rows: int = 100,
) -> pd.DataFrame:
    if audit_df is None or audit_df.empty:
        return pd.DataFrame()
    out = audit_df.copy()
    if statuses:
        out = out[out["STATUS"].isin(statuses)]
    if country and country != "All":
        out = out[out["COUNTRY"] == country]
    if only_unassigned:
        out = out[out["OWNER_STATE"] == "Unassigned"]
    out = out.sort_values(["PRIORITY_SCORE", "STATUS", "COUNTRY", "SATNAME"], ascending=[False, True, True, True])
    return out.head(max_rows).reset_index(drop=True)


def _merge_canonical(existing_df: pd.DataFrame, generated_df: pd.DataFrame, key_col_existing: str, key_col_generated: str, keep_existing_nonblank: bool = True) -> pd.DataFrame:
    existing_keyed = _add_key(existing_df, key_col_existing) if existing_df is not None else pd.DataFrame()
    generated_keyed = _add_key(generated_df, key_col_generated) if generated_df is not None else pd.DataFrame()

    if existing_keyed.empty:
        return generated_keyed.drop(columns=["ROW_KEY"], errors="ignore")
    if generated_keyed.empty:
        return existing_keyed.drop(columns=["ROW_KEY"], errors="ignore")

    existing_idx = {r["ROW_KEY"]: i for i, r in existing_keyed.iterrows() if safe_str(r["ROW_KEY"]) != ""}
    out = existing_keyed.copy()

    for _, gen_row in generated_keyed.iterrows():
        key = gen_row["ROW_KEY"]
        if not key:
            continue
        if key in existing_idx:
            i = existing_idx[key]
            for col in generated_keyed.columns:
                if col == "ROW_KEY" or col not in out.columns:
                    continue
                if keep_existing_nonblank and not is_blank(out.at[i, col]):
                    continue
                if not is_blank(gen_row[col]):
                    out.at[i, col] = gen_row[col]
        else:
            new_row = {col: "" for col in out.columns}
            for col in generated_keyed.columns:
                if col in new_row:
                    new_row[col] = gen_row[col]
            out = pd.concat([out, pd.DataFrame([new_row])], ignore_index=True)
    return out.drop(columns=["ROW_KEY"], errors="ignore")


def merge_generated_into_existing(existing_data_df: pd.DataFrame, existing_gpt_df: pd.DataFrame, generated_data_df: pd.DataFrame, generated_gpt_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    merged_data = _merge_canonical(existing_data_df, generated_data_df, "SATELLITE CODE", "SATELLITE CODE")
    merged_gpt = _merge_canonical(existing_gpt_df, generated_gpt_df, "NORAD_ CAT_ID", "NORAD_ CAT_ID")
    merged_data = ensure_columns(merged_data, DATA_COLUMNS)
    base_gpt_cols = [c for c in GPT_COLUMNS if c in merged_gpt.columns or c in generated_gpt_df.columns]
    merged_gpt = ensure_columns(merged_gpt, base_gpt_cols)
    return merged_data, merged_gpt


def decanonicalize_data_for_export(canonical_df: pd.DataFrame, raw_template_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    out = pd.DataFrame()
    ordered_cols = list(raw_template_df.columns) if raw_template_df is not None and not raw_template_df.empty else list(RAW_DATA_TO_CANONICAL.keys())
    for raw_col in ordered_cols:
        if raw_col in RAW_DATA_TO_CANONICAL:
            can_col = RAW_DATA_TO_CANONICAL[raw_col]
            out[raw_col] = canonical_df[can_col] if can_col in canonical_df.columns else ""
        else:
            out[raw_col] = ""
    return out


def decanonicalize_gpt_for_export(canonical_df: pd.DataFrame, raw_template_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    out = pd.DataFrame()
    ordered_cols = list(raw_template_df.columns) if raw_template_df is not None and not raw_template_df.empty else list(RAW_GPT_TO_CANONICAL.keys())
    for raw_col in ordered_cols:
        if raw_col in RAW_GPT_TO_CANONICAL:
            can_col = RAW_GPT_TO_CANONICAL[raw_col]
            out[raw_col] = canonical_df[can_col] if can_col in canonical_df.columns else ""
        else:
            out[raw_col] = ""
    return out
