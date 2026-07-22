import re
from typing import Dict, Tuple

from .constants import UCS_DB_LINK
from .helpers import multi_join, parse_date, safe_str, to_float


def infer_user_category(operator: str, users: str, comments: str, purpose: str) -> Tuple[str, str, str, float]:
    blob = " ".join([operator, users, comments, purpose]).lower()
    organizations = multi_join([operator, users])

    military_keywords = [
        "military", "defense", "defence", "air force", "navy", "army", "intelligence", "reconnaissance",
        "space force", "strategic communications", "defence ministry", "armed forces", "surveillance"
    ]
    commercial_keywords = [
        "commercial", "company", "corp", "corporation", "ltd", "llc", "inc", "telecom", "broadband",
        "satellite services", "operator", "broadcast", "planet", "maxar", "eutelsat", "ses", "intelsat",
        "orbcomm", "spacex", "satellogic", "optus", "skykraft", "aerospacelab", "hispasat", "star one"
    ]
    civil_keywords = [
        "university", "research", "academic", "scientific", "civil", "student", "institute", "non-profit",
        "observatory", "meteorological institute", "laboratory"
    ]
    government_keywords = [
        "government", "ministry", "agency", "space agency", "nasa", "esa", "isro", "jaxa", "cnes", "dlr",
        "roscosmos", "cnsa", "noaa", "eumetsat", "public", "state", "department", "telebras", "arsu",
        "national institute", "commission", "telebrás", "conae", "inpe", "airservices australia"
    ]

    extracted_phrase = ""
    for pattern in [
        r"operated by ([^.]+)",
        r"owned by ([^.]+)",
        r"developed by ([^.]+)",
        r"built by ([^.]+)",
        r"managed by ([^.]+)",
    ]:
        m = re.search(pattern, blob)
        if m:
            extracted_phrase = m.group(1).strip(" ,.;")
            break

    has_military = any(k in blob for k in military_keywords)
    has_civil = any(k in blob for k in civil_keywords)
    has_commercial = any(k in blob for k in commercial_keywords)
    has_government = any(k in blob for k in government_keywords)

    if has_military and (has_government or has_commercial):
        desc = organizations or extracted_phrase or "Multiple user types appear to be involved, including military participation."
        return "Mix", "5", desc, 0.9
    if has_commercial and has_government:
        desc = organizations or extracted_phrase or "Commercial and government actors appear to share usage or control."
        return "Mix", "5", desc, 0.86
    if has_government and has_civil:
        desc = organizations or extracted_phrase or "Government and research / civil institutions appear to be involved together."
        return "Mix", "5", desc, 0.8
    if has_military:
        return "Military", "1", organizations or extracted_phrase or "Likely operated or used by military / defense actors.", 0.93
    if has_commercial:
        return "Commercial", "3", organizations or extracted_phrase or "Likely operated by a commercial satellite or telecom actor.", 0.9
    if has_government:
        return "Government", "4", organizations or extracted_phrase or "Likely operated by a government or public agency.", 0.87
    if has_civil:
        return "Civil", "2", organizations or extracted_phrase or "Likely operated for civil, academic, or research purposes.", 0.8
    if organizations:
        return "Government", "4", organizations, 0.55
    return "", "", "Insufficient evidence from current sources.", 0.25


