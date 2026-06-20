import json
import csv
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

CSV_PATH = Path("daily_debates.csv")

def int_to_roman(num):
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syb = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num

# Thread-local storage for requests.Session
thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
        thread_local.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return thread_local.session

def fetch_debate_pdf_with_retry(item, max_retries=3):
    session = get_session()
    loksabha = item["loksabha"]
    session_no = item["session"]
    date_str = item["date_str"]  # DD/MM/YYYY
    
    # Convert date to MM/DD/YYYY format for API query
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        api_date_str = dt.strftime("%m/%d/%Y")
    except Exception:
        return item, "", 0
        
    url = f"https://sansad.in/api_ls/debate/text-of-debate?loksabha={loksabha}&sessionNo={session_no}&debateDate={api_date_str}&locale=en"
    
    attempts = 0
    for attempt in range(1, max_retries + 1):
        attempts += 1
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                pdf_url = data.get("pdfUrl", "")
                return item, pdf_url, attempts
        except Exception:
            if attempt < max_retries:
                time.sleep(1)
            
    return item, "", attempts

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    if iteration == total: 
        print()

def save_csv(records_dict):
    # Sort records by date descending
    sorted_records = sorted(records_dict.values(), key=lambda x: x["date"], reverse=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["date", "lok_sabha", "session", "pdf_url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rec in sorted_records:
            writer.writerow({
                "date": rec["date"],
                "lok_sabha": rec["lok_sabha"],
                "session": rec["session"],
                "pdf_url": rec["pdf_url"]
            })

def print_statistics(records_dict, api_calls):
    total_sitting = len(records_dict)
    pdf_found = sum(1 for r in records_dict.values() if r.get("pdf_url"))
    missing_pdf = total_sitting - pdf_found
    
    dates = list(records_dict.keys())
    earliest = min(dates) if dates else "N/A"
    latest = max(dates) if dates else "N/A"
    
    print("\n=== Statistics ===")
    print(f"Total sitting dates discovered: {total_sitting}")
    print(f"Total API calls attempted: {api_calls}")
    print(f"Total PDF URLs found: {pdf_found}")
    print(f"Total missing PDF URLs: {missing_pdf}")
    print(f"Earliest date: {earliest}")
    print(f"Latest date: {latest}")

def print_validation():
    if not CSV_PATH.exists():
        print("Error: CSV file was not written.")
        return
        
    with open(CSV_PATH, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)
        rows = []
        for _ in range(10):
            row = next(reader, None)
            if row is None:
                break
            rows.append(row)
            
    # Count rows in CSV
    row_count = sum(1 for _ in csv.reader(open(CSV_PATH, 'r', encoding='utf-8'))) - 1
            
    print(f"\nRows written to CSV: {row_count}")
    print("\nFirst 10 rows in CSV:")
    if header:
        print(",".join(header))
    for r in rows:
        print(",".join(r))

def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # Resume Support: load existing records from CSV
    existing_data = {}
    if CSV_PATH.exists():
        try:
            with open(CSV_PATH, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_data[row["date"]] = row
            print(f"Loaded {len(existing_data)} existing records from {CSV_PATH}.")
        except Exception as e:
            print(f"Warning: Could not load existing CSV: {e}")

    print("Fetching Lok Sabha session calendar...")
    url_dates = "https://sansad.in/api_ls/business/AllLoksabhaAndSessionDates"
    try:
        r = requests.get(url_dates, headers=headers, timeout=15)
        r.raise_for_status()
        dates_data = r.json()
    except Exception as e:
        print(f"Error fetching session dates: {e}")
        sys.exit(1)
        
    # Filter dates from 2019-present
    dates_to_crawl = []
    for ls_item in dates_data:
        ls_num = ls_item.get("loksabha")
        for session_info in ls_item.get("sessions", []):
            session_no = session_info.get("sessionNo")
            session_roman = int_to_roman(session_no)
            for d_str in session_info.get("dates", []):
                try:
                    dt = datetime.strptime(d_str, "%d/%m/%Y")
                    if dt.year >= 2019:
                        dates_to_crawl.append({
                            "date_str": d_str,
                            "date_iso": dt.strftime("%Y-%m-%d"),
                            "loksabha": ls_num,
                            "session": session_roman
                        })
                except Exception:
                    pass
                    
    total_discovered = len(dates_to_crawl)
    
    print("\n==================================================")
    print(f"Total daily debate records discovered (2019-present): {total_discovered}")
    print("Comparison against the 6658-item DSpace collection:")
    print("  - The 6658-item DSpace collection contains historical records spanning from 1952 to present.")
    print(f"  - The official web API calendar yields {total_discovered} debate days from 2019 to present.")
    print("==================================================\n")
    
    # Separate skipped vs to-query
    to_query = []
    skipped_count = 0
    final_records = {}
    
    for item in dates_to_crawl:
        date_iso = item["date_iso"]
        # Skip if already in CSV with a non-empty pdf_url
        if date_iso in existing_data and existing_data[date_iso].get("pdf_url"):
            final_records[date_iso] = {
                "date": date_iso,
                "lok_sabha": existing_data[date_iso].get("lok_sabha"),
                "session": existing_data[date_iso].get("session"),
                "pdf_url": existing_data[date_iso].get("pdf_url")
            }
            skipped_count += 1
        else:
            to_query.append(item)
            
    total_to_query = len(to_query)
    completed = 0
    api_calls_count = 0
    new_rows_since_save = 0
    write_lock = threading.Lock()
    
    print(f"Already cached (skipped): {skipped_count}")
    print(f"To query: {total_to_query}")
    
    if total_to_query > 0:
        print_progress_bar(0, total_to_query, prefix='Progress:', suffix='Complete', length=40)
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(fetch_debate_pdf_with_retry, item): item for item in to_query}
            
            for future in as_completed(futures):
                item, pdf_url, attempts = future.result()
                
                with write_lock:
                    completed += 1
                    api_calls_count += attempts
                    new_rows_since_save += 1
                    
                    final_records[item["date_iso"]] = {
                        "date": item["date_iso"],
                        "lok_sabha": item["loksabha"],
                        "session": item["session"],
                        "pdf_url": pdf_url
                    }
                    
                    # Save incrementally every 50 rows
                    if new_rows_since_save >= 50:
                        save_csv(final_records)
                        new_rows_since_save = 0
                        
                    print_progress_bar(completed, total_to_query, prefix='Progress:', suffix=f'({completed}/{total_to_query})', length=40)
        
        # Save any final remaining records
        if new_rows_since_save > 0:
            save_csv(final_records)
    else:
        # Re-save to enforce column format
        save_csv(final_records)
        
    print_statistics(final_records, api_calls_count)
    print_validation()

if __name__ == "__main__":
    main()
