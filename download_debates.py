import json
import csv
import sys
import time
import threading
from pathlib import Path
import requests
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set global socket timeout to prevent indefinite hangs in stream chunk reading
socket.setdefaulttimeout(30.0)

CSV_PATH = Path("daily_debates.csv")
DOWNLOADS_DIR = Path("downloads/debates")

# Thread-local storage for requests.Session
thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        thread_local.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return thread_local.session

def download_file(row, total, lock, stats):
    session = get_session()
    
    date_str = row["date"]
    lok_sabha = row["lok_sabha"]
    session_no = row["session"]
    pdf_url = row["pdf_url"]
    
    # Extract year
    year = date_str.split("-")[0]
    
    dest_dir = DOWNLOADS_DIR / year
    pdf_path = dest_dir / f"{date_str}.pdf"
    json_path = dest_dir / f"{date_str}.json"
    
    # Resume check: skip if PDF exists (create metadata JSON if missing)
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        if not (json_path.exists() and json_path.stat().st_size > 0):
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                meta = {
                    "date": date_str,
                    "lok_sabha": lok_sabha,
                    "session": session_no,
                    "pdf_url": pdf_url
                }
                json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            except Exception:
                pass
        with lock:
            stats["skipped"] += 1
            stats["completed"] += 1
            print(f"Downloaded {stats['completed']} / {total}")
        return
            
    # Download with retry
    max_retries = 3
    success = False
    bytes_downloaded = 0
    
    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(pdf_url, timeout=30, stream=True)
            if r.status_code == 200:
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Write PDF
                with open(pdf_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                # Write JSON metadata
                meta = {
                    "date": date_str,
                    "lok_sabha": lok_sabha,
                    "session": session_no,
                    "pdf_url": pdf_url
                }
                json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                
                bytes_downloaded = pdf_path.stat().st_size
                success = True
                break
        except Exception:
            if attempt < max_retries:
                time.sleep(1)
                
    with lock:
        stats["completed"] += 1
        if success:
            stats["downloaded"] += 1
            stats["total_bytes"] += bytes_downloaded
        else:
            stats["failed"] += 1
        print(f"Downloaded {stats['completed']} / {total}")

def main():
    if not CSV_PATH.exists():
        print(f"Error: CSV file {CSV_PATH} not found.")
        sys.exit(1)
        
    # Read rows
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            
    total_rows = len(rows)
    
    # Filter rows with pdf_url
    valid_rows = [r for r in rows if r.get("pdf_url")]
    total_valid = len(valid_rows)
    
    print(f"Total rows read: {total_rows}")
    print(f"Rows with PDF URLs: {total_valid}")
    
    if total_valid == 0:
        print("No valid PDF URLs to download.")
        return
        
    stats = {
        "completed": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "total_bytes": 0
    }
    
    lock = threading.Lock()
    
    # Concurrently download PDFs with 24 workers
    print(f"Starting downloads using 24 concurrent workers...")
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = [executor.submit(download_file, row, total_valid, lock, stats) for row in valid_rows]
        for future in as_completed(futures):
            pass
            
    # Completion statistics
    print("\n--- Completion Summary ---")
    print(f"Total rows: {total_rows}")
    print(f"Rows with PDF URLs: {total_valid}")
    print(f"Downloaded files: {stats['downloaded']}")
    print(f"Skipped files: {stats['skipped']}")
    print(f"Failed files: {stats['failed']}")
    print(f"Total bytes downloaded: {stats['total_bytes']}")
    
    # Verify downloaded PDFs
    pdf_files = sorted(list(DOWNLOADS_DIR.glob("**/*.pdf")))
    if pdf_files:
        earliest_pdf = pdf_files[0]
        latest_pdf = pdf_files[-1]
        
        print("\n--- Verification ---")
        print(f"Earliest PDF exists: {earliest_pdf.name} ({earliest_pdf.stat().st_size} bytes) - Path: {earliest_pdf}")
        print(f"Latest PDF exists: {latest_pdf.name} ({latest_pdf.stat().st_size} bytes) - Path: {latest_pdf}")
        print(f"Report earliest date: {earliest_pdf.stem}")
        print(f"Report latest date: {latest_pdf.stem}")
    else:
        print("\nNo downloaded PDF files found for verification.")

if __name__ == "__main__":
    main()