def infer_purpose_category(purpose: str, detailed_purpose: str, comments: str, satname: str, wiki_summary: str = "") -> Tuple[str, str, str, float]:
    blob = " ".join([purpose, detailed_purpose, comments, satname, wiki_summary]).lower()

    navigation_keywords = ["navigation", "gnss", "positioning", "timing", "gps", "galileo", "beidou", "navstar"]
    communication_keywords = [
        "communication", "telecom", "broadband", "internet", "broadcast", "tv", "television", "telephony",
        "backhaul", "transponder", "ku-band", "c-band", "ka-band", "vhf", "ads-b", "satcom"
    ]
    eo_keywords = [
        "earth observation", "remote sensing", "weather", "meteorology", "imaging", "optical", "radar", "sar",
        "multispectral", "hyperspectral", "land surface", "vegetation", "mapping", "disaster monitoring",
        "monitoring", "environment", "deforestation", "agriculture", "climate"
    ]
    science_keywords = [
        "space science", "astronomy", "astrophysics", "planetary", "science mission", "heliophysics",
        "ionosphere", "aurora", "radiation budget", "atmosphere", "magnetosphere", "solar", "physics"
    ]
    tech_keywords = [
        "technology", "experimental", "demonstration", "demo", "test", "prototype", "cubesat", "nanosat",
        "in-orbit validation", "iod", "hosted payload", "shared satellite", "platform validation"
    ]

    if any(k in blob for k in navigation_keywords):
        return "Navigation", "3", "Used for navigation, positioning, and timing services.", 0.93
    if any(k in blob for k in eo_keywords):
        return "Earth Observation", "2", "Used for Earth imaging, remote sensing, weather, or environmental monitoring.", 0.93
    if any(k in blob for k in science_keywords) and not any(k in blob for k in communication_keywords):
        return "Space Science", "4", "Used for scientific exploration, atmospheric study, or space science research.", 0.9
    if any(k in blob for k in communication_keywords):
        return "Communications", "1", "Used to provide communications, connectivity, broadcast, or satcom services.", 0.91
    if any(k in blob for k in tech_keywords):
        return "Technology Development", "5", "Used for technology demonstration, platform validation, or experimental missions.", 0.88
    if safe_str(purpose):
        purpose_clean = safe_str(purpose)
        normalized = purpose_clean.lower()
        if "communication" in normalized:
            return "Communications", "1", purpose_clean, 0.7
        if "earth" in normalized or "observation" in normalized:
            return "Earth Observation", "2", purpose_clean, 0.7
        if "science" in normalized:
            return "Space Science", "4", purpose_clean, 0.7
        if "technology" in normalized or "experimental" in normalized:
            return "Technology Development", "5", purpose_clean, 0.7
        if "navigation" in normalized:
            return "Navigation", "3", purpose_clean, 0.7
        return purpose_clean, "", purpose_clean, 0.5
    return "", "", "Insufficient evidence from current sources.", 0.25


def map_purpose_to_data_type(purpose_label: str) -> str:
    mapping = {
        "Communications": "Communication",
        "Earth Observation": "Earth Observation",
        "Technology Development": "Experimental",
        "Navigation": "Navigation",
        "Space Science": "Science & Exploration",
    }
    return mapping.get(purpose_label, "")


def infer_sdg(purpose_label: str, purpose_text: str, comments: str, users: str) -> Tuple[str, str, str, float]:
    blob = " ".join([purpose_label, purpose_text, comments, users]).lower()
    if any(k in blob for k in ["climate", "weather", "environment", "forest", "water", "agriculture", "disaster", "mapping", "earth observation", "remote sensing"]):
        return "Environmental", "13, 15", "Supports environmental monitoring and climate-related decision-making through Earth observation, resource monitoring, or disaster response.", 0.88
    if any(k in blob for k in ["internet", "connectivity", "telecom", "broadband", "navigation", "infrastructure"]):
        return "Innovation", "9", "Supports infrastructure and innovation by improving communications, connectivity, or navigation capability.", 0.84
    if any(k in blob for k in ["education", "health", "partnership", "civil", "community"]):
        return "Social", "4, 17", "Supports social development through knowledge access, services, or partnerships.", 0.75
    if any(k in blob for k in ["commerce", "economic", "industry", "jobs", "market"]):
        return "Economic", "8", "Supports economic activity through commercial space services or productivity gains.", 0.72
    if purpose_label == "Earth Observation":
        return "Environmental", "13, 15", "Earth observation data commonly supports climate action, land monitoring, and environmental management.", 0.78
    if purpose_label in {"Communications", "Navigation", "Technology Development", "Space Science"}:
        return "Innovation", "9", "The mission primarily contributes to innovation and infrastructure development.", 0.7
    return "", "", "Insufficient evidence from current sources.", 0.2


