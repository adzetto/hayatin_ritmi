"""
upload_to_kaggle.py — Advanced ECG Dataset Uploader with Rich Terminal UI
==========================================================================
Uploads all local ECG dataset folders to Kaggle as individual datasets.
Features: Rich panels, live progress bars, size graphs, summary dashboard.

Usage:
  python upload_to_kaggle.py                  # Upload all datasets
  python upload_to_kaggle.py --dry-run        # Preview without uploading
  python upload_to_kaggle.py --only ptb-xl    # Upload specific dataset
  python upload_to_kaggle.py --list           # Show dataset inventory
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeElapsedColumn,
    TimeRemainingColumn, SpinnerColumn, TaskProgressColumn,
    MofNCompleteColumn,
)
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.columns import Columns
from rich import box
from rich.tree import Tree
from rich.markup import escape

console = Console()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
KAGGLE_USERNAME = "muhammetyaciolu"
SCRIPT_DIR = Path(__file__).parent.resolve()

DATASETS = [
    {"dir": "ecg-arrhythmia",     "slug": "ecg-arrhythmia",           "title": "SPH 12-Lead ECG Arrhythmia (45K, 500Hz)",     "records": 45152, "leads": "12",   "freq": 500},
    {"dir": "ptb-xl",             "slug": "ptb-xl-ecg",               "title": "PTB-XL 12-Lead ECG Dataset (21K, 500Hz)",      "records": 21799, "leads": "12",   "freq": 500},
    {"dir": "cpsc2018",           "slug": "cpsc2018-ecg",             "title": "CPSC 2018 12-Lead ECG Challenge (6.8K)",        "records": 6877,  "leads": "12",   "freq": 500},
    {"dir": "cpsc2018-extra",     "slug": "cpsc2018-extra",           "title": "CPSC 2018 Extra 12-Lead ECG (3.4K)",            "records": 3453,  "leads": "12",   "freq": 500},
    {"dir": "georgia",            "slug": "georgia-ecg",              "title": "Georgia 12-Lead ECG Database (10K, 500Hz)",     "records": 10344, "leads": "12",   "freq": 500},
    {"dir": "chapman-shaoxing",   "slug": "chapman-shaoxing",         "title": "Chapman-Shaoxing 12-Lead ECG (10K, 500Hz)",     "records": 10247, "leads": "12",   "freq": 500},
    {"dir": "ningbo",             "slug": "ningbo-ecg",               "title": "Ningbo 12-Lead ECG Database (34K, 500Hz)",      "records": 34905, "leads": "12",   "freq": 500},
    {"dir": "ptb-diagnostic",     "slug": "ptb-diagnostic",           "title": "PTB Diagnostic ECG (549 Records, 1000Hz)",      "records": 549,   "leads": "15",   "freq": 1000},
    {"dir": "incart",             "slug": "incart-ecg",               "title": "INCART 12-Lead Arrhythmia (75 Rec, 257Hz)",     "records": 75,    "leads": "12",   "freq": 257},
    {"dir": "ludb",               "slug": "ludb-ecg-database",        "title": "LUDB ECG Database (200 Records, 500Hz)",        "records": 200,   "leads": "12",   "freq": 500},
    {"dir": "ltstdb",             "slug": "ltstdb-long-term-st",      "title": "LTSTDB Long-Term ST Holter (86 Rec)",           "records": 86,    "leads": "2-3",  "freq": 250},
    {"dir": "ucddb",              "slug": "ucddb-sleep-apnea-ecg",    "title": "UCDDB Sleep Apnea ECG (25 Rec, 128Hz)",         "records": 25,    "leads": "3",    "freq": 128},
    {"dir": "mhd-effect-ecg-mri", "slug": "mhd-effect-ecg-mri",      "title": "MHD Effect ECG-MRI Dataset (53 Records)",       "records": 53,    "leads": "3-12", "freq": 1024},
    {"dir": "twadb",              "slug": "twadb-twave-alternans",    "title": "TWADB T-Wave Alternans (100 Rec, 500Hz)",       "records": 100,   "leads": "2-12", "freq": 500},
    {"dir": "mghdb",              "slug": "mghdb-icu-waveform",       "title": "MGHDB ICU Waveform ECG (250 Rec, 360Hz)",       "records": 250,   "leads": "3",    "freq": 360},
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_dir_size(path: Path) -> int:
    """Recursively sum file sizes in bytes."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def get_file_count(path: Path) -> int:
    return sum(1 for f in path.rglob("*") if f.is_file())


