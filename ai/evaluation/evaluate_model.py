"""
ECG Model Değerlendirme & Benchmark Scripti
============================================
- Train / Val / Test split (70/15/15)
- Detaylı model mimarisi analizi (layer, nöron, parametre)
- GPU/CPU inference hızı benchmark
- Per-class AUC, F1, Precision, Recall
- Confusion matrix + raporlama
"""

import os, sys, time, csv, json
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, Subset
from sklearn.metrics import (
    roc_auc_score, f1_score, precision_score, recall_score,
    classification_report, multilabel_confusion_matrix
)
from sklearn.model_selection import train_test_split
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── Paths ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "ecg-arrhythmia")
MODEL_DIR    = os.path.join(AI_DIR, "models", "checkpoints")
RESULTS_DIR  = os.path.join(AI_DIR, "models", "results")
CACHE_DIR    = os.path.join(AI_DIR, "cache")
SNOMED_CSV   = os.path.join(DATASET_PATH, "ConditionNames_SNOMED-CT.csv")
CACHE_FILE   = os.path.join(CACHE_DIR, "dataset_cache.npz")
BEST_PT      = os.path.join(MODEL_DIR, "ecg_best.pt")
ONNX_PATH    = os.path.join(MODEL_DIR, "ecg_model.onnx")

