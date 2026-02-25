import os
import logging
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
import threading

# --- 1. CONFIGURATION ---
BASE_URL = "https://physionet.org/files/ecg-arrhythmia/1.0.0/"
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "ecg-arrhythmia")
MAX_CRAWL_WORKERS = 10   # Threads for finding links
MAX_DL_WORKERS = 15      # Threads for downloading files

# --- 2. SETUP ADVANCED DUAL LOGGING ---
# We write verbose logs to a file so we don't break the terminal progress bar
log_file = os.path.join(DOWNLOAD_DIR, "download_debug.log")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logger = logging.getLogger("PhysioNetCrawler")
logger.setLevel(logging.DEBUG)

# File handler (Verbose / Debug)
fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(threadName)s: %(message)s'))
logger.addHandler(fh)

def create_session():
    """Create a robust requests session with automatic retry logic."""
    session = requests.Session()
    # Heavily increased retries to survive 90k+ requests
    retries = Retry(total=10, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=MAX_DL_WORKERS, pool_maxsize=MAX_DL_WORKERS))
    return session

def fetch_directory_contents(session, url):
    """Fetch all links in a single directory."""
    logger.debug(f"Scanning directory: {url}")
    files, directories = [], []
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href')
            if href in ['../', '?C=N;O=D', '?C=M;O=A', '?C=S;O=A', '?C=D;O=A'] or href.startswith('?'):
                continue
                
            full_url = urljoin(url, href)
            if href.endswith('/'):
                directories.append(full_url)
            else:
                files.append(full_url)
    except Exception as e:
        logger.error(f"Failed to scan {url}: {e}")
        
    return files, directories

def concurrent_crawl(session, start_url):
    """Uses thread pooling to rapidly map the entire 90k+ file directory structure."""
    print("Mapping directory structure... (This may take a few minutes for 90,000+ files)")
    all_files = []
    directories_to_scan = [start_url]
    
    with ThreadPoolExecutor(max_workers=MAX_CRAWL_WORKERS) as executor:
        while directories_to_scan:
            futures = {executor.submit(fetch_directory_contents, session, d): d for d in directories_to_scan}
            directories_to_scan = [] # Reset for the next depth level
            
            for future in as_completed(futures):
                files, subdirs = future.result()
                all_files.extend(files)
                directories_to_scan.extend(subdirs)
                
    return all_files

def download_file(session, file_url, save_dir, progress_bar):
    """Download a single file and update the progress bar."""
    relative_path = file_url.replace(BASE_URL, "")
    local_path = os.path.join(save_dir, os.path.normpath(relative_path))
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    # Fast-Resume: Skip if file exists and has data (ignores size check to save HTTP requests)
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        logger.debug(f"Skipping already existing file: {relative_path}")
        progress_bar.update(1)
        return True

    logger.info(f"Downloading: {relative_path}")
    try:
        response = session.get(file_url, stream=True, timeout=20)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=16384): # Larger chunk size for speed
                if chunk:
                    f.write(chunk)
        logger.debug(f"Successfully saved: {local_path}")
        progress_bar.update(1)
        return True
    except Exception as e:
        logger.error(f"Error downloading {file_url}: {e}")
        return False

def main():
    start_time = time.time()
    print(f"--- PhysioNet Advanced Concurrent Downloader ---")
    print(f"Check '{log_file}' for deep verbose logs.\n")
    
    session = create_session()
    
    # 1. Map the whole site concurrently
    file_urls = concurrent_crawl(session, BASE_URL)
    total_files = len(file_urls)
    print(f"\nDiscovered {total_files} files. Starting download phase...")
    logger.info(f"Total files discovered: {total_files}")
    
    if total_files == 0:
        print("No files found. Check your internet connection or the BASE_URL.")
        return

    # 2. Download concurrently with a progress bar
    with tqdm(total=total_files, desc="Downloading Dataset", unit="file") as progress_bar:
        with ThreadPoolExecutor(max_workers=MAX_DL_WORKERS) as executor:
            futures = [
                executor.submit(download_file, session, url, DOWNLOAD_DIR, progress_bar) 
                for url in file_urls
            ]
            
            for future in as_completed(futures):
                pass # Exceptions are logged inside download_file
                
    elapsed_time = time.time() - start_time
    print(f"\nProcess complete in {elapsed_time/60:.2f} minutes!")
    print(f"Check {DOWNLOAD_DIR} for your files.")

if __name__ == "__main__":
    main()