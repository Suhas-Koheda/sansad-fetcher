import json
import re
import random
from pathlib import Path

CORPUS_DIR = Path("corpus/raw_text")

def analyze_corpus():
    json_files = list(CORPUS_DIR.glob("**/*.json"))
    if not json_files:
        print("No metadata JSON files found in the corpus.")
        return

    data = []
    for jf in json_files:
        try:
            meta = json.loads(jf.read_text(encoding="utf-8"))
            data.append(meta)
        except Exception as e:
            print(f"Error reading {jf}: {e}")

    total_files = len(data)
    
    # Sort by words
    sorted_by_words = sorted(data, key=lambda x: x["words"])
    sorted_by_pages = sorted(data, key=lambda x: x["pages"])

    # Largest / Smallest
    largest_by_words = sorted_by_words[-1]
    smallest_by_words = sorted_by_words[0]
    
    # Filter out empty/scanned PDFs to find the smallest valid debate day
    non_empty_days = [d for d in data if d.get("words", 0) >= 100]
    sorted_non_empty = sorted(non_empty_days, key=lambda x: x["words"])
    smallest_valid = sorted_non_empty[0] if sorted_non_empty else None

    # Averages
    total_pages = sum(d["pages"] for d in data)
    total_words = sum(d["words"] for d in data)
    total_chars = sum(d["characters"] for d in data)

    avg_pages = total_pages / total_files
    avg_words = total_words / total_files

    print("=== Corpus Analysis Summary ===")
    print(f"Total Debate Days: {total_files}")
    print(f"Total Pages:       {total_pages}")
    print(f"Total Words:       {total_words}")
    print(f"Total Characters:  {total_chars}")
    print(f"Average Pages/Day: {avg_pages:.2f}")
    print(f"Average Words/Day: {avg_words:.2f}")
    print()
    print("=== Largest Debate Day (by words) ===")
    print(f"Date:       {largest_by_words['date']}")
    print(f"Pages:      {largest_by_words['pages']}")
    print(f"Words:      {largest_by_words['words']}")
    print(f"Source PDF: {largest_by_words['source_pdf']}")
    print()
    print("=== Smallest Debate Day (overall) ===")
    print(f"Date:       {smallest_by_words['date']}")
    print(f"Pages:      {smallest_by_words['pages']}")
    print(f"Words:      {smallest_by_words['words']}")
    print(f"Source PDF: {smallest_by_words['source_pdf']}")
    print(f"Scanned?:   {smallest_by_words.get('suspected_scanned', False)}")
    print()
    if smallest_valid:
        print("=== Smallest Valid Debate Day (words >= 100) ===")
        print(f"Date:       {smallest_valid['date']}")
        print(f"Pages:      {smallest_valid['pages']}")
        print(f"Words:      {smallest_valid['words']}")
        print(f"Source PDF: {smallest_valid['source_pdf']}")
        print()

    # Manually inspect 5 random valid files
    print("=== Random 5-File Inspection ===")
    valid_files = [jf for jf in json_files if json.loads(jf.read_text(encoding="utf-8")).get("words", 0) >= 100]
    sampled_jfs = random.sample(valid_files, min(5, len(valid_files)))

    # Regex pattern to match speaker lines
    # Usually uppercase words followed by a colon: "HON. SPEAKER:" or "SHRI RAHUL GANDHI:"
    speaker_pattern = re.compile(
        r"^(?:"
        r"HON\.\s+[A-Z\s]+|"
        r"SHRI\s+[A-Z\s\.]+|"
        r"SMT\.\s+[A-Z\s\.]+|"
        r"DR\.\s+[A-Z\s\.]+|"
        r"KUMARI\s+[A-Z\s\.]+|"
        r"PROF\.\s+[A-Z\s\.]+|"
        r"[A-Z]{3,}(?:\s+[A-Z]+)*"
        r")\s*:", 
        re.MULTILINE
    )

    for idx, jf in enumerate(sampled_jfs):
        meta = json.loads(jf.read_text(encoding="utf-8"))
        date = meta["date"]
        txt_path = CORPUS_DIR / jf.parent.name / f"{date}.txt"
        
        print(f"\n[{idx + 1}] Date: {date} (Pages: {meta['pages']}, Words: {meta['words']})")
        print(f"File Path: {txt_path}")
        
        if txt_path.exists():
            text = txt_path.read_text(encoding="utf-8")
            
            # Find speakers in the text
            matches = []
            for line in text.splitlines():
                line = line.strip()
                if speaker_pattern.match(line):
                    matches.append(line)
                    if len(matches) >= 5:
                        break
                        
            print("Detected Speaker Lines Sample:")
            if matches:
                for match in matches:
                    print(f"  - {match}")
            else:
                print("  No clear uppercase speaker: lines detected. Printing first 5 non-empty lines instead:")
                non_empty = [line.strip() for line in text.splitlines() if line.strip()][:5]
                for line in non_empty:
                    print(f"  - {line}")
        else:
            print("  Text file not found.")

if __name__ == "__main__":
    analyze_corpus()
