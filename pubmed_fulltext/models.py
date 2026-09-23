from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Article:
    pmid: str
    title: str = ""
    authors: str = ""
    journal: str = ""
    year: str = ""
    doi: str = ""
    pmcid: str = ""
    fulltext_source: str = ""
    fulltext_url: str = ""
    download_path: str = ""
    status: str = "pending"
    note: str = ""
