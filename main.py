import csv
import glob
import re
from pathlib import Path

import fitz

# --- Konfiguration ---
MODE = "folder"        # "folder" = alle PDFs im Ordner, "single" = nur eine Datei
SINGLE_PDF = "Regel+17.pdf"
CSV_FILE = "output.csv"
# ---------------------


def strip_question_number(question: str) -> str:
    """Entfernt 'Frage' + 4-5 Ziffern vom Anfang für den Duplikat-Vergleich."""
    return re.sub(r'^Frage\d{4,5}\s*', '', question)


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


def load_existing_csv(csv_file: str) -> tuple[dict[str, str], dict[str, str]]:
    """Gibt (original_key→answer, normalized_key→original_key) zurück."""
    existing: dict[str, str] = {}
    norm_to_original: dict[str, str] = {}
    if Path(csv_file).exists():
        with open(csv_file, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) == 2:
                    existing[row[0]] = row[1]
                    norm_to_original[strip_question_number(row[0])] = row[0]
    return existing, norm_to_original


def main() -> None:
    if MODE == "folder":
        pdf_files = glob.glob("*.pdf")
        if not pdf_files:
            print("Keine PDF-Dateien im aktuellen Ordner gefunden.")
            return
    else:
        pdf_files = [SINGLE_PDF]

    print(f"Verarbeite {len(pdf_files)} PDF(s): {pdf_files}")

    new_pairs: dict[str, str] = {}
    for pdf_path in pdf_files:
        pairs = extract_qa_from_pdf(pdf_path)
        print(f"  {pdf_path}: {len(pairs)} Frage-Antwort-Paare gefunden")
        new_pairs.update(pairs)

    existing, norm_to_original = load_existing_csv(CSV_FILE)

    added = 0
    updated = 0
    unchanged = 0
    changed = False

    for question, answer in new_pairs.items():
        norm = strip_question_number(question)
        original_key = norm_to_original.get(norm)

        if original_key is None:
            existing[question] = answer
            norm_to_original[norm] = question
            added += 1
            changed = True
        elif existing[original_key] != answer:
            existing[original_key] = answer
            updated += 1
            changed = True
        else:
            unchanged += 1

    if changed:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(existing.items())
        print(f"\nCSV aktualisiert: {added} neu, {updated} überschrieben, {unchanged} unverändert")
    else:
        print(f"\nKeine Änderungen: {unchanged} Paare bereits aktuell")


if __name__ == "__main__":
    main()
