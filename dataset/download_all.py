"""
download_all.py - Hayatin Ritmi Rclone Downloader
=================================================
Tum PhysioNet ve Kaggle ECG veri setlerini rclone uzerinden 
dogrudan Google Drive'a (veya harici buluta) indirir.
Diskinizi doldurmaz, streaming yapar.

Kullanim:
  python download_all.py                  # Interaktif menu
  python download_all.py --bundle all     # Tum PhysioNet
  python download_all.py --bundle everything  # Hersey (~33 GB)
  python download_all.py --remote gdrive:TUBITAK_Datasets  # Rclone remote dizini
"""

import os
import sys
import time
import argparse
import subprocess
import logging
import requests
import tempfile
import shutil
from pathlib import Path
from datetime import timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, BarColumn, TextColumn, DownloadColumn,
    TransferSpeedColumn, TimeRemainingColumn, SpinnerColumn,
    TaskProgressColumn,
)
from rich.layout import Layout
from rich.live import Live
from rich import box

# ---------------------------------------------------------------------------
# Yapilandirma
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
MAX_CRAWL_WORKERS = 10
MAX_DL_WORKERS = 15
CHUNK_SIZE = 128 * 1024  # Rclone'a hizli yazim icin 128KB chunk

console = Console()
logger = logging.getLogger("RcloneDL")
logger.setLevel(logging.DEBUG)

# Varsayilan rclone hedefi 
DEFAULT_RCLONE_REMOTE = "gdrive:TUBITAK_Datasets"

# Windows ise rclone'u wsl uzerinden calistirin
USE_WSL = sys.platform == "win32"
RCLONE_CMD = ["wsl", "rclone"] if USE_WSL else ["rclone"]