def infer_frugal(launch_mass, launch_cost_musd, purpose_text: str, comments: str, satname: str, country: str) -> Dict[str, str]:
    blob = " ".join([purpose_text, comments, satname, country]).lower()
    reasons = []
    negative_reasons = []
    score = 0

    if launch_mass is not None:
        if launch_mass <= 50:
            score += 2
            reasons.append(f"Very small satellite mass (~{launch_mass:g} kg) suggests strong cost-conscious design.")
        elif launch_mass <= 300:
            score += 2
            reasons.append(f"Small satellite mass (~{launch_mass:g} kg) suggests lower development and launch burden.")
        elif launch_mass <= 500:
            score += 1
            reasons.append(f"Medium-small satellite mass (~{launch_mass:g} kg) may support some cost efficiency.")
        elif launch_mass >= 3000:
            negative_reasons.append("Large spacecraft mass suggests a more capital-intensive mission profile.")

    signal_map = {
        "cubesat": (2, "CubeSat architecture is a strong frugal design signal."),
        "nanosat": (2, "Nanosatellite architecture is a strong frugal design signal."),
        "smallsat": (1, "Smallsat framing suggests cost-efficient architecture."),
        "rideshare": (2, "Rideshare launch usually reduces launch cost per mission."),
        "hosted payload": (2, "Hosted payload model can lower mission cost by sharing infrastructure."),
        "constellation": (1, "Constellation standardization can reduce unit cost through repetition."),
        "university": (1, "University participation can lower labour or overhead costs."),
        "student": (1, "Student-led or academic participation can reduce labour cost intensity."),
        "technology demonstration": (1, "Technology demonstration missions often use compact, lower-cost designs."),
        "low-cost": (2, "Source text explicitly mentions low-cost design or operations."),
        "low cost": (2, "Source text explicitly mentions low-cost design or operations."),
        "miniaturized": (1, "Miniaturization is consistent with frugal engineering."),
        "modular": (1, "Modular architecture supports development efficiency and reuse."),
        "cots": (2, "Use of commercial off-the-shelf components is a classic frugal signal."),
        "open-source": (1, "Open-source or open-platform design can reduce development costs."),
        "shared satellite": (2, "Shared satellite/service model spreads mission cost across users."),
        "in-house": (1, "In-house design/manufacturing may reduce coordination and procurement costs."),
        "all-electric propulsion": (1, "All-electric propulsion can reduce launch mass and improve cost efficiency."),
    }

    for key, (pts, reason) in signal_map.items():
        if key in blob:
            score += pts
            reasons.append(reason)

    cost_per_kg = None
    if launch_mass and launch_cost_musd:
        cost_per_kg = (launch_cost_musd * 1_000_000) / launch_mass
        if cost_per_kg < 10000:
            score += 3
            reasons.append(f"Estimated launch cost per kg is below $10,000/kg (~${cost_per_kg:,.0f}/kg).")
        elif cost_per_kg < 20000:
            score += 1
            reasons.append(f"Estimated launch cost per kg is relatively competitive (~${cost_per_kg:,.0f}/kg).")
        else:
            negative_reasons.append(f"Estimated launch cost per kg appears high (~${cost_per_kg:,.0f}/kg).")

    if any(k in blob for k in ["custom bus", "bespoke", "large geostationary", "high throughput geostationary"]):
        negative_reasons.append("The mission appears to rely on a large bespoke / geostationary architecture rather than a frugal one.")

    frugal = "Yes" if score >= 3 else "No"
    dev_eff = 1 if any(k in blob for k in ["modular", "cubesat", "nanosat", "mass production", "miniaturized", "prototype", "demo", "cots", "in-house", "shared satellite"]) or (launch_mass is not None and launch_mass <= 300) else 0
    ops_eff = 1 if any(k in blob for k in ["rideshare", "hosted payload", "commercial service", "constellation", "all-electric propulsion", "shared satellite"]) else 0
    labour_eff = 1 if any(k in blob for k in ["university", "student", "academic", "consortium", "in-house", "lean team"]) else 0
    frugal_design = 1 if frugal == "Yes" else 0

    roi_desc = "No reliable public ROI / revenue figure was found automatically; manual research may be required."
    if any(k in blob for k in ["commercial", "telecom", "broadband", "broadcast", "constellation", "iot"]):
        roi_desc = "The mission likely creates economic value through commercial services, but exact ROI figures still need manual source verification."

    if frugal == "Yes":
        frugal_desc = multi_join(reasons)
    else:
        frugal_desc = multi_join(negative_reasons) or "No strong public evidence of frugal design was detected automatically."

    return {
        "FRUGAL (YES/ NO)": frugal,
        "Development Cost Efficiency (0/1)": str(dev_eff),
        "Development Cost Efficiency Description": reasons[0] if dev_eff and reasons else "No strong automated evidence of development cost efficiency.",
        "Dev cost efficiency source": UCS_DB_LINK,
        "Operational Cost Efficiency (0/1)": str(ops_eff),
        "Operational Cost Efficiency Description": "Operational setup suggests some efficiency (e.g., rideshare/constellation/shared operations)." if ops_eff else "No strong automated evidence of operational cost efficiency.",
        "ops cost efficiency source": UCS_DB_LINK,
        "Labour Cost Efficiency (0/1)": str(labour_eff),
        "Labour Cost Efficiency Description": "Academic, consortium, or lean in-house participation may have lowered labour costs." if labour_eff else "No strong automated evidence of labour cost efficiency.",
        "Labour cost efficiency source": UCS_DB_LINK,
        "Frugal Innovation Design (0/1)": str(frugal_design),
        "Frugal Innovation Design Description": frugal_desc,
        "frugal innovation design source": UCS_DB_LINK,
        "Return on Investment Data of Revenue from Satellite Launch ($ million)": "",
        "Return on Investment Description": roi_desc,
        "Source": UCS_DB_LINK,
    }


