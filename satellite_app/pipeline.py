from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz, process

from .constants import DATA_COLUMNS, EVIDENCE_COLUMNS, GPT_COLUMNS, KNOWN_COL_ALIASES, NEXTSPACEFLIGHT_LAUNCHES_URL, NUMERIC_COLUMNS, PLANET4589_LV_URL
from .helpers import (
    average_altitude,
    best_text_snippet,
    classify_isro_orbit,
    ensure_columns,
    get_col,
    infer_region_from_country,
    is_blank,
    multi_join,
    parse_intldes_parts,
    pick_first_value,
    safe_str,
    standardize_country,
    to_float,
    to_int_str,
    year_from_date,
)
from .preferred_rag import retrieve_priority_context
from .scoring import (
    determine_review_status,
    estimate_orbital_life_years,
    infer_frugal,
    infer_nis,
    infer_purpose_category,
    infer_sdg,
    infer_tip,
    infer_user_category,
    make_numeric_record,
    map_purpose_to_data_type,
)
from .sources import find_celestrak_match, find_ucs_match, wikipedia_lookup


VEHICLE_REF_PATH = Path(__file__).resolve().parent.parent / "launch_vehicle_reference.csv"


def load_vehicle_reference() -> pd.DataFrame:
    df = pd.read_csv(VEHICLE_REF_PATH)
    df = df.copy()
    df["__norm_vehicle__"] = df["vehicle_name"].str.upper().str.replace(r"[^A-Z0-9]+", " ", regex=True).str.strip()
    return df


def normalize_vehicle_name(value: str) -> str:
    return safe_str(value).upper().replace("/", " ").replace("-", " ").strip()


def find_vehicle_match(vehicle_name: str, vehicle_df: Optional[pd.DataFrame]) -> Tuple[Optional[pd.Series], float]:
    if vehicle_df is None or vehicle_df.empty or is_blank(vehicle_name):
        return None, 0.0
    norm_vehicle = normalize_vehicle_name(vehicle_name)
    exact = vehicle_df[vehicle_df["__norm_vehicle__"] == norm_vehicle]
    if not exact.empty:
        return exact.iloc[0], 1.0
    best = process.extractOne(norm_vehicle, vehicle_df["__norm_vehicle__"].tolist(), scorer=fuzz.token_set_ratio)
    if best:
        _, score, idx = best
        if score >= 70:
            return vehicle_df.iloc[idx], round(score / 100.0, 2)
    return None, 0.0


def get_series_value(series: Optional[pd.Series], canonical: str) -> str:
    if series is None:
        return ""
    for key in KNOWN_COL_ALIASES.get(canonical, [canonical]):
        if key in series and not is_blank(series[key]):
            return safe_str(series[key])
    return ""


def canonical_from_input_row(row: pd.Series, canonical: str) -> str:
    return get_series_value(row, canonical)


def pick_with_source(candidates: List[Tuple[str, str, str]]) -> Tuple[str, str, str]:
    for value, source_name, source_url in candidates:
        if not is_blank(value):
            return safe_str(value), source_name, source_url
    return "", "", ""


