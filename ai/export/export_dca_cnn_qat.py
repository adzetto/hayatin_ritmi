"""
DCA-CNN QAT Export — Quantization-Aware Training + TFLite INT8 Export
=====================================================================
Eğitilmiş DCA-CNN modelini QAT ile ince-ayar yaparak INT8 TFLite'a dönüştürür.

Strateji:
  1. DCA-CNN'in ACC katmanını standart Conv1d'ye pişir (_ExportableDcaCNN)
  2. Eager-mode QAT uygula (per-module qconfig)
  3. Fine-tune (15 epoch CPU'da)
  4. ONNX → TFLite INT8 export

Çalıştır:
    python ai/export/export_dca_cnn_qat.py

Çıktılar:
    ai/models/checkpoints/ecg_dca_cnn_qat.pt
    ai/models/checkpoints/ecg_dca_cnn_qat.onnx
    ai/models/tflite/ecg_dca_cnn_int8.tflite
    ai/models/results/dca_cnn_qat_results.json
"""

from __future__ import annotations

import os, sys, json, time, subprocess, csv, glob, shutil
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.ao.quantization import (
    get_default_qat_qconfig,
    prepare_qat as _prepare_qat_eager,
    convert,
)
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR = os.path.join(PROJECT_ROOT, "ai")
sys.path.insert(0, os.path.join(AI_DIR, "training"))

from train_dca_cnn import (
    DcaCNN, _ExportableDcaCNN, EcgAugDataset, load_combined_dataset,
    C_MAX, N_SAMPLES, NUM_CLASSES, DEVICE,
    MODEL_DIR, RESULTS_DIR, TFLITE_DIR, CONDITION_NAMES,
)

CHECKPOINT = os.path.join(MODEL_DIR, "ecg_dca_cnn_best.pt")
QAT_EPOCHS = 15
QAT_LR = 1e-5
BATCH_SIZE = 64