def infer_tip(purpose_label: str, purpose_text: str, comments: str) -> Tuple[str, str]:
    blob = " ".join([purpose_label, purpose_text, comments]).lower()
    ids = []
    explanations = []
    if any(k in blob for k in ["climate", "disaster", "sustainability", "environment", "weather"]):
        ids.append("1")
        explanations.append("Targets a societal or environmental challenge.")
    if any(k in blob for k in ["constellation", "infrastructure", "ecosystem", "system"]):
        ids.append("2")
        explanations.append("Contributes to a broader socio-technical system.")
    if any(k in blob for k in ["partnership", "consortium", "international", "agency", "commercial service"]):
        ids.append("3")
        explanations.append("Suggests multi-actor involvement.")
    if any(k in blob for k in ["technology", "demo", "experimental", "prototype"]):
        ids.append("4")
        explanations.append("Supports experimentation and learning.")
    if purpose_label in {"Earth Observation", "Communications", "Navigation"}:
        ids.append("6")
        explanations.append("Has mission-oriented public or infrastructure value.")
    return ", ".join(sorted(set(ids))), " ".join(explanations) if explanations else "No strong TIP signal detected automatically."


def infer_nis(purpose_label: str, purpose_text: str, comments: str, users: str) -> Tuple[str, str]:
    blob = " ".join([purpose_label, purpose_text, comments, users]).lower()
    ids = []
    explanations = []
    if any(k in blob for k in ["science", "research", "earth observation", "data", "weather", "monitoring"]):
        ids.append("1")
        explanations.append("Supports R&D and knowledge generation through data and observation.")
    if any(k in blob for k in ["commercial", "industry", "broadband", "telecom", "market"]):
        ids.append("2")
        explanations.append("Supports business and industry innovation.")
    if any(k in blob for k in ["education", "university", "student", "academic"]):
        ids.append("4")
        explanations.append("Supports education and skill development.")
    if any(k in blob for k in ["partnership", "consortium", "technology transfer", "international"]):
        ids.append("5")
        explanations.append("Enables knowledge and technology transfer.")
    if purpose_label in {"Communications", "Navigation"}:
        ids.append("6")
        explanations.append("Acts as enabling infrastructure for innovation systems.")
    return ", ".join(sorted(set(ids))), " ".join(explanations) if explanations else "No strong NIS signal detected automatically."


