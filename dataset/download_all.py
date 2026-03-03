"""
download_all.py - Hayatin Ritmi Full Dataset Downloader
=======================================================
Tum PhysioNet ve Kaggle ECG veri setlerini indirir.
Rich paneller, tqdm progress bar, resume destegi, paralel indirme.

Kullanim:
  python download_all.py                  # Interaktif menu
  python download_all.py --bundle all     # Tum PhysioNet
  python download_all.py --bundle everything  # Hersey (~33 GB)
  python download_all.py --dataset sph    # Tek veri seti
  python download_all.py --list           # Katalog goster
"""

import os
import sys
import time
import argparse
import hashlib
import logging
import requests
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
CHUNK_SIZE = 64 * 1024  # 64 KB

console = Console()

logger = logging.getLogger("DL")
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Veri Seti Kayit Defteri
# ---------------------------------------------------------------------------
DATASETS = {
    # --- PhysioNet ------------------------------------------------------------
    "sph": {
        "source": "physionet",
        "url": "https://physionet.org/files/ecg-arrhythmia/1.0.0/",
        "dir": "ecg-arrhythmia",
        "desc": "SPH 12-Lead ECG Arrhythmia",
        "size_gb": 7.0,
        "records": 45152,
        "leads": 12,
        "freq_hz": 500,
    },
    "ptb-xl": {
        "source": "physionet",
        "url": "https://physionet.org/files/ptb-xl/1.0.3/",
        "dir": "ptb-xl",
        "desc": "PTB-XL Large ECG",
        "size_gb": 3.0,
        "records": 21799,
        "leads": 12,
        "freq_hz": 500,
    },
    "cpsc2018": {
        "source": "physionet",
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018/",
        "dir": "cpsc2018",
        "desc": "CPSC 2018 China",
        "size_gb": 1.0,
        "records": 6877,
        "leads": 12,
        "freq_hz": 500,
    },
    "cpsc2018-extra": {
        "source": "physionet",
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/cpsc_2018_extra/",
        "dir": "cpsc2018-extra",
        "desc": "CPSC 2018 Extra",
        "size_gb": 0.5,
        "records": 3453,
        "leads": 12,
        "freq_hz": 500,
    },
    "georgia": {
        "source": "physionet",
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/georgia/",
        "dir": "georgia",
        "desc": "Georgia 12-Lead ECG",
        "size_gb": 1.5,
        "records": 10344,
        "leads": 12,
        "freq_hz": 500,
    },
    "chapman-shaoxing": {
        "source": "physionet",
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/chapman_shaoxing/",
        "dir": "chapman-shaoxing",
        "desc": "Chapman-Shaoxing",
        "size_gb": 1.5,
        "records": 10247,
        "leads": 12,
        "freq_hz": 500,
    },
    "ningbo": {
        "source": "physionet",
        "url": "https://physionet.org/files/challenge-2021/1.0.3/training/ningbo/",
        "dir": "ningbo",
        "desc": "Ningbo First Hospital",
        "size_gb": 5.0,
        "records": 34905,
        "leads": 12,
        "freq_hz": 500,
    },
    "ptb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ptbdb/1.0.0/",
        "dir": "ptb-diagnostic",
        "desc": "PTB Diagnostic ECG",
        "size_gb": 1.7,
        "records": 549,
        "leads": 15,
        "freq_hz": 1000,
    },
    "incart": {
        "source": "physionet",
        "url": "https://physionet.org/files/incartdb/1.0.0/",
        "dir": "incart",
        "desc": "INCART 12-Lead Arrhythmia",
        "size_gb": 0.8,
        "records": 75,
        "leads": 12,
        "freq_hz": 257,
    },
    "ludb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ludb/1.0.1/",
        "dir": "ludb",
        "desc": "Lobachevsky University ECG",
        "size_gb": 0.02,
        "records": 200,
        "leads": 12,
        "freq_hz": 500,
    },
    "ltstdb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ltstdb/1.0.0/",
        "dir": "ltstdb",
        "desc": "Long-Term ST Database",
        "size_gb": 9.5,
        "records": 86,
        "leads": 3,
        "freq_hz": 250,
    },
    "ucddb": {
        "source": "physionet",
        "url": "https://physionet.org/files/ucddb/1.0.0/",
        "dir": "ucddb",
        "desc": "UCD Sleep Apnea DB",
        "size_gb": 1.3,
        "records": 25,
        "leads": 3,
        "freq_hz": 128,
    },
    "mhd-effect": {
        "source": "physionet",
        "url": "https://physionet.org/files/mhd-effect-ecg-mri/1.0.0/",
        "dir": "mhd-effect-ecg-mri",
        "desc": "MRI MHD Effect ECG",
        "size_gb": 0.3,
        "records": 53,
        "leads": 12,
        "freq_hz": 1024,
    },
    "twadb": {
        "source": "physionet",
        "url": "https://physionet.org/files/twadb/1.0.0/",
        "dir": "twadb",
        "desc": "T-Wave Alternans DB",
        "size_gb": 0.1,
        "records": 100,
        "leads": 12,
        "freq_hz": 500,
    },
    "mghdb": {
        "source": "physionet",
        "url": "https://physionet.org/files/mghdb/1.0.0/",
        "dir": "mghdb",
        "desc": "MGH/MF ICU Waveform DB",
        "size_gb": 4.2,
        "records": 250,
        "leads": 3,
        "freq_hz": 360,
    },
    # --- Kaggle ---------------------------------------------------------------
    "heartbeat": {
        "source": "kaggle",
        "kaggle_id": "shayanfazeli/heartbeat",
        "dir": "ecg-heartbeat-categorization",
        "desc": "ECG Heartbeat Categorization",
        "size_gb": 0.3,
        "records": 109446,
        "leads": 1,
        "freq_hz": 125,
    },
    "cinc2020": {
        "source": "kaggle",
        "kaggle_id": "bjoernjostein/physionet-challenge-2020",
        "dir": "physionet-challenge-2020",
        "desc": "PhysioNet Challenge 2020",
        "size_gb": 7.0,
        "records": 43101,
        "leads": 12,
        "freq_hz": 500,
    },
    "cinc2017": {
        "source": "kaggle",
        "kaggle_id": "daniildeltsov/physionet-challenge-2017",
        "dir": "physionet-challenge-2017",
        "desc": "PhysioNet Challenge 2017 AFib",
        "size_gb": 0.6,
        "records": 8528,
        "leads": 1,
        "freq_hz": 300,
    },
    "ecg-images": {
        "source": "kaggle",
        "kaggle_id": "khotijahs1/ecg-images-dataset-of-cardiac-patients",
        "dir": "ecg-images-cardiac",
        "desc": "ECG Images Cardiac Patients",
        "size_gb": 0.5,
        "records": 928,
        "leads": 12,
        "freq_hz": 0,
    },
    "shdb-af": {
        "source": "kaggle",
        "kaggle_id": "bjoernjostein/shdb-af",
        "dir": "shdb-af-holter",
        "desc": "SHDB-AF Holter (Japan)",
        "size_gb": 2.0,
        "records": 100,
        "leads": 2,
        "freq_hz": 200,
    },
}

