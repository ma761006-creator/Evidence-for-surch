from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import requests

from .models import Article

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class EntrezClient:
    def __init__(self, email: str, api_key: str = "", tool: str = "pubmed-fulltext"):
        if not email:
            raise ValueError("NCBI 要求提供聯絡信箱 (email)")
        self.email = email
        self.api_key = api_key
        self.tool = tool
        self._min_interval = 0.11 if api_key else 0.34
        self._last_request = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        wait = self._min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _params(self, **extra):
        params = {"email": self.email, "tool": self.tool}
        if self.api_key:
            params["api_key"] = self.api_key
        params.update(extra)
        return params

    def search(self, query: str, max_results: int = 20) -> list[str]:
        self._throttle()
        resp = requests.get(
            f"{EUTILS_BASE}/esearch.fcgi",
            params=self._params(db="pubmed", term=query, retmax=max_results, retmode="json"),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_articles(self, pmids: list[str]) -> list[Article]:
        if not pmids:
            return []
        self._throttle()
        resp = requests.get(
            f"{EUTILS_BASE}/efetch.fcgi",
            params=self._params(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml"),
            timeout=60,
        )
        resp.raise_for_status()
        return self._parse_articles(resp.text)

    def find_linkout_url(self, pmid: str) -> str:
        self._throttle()
        resp = requests.get(
            f"{EUTILS_BASE}/elink.fcgi",
            params=self._params(dbfrom="pubmed", id=pmid, cmd="llinks", retmode="xml"),
            timeout=30,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        for obj_url in root.findall(".//ObjUrl"):
            attributes = [(a.text or "").lower() for a in obj_url.findall("Attribute")]
            if any("free" in attr for attr in attributes):
                url = (obj_url.findtext("Url") or "").strip()
                if url:
                    return url
        return ""

    @staticmethod
    def _parse_articles(xml_text: str) -> list[Article]:
        root = ET.fromstring(xml_text)
        articles = []
        for pubmed_article in root.findall(".//PubmedArticle"):
            medline = pubmed_article.find("MedlineCitation")
            article_el = medline.find("Article")
            pmid = medline.findtext("PMID", default="").strip()

            title = (article_el.findtext("ArticleTitle") or "").strip()

            authors = []
            for author in article_el.findall("./AuthorList/Author"):
                last = author.findtext("LastName")
                fore = author.findtext("ForeName")
                if last and fore:
                    authors.append(f"{last} {fore}")
                elif last:
                    authors.append(last)
            authors_str = "; ".join(authors)

            journal = (article_el.findtext("Journal/Title") or "").strip()
            year = (
                article_el.findtext("Journal/JournalIssue/PubDate/Year")
                or article_el.findtext("Journal/JournalIssue/PubDate/MedlineDate")
                or ""
            ).strip()

            doi = ""
            pmcid = ""
            for article_id in pubmed_article.findall(".//PubmedData/ArticleIdList/ArticleId"):
                id_type = article_id.get("IdType", "")
                if id_type == "doi":
                    doi = (article_id.text or "").strip()
                elif id_type == "pmc":
                    pmcid = (article_id.text or "").strip()

            articles.append(
                Article(
                    pmid=pmid,
                    title=title,
                    authors=authors_str,
                    journal=journal,
                    year=year,
                    doi=doi,
                    pmcid=pmcid,
                )
            )
        return articles
