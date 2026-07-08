"""Document parsers for knowledge ingest (PDF handled separately via pypdf)."""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Formats with dedicated parsers (images use OCR elsewhere).
SUPPORTED_TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".pdf",
    ".docx",
    ".html",
    ".htm",
    ".json",
    ".xlsx",
    ".xlsm",
    ".pptx",
}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
UNSUPPORTED_OFFICE = {".doc", ".ppt", ".xls"}


def is_supported_suffix(suffix: str) -> bool:
    s = (suffix or "").lower()
    return s in SUPPORTED_TEXT_SUFFIXES or s in IMAGE_SUFFIXES


def extract_docx(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        if "word/document.xml" not in zf.namelist():
            return ""
        xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for para in root.findall(".//w:p", ns):
            texts = [t.text for t in para.findall(".//w:t", ns) if t.text]
            if texts:
                parts.append("".join(texts))
    return "\n\n".join(parts)


def extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def extract_json_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))

    def flatten(obj, prefix="") -> list[str]:
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                lines.extend(flatten(v, f"{prefix}{k}."))
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:200]):
                lines.extend(flatten(v, f"{prefix}[{i}]."))
        else:
            lines.append(f"{prefix.rstrip('.')}: {obj}")
        return lines

    return "\n".join(flatten(data)[:500])


def extract_csv_text(path: Path) -> str:
    """Turn CSV/TSV into readable rows so RAG can hit column values."""
    raw = path.read_text(encoding="utf-8-sig", errors="ignore")
    if not raw.strip():
        return ""
    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
    except csv.Error:
        dialect = csv.excel
        if "\t" in sample and sample.count("\t") > sample.count(","):
            dialect = csv.excel_tab
    reader = csv.reader(io.StringIO(raw), dialect)
    rows = list(reader)
    if not rows:
        return ""
    headers = [h.strip() or f"col_{i+1}" for i, h in enumerate(rows[0])]
    lines = [f"Table columns: {', '.join(headers)}"]
    for idx, row in enumerate(rows[1:400], start=1):
        cells = []
        for i, cell in enumerate(row):
            key = headers[i] if i < len(headers) else f"col_{i+1}"
            val = (cell or "").strip()
            if val:
                cells.append(f"{key}={val}")
        if cells:
            lines.append(f"Row {idx}: " + "; ".join(cells))
    return "\n".join(lines)


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    out: list[str] = []
    for si in root.findall("m:si", ns):
        texts = [t.text or "" for t in si.findall(".//m:t", ns)]
        out.append("".join(texts))
    return out


def _col_row(cell_ref: str) -> tuple[str, int]:
    m = re.match(r"([A-Z]+)(\d+)", cell_ref or "A1")
    if not m:
        return "A", 1
    return m.group(1), int(m.group(2))


def extract_xlsx(path: Path) -> str:
    """Parse XLSX sheets via OOXML (no openpyxl required)."""
    lines: list[str] = []
    with zipfile.ZipFile(path) as zf:
        shared = _xlsx_shared_strings(zf)
        sheet_files = sorted(
            n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for si, sheet_name in enumerate(sheet_files[:8], start=1):
            root = ET.fromstring(zf.read(sheet_name))
            rows_map: dict[int, dict[str, str]] = {}
            for c in root.findall(".//m:c", ns):
                ref = c.get("r") or "A1"
                col, row = _col_row(ref)
                cell_type = c.get("t")
                v = c.find("m:v", ns)
                if v is None or v.text is None:
                    continue
                if cell_type == "s":
                    try:
                        val = shared[int(v.text)]
                    except (IndexError, ValueError):
                        val = v.text
                else:
                    val = v.text
                rows_map.setdefault(row, {})[col] = val
            if not rows_map:
                continue
            lines.append(f"Sheet {si}:")
            for row_idx in sorted(rows_map)[:300]:
                cols = rows_map[row_idx]
                ordered = [cols[k] for k in sorted(cols, key=lambda x: (len(x), x))]
                line = " | ".join(x for x in ordered if x)
                if line.strip():
                    lines.append(f"  R{row_idx}: {line}")
    return "\n".join(lines)


def extract_pptx(path: Path) -> str:
    """Extract text from PowerPoint slides via OOXML."""
    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        slides = sorted(
            n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        )
        for i, name in enumerate(slides[:80], start=1):
            root = ET.fromstring(zf.read(name))
            texts = [
                node.text
                for node in root.iter()
                if node.tag.endswith("}t") and node.text and node.text.strip()
            ]
            if texts:
                parts.append(f"Slide {i}:\n" + "\n".join(texts))
    return "\n\n".join(parts)


def extract_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return extract_docx(path)
    if suffix in {".html", ".htm"}:
        return extract_html(path)
    if suffix == ".json":
        try:
            return extract_json_text(path)
        except json.JSONDecodeError:
            return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".csv", ".tsv"}:
        return extract_csv_text(path)
    if suffix in {".xlsx", ".xlsm"}:
        return extract_xlsx(path)
    if suffix == ".pptx":
        return extract_pptx(path)
    if suffix in UNSUPPORTED_OFFICE:
        raise ValueError(
            f"Legacy Office format {suffix} is not supported. "
            f"Please convert to {'.docx' if suffix == '.doc' else '.xlsx' if suffix == '.xls' else '.pptx'} and re-upload."
        )
    return ""
