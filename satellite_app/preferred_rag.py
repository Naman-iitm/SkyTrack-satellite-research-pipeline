from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .helpers import best_text_snippet, is_blank, normalize_name, safe_str

DDG_HTML_SEARCH = "https://html.duckduckgo.com/html/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Satellite-Project-Successor-Tool)"}

PREFERRED_GLOBAL_DOMAINS = [
    "ucsusa.org",
    "nssdc.gsfc.nasa.gov",
    "eoportal.org",
    "space.skyrocket.de",
    "satbeams.com",
    "satcat.com",
    "keeptrack.space",
    "n2yo.com",
    "nextspaceflight.com",
    "celestrak.org",
    "planet4589.org",
    "nanosats.eu",
    "satnogs.org",
    "unoosa.org",
    "nasa.gov",
    "esa.int",
    "copernicus.eu",
    "isro.gov.in",
    "global.jaxa.jp",
    "cnsa.gov.cn",
    "cast.cn",
    "asc-csa.gc.ca",
    "dlr.de",
    "cnes.fr",
    "space-track.org",
    "aerospace.csis.org",
]


def _url_domain(url: str) -> str:
    s = safe_str(url)
    if not s:
        return ""
    if not s.startswith("http"):
        s = "https://" + s.lstrip("/")
    try:
        parsed = urlparse(s)
        domain = parsed.netloc.lower().replace("www.", "")
        return domain
    except Exception:
        return ""


def _candidate_domains_from_country(country_websites_df, country_acronym: str) -> List[str]:
    if country_websites_df is None or getattr(country_websites_df, "empty", True) or is_blank(country_acronym):
        return []
    rows = country_websites_df[country_websites_df["Acronym"] == safe_str(country_acronym)]
    if rows.empty:
        return []
    urls = rows.iloc[0].get("URLS", [])
    domains = []
    if isinstance(urls, list):
        for url in urls:
            d = _url_domain(url)
            if d and d not in domains:
                domains.append(d)
    return domains


def _candidate_domains_from_generic(generic_websites_df, limit: int = 8) -> List[str]:
    domains = []
    if generic_websites_df is None or getattr(generic_websites_df, "empty", True):
        return domains
    for _, row in generic_websites_df.iterrows():
        urls = row.get("URLS", [])
        if isinstance(urls, list):
            for url in urls:
                d = _url_domain(url)
                if d and d not in domains:
                    domains.append(d)
                    if len(domains) >= limit:
                        return domains
    return domains


def build_priority_domains(country_acronym: str, country_websites_df=None, generic_websites_df=None, max_domains: int = 10) -> List[str]:
    domains: List[str] = []

    # First: project-approved structured databases that are fast and highly useful
    for d in PREFERRED_GLOBAL_DOMAINS:
        if d and d not in domains:
            domains.append(d)

    # Second: country-specific websites supplied by the project team
    for d in _candidate_domains_from_country(country_websites_df, country_acronym):
        if d and d not in domains:
            domains.append(d)

    # Third: additional generic project websites gathered from the Websites sheet
    for d in _candidate_domains_from_generic(generic_websites_df):
        if d and d not in domains:
            domains.append(d)

    return domains[:max_domains]