def fmt_size(nbytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def bar_chart(value: float, max_val: float, width: int = 30) -> str:
    """ASCII horizontal bar for size visualization."""
    if max_val == 0:
        return " " * width
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    blocks = "█" * filled + "░" * (width - filled)
    return blocks


def make_sparkline(values: list, width: int = 20) -> str:
    """Sparkline graph from a list of values."""
    sparks = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    # Resample values to width
    step = max(len(values) / width, 1)
    resampled = []
    for i in range(width):
        idx = int(i * step)
        idx = min(idx, len(values) - 1)
        resampled.append(values[idx])
    return "".join(sparks[min(int((v - mn) / rng * 7), 7)] for v in resampled)


# ─── SCAN & MEASURE ─────────────────────────────────────────────────────────

def scan_datasets():
    """Scan local disk for dataset sizes and file counts."""
    results = []
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold cyan]Scanning[/] {task.fields[name]:<24s}"),
        BarColumn(bar_width=30, style="cyan", complete_style="bold cyan"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning...", total=len(DATASETS), name="")
        for ds in DATASETS:
            path = SCRIPT_DIR / ds["dir"]
            progress.update(task, advance=0, name=ds["dir"])
            if path.exists():
                ds["size_bytes"] = get_dir_size(path)
                ds["file_count"] = get_file_count(path)
                ds["exists"] = True
            else:
                ds["size_bytes"] = 0
                ds["file_count"] = 0
                ds["exists"] = False
            progress.update(task, advance=1)
    return DATASETS


# ─── DISPLAY ─────────────────────────────────────────────────────────────────

def show_header():
    """Print the app banner."""
    banner = Text()
    banner.append("  ♥  ", style="bold red")
    banner.append("Hayatın Ritmi", style="bold white")
    banner.append("  —  ", style="dim")
    banner.append("Kaggle ECG Dataset Uploader", style="bold cyan")
    banner.append("  ♥  ", style="bold red")

    panel = Panel(
        Align.center(banner),
        border_style="bright_cyan",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
        subtitle=f"[dim]Kaggle User: [bold]{KAGGLE_USERNAME}[/bold]  |  {datetime.now():%Y-%m-%d %H:%M}[/dim]",
    )
    console.print(panel)
    console.print()


def show_inventory(datasets):
    """Show a rich table with bar charts of dataset sizes."""
    max_size = max(ds["size_bytes"] for ds in datasets if ds["exists"]) if datasets else 1

    table = Table(
        title="[bold]📊 Dataset Inventory[/bold]",
        box=box.ROUNDED,
        border_style="bright_cyan",
        header_style="bold white on dark_blue",
        row_styles=["", "dim"],
        show_lines=False,
        padding=(0, 1),
        title_justify="center",
    )

    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("Dataset", style="bold white", min_width=20)
    table.add_column("Size", justify="right", style="green", width=10)
    table.add_column("Files", justify="right", style="yellow", width=8)
    table.add_column("Records", justify="right", style="magenta", width=9)
    table.add_column("Leads", justify="center", style="cyan", width=6)
    table.add_column("Hz", justify="right", style="blue", width=6)
    table.add_column("Size Distribution", min_width=32, no_wrap=True)
    table.add_column("Status", justify="center", width=5)

    total_size = 0
    total_files = 0
    total_records = 0

    for i, ds in enumerate(datasets, 1):
        exists = ds["exists"]
        size = ds["size_bytes"]
        total_size += size
        total_files += ds["file_count"]
        total_records += ds["records"]

        bar = bar_chart(size, max_size, 28)
        bar_colored = f"[cyan]{bar}[/cyan]"
        status = "[green]✔[/green]" if exists else "[red]✘[/red]"

        table.add_row(
            str(i),
            ds["dir"],
            fmt_size(size) if exists else "[dim]N/A[/dim]",
            f"{ds['file_count']:,}" if exists else "[dim]—[/dim]",
            f"{ds['records']:,}",
            ds["leads"],
            str(ds["freq"]),
            bar_colored,
            status,
        )

    # Footer row
    table.add_section()
    table.add_row(
        "",
        "[bold]TOTAL[/bold]",
        f"[bold green]{fmt_size(total_size)}[/bold green]",
        f"[bold yellow]{total_files:,}[/bold yellow]",
        f"[bold magenta]{total_records:,}[/bold magenta]",
        "",
        "",
        "",
        "",
    )

    console.print(table)
    console.print()

    # Size distribution mini-chart
    sizes_mb = [ds["size_bytes"] / (1024**2) for ds in datasets if ds["exists"]]
    names = [ds["dir"][:12] for ds in datasets if ds["exists"]]
    spark = make_sparkline(sizes_mb, width=len(sizes_mb))
    console.print(
        Panel(
            f"[cyan]{spark}[/cyan]\n"
            + "[dim]" + "  ".join(f"{n[:8]}" for n in names[:8]) + "[/dim]",
            title="[bold]Size Sparkline (relative)[/bold]",
            border_style="dim cyan",
            padding=(0, 1),
        )
    )
    console.print()


def show_tree(datasets):
    """Display a tree view of the dataset directory structure."""
    tree = Tree(
        f"[bold cyan]📁 {SCRIPT_DIR}[/bold cyan]",
        guide_style="bright_cyan",
    )
    for ds in datasets:
        if ds["exists"]:
            label = (
                f"[bold]{ds['dir']}[/bold]  "
                f"[green]{fmt_size(ds['size_bytes'])}[/green]  "
                f"[dim]{ds['file_count']:,} files[/dim]"
            )
            tree.add(f"📂 {label}")
        else:
            tree.add(f"[dim red]📂 {ds['dir']}  (not found)[/dim red]")

    console.print(Panel(tree, title="[bold]Directory Tree[/bold]", border_style="cyan", box=box.ROUNDED))
    console.print()


# ─── METADATA CREATION ──────────────────────────────────────────────────────

def create_metadata(ds: dict) -> Path:
    """Write dataset-metadata.json into the dataset folder."""
    meta = {
        "title": ds["title"],
        "id": f"{KAGGLE_USERNAME}/{ds['slug']}",
        "licenses": [{"name": "other"}],
        "keywords": ["ecg", "physionet", "hayatin-ritmi", "arrhythmia", "12-lead"],
    }
    meta_path = SCRIPT_DIR / ds["dir"] / "dataset-metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta_path


# ─── KAGGLE API (lazy init) ──────────────────────────────────────────────────
_kaggle_api = None

def _get_kaggle_api():
    """Lazily initialize and authenticate the Kaggle API client."""
    global _kaggle_api
    if _kaggle_api is None:
        from kaggle.api.kaggle_api_extended import KaggleApi
        _kaggle_api = KaggleApi()
        _kaggle_api.authenticate()
    return _kaggle_api


# ─── UPLOAD ENGINE ───────────────────────────────────────────────────────────

def _zip_dataset(ds: dict, progress_callback=None) -> Path:
    """
    Zip a dataset folder into a staging directory.
    Returns the staging directory path (contains zip + metadata).
    """
    import zipfile

    src = SCRIPT_DIR / ds["dir"]
    staging = SCRIPT_DIR / f"_staging_{ds['dir']}"
    staging.mkdir(exist_ok=True)

    zip_path = staging / f"{ds['dir']}.zip"

    # Collect all files (excluding debug logs and metadata)
    files = []
    for f in src.rglob("*"):
        if f.is_file() and f.name not in ("download_debug.log", "dataset-metadata.json"):
            files.append(f)

    # Create zip with progress
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for i, fpath in enumerate(files):
            arcname = str(fpath.relative_to(src))
            zf.write(fpath, arcname)
            if progress_callback:
                progress_callback(i + 1, len(files))

    # Write metadata into staging dir
    meta = {
        "title": ds["title"],
        "id": f"{KAGGLE_USERNAME}/{ds['slug']}",
        "licenses": [{"name": "other"}],
        "keywords": ["ecg", "physionet", "hayatin-ritmi", "arrhythmia", "12-lead"],
    }
    meta_path = staging / "dataset-metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return staging


def _cleanup_staging(ds: dict):
    """Remove the staging directory for a dataset."""
    import shutil
    staging = SCRIPT_DIR / f"_staging_{ds['dir']}"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)


