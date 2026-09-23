import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

PMC_OA_SERVICE = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
UNPAYWALL_API = "https://api.unpaywall.org/v2"


@dataclass
class OALocation:
    source: str  # "pmc" or "unpaywall"
    url: str
    format: str  # "pdf" or "tgz" / "html"


def find_pmc_oa_link(pmcid: str) -> OALocation | None:
    if not pmcid:
        return None
    resp = requests.get(PMC_OA_SERVICE, params={"id": pmcid}, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    if root.find("error") is not None:
        return None

    record = root.find(".//record")
    if record is None:
        return None

    links = record.findall("link")
    for fmt in ("pdf", "tgz"):
        for link in links:
            if link.get("format") == fmt:
                href = link.get("href", "")
                if href:
                    return OALocation(source="pmc", url=href, format=fmt)
    return None


def find_unpaywall_link(doi: str, email: str) -> OALocation | None:
    if not doi or not email:
        return None
    resp = requests.get(f"{UNPAYWALL_API}/{doi}", params={"email": email}, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()

    if not data.get("is_oa"):
        return None

    best = data.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf")
    if pdf_url:
        return OALocation(source="unpaywall", url=pdf_url, format="pdf")

    page_url = best.get("url")
    if page_url:
        return OALocation(source="unpaywall", url=page_url, format="html")

    for loc in data.get("oa_locations") or []:
        pdf_url = loc.get("url_for_pdf")
        if pdf_url:
            return OALocation(source="unpaywall", url=pdf_url, format="pdf")

    return None