@lru_cache(maxsize=2048)
def ddg_site_search(query: str) -> List[str]:
    try:
        response = requests.post(DDG_HTML_SEARCH, data={"q": query}, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        urls: List[str] = []
        for a in soup.select("a.result__a, a[data-testid='result-title-a'], a[href]"):
            href = a.get("href", "")
            if not href:
                continue
            if "duckduckgo.com/l/?" in href:
                qs = parse_qs(urlparse(href).query)
                href = unquote(qs.get("uddg", [href])[0])
            if href.startswith("http") and href not in urls:
                urls.append(href)
            if len(urls) >= 5:
                break
        return urls
    except Exception:
        return []


@lru_cache(maxsize=4096)
def fetch_clean_text(url: str) -> Dict[str, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
        if meta and meta.get("content"):
            meta_desc = meta.get("content", "")

        texts = []
        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            t = tag.get_text(" ", strip=True)
            if t and len(t) > 25:
                texts.append(t)
        merged = " ".join(texts)
        merged = re.sub(r"\s+", " ", merged).strip()
        merged = merged[:12000]
        snippet = best_text_snippet(meta_desc or merged or title, 320)
        return {"url": url, "title": title, "text": merged, "snippet": snippet}
    except Exception:
        return {"url": url, "title": "", "text": "", "snippet": ""}


def _query_variants(satname: str, intldes: str, norad: str) -> List[str]:
    variants = []
    if not is_blank(satname):
        raw_name = safe_str(satname)
        variants.append(f'"{raw_name}" satellite')
        stripped = re.sub(r"\(.*?\)", " ", raw_name)
        stripped = re.sub(r"\s+", " ", stripped).strip()
        if stripped and stripped != raw_name:
            variants.append(f'"{stripped}" satellite')
        norm = normalize_name(satname)
        if norm and norm != raw_name.upper() and norm != stripped.upper():
            variants.append(f'"{norm}" satellite')
    if not is_blank(intldes):
        variants.append(f'"{safe_str(intldes)}" satellite')
    if not is_blank(norad):
        variants.append(f'"{safe_str(norad)}" satellite')
    deduped = []
    for v in variants:
        if v not in deduped:
            deduped.append(v)
    return deduped[:3]


def _direct_url_candidates(domain: str, satname: str, intldes: str, norad: str) -> List[str]:
    candidates: List[str] = []
    if domain == "nssdc.gsfc.nasa.gov" and not is_blank(intldes):
        candidates.append(f"https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id={quote_plus(safe_str(intldes))}")
    if domain == "n2yo.com" and not is_blank(norad):
        candidates.append(f"https://www.n2yo.com/satellite/?s={safe_str(norad)}")
    if domain == "satbeams.com" and not is_blank(norad):
        candidates.append(f"https://www.satbeams.com/satellites?norad={safe_str(norad)}")
    if domain == "celestrak.org":
        if not is_blank(norad):
            candidates.append(f"https://celestrak.org/satcat/search.php?CATNR={safe_str(norad)}")
        if not is_blank(intldes):
            candidates.append(f"https://celestrak.org/satcat/search.php?INTDES={quote_plus(safe_str(intldes))}")
    if domain == "satcat.com" and not is_blank(norad):
        candidates.append(f"https://www.satcat.com/sats/{safe_str(norad)}")
    if domain == "keeptrack.space" and not is_blank(norad):
        candidates.append(f"https://keeptrack.space/satellite/{safe_str(norad)}")
    if domain == "ucsusa.org":
        candidates.append("https://www.ucsusa.org/resources/satellite-database")
    return candidates


def _record_relevant(record: Dict[str, str], satname: str, intldes: str, norad: str) -> bool:
    hay = " ".join([record.get("title", ""), record.get("snippet", ""), record.get("text", "")]).lower()
    if not is_blank(intldes) and safe_str(intldes).lower() in hay:
        return True
    if not is_blank(norad) and safe_str(norad).lower() in hay:
        return True
    if not is_blank(satname):
        raw_name = re.sub(r"\(.*?\)", " ", safe_str(satname)).strip().lower()
        if raw_name and raw_name in hay:
            return True
        tokens = [t for t in re.split(r"[^a-z0-9]+", raw_name) if len(t) > 3]
        hits = sum(1 for t in tokens if t in hay)
        if hits >= 2:
            return True
    return False


def retrieve_priority_context(
    satname: str,
    intldes: str,
    norad: str,
    country_acronym: str,
    country_websites_df=None,
    generic_websites_df=None,
    max_domains: int = 8,
    max_pages: int = 4,
) -> Dict[str, object]:
    domains = build_priority_domains(country_acronym, country_websites_df, generic_websites_df, max_domains=max_domains)
    page_records: List[Dict[str, str]] = []
    seen_urls = set()

    for domain in domains:
        direct_urls = _direct_url_candidates(domain, satname, intldes, norad)
        found_url = None
        for direct_url in direct_urls:
            if direct_url not in seen_urls:
                found_url = direct_url
                break

        if not found_url:
            for query_variant in _query_variants(satname, intldes, norad):
                query = f"site:{domain} {query_variant}"
                urls = ddg_site_search(query)
                for url in urls:
                    if _url_domain(url).endswith(domain) and url not in seen_urls:
                        found_url = url
                        break
                if found_url:
                    break

        if found_url:
            seen_urls.add(found_url)
            record = fetch_clean_text(found_url)
            if (record.get("text") or record.get("snippet")) and _record_relevant(record, satname, intldes, norad):
                page_records.append(record)
            if len(page_records) >= max_pages:
                break

    combined_text = " || ".join([r.get("text", "") for r in page_records if r.get("text")])
    snippets = [r.get("snippet", "") for r in page_records if r.get("snippet")]
    top_source_url = page_records[0]["url"] if page_records else ""
    return {
        "priority_domains": domains,
        "page_records": page_records,
        "combined_text": combined_text[:20000],
        "snippets": snippets,
        "top_source_url": top_source_url,
    }