def upload_single(ds: dict, dry_run: bool = False) -> dict:
    """
    Upload a single dataset to Kaggle.
    Strategy: zip locally first → upload one file → much faster.
    """
    result = {
        "name": ds["dir"],
        "size": ds["size_bytes"],
        "status": "pending",
        "duration": 0,
        "message": "",
    }

    path = SCRIPT_DIR / ds["dir"]
    if not path.exists():
        result["status"] = "skipped"
        result["message"] = "Directory not found"
        return result

    # Create metadata in original dir too (for reference)
    create_metadata(ds)

    if dry_run:
        result["status"] = "dry-run"
        result["message"] = "Metadata created (dry run — no upload)"
        return result

    # Remove debug logs before zipping
    for log in path.rglob("download_debug.log"):
        log.unlink(missing_ok=True)

    start = time.time()
    staging = None
    try:
        # Step 1: Zip dataset into staging folder
        staging = _zip_dataset(ds)
        zip_time = time.time() - start

        # Step 2: Upload staging folder (contains just 1 zip + metadata)
        api = _get_kaggle_api()

        # Suppress kaggle's internal tqdm to avoid conflict with Rich
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()), \
             contextlib.redirect_stdout(io.StringIO()):
            api.dataset_create_new(
                folder=str(staging),
                dir_mode="skip",
                convert_to_csv=False,
                public=False,
            )

        result["duration"] = time.time() - start
        result["status"] = "success"
        zip_size = sum(f.stat().st_size for f in staging.rglob("*") if f.is_file() and f.suffix == ".zip")
        ratio = (zip_size / ds["size_bytes"] * 100) if ds["size_bytes"] > 0 else 0
        result["message"] = (
            f"Zipped in {zip_time:.0f}s ({fmt_size(zip_size)}, {ratio:.0f}% of orig) → "
            f"kaggle.com/datasets/{KAGGLE_USERNAME}/{ds['slug']}"
        )

    except Exception as e:
        result["duration"] = time.time() - start
        err_msg = str(e)
        if "already exists" in err_msg.lower() or "409" in err_msg:
            result["status"] = "exists"
            result["message"] = "Dataset already exists on Kaggle. Use version update to push changes."
        else:
            result["status"] = "error"
            result["message"] = err_msg[:300]
    finally:
        # Clean up staging
        if staging and staging.exists():
            _cleanup_staging(ds)

    return result