BUNDLES = {
    "all":         [k for k, v in DATASETS.items() if v["source"] == "physionet"],
    "all-kaggle":  [k for k, v in DATASETS.items() if v["source"] == "kaggle"],
    "everything":  list(DATASETS.keys()),
    "arrhythmia":  ["sph", "cpsc2018", "cpsc2018-extra", "georgia",
                    "chapman-shaoxing", "ningbo", "incart"],
    "cinc2021":    ["cpsc2018", "cpsc2018-extra", "georgia",
                    "chapman-shaoxing", "ningbo"],
    "diagnostic":  ["ptb-xl", "ptb", "ludb"],
}


# ---------------------------------------------------------------------------
# HTTP oturum
# ---------------------------------------------------------------------------
def create_session():
    s = requests.Session()
    retries = Retry(total=10, backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries,
                          pool_connections=MAX_DL_WORKERS,
                          pool_maxsize=MAX_DL_WORKERS)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# ---------------------------------------------------------------------------
# PhysioNet dizin tarayici
# ---------------------------------------------------------------------------
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
        logger.error("Tarama hatasi %s: %s", url, e)
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
# Tekli dosya indirici (byte bazli progress)
# ---------------------------------------------------------------------------
def download_file(session, file_url, base_url, save_dir, progress, task_id):
    rel = file_url.replace(base_url, "")
    local = save_dir / Path(os.path.normpath(rel))
    local.parent.mkdir(parents=True, exist_ok=True)

    # Boyutu ogren
    try:
        head = session.head(file_url, timeout=15, allow_redirects=True)
        remote_size = int(head.headers.get("Content-Length", 0))
    except Exception:
        remote_size = 0

    # Zaten indirilmis mi kontrol et
    if local.exists():
        local_size = local.stat().st_size
        if local_size > 0 and (remote_size == 0 or local_size >= remote_size):
            progress.advance(task_id, remote_size or local_size)
            return True

    # Indir
    try:
        resp = session.get(file_url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(local, "wb") as f:
            for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    progress.advance(task_id, len(chunk))
        return True
    except Exception as e:
        logger.error("Indirme hatasi %s: %s", file_url, e)
        return False


# ---------------------------------------------------------------------------
# PhysioNet veri seti indirici
# ---------------------------------------------------------------------------
def download_physionet(key, ds):
    base_url = ds["url"]
    save_dir = SCRIPT_DIR / ds["dir"]
    save_dir.mkdir(parents=True, exist_ok=True)

    # Log
    log_path = save_dir / "download_debug.log"
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    session = create_session()

    # Faz 1: Dizin tarama
    console.print(f"\n  [bold]Faz 1/2[/bold] — Dizin yapisi taraniyor...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        tid = progress.add_task("  Tarama basliyor...", total=None)
        file_urls = crawl_physionet(session, base_url, progress, tid)

    total_files = len(file_urls)
    console.print(f"  Bulunan dosya sayisi: [bold cyan]{total_files:,}[/bold cyan]")

    if total_files == 0:
        console.print("  [red]Dosya bulunamadi — baglanti veya URL'yi kontrol edin.[/red]")
        logger.removeHandler(fh)
        return

    # Tahmini boyut
    est_bytes = int(ds["size_gb"] * 1024 * 1024 * 1024)

    # Faz 2: Paralel indirme
    console.print(f"  [bold]Faz 2/2[/bold] — Dosyalar indiriliyor ({MAX_DL_WORKERS} paralel baglanti)...")
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
        tid = progress.add_task(
            f"  {key}",
            total=est_bytes,
        )

        with ThreadPoolExecutor(max_workers=MAX_DL_WORKERS) as pool:
            futs = [
                pool.submit(download_file, session, u, base_url, save_dir, progress, tid)
                for u in file_urls
            ]
            ok = 0
            fail = 0
            for f in as_completed(futs):
                if f.result():
                    ok += 1
                else:
                    fail += 1

        # Progress'i tamamla
        progress.update(tid, completed=est_bytes)

    console.print(f"  Basarili: [green]{ok}[/green]  |  Hatali: [red]{fail}[/red]")
    console.print(f"  Konum: [dim]{save_dir}[/dim]")
    logger.removeHandler(fh)


# ---------------------------------------------------------------------------
# Kaggle veri seti indirici
# ---------------------------------------------------------------------------
def download_kaggle(key, ds):
    kaggle_id = ds["kaggle_id"]
    save_dir = SCRIPT_DIR / ds["dir"]

    # Zaten var mi?
    if save_dir.exists() and any(save_dir.iterdir()):
        console.print(f"  [yellow]ATLA[/yellow] — Klasor bos degil: {save_dir}")
        console.print(f"  Yeniden indirmek icin klasoru silin.")
        return

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        console.print("  [red]HATA[/red] — kaggle paketi yuklu degil: pip install kaggle")
        return

    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        console.print(f"  [red]HATA[/red] — Kaggle kimlik dogrulama basarisiz: {e}")
        console.print("  ~/.kaggle/kaggle.json dosyasini kontrol edin.")
        return

    save_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"  Kaggle API ile indiriliyor...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]{task.description}[/bold magenta]"),
        BarColumn(bar_width=40),
        console=console,
    ) as progress:
        tid = progress.add_task(f"  {key} (Kaggle)", total=None)
        try:
            api.dataset_download_files(
                kaggle_id,
                path=str(save_dir),
                unzip=True,
                quiet=True,
            )
            progress.update(tid, description=f"  {key} — tamamlandi")
        except Exception as e:
            console.print(f"  [red]HATA[/red] — Indirme basarisiz: {e}")
            return

    console.print(f"  Konum: [dim]{save_dir}[/dim]")


