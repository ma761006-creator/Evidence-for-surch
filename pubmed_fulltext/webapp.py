from __future__ import annotations

import re
import uuid
from pathlib import Path

from flask import Flask, abort, render_template_string, request, send_from_directory

from .pipeline import build_pico_query, run_pipeline

app = Flask(__name__)
BASE_DOWNLOADS_DIR = Path("downloads")

FORM_TEMPLATE = """
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>PubMed 免費全文搜尋</title>
<style>
  body { font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 22px; }
  fieldset { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 16px; padding: 12px 16px; }
  legend { font-weight: bold; padding: 0 6px; }
  label { display: block; margin-top: 10px; font-size: 14px; color: #444; }
  input[type=text], input[type=email], input[type=number] {
    width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box;
    border: 1px solid #ccc; border-radius: 6px; font-size: 14px;
  }
  .checkbox-row { display: flex; align-items: center; gap: 6px; margin-top: 10px; }
  .checkbox-row label { margin: 0; }
  button {
    margin-top: 20px; padding: 10px 24px; font-size: 15px; border: none;
    border-radius: 6px; background: #2563eb; color: white; cursor: pointer;
  }
  button:hover { background: #1d4ed8; }
  .hint { color: #888; font-size: 12px; margin-top: 4px; }
</style>
</head>
<body>
<h1>PubMed 免費全文搜尋 / 下載</h1>
{% if error %}<p style="color:#b91c1c; background:#fef2f2; padding:10px 14px; border-radius:6px;">{{ error }}</p>{% endif %}
<form method="post" action="/search">
  <fieldset>
    <legend>PICO 關鍵字（可只填部分欄位；同一欄位多個詞用逗號分隔會自動用 OR 組合）</legend>
    <label>P（族群 / 問題）<input type="text" name="population" value="{{ population }}"></label>
    <label>I（介入措施）<input type="text" name="intervention" value="{{ intervention }}"></label>
    <label>C（對照組，可留空）<input type="text" name="comparison" value="{{ comparison }}"></label>
    <label>O（結果指標，可留空）<input type="text" name="outcome" value="{{ outcome }}"></label>
  </fieldset>

  <fieldset>
    <legend>或直接輸入完整 PubMed 查詢式（填了就優先使用，忽略上面的 PICO 欄位）</legend>
    <label>自訂查詢式<input type="text" name="raw_query" value="{{ raw_query }}" placeholder='例如：COPD[Title] AND 2023[PDAT]'></label>
  </fieldset>

  <fieldset>
    <legend>搜尋設定</legend>
    <label>聯絡信箱（NCBI / Unpaywall 要求）
      <input type="email" name="email" value="{{ email }}" required>
    </label>
    <label>最多搜尋筆數
      <input type="number" name="max_results" value="{{ max_results }}" min="1" max="200">
    </label>
    <label>NCBI API key（可選）
      <input type="text" name="api_key" value="{{ api_key }}">
    </label>
    <div class="checkbox-row">
      <input type="checkbox" id="free_full_text_only" name="free_full_text_only" {{ 'checked' if free_full_text_only else '' }}>
      <label for="free_full_text_only">只搜尋 PubMed 標記為 Free full text 的文章</label>
    </div>
    <div class="checkbox-row">
      <input type="checkbox" id="use_unpaywall" name="use_unpaywall" {{ 'checked' if use_unpaywall else '' }}>
      <label for="use_unpaywall">查詢 Unpaywall（找非 PMC 期刊的開放取用全文）</label>
    </div>
  </fieldset>

  <button type="submit">搜尋並下載免費全文</button>
</form>
</body>
</html>
"""