# ---------------------------------------------------------------------------
# Veri Seti Kayit Defteri
# ---------------------------------------------------------------------------
DATASETS = {
    # --- PhysioNet ------------------------------------------------------------
    "sph": {"source": "physionet", "url": "https://physionet.org/files/ecg-arrhythmia/1.0.0/", "dir": "ecg-arrhythmia", "desc": "SPH 12-Lead ECG Arrhythmia", "size_gb": 7.0, "records": 45152, "leads": 12, "freq_hz": 500},
    "ptb-xl": {"source": "physionet", "url": "https://physionet.org/files/ptb-xl/1.0.3/", "dir": "ptb-xl", "desc": "PTB-XL Large ECG", "size_gb": 3.0, "records": 21799, "leads": 12, "freq_hz": 500},
    "cpsc2018": {"source": "physionet", "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018/", "dir": "cpsc2018", "desc": "CPSC 2018 China", "size_gb": 1.0, "records": 6877, "leads": 12, "freq_hz": 500},
    "cpsc2018-extra": {"source": "physionet", "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018_extra/", "dir": "cpsc2018-extra", "desc": "CPSC 2018 Extra", "size_gb": 0.5, "records": 3453, "leads": 12, "freq_hz": 500},
    "georgia": {"source": "physionet", "url": "https://physionet.org/files/challenge-2021/1.0.3/training/georgia/", "dir": "georgia", "desc": "Georgia 12-Lead ECG", "size_gb": 1.5, "records": 10344, "leads": 12, "freq_hz": 500},
    "chapman-shaoxing": {"source": "physionet", "url": "https://physionet.org/files/challenge-2021/1.0.3/training/chapman_shaoxing/", "dir": "chapman-shaoxing", "desc": "Chapman-Shaoxing", "size_gb": 1.5, "records": 10247, "leads": 12, "freq_hz": 500},
    "ningbo": {"source": "physionet", "url": "https://physionet.org/files/challenge-2021/1.0.3/training/ningbo/", "dir": "ningbo", "desc": "Ningbo First Hospital", "size_gb": 5.0, "records": 34905, "leads": 12, "freq_hz": 500},
    "ptb": {"source": "physionet", "url": "https://physionet.org/files/ptbdb/1.0.0/", "dir": "ptb-diagnostic", "desc": "PTB Diagnostic ECG", "size_gb": 1.7, "records": 549, "leads": 15, "freq_hz": 1000},
    "incart": {"source": "physionet", "url": "https://physionet.org/files/incartdb/1.0.0/", "dir": "incart", "desc": "INCART 12-Lead Arrhythmia", "size_gb": 0.8, "records": 75, "leads": 12, "freq_hz": 257},
    "ludb": {"source": "physionet", "url": "https://physionet.org/files/ludb/1.0.1/", "dir": "ludb", "desc": "Lobachevsky Univ. ECG", "size_gb": 0.02, "records": 200, "leads": 12, "freq_hz": 500},
    "ltstdb": {"source": "physionet", "url": "https://physionet.org/files/ltstdb/1.0.0/", "dir": "ltstdb", "desc": "Long-Term ST Database", "size_gb": 9.5, "records": 86, "leads": 3, "freq_hz": 250},
    "ucddb": {"source": "physionet", "url": "https://physionet.org/files/ucddb/1.0.0/", "dir": "ucddb", "desc": "UCD Sleep Apnea", "size_gb": 1.3, "records": 25, "leads": 3, "freq_hz": 128},
    "mhd-effect": {"source": "physionet", "url": "https://physionet.org/files/mhd-effect-ecg-mri/1.0.0/", "dir": "mhd-effect-ecg-mri", "desc": "MRI MHD Effect ECG", "size_gb": 0.3, "records": 53, "leads": 12, "freq_hz": 1024},
    "twadb": {"source": "physionet", "url": "https://physionet.org/files/twadb/1.0.0/", "dir": "twadb", "desc": "T-Wave Alternans", "size_gb": 0.1, "records": 100, "leads": 12, "freq_hz": 500},
    "mghdb": {"source": "physionet", "url": "https://physionet.org/files/mghdb/1.0.0/", "dir": "mghdb", "desc": "MGH/MF ICU Waveform", "size_gb": 4.2, "records": 250, "leads": 3, "freq_hz": 360},
    
    # --- Kaggle ---------------------------------------------------------------
    "heartbeat": {"source": "kaggle", "kaggle_id": "shayanfazeli/heartbeat", "dir": "ecg-heartbeat-categorization", "desc": "ECG Heartbeat Categorization", "size_gb": 0.3, "records": 109446, "leads": 1, "freq_hz": 125},
    "cinc2020": {"source": "kaggle", "kaggle_id": "bjoernjostein/physionet-challenge-2020", "dir": "physionet-challenge-2020", "desc": "PhysioNet Challenge 2020", "size_gb": 7.0, "records": 43101, "leads": 12, "freq_hz": 500},
    "cinc2017": {"source": "kaggle", "kaggle_id": "daniildeltsov/physionet-challenge-2017", "dir": "physionet-challenge-2017", "desc": "PhysioNet Challenge 2017 AFib", "size_gb": 0.6, "records": 8528, "leads": 1, "freq_hz": 300},
    "ecg-images": {"source": "kaggle", "kaggle_id": "khotijahs1/ecg-images-dataset-of-cardiac-patients", "dir": "ecg-images-cardiac", "desc": "ECG Images Cardiac Patients", "size_gb": 0.5, "records": 928, "leads": 12, "freq_hz": 0},
    "shdb-af": {"source": "kaggle", "kaggle_id": "bjoernjostein/shdb-af", "dir": "shdb-af-holter", "desc": "SHDB-AF Holter (Japan)", "size_gb": 2.0, "records": 100, "leads": 2, "freq_hz": 200},
}

BUNDLES = {
    "all":         [k for k, v in DATASETS.items() if v["source"] == "physionet"],
    "all-kaggle":  [k for k, v in DATASETS.items() if v["source"] == "kaggle"],
    "everything":  list(DATASETS.keys()),
    "arrhythmia":  ["sph", "cpsc2018", "cpsc2018-extra", "georgia", "chapman-shaoxing", "ningbo", "incart"],
    "cinc2021":    ["cpsc2018", "cpsc2018-extra", "georgia", "chapman-shaoxing", "ningbo"],
    "diagnostic":  ["ptb-xl", "ptb", "ludb"],
}

