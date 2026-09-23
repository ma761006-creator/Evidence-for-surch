# Evidence for Search — PubMed 免費全文自動下載工具

搜尋 PubMed 文獻，並自動嘗試下載免費（開放取用）全文，同時輸出一份包含後設資料與下載結果的索引檔（`index.csv`）。

## 運作原理

1. **搜尋**：透過 NCBI E-utilities（`esearch` + `efetch`）依關鍵字搜尋 PubMed，取得 PMID、標題、作者、期刊、年份、DOI、PMCID 等資訊。
2. **找免費全文**：
   - 若文章有 **PMCID**（已收錄於 PubMed Central），查詢 [PMC Open Access 服務](https://www.ncbi.nlm.nih.gov/pmc/tools/oai/) 取得 PDF 或全文壓縮包下載連結。
   - 若文章不在 PMC 開放取用子集內，但有 **DOI**，改用 [Unpaywall API](https://unpaywall.org/products/api) 查詢是否有其他來源（如機構典藏、作者自存檔、出版商網站）提供的合法開放取用全文。
   - 若以上兩者都找不到，再查詢 **Europe PMC**（歐洲版 PMC，常會比 NCBI 自己更快收錄部分開放取用全文），確認該篇是否標示為開放取用並取得全文連結。
   - 最後查詢 PubMed 自己的 **LinkOut** 服務（`elink.fcgi`），比對出版商是否直接向 NCBI 登記該篇為「free resource」（也就是 PubMed 頁面上會顯示的「Free article」小圖示），藉此多抓一些前面來源都未收錄、但出版商自己標記免費的文章。
3. **下載**：將找到的全文下載至指定資料夾，副檔名依來源為 PDF 或 HTML，檔名為 `PMID_文章標題.pdf`。
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
| `--query` | 二擇一 | PubMed 搜尋字串，語法與 PubMed 網站相同（可用 `AND`/`OR`、`[Title]`、`[MeSH Terms]` 等）。與 `--title` 二選一 |
| `--title` | 二擇一 | 直接用文章標題搜尋，會自動組成 `"標題"[Title]` 精確比對 PubMed 的標題欄位。與 `--query` 二選一 |
| `--max-results` | 否 | 最多搜尋筆數，預設 20 |
| `--email` | 是 | 聯絡信箱，NCBI 與 Unpaywall API 皆要求提供以識別呼叫來源 |
| `--api-key` | 否 | [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/)，可將查詢速率上限從每秒 3 次提高到每秒 10 次 |
| `--outdir` | 否 | 全文與索引檔輸出資料夾，預設 `downloads` |
| `--no-unpaywall` | 否 | 加上此參數則不查詢 Unpaywall，只下載 PMC 開放取用全文 |
| `--free-full-text-only` | 否 | 在搜尋時就加上 PubMed 的「Free full text」篩選（附加 `free full text[sb]`），避免搜到大量沒有全文的文章，適合想先驗證下載流程或只想要免費全文結果的情境 |

### 範例查詢語法

```bash
python -m pubmed_fulltext.cli \
  --query "diabetes[Title] AND 2023[PDAT]" \
  --email your_email@example.com
```

### 依文章標題搜尋

如果已經知道確切（或接近確切）的文章標題，可以直接用 `--title`，不用自己組查詢語法：

```bash
python -m pubmed_fulltext.cli \
  --title "A Novel Coronavirus from Patients with Pneumonia in China, 2019" \
  --email your_email@example.com
```

找不到完全相符的標題時，可以只保留關鍵幾個字再試一次，或改用 `--query` 搭配 `[Title]` 做部分比對。

## 網頁版（適合用 PICO 架構搜尋）

如果不想用指令列，也可以啟動本機網頁介面，用表單填寫 PICO（Population / Intervention / Comparison / Outcome）關鍵字：

```bash
pip install -r requirements.txt
python -m pubmed_fulltext.webapp
```

啟動後，用瀏覽器打開 <http://127.0.0.1:5000>，會看到一個表單，三種搜尋方式擇一使用（優先順序：**文章標題 > 自訂查詢式 > PICO 欄位**）：

- **依文章標題搜尋**：貼上完整或接近完整的文章標題，直接精確比對
- **PICO 關鍵字**：分別填 **P / I / C / O** 欄位（同一欄位可用逗號分隔多個同義詞，會自動用 `OR` 組合，各欄位之間用 `AND` 組合）
- **自訂查詢式**：直接貼完整的 PubMed 查詢語法

填入聯絡信箱、要抓的最多筆數，勾選是否要查 Unpaywall、是否只搜尋 Free full text，送出後會直接在網頁上看到每篇文章的下載狀態，成功下載的可以直接點連結開啟 PDF，也可以下載整份 `index.csv`。

> 這個網頁介面只會在你自己的電腦上執行（`127.0.0.1`，只有你的瀏覽器連得到），不會對外公開，也沒有帳號登入機制，設計上就是給自己本機使用的小工具。

網頁版每次搜尋會建立一個獨立的子資料夾（`downloads/<隨機代碼>/`），避免不同次搜尋的結果互相覆蓋。

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