RESULTS_TEMPLATE = """
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>搜尋結果</title>
<style>
  body { font-family: -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif; max-width: 960px; margin: 40px auto; padding: 0 16px; color: #222; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
  th { background: #f5f5f5; }
  .status-downloaded { color: #15803d; font-weight: bold; }
  .status-not_found { color: #b45309; }
  .status-download_failed { color: #b91c1c; }
  a.back { display: inline-block; margin-top: 20px; }
  .summary { background: #eff6ff; border-radius: 8px; padding: 12px 16px; margin-top: 12px; }
</style>
</head>
<body>
<h1>搜尋結果</h1>
<p>查詢式：<code>{{ query }}</code></p>
<div class="summary">共 {{ articles|length }} 篇，成功下載 {{ downloaded_count }} 篇。
<a href="/files/{{ run_id }}/index.csv">下載完整索引 CSV</a></div>

<table>
<tr>
  <th>PMID</th><th>標題</th><th>期刊 / 年份</th><th>狀態</th><th>來源</th><th>全文</th>
</tr>
{% for a in articles %}
<tr>
  <td><a href="https://pubmed.ncbi.nlm.nih.gov/{{ a.pmid }}/" target="_blank">{{ a.pmid }}</a></td>
  <td>{{ a.title }}</td>
  <td>{{ a.journal }} ({{ a.year }})</td>
  <td class="status-{{ a.status }}">{{ a.status }}</td>
  <td>{{ a.fulltext_source }}</td>
  <td>
    {% if a.status == 'downloaded' %}
      <a href="/files/{{ run_id }}/{{ a.download_path.split('/')[-1] }}" target="_blank">下載檔案</a>
    {% else %}
      {{ a.note }}
    {% endif %}
  </td>
</tr>
{% endfor %}
</table>

<a class="back" href="/">← 回到搜尋表單</a>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(
        FORM_TEMPLATE,
        population="",
        intervention="",
        comparison="",
        outcome="",
        raw_query="",
        email="",
        max_results=20,
        api_key="",
        free_full_text_only=False,
        use_unpaywall=True,
    )


@app.post("/search")
def search():
    form = request.form
    raw_query = form.get("raw_query", "").strip()

    if raw_query:
        query = raw_query
    else:
        query = build_pico_query(
            population=form.get("population", ""),
            intervention=form.get("intervention", ""),
            comparison=form.get("comparison", ""),
            outcome=form.get("outcome", ""),
        )

    if not query:
        return render_template_string(
            FORM_TEMPLATE,
            population=form.get("population", ""),
            intervention=form.get("intervention", ""),
            comparison=form.get("comparison", ""),
            outcome=form.get("outcome", ""),
            raw_query=raw_query,
            email=form.get("email", ""),
            max_results=form.get("max_results", 20),
            api_key=form.get("api_key", ""),
            free_full_text_only=bool(form.get("free_full_text_only")),
            use_unpaywall=bool(form.get("use_unpaywall")),
        ), 400

    run_id = uuid.uuid4().hex
    outdir = BASE_DOWNLOADS_DIR / run_id

    try:
        articles = run_pipeline(
            query=query,
            email=form.get("email", ""),
            max_results=int(form.get("max_results") or 20),
            api_key=form.get("api_key", ""),
            outdir=str(outdir),
            use_unpaywall=bool(form.get("use_unpaywall")),
            free_full_text_only=bool(form.get("free_full_text_only")),
            log=app.logger.info,
        )
    except Exception as exc:
        return render_template_string(
            FORM_TEMPLATE,
            population=form.get("population", ""),
            intervention=form.get("intervention", ""),
            comparison=form.get("comparison", ""),
            outcome=form.get("outcome", ""),
            raw_query=raw_query,
            email=form.get("email", ""),
            max_results=form.get("max_results", 20),
            api_key=form.get("api_key", ""),
            free_full_text_only=bool(form.get("free_full_text_only")),
            use_unpaywall=bool(form.get("use_unpaywall")),
            error=f"搜尋過程發生錯誤：{exc}",
        ), 502

    downloaded_count = sum(1 for a in articles if a.status == "downloaded")

    return render_template_string(
        RESULTS_TEMPLATE,
        query=query,
        run_id=run_id,
        articles=articles,
        downloaded_count=downloaded_count,
    )


@app.get("/files/<run_id>/<path:filename>")
def serve_file(run_id, filename):
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        abort(404)
    directory = (BASE_DOWNLOADS_DIR / run_id).resolve()
    if not directory.is_relative_to(BASE_DOWNLOADS_DIR.resolve()):
        abort(404)
    return send_from_directory(directory, filename)


def main():
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
