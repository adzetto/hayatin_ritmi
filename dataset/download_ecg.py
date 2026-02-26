"""
download_ecg.py  –  Multi-Dataset 12-Lead ECG Downloader
=========================================================
Downloads publicly available 12-lead ECG datasets from PhysioNet.

Supported datasets (all Open Access):
  1. sph          – Chapman-Shaoxing/SPH 12-Lead ECG Arrhythmia   (45,152 records)
  2. ptb-xl       – PTB-XL Electrocardiography Dataset            (21,799 records)
  3. cpsc2018     – CPSC 2018 + Extra (CinC Challenge 2021)       (10,330 records)
  4. georgia      – Georgia 12-Lead ECG Challenge (CinC 2021)     (10,344 records)
  5. chapman-ningbo – Chapman-Shaoxing + Ningbo (CinC 2021)       (45,152 records)
  6. ptb          – PTB Diagnostic ECG Database                    (   549 records)
  7. incart       – St Petersburg INCART 12-lead Arrhythmia       (    75 records)
  8. ludb         – Lobachevsky University ECG Database            (   200 records)

Usage:
  python download_ecg.py                       # Interactive menu
  python download_ecg.py --dataset sph         # Download specific dataset
  python download_ecg.py --dataset all         # Download everything
  python download_ecg.py --list                # List available datasets
"""

import os
import sys
import argparse
import logging
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# ─── PATHS ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── DATASET REGISTRY ────────────────────────────────────────────────────────
# Each entry: key -> (base_url, local_folder_name, description, approx_size)
DATASETS = {
    "sph": {
        "url": "https://physionet.org/files/ecg-arrhythmia/1.0.0/",
        "dir": "ecg-arrhythmia",
        "desc": "Chapman-Shaoxing/SPH 12-Lead ECG Arrhythmia (45,152 records, 500Hz)",
        "size": "~7 GB",
        "records": 45152,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT arrhythmia codes",
    },
    "ptb-xl": {
        "url": "https://physionet.org/files/ptb-xl/1.0.3/",
        "dir": "ptb-xl",
        "desc": "PTB-XL Large ECG Dataset (21,799 records, 500Hz, 71 SCP-ECG statements)",
        "size": "~3.0 GB",
        "records": 21799,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SCP-ECG diagnostic/form/rhythm statements",
    },
    "cpsc2018": {
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018/",
        "dir": "cpsc2018",
        "desc": "CPSC 2018 China 12-Lead ECG Challenge (6,877 records, 500Hz)",
        "size": "~1.0 GB",
        "records": 6877,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT codes",
    },
    "cpsc2018-extra": {
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018_extra/",
        "dir": "cpsc2018-extra",
        "desc": "CPSC 2018 Extra – Unused CPSC 2018 data (3,453 records, 500Hz)",
        "size": "~0.5 GB",
        "records": 3453,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT codes",
    },
    "georgia": {
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/georgia/",
        "dir": "georgia",
        "desc": "Georgia 12-Lead ECG Challenge Database (10,344 records, 500Hz)",
        "size": "~1.5 GB",
        "records": 10344,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT codes",
    },
    "chapman-shaoxing": {
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/chapman_shaoxing/",
        "dir": "chapman-shaoxing",
        "desc": "Chapman-Shaoxing 12-Lead ECG (10,247 records, 500Hz) [CinC 2021]",
        "size": "~1.5 GB",
        "records": 10247,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT codes",
    },
    "ningbo": {
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/ningbo/",
        "dir": "ningbo",
        "desc": "Ningbo First Hospital 12-Lead ECG (34,905 records, 500Hz) [CinC 2021]",
        "size": "~5 GB",
        "records": 34905,
        "leads": 12,
        "freq_hz": 500,
        "labels": "SNOMED-CT codes",
    },
    "ptb": {
        "url": "https://physionet.org/files/ptbdb/1.0.0/",
        "dir": "ptb-diagnostic",
        "desc": "PTB Diagnostic ECG Database (549 records, 15-lead, 1000Hz)",
        "size": "~1.7 GB",
        "records": 549,
        "leads": 15,
        "freq_hz": 1000,
        "labels": "MI, cardiomyopathy, BBB, dysrhythmia, hypertrophy, healthy",
    },
    "incart": {
        "url": "https://physionet.org/files/incartdb/1.0.0/",
        "dir": "incart",
        "desc": "St Petersburg INCART 12-lead Arrhythmia (75 records, 257Hz, 30min Holter)",
        "size": "~794 MB",
        "records": 75,
        "leads": 12,
        "freq_hz": 257,
        "labels": "Beat annotations (175K+ beats), ischemia, arrhythmia",
    },
    "ludb": {
        "url": "https://physionet.org/files/ludb/1.0.1/",
        "dir": "ludb",
        "desc": "Lobachevsky University ECG Database (200 records, 500Hz, wave delineation)",
        "size": "~23.6 MB",
        "records": 200,
        "leads": 12,
        "freq_hz": 500,
        "labels": "P/QRS/T wave boundaries + cardiac diagnoses",
    },
}