def upload_all(datasets, dry_run=False):
    """Upload all datasets with a live Rich progress display."""
    results = []
    total_bytes = sum(ds["size_bytes"] for ds in datasets if ds["exists"])

    console.print(Rule("[bold cyan]🚀 Upload Progress[/bold cyan]", style="cyan"))
    console.print()

    # Overall progress
    overall_progress = Progress(
        SpinnerColumn("earth"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="bold green", finished_style="bold green"),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.fields[size_done]}/{task.fields[size_total]}[/cyan]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    # Per-dataset progress
    dataset_progress = Progress(
        SpinnerColumn("dots12"),
        TextColumn("  [bold]{task.fields[icon]}[/bold] {task.description:<24s}"),
        BarColumn(bar_width=25, style="cyan", complete_style="green"),
        TextColumn("{task.fields[status]}", justify="right"),
        TextColumn("[dim]{task.fields[size]}[/dim]", justify="right"),
        TextColumn("[dim]{task.fields[elapsed]}[/dim]", justify="right"),
        console=console,
    )

    overall_task = overall_progress.add_task(
        "Overall Upload",
        total=len([d for d in datasets if d["exists"]]),
        size_done="0 B",
        size_total=fmt_size(total_bytes),
    )

    # Create per-dataset tasks
    ds_tasks = {}
    for ds in datasets:
        if ds["exists"]:
            tid = dataset_progress.add_task(
                ds["dir"],
                total=1,
                icon="⏳",
                status="[dim]waiting[/dim]",
                size=fmt_size(ds["size_bytes"]),
                elapsed="",
            )
            ds_tasks[ds["dir"]] = tid

    from rich.console import Group
    progress_group = Group(overall_progress, dataset_progress)

    with Live(progress_group, console=console, refresh_per_second=4):
        uploaded_bytes = 0
        for ds in datasets:
            if not ds["exists"]:
                continue

            tid = ds_tasks[ds["dir"]]

            # Mark as zipping first
            dataset_progress.update(tid, icon="📦", status="[cyan]zipping…[/cyan]")

            # Do the upload (internally: zip → upload → cleanup)
            result = upload_single(ds, dry_run=dry_run)

            # If it was a live upload, the status would have changed internally
            if result["status"] == "pending":
                dataset_progress.update(tid, icon="🔄", status="[yellow]uploading…[/yellow]")

            results.append(result)

            # Update status
            elapsed_str = f"{result['duration']:.0f}s" if result["duration"] > 0 else ""

            status_map = {
                "success":  ("[green]✔ uploaded[/green]", "✅"),
                "exists":   ("[yellow]⚠ exists[/yellow]", "⚠️"),
                "dry-run":  ("[cyan]● dry-run[/cyan]", "🔵"),
                "error":    ("[red]✘ error[/red]", "❌"),
                "timeout":  ("[red]⏰ timeout[/red]", "⏰"),
                "skipped":  ("[dim]● skipped[/dim]", "⏭️"),
            }
            status_text, icon = status_map.get(result["status"], ("[dim]?[/dim]", "❓"))

            dataset_progress.update(
                tid,
                completed=1,
                icon=icon,
                status=status_text,
                elapsed=elapsed_str,
            )

            uploaded_bytes += ds["size_bytes"]
            overall_progress.update(
                overall_task,
                advance=1,
                size_done=fmt_size(uploaded_bytes),
            )

    console.print()
    return results


