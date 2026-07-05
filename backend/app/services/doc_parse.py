import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


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
    return ""