def determine_review_status(confidence: float, user_value: str, purpose_value: str, sdg_value: str) -> str:
    if not user_value or not purpose_value or not sdg_value:
        return "Needs manual review"
    if confidence >= 0.85:
        return "High confidence"
    if confidence >= 0.65:
        return "Medium confidence"
    return "Needs manual review"


def parse_resolution_meters(text: str):
    text = safe_str(text).lower()
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(m|meter|meters)\b", text)
    if match:
        return float(match.group(1))
    return None


def score_payload_innovation(text: str) -> Tuple[int, str]:
    blob = text.lower()
    if any(k in blob for k in ["ai", "autonomous", "reconfigurable", "multi-payload", "modular payload"]):
        return 5, "Payload text suggests highly adaptive, autonomous, or multi-role payload innovation."
    if any(k in blob for k in ["modular", "integrated", "dual-purpose", "miniaturized", "multi-sensor"]):
        return 4, "Payload text suggests modular, integrated, or miniaturized innovation beyond basic systems."
    if any(k in blob for k in ["experimental", "demonstration", "prototype", "technology"]):
        return 3, "Payload indicates moderate innovation through testing or technology demonstration."
    if any(k in blob for k in ["camera", "imager", "transponder", "sensor"]):
        return 2, "Payload appears functional but not strongly differentiated by available text."
    return 1, "No clear payload innovation evidence was found automatically."


def score_spectral_innovation(text: str) -> Tuple[int, str]:
    blob = text.lower()
    if "hyperspectral" in blob:
        return 5, "Hyperspectral capability suggests very advanced spectral innovation."
    if any(k in blob for k in ["multispectral", "thermal infrared", "swir", "nir", "atmospheric correction"]):
        return 4, "Multispectral or extended spectral coverage indicates significant spectral innovation."
    band_count = len(re.findall(r"band", blob))
    if band_count >= 4:
        return 3, "Multiple bands are mentioned, suggesting moderate multispectral capability."
    if any(k in blob for k in ["optical", "panchromatic", "single band"]):
        return 2, "Basic optical or limited-band imaging suggests low-to-moderate spectral innovation."
    return 1, "No spectral-band information was found automatically."


def score_sensor_innovation(text: str) -> Tuple[int, str]:
    blob = text.lower()
    if any(k in blob for k in ["ai", "adaptive", "quantum", "self-calibrating", "onboard processing"]):
        return 5, "Sensor text suggests advanced autonomous or next-generation sensing capability."
    if any(k in blob for k in ["synthetic aperture radar", "sar", "miniaturized", "radiation hardened", "high sensitivity"]):
        return 4, "Sensor text suggests significant engineering improvement or advanced sensing technology."
    if any(k in blob for k in ["multispectral", "imager", "uv", "infrared", "linear transponder"]):
        return 3, "Sensor payload suggests moderate technical advancement over very basic systems."
    if any(k in blob for k in ["camera", "sensor", "transponder"]):
        return 2, "Sensor text indicates standard sensing hardware with limited innovation detail."
    return 1, "No sensor innovation evidence was found automatically."