# ─── SUMMARY DASHBOARD ──────────────────────────────────────────────────────

def show_summary(results):
    """Post-upload summary dashboard."""
    console.print(Rule("[bold cyan]📋 Upload Summary[/bold cyan]", style="cyan"))
    console.print()

    # Counts
    success = sum(1 for r in results if r["status"] == "success")
    exists  = sum(1 for r in results if r["status"] == "exists")
    errors  = sum(1 for r in results if r["status"] in ("error", "timeout"))
    dry_run = sum(1 for r in results if r["status"] == "dry-run")
    total_time = sum(r["duration"] for r in results)
    total_size = sum(r["size"] for r in results)

    # Stats cards
    cards = []

    cards.append(Panel(
        Align.center(Text(str(success), style="bold green" if success else "dim"), vertical="middle"),
        title="[green]✔ Uploaded[/green]", border_style="green", width=16, height=5,
    ))
    cards.append(Panel(
        Align.center(Text(str(exists), style="bold yellow" if exists else "dim"), vertical="middle"),
        title="[yellow]⚠ Exists[/yellow]", border_style="yellow", width=16, height=5,
    ))
    cards.append(Panel(
        Align.center(Text(str(errors), style="bold red" if errors else "dim"), vertical="middle"),
        title="[red]✘ Errors[/red]", border_style="red", width=16, height=5,
    ))
    cards.append(Panel(
        Align.center(Text(fmt_size(total_size), style="bold cyan"), vertical="middle"),
        title="[cyan]📦 Total Size[/cyan]", border_style="cyan", width=16, height=5,
    ))
    cards.append(Panel(
        Align.center(Text(str(timedelta(seconds=int(total_time))), style="bold magenta"), vertical="middle"),
        title="[magenta]⏱ Duration[/magenta]", border_style="magenta", width=16, height=5,
    ))

    console.print(Columns(cards, padding=(0, 1), expand=True))
    console.print()

    # Detailed result table
    table = Table(
        title="[bold]Detailed Results[/bold]",
        box=box.SIMPLE_HEAD,
        border_style="dim",
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Dataset", style="white", min_width=20)
    table.add_column("Size", justify="right", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Time", justify="right", style="magenta")
    table.add_column("Message", style="dim", max_width=60, overflow="ellipsis")

    for r in results:
        status_map = {
            "success": "[green]✔ SUCCESS[/green]",
            "exists":  "[yellow]⚠ EXISTS[/yellow]",
            "dry-run": "[cyan]● DRY RUN[/cyan]",
            "error":   "[red]✘ ERROR[/red]",
            "timeout": "[red]⏰ TIMEOUT[/red]",
            "skipped": "[dim]⏭ SKIPPED[/dim]",
        }
        table.add_row(
            r["name"],
            fmt_size(r["size"]),
            status_map.get(r["status"], r["status"]),
            f"{r['duration']:.1f}s" if r["duration"] > 0 else "—",
            escape(r["message"][:100]) if r["message"] else "",
        )

    console.print(table)
    console.print()

    # Kaggle URLs
    if success > 0 or exists > 0:
        console.print(Panel(
            "\n".join(
                f"  [link=https://www.kaggle.com/datasets/{KAGGLE_USERNAME}/{ds['slug']}]"
                f"https://kaggle.com/datasets/{KAGGLE_USERNAME}/{ds['slug']}[/link]"
                for ds in DATASETS
                if any(r["name"] == ds["dir"] and r["status"] in ("success", "exists") for r in results)
            ),
            title="[bold]🔗 Kaggle Dataset URLs[/bold]",
            border_style="bright_cyan",
            padding=(1, 2),
        ))
        console.print()

    # Upload speed chart (bar chart of per-dataset upload times)
    durations = [(r["name"], r["duration"]) for r in results if r["duration"] > 0]
    if durations:
        max_dur = max(d for _, d in durations)
        chart_text = ""
        for name, dur in durations:
            bar_w = int((dur / max_dur) * 30) if max_dur > 0 else 0
            chart_text += f"  {name:<22s} {'█' * bar_w}{'░' * (30 - bar_w)}  {dur:.0f}s\n"
        console.print(Panel(
            chart_text.rstrip(),
            title="[bold]⏱ Upload Duration per Dataset[/bold]",
            border_style="magenta",
            padding=(0, 1),
        ))
        console.print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload ECG datasets to Kaggle with Rich terminal UI."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Create metadata only, don't upload")
    parser.add_argument("--only", type=str, default=None,
                        help="Upload only a specific dataset (e.g. ptb-xl)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="Show dataset inventory and exit")
    args = parser.parse_args()

    show_header()

    # Scan
    console.print("[bold cyan]🔍 Scanning local dataset directories...[/bold cyan]\n")
    datasets = scan_datasets()

    # Filter if --only
    if args.only:
        datasets = [ds for ds in datasets if ds["dir"] == args.only]
        if not datasets:
            console.print(f"[red]Dataset '{args.only}' not found.[/red]")
            console.print(f"[dim]Available: {', '.join(d['dir'] for d in DATASETS)}[/dim]")
            sys.exit(1)

    # Show inventory
    show_inventory(datasets)
    show_tree(datasets)

    if args.list:
        return

    # Confirm
    uploadable = [ds for ds in datasets if ds["exists"]]
    total_size = sum(ds["size_bytes"] for ds in uploadable)

    if not uploadable:
        console.print("[red]No datasets found on disk. Nothing to upload.[/red]")
        return

    mode_label = "[cyan]DRY RUN[/cyan]" if args.dry_run else "[bold green]LIVE UPLOAD[/bold green]"
    console.print(Panel(
        f"  Mode: {mode_label}\n"
        f"  Datasets: [bold]{len(uploadable)}[/bold]\n"
        f"  Total size: [bold green]{fmt_size(total_size)}[/bold green]\n"
        f"  Target: [bold]kaggle.com/[cyan]{KAGGLE_USERNAME}[/cyan][/bold]",
        title="[bold]🚀 Upload Plan[/bold]",
        border_style="bright_green",
        padding=(0, 2),
    ))
    console.print()

    if not args.dry_run:
        try:
            answer = console.input("[bold yellow]  Proceed with upload? [Y/n] [/bold yellow]").strip().lower()
            if answer and answer not in ("y", "yes"):
                console.print("[dim]Cancelled.[/dim]")
                return
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

    console.print()

    # Upload
    results = upload_all(uploadable, dry_run=args.dry_run)

    # Summary
    show_summary(results)

    console.print(
        Panel(
            Align.center(Text("♥ Hayatın Ritmi — Upload Complete ♥", style="bold white")),
            border_style="bold red",
            box=box.DOUBLE_EDGE,
        )
    )


if __name__ == "__main__":
    main()