# Pre-defined bundles for convenience
BUNDLES = {
    "all":       list(DATASETS.keys()),
    "arrhythmia": ["sph", "cpsc2018", "cpsc2018-extra", "georgia",
                   "chapman-shaoxing", "ningbo", "incart"],
    "cinc2021":  ["cpsc2018", "cpsc2018-extra", "georgia",
                  "chapman-shaoxing", "ningbo"],
    "diagnostic": ["ptb-xl", "ptb", "ludb"],
}

# ─── THREAD CONFIG ────────────────────────────────────────────────────────────
MAX_CRAWL_WORKERS = 10
MAX_DL_WORKERS    = 15

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("ECGDownloader")
logger.setLevel(logging.DEBUG)


def _setup_logging(download_dir):
    """Create file handler for verbose logging (won't break tqdm bars)."""
    os.makedirs(download_dir, exist_ok=True)
    log_file = os.path.join(download_dir, "download_debug.log")
    if not logger.handlers:
        fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(threadName)s: %(message)s"
        ))
        logger.addHandler(fh)
    return log_file


def _create_session():
    """Robust requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=10, backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=MAX_DL_WORKERS,
        pool_maxsize=MAX_DL_WORKERS,
    )
    session.mount("https://", adapter)
    return session


# ─── CRAWLER ──────────────────────────────────────────────────────────────────
def _fetch_directory(session, url):
    """Return (files, subdirectories) found at a PhysioNet directory URL."""
    logger.debug("Scanning directory: %s", url)
    files, dirs = [], []
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        skip = {"../", "?C=N;O=D", "?C=M;O=A", "?C=S;O=A", "?C=D;O=A"}
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href or href in skip or href.startswith("?"):
                continue
            full = urljoin(url, href)
            (dirs if href.endswith("/") else files).append(full)
    except Exception as e:
        logger.error("Failed to scan %s: %s", url, e)
    return files, dirs


def _crawl(session, start_url):
    """Concurrently map the full directory tree starting from start_url."""
    all_files = []
    to_scan = [start_url]
    with ThreadPoolExecutor(max_workers=MAX_CRAWL_WORKERS) as pool:
        while to_scan:
            futs = {pool.submit(_fetch_directory, session, d): d for d in to_scan}
            to_scan = []
            for fut in as_completed(futs):
                files, subdirs = fut.result()
                all_files.extend(files)
                to_scan.extend(subdirs)
    return all_files


# ─── DOWNLOADER ───────────────────────────────────────────────────────────────
def _download_file(session, file_url, base_url, save_dir, pbar):
    """Download one file; skip if already present."""
    rel = file_url.replace(base_url, "")
    local = os.path.join(save_dir, os.path.normpath(rel))
    os.makedirs(os.path.dirname(local), exist_ok=True)

    if os.path.exists(local) and os.path.getsize(local) > 0:
        logger.debug("Skipping existing: %s", rel)
        pbar.update(1)
        return True

    logger.info("Downloading: %s", rel)
    try:
        resp = session.get(file_url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(local, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                if chunk:
                    f.write(chunk)
        pbar.update(1)
        return True
    except Exception as e:
        logger.error("Error downloading %s: %s", file_url, e)
        return False


def download_dataset(key):
    """Download a single dataset by its registry key."""
    ds = DATASETS[key]
    base_url = ds["url"]
    save_dir = os.path.join(SCRIPT_DIR, ds["dir"])
    log_file = _setup_logging(save_dir)

    print(f"\n{'='*70}")
    print(f"  Dataset : {key}")
    print(f"  {ds['desc']}")
    print(f"  Size    : {ds['size']}   |   Records: {ds['records']}")
    print(f"  Save to : {save_dir}")
    print(f"  Log     : {log_file}")
    print(f"{'='*70}")

    session = _create_session()

    # Crawl
    print("  Mapping directory structure...")
    file_urls = _crawl(session, base_url)
    total = len(file_urls)
    print(f"  Discovered {total} files.")
    logger.info("[%s] Discovered %d files from %s", key, total, base_url)

    if total == 0:
        print("  No files found – check connection or URL.")
        return

    # Download
    with tqdm(total=total, desc=f"  {key}", unit="file") as pbar:
        with ThreadPoolExecutor(max_workers=MAX_DL_WORKERS) as pool:
            futs = [
                pool.submit(_download_file, session, u, base_url, save_dir, pbar)
                for u in file_urls
            ]
            for f in as_completed(futs):
                pass  # errors logged internally

    print(f"  ✓ {key} complete → {save_dir}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────
def _print_catalog():
    """Pretty-print the available datasets."""
    print("\n  Available 12-Lead ECG Datasets")
    print("  " + "─" * 68)
    total_records = 0
    for i, (k, ds) in enumerate(DATASETS.items(), 1):
        total_records += ds["records"]
        print(f"  {i:>2}. {k:<20s} {ds['records']:>7,} records  "
              f"{ds['leads']:>2}-lead  {ds['freq_hz']:>5}Hz  {ds['size']:>8s}")
    print("  " + "─" * 68)
    print(f"  Total: {total_records:,} records across {len(DATASETS)} datasets\n")
    print("  Bundles:")
    for bname, bkeys in BUNDLES.items():
        recs = sum(DATASETS[k]["records"] for k in bkeys)
        print(f"    {bname:<14s} → {', '.join(bkeys)}  ({recs:,} records)")
    print()


def _interactive_menu():
    """Show an interactive selection menu if no CLI args given."""
    _print_catalog()
    print("  Enter dataset key(s) separated by commas, a bundle name, or 'q' to quit.")
    choice = input("  > ").strip().lower()
    if choice in ("q", "quit", "exit"):
        return []

    # Check bundle first
    if choice in BUNDLES:
        return BUNDLES[choice]

    # Parse comma-separated keys
    keys = [k.strip() for k in choice.split(",")]
    valid = []
    for k in keys:
        if k in DATASETS:
            valid.append(k)
        elif k in BUNDLES:
            valid.extend(BUNDLES[k])
        else:
            print(f"  ⚠ Unknown dataset: '{k}' – skipping")
    return list(dict.fromkeys(valid))  # deduplicate, keep order


def main():
    parser = argparse.ArgumentParser(
        description="Download 12-lead ECG datasets from PhysioNet."
    )
    parser.add_argument(
        "--dataset", "-d", type=str, default=None,
        help="Dataset key, bundle name, or comma-separated list (e.g. 'ptb-xl,sph')"
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List all available datasets and exit"
    )
    args = parser.parse_args()

    if args.list:
        _print_catalog()
        return

    # Determine which datasets to download
    if args.dataset:
        raw = args.dataset.lower()
        if raw in BUNDLES:
            targets = BUNDLES[raw]
        else:
            targets = [k.strip() for k in raw.split(",")]
            for t in targets:
                if t not in DATASETS and t not in BUNDLES:
                    print(f"Error: Unknown dataset '{t}'.")
                    print("Use --list to see available datasets.")
                    sys.exit(1)
            expanded = []
            for t in targets:
                if t in BUNDLES:
                    expanded.extend(BUNDLES[t])
                else:
                    expanded.append(t)
            targets = list(dict.fromkeys(expanded))
    else:
        targets = _interactive_menu()

    if not targets:
        print("Nothing selected. Exiting.")
        return

    print(f"\n  Will download {len(targets)} dataset(s): {', '.join(targets)}")
    start = time.time()

    for key in targets:
        download_dataset(key)

    elapsed = time.time() - start
    print(f"{'='*70}")
    print(f"  All done! {len(targets)} dataset(s) in {elapsed/60:.1f} minutes.")
    print(f"  Files saved under: {SCRIPT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()