import json
from typing import Optional

import pandas as pd
import streamlit as st

from satellite_app.constants import DATA_COLUMNS, EVIDENCE_COLUMNS, GPT_COLUMNS, NUMERIC_COLUMNS
from satellite_app.gsheets import (
    credentials_json_text_from_upload,
    list_worksheets,
    read_worksheet_as_df,
    write_df_to_worksheet,
)
from satellite_app.helpers import dataframe_to_excel_bytes, ensure_columns, excel_export_available, get_col, safe_str
from satellite_app.pipeline import load_vehicle_reference, process_dataframe
from satellite_app.project_audit import (
    ProjectContext,
    analyze_existing_project,
    build_processing_input_from_audit_selection,
    decanonicalize_data_for_export,
    decanonicalize_gpt_for_export,
    filter_work_queue,
    merge_generated_into_existing,
)
from satellite_app.sources import get_sheet_names, load_celestrak_satcat, prepare_ucs_dataframe_from_bytes, read_table_from_upload
from satellite_app.websites_catalog import parse_websites_catalog, websites_for_country


st.set_page_config(page_title="Satellite Project Successor Tool", page_icon="🛰️", layout="wide")


def inject_css():
    st.markdown(
        """
        <style>
        .main .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        .hero {
            background: linear-gradient(135deg, #091540 0%, #0b5ed7 50%, #29b6f6 100%);
            padding: 1.4rem 1.5rem;
            border-radius: 18px;
            color: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            margin-bottom: 1rem;
        }
        .hero h1 {margin: 0 0 0.35rem 0; font-size: 2rem;}
        .hero p {margin: 0; opacity: 0.95;}
        .small-note {color: #6c757d; font-size: 0.92rem;}
        .card {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(120,120,120,0.15);
            border-radius: 16px;
            padding: 1rem 1rem 0.8rem 1rem;
            margin-bottom: 0.85rem;
        }
        .success-box {
            background: #ecfdf3;
            border-left: 4px solid #10b981;
            padding: 0.8rem 1rem;
            border-radius: 10px;
            margin: 0.7rem 0;
            color: #065f46;
        }
        .warn-box {
            background: #fff8e6;
            border-left: 4px solid #f59e0b;
            padding: 0.8rem 1rem;
            border-radius: 10px;
            margin: 0.7rem 0;
            color: #92400e;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def cached_prepare_ucs(file_bytes: bytes, file_name: str):
    return prepare_ucs_dataframe_from_bytes(file_bytes, file_name)


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def cached_celestrak():
    return load_celestrak_satcat()


@st.cache_data(show_spinner=False)
def cached_vehicle_reference():
    return load_vehicle_reference()


def show_header():
    st.markdown(
        """
        <div class="hero">
            <h1>🛰️ Satellite Project Successor Tool</h1>
            <p>Batch processing, exact Data/GPT sheet columns, Google Sheets sync, CelesTrak + UCS + Wikipedia enrichment, review-ready UI.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sample_input_df():
    return pd.DataFrame(
        {
            "SATNAME": ["NUSAT-23 (ANNIE MAUNDER)", "NUSAT-26 (SOMERVILLE)", "Cartosat-2A"],
            "NORAD_ CAT_ID": ["", "", "32783"],
            "INTLDES": ["", "", "2008-021A"],
            "RA NAME": ["Naman", "Naman", "Naman"],
            "VEHICLE TYPE NAME": ["Falcon 9", "Falcon 9", "PSLV-XL"],
        }
    )


def template_gpt_df():
    return ensure_columns(pd.DataFrame(), GPT_COLUMNS)


def template_data_df():
    return ensure_columns(pd.DataFrame(), DATA_COLUMNS)


def template_numeric_df():
    return ensure_columns(pd.DataFrame(), NUMERIC_COLUMNS)


def template_evidence_df():
    return ensure_columns(pd.DataFrame(), EVIDENCE_COLUMNS)


def status_badge(text: str):
    colors = {
        "Complete": "#10b981",
        "Missing GPT row": "#ef4444",
        "Missing DATA row": "#f97316",
        "Needs GPT fill": "#f59e0b",
        "Needs DATA fill": "#f59e0b",
        "Partial / Review": "#6366f1",
    }
    color = colors.get(text, "#6b7280")
    st.markdown(
        f"<span style='display:inline-block;padding:0.25rem 0.55rem;border-radius:999px;background:{color};color:white;font-size:0.85rem;margin-right:0.35rem;'>{text}</span>",
        unsafe_allow_html=True,
    )


def session_defaults():
    defaults = {
        "input_df": pd.DataFrame(),
        "processed_data_df": None,
        "processed_gpt_df": None,
        "processed_numeric_df": None,
        "processed_evidence_df": None,
        "merged_existing_data_df": None,
        "merged_existing_gpt_df": None,
        "project_context": None,
        "project_audit_df": pd.DataFrame(),
        "project_work_queue_df": pd.DataFrame(),
        "project_generic_websites_df": pd.DataFrame(),
        "project_country_websites_df": pd.DataFrame(),
        "raw_existing_data_df": None,
        "raw_existing_gpt_df": None,
        "service_account_json_text": None,
        "google_input_sheet_names": [],
        "google_output_sheet_names": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_manual_mapping(df: pd.DataFrame, sat_col: Optional[str], norad_col: Optional[str], intldes_col: Optional[str], ra_col: Optional[str], vehicle_col: Optional[str]):
    out = df.copy()
    rename_map = {}
    if sat_col and sat_col in out.columns and sat_col != "SATNAME":
        rename_map[sat_col] = "SATNAME"
    if norad_col and norad_col in out.columns and norad_col != "NORAD_ CAT_ID":
        rename_map[norad_col] = "NORAD_ CAT_ID"
    if intldes_col and intldes_col in out.columns and intldes_col != "INTLDES":
        rename_map[intldes_col] = "INTLDES"
    if ra_col and ra_col in out.columns and ra_col != "RA NAME":
        rename_map[ra_col] = "RA NAME"
    if vehicle_col and vehicle_col in out.columns and vehicle_col != "VEHICLE TYPE NAME":
        rename_map[vehicle_col] = "VEHICLE TYPE NAME"
    return out.rename(columns=rename_map)


def load_input_from_local(uploaded_input, selected_sheet):
    if uploaded_input is None:
        return pd.DataFrame()
    return read_table_from_upload(uploaded_input, selected_sheet)


def load_input_from_google(sheet_url, worksheet_name, service_json_text):
    if not sheet_url or not worksheet_name:
        return pd.DataFrame()
    return read_worksheet_as_df(sheet_url, worksheet_name, service_json_text)


def render_sidebar():
    with st.sidebar:
        st.markdown("### Workflow")
        st.markdown(
            "1. Input select karo  \n2. UCS DB add karo  \n3. Process All  \n4. Review tables  \n5. Export / Google Sheets"
        )
        st.markdown("---")
        st.markdown("### Quick downloads")
        st.download_button(
            "Sample input CSV",
            sample_input_df().to_csv(index=False).encode("utf-8"),
            file_name="sample_satellite_input.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "Data schema CSV",
            template_data_df().to_csv(index=False).encode("utf-8"),
            file_name="data_schema_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "GPT schema CSV",
            template_gpt_df().to_csv(index=False).encode("utf-8"),
            file_name="gpt_schema_template.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("---")
        st.caption("Tip: agar exact matching chahiye toh NORAD ya INTLDES input me include karo.")


inject_css()
session_defaults()
show_header()
render_sidebar()


tab_setup, tab_audit, tab_overview, tab_data, tab_gpt, tab_numeric, tab_evidence, tab_export = st.tabs(
    [
        "1) Setup & Run",
        "2) Project Audit & Queue",
        "3) Overview",
        "4) Data Tab Output",
        "5) GPT Tab Output",
        "6) Numeric Output",
        "7) Evidence Log",
        "8) Export / Sheets",
    ]
)

with tab_setup:
    st.markdown("### Input source")
    c1, c2 = st.columns([1.25, 1])

    with c1:
        input_mode = st.radio(
            "Choose input mode",
            ["Upload local CSV/Excel", "Google Sheet", "Paste satellite names manually"],
            horizontal=True,
        )

        uploaded_input = None
        selected_input_sheet = None
        input_df = pd.DataFrame()
        manual_text = ""
        google_input_url = ""
        google_input_ws = ""

        if input_mode == "Upload local CSV/Excel":
            uploaded_input = st.file_uploader("Upload input file", type=["csv", "xls", "xlsx"], key="input_upload")
            if uploaded_input is not None:
                sheet_names = get_sheet_names(uploaded_input)
                selected_input_sheet = st.selectbox("Select worksheet", sheet_names, key="input_sheet_selector")
                input_df = load_input_from_local(uploaded_input, selected_input_sheet)

        elif input_mode == "Google Sheet":
            google_input_url = st.text_input("Google Sheet URL", key="google_input_url")
            service_json_upload = st.file_uploader("Upload Google service-account JSON", type=["json"], key="google_creds_upload")
            if service_json_upload is not None:
                try:
                    st.session_state["service_account_json_text"] = credentials_json_text_from_upload(service_json_upload)
                    st.success("Google credentials loaded.")
                except Exception as exc:
                    st.error(f"Credential error: {exc}")
            col_g1, col_g2 = st.columns([1, 1])
            with col_g1:
                if st.button("Load Google worksheet names"):
                    try:
                        names = list_worksheets(google_input_url, st.session_state.get("service_account_json_text"))
                        st.session_state["google_input_sheet_names"] = names
                        st.success("Worksheet names fetched.")
                    except Exception as exc:
                        st.error(f"Could not fetch worksheets: {exc}")
            with col_g2:
                if st.session_state.get("google_input_sheet_names"):
                    google_input_ws = st.selectbox("Choose worksheet", st.session_state["google_input_sheet_names"], key="google_input_ws_select")
                else:
                    google_input_ws = st.text_input("Worksheet name", key="google_input_ws_manual")
            if google_input_url and google_input_ws:
                try:
                    input_df = load_input_from_google(google_input_url, google_input_ws, st.session_state.get("service_account_json_text"))
                except Exception as exc:
                    st.warning(f"Input sheet अभी load nahi hua: {exc}")

        else:
            manual_text = st.text_area(
                "Paste one satellite per line",
                value="NUSAT-23 (ANNIE MAUNDER)\nNUSAT-26 (SOMERVILLE)\nCartosat-2A",
                height=180,
            )
            names = [line.strip() for line in manual_text.splitlines() if line.strip()]
            input_df = pd.DataFrame({"SATNAME": names})

        st.session_state["input_df"] = input_df

        st.markdown("### Optional primary source: UCS database")
        uploaded_ucs = st.file_uploader("Upload UCS Satellite Database", type=["csv", "xls", "xlsx"], key="ucs_upload")
        ucs_df = None
        if uploaded_ucs is not None:
            try:
                ucs_df = cached_prepare_ucs(uploaded_ucs.getvalue(), uploaded_ucs.name.lower())
                st.success(f"UCS database loaded: {len(ucs_df):,} rows")
            except Exception as exc:
                st.error(f"UCS DB load error: {exc}")

        st.markdown("### Existing project sheets (recommended for real workflow)")
        st.caption("Agar current DATA tab aur GPT DATA tab upload karoge, tool automatically detect karega kaunsi rows complete hain, kaunsi partial hain, aur kaunsi 100 rows pick karni chahiye.")
        existing_data_upload = st.file_uploader("Upload current DATA tab CSV/XLSX", type=["csv", "xls", "xlsx"], key="existing_data_upload")
        existing_gpt_upload = st.file_uploader("Upload current GPT DATA tab CSV/XLSX", type=["csv", "xls", "xlsx"], key="existing_gpt_upload")
        websites_upload = st.file_uploader("Upload Websites mapping CSV (optional)", type=["csv", "xls", "xlsx"], key="websites_upload")

        if existing_data_upload is not None and existing_gpt_upload is not None:
            try:
                raw_existing_data_df = read_table_from_upload(existing_data_upload, None)
                raw_existing_gpt_df = read_table_from_upload(existing_gpt_upload, None)
                st.session_state["raw_existing_data_df"] = raw_existing_data_df
                st.session_state["raw_existing_gpt_df"] = raw_existing_gpt_df
                context = analyze_existing_project(raw_existing_data_df, raw_existing_gpt_df)
                st.session_state["project_context"] = context
                st.session_state["project_audit_df"] = context.audit_df
                st.success(f"Project sheets loaded. Audit rows: {len(context.audit_df):,}")
            except Exception as exc:
                st.error(f"Could not analyze existing project sheets: {exc}")

        if websites_upload is not None:
            try:
                raw_websites_df = read_table_from_upload(websites_upload, None)
                generic_df, country_df = parse_websites_catalog(raw_websites_df)
                st.session_state["project_generic_websites_df"] = generic_df
                st.session_state["project_country_websites_df"] = country_df
                st.success(f"Websites catalog loaded: {len(country_df):,} country rows")
            except Exception as exc:
                st.error(f"Could not parse websites catalog: {exc}")

    with c2:
        st.markdown("### Processing options")
        use_celestrak = st.toggle("Use CelesTrak SATCAT live data", value=True)
        use_wikipedia = st.toggle("Use Wikipedia summary fallback", value=True)
        use_preferred_rag = st.toggle("Use preferred-source RAG flow (project websites first)", value=True)
        show_column_mapping = st.toggle("Advanced: manual column mapping", value=False)
        use_project_queue = st.toggle("Use work queue generated from Project Audit tab", value=False)

        sat_col = norad_col = intldes_col = ra_col = vehicle_col = None
        if not input_df.empty and show_column_mapping:
            detected_sat = get_col(input_df, "SATNAME")
            detected_norad = get_col(input_df, "NORAD_ CAT_ID")
            detected_intldes = get_col(input_df, "INTLDES")
            detected_ra = get_col(input_df, "RA NAME") or get_col(input_df, "RA Name")
            detected_vehicle = get_col(input_df, "VEHICLE TYPE NAME")
            options = [None] + list(input_df.columns)
            sat_col = st.selectbox("Map satellite name column", options, index=options.index(detected_sat) if detected_sat in options else 0)
            norad_col = st.selectbox("Map NORAD column", options, index=options.index(detected_norad) if detected_norad in options else 0)
            intldes_col = st.selectbox("Map INTLDES column", options, index=options.index(detected_intldes) if detected_intldes in options else 0)
            ra_col = st.selectbox("Map RA column", options, index=options.index(detected_ra) if detected_ra in options else 0)
            vehicle_col = st.selectbox("Map vehicle column", options, index=options.index(detected_vehicle) if detected_vehicle in options else 0)

        st.markdown("### What this version improves")
        st.markdown(
            """
            - exact **Data tab** and **GPT tab** columns  
            - **Google Sheets read + write**  
            - **batch processing**  
            - **manual review tables** instead of raw JSON  
            - **official-source enrichment** using UCS + CelesTrak + Wikipedia fallback  
            - **vehicle reference layer** for max LEO mass / reuse / cost  
            """
        )

        process_clicked = st.button("🚀 Process All Satellites", use_container_width=True, type="primary")

    if not st.session_state["input_df"].empty:
        preview_df = st.session_state["input_df"].copy()
        if show_column_mapping:
            preview_df = apply_manual_mapping(preview_df, sat_col, norad_col, intldes_col, ra_col, vehicle_col)
        st.markdown("### Input preview")
        st.caption("Input file me kam columns hona bilkul okay hai. Minimum me SATNAME helpful hai; best matching ke liye NORAD_ CAT_ID, INTLDES, RA NAME, aur VEHICLE TYPE NAME dena aur bhi better hai. Full output columns process ke baad Data/GPT tabs me auto-generate honge.")
        st.dataframe(preview_df.head(50), use_container_width=True, height=280)
    else:
        st.info("Abhi input load nahi hua hai.")

    if process_clicked:
        input_df = st.session_state["input_df"].copy()
        if use_project_queue and not st.session_state.get("project_work_queue_df", pd.DataFrame()).empty:
            project_context = st.session_state.get("project_context")
            if isinstance(project_context, ProjectContext) and project_context.data_df is not None and project_context.gpt_df is not None:
                input_df = build_processing_input_from_audit_selection(
                    st.session_state["project_work_queue_df"],
                    project_context.data_df,
                    project_context.gpt_df,
                )
                st.info(f"Using project work queue as processing input: {len(input_df)} rows")

        if input_df.empty:
            st.warning("Pehle input do — file upload karo, Google Sheet connect karo, names paste karo, ya Project Audit tab se work queue generate karo.")
        else:
            if show_column_mapping and not use_project_queue:
                input_df = apply_manual_mapping(input_df, sat_col, norad_col, intldes_col, ra_col, vehicle_col)
            satcat_df = None
            if use_celestrak:
                with st.spinner("Loading CelesTrak SATCAT..."):
                    try:
                        satcat_df = cached_celestrak()
                        st.success(f"CelesTrak SATCAT loaded: {len(satcat_df):,} rows")
                    except Exception as exc:
                        satcat_df = None
                        st.warning(
                            "CelesTrak SATCAT load nahi ho paaya, isliye app ab without CelesTrak continue karega. "
                            f"Error: {exc}. Agar chaho toh 'Use CelesTrak SATCAT live data' toggle off karke bhi run kar sakte ho."
                        )
            vehicle_df = cached_vehicle_reference()
            progress = st.progress(0, text="Preparing pipeline...")
            status = st.empty()

            def callback(done, total, satname):
                progress.progress(done / total, text=f"Processed {done}/{total}")
                status.info(f"Running row {done}/{total}: {satname}")

            with st.spinner("Processing all rows..."):
                data_df, gpt_df, numeric_df, evidence_df = process_dataframe(
                    input_df=input_df,
                    ucs_df=ucs_df,
                    satcat_df=satcat_df,
                    vehicle_df=vehicle_df,
                    use_wikipedia=use_wikipedia,
                    use_preferred_rag=use_preferred_rag,
                    preferred_country_websites_df=st.session_state.get("project_country_websites_df"),
                    preferred_generic_websites_df=st.session_state.get("project_generic_websites_df"),
                    progress_callback=callback,
                )
            st.session_state["processed_data_df"] = data_df
            st.session_state["processed_gpt_df"] = gpt_df
            st.session_state["processed_numeric_df"] = numeric_df
            st.session_state["processed_evidence_df"] = evidence_df

            project_context = st.session_state.get("project_context")
            if isinstance(project_context, ProjectContext) and project_context.data_df is not None and project_context.gpt_df is not None:
                merged_data_df, merged_gpt_df = merge_generated_into_existing(
                    project_context.data_df,
                    project_context.gpt_df,
                    data_df,
                    gpt_df,
                )
                st.session_state["merged_existing_data_df"] = merged_data_df
                st.session_state["merged_existing_gpt_df"] = merged_gpt_df

            status.success("Processing complete.")
            st.markdown('<div class="success-box">Done — Data, GPT, Numeric, and Evidence tables generate ho gaye.</div>', unsafe_allow_html=True)

with tab_audit:
    st.markdown("### Existing project audit")
    audit_df = st.session_state.get("project_audit_df", pd.DataFrame())
    project_context = st.session_state.get("project_context")
    country_websites_df = st.session_state.get("project_country_websites_df", pd.DataFrame())

    if audit_df is None or audit_df.empty:
        st.info("Current DATA tab aur GPT DATA tab upload karoge toh yahan automatic audit, missing-row detection, aur 100-satellite work queue dikhega.")
    else:
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Audit rows", len(audit_df))
        a2.metric("Complete", int((audit_df["STATUS"] == "Complete").sum()))
        a3.metric("Needs GPT fill", int((audit_df["STATUS"] == "Needs GPT fill").sum() + (audit_df["STATUS"] == "Missing GPT row").sum()))
        a4.metric("Unassigned", int((audit_df["OWNER_STATE"] == "Unassigned").sum()))

        cfa, cfb, cfc, cfd = st.columns([1.3, 1.1, 1, 1])
        with cfa:
            selected_statuses = st.multiselect(
                "Filter by status",
                options=sorted(audit_df["STATUS"].dropna().unique().tolist()),
                default=[s for s in ["Missing GPT row", "Needs GPT fill", "Partial / Review", "Missing DATA row", "Needs DATA fill"] if s in audit_df["STATUS"].unique().tolist()],
            )
        with cfb:
            countries = ["All"] + sorted([c for c in audit_df["COUNTRY"].dropna().astype(str).unique().tolist() if c])
            selected_country = st.selectbox("Country filter", countries)
        with cfc:
            only_unassigned = st.checkbox("Only unassigned rows", value=False)
        with cfd:
            queue_size = st.number_input("Queue size", min_value=1, max_value=500, value=100, step=1)

        filtered_queue = filter_work_queue(
            audit_df=audit_df,
            statuses=selected_statuses,
            country=selected_country,
            only_unassigned=only_unassigned,
            max_rows=int(queue_size),
        )
        st.session_state["project_work_queue_df"] = filtered_queue

        st.markdown("#### Suggested work queue")
        st.caption("Ye queue incomplete / missing rows ko priority score ke saath pick karti hai. Isse directly processing input banaya ja sakta hai.")
        st.dataframe(filtered_queue, use_container_width=True, height=380)

        q1, q2 = st.columns([1, 1])
        with q1:
            st.download_button(
                "Download work queue CSV",
                filtered_queue.to_csv(index=False).encode("utf-8"),
                file_name="project_work_queue.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with q2:
            if not filtered_queue.empty:
                st.success(f"Queue ready: {len(filtered_queue)} rows. Setup tab me 'Use work queue generated from Project Audit tab' ON karke process kar sakte ho.")

        st.markdown("#### Audit table")
        st.dataframe(audit_df, use_container_width=True, height=420)

        if not filtered_queue.empty and not country_websites_df.empty:
            first_country = safe_str(filtered_queue.iloc[0].get("COUNTRY", ""))
            urls = websites_for_country(country_websites_df, first_country)
            if urls:
                st.markdown(f"#### Country-source suggestions for `{first_country}`")
                for u in urls[:12]:
                    st.markdown(f"- {u}")

with tab_overview:
    data_df = st.session_state.get("processed_data_df")
    gpt_df = st.session_state.get("processed_gpt_df")
    evidence_df = st.session_state.get("processed_evidence_df")
    input_df = st.session_state.get("input_df")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input rows", 0 if input_df is None else len(input_df))
    c2.metric("Processed rows", 0 if data_df is None else len(data_df))
    c3.metric("Review needed", 0 if gpt_df is None or gpt_df.empty else int((gpt_df["REVIEW STATUS"] == "Needs manual review").sum()))
    avg_conf = 0 if gpt_df is None or gpt_df.empty else round(pd.to_numeric(gpt_df["CONFIDENCE"], errors="coerce").fillna(0).mean(), 2)
    c4.metric("Avg confidence", avg_conf)

    if gpt_df is None or gpt_df.empty:
        st.info("Abhi tak batch run nahi hua hai.")
    else:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Review status distribution")
            status_counts = gpt_df["REVIEW STATUS"].value_counts()
            st.bar_chart(status_counts)
        with right:
            st.markdown("#### Purpose distribution")
            purpose_counts = gpt_df["PURPOSE"].replace("", "Unknown").value_counts()
            st.bar_chart(purpose_counts)

        with st.expander("Top notes / next action"):
            st.markdown(
                """
                - **High confidence** rows can usually be exported directly.
                - **Medium confidence** rows should be spot-checked.
                - **Needs manual review** rows should be reviewed against official source links.
                - For best results, keep **NORAD** and **INTLDES** in input rows whenever possible.
                """
            )

with tab_data:
    st.markdown("### Exact Data tab output")
    if st.session_state.get("processed_data_df") is None:
        st.info("Abhi process run nahi hua hai. Neeche full Data-tab schema preview dikha raha hoon.")
        st.dataframe(template_data_df(), use_container_width=True, height=240)
    else:
        data_view_mode = "Generated rows only"
        if st.session_state.get("merged_existing_data_df") is not None:
            data_view_mode = st.radio("Data view", ["Generated rows only", "Merged into existing DATA sheet"], horizontal=True, key="data_view_mode")
        active_data_df = st.session_state["processed_data_df"] if data_view_mode == "Generated rows only" else st.session_state["merged_existing_data_df"]
        edited = st.data_editor(
            active_data_df,
            use_container_width=True,
            height=560,
            num_rows="dynamic",
            key="data_editor",
        )
        if data_view_mode == "Generated rows only":
            st.session_state["processed_data_df"] = ensure_columns(edited, DATA_COLUMNS)
        else:
            st.session_state["merged_existing_data_df"] = ensure_columns(edited, DATA_COLUMNS)

with tab_gpt:
    st.markdown("### Exact GPT tab output")
    if st.session_state.get("processed_gpt_df") is None:
        st.info("Abhi process run nahi hua hai. Neeche full GPT-tab schema preview dikha raha hoon.")
        st.dataframe(template_gpt_df(), use_container_width=True, height=240)
    else:
        gpt_view_mode = "Generated rows only"
        if st.session_state.get("merged_existing_gpt_df") is not None:
            gpt_view_mode = st.radio("GPT view", ["Generated rows only", "Merged into existing GPT sheet"], horizontal=True, key="gpt_view_mode")
        active_gpt_df = st.session_state["processed_gpt_df"] if gpt_view_mode == "Generated rows only" else st.session_state["merged_existing_gpt_df"]
        edited = st.data_editor(
            active_gpt_df,
            use_container_width=True,
            height=560,
            num_rows="dynamic",
            key="gpt_editor",
        )
        if gpt_view_mode == "Generated rows only":
            st.session_state["processed_gpt_df"] = ensure_columns(edited, GPT_COLUMNS)
            flagged = edited[edited["REVIEW STATUS"] == "Needs manual review"]
        else:
            st.session_state["merged_existing_gpt_df"] = edited
            flagged = edited[edited["REVIEW STATUS"] == "Needs manual review"] if "REVIEW STATUS" in edited.columns else pd.DataFrame()
        with st.expander("Rows needing manual review"):
            if flagged.empty:
                st.success("Great — फिलहाल koi row forced manual review me nahi hai.")
            else:
                st.dataframe(flagged, use_container_width=True, height=250)

with tab_numeric:
    st.markdown("### Numeric innovation scores")
    if st.session_state.get("processed_numeric_df") is None:
        st.info("Abhi process run nahi hua hai. Neeche numeric schema preview dikha raha hoon.")
        st.dataframe(template_numeric_df(), use_container_width=True, height=200)
    else:
        edited = st.data_editor(
            st.session_state["processed_numeric_df"],
            use_container_width=True,
            height=560,
            num_rows="dynamic",
            key="numeric_editor",
        )
        st.session_state["processed_numeric_df"] = ensure_columns(edited, NUMERIC_COLUMNS)

with tab_evidence:
    st.markdown("### Evidence log")
    if st.session_state.get("processed_evidence_df") is None:
        st.info("Abhi process run nahi hua hai. Neeche evidence-log schema preview dikha raha hoon.")
        st.dataframe(template_evidence_df(), use_container_width=True, height=180)
    else:
        st.dataframe(st.session_state["processed_evidence_df"], use_container_width=True, height=560)
        st.markdown('<div class="warn-box">Evidence log is useful for inter-rater review and source auditing.</div>', unsafe_allow_html=True)

with tab_export:
    st.markdown("### Download exports")
    data_df = st.session_state.get("processed_data_df")
    gpt_df = st.session_state.get("processed_gpt_df")
    numeric_df = st.session_state.get("processed_numeric_df")
    evidence_df = st.session_state.get("processed_evidence_df")
    merged_data_df = st.session_state.get("merged_existing_data_df")
    merged_gpt_df = st.session_state.get("merged_existing_gpt_df")
    project_context = st.session_state.get("project_context")

    if data_df is None or gpt_df is None:
        st.info("Pehle processing run karo, phir export available hoga.")
    else:
        export_mode = "Generated rows only"
        if merged_data_df is not None and merged_gpt_df is not None:
            export_mode = st.radio(
                "Export mode",
                ["Generated rows only", "Merged into existing project sheets"],
                horizontal=True,
            )

        active_data_df = data_df if export_mode == "Generated rows only" else merged_data_df
        active_gpt_df = gpt_df if export_mode == "Generated rows only" else merged_gpt_df
        raw_data_upload_df = None
        raw_gpt_upload_df = None
        if export_mode == "Merged into existing project sheets" and isinstance(project_context, ProjectContext):
            raw_data_upload_df = decanonicalize_data_for_export(active_data_df, project_context.raw_data_df)
            raw_gpt_upload_df = decanonicalize_gpt_for_export(active_gpt_df, project_context.raw_gpt_df)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "Download Data tab CSV",
                active_data_df.to_csv(index=False).encode("utf-8"),
                file_name="data_tab_output.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                "Download GPT tab CSV",
                active_gpt_df.to_csv(index=False).encode("utf-8"),
                file_name="gpt_tab_output.csv",
                mime="text/csv",
                use_container_width=True,
            )

            if raw_data_upload_df is not None and raw_gpt_upload_df is not None:
                st.download_button(
                    "Download merged DATA sheet in original format",
                    raw_data_upload_df.to_csv(index=False).encode("utf-8"),
                    file_name="merged_existing_DATA_sheet.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                st.download_button(
                    "Download merged GPT sheet in original format",
                    raw_gpt_upload_df.to_csv(index=False).encode("utf-8"),
                    file_name="merged_existing_GPT_sheet.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        with c2:
            if numeric_df is not None:
                st.download_button(
                    "Download Numeric CSV",
                    numeric_df.to_csv(index=False).encode("utf-8"),
                    file_name="numeric_output.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            if evidence_df is not None:
                st.download_button(
                    "Download Evidence CSV",
                    evidence_df.to_csv(index=False).encode("utf-8"),
                    file_name="evidence_log.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            if not st.session_state.get("project_work_queue_df", pd.DataFrame()).empty:
                st.download_button(
                    "Download current work queue CSV",
                    st.session_state["project_work_queue_df"].to_csv(index=False).encode("utf-8"),
                    file_name="project_work_queue.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        with c3:
            if excel_export_available():
                workbook_sheets = {
                    "Data_Tab": active_data_df,
                    "GPT_Tab": active_gpt_df,
                    "Numeric_Tab": numeric_df if numeric_df is not None else pd.DataFrame(),
                    "Evidence_Log": evidence_df if evidence_df is not None else pd.DataFrame(),
                }
                if not st.session_state.get("project_work_queue_df", pd.DataFrame()).empty:
                    workbook_sheets["Work_Queue"] = st.session_state["project_work_queue_df"]
                if not st.session_state.get("project_audit_df", pd.DataFrame()).empty:
                    workbook_sheets["Project_Audit"] = st.session_state["project_audit_df"]
                workbook_bytes = dataframe_to_excel_bytes(workbook_sheets)
                st.download_button(
                    "Download full Excel workbook",
                    workbook_bytes,
                    file_name="satellite_project_successor_output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.warning("Excel export abhi unavailable hai kyunki `openpyxl` installed nahi hai.")
                st.code("pip install openpyxl")
                st.caption("CSV downloads phir bhi kaam karenge. Agar sab dependencies ek saath install karni hain toh: `pip install -r requirements.txt`")

        st.markdown("### Direct Google Sheets output")
        st.caption("Use uploaded service-account JSON from Setup tab, or set GOOGLE_SERVICE_ACCOUNT_JSON in deployment secrets.")
        out_url = st.text_input("Output Google Sheet URL")
        mode = st.radio("Write mode", ["overwrite", "append"], horizontal=True)
        col_o1, col_o2, col_o3, col_o4 = st.columns(4)
        with col_o1:
            data_ws = st.text_input("Data worksheet", value="DATA")
        with col_o2:
            gpt_ws = st.text_input("GPT worksheet", value="GPT DATA")
        with col_o3:
            numeric_ws = st.text_input("Numeric worksheet", value="Numeric_Tab")
        with col_o4:
            evidence_ws = st.text_input("Evidence worksheet", value="Evidence_Log")

        if st.button("Upload all outputs to Google Sheets", type="primary"):
            try:
                data_sheet_to_upload = raw_data_upload_df if raw_data_upload_df is not None else active_data_df
                gpt_sheet_to_upload = raw_gpt_upload_df if raw_gpt_upload_df is not None else active_gpt_df
                write_df_to_worksheet(out_url, data_ws, data_sheet_to_upload, mode=mode, service_account_json_text=st.session_state.get("service_account_json_text"))
                write_df_to_worksheet(out_url, gpt_ws, gpt_sheet_to_upload, mode=mode, service_account_json_text=st.session_state.get("service_account_json_text"))
                if numeric_df is not None:
                    write_df_to_worksheet(out_url, numeric_ws, numeric_df, mode=mode, service_account_json_text=st.session_state.get("service_account_json_text"))
                if evidence_df is not None:
                    write_df_to_worksheet(out_url, evidence_ws, evidence_df, mode=mode, service_account_json_text=st.session_state.get("service_account_json_text"))
                st.success("All tables uploaded to Google Sheets successfully.")
            except Exception as exc:
                st.error(f"Upload failed: {exc}")

st.divider()
st.markdown(
    "<span class='small-note'>Note: ye version strong MVP + workflow successor hai. Final research submission se pehle low-confidence rows aur cost-related rows ko manual official-source verification dena best rahega.</span>",
    unsafe_allow_html=True,
)
