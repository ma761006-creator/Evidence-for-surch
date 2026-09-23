from __future__ import annotations

import csv
import time
from pathlib import Path

from .downloader import download_oa_location
from .entrez_client import EntrezClient
from .models import Article
from .oa_locator import OALocation, find_europepmc_link, find_pmc_oa_link, find_unpaywall_link


def build_pico_query(
    population: str = "",
    intervention: str = "",
    comparison: str = "",
    outcome: str = "",
) -> str:
    parts = []
    for field in (population, intervention, comparison, outcome):
        field = field.strip()
        if not field:
            continue
        terms = [t.strip() for t in field.replace(" OR ", ",").split(",") if t.strip()]
        if len(terms) > 1:
            parts.append("(" + " OR ".join(terms) + ")")
        else:
            parts.append(terms[0])
    return " AND ".join(parts)


def run_pipeline(
    query: str,
    email: str,
    max_results: int = 20,
    api_key: str = "",
    outdir: str = "downloads",
    use_unpaywall: bool = True,
    free_full_text_only: bool = False,
    log=print,
) -> list[Article]:
    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = EntrezClient(email=email, api_key=api_key)

    if free_full_text_only:
        query = f"({query}) AND free full text[sb]"

    log(f"搜尋 PubMed: {query}")
    pmids = client.search(query, max_results=max_results)
    log(f"找到 {len(pmids)} 篇文獻，開始擷取詳細資料...")

    articles = client.fetch_articles(pmids)

    for article in articles:
        location = None

        if article.pmcid:
            try:
                location = find_pmc_oa_link(article.pmcid)
            except Exception as exc:
                article.note = f"PMC OA 查詢失敗: {exc}"

        if location is None and use_unpaywall and article.doi:
            try:
                location = find_unpaywall_link(article.doi, email)
                time.sleep(0.1)
            except Exception as exc:
                article.note = f"Unpaywall 查詢失敗: {exc}"

        if location is None:
            try:
                location = find_europepmc_link(article.pmid)
            except Exception as exc:
                article.note = f"Europe PMC 查詢失敗: {exc}"

        if location is None:
            try:
                url = client.find_linkout_url(article.pmid)
                if url:
                    fmt = "pdf" if url.lower().endswith(".pdf") else "html"
                    location = OALocation(source="linkout", url=url, format=fmt)
            except Exception as exc:
                article.note = f"PubMed LinkOut 查詢失敗: {exc}"

        if location is None:
            article.status = "not_found"
            log(f"[{article.pmid}] 找不到免費全文")
            continue

        try:
            path = download_oa_location(location, article.pmid, article.title, out_dir)
            article.fulltext_source = location.source
            article.fulltext_url = location.url
            article.download_path = str(path)
            article.status = "downloaded"
            log(f"[{article.pmid}] 已下載 ({location.source}) -> {path}")
        except Exception as exc:
            article.status = "download_failed"
            article.note = str(exc)
            log(f"[{article.pmid}] 下載失敗: {exc}")

    write_index_csv(articles, out_dir / "index.csv")

    downloaded = sum(1 for a in articles if a.status == "downloaded")
    log(f"\n完成：共 {len(articles)} 篇，成功下載 {downloaded} 篇。索引檔：{out_dir / 'index.csv'}")

    return articles


def write_index_csv(articles: list[Article], index_path: Path) -> None:
    with open(index_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pmid", "title", "authors", "journal", "year", "doi", "pmcid",
                "status", "fulltext_source", "fulltext_url", "download_path", "note",
            ],
        )
        writer.writeheader()
        for article in articles:
            writer.writerow(vars(article))
