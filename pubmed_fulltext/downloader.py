import re
import tarfile
import urllib.request
from pathlib import Path

import requests

from .oa_locator import OALocation


def _safe_filename(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^\w\-. ]", "_", text).strip()
    return text[:max_len] if text else "untitled"


def download_oa_location(location: OALocation, pmid: str, title: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{pmid}_{_safe_filename(title)}"

    if location.url.startswith("ftp://"):
        suffix = ".tar.gz" if location.format == "tgz" else ".pdf"
        dest = out_dir / f"{base_name}{suffix}"
        urllib.request.urlretrieve(location.url, dest)
        if location.format == "tgz":
            return _extract_pdf_from_tarball(dest, out_dir, base_name)
        return dest

    suffix = ".pdf" if location.format == "pdf" else ".html"
    dest = out_dir / f"{base_name}{suffix}"
    with requests.get(location.url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    return dest


def _extract_pdf_from_tarball(tarball_path: Path, out_dir: Path, base_name: str) -> Path:
    with tarfile.open(tarball_path, "r:gz") as tar:
        pdf_members = [m for m in tar.getmembers() if m.name.lower().endswith(".pdf")]
        if not pdf_members:
            return tarball_path
        member = pdf_members[0]
        member.name = f"{base_name}.pdf"
        tar.extract(member, path=out_dir)
    tarball_path.unlink(missing_ok=True)
    return out_dir / member.name
