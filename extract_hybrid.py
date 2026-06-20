import os
# Set OMP_THREAD_LIMIT globally to avoid Tesseract thread thrashing
os.environ["OMP_THREAD_LIMIT"] = "1"

import re
import sys
import json
import io
import argparse
import threading
from pathlib import Path
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

PDF_DIR = Path("downloads/debates")
CORPUS_DIR = Path("corpus/final")

def process_pdf(pdf_path, total, lock, stats, scale):
    date_str = pdf_path.stem  # YYYY-MM-DD
    year_str = date_str.split("-")[0]
    
    out_dir = CORPUS_DIR / year_str
    txt_path = out_dir / f"{date_str}.txt"
    json_path = out_dir / f"{date_str}.json"
    
    # Resume support: skip if output txt and json both exist and are valid (non-empty and valid JSON)
    if txt_path.exists() and json_path.exists():
        if txt_path.stat().st_size > 0 and json_path.stat().st_size > 0:
            try:
                meta = json.loads(json_path.read_text(encoding="utf-8"))
                # Basic schema validation check
                required_keys = {"date", "source_pdf", "pages", "pdf_pages", "ocr_pages", "words", "characters"}
                if required_keys.issubset(meta.keys()):
                    with lock:
                        stats["completed"] += 1
                        stats["skipped"] += 1
                        stats["pages"] += meta["pages"]
                        stats["pdf_pages"] += meta["pdf_pages"]
                        stats["ocr_pages"] += meta["ocr_pages"]
                        stats["words"] += meta["words"]
                        stats["characters"] += meta["characters"]
                    return
            except Exception:
                pass  # Re-process if metadata JSON is invalid
                
    try:
        pdf_pages_count = 0
        ocr_pages_count = 0
        page_texts = []
        
        with fitz.open(pdf_path) as doc:
            total_doc_pages = len(doc)
            
            for idx, page in enumerate(doc):
                # 1. Extract raw text from page
                raw_text = page.get_text()
                
                # 2. Count characters belonging to Devanagari block
                devanagari_chars = len(re.findall(r"[\u0900-\u097F]", raw_text))
                
                # 3. Check condition
                if devanagari_chars > 0:
                    ocr_pages_count += 1
                    # Render page at custom DPI (e.g. 2x2 = 144 DPI)
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                    
                    # Convert to PIL image directly in memory
                    img_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_bytes))
                    
                    # Run OCR directly in memory using pytesseract
                    page_text = pytesseract.image_to_string(image, lang="hin+eng")
                else:
                    pdf_pages_count += 1
                    page_text = raw_text
                
                page_texts.append(page_text)
                
        # Format output text: join pages with standard marker format
        text_parts = []
        for idx, p_text in enumerate(page_texts):
            text_parts.append(f"===== PAGE {idx + 1} =====")
            text_parts.append(p_text)
            
        full_text = "\n\n".join(text_parts).strip()
        words = len(re.findall(r"\S+", full_text))
        characters = len(full_text)
        
        # Save output text
        out_dir.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(full_text, encoding="utf-8")
        
        # Save metadata
        meta = {
            "date": date_str,
            "source_pdf": str(pdf_path),
            "pages": total_doc_pages,
            "pdf_pages": pdf_pages_count,
            "ocr_pages": ocr_pages_count,
            "words": words,
            "characters": characters
        }
        json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        
        with lock:
            stats["completed"] += 1
            stats["processed"] += 1
            stats["pages"] += total_doc_pages
            stats["pdf_pages"] += pdf_pages_count
            stats["ocr_pages"] += ocr_pages_count
            stats["words"] += words
            stats["characters"] += characters
            
    except Exception as e:
        with lock:
            stats["completed"] += 1
            stats["failed"] += 1
            # We use tqdm.write to print errors without breaking the progress bar
            tqdm.write(f"Failed to process {pdf_path.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Hybrid text extraction pipeline with selective OCR")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent PDF threads")
    parser.add_argument("--scale", type=float, default=2.0, help="DPI scaling factor for OCR rendering")
    args = parser.parse_args()

    if not PDF_DIR.exists():
        print(f"Error: PDF directory {PDF_DIR} does not exist.")
        sys.exit(1)
        
    pdf_paths = sorted(list(PDF_DIR.glob("**/*.pdf")))
    total_pdfs = len(pdf_paths)
    
    print(f"Found {total_pdfs} PDF files to process.")
    print(f"Configuration: workers={args.workers}, scale={args.scale}")
    
    stats = {
        "completed": 0,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "pages": 0,
        "pdf_pages": 0,
        "ocr_pages": 0,
        "words": 0,
        "characters": 0
    }
    
    lock = threading.Lock()
    
    # Process files concurrently using configured threads and display tqdm progress bar
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process_pdf, path, total_pdfs, lock, stats, args.scale) for path in pdf_paths]
        
        with tqdm(total=total_pdfs, desc="Extracting Corpus", unit="pdf") as pbar:
            for future in as_completed(futures):
                pbar.update(1)
                with lock:
                    pbar.set_postfix({
                        "ok": stats["processed"],
                        "skip": stats["skipped"],
                        "fail": stats["failed"]
                    })
            
    print("\n--- Final Statistics ---")
    print(f"Total PDFs: {total_pdfs}")
    print(f"Total pages: {stats['pages']}")
    print(f"PDF pages: {stats['pdf_pages']}")
    print(f"OCR pages: {stats['ocr_pages']}")
    print(f"Total words: {stats['words']}")
    print(f"Total characters: {stats['characters']}")
    print(f"Skipped (cached): {stats['skipped']}")
    print(f"Processed: {stats['processed']}")
    print(f"Failed: {stats['failed']}")

if __name__ == "__main__":
    main()