def build_evidence_bundle(
    input_row: pd.Series,
    ucs_row: Optional[pd.Series],
    celestrak_row: Optional[pd.Series],
    wiki: Dict[str, str],
    preferred_retrieval: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    retrieval_text = safe_str((preferred_retrieval or {}).get("combined_text", ""))
    retrieval_snippets = multi_join((preferred_retrieval or {}).get("snippets", []), sep=" || ")

    operator = pick_first_value(
        canonical_from_input_row(input_row, "Operator/Owner"),
        get_series_value(ucs_row, "Operator/Owner"),
    )
    users = pick_first_value(
        canonical_from_input_row(input_row, "Users"),
        get_series_value(ucs_row, "Users"),
    )
    purpose = pick_first_value(
        canonical_from_input_row(input_row, "Purpose"),
        get_series_value(ucs_row, "Purpose"),
    )
    detailed_purpose = pick_first_value(
        canonical_from_input_row(input_row, "Detailed Purpose"),
        get_series_value(ucs_row, "Detailed Purpose"),
        wiki.get("summary", ""),
        retrieval_snippets,
    )
    comments = pick_first_value(
        canonical_from_input_row(input_row, "Comments"),
        get_series_value(ucs_row, "Comments"),
        retrieval_snippets,
    )
    sensors = pick_first_value(
        canonical_from_input_row(input_row, "Sensor Specifications (if applicable)"),
        get_series_value(ucs_row, "Sensor Specifications (if applicable)"),
    )
    spectral = pick_first_value(
        canonical_from_input_row(input_row, "Spectral Bands"),
        get_series_value(ucs_row, "Spectral Bands"),
    )
    resolution = pick_first_value(
        canonical_from_input_row(input_row, "Spatial Resolution"),
        get_series_value(ucs_row, "Spatial Resolution"),
    )
    breakthroughs = pick_first_value(
        canonical_from_input_row(input_row, "Technological breakthroughs"),
        get_series_value(ucs_row, "Technological breakthroughs"),
    )
    return {
        "operator": operator,
        "users": users,
        "purpose": purpose,
        "detailed_purpose": detailed_purpose,
        "comments": comments,
        "sensors": sensors,
        "spectral": spectral,
        "resolution": resolution,
        "breakthroughs": breakthroughs,
        "wiki_summary": wiki.get("summary", ""),
        "retrieval_text": retrieval_text,
        "retrieval_source_url": safe_str((preferred_retrieval or {}).get("top_source_url", "")),
        "all_text": multi_join([
            operator,
            users,
            purpose,
            detailed_purpose,
            comments,
            sensors,
            spectral,
            resolution,
            breakthroughs,
            wiki.get("summary", ""),
            retrieval_text,
        ], sep=" || "),
    }


def build_data_record(
    input_row: pd.Series,
    ucs_row: Optional[pd.Series],
    ucs_meta: Tuple[str, float, str],
    celestrak_row: Optional[pd.Series],
    celestrak_meta: Tuple[str, float, str],
    wiki: Dict[str, str],
    vehicle_row: Optional[pd.Series],
    preferred_retrieval: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    ucs_match_type, ucs_score, ucs_url = ucs_meta
    cel_match_type, cel_score, cel_url = celestrak_meta

    intldes, _, _ = pick_with_source([
        (canonical_from_input_row(input_row, "INTLDES"), "Input", ""),
        (get_series_value(ucs_row, "INTLDES"), f"UCS ({ucs_match_type})", ucs_url),
        (safe_str(celestrak_row["OBJECT_ID"]) if celestrak_row is not None and "OBJECT_ID" in celestrak_row else "", f"CelesTrak ({cel_match_type})", cel_url),
    ])

    norad, _, _ = pick_with_source([
        (canonical_from_input_row(input_row, "NORAD_ CAT_ID"), "Input", ""),
        (get_series_value(ucs_row, "NORAD_ CAT_ID"), f"UCS ({ucs_match_type})", ucs_url),
        (safe_str(celestrak_row["NORAD_CAT_ID"]) if celestrak_row is not None and "NORAD_CAT_ID" in celestrak_row else "", f"CelesTrak ({cel_match_type})", cel_url),
    ])

    satname, satname_source, satname_url = pick_with_source([
        (canonical_from_input_row(input_row, "SATNAME"), "Input", ""),
        (get_series_value(ucs_row, "SATNAME"), f"UCS ({ucs_match_type})", ucs_url),
        (safe_str(celestrak_row["OBJECT_NAME"]) if celestrak_row is not None and "OBJECT_NAME" in celestrak_row else "", f"CelesTrak ({cel_match_type})", cel_url),
    ])

    object_type, _, _ = pick_with_source([
        (canonical_from_input_row(input_row, "OBJECT_ TYPE"), "Input", ""),
        (get_series_value(ucs_row, "OBJECT_ TYPE"), f"UCS ({ucs_match_type})", ucs_url),
        (safe_str(celestrak_row["OBJECT_TYPE"]) if celestrak_row is not None and "OBJECT_TYPE" in celestrak_row else "", f"CelesTrak ({cel_match_type})", cel_url),
    ])

    launch_date, _, _ = pick_with_source([
        (canonical_from_input_row(input_row, "LAUNCH DATE"), "Input", ""),
        (get_series_value(ucs_row, "LAUNCH DATE"), f"UCS ({ucs_match_type})", ucs_url),
        (safe_str(celestrak_row["LAUNCH_DATE"]) if celestrak_row is not None and "LAUNCH_DATE" in celestrak_row else "", f"CelesTrak ({cel_match_type})", cel_url),
    ])

    country = standardize_country(pick_first_value(
        canonical_from_input_row(input_row, "COUNTRY"),
        get_series_value(ucs_row, "COUNTRY"),
        safe_str(celestrak_row["OWNER"]) if celestrak_row is not None and "OWNER" in celestrak_row else "",
    ))

    region = pick_first_value(
        canonical_from_input_row(input_row, "REGION"),
        get_series_value(ucs_row, "REGION"),
        infer_region_from_country(country),
    )

    mission_name = pick_first_value(
        canonical_from_input_row(input_row, "MISSION NAME"),
        satname,
    )
    vehicle_name = pick_first_value(
        canonical_from_input_row(input_row, "VEHICLE TYPE NAME"),
        get_series_value(ucs_row, "VEHICLE TYPE NAME"),
    )

    site = pick_first_value(
        canonical_from_input_row(input_row, "SITE"),
        safe_str(celestrak_row["LAUNCH_SITE"]) if celestrak_row is not None and "LAUNCH_SITE" in celestrak_row else "",
    )
    decay = pick_first_value(
        canonical_from_input_row(input_row, "DECAY"),
        safe_str(celestrak_row["DECAY_DATE"]) if celestrak_row is not None and "DECAY_DATE" in celestrak_row else "",
    )
    period = pick_first_value(
        canonical_from_input_row(input_row, "PERIOD"),
        safe_str(celestrak_row["PERIOD"]) if celestrak_row is not None and "PERIOD" in celestrak_row else "",
    )
    inclination = pick_first_value(
        canonical_from_input_row(input_row, "INCLINATION"),
        safe_str(celestrak_row["INCLINATION"]) if celestrak_row is not None and "INCLINATION" in celestrak_row else "",
    )
    apogee = pick_first_value(
        canonical_from_input_row(input_row, "APOGEE"),
        safe_str(celestrak_row["APOGEE"]) if celestrak_row is not None and "APOGEE" in celestrak_row else "",
    )
    perigee = pick_first_value(
        canonical_from_input_row(input_row, "PERIGEE"),
        safe_str(celestrak_row["PERIGEE"]) if celestrak_row is not None and "PERIGEE" in celestrak_row else "",
    )
    rcs = pick_first_value(
        canonical_from_input_row(input_row, "RCS_SIZE"),
        safe_str(celestrak_row["RCS"]) if celestrak_row is not None and "RCS" in celestrak_row else "",
    )

    launch_year, launch_num, launch_piece = parse_intldes_parts(intldes)
    if not launch_year:
        launch_year = year_from_date(launch_date)

    class_of_orbit = pick_first_value(canonical_from_input_row(input_row, "Class of Orbit"), safe_str(celestrak_row["ORBIT_TYPE"]) if celestrak_row is not None and "ORBIT_TYPE" in celestrak_row else "")
    type_of_orbit = canonical_from_input_row(input_row, "Type of Orbit")
    orbit_class = classify_isro_orbit(class_of_orbit, type_of_orbit, apogee, perigee, inclination)

    evidence = build_evidence_bundle(input_row, ucs_row, celestrak_row, wiki, preferred_retrieval)
    purpose_label, _, purpose_desc, _ = infer_purpose_category(
        evidence["purpose"], evidence["detailed_purpose"], evidence["comments"], satname, wiki.get("summary", "") + " " + evidence.get("retrieval_text", "")
    )
    satellite_type = map_purpose_to_data_type(purpose_label)

    launch_mass = pick_first_value(
        canonical_from_input_row(input_row, "Actual Launch Mass Carried by the Vehicle (Kg)"),
        canonical_from_input_row(input_row, "Launch Mass (kg.)"),
        get_series_value(ucs_row, "Actual Launch Mass Carried by the Vehicle (Kg)"),
        get_series_value(ucs_row, "Launch Mass (kg.)"),
    )

    expected_lifetime = pick_first_value(canonical_from_input_row(input_row, "Expected Lifetime (yrs.)"), get_series_value(ucs_row, "Expected Lifetime (yrs.)"))
    orbital_life_years = estimate_orbital_life_years(launch_date, decay, expected_lifetime)

    vehicle_max_leo = safe_str(vehicle_row["max_leo_kg"]) if vehicle_row is not None else ""
    vehicle_max_source = safe_str(vehicle_row["max_leo_source"]) if vehicle_row is not None else PLANET4589_LV_URL
    vehicle_reusable = safe_str(vehicle_row["reusable_flag"]) if vehicle_row is not None else ""
    vehicle_reuse_details = safe_str(vehicle_row["reusability_details"]) if vehicle_row is not None else ""
    vehicle_reuse_source = safe_str(vehicle_row["reusability_source"]) if vehicle_row is not None else ""
    vehicle_launch_cost = pick_first_value(
        canonical_from_input_row(input_row, "SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year"),
        safe_str(vehicle_row["approx_launch_cost_musd"]) if vehicle_row is not None else "",
    )
    vehicle_launch_cost_source = safe_str(vehicle_row["launch_cost_source"]) if vehicle_row is not None else NEXTSPACEFLIGHT_LAUNCHES_URL

    no_payloads = pick_first_value(canonical_from_input_row(input_row, "No. of payloads"), "1" if object_type.upper() in {"PAY", "PAYLOAD"} else "")
    sat_code = pick_first_value(canonical_from_input_row(input_row, "SATELLITE CODE"), norad)

    data_record = {
        "__NORAD__": norad,
        "RA NAME": pick_first_value(canonical_from_input_row(input_row, "RA NAME"), canonical_from_input_row(input_row, "RA Name")),
        "INTLDES": intldes,
        "SATELLITE CODE": sat_code,
        "OBJECT_ TYPE": object_type,
        "SATNAME": satname,
        "MISSION NAME": mission_name,
        "VEHICLE TYPE NAME": vehicle_name,
        "REGION": region,
        "COUNTRY": country,
        "LAUNCH DATE": launch_date,
        "LAUNCH_ YEAR": launch_year,
        "LAUNCH_ NUM": launch_num,
        "LAUNCH_ PIECE": launch_piece,
        "SITE": site,
        "DECAY": decay,
        "PERIOD": period,
        "INCLINATION": inclination,
        "APOGEE": apogee,
        "PERIGEE": perigee,
        "RCS_SIZE": rcs,
        "ALTITUDE": average_altitude(apogee, perigee),
        "ORBITAL LIFE YEARS (right in numbers, no need to write any text- in yrs)": orbital_life_years,
        "Launch Orbit Classification (ISRO)": orbit_class,
        "No. of payloads": no_payloads,
        "Type of Satellite (Communication/ Earth Observation / Experimental / Navigation / Science & Exploration)": satellite_type,
        "Satellite Application Description": purpose_desc or wiki.get("summary", "") or best_text_snippet(evidence.get("retrieval_text", ""), 260),
        "Satellite Application Source": evidence.get("retrieval_source_url", "") or wiki.get("url", satname_url),
        "Sensor Specifications (if applicable)": evidence["sensors"],
        "Spectral Bands": evidence["spectral"],
        "Spatial Resolution": evidence["resolution"],
        "Technological breakthroughs": evidence["breakthroughs"],
        "Technological Breakthroughs Source": evidence.get("retrieval_source_url", "") or wiki.get("url", satname_url),
        "Max Launch Mass of Vehicle to LEO (Kg)": vehicle_max_leo,
        "Max Launch Mass Reference": vehicle_max_source,
        "Actual Launch Mass Carried by the Vehicle (Kg)": launch_mass,
        "Actual Launch Mass Reference": pick_first_value(canonical_from_input_row(input_row, "Actual Launch Mass Carried by the Vehicle (Kg)"), satname_url, cel_url, ucs_url),
        "LAUNCH SUCCESS (1) / FAILURE (0)": "1" if satname or norad or launch_date else "",
        "VEHICLE RESUABILITY (0/1)": vehicle_reusable,
        "Vehicle Resubaility Details (First stage/ second stage/ or more)": vehicle_reuse_details,
        "Vehicle Resuability Source": vehicle_reuse_source,
        "MISSION COST (Overall Mission Cost, Vehicle (Launch) Cost, Development Cost, Approved Cost, Operational Cost) by Official instutiuons or Space Agencies": canonical_from_input_row(input_row, "MISSION COST (Overall Mission Cost, Vehicle (Launch) Cost, Development Cost, Approved Cost, Operational Cost) by Official instutiuons or Space Agencies"),
        "Mission Cost Source": canonical_from_input_row(input_row, "Mission Cost Source"),
        "SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year": vehicle_launch_cost,
        "Launch Vehicle Cost Source": vehicle_launch_cost_source,
        "SATELLITE Cost by Govt/ Parliament/ Space Agency (in $ million) in launch year": canonical_from_input_row(input_row, "SATELLITE Cost by Govt/ Parliament/ Space Agency (in $ million) in launch year"),
        "Satellite Development Cost Source": canonical_from_input_row(input_row, "Satellite Development Cost Source"),
        "MISSION/SATELLITE Cost by Other / News/ Wiklipedia sources (in $ million) in launch year": canonical_from_input_row(input_row, "MISSION/SATELLITE Cost by Other / News/ Wiklipedia sources (in $ million) in launch year"),
        "Other Reported Cost Source": canonical_from_input_row(input_row, "Other Reported Cost Source"),
        "COST Reference": canonical_from_input_row(input_row, "COST Reference"),
        "Other Insights/ Comments": pick_first_value(canonical_from_input_row(input_row, "Other Insights/ Comments"), evidence["comments"]),
    }
    return data_record


def build_gpt_record(
    data_record: Dict[str, str],
    input_row: pd.Series,
    ucs_row: Optional[pd.Series],
    wiki: Dict[str, str],
    ucs_meta: Tuple[str, float, str],
    celestrak_meta: Tuple[str, float, str],
    preferred_retrieval: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    evidence = build_evidence_bundle(input_row, ucs_row, None, wiki, preferred_retrieval)
    ucs_match_type, ucs_score, ucs_url = ucs_meta
    cel_match_type, cel_score, cel_url = celestrak_meta
    best_match_type = ucs_match_type if ucs_score >= cel_score else cel_match_type
    best_match_score = max(ucs_score, cel_score)
    best_source = evidence.get("retrieval_source_url", "") or wiki.get("url") or ucs_url or cel_url

    user_label, user_num, user_desc, user_conf = infer_user_category(
        evidence["operator"],
        evidence["users"],
        evidence["comments"] + " " + evidence.get("retrieval_text", "") + " " + wiki.get("summary", ""),
        evidence["purpose"],
    )
    purpose_label, purpose_num, purpose_desc, purpose_conf = infer_purpose_category(
        evidence["purpose"], evidence["detailed_purpose"], evidence["comments"] + " " + evidence.get("retrieval_text", ""), data_record["SATNAME"], wiki.get("summary", "") + " " + evidence.get("retrieval_text", "")
    )
    sdg_cat, sdg_ids, sdg_desc, sdg_conf = infer_sdg(purpose_label, evidence["purpose"], evidence["comments"], evidence["users"])

    launch_mass_value = to_float(data_record.get("Actual Launch Mass Carried by the Vehicle (Kg)"))
    launch_cost_value = to_float(data_record.get("SATELLITE Vehicle Launch Cost by NextSpaceFlight (in $ million) in launch year"))
    frugal = infer_frugal(launch_mass_value, launch_cost_value, evidence["purpose"], evidence["comments"], data_record["SATNAME"], data_record["COUNTRY"])
    tip_ids, tip_desc = infer_tip(purpose_label, evidence["purpose"], evidence["comments"])
    nis_ids, nis_desc = infer_nis(purpose_label, evidence["purpose"], evidence["comments"], evidence["users"])

    retrieval_bonus = 0.05 if evidence.get("retrieval_source_url") else 0.0
    confidence = round(min(0.98, ((best_match_score + user_conf + purpose_conf + sdg_conf) / 4) + retrieval_bonus), 2)
    review_status = determine_review_status(confidence, user_label, purpose_label, sdg_cat)

    record = {
        "RA Name": data_record.get("RA NAME", ""),
        "INTLDES": data_record.get("INTLDES", ""),
        "NORAD_ CAT_ID": data_record.get("__NORAD__", data_record.get("SATELLITE CODE", "")),
        "OBJECT_ TYPE": data_record.get("OBJECT_ TYPE", ""),
        "SATNAME": data_record.get("SATNAME", ""),
        "MISSION NAME": data_record.get("MISSION NAME", ""),
        "VEHICLE TYPE NAME": data_record.get("VEHICLE TYPE NAME", ""),
        "REGION": data_record.get("REGION", ""),
        "COUNTRY": data_record.get("COUNTRY", ""),
        "LAUNCH DATE": data_record.get("LAUNCH DATE", ""),
        "USER": user_label,
        "USER CATEGORY NUMBER": user_num,
        "USER DESCRIPTION": user_desc,
        "USER SOURCE LINK": best_source,
        "PURPOSE": purpose_label,
        "PURPOSE CATEGORY NUMBER": purpose_num,
        "PURPOSE DESCRIPTION": purpose_desc,
        "PURPOSE SOURCE LINK": best_source,
        "SDG CATEGORY": sdg_cat,
        "SDG CATEGORY IDENTIFICATION NUMBERS": sdg_ids,
        "SDG DESCRIPTION": sdg_desc,
        "SDG SOURCE LINK": best_source,
        **frugal,
        "TIP": tip_ids,
        "TIP Description": tip_desc,
        "TIP Source": best_source,
        "NIS": nis_ids,
        "NIS Description": nis_desc,
        "NIS Source": best_source,
        "MATCH TYPE": best_match_type,
        "MATCH SCORE": best_match_score,
        "CONFIDENCE": confidence,
        "REVIEW STATUS": review_status,
        "EXTRACTION DATE": pd.Timestamp.now().strftime("%Y-%m-%d"),
    }
    return record


def build_evidence_rows(
    row_id: int,
    data_record: Dict[str, str],
    ucs_meta: Tuple[str, float, str],
    celestrak_meta: Tuple[str, float, str],
    wiki: Dict[str, str],
    evidence_text: str,
    preferred_retrieval: Optional[Dict[str, object]] = None,
) -> List[Dict[str, str]]:
    ucs_match_type, _, ucs_url = ucs_meta
    cel_match_type, _, cel_url = celestrak_meta
    satname = data_record.get("SATNAME", "")
    norad = data_record.get("SATELLITE CODE", "")
    rows = [
        {
            "ROW_ID": row_id,
            "SATNAME": satname,
            "NORAD_ CAT_ID": norad,
            "SOURCE_NAME": "UCS Database",
            "SOURCE_URL": ucs_url,
            "MATCH_TYPE": ucs_match_type,
            "FIELD_GROUP": "Primary structured source",
            "SNIPPET": "Matched against uploaded UCS database.",
            "STATUS": "Used",
        },
        {
            "ROW_ID": row_id,
            "SATNAME": satname,
            "NORAD_ CAT_ID": norad,
            "SOURCE_NAME": "CelesTrak SATCAT",
            "SOURCE_URL": cel_url,
            "MATCH_TYPE": cel_match_type,
            "FIELD_GROUP": "Orbit / catalog source",
            "SNIPPET": "Used for catalog, orbit, and launch metadata where available.",
            "STATUS": "Used",
        },
    ]
    if wiki:
        rows.append(
            {
                "ROW_ID": row_id,
                "SATNAME": satname,
                "NORAD_ CAT_ID": norad,
                "SOURCE_NAME": "Wikipedia",
                "SOURCE_URL": wiki.get("url", ""),
                "MATCH_TYPE": "Search summary",
                "FIELD_GROUP": "Fallback narrative source",
                "SNIPPET": best_text_snippet(wiki.get("summary", "")),
                "STATUS": "Used" if wiki.get("summary") else "Missing",
            }
        )
    if preferred_retrieval and preferred_retrieval.get("page_records"):
        for page in preferred_retrieval.get("page_records", [])[:4]:
            rows.append(
                {
                    "ROW_ID": row_id,
                    "SATNAME": satname,
                    "NORAD_ CAT_ID": norad,
                    "SOURCE_NAME": page.get("title", "Preferred Website Source") or "Preferred Website Source",
                    "SOURCE_URL": page.get("url", ""),
                    "MATCH_TYPE": "Priority website retrieval",
                    "FIELD_GROUP": "Preferred website / RAG retrieval",
                    "SNIPPET": best_text_snippet(page.get("snippet", "")),
                    "STATUS": "Used",
                }
            )
    rows.append(
        {
            "ROW_ID": row_id,
            "SATNAME": satname,
            "NORAD_ CAT_ID": norad,
            "SOURCE_NAME": "Combined evidence",
            "SOURCE_URL": wiki.get("url") or cel_url or ucs_url,
            "MATCH_TYPE": "Merged",
            "FIELD_GROUP": "Heuristic classification text",
            "SNIPPET": best_text_snippet(evidence_text),
            "STATUS": "Used",
        }
    )
    return rows


def process_dataframe(
    input_df: pd.DataFrame,
    ucs_df: Optional[pd.DataFrame],
    satcat_df: Optional[pd.DataFrame],
    vehicle_df: Optional[pd.DataFrame],
    use_wikipedia: bool = True,
    use_preferred_rag: bool = True,
    preferred_country_websites_df: Optional[pd.DataFrame] = None,
    preferred_generic_websites_df: Optional[pd.DataFrame] = None,
    progress_callback=None,
):
    data_rows: List[Dict[str, str]] = []
    gpt_rows: List[Dict[str, str]] = []
    numeric_rows: List[Dict[str, str]] = []
    evidence_rows: List[Dict[str, str]] = []

    total = len(input_df)
    for idx, (_, row) in enumerate(input_df.iterrows(), start=1):
        satname_input = canonical_from_input_row(row, "SATNAME")
        norad_input = canonical_from_input_row(row, "NORAD_ CAT_ID")
        intldes_input = canonical_from_input_row(row, "INTLDES")

        ucs_row, ucs_match_type, ucs_score, ucs_url = find_ucs_match(satname_input, norad_input, intldes_input, ucs_df)
        cel_row, cel_match_type, cel_score, cel_url = find_celestrak_match(satname_input, norad_input, intldes_input, satcat_df)
        wiki = wikipedia_lookup(satname_input or get_series_value(ucs_row, "SATNAME")) if use_wikipedia else {}

        basic_evidence = build_evidence_bundle(row, ucs_row, cel_row, wiki)
        need_preferred_rag = use_preferred_rag and (
            is_blank(basic_evidence.get("users", ""))
            or is_blank(basic_evidence.get("purpose", ""))
            or is_blank(basic_evidence.get("detailed_purpose", ""))
            or len(safe_str(basic_evidence.get("all_text", ""))) < 120
        )
        preferred_retrieval = {}
        if need_preferred_rag:
            preferred_retrieval = retrieve_priority_context(
                satname=satname_input or get_series_value(ucs_row, "SATNAME"),
                intldes=intldes_input or get_series_value(ucs_row, "INTLDES"),
                norad=norad_input or get_series_value(ucs_row, "NORAD_ CAT_ID"),
                country_acronym=canonical_from_input_row(row, "COUNTRY") or get_series_value(ucs_row, "COUNTRY"),
                country_websites_df=preferred_country_websites_df,
                generic_websites_df=preferred_generic_websites_df,
            )

        vehicle_name = pick_first_value(canonical_from_input_row(row, "VEHICLE TYPE NAME"), get_series_value(ucs_row, "VEHICLE TYPE NAME"))
        vehicle_row, _ = find_vehicle_match(vehicle_name, vehicle_df)

        data_record = build_data_record(
            row,
            ucs_row,
            (ucs_match_type, ucs_score, ucs_url),
            cel_row,
            (cel_match_type, cel_score, cel_url),
            wiki,
            vehicle_row,
            preferred_retrieval,
        )
        gpt_record = build_gpt_record(
            data_record,
            row,
            ucs_row,
            wiki,
            (ucs_match_type, ucs_score, ucs_url),
            (cel_match_type, cel_score, cel_url),
            preferred_retrieval,
        )
        evidence_bundle = build_evidence_bundle(row, ucs_row, cel_row, wiki, preferred_retrieval)
        numeric_record = make_numeric_record(gpt_record, evidence_bundle["all_text"], evidence_bundle.get("retrieval_source_url", "") or wiki.get("url") or cel_url or ucs_url)
        evidence = build_evidence_rows(
            idx,
            data_record,
            (ucs_match_type, ucs_score, ucs_url),
            (cel_match_type, cel_score, cel_url),
            wiki,
            evidence_bundle["all_text"],
            preferred_retrieval,
        )

        data_rows.append(data_record)
        gpt_rows.append(gpt_record)
        numeric_rows.append(numeric_record)
        evidence_rows.extend(evidence)

        if progress_callback is not None:
            progress_callback(idx, total, data_record.get("SATNAME", satname_input))

    data_df = ensure_columns(pd.DataFrame(data_rows), DATA_COLUMNS)
    gpt_df = ensure_columns(pd.DataFrame(gpt_rows), GPT_COLUMNS)
    numeric_df = ensure_columns(pd.DataFrame(numeric_rows), NUMERIC_COLUMNS)
    evidence_df = ensure_columns(pd.DataFrame(evidence_rows), EVIDENCE_COLUMNS)
    return data_df, gpt_df, numeric_df, evidence_df
