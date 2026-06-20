import re
import json
import random
from pathlib import Path

CORPUS_DIR = Path("corpus/final")

def sample_validation():
    json_files = list(CORPUS_DIR.glob("**/*.json"))
    if not json_files:
        print("No metadata JSON files found in corpus/final.")
        return
        
    sampled_jfs = random.sample(json_files, min(20, len(json_files)))
    
    for idx, jf in enumerate(sampled_jfs):
        try:
            meta = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error reading JSON {jf}: {e}")
            continue
            
        date = meta["date"]
        ocr_count = meta["ocr_pages"]
        txt_path = CORPUS_DIR / jf.parent.name / f"{date}.txt"
        
        print(f"\n=================== SAMPLE {idx + 1} / 20 ===================")
        print(f"Date:      {date}")
        print(f"OCR Pages: {ocr_count} / {meta['pages']}")
        
        if not txt_path.exists():
            print("Text file missing!")
            continue
            
        text = txt_path.read_text(encoding="utf-8")
        
        # Split text into paragraphs
        # Paragraphs are usually separated by double newlines or multiple newlines
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        
        # Filter page markers so we don't treat them as paragraphs
        paragraphs = [p for p in paragraphs if not re.match(r"^===== PAGE \d+ =====", p)]
        
        first_hindi_p = None
        first_english_p = None
        
        devanagari_re = re.compile(r"[\u0900-\u097F]")
        latin_re = re.compile(r"[a-zA-Z]")
        
        for p in paragraphs:
            # Check for Hindi (has Devanagari)
            if not first_hindi_p and devanagari_re.search(p):
                first_hindi_p = p
            # Check for English (has Latin, NO Devanagari)
            if not first_english_p and latin_re.search(p) and not devanagari_re.search(p):
                first_english_p = p
                
            if first_hindi_p and first_english_p:
                break
                
        print("\n[First Hindi Paragraph]:")
        if first_hindi_p:
            # Print first 200 chars or full paragraph
            print(first_hindi_p[:400] + ("..." if len(first_hindi_p) > 400 else ""))
        else:
            print("(None found)")
            
        print("\n[First English Paragraph]:")
        if first_english_p:
            print(first_english_p[:400] + ("..." if len(first_english_p) > 400 else ""))
        else:
            print("(None found)")

if __name__ == "__main__":
    sample_validation()
