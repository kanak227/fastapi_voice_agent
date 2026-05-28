import os
import re
import zipfile
import xml.etree.ElementTree as ET


def normalize_text(text: str) -> str:
    # Replace common Unicode punctuation with ASCII equivalents.
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Collapse excess whitespace while keeping paragraph breaks.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_docx_text(docx_path: str) -> str:
    with zipfile.ZipFile(docx_path) as zf:
        with zf.open("word/document.xml") as fh:
            xml_bytes = fh.read()

    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        parts = []
        for t in para.findall(".//w:t", ns):
            if t.text:
                parts.append(t.text)
        if parts:
            paragraphs.append("".join(parts))

    return normalize_text("\n".join(paragraphs))


def main() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    helper_dir = os.path.join(base_dir, "bot-helper-data")
    out_dir = os.path.join(helper_dir, "extracted")
    os.makedirs(out_dir, exist_ok=True)

    inputs = []
    for root, _, files in os.walk(helper_dir):
        for name in files:
            if name.lower().endswith(".docx"):
                inputs.append(os.path.join(root, name))

    inputs.sort()
    for path in inputs:
        rel = os.path.relpath(path, helper_dir)
        safe = rel.replace(os.sep, "__")
        out_path = os.path.join(out_dir, safe.replace(".docx", ".txt"))
        text = extract_docx_text(path)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Extracted {rel} -> {os.path.relpath(out_path, base_dir)}")


if __name__ == "__main__":
    main()
