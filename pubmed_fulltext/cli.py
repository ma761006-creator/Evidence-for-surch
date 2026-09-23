import argparse

from .pipeline import build_title_query, run_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="搜尋 PubMed 並自動下載免費全文")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query", help="PubMed 搜尋關鍵字，語法同 PubMed 網站")
    query_group.add_argument("--title", help="用文章標題精確搜尋（比對 PubMed 的 [Title] 欄位）")
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


def main():
    args = parse_args()
    query = build_title_query(args.title) if args.title else args.query
    run_pipeline(
        query=query,
        email=args.email,
        max_results=args.max_results,
        api_key=args.api_key,
        outdir=args.outdir,
        use_unpaywall=not args.no_unpaywall,
        free_full_text_only=args.free_full_text_only,
    )


if __name__ == "__main__":
    main()
