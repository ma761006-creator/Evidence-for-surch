import argparse
import csv
import time
from pathlib import Path

from .downloader import download_oa_location
from .entrez_client import EntrezClient
from .oa_locator import OALocation, find_europepmc_link, find_pmc_oa_link, find_unpaywall_link


def parse_args():
    parser = argparse.ArgumentParser(description="搜尋 PubMed 並自動下載免費全文")
    parser.add_argument("--query", required=True, help="PubMed 搜尋關鍵字，語法同 PubMed 網站")
    parser.add_argument("--max-results", type=int, default=20, help="最多搜尋筆數（預設 20）")
    parser.add_argument("--email", required=True, help="聯絡信箱，NCBI 及 Unpaywall 皆要求提供")
    parser.add_argument("--api-key", default="", help="NCBI API key（可選，可提高查詢速率上限）")
    parser.add_argument("--outdir", default="downloads", help="全文與索引檔輸出資料夾")
    parser.add_argument(
        "--no-unpaywall",
        action="store_true",
        help="不使用 Unpaywall 查詢非 PMC 期刊的開放取用連結",
    )
    parser.add_argument(
        "--free-full-text-only",
        action="store_true",
        help='在搜尋階段就加上 PubMed 的「Free full text」篩選（附加 free full text[sb]），避免搜到大量沒有全文的文章',
    )
    return parser.parse_args()


def run(args):
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = EntrezClient(email=args.email, api_key=args.api_key)

    query = args.query
    if args.free_full_text_only:
        query = f"({query}) AND free full text[sb]"

    print(f"搜尋 PubMed: {query}")
    pmids = client.search(query, max_results=args.max_results)
    print(f"找到 {len(pmids)} 篇文獻，開始擷取詳細資料...")

    articles = client.fetch_articles(pmids)

    for article in articles:
        location = None

        if article.pmcid:
            try:
                location = find_pmc_oa_link(article.pmcid)
            except Exception as exc:
                article.note = f"PMC OA 查詢失敗: {exc}"

        if location is None and not args.no_unpaywall and article.doi:
            try:
                location = find_unpaywall_link(article.doi, args.email)
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
            print(f"[{article.pmid}] 找不到免費全文")
            continue

        try:
            path = download_oa_location(location, article.pmid, article.title, out_dir)
            article.fulltext_source = location.source
            article.fulltext_url = location.url
            article.download_path = str(path)
            article.status = "downloaded"
            print(f"[{article.pmid}] 已下載 ({location.source}) -> {path}")
        except Exception as exc:
            article.status = "download_failed"
            article.note = str(exc)
            print(f"[{article.pmid}] 下載失敗: {exc}")

    index_path = out_dir / "index.csv"
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

    downloaded = sum(1 for a in articles if a.status == "downloaded")
    print(f"\n完成：共 {len(articles)} 篇，成功下載 {downloaded} 篇。索引檔：{index_path}")


def main():
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()