def score_spatial_resolution(text: str) -> Tuple[int, str]:
    meters = parse_resolution_meters(text)
    if meters is None:
        blob = text.lower()
        if any(k in blob for k in ["sub-meter", "sub meter"]):
            return 5, "Sub-meter wording suggests ultra-high-resolution imaging."
        return 1, "No spatial resolution information was found automatically."
    if meters < 1:
        return 5, f"Approximate spatial resolution of {meters} m indicates ultra-high-resolution capability."
    if meters < 10:
        return 4, f"Approximate spatial resolution of {meters} m indicates very high-resolution imaging."
    if meters <= 50:
        return 3, f"Approximate spatial resolution of {meters} m indicates good medium-to-high resolution."
    if meters <= 100:
        return 2, f"Approximate spatial resolution of {meters} m indicates moderate resolution."
    return 1, f"Approximate spatial resolution of {meters} m indicates coarse imagery."


def score_breakthrough(text: str) -> Tuple[int, str]:
    blob = text.lower()
    if any(k in blob for k in ["quantum", "ion propulsion", "electric propulsion", "fully autonomous", "autonomous navigation"]):
        return 5, "Breakthrough text suggests revolutionary propulsion or autonomous operation."
    if any(k in blob for k in ["ai", "reusable", "fault detection", "novel communication", "advanced propulsion"]):
        return 4, "Text suggests significant technological advancement in systems or operations."
    if any(k in blob for k in ["improved", "lightweight", "miniaturized", "deployable", "thermal regulation"]):
        return 3, "Text suggests moderate technological improvement relative to baseline systems."
    if any(k in blob for k in ["standard", "legacy", "conventional"]):
        return 1, "Available text points to largely conventional technology."
    if blob:
        return 2, "Some technical information exists, but clear breakthrough evidence is limited."
    return 1, "No breakthrough evidence was found automatically."


def make_numeric_record(base: Dict[str, str], evidence_text: str, source_link: str) -> Dict[str, str]:
    payload_score, payload_why = score_payload_innovation(evidence_text)
    spectral_score, spectral_why = score_spectral_innovation(evidence_text)
    sensor_score, sensor_why = score_sensor_innovation(evidence_text)
    resolution_score, resolution_why = score_spatial_resolution(evidence_text)
    breakthrough_score, breakthrough_why = score_breakthrough(evidence_text)
    total = round((payload_score + spectral_score + sensor_score + resolution_score + breakthrough_score) / 5, 2)
    confidence = round(min(0.95, 0.40 + (len(evidence_text) / 1000)), 2) if evidence_text else 0.25
    return {
        "SATNAME": base.get("SATNAME", ""),
        "NORAD_ CAT_ID": base.get("NORAD_ CAT_ID", ""),
        "SOURCE LINK": source_link,
        "PAYLOAD INNOVATION SCORE": payload_score,
        "PAYLOAD INNOVATION JUSTIFICATION": payload_why,
        "SPECTRAL BAND INNOVATION SCORE": spectral_score,
        "SPECTRAL BAND INNOVATION JUSTIFICATION": spectral_why,
        "SENSOR SPECIFICATION INNOVATION SCORE": sensor_score,
        "SENSOR SPECIFICATION INNOVATION JUSTIFICATION": sensor_why,
        "SPATIAL RESOLUTION INNOVATION SCORE": resolution_score,
        "SPATIAL RESOLUTION INNOVATION JUSTIFICATION": resolution_why,
        "TECHNOLOGICAL BREAKTHROUGH SCORE": breakthrough_score,
        "TECHNOLOGICAL BREAKTHROUGH JUSTIFICATION": breakthrough_why,
        "NUMERIC TOTAL SCORE": total,
        "NUMERIC CONFIDENCE": confidence,
    }


def estimate_orbital_life_years(launch_date: str, decay_date: str, expected_lifetime: str) -> str:
    if safe_str(expected_lifetime):
        value = to_float(expected_lifetime)
        return "" if value is None else str(value)
    s = parse_date(launch_date)
    e = parse_date(decay_date)
    if s is None or e is None:
        return ""
    return str(round((e - s).days / 365.25, 2)) if e >= s else ""