FS_TARGET = 250
N_SAMPLES = 2500
N_LEADS   = 12
DEVICE    = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ═══════════════════════════════════════════════════════════
#  SNOMED Labels
# ═══════════════════════════════════════════════════════════
def load_snomed_map():
    codes, names = [], []
    with open(SNOMED_CSV, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            codes.append(int(row["Snomed_CT"]))
            names.append(row["Acronym Name"])
    return {code: i for i, code in enumerate(codes)}, names

SNOMED_MAP, CONDITION_NAMES = load_snomed_map()
NUM_CLASSES = len(SNOMED_MAP)

# ═══════════════════════════════════════════════════════════
#  Model (same architecture as training)
# ═══════════════════════════════════════════════════════════
class DSConv1d(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=7, stride=1):
        super().__init__()
        self.dw = nn.Conv1d(in_ch, in_ch, kernel_size, stride=stride,
                            padding=kernel_size // 2, groups=in_ch, bias=False)
        self.bn1 = nn.BatchNorm1d(in_ch)
        self.pw  = nn.Conv1d(in_ch, out_ch, 1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU6()

    def forward(self, x):
        x = self.act(self.bn1(self.dw(x)))
        x = self.act(self.bn2(self.pw(x)))
        return x

class EcgDSCNN(nn.Module):
    def __init__(self, n_leads=N_LEADS, n_classes=NUM_CLASSES):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(n_leads, 32, 15, stride=2, padding=7, bias=False),
            nn.BatchNorm1d(32),
            nn.ReLU6(),
        )
        self.blocks = nn.Sequential(
            DSConv1d(32,  64,  kernel_size=7, stride=2),
            DSConv1d(64,  128, kernel_size=7, stride=2),
            DSConv1d(128, 128, kernel_size=5, stride=2),
            DSConv1d(128, 256, kernel_size=5, stride=2),
            DSConv1d(256, 256, kernel_size=3, stride=2),
        )
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU6(),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        return self.head(x)

class EcgDataset(Dataset):
    def __init__(self, X, Y):
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)
    def __len__(self): return len(self.X)
    def __getitem__(self, idx): return self.X[idx], self.Y[idx]


# ═══════════════════════════════════════════════════════════
#  1. MODEL MİMARİSİ ANALİZİ
# ═══════════════════════════════════════════════════════════
def analyze_architecture(model):
    console.print(Panel.fit(
        "[bold white]MODEL MİMARİSİ ANALİZİ[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    # ── Layer-by-layer breakdown ──
    layer_table = Table(box=box.ROUNDED, title="[bold]Layer Detayları[/]",
                        border_style="cyan", title_style="bold")
    layer_table.add_column("#", style="dim", width=4)
    layer_table.add_column("Layer", style="cyan", min_width=30)
    layer_table.add_column("Output Shape", style="white", min_width=18)
    layer_table.add_column("Param", style="yellow", justify="right")
    layer_table.add_column("Nöron", style="green", justify="right")

    # Run a dummy forward to capture shapes
    hooks = []
    layer_info = []

    def make_hook(name):
        def hook(module, inp, out):
            if isinstance(out, torch.Tensor):
                params = sum(p.numel() for p in module.parameters())
                # "neurons" = output channels (for conv/linear) or features
                if hasattr(module, 'out_channels'):
                    neurons = module.out_channels
                elif hasattr(module, 'out_features'):
                    neurons = module.out_features
                elif hasattr(module, 'num_features'):
                    neurons = module.num_features
                else:
                    neurons = out.shape[1] if out.dim() > 1 else out.shape[0]
                layer_info.append({
                    "name": name,
                    "shape": str(list(out.shape)),
                    "params": params,
                    "neurons": neurons,
                    "type": module.__class__.__name__,
                })
        return hook

    idx = 0
    for name, module in model.named_modules():
        if isinstance(module, (nn.Conv1d, nn.Linear, nn.BatchNorm1d,
                               nn.AdaptiveAvgPool1d, nn.Dropout, nn.Flatten)):
            h = module.register_forward_hook(make_hook(name))
            hooks.append(h)

    model.eval()
    with torch.no_grad():
        dummy = torch.zeros(1, N_LEADS, N_SAMPLES).to(DEVICE)
        model(dummy)

    for h in hooks:
        h.remove()

    total_params = 0
    total_neurons = 0
    for i, info in enumerate(layer_info):
        layer_table.add_row(
            str(i + 1),
            f"[dim]{info['name']}[/] ({info['type']})",
            info["shape"],
            f"{info['params']:,}" if info['params'] > 0 else "-",
            f"{info['neurons']:,}" if info['type'] not in ('Dropout', 'Flatten', 'AdaptiveAvgPool1d') else "-",
        )
        total_params += info['params']
        if info['type'] not in ('Dropout', 'Flatten', 'AdaptiveAvgPool1d', 'BatchNorm1d'):
            total_neurons += info['neurons']

    console.print(layer_table)

    # ── Summary table ──
    summary = Table(box=box.SIMPLE_HEAVY, border_style="green",
                    title="[bold]Model Özeti[/]")
    summary.add_column("Metrik", style="cyan")
    summary.add_column("Değer", style="bold white")

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    non_trainable = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    total = trainable + non_trainable

    # Count specific layer types
    n_conv = sum(1 for m in model.modules() if isinstance(m, nn.Conv1d))
    n_bn = sum(1 for m in model.modules() if isinstance(m, nn.BatchNorm1d))
    n_linear = sum(1 for m in model.modules() if isinstance(m, nn.Linear))
    n_relu = sum(1 for m in model.modules() if isinstance(m, nn.ReLU6))
    n_dropout = sum(1 for m in model.modules() if isinstance(m, nn.Dropout))

    # Model sizes
    pt_size = os.path.getsize(BEST_PT) / 1024 if os.path.exists(BEST_PT) else 0
    onnx_size = os.path.getsize(ONNX_PATH) / 1024 if os.path.exists(ONNX_PATH) else 0

    summary.add_row("Toplam Parametre", f"{total:,}")
    summary.add_row("Eğitilebilir Parametre", f"{trainable:,}")
    summary.add_row("Sabit Parametre", f"{non_trainable:,}")
    summary.add_row("Toplam Nöron (Conv+Linear)", f"{total_neurons:,}")
    summary.add_row("", "")
    summary.add_row("Conv1d Katmanları", f"{n_conv}")
    summary.add_row("BatchNorm1d Katmanları", f"{n_bn}")
    summary.add_row("Linear (FC) Katmanları", f"{n_linear}")
    summary.add_row("ReLU6 Aktivasyonları", f"{n_relu}")
    summary.add_row("Dropout Katmanları", f"{n_dropout}")
    summary.add_row("", "")
    summary.add_row("Girdi Boyutu", f"(1, {N_LEADS}, {N_SAMPLES}) = {N_LEADS*N_SAMPLES:,} değer")
    summary.add_row("Çıktı Boyutu", f"(1, {NUM_CLASSES}) — {NUM_CLASSES} sınıf sigmoid")
    summary.add_row("", "")
    summary.add_row("PT Dosya Boyutu", f"{pt_size:.1f} KB")
    summary.add_row("ONNX Dosya Boyutu", f"{onnx_size:.1f} KB")

    # Estimated FLOPs (approximate)
    flops = estimate_flops(model)
    if flops > 1e6:
        summary.add_row("Tahmini FLOPs", f"{flops/1e6:.1f} MFLOPs")
    else:
        summary.add_row("Tahmini FLOPs", f"{flops:,.0f}")

    console.print(summary)

    return total, trainable


def estimate_flops(model):
    """Rough FLOPs estimation for Conv1d + Linear layers."""
    flops = 0
    hooks = []
    def hook_fn(module, inp, out):
        nonlocal flops
        if isinstance(module, nn.Conv1d):
            # FLOPs = 2 * Cout * Cin/groups * K * Lout
            batch, _, l_out = out.shape
            cin = module.in_channels
            cout = module.out_channels
            k = module.kernel_size[0]
            groups = module.groups
            flops += 2 * cout * (cin // groups) * k * l_out
        elif isinstance(module, nn.Linear):
            flops += 2 * module.in_features * module.out_features

    for m in model.modules():
        if isinstance(m, (nn.Conv1d, nn.Linear)):
            hooks.append(m.register_forward_hook(hook_fn))

    model.eval()
    with torch.no_grad():
        model(torch.zeros(1, N_LEADS, N_SAMPLES).to(DEVICE))

    for h in hooks:
        h.remove()
    return flops


# ═══════════════════════════════════════════════════════════
#  2. INFERENCE HIZ BENCHMARKı
# ═══════════════════════════════════════════════════════════
def benchmark_speed(model, n_warmup=20, n_runs=100):
    console.print(Panel.fit(
        "[bold white]INFERENCE HIZ BENCHMARKı[/]",
        border_style="bright_blue", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    model.eval()
    dummy = torch.zeros(1, N_LEADS, N_SAMPLES).to(DEVICE)

    results = {}

    # ── GPU Benchmark ──
    if DEVICE.type == "cuda":
        # Warmup
        for _ in range(n_warmup):
            with torch.no_grad():
                model(dummy)
        torch.cuda.synchronize()

        # Timed runs
        times = []
        for _ in range(n_runs):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            with torch.no_grad():
                model(dummy)
            torch.cuda.synchronize()
            times.append((time.perf_counter() - t0) * 1000)  # ms

        results["GPU single"] = times

        # Batch benchmark
        for bs in [1, 8, 32, 128]:
            batch_dummy = torch.zeros(bs, N_LEADS, N_SAMPLES).to(DEVICE)
            for _ in range(5):
                with torch.no_grad():
                    model(batch_dummy)
            torch.cuda.synchronize()

            btimes = []
            for _ in range(30):
                torch.cuda.synchronize()
                t0 = time.perf_counter()
                with torch.no_grad():
                    model(batch_dummy)
                torch.cuda.synchronize()
                btimes.append((time.perf_counter() - t0) * 1000)
            results[f"GPU batch={bs}"] = btimes

    # ── CPU Benchmark ──
    model_cpu = model.cpu()
    dummy_cpu = torch.zeros(1, N_LEADS, N_SAMPLES)

    for _ in range(5):
        with torch.no_grad():
            model_cpu(dummy_cpu)

    cpu_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        with torch.no_grad():
            model_cpu(dummy_cpu)
        cpu_times.append((time.perf_counter() - t0) * 1000)
    results["CPU single"] = cpu_times

    # Move model back to GPU
    model.to(DEVICE)

    # ── ONNX Runtime Benchmark ──
    onnx_times = None
    if os.path.exists(ONNX_PATH):
        try:
            import onnxruntime as ort
            sess = ort.InferenceSession(ONNX_PATH, providers=["CPUExecutionProvider"])
            onnx_input = {sess.get_inputs()[0].name: np.zeros((1, N_LEADS, N_SAMPLES), dtype=np.float32)}

            for _ in range(10):
                sess.run(None, onnx_input)

            onnx_times = []
            for _ in range(50):
                t0 = time.perf_counter()
                sess.run(None, onnx_input)
                onnx_times.append((time.perf_counter() - t0) * 1000)
            results["ONNX-RT CPU"] = onnx_times
        except Exception as e:
            console.print(f"[yellow]⚠ ONNX Runtime benchmark atlandı: {e}[/]")

    # ── Display results ──
    speed_table = Table(box=box.ROUNDED, title="[bold]Inference Süreleri[/]",
                        border_style="blue")
    speed_table.add_column("Backend", style="cyan")
    speed_table.add_column("Ortalama", style="bold green", justify="right")
    speed_table.add_column("Medyan", style="green", justify="right")
    speed_table.add_column("Min", style="dim", justify="right")
    speed_table.add_column("Max", style="dim", justify="right")
    speed_table.add_column("Std", style="dim", justify="right")
    speed_table.add_column("Throughput", style="yellow", justify="right")

    for name, times in results.items():
        arr = np.array(times)
        # Extract batch size for throughput calc
        if "batch=" in name:
            bs = int(name.split("=")[1])
        else:
            bs = 1
        throughput = bs / (arr.mean() / 1000)  # samples/sec

        speed_table.add_row(
            name,
            f"{arr.mean():.2f} ms",
            f"{np.median(arr):.2f} ms",
            f"{arr.min():.2f} ms",
            f"{arr.max():.2f} ms",
            f"{arr.std():.2f} ms",
            f"{throughput:.0f} ECG/s",
        )

    console.print(speed_table)
    return results


# ═══════════════════════════════════════════════════════════
#  3. TEST SET DEĞERLENDİRME
# ═══════════════════════════════════════════════════════════
def evaluate_on_test(model, X, Y):
    console.print(Panel.fit(
        "[bold white]TEST SET DEĞERLENDİRME[/]",
        border_style="bright_green", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    # ── 70/15/15 split ──
    indices = np.arange(len(X))
    train_idx, temp_idx = train_test_split(indices, test_size=0.30, random_state=42)
    val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42)

    split_table = Table(box=box.SIMPLE_HEAVY, title="[bold]Dataset Split (70/15/15)[/]",
                        border_style="cyan")
    split_table.add_column("Set", style="cyan")
    split_table.add_column("Kayıt", style="bold white", justify="right")
    split_table.add_column("Oran", style="dim", justify="right")
    split_table.add_row("Train", f"{len(train_idx):,}", f"{len(train_idx)/len(X)*100:.1f}%")
    split_table.add_row("Validation", f"{len(val_idx):,}", f"{len(val_idx)/len(X)*100:.1f}%")
    split_table.add_row("[bold green]Test[/]", f"[bold green]{len(test_idx):,}[/]", f"[bold green]{len(test_idx)/len(X)*100:.1f}%[/]")
    split_table.add_row("[dim]Toplam[/]", f"[dim]{len(X):,}[/]", "[dim]100%[/]")
    console.print(split_table)

    # ── Inference on test set ──
    X_test = torch.from_numpy(X[test_idx]).to(DEVICE)
    Y_test = Y[test_idx]

    model.eval()
    all_preds = []
    bs = 256
    with torch.no_grad():
        for i in range(0, len(X_test), bs):
            batch = X_test[i:i+bs]
            logits = model(batch)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_preds.append(probs)

    preds = np.vstack(all_preds)
    preds = np.nan_to_num(preds, nan=0.5, posinf=1.0, neginf=0.0)

    # ── Metrics ──
    # Threshold 0.5 for binary predictions
    preds_bin = (preds > 0.5).astype(np.float32)

    # Per-class AUC
    valid_cols = Y_test.sum(0) > 0  # classes that appear in test set
    n_valid = valid_cols.sum()

    macro_auc = roc_auc_score(Y_test[:, valid_cols], preds[:, valid_cols],
                               average="macro") if n_valid > 0 else 0.0
    micro_auc = roc_auc_score(Y_test[:, valid_cols], preds[:, valid_cols],
                               average="micro") if n_valid > 0 else 0.0

    # F1 scores
    macro_f1 = f1_score(Y_test, preds_bin, average="macro", zero_division=0)
    micro_f1 = f1_score(Y_test, preds_bin, average="micro", zero_division=0)
    weighted_f1 = f1_score(Y_test, preds_bin, average="weighted", zero_division=0)

    macro_prec = precision_score(Y_test, preds_bin, average="macro", zero_division=0)
    macro_rec = recall_score(Y_test, preds_bin, average="macro", zero_division=0)

    # Samples with at least one correct prediction
    sample_acc = ((preds_bin * Y_test).sum(1) > 0).mean()

    # Overall metrics table
    metrics_table = Table(box=box.ROUNDED, title="[bold]Test Set Metrikleri[/]",
                          border_style="green")
    metrics_table.add_column("Metrik", style="cyan")
    metrics_table.add_column("Değer", style="bold white", justify="right")

    metrics_table.add_row("[bold]Macro AUC[/]", f"[bold green]{macro_auc:.4f}[/]")
    metrics_table.add_row("Micro AUC", f"{micro_auc:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("[bold]Macro F1[/]", f"[bold]{macro_f1:.4f}[/]")
    metrics_table.add_row("Micro F1", f"{micro_f1:.4f}")
    metrics_table.add_row("Weighted F1", f"{weighted_f1:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Macro Precision", f"{macro_prec:.4f}")
    metrics_table.add_row("Macro Recall", f"{macro_rec:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Sample Hit Rate", f"{sample_acc:.4f}")
    metrics_table.add_row("Aktif Sınıf (test)", f"{int(n_valid)} / {NUM_CLASSES}")

    console.print(metrics_table)

    # ── Per-class AUC Table (top conditions) ──
    per_class_auc = []
    for c in range(NUM_CLASSES):
        if Y_test[:, c].sum() > 0:
            try:
                auc = roc_auc_score(Y_test[:, c], preds[:, c])
            except ValueError:
                auc = 0.0
            support = int(Y_test[:, c].sum())
            per_class_auc.append((CONDITION_NAMES[c], auc, support))

    per_class_auc.sort(key=lambda x: -x[1])

    cls_table = Table(box=box.ROUNDED, title="[bold]Sınıf Bazlı AUC (test seti)[/]",
                      border_style="yellow")
    cls_table.add_column("#", style="dim", width=4)
    cls_table.add_column("Kondisyon", style="cyan", min_width=12)
    cls_table.add_column("AUC", style="bold green", justify="right")
    cls_table.add_column("Destek", style="dim", justify="right")
    cls_table.add_column("Bar", min_width=20)

    for i, (name, auc, support) in enumerate(per_class_auc):
        bar_len = int(auc * 20)
        if auc >= 0.95:
            color = "green"
        elif auc >= 0.85:
            color = "yellow"
        elif auc >= 0.70:
            color = "red"
        else:
            color = "dim red"
        bar = f"[{color}]{'█' * bar_len}{'░' * (20 - bar_len)}[/]"
        cls_table.add_row(str(i + 1), name, f"{auc:.4f}", str(support), bar)

    console.print(cls_table)

    # ── Label distribution ──
    dist_table = Table(box=box.SIMPLE, title="[bold]Test Seti Label Dağılımı (Top 15)[/]",
                       border_style="dim")
    dist_table.add_column("Kondisyon", style="cyan")
    dist_table.add_column("Sayı", style="white", justify="right")
    dist_table.add_column("Oran", style="dim", justify="right")

    class_counts = [(CONDITION_NAMES[c], int(Y_test[:, c].sum())) for c in range(NUM_CLASSES)]
    class_counts.sort(key=lambda x: -x[1])
    for name, count in class_counts[:15]:
        dist_table.add_row(name, str(count), f"{count/len(Y_test)*100:.2f}%")

    console.print(dist_table)

    return {
        "macro_auc": macro_auc,
        "micro_auc": micro_auc,
        "macro_f1": macro_f1,
        "micro_f1": micro_f1,
        "weighted_f1": weighted_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "n_test": len(test_idx),
        "per_class_auc": per_class_auc,
    }


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold white]ECG DS-1D-CNN  —  Model Değerlendirme & Benchmark[/]\n"
        "[dim]TÜBİTAK 2209-A — Hayatın Ritmi[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # ── Load model ──
    console.print(f"\n[bold cyan]📦 Model yükleniyor:[/] [dim]{BEST_PT}[/]")
    model = EcgDSCNN().to(DEVICE)
    model.load_state_dict(torch.load(BEST_PT, map_location=DEVICE, weights_only=True))
    model.eval()
    console.print("[green]✅ Model yüklendi[/]\n")

    # 1. Architecture analysis
    analyze_architecture(model)

    # 2. Speed benchmark
    benchmark_speed(model)

    # 3. Load dataset from cache + test evaluation
    if os.path.exists(CACHE_FILE):
        console.print(f"\n[bold cyan]💾 Dataset önbellekten yükleniyor...[/]")
        data = np.load(CACHE_FILE, allow_pickle=True)
        X, Y = data["X"], data["Y"]
        # Clean NaN
        nan_mask = ~np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
        if nan_mask.any():
            X, Y = X[~nan_mask], Y[~nan_mask]
        console.print(f"[green]✅ {X.shape[0]:,} kayıt yüklendi[/]\n")

        metrics = evaluate_on_test(model, X, Y)

        # Save evaluation results
        eval_path = os.path.join(RESULTS_DIR, "evaluation_results.json")
        save_metrics = {k: v for k, v in metrics.items() if k != "per_class_auc"}
        save_metrics["per_class_auc"] = [
            {"condition": n, "auc": round(a, 4), "support": s}
            for n, a, s in metrics["per_class_auc"]
        ]
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(save_metrics, f, indent=2, ensure_ascii=False)
        console.print(f"\n[green]📄 Sonuçlar kaydedildi:[/] [dim]{eval_path}[/]")
    else:
        console.print("[red]❌ dataset_cache.npz bulunamadı! Önce train scriptini çalıştırın.[/]")

    console.print("\n[bold green]✅ Değerlendirme tamamlandı![/]")