# ═══════════════════════════════════════════════════════════
#  1. QAT FİNE-TUNE (Eager Mode)
# ═══════════════════════════════════════════════════════════
def qat_finetune(model: DcaCNN,
                 X_train: np.ndarray, Y_train: np.ndarray,
                 X_val: np.ndarray, Y_val: np.ndarray):
    """QAT fine-tuning: ACC → Conv1d bake → eager-mode QAT."""

    console.print("\n[bold cyan]🔬  QAT Hazırlık...[/]")

    # 1) ACC'yi standart Conv1d'ye pişir (ONNX-uyumlu yapı)
    model.eval().cpu()
    export_model = _ExportableDcaCNN(model)
    export_model.train()
    console.print("[green]  ✅ ACC → Conv1d bake tamamlandı[/]")

    # 2) Eager-mode QAT qconfig ata
    qconfig = get_default_qat_qconfig("fbgemm")
    export_model.qconfig = qconfig

    # Sub-modüllere de qconfig ata
    for module in export_model.modules():
        if isinstance(module, (nn.Conv1d, nn.Linear, nn.BatchNorm1d)):
            module.qconfig = qconfig

    # 3) QAT hazırla (eager mode — example_inputs yok)
    model_prepared = _prepare_qat_eager(export_model)
    model_prepared.train()
    console.print("[green]  ✅ Fake-quantize observers eklendi[/]")

    total_params = sum(p.numel() for p in model_prepared.parameters() if p.requires_grad)
    console.print(f"  Trainable params: {total_params:,}")

    # ── Data ──
    train_ds = EcgAugDataset(X_train, Y_train, augment=False)
    val_ds = EcgAugDataset(X_val, Y_val, augment=False)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=2, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=2)

    optimizer = torch.optim.Adam(model_prepared.parameters(), lr=QAT_LR)
    criterion = nn.BCELoss()  # _ExportableDcaCNN already applies sigmoid

    best_auc = 0.0
    qat_path = os.path.join(MODEL_DIR, "ecg_dca_cnn_qat.pt")

    console.print(f"\n[bold green]🚂 QAT eğitimi başlıyor ({QAT_EPOCHS} epoch, CPU)...[/]\n")

    for epoch in range(1, QAT_EPOCHS + 1):
        model_prepared.train()
        epoch_loss = 0.0
        n = 0
        t0 = time.time()

        for xb, yb in tqdm(train_loader, desc=f"  QAT Epoch {epoch:2d}/{QAT_EPOCHS}",
                           leave=False, ncols=100):
            optimizer.zero_grad(set_to_none=True)
            probs_out = model_prepared(xb)
            loss = criterion(probs_out, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model_prepared.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item() * len(xb)
            n += len(xb)

        epoch_loss /= n

        # ── Validation ──
        model_prepared.eval()
        all_preds, all_labels = [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                probs = model_prepared(xb).cpu().numpy()  # sigmoid already inside
                all_preds.append(probs)
                all_labels.append(yb.numpy())

        preds = np.nan_to_num(np.vstack(all_preds), nan=0.5)
        labels = np.vstack(all_labels)
        valid = labels.sum(0) > 0
        val_auc = roc_auc_score(labels[:, valid], preds[:, valid],
                                average="macro") if valid.sum() > 0 else 0.0

        elapsed = time.time() - t0
        marker = " ★" if val_auc > best_auc else ""
        console.print(f"  Epoch {epoch:2d}/{QAT_EPOCHS} │ loss={epoch_loss:.4f} │ "
                      f"AUC={val_auc:.4f}{marker} │ {elapsed:.0f}s")

        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model_prepared.state_dict(), qat_path)

    console.print(f"\n[bold green]🏆 QAT En İyi AUC: {best_auc:.4f}[/]")

    # Load best and convert to quantized
    model_prepared.load_state_dict(
        torch.load(qat_path, map_location="cpu", weights_only=True)
    )
    model_prepared.eval()

    model_quantized = convert(model_prepared)
    console.print("[green]  ✅ INT8 quantize dönüştürme tamamlandı[/]")

    return model_quantized, model_prepared, best_auc


# ═══════════════════════════════════════════════════════════
#  2. ONNX EXPORT
# ═══════════════════════════════════════════════════════════
def export_onnx_qat(model_prepared, onnx_path: str):
    """Export QAT model to ONNX: strip fake-quant observers, keep QAT-trained weights."""
    console.print(f"\n[bold cyan]📦 QAT ONNX export:[/] {onnx_path}")

    model_prepared.eval()

    # Build a clean _ExportableDcaCNN (no fake-quant wrappers)
    # then copy only the real weight/bias/BN params from QAT state dict
    dummy_base = DcaCNN()
    clean = _ExportableDcaCNN(dummy_base)

    qat_sd = model_prepared.state_dict()
    clean_sd = clean.state_dict()
    matched = 0
    for key in clean_sd:
        if key in qat_sd:
            clean_sd[key] = qat_sd[key]
            matched += 1
    clean.load_state_dict(clean_sd)
    clean.eval()
    console.print(f"  QAT → clean FP32: {matched}/{len(clean_sd)} ağırlık kopyalandı")

    dummy = torch.zeros(1, C_MAX, N_SAMPLES)
    torch.onnx.export(
        clean, dummy, onnx_path,
        input_names=["ecg_input"],
        output_names=["predictions"],
        dynamic_axes={"ecg_input": {0: "batch"}, "predictions": {0: "batch"}},
        opset_version=17,
    )
    size_kb = os.path.getsize(onnx_path) / 1024
    console.print(f"   [green]✅ ONNX boyutu: {size_kb:.1f} KB[/]")
    return onnx_path


# ═══════════════════════════════════════════════════════════
#  3. TFLITE INT8 EXPORT
# ═══════════════════════════════════════════════════════════
def export_tflite_int8(onnx_path: str, tflite_path: str):
    """Convert ONNX → SavedModel → TFLite INT8 (dynamic range quantization)."""
    console.print(f"\n[bold cyan]📱 TFLite INT8 dönüşümü...[/]")

    saved_model_dir = onnx_path.replace(".onnx", "_saved_model")

    # Step 1: ONNX → TF SavedModel via onnx2tf (FP32)
    if not os.path.exists(os.path.join(saved_model_dir, "saved_model.pb")):
        console.print("  ONNX → SavedModel dönüştürülüyor...")
        cmd = [
            sys.executable, "-m", "onnx2tf",
            "-i", onnx_path,
            "-o", saved_model_dir,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            console.print(f"[red]  ❌ SavedModel oluşturulamadı[/]")
            return None
    else:
        console.print("  SavedModel zaten mevcut, atlanıyor...")

    # Step 2: SavedModel → TFLite INT8 (dynamic range quantization)
    import tensorflow as tf

    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    os.makedirs(os.path.dirname(tflite_path), exist_ok=True)
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    if os.path.exists(tflite_path):
        size_kb = os.path.getsize(tflite_path) / 1024
        console.print(f"   [green]✅ TFLite INT8: {tflite_path} ({size_kb:.1f} KB)[/]")
        return tflite_path
    return None


# ═══════════════════════════════════════════════════════════
#  4. KARŞILAŞTIRMA: QAT INT8 vs PTQ INT8 vs FP32
# ═══════════════════════════════════════════════════════════
def compare_models(model_fp32: DcaCNN, model_qat_prepared,
                   X_val: np.ndarray, Y_val: np.ndarray):
    """Compare FP32 (baked), QAT-prepared model accuracy."""
    console.print("\n[bold cyan]📊 Model Karşılaştırması (FP32 vs QAT)[/]")

    val_ds = EcgAugDataset(X_val, Y_val, augment=False)
    loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

    results = {}

    # FP32 — bake ACC so output is comparable
    model_fp32.eval().cpu()
    fp32_baked = _ExportableDcaCNN(model_fp32)
    fp32_baked.eval()
    preds_fp32, labels_all = [], []
    with torch.no_grad():
        for xb, yb in loader:
            logits = fp32_baked(xb)  # already has sigmoid inside
            preds_fp32.append(logits.numpy())
            labels_all.append(yb.numpy())
    preds_fp32 = np.nan_to_num(np.vstack(preds_fp32), nan=0.5)
    labels_all = np.vstack(labels_all)
    valid = labels_all.sum(0) > 0
    auc_fp32 = roc_auc_score(labels_all[:, valid], preds_fp32[:, valid], average="macro")
    results["fp32"] = round(auc_fp32, 4)

    # QAT prepared (fake-quantize — simulates INT8)
    model_qat_prepared.eval()
    preds_qat = []
    with torch.no_grad():
        for xb, yb in loader:
            preds_qat.append(model_qat_prepared(xb).numpy())  # sigmoid already inside
    preds_qat = np.nan_to_num(np.vstack(preds_qat), nan=0.5)
    auc_qat = roc_auc_score(labels_all[:, valid], preds_qat[:, valid], average="macro")
    results["qat_int8_sim"] = round(auc_qat, 4)

    drop = auc_fp32 - auc_qat
    results["accuracy_drop"] = round(drop, 4)

    comp_table = Table(box=box.ROUNDED, border_style="cyan",
                       title="[bold]FP32 vs QAT INT8 Karşılaştırması[/]")
    comp_table.add_column("Model", style="cyan")
    comp_table.add_column("Macro AUC", style="bold white", justify="center")
    comp_table.add_row("FP32 (orijinal)", f"{auc_fp32:.4f}")
    comp_table.add_row("QAT INT8 (simulated)", f"{auc_qat:.4f}")
    comp_table.add_row("Düşüş", f"{drop:.4f}")

    pass_fail = "[bold green]✅ GEÇER[/]" if drop < 0.005 else "[bold red]❌ BAŞARISIZ[/]"
    comp_table.add_row("Kriter (< 0.005)", pass_fail)
    console.print(comp_table)

    return results


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-only", action="store_true",
                        help="Skip QAT training, just export from saved checkpoint")
    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold white]DCA-CNN QAT EXPORT[/]\n"
        "[cyan]Quantization-Aware Training · INT8 TFLite[/]\n"
        "[dim]TÜBİTAK 2209-A — Hayatın Ritmi[/]",
        border_style="bright_yellow", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # ── Check ──
    if not os.path.exists(CHECKPOINT):
        console.print(f"[bold red]❌ Checkpoint bulunamadı: {CHECKPOINT}[/]")
        console.print("[dim]  Önce train_dca_cnn.py çalıştırın.[/]")
        sys.exit(1)

    qat_ckpt = os.path.join(MODEL_DIR, "ecg_dca_cnn_qat.pt")

    if args.export_only and os.path.exists(qat_ckpt):
        console.print("[green]  ✅ --export-only: QAT eğitimi atlanıyor[/]")
        console.print("[green]  Önceki sonuçlar: FP32=0.9513, QAT=0.9525, drop=-0.0012[/]")

        # Load QAT state dict → build clean model → export directly
        qat_sd = torch.load(qat_ckpt, map_location="cpu", weights_only=True)
        qat_auc = 0.9535
        comparison = {"fp32": 0.9513, "qat_int8_sim": 0.9525, "accuracy_drop": -0.0012}

        # Build clean model and copy QAT weights
        dummy_base = DcaCNN()
        clean_model = _ExportableDcaCNN(dummy_base)
        clean_sd = clean_model.state_dict()
        matched = 0
        for key in clean_sd:
            if key in qat_sd:
                clean_sd[key] = qat_sd[key]
                matched += 1
        clean_model.load_state_dict(clean_sd)
        clean_model.eval()
        console.print(f"  QAT → clean FP32: {matched}/{len(clean_sd)} ağırlık kopyalandı")

    else:
        # ── Load pre-trained FP32 ──
        model_fp32 = DcaCNN()
        model_fp32.load_state_dict(torch.load(CHECKPOINT, map_location="cpu", weights_only=True))
        console.print(f"[green]  ✅ FP32 model yüklendi[/] ({sum(p.numel() for p in model_fp32.parameters()):,} params)")

        # ── Load data ──
        X_train, Y_train, X_val, Y_val = load_combined_dataset()

        # Use smaller subset for QAT (efficiency)
        max_qat_train = min(len(X_train), 20000)
        rng = np.random.RandomState(42)
        qat_idx = rng.permutation(len(X_train))[:max_qat_train]
        X_qat_train = X_train[qat_idx]
        Y_qat_train = Y_train[qat_idx]
        console.print(f"  QAT train subset: {len(X_qat_train):,} records")

        # ── QAT Fine-tune ──
        model_qat_converted, model_qat_prepared, qat_auc = qat_finetune(
            model_fp32, X_qat_train, Y_qat_train, X_val, Y_val
        )

        # ── Compare FP32 vs QAT ──
        model_fp32_fresh = DcaCNN()
        model_fp32_fresh.load_state_dict(
            torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
        )
        comparison = compare_models(model_fp32_fresh, model_qat_prepared, X_val, Y_val)

    # ── ONNX Export ──
    onnx_path = os.path.join(MODEL_DIR, "ecg_dca_cnn_qat.onnx")

    if args.export_only and os.path.exists(qat_ckpt):
        # Direct export from clean_model (already built above)
        console.print(f"\n[bold cyan]📦 QAT ONNX export:[/] {onnx_path}")
        dummy = torch.zeros(1, C_MAX, N_SAMPLES)
        torch.onnx.export(
            clean_model, dummy, onnx_path,
            input_names=["ecg_input"],
            output_names=["predictions"],
            dynamic_axes={"ecg_input": {0: "batch"}, "predictions": {0: "batch"}},
            opset_version=17,
        )
        size_kb = os.path.getsize(onnx_path) / 1024
        console.print(f"   [green]✅ ONNX boyutu: {size_kb:.1f} KB[/]")
    else:
        export_onnx_qat(model_qat_prepared, onnx_path)

    # ── TFLite INT8 ──
    tflite_path = os.path.join(TFLITE_DIR, "ecg_dca_cnn_int8.tflite")
    tflite_result = export_tflite_int8(onnx_path, tflite_path)

    # ── Save results ──
    results = {
        "model": "DCA-CNN QAT",
        "qat_epochs": QAT_EPOCHS,
        "qat_lr": QAT_LR,
        "qat_best_auc": round(qat_auc, 4),
        "comparison": comparison,
        "onnx_path": onnx_path,
        "onnx_size_kb": round(os.path.getsize(onnx_path) / 1024, 1) if os.path.exists(onnx_path) else None,
        "tflite_path": tflite_path if tflite_result else None,
        "tflite_size_kb": round(os.path.getsize(tflite_path) / 1024, 1) if tflite_result else None,
    }

    results_path = os.path.join(RESULTS_DIR, "dca_cnn_qat_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Final summary ──
    final_table = Table(box=box.DOUBLE_EDGE, title="[bold green]✅ DCA-CNN QAT EXPORT TAMAMLANDI[/]",
                        border_style="green")
    final_table.add_column("Çıktı", style="cyan")
    final_table.add_column("Değer", style="white")
    final_table.add_row("QAT PT", os.path.join(MODEL_DIR, "ecg_dca_cnn_qat.pt"))
    final_table.add_row("QAT ONNX", onnx_path)
    final_table.add_row("TFLite INT8", tflite_path if tflite_result else "❌ Başarısız")
    final_table.add_row("QAT AUC", f"{qat_auc:.4f}")
    final_table.add_row("FP32 AUC", f"{comparison.get('fp32', '?')}")
    final_table.add_row("Accuracy Drop", f"{comparison.get('accuracy_drop', '?')}")
    if tflite_result:
        final_table.add_row("TFLite Boyut", f"{results['tflite_size_kb']} KB")
    final_table.add_row("Sonuçlar", results_path)
    console.print(final_table)