# ---------------------------------------------------------------------------
# RClone / Ag Fonksiyonlari
# ---------------------------------------------------------------------------
def check_rclone():
    try:
        res = subprocess.run(RCLONE_CMD + ["version"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def get_existing_rclone_files(remote_path):
    """Hedef rclone klasorundeki bagil dosya yollarini hizlica alir."""
    try:
        # lsf -R dosyalari hizlica listeler
        res = subprocess.run(
            RCLONE_CMD + ["lsf", "-R", remote_path],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            return set(line.strip() for line in res.stdout.splitlines() if line.strip() and not line.endswith('/'))
    except Exception:
        pass
    return set()

def create_session():
    s = requests.Session()
    retries = Retry(total=10, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=MAX_DL_WORKERS, pool_maxsize=MAX_DL_WORKERS)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def fetch_directory(session, url):
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
        logger.error(f"Tarama hatasi {url}: {e}")
    return files, dirs

def crawl_physionet(session, start_url, progress, task_id):
    all_files = []
    to_scan = [start_url]
    scanned = 0
    with ThreadPoolExecutor(max_workers=MAX_CRAWL_WORKERS) as pool:
        while to_scan:
            futs = {pool.submit(fetch_directory, session, d): d for d in to_scan}
            to_scan = []
            for fut in as_completed(futs):
                files, subdirs = fut.result()
                all_files.extend(files)
                to_scan.extend(subdirs)
                scanned += 1
                progress.update(task_id, description=f"  Tarama: {scanned} klasor, {len(all_files)} dosya")
    return all_files

# ---------------------------------------------------------------------------
# Sadece stream: Bilgisayara kaydetmeden Rclone rcat kullanarak Drive'a basar
# ---------------------------------------------------------------------------
def process_single_file(session, file_url, base_url, dest_dir, existing_files, is_local, progress, task_id):
    rel = file_url.replace(base_url, "")
    rel_unix = rel.replace("\\", "/")
    
    try:
        head = session.head(file_url, timeout=15, allow_redirects=True)
        remote_size = int(head.headers.get("Content-Length", 0))
    except Exception:
        remote_size = 0

    if is_local:
        local_path = os.path.join(dest_dir, rel.lstrip("/"))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        if os.path.exists(local_path):
            curr_size = os.path.getsize(local_path)
            if remote_size > 0 and curr_size == remote_size:
                progress.advance(task_id, remote_size)
                return True
            if remote_size == 0 and curr_size > 0:
                progress.advance(task_id, curr_size)
                return True
                
        try:
            resp = session.get(file_url, stream=True, timeout=60)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        progress.advance(task_id, len(chunk))
            return True
        except Exception as e:
            logger.error(f"Yerel indirme hatasi {file_url}: {e}")
            return False

    else:
        # RCLONE RCAT STREAM
        remote_file_path = f"{dest_dir}/{rel_unix}"
        if rel_unix in existing_files:
            progress.advance(task_id, remote_size or 0)
            return True

        try:
            resp = session.get(file_url, stream=True, timeout=60)
            resp.raise_for_status()
            
            proc = subprocess.Popen(
                RCLONE_CMD + ["rcat", remote_file_path],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    try:
                        proc.stdin.write(chunk)
                        proc.stdin.flush()
                    except BrokenPipeError:
                        break
                    progress.advance(task_id, len(chunk))
                    
            proc.stdin.close()
            proc.wait()
            
            if proc.returncode != 0:
                err = proc.stderr.read().decode('utf-8')
                logger.error(f"Rcat hatasi {file_url}: {err}")
                return False
            return True
        except Exception as e:
            logger.error(f"Rclone stream hatasi {file_url}: {e}")
            return False

# ---------------------------------------------------------------------------
# PhysioNet - Direkt Buluta Indirme (Streaming)
# ---------------------------------------------------------------------------
def download_physionet_worker(key, ds, args):
    base_url = ds["url"]
    session = create_session()

    if args.local_dir:
        dest_dir = os.path.join(args.local_dir, ds['dir'])
        os.makedirs(dest_dir, exist_ok=True)
    else:
        dest_dir = f"{args.remote}/{ds['dir']}"

    console.print(f"\n  [bold]Faz 1/3[/bold] — Dizin yapisi taraniyor...")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        tid = progress.add_task("  Tarama basliyor...", total=None)
        file_urls = crawl_physionet(session, base_url, progress, tid)

    total_files = len(file_urls)
    console.print(f"  Bulunan dosya: [bold cyan]{total_files:,}[/bold cyan]")
    if total_files == 0:
        return

    existing = set()
    if args.local_dir:
        console.print(f"  [bold]Faz 2/3[/bold] — Yerel disk atlandi (os.path.exists kullanilacak)")
    else:
        console.print(f"  [bold]Faz 2/3[/bold] — Google Drive mevcut dosyalar sorgulaniyor...")
        existing = get_existing_rclone_files(dest_dir)
        if existing:
            console.print(f"  Bulunan Drive dosyasi: [bold green]{len(existing):,}[/bold green] (Atlanacak)")

    est_bytes = int(ds["size_gb"] * 1024 * 1024 * 1024)

    msg = "Yerel diske indiriliyor" if args.local_dir else "Drive'a dogrudan stream yapiliyor"
    console.print(f"  [bold]Faz 3/3[/bold] — {msg} ({MAX_DL_WORKERS} baglanti)...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        tid = progress.add_task(f"  {key}", total=est_bytes)

        with ThreadPoolExecutor(max_workers=MAX_DL_WORKERS) as pool:
            futs = [
                pool.submit(process_single_file, session, u, base_url, dest_dir, existing, args.local_dir, progress, tid)
                for u in file_urls
            ]
            ok, fail = 0, 0
            for f in as_completed(futs):
                if f.result(): ok += 1
                else: fail += 1

        progress.update(tid, completed=est_bytes)

    console.print(f"  Basarili: [green]{ok}[/green]  |  Hatali: [red]{fail}[/red]")
    console.print(f"  Konum: [dim]{dest_dir}[/dim]")

# ---------------------------------------------------------------------------
# Kaggle - Temp Folder + Rclone Move (Kaggle API zorunlulugu)
# ---------------------------------------------------------------------------
def download_kaggle_worker(key, ds, args):
    kaggle_id = ds["kaggle_id"]
    
    if args.local_dir:
        dest_dir = os.path.join(args.local_dir, ds['dir'])
        os.makedirs(dest_dir, exist_ok=True)
    else:
        dest_dir = f"{args.remote}/{ds['dir']}"

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        console.print(f"  [red]HATA[/red] — Kaggle hazirlanamadi: {e} (Kaggle paketini kurun ve kaggle.json ekleyin)")
        return

    with Progress(SpinnerColumn(), TextColumn("[bold magenta]{task.description}[/bold magenta]"), console=console) as progress:
        tid = progress.add_task(f"  {key} indiriliyor", total=None)
        
        if args.local_dir:
            try:
                api.dataset_download_files(kaggle_id, path=dest_dir, unzip=True, quiet=True)
                progress.update(tid, description=f"  {key} dizine cikarildi: {dest_dir}")
                console.print(f"  Kaggle indirmesi [bold green]BAŞARILI[/bold green].")
            except Exception as e:
                console.print(f"  [red]HATA[/red] — Kaggle Indirme: {e}")
        else:
            tmp_dir = tempfile.mkdtemp(prefix=f"kaggle_{key}_")
            try:
                api.dataset_download_files(kaggle_id, path=tmp_dir, unzip=True, quiet=True)
                progress.update(tid, description=f"  Gecici diske alindi, rclone move basliyor...")
                proc = subprocess.run(RCLONE_CMD + ["move", tmp_dir, dest_dir, "--transfers", "10", "--stats", "2s"], capture_output=True, text=True)
                if proc.returncode == 0:
                    console.print(f"  Google Drive aktarimi [bold green]BAŞARILI[/bold green]. Gecici dosyalar silindi.")
                else:
                    console.print(f"  [red]Rclone Hatasi:[/red] {proc.stderr}")
            except Exception as e:
                console.print(f"  [red]HATA[/red] — Rclone: {e}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                
    console.print(f"  Konum: [dim]{dest_dir}[/dim]")

# ---------------------------------------------------------------------------
# Ana İndirme Yoneticisi
# ---------------------------------------------------------------------------
def download_dataset(key, args):
    ds = DATASETS[key]
    source = ds["source"]

    console.print(Panel(
        f"[bold]{ds['desc']}[/bold]\n"
        f"Kaynak: {source.upper()}  |  Kayit: {ds['records']:,}  |  "
        f"Hz: {ds['freq_hz']}  |  Boyut: ~{ds['size_gb']} GB",
        title=f"[bold cyan]{key}[/bold cyan]",
        border_style="cyan",
        width=80,
    ))

    if source == "kaggle":
        download_kaggle_worker(key, ds, args)
    else:
        download_physionet_worker(key, ds, args)

# ---------------------------------------------------------------------------
# UI & Main
# ---------------------------------------------------------------------------
def print_catalog():
    # ... Katalog gorselleri ... (BKNZ: eski dosya; yer kaplamamasi icin ozetlendi)
    table_pn = Table(title="PhysioNet ECG Veri Setleri (Direct Stream)", box=box.ROUNDED, border_style="cyan")
    table_pn.add_column("Anahtar", style="bold")
    table_pn.add_column("Aciklama")
    table_pn.add_column("Boyut", justify="right")
    
    for k, ds in DATASETS.items():
        if ds["source"] == "physionet":
            table_pn.add_row(k, ds["desc"], f"{ds['size_gb']:.1f} GB")
    console.print(table_pn)

    table_kg = Table(title="Kaggle ECG Veri Setleri (Temp-to-Cloud)", box=box.ROUNDED, border_style="magenta")
    table_kg.add_column("Anahtar", style="bold")
    table_kg.add_column("Aciklama")
    table_kg.add_column("Boyut", justify="right")
    for k, ds in DATASETS.items():
        if ds["source"] == "kaggle":
            table_kg.add_row(k, ds["desc"], f"{ds['size_gb']:.1f} GB")
    console.print(table_kg)

def interactive_menu():
    print_catalog()
    console.print("\n  Veri seti anahtari (orn: 'ptb-xl'), paket (orn: 'arrhythmia') girin veya cikmak icin 'q'.")
    choice = input("  > ").strip().lower()
    if choice in ("q", "quit", "exit"): return []
    if choice in BUNDLES: return BUNDLES[choice]
    keys = [k.strip() for k in choice.split(",")]
    return [k for k in keys if k in DATASETS or k in BUNDLES]

def main():
    parser = argparse.ArgumentParser(description="Hayatin Ritmi — Rclone ECG Downloader")
    parser.add_argument("--dataset", "-d", type=str, default=None)
    parser.add_argument("--bundle", "-b", type=str, default=None)
    parser.add_argument("--remote", "-r", type=str, default=DEFAULT_RCLONE_REMOTE, help="Ornek: gdrive:TUBITAK_Datasets")
    parser.add_argument("--local-dir", "-L", type=str, default=None, help="Eger bu parametre verilirse Rclone deaktif olur, dogrudan diske kaydedilir (Google Colab icin)")
    parser.add_argument("--list", "-l", action="store_true")
    args = parser.parse_args()

    if not args.local_dir and not check_rclone():
        console.print("[bold red]HATA:[/bold red] Rclone bulunamadi. WSL'de kurulu oldugundan emin olun (veya --local-dir kullanin).")
        sys.exit(1)

    if args.local_dir:
        target_info = f"Yerel Disk   : [bold yellow]{args.local_dir}[/bold yellow]\nMod          : [bold green]LOCAL (Colab/Disk)[/bold green]"
    else:
        target_info = f"Hedef Rclone : [bold yellow]{args.remote}[/bold yellow]\nMod          : [bold blue]RCLONE DIRECT STREAM[/bold blue]"

    console.print(Panel(
        f"[bold]HAYATIN RITMI — Dataset Downloader[/bold]\n\n{target_info}\nParalel is   : {MAX_DL_WORKERS} baglanti",
        title="[bold cyan]download_all.py[/bold cyan]",
        border_style="cyan",
        width=70,
    ))

    if args.list:
        print_catalog()
        return

    targets = []
    if args.bundle and args.bundle in BUNDLES:
        targets = BUNDLES[args.bundle]
    elif args.dataset:
        targets = [k.strip() for k in args.dataset.split(",") if k.strip() in DATASETS]
    else:
        targets = interactive_menu()

    if not targets:
        console.print("Hicbir sey secilmedi.")
        return

    console.print(f"\n  {len(targets)} veri seti {args.remote} hedefine yuklenecek.")
    t0 = time.time()
    
    for idx, key in enumerate(targets, 1):
        console.rule(f"[bold]{idx}/{len(targets)}[/bold] — {key}")
        download_dataset(key, args)

    dt = str(timedelta(seconds=int(time.time() - t0)))
    console.print(Panel(
        f"[bold green]TAMAMLANDI[/bold green]\n\nTum veriler dogrudan Google Drive'a aktarildi!\nSure: {dt}",
        border_style="green",
        width=60,
    ))

if __name__ == "__main__":
    main()
