import json
import sys
import re
import threading
from pathlib import Path
import fitz  # PyMuPDF
from concurrent.futures import ThreadPoolExecutor, as_completed

PDF_DIR = Path("downloads/debates")
CORPUS_DIR = Path("corpus/raw_text")

def process_pdf(pdf_path, total, lock, stats):
    date_str = pdf_path.stem  # YYYY-MM-DD
    year_str = date_str.split("-")[0]
    
    out_dir = CORPUS_DIR / year_str
    txt_path = out_dir / f"{date_str}.txt"
    json_path = out_dir / f"{date_str}.json"
    
    # Resume/deduplication check: skip if output txt and json both exist and are not empty
    if txt_path.exists() and json_path.exists():
        if txt_path.stat().st_size > 0 and json_path.stat().st_size > 0:
            try:
                meta = json.loads(json_path.read_text(encoding="utf-8"))
                with lock:
                    stats["completed"] += 1
                    stats["pages"] += meta.get("pages", 0)
                    stats["words"] += meta.get("words", 0)
                    stats["characters"] += meta.get("characters", 0)
                    if meta.get("words", 0) == 0:
                        stats["empty"] += 1
                    if meta.get("suspected_scanned"):
                        stats["suspected_scanned"] += 1
                    stats["skipped"] += 1
                    print(f"Processed {stats['completed']} / {total} PDFs")
                return
            except Exception:
                pass  # Reprocess if JSON metadata load fails
                
    # Process PDF file using fitz context manager
    try:
        with fitz.open(pdf_path) as doc:
            text_parts = []
            for idx, page in enumerate(doc):
                # Custom page break marker with clear spacing
                text_parts.append(f"\n\n===== PAGE {idx + 1} =====\n\n")
                page_text = page.get_text()
                text_parts.append(page_text)
                
            full_text = "".join(text_parts).strip()
            pages = len(doc)
            characters = len(full_text)
            
            # Robust word count using \S+ regex
            words = len(re.findall(r"\S+", full_text))
            
            # Save extracted text
            out_dir.mkdir(parents=True, exist_ok=True)
            txt_path.write_text(full_text, encoding="utf-8")
            
            # Metadata construction with file path and stats
            meta = {
                "date": date_str,
                "pages": pages,
                "characters": characters,
                "words": words,
                "source_pdf": str(pdf_path)
            }
            
            # Scanned / Image-only PDF detection
            if words < 100:
                meta["suspected_scanned"] = True
                
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            
        with lock:
            stats["completed"] += 1
            stats["pages"] += pages
            stats["words"] += words
            stats["characters"] += characters
            if words == 0:
                stats["empty"] += 1
            if words < 100:
                stats["suspected_scanned"] += 1
            stats["processed"] += 1
            print(f"Processed {stats['completed']} / {total} PDFs")
            
    except Exception as e:
        with lock:
            stats["completed"] += 1
            stats["failed"] += 1
            print(f"Failed to process {pdf_path.name}: {e}")
            print(f"Processed {stats['completed']} / {total} PDFs")

def main():
    if not PDF_DIR.exists():
        print(f"Error: PDF directory {PDF_DIR} does not exist.")
        sys.exit(1)
        
    pdf_paths = sorted(list(PDF_DIR.glob("**/*.pdf")))
    total_pdfs = len(pdf_paths)
    
    print(f"Found {total_pdfs} PDF files to process.")
    
    stats = {
        "completed": 0,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "pages": 0,
        "words": 0,
        "characters": 0,
        "empty": 0,
        "suspected_scanned": 0
    }
    
    lock = threading.Lock()
    
    # Process files concurrently using 8 threads
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_pdf, path, total_pdfs, lock, stats) for path in pdf_paths]
        for future in as_completed(futures):
            pass
            
    print("\n--- Final Statistics ---")
    print(f"Total PDFs: {total_pdfs}")
    print(f"Total pages: {stats['pages']}")
    print(f"Total words: {stats['words']}")
    print(f"Total characters: {stats['characters']}")
    print(f"Skipped (cached): {stats['skipped']}")
    print(f"Processed (extracted): {stats['processed']}")
    print(f"Empty PDFs: {stats['empty']}")
    print(f"Suspected Scanned PDFs: {stats['suspected_scanned']}")
    print(f"Failed: {stats['failed']}")

if __name__ == "__main__":
    main()
