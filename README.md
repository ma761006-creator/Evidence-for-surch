# Evidence for Search — PubMed 免費全文自動下載工具

搜尋 PubMed 文獻，並自動嘗試下載免費（開放取用）全文，同時輸出一份包含後設資料與下載結果的索引檔（`index.csv`）。

## 運作原理

1. **搜尋**：透過 NCBI E-utilities（`esearch` + `efetch`）依關鍵字搜尋 PubMed，取得 PMID、標題、作者、期刊、年份、DOI、PMCID 等資訊。
2. **找免費全文**：
   - 若文章有 **PMCID**（已收錄於 PubMed Central），查詢 [PMC Open Access 服務](https://www.ncbi.nlm.nih.gov/pmc/tools/oai/) 取得 PDF 或全文壓縮包下載連結。
   - 若文章不在 PMC 開放取用子集內，但有 **DOI**，改用 [Unpaywall API](https://unpaywall.org/products/api) 查詢是否有其他來源（如機構典藏、作者自存檔）提供的合法開放取用全文。
3. **下載**：將找到的全文（PDF）下載至指定資料夾，檔名為 `PMID_文章標題.pdf`。
4. **輸出索引**：所有文章無論是否成功下載，都會列在 `downloads/index.csv`，包含下載狀態（`downloaded` / `not_found` / `download_failed`）。

> 本工具只會下載「開放取用（Open Access）」或依合法授權可公開取得」的全文，不會、也無法繞過付費牆下載訂閱制文獻。

## 安裝

```bash
pip install -r requirements.txt
```

## 使用方式

```bash
python -m pubmed_fulltext.cli \
  --query "COVID-19 vaccine efficacy" \
  --max-results 30 \
  --email your_email@example.com \
  --outdir downloads
```

### 參數說明

| 參數 | 必填 | 說明 |
|---|---|---|
| `--query` | 是 | PubMed 搜尋字串，語法與 PubMed 網站相同（可用 `AND`/`OR`、`[Title]`、`[MeSH Terms]` 等） |
| `--max-results` | 否 | 最多搜尋筆數，預設 20 |
| `--email` | 是 | 聯絡信箱，NCBI 與 Unpaywall API 皆要求提供以識別呼叫來源 |
| `--api-key` | 否 | [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/)，可將查詢速率上限從每秒 3 次提高到每秒 10 次 |
| `--outdir` | 否 | 全文與索引檔輸出資料夾，預設 `downloads` |
| `--no-unpaywall` | 否 | 加上此參數則不查詢 Unpaywall，只下載 PMC 開放取用全文 |

### 範例查詢語法

```bash
python -m pubmed_fulltext.cli \
  --query "diabetes[Title] AND 2023[PDAT]" \
  --email your_email@example.com
```

## 輸出結果

```
downloads/
├── index.csv                          # 所有文章的後設資料與下載狀態
├── 39012345_Some_Article_Title.pdf    # 成功下載的全文
└── ...
```

`index.csv` 欄位：`pmid, title, authors, journal, year, doi, pmcid, status, fulltext_source, fulltext_url, download_path, note`

## 限制與注意事項

- 並非所有 PubMed 文獻都有免費全文；找不到時 `status` 會標示為 `not_found`。
- 請遵守 [NCBI 使用規範](https://www.ncbi.nlm.nih.gov/books/NBK25497/)：不要用過高頻率查詢，本工具已內建節流（無 API key 時每秒最多 3 次請求）。
- Unpaywall API 為免費服務，但要求提供真實聯絡信箱。
- 大量下載（例如上千篇）建議申請 NCBI API key 並適度分批執行。
