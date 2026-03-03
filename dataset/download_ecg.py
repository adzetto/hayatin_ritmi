"""
download_ecg.py - Multi-Dataset ECG Downloader
===============================================
Downloads publicly available ECG datasets from PhysioNet and Kaggle.

Usage:
  python download_ecg.py                        # Interactive menu
  python download_ecg.py --dataset sph          # Download specific dataset
  python download_ecg.py --dataset lead-flex    # Download robustness bundle
  python download_ecg.py --dataset all          # Download all PhysioNet datasets
  python download_ecg.py --dataset all-kaggle   # Download all Kaggle datasets
  python download_ecg.py --dataset everything   # Download everything
  python download_ecg.py --list                 # List available datasets
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
# source: "physionet" → crawl HTML directory listing
# source: "kaggle"    → download via Kaggle API (pip install kaggle)
DATASETS = {
    # ══════════════════════════════════════════════════════════════════════
    # PhysioNet Datasets (HTML directory crawl)
    # ══════════════════════════════════════════════════════════════════════
    "sph": {
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
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
        "source": "physionet",
        "url": "https://physionet.org/files/ludb/1.0.1/",
        "dir": "ludb",
        "desc": "Lobachevsky University ECG Database (200 records, 500Hz, wave delineation)",
        "size": "~23.6 MB",
        "records": 200,
        "leads": 12,
        "freq_hz": 500,
        "labels": "P/QRS/T wave boundaries + cardiac diagnoses",
    },
    "ltstdb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ltstdb/1.0.0/",
        "dir": "ltstdb",
        "desc": "Long-Term ST Database (86 records, mixed 2/3-channel Holter ECG, 250Hz)",
        "size": "~9.5 GB",
        "records": 86,
        "lead_range": "2-3",
        "freq_hz": 250,
        "labels": "ST episodes and rhythm annotations",
    },
    "ucddb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ucddb/1.0.0/",
        "dir": "ucddb",
        "desc": "UCD Sleep Apnea Database (25 records, 3-channel Holter ECG, 128Hz)",
        "size": "~1.3 GB",
        "records": 25,
        "leads": 3,
        "freq_hz": 128,
        "labels": "Sleep apnea event annotations + overnight ECG",
    },
    "mhd-effect-ecg-mri": {
        "source": "physionet",
        "url": "https://physionet.org/files/mhd-effect-ecg-mri/1.0.0/",
        "dir": "mhd-effect-ecg-mri",
        "desc": "MRI MHD Effect ECG Dataset (53 records, mixed 3/12-lead, 1024Hz)",
        "size": "~279.8 MB",
        "records": 53,
        "lead_range": "3-12",
        "freq_hz": 1024,
        "labels": "Clean outside-MRI vs MRI-corrupted ECG recordings",
    },
    "twadb": {
        "source": "physionet",
        "url": "https://physionet.org/files/twadb/1.0.0/",
        "dir": "twadb",
        "desc": "T-Wave Alternans Challenge DB (100 records, mixed 2/3/12-lead, 500Hz)",
        "size": "~105 MB",
        "records": 100,
        "lead_range": "2-12",
        "freq_hz": 500,
        "labels": "TWA challenge records with alternans-focused labels",
    },
    "mghdb": {
        "source": "physionet",
        "url": "https://physionet.org/files/mghdb/1.0.0/",
        "dir": "mghdb",
        "desc": "MGH/MF ICU Waveform DB (250 records, typically 3 ECG leads, 360Hz)",
        "size": "~4.2 GB",
        "records": 250,
        "leads": 3,
        "freq_hz": 360,
        "labels": "ECG leads + hemodynamic waveforms (ICU)",
    },

    # ══════════════════════════════════════════════════════════════════════
    # Kaggle Datasets (downloaded via Kaggle API)
    # ══════════════════════════════════════════════════════════════════════

    # ── Tier 1: ML-Ready / Most Popular ───────────────────────────────────
    "heartbeat": {
        "source": "kaggle",
        "kaggle_id": "shayanfazeli/heartbeat",
        "dir": "ecg-heartbeat-categorization",
        "desc": "ECG Heartbeat Categorization (109K samples, 5 classes, CSV, 125Hz)",
        "size": "~300 MB",
        "records": 109446,
        "leads": 1,
        "freq_hz": 125,
        "labels": "Normal, SVEB, VEB, Fusion, Unknown (MIT-BIH preprocessed)",
    },
    "cinc2020": {
        "source": "kaggle",
        "kaggle_id": "bjoernjostein/physionet-challenge-2020",
        "dir": "physionet-challenge-2020",
        "desc": "PhysioNet Challenge 2020 – 12-Lead ECG (43K records, 27 diagnoses)",
        "size": "~7 GB",
        "records": 43101,
        "leads": 12,
        "freq_hz": 500,
        "labels": "27 SNOMED-CT cardiac abnormality codes (unified multi-source)",
    },
    "cinc2017": {
        "source": "kaggle",
        "kaggle_id": "daniildeltsov/physionet-challenge-2017",
        "dir": "physionet-challenge-2017",
        "desc": "PhysioNet Challenge 2017 – AFib Single-Lead (8.5K records, 300Hz)",
        "size": "~600 MB",
        "records": 8528,
        "leads": 1,
        "freq_hz": 300,
        "labels": "Normal, AFib, Other rhythm, Noisy",
    },

    # ── Tier 2: AFib-Specific ─────────────────────────────────────────────
    "afib-detect": {
        "source": "kaggle",
        "kaggle_id": "taejoongyoon/cardiac-arrhythmia-detection",
        "dir": "afib-detection",
        "desc": "Cardiac Arrhythmia Detection – AFib vs Normal (8.5K instances)",
        "size": "~100 MB",
        "records": 8528,
        "leads": 1,
        "freq_hz": 300,
        "labels": "AF, Normal (from PhysioNet 2017 Challenge, pre-split)",
    },
    "afib-signal": {
        "source": "kaggle",
        "kaggle_id": "nelsonsharma/af-classification-from-a-short-single-lead-ecg",
        "dir": "afib-signal-wearable",
        "desc": "AF Classification from Single-Lead ECG (wearable data)",
        "size": "~150 MB",
        "records": 8528,
        "leads": 1,
        "freq_hz": 300,
        "labels": "Labeled + unlabeled AF segments (wearable ECG)",
    },
    "afib-termination": {
        "source": "kaggle",
        "kaggle_id": "annavictoria/healthcare-atrial-fibrillation",
        "dir": "afib-termination",
        "desc": "AF Termination Prediction (non-term, 1min-term, immediate-term)",
        "size": "~20 MB",
        "records": 75,
        "leads": 2,
        "freq_hz": 128,
        "labels": "Non-terminating, Terminating-1min, Terminating-immediately",
    },
    "mitbih-afib": {
        "source": "kaggle",
        "kaggle_id": "taejoongyoon/mit-bih-af-database",
        "dir": "mitbih-afib-database",
        "desc": "MIT-BIH AF Database (25 long-term Holter ECG, 10hr each, 250Hz)",
        "size": "~300 MB",
        "records": 25,
        "leads": 2,
        "freq_hz": 250,
        "labels": "Beat-by-beat AFib, AFL, J-rhythm, Normal annotations",
    },

    # ── Tier 3: Image-Based ECG ───────────────────────────────────────────
    "ecg-images": {
        "source": "kaggle",
        "kaggle_id": "khotijahs1/ecg-images-dataset-of-cardiac-patients",
        "dir": "ecg-images-cardiac",
        "desc": "ECG Images of Cardiac Patients (MI, abnormal, normal printouts)",
        "size": "~500 MB",
        "records": 928,
        "leads": 12,
        "freq_hz": 0,
        "labels": "MI, Abnormal, Historical MI, Normal (paper ECG images)",
    },
    "ecg-image-arrhythmia": {
        "source": "kaggle",
        "kaggle_id": "sadmansakib7/ecg-arrhythmia-classification-dataset",
        "dir": "ecg-image-arrhythmia",
        "desc": "ECG Arrhythmia Classification Images (7.9K downloads)",
        "size": "~200 MB",
        "records": 7000,
        "leads": 12,
        "freq_hz": 0,
        "labels": "Arrhythmia classes as ECG waveform images",
    },

    # ── Tier 4: Large-Scale / Emerging ────────────────────────────────────
    "mimic-perform-af": {
        "source": "kaggle",
        "kaggle_id": "pcharambira/mimic-perform-af-dataset",
        "dir": "mimic-perform-af",
        "desc": "MIMIC PERform AF Dataset (ECG+PPG, AF vs normal sinus rhythm)",
        "size": "~500 MB",
        "records": 35,
        "leads": 1,
        "freq_hz": 125,
        "labels": "Atrial fibrillation, Normal sinus rhythm (ECG + PPG)",
    },
    "shdb-af": {
        "source": "kaggle",
        "kaggle_id": "bjoernjostein/shdb-af",
        "dir": "shdb-af-holter",
        "desc": "SHDB-AF: Japanese Holter AF Database (Saitama Heart DB)",
        "size": "~2 GB",
        "records": 100,
        "leads": 2,
        "freq_hz": 200,
        "labels": "Atrial fibrillation Holter annotations (Japanese population)",
    },
}

# Pre-defined bundles for convenience
BUNDLES = {
    # PhysioNet only
    "all":       [k for k, v in DATASETS.items() if v.get("source") == "physionet"],
    "arrhythmia": ["sph", "cpsc2018", "cpsc2018-extra", "georgia",
                   "chapman-shaoxing", "ningbo", "incart"],
    "cinc2021":  ["cpsc2018", "cpsc2018-extra", "georgia",
                  "chapman-shaoxing", "ningbo"],
    "diagnostic": ["ptb-xl", "ptb", "ludb"],
    "three-lead": ["ucddb", "mghdb"],
    "lead-flex": ["ltstdb", "ucddb", "mhd-effect-ecg-mri", "twadb", "mghdb"],
    "ai-robustness": [
        "ptb-xl", "sph", "ltstdb", "ucddb",
        "mhd-effect-ecg-mri", "twadb", "mghdb",
    ],
    # Kaggle only
    "all-kaggle": [k for k, v in DATASETS.items() if v.get("source") == "kaggle"],
    "ml-ready":   ["heartbeat", "cinc2020", "cinc2017"],
    "afib":       ["cinc2017", "afib-detect", "afib-signal", "afib-termination",
                   "mitbih-afib", "mimic-perform-af", "shdb-af"],
    "challenge":  ["cinc2017", "cinc2020"],
    "ecg-vision": ["ecg-images", "ecg-image-arrhythmia"],
    # Everything
    "everything": list(DATASETS.keys()),
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


# ─── KAGGLE DOWNLOADER ────────────────────────────────────────────────────────
def _download_kaggle_dataset(key):
    """Download a single dataset from Kaggle via the kaggle API."""
    ds = DATASETS[key]
    kaggle_id = ds["kaggle_id"]
    save_dir = os.path.join(SCRIPT_DIR, ds["dir"])

    print(f"\n{'='*70}")
    print(f"  Dataset : {key}  [KAGGLE]")
    print(f"  {ds['desc']}")
    print(f"  Size    : {ds['size']}   |   Records: {ds['records']}")
    print(f"  Kaggle  : kaggle.com/datasets/{kaggle_id}")
    print(f"  Save to : {save_dir}")
    print(f"{'='*70}")

    # Check if already downloaded
    if os.path.exists(save_dir) and any(True for _ in os.scandir(save_dir)):
        print(f"  [SKIP] Directory already exists with files: {save_dir}")
        print(f"         Delete it first to re-download.")
        return

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        print("  [ERROR] kaggle package not installed. Run: pip install kaggle")
        return

    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        print(f"  [ERROR] Kaggle auth failed: {e}")
        print("  Make sure ~/.kaggle/kaggle.json exists.")
        return

    os.makedirs(save_dir, exist_ok=True)
    print(f"  Downloading from Kaggle (this may take a while)...")
    try:
        api.dataset_download_files(
            kaggle_id,
            path=save_dir,
            unzip=True,
            quiet=False,
        )
        print(f"  [OK] {key} complete -> {save_dir}\n")
    except Exception as e:
        print(f"  [ERROR] Download failed: {e}")


def download_dataset(key):
    """Download a single dataset by its registry key (auto-routes by source)."""
    ds = DATASETS[key]
    source = ds.get("source", "physionet")

    if source == "kaggle":
        _download_kaggle_dataset(key)
        return

    # PhysioNet download path
    base_url = ds["url"]
    save_dir = os.path.join(SCRIPT_DIR, ds["dir"])
    log_file = _setup_logging(save_dir)

    print(f"\n{'='*70}")
    print(f"  Dataset : {key}  [PHYSIONET]")
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
        print("  No files found - check connection or URL.")
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

    print(f"  [OK] {key} complete -> {save_dir}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────
def _print_catalog():
    """Pretty-print the available datasets."""
    # PhysioNet datasets
    physionet = {k: v for k, v in DATASETS.items() if v.get("source") == "physionet"}
    kaggle = {k: v for k, v in DATASETS.items() if v.get("source") == "kaggle"}

    print("\n  ╔══ PhysioNet ECG Datasets (HTML crawler) ══╗")
    print("  " + "-" * 75)
    total_records = 0
    for i, (k, ds) in enumerate(physionet.items(), 1):
        total_records += ds["records"]
        lead_text = ds.get("lead_range", str(ds.get("leads", "?")))
        print(f"  {i:>2}. {k:<20s} {ds['records']:>7,} records  "
              f"{lead_text:>5s} lead  {ds['freq_hz']:>5}Hz  {ds['size']:>8s}")
    print("  " + "-" * 75)
    print(f"  Subtotal: {total_records:,} records across {len(physionet)} datasets\n")

    print("  ╔══ Kaggle ECG Datasets (Kaggle API) ══╗")
    print("  " + "-" * 75)
    kaggle_records = 0
    for i, (k, ds) in enumerate(kaggle.items(), 1):
        kaggle_records += ds["records"]
        lead_text = ds.get("lead_range", str(ds.get("leads", "?")))
        src_tag = ds.get("kaggle_id", "").split("/")[0][:12]
        print(f"  {i:>2}. {k:<22s} {ds['records']:>7,} rec  "
              f"{lead_text:>5s} lead  {ds['freq_hz']:>5}Hz  {ds['size']:>8s}  @{src_tag}")
    print("  " + "-" * 75)
    print(f"  Subtotal: {kaggle_records:,} records across {len(kaggle)} datasets")
    print(f"  ═══════════════════════════════════════")
    print(f"  GRAND TOTAL: {total_records + kaggle_records:,} records across {len(DATASETS)} datasets\n")

    print("  Bundles:")
    for bname, bkeys in BUNDLES.items():
        recs = sum(DATASETS[k]["records"] for k in bkeys if k in DATASETS)
        src_mix = set(DATASETS[k].get("source", "?") for k in bkeys if k in DATASETS)
        tag = "/".join(sorted(src_mix))
        print(f"    {bname:<16s} -> {', '.join(bkeys)}  ({recs:,} rec) [{tag}]")
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
            print(f"  [WARN] Unknown dataset: '{k}' - skipping")
    return list(dict.fromkeys(valid))  # deduplicate, keep order


def main():
    parser = argparse.ArgumentParser(
        description="Download ECG datasets (multi-lead, mixed-lead) from PhysioNet."
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
