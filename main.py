import csv
import glob
import os

import fitz

CSV_FILE = "output.csv"


def normalize_color(color):
    if isinstance(color, tuple):
        if all(isinstance(c, float) and c <= 1 for c in color):
            color = tuple(int(c * 255) for c in color)
        return "#{:02x}{:02x}{:02x}".format(*color)
    elif isinstance(color, int):
        return "#{:06x}".format(color)
    elif isinstance(color, str):
        return color.lower()
    return None


def extract_qa_from_pdf(pdf_path: str) -> dict[str, str]:
    doc = fitz.open(pdf_path)
    qa_pairs: dict[str, str] = {}
    current_question = ""
    current_answer = ""
    prev = 0  # 0 = zuletzt Frage, 1 = zuletzt Antwort

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    size = span["size"]
                    color = normalize_color(span["color"])

                    if size == 12.0 and color == "#000000":
                        if prev == 1 and current_question:
                            qa_pairs[current_question] = current_answer
                            current_question = ""
                            current_answer = ""
                        current_question += text
                        prev = 0
                    elif size == 12.0 and color == "#00ff00":
                        current_answer += text
                        prev = 1

    if current_question:
        qa_pairs[current_question] = current_answer

    doc.close()
    return qa_pairs


def main() -> None:
    pdf_files = glob.glob("*.pdf")
    if not pdf_files:
        print("Keine PDF-Dateien im aktuellen Ordner gefunden.")
        return

    print(f"Verarbeite {len(pdf_files)} PDF(s): {pdf_files}")

    pairs: dict[str, str] = {}
    for pdf_path in pdf_files:
        extracted = extract_qa_from_pdf(pdf_path)
        print(f"  {pdf_path}: {len(extracted)} Frage-Antwort-Paare gefunden")
        pairs.update(extracted)

    tmp = CSV_FILE + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(pairs.items())
    os.replace(tmp, CSV_FILE)

    print(f"\n{len(pairs)} Frage-Antwort-Paare in {CSV_FILE} geschrieben")


if __name__ == "__main__":
    main()