# ---------------------------------------------------------------------------
# Ana indirme fonksiyonu
# ---------------------------------------------------------------------------
def download_dataset(key):
    ds = DATASETS[key]
    source = ds["source"]

    console.print(Panel(
        f"[bold]{ds['desc']}[/bold]\n"
        f"Kaynak: {source.upper()}  |  "
        f"Kayit: {ds['records']:,}  |  "
        f"Lead: {ds.get('leads', '?')}  |  "
        f"Hz: {ds['freq_hz']}  |  "
        f"Boyut: ~{ds['size_gb']} GB",
        title=f"[bold cyan]{key}[/bold cyan]",
        border_style="cyan",
        width=80,
    ))

    if source == "kaggle":
        download_kaggle(key, ds)
    else:
        download_physionet(key, ds)


# ---------------------------------------------------------------------------
# Katalog yazdirma
# ---------------------------------------------------------------------------
def print_catalog():
    # PhysioNet tablosu
    table_pn = Table(
        title="PhysioNet ECG Veri Setleri",
        box=box.ROUNDED,
        border_style="cyan",
        title_style="bold cyan",
    )
    table_pn.add_column("#", justify="right", width=3)
    table_pn.add_column("Anahtar", style="bold")
    table_pn.add_column("Aciklama")
    table_pn.add_column("Kayit", justify="right")
    table_pn.add_column("Lead", justify="center")
    table_pn.add_column("Hz", justify="right")
    table_pn.add_column("Boyut", justify="right")
    table_pn.add_column("Durum", justify="center")

    pn_total_gb = 0
    pn_total_rec = 0
    i = 0
    for k, ds in DATASETS.items():
        if ds["source"] != "physionet":
            continue
        i += 1
        pn_total_gb += ds["size_gb"]
        pn_total_rec += ds["records"]
        exists = (SCRIPT_DIR / ds["dir"]).exists()
        status = "[green]VAR[/green]" if exists else "[dim]--[/dim]"
        table_pn.add_row(
            str(i), k, ds["desc"],
            f"{ds['records']:,}", str(ds.get("leads", "?")),
            str(ds["freq_hz"]), f"{ds['size_gb']:.1f} GB",
            status,
        )

    table_pn.add_row(
        "", "[bold]TOPLAM[/bold]", "",
        f"[bold]{pn_total_rec:,}[/bold]", "", "",
        f"[bold]{pn_total_gb:.1f} GB[/bold]", "",
    )
    console.print(table_pn)

    # Kaggle tablosu
    table_kg = Table(
        title="Kaggle ECG Veri Setleri",
        box=box.ROUNDED,
        border_style="magenta",
        title_style="bold magenta",
    )
    table_kg.add_column("#", justify="right", width=3)
    table_kg.add_column("Anahtar", style="bold")
    table_kg.add_column("Aciklama")
    table_kg.add_column("Kayit", justify="right")
    table_kg.add_column("Boyut", justify="right")
    table_kg.add_column("Durum", justify="center")

    kg_total_gb = 0
    kg_total_rec = 0
    j = 0
    for k, ds in DATASETS.items():
        if ds["source"] != "kaggle":
            continue
        j += 1
        kg_total_gb += ds["size_gb"]
        kg_total_rec += ds["records"]
        exists = (SCRIPT_DIR / ds["dir"]).exists()
        status = "[green]VAR[/green]" if exists else "[dim]--[/dim]"
        table_kg.add_row(
            str(j), k, ds["desc"],
            f"{ds['records']:,}", f"{ds['size_gb']:.1f} GB",
            status,
        )

    table_kg.add_row(
        "", "[bold]TOPLAM[/bold]", "",
        f"[bold]{kg_total_rec:,}[/bold]",
        f"[bold]{kg_total_gb:.1f} GB[/bold]", "",
    )
    console.print(table_kg)

    # Paketler
    table_b = Table(
        title="Hazir Paketler",
        box=box.SIMPLE,
        border_style="yellow",
    )
    table_b.add_column("Paket", style="bold yellow")
    table_b.add_column("Icerik")
    table_b.add_column("Toplam GB", justify="right")

    for bname, bkeys in BUNDLES.items():
        total = sum(DATASETS[k]["size_gb"] for k in bkeys if k in DATASETS)
        table_b.add_row(bname, ", ".join(bkeys), f"{total:.1f} GB")
    console.print(table_b)

    grand_gb = pn_total_gb + kg_total_gb
    grand_rec = pn_total_rec + kg_total_rec
    console.print(Panel(
        f"Toplam: [bold]{len(DATASETS)}[/bold] veri seti  |  "
        f"[bold]{grand_rec:,}[/bold] kayit  |  "
        f"[bold]{grand_gb:.1f} GB[/bold]",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# Interaktif menu
# ---------------------------------------------------------------------------
def interactive_menu():
    print_catalog()
    console.print(
        "\n  Veri seti anahtari, paket adi veya virgulla ayrilmis liste girin.\n"
        "  Cikmak icin 'q' yazin.\n"
    )
    choice = input("  > ").strip().lower()
    if choice in ("q", "quit", "exit"):
        return []
    if choice in BUNDLES:
        return BUNDLES[choice]
    keys = [k.strip() for k in choice.split(",")]
    valid = []
    for k in keys:
        if k in DATASETS:
            valid.append(k)
        elif k in BUNDLES:
            valid.extend(BUNDLES[k])
        else:
            console.print(f"  [yellow]UYARI[/yellow] Bilinmeyen: '{k}' — atlandi")
    return list(dict.fromkeys(valid))


# ---------------------------------------------------------------------------
# Giris noktasi
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hayatin Ritmi — ECG Veri Seti Indirici"
    )
    parser.add_argument("--dataset", "-d", type=str, default=None,
                        help="Tek veri seti anahtari (orn: sph, ptb-xl)")
    parser.add_argument("--bundle", "-b", type=str, default=None,
                        help="Paket adi (orn: all, everything, arrhythmia)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="Mevcut veri setlerini listele")
    args = parser.parse_args()

    # Baslik
    console.print(Panel(
        "[bold]HAYATIN RITMI — ECG Veri Seti Indirici[/bold]\n\n"
        f"Hedef klasor : {SCRIPT_DIR}\n"
        f"Paralel is   : {MAX_DL_WORKERS} baglanti\n"
        f"Chunk boyutu : {CHUNK_SIZE // 1024} KB",
        title="[bold cyan]download_all.py[/bold cyan]",
        border_style="cyan",
        width=70,
    ))

    if args.list:
        print_catalog()
        return

    # Hedefleri belirle
    if args.bundle:
        bname = args.bundle.lower()
        if bname not in BUNDLES:
            console.print(f"[red]Bilinmeyen paket: '{bname}'[/red]")
            console.print(f"Mevcut paketler: {', '.join(BUNDLES.keys())}")
            sys.exit(1)
        targets = BUNDLES[bname]
    elif args.dataset:
        raw = args.dataset.lower()
        targets = [k.strip() for k in raw.split(",")]
        for t in targets:
            if t not in DATASETS:
                console.print(f"[red]Bilinmeyen veri seti: '{t}'[/red]")
                sys.exit(1)
    else:
        targets = interactive_menu()

    if not targets:
        console.print("Hicbir sey secilmedi. Cikiliyor.")
        return

    # Ozet tablosu
    total_gb = sum(DATASETS[k]["size_gb"] for k in targets)
    total_rec = sum(DATASETS[k]["records"] for k in targets)

    summary = Table(title="Indirme Plani", box=box.ROUNDED, border_style="green")
    summary.add_column("#", justify="right", width=3)
    summary.add_column("Veri Seti", style="bold")
    summary.add_column("Kaynak", justify="center")
    summary.add_column("Boyut", justify="right")
    summary.add_column("Kayit", justify="right")
    for i, k in enumerate(targets, 1):
        ds = DATASETS[k]
        summary.add_row(
            str(i), k, ds["source"].upper(),
            f"{ds['size_gb']:.1f} GB", f"{ds['records']:,}",
        )
    summary.add_row(
        "", "[bold]TOPLAM[/bold]", "",
        f"[bold]{total_gb:.1f} GB[/bold]",
        f"[bold]{total_rec:,}[/bold]",
    )
    console.print(summary)

    console.print(f"\n  {len(targets)} veri seti indirilecek (~{total_gb:.1f} GB)")

    # Indirme dongusu
    t0 = time.time()
    done = 0
    for key in targets:
        done += 1
        console.rule(f"[bold]{done}/{len(targets)}[/bold] — {key}")
        download_dataset(key)

    elapsed = time.time() - t0
    dt = str(timedelta(seconds=int(elapsed)))

    console.print(Panel(
        f"[bold green]TAMAMLANDI[/bold green]\n\n"
        f"Veri seti   : {len(targets)}\n"
        f"Toplam sure : {dt}\n"
        f"Konum       : {SCRIPT_DIR}",
        border_style="green",
        width=60,
    ))


if __name__ == "__main__":
    main()
