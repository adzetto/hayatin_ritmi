"""
ECG INT8 TFLite Model — Evaluation & Architecture Analysis
===========================================================
- TFLite layer-by-layer analysis (names, types, shapes, quantization params)
- Neuron counts per layer
- Test set inference with 70/15/15 split (same seed as evaluate_model.py)
- Macro/Micro AUC, F1, Precision, Recall
- Per-class AUC comparison vs PyTorch model
- TFLite inference speed benchmark
"""

import os, sys, csv, time, json
import numpy as np
import tensorflow as tf
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── Paths ──
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "ecg-arrhythmia")
MODEL_DIR    = os.path.join(SCRIPT_DIR, "models")
SNOMED_CSV   = os.path.join(DATASET_PATH, "ConditionNames_SNOMED-CT.csv")
CACHE_FILE   = os.path.join(MODEL_DIR, "dataset_cache.npz")
INT8_PATH    = os.path.join(MODEL_DIR, "tflite", "ecg_model_int8.tflite")
FLOAT32_PATH = os.path.join(MODEL_DIR, "tflite", "ecg_model_float32.tflite")
FLOAT16_PATH = os.path.join(MODEL_DIR, "tflite", "ecg_model_float16.tflite")
EVAL_JSON    = os.path.join(MODEL_DIR, "tflite_evaluation_results.json")


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
#  1. TFLite MODEL ANALİZİ
# ═══════════════════════════════════════════════════════════
def analyze_tflite(model_path, model_name="INT8"):
    """Detailed TFLite model analysis: layers, shapes, quantization params, neurons."""
    console.print(Panel.fit(
        f"[bold white]TFLite {model_name} MODEL ANALİZİ[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    # ── Input/Output details ──
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    io_table = Table(box=box.ROUNDED, title="[bold]Girdi / Çıktı[/]",
                     border_style="cyan")
    io_table.add_column("Tür", style="cyan")
    io_table.add_column("İsim", style="white")
    io_table.add_column("Shape", style="yellow")
    io_table.add_column("Dtype", style="green")
    io_table.add_column("Quantization (scale, zp)", style="magenta")

    for inp in input_details:
        q = inp.get('quantization', (0, 0))
        q_params = inp.get('quantization_parameters', {})
        scales = q_params.get('scales', [])
        zps = q_params.get('zero_points', [])
        q_str = f"scale={scales[0]:.6f}, zp={zps[0]}" if len(scales) > 0 else "none"
        io_table.add_row("Input", inp['name'], str(inp['shape']), str(inp['dtype']),
                         q_str)

    for out in output_details:
        q_params = out.get('quantization_parameters', {})
        scales = q_params.get('scales', [])
        zps = q_params.get('zero_points', [])
        q_str = f"scale={scales[0]:.6f}, zp={zps[0]}" if len(scales) > 0 else "none"
        io_table.add_row("Output", out['name'], str(out['shape']), str(out['dtype']),
                         q_str)

    console.print(io_table)

    # ── All tensor details (layer analysis) ──
    tensor_details = interpreter.get_tensor_details()

    layer_table = Table(box=box.ROUNDED, title="[bold]Tüm Katmanlar (Tensor Detayları)[/]",
                        border_style="cyan", show_lines=False)
    layer_table.add_column("#", style="dim", width=4)
    layer_table.add_column("Tensor İsmi", style="cyan", max_width=50, overflow="ellipsis")
    layer_table.add_column("Shape", style="yellow", min_width=20)
    layer_table.add_column("Dtype", style="green", width=10)
    layer_table.add_column("Eleman", style="white", justify="right", width=10)
    layer_table.add_column("Quantized", style="magenta", width=10)

    total_tensors = 0
    total_params = 0
    weight_tensors = []
    conv_layers = []
    linear_layers = []
    bn_layers = []
    activation_count = 0

    for i, t in enumerate(tensor_details):
        name = t['name']
        shape = t['shape']
        dtype = t['dtype']
        n_elements = int(np.prod(shape)) if len(shape) > 0 else 0

        q_params = t.get('quantization_parameters', {})
        scales = q_params.get('scales', [])
        is_quantized = len(scales) > 0 and scales[0] != 0.0

        total_tensors += 1

        # Identify layer types by name patterns
        name_lower = name.lower()

        # Weight/bias tensors (parameters)
        is_weight = False
        if any(kw in name_lower for kw in ['kernel', 'weight', 'bias', 'gamma',
                                             'beta', 'moving_mean', 'moving_variance',
                                             'depthwise', 'pointwise']):
            is_weight = True
            total_params += n_elements
            weight_tensors.append({
                'name': name, 'shape': list(shape), 'elements': n_elements,
                'quantized': is_quantized, 'dtype': str(dtype)
            })

        # Classify conv/linear/bn layers
        if 'conv' in name_lower or 'depthwise' in name_lower:
            if 'kernel' in name_lower or 'weight' in name_lower:
                if 'depthwise' in name_lower:
                    conv_layers.append(('DepthwiseConv1D', name, list(shape)))
                else:
                    conv_layers.append(('Conv1D', name, list(shape)))
        elif 'dense' in name_lower or 'matmul' in name_lower or 'fully_connected' in name_lower:
            if 'kernel' in name_lower or 'weight' in name_lower:
                linear_layers.append(('Dense', name, list(shape)))

        if 'batch_norm' in name_lower or 'batchnorm' in name_lower or 'fused_batch_norm' in name_lower:
            if 'gamma' in name_lower or 'beta' in name_lower:
                bn_layers.append(name)

        if 'relu' in name_lower or 'activation' in name_lower:
            activation_count += 1

        layer_table.add_row(
            str(i),
            name[:50],
            str(list(shape)),
            str(dtype).replace("<class 'numpy.", "").replace("'>", ""),
            f"{n_elements:,}" if n_elements > 0 else "-",
            "✅" if is_quantized else "—",
        )

    console.print(layer_table)

    # ── Neuron analysis from weight tensors ──
    neuron_table = Table(box=box.ROUNDED, title="[bold]Nöron & Parametre Dağılımı[/]",
                         border_style="green")
    neuron_table.add_column("#", style="dim", width=4)
    neuron_table.add_column("Katman", style="cyan", min_width=25)
    neuron_table.add_column("Tür", style="white", width=18)
    neuron_table.add_column("Kernel Shape", style="yellow", min_width=20)
    neuron_table.add_column("Çıkış Nöron", style="bold green", justify="right")
    neuron_table.add_column("Parametre", style="yellow", justify="right")

    total_neurons = 0
    layer_idx = 0

    for layer_type, name, shape in conv_layers:
        layer_idx += 1
        if layer_type == 'DepthwiseConv1D':
            # DW conv: shape is typically [1, kernel, channels, 1] or [filters, kernel, 1]
            out_ch = shape[-2] if len(shape) == 4 else shape[0]
        else:
            # Regular conv: [filters, kernel, in_ch] or [1, 1, in_ch, out_ch]
            out_ch = shape[0] if len(shape) == 3 else shape[-1]
        total_neurons += out_ch
        n_params = int(np.prod(shape))
        neuron_table.add_row(
            str(layer_idx), name[:25], layer_type,
            str(shape), f"{out_ch:,}", f"{n_params:,}"
        )

    for layer_type, name, shape in linear_layers:
        layer_idx += 1
        out_features = shape[-1] if len(shape) >= 2 else shape[0]
        total_neurons += out_features
        n_params = int(np.prod(shape))
        neuron_table.add_row(
            str(layer_idx), name[:25], "Dense/Linear",
            str(shape), f"{out_features:,}", f"{n_params:,}"
        )

    console.print(neuron_table)

    # ── Op count from graph ──
    # Use interpreter to get ops
    ops = set()
    try:
        # TFLite model analysis via flatbuffers
        with open(model_path, 'rb') as f:
            model_bytes = f.read()

        # Alternative: count unique op types from tensor names
        op_types = set()
        for t in tensor_details:
            name = t['name'].lower()
            if 'conv' in name: op_types.add('Conv')
            elif 'depthwise' in name: op_types.add('DepthwiseConv')
            elif 'batch_norm' in name or 'fused_batch' in name: op_types.add('BatchNorm')
            elif 'dense' in name or 'matmul' in name or 'fully_connected' in name: op_types.add('FullyConnected')
            elif 'relu' in name: op_types.add('ReLU')
            elif 'pool' in name: op_types.add('Pool')
            elif 'sigmoid' in name: op_types.add('Sigmoid')
            elif 'add' in name: op_types.add('Add')
            elif 'reshape' in name: op_types.add('Reshape')
            elif 'mean' in name: op_types.add('Mean/GlobalPool')
    except Exception:
        op_types = set()

    # ── Summary table ──
    summary = Table(box=box.SIMPLE_HEAVY, border_style="green",
                    title="[bold]Model Özeti[/]")
    summary.add_column("Metrik", style="cyan")
    summary.add_column("Değer", style="bold white")

    file_size = os.path.getsize(model_path)
    summary.add_row("Dosya Boyutu", f"{file_size / 1024:.1f} KB")
    summary.add_row("Toplam Tensor", f"{total_tensors:,}")
    summary.add_row("Toplam Parametre", f"{total_params:,}")
    summary.add_row("Toplam Nöron (Conv+Dense)", f"{total_neurons:,}")
    summary.add_row("Conv Katman (kernel)", f"{len(conv_layers)}")
    summary.add_row("Dense/Linear Katman", f"{len(linear_layers)}")
    summary.add_row("BatchNorm Tensörleri", f"{len(set(n.rsplit('/', 1)[0] if '/' in n else n for n in bn_layers))}")
    summary.add_row("Quantization", "INT8" if "int8" in model_path.lower() else "Float")
    summary.add_row("Girdi", f"{input_details[0]['shape']} ({input_details[0]['dtype']})")
    summary.add_row("Çıktı", f"{output_details[0]['shape']} ({output_details[0]['dtype']})")
    if op_types:
        summary.add_row("Op Türleri", ", ".join(sorted(op_types)))

    console.print(summary)

    return {
        "file_size_kb": round(file_size / 1024, 1),
        "total_tensors": total_tensors,
        "total_params": total_params,
        "total_neurons": total_neurons,
        "n_conv": len(conv_layers),
        "n_dense": len(linear_layers),
        "input_shape": input_details[0]['shape'].tolist(),
        "input_dtype": str(input_details[0]['dtype']),
        "output_shape": output_details[0]['shape'].tolist(),
        "output_dtype": str(output_details[0]['dtype']),
        "input_details": input_details,
        "output_details": output_details,
    }


# ═══════════════════════════════════════════════════════════
#  2. TEST SET DEĞERLENDİRME
# ═══════════════════════════════════════════════════════════
def evaluate_tflite(model_path, model_info, X_test, Y_test):
    console.print(Panel.fit(
        "[bold white]TFLite INT8 — TEST SET DEĞERLENDİRME[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()

    inp_detail = interpreter.get_input_details()[0]
    out_detail = interpreter.get_output_details()[0]

    inp_dtype = inp_detail['dtype']
    inp_shape = inp_detail['shape']  # e.g., [1, 2500, 12]

    # Quantization params for INT8
    q_params = inp_detail.get('quantization_parameters', {})
    inp_scale = q_params.get('scales', [1.0])[0]
    inp_zp = q_params.get('zero_points', [0])[0]

    # X_test is (N, 12, 2500) — TFLite expects (N, 2500, 12) channels-last
    X_cl = np.transpose(X_test, (0, 2, 1)).astype(np.float32)  # (N, 2500, 12)

    all_preds = []
    n = len(X_cl)

    console.print(f"   [cyan]Test seti:[/] {n:,} kayıt")
    console.print(f"   [cyan]Input:[/] {inp_shape}, dtype={inp_dtype}")
    console.print(f"   [cyan]Quantization:[/] scale={inp_scale:.6f}, zero_point={inp_zp}")
    console.print()

    t0 = time.time()
    for i in range(n):
        sample = X_cl[i:i+1]  # (1, 2500, 12)

        # Quantize input if INT8
        if inp_dtype == np.int8:
            sample = np.clip(sample / inp_scale + inp_zp, -128, 127).astype(np.int8)
        elif inp_dtype == np.uint8:
            sample = np.clip(sample / inp_scale + inp_zp, 0, 255).astype(np.uint8)

        interpreter.set_tensor(inp_detail['index'], sample)
        interpreter.invoke()
        output = interpreter.get_tensor(out_detail['index'])[0]  # (55,)
        all_preds.append(output)

        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            speed = (i + 1) / elapsed
            console.print(f"   [dim]{i+1:,}/{n:,} — {speed:.0f} ECG/s — {elapsed:.1f}s[/]")

    total_time = time.time() - t0
    preds = np.array(all_preds, dtype=np.float32)  # (N, 55)

    # If output is logits (not sigmoid), apply sigmoid
    if preds.max() > 1.0 or preds.min() < 0.0:
        console.print("   [yellow]Logits detected → applying sigmoid[/]")
        preds = 1.0 / (1.0 + np.exp(-preds))

    preds = np.nan_to_num(preds, nan=0.5, posinf=1.0, neginf=0.0)

    console.print(f"\n   [green]✅ {n:,} inference tamamlandı — {total_time:.1f}s ({n/total_time:.0f} ECG/s)[/]\n")

    # ── Metrics ──
    valid_cols = Y_test.sum(0) > 0
    n_active = int(valid_cols.sum())

    Y_valid = Y_test[:, valid_cols]
    P_valid = preds[:, valid_cols]

    macro_auc = roc_auc_score(Y_valid, P_valid, average="macro")
    micro_auc = roc_auc_score(Y_valid, P_valid, average="micro")

    # Binary predictions at threshold=0.5
    preds_bin = (preds >= 0.5).astype(np.float32)

    macro_f1 = f1_score(Y_test, preds_bin, average="macro", zero_division=0)
    micro_f1 = f1_score(Y_test, preds_bin, average="micro", zero_division=0)
    weighted_f1 = f1_score(Y_test, preds_bin, average="weighted", zero_division=0)
    macro_prec = precision_score(Y_test, preds_bin, average="macro", zero_division=0)
    macro_rec = recall_score(Y_test, preds_bin, average="macro", zero_division=0)

    # Sample-level hit rate
    hit = 0
    for i in range(n):
        true_pos = set(np.where(Y_test[i] > 0.5)[0])
        pred_pos = set(np.where(preds_bin[i] > 0.5)[0])
        if len(true_pos) == 0 and len(pred_pos) == 0:
            hit += 1
        elif len(true_pos) > 0 and len(true_pos & pred_pos) > 0:
            hit += 1
    hit_rate = hit / n

    metrics_table = Table(box=box.ROUNDED, title="[bold]Test Set Metrikleri (INT8 TFLite)[/]",
                          border_style="green")
    metrics_table.add_column("Metrik", style="cyan", min_width=20)
    metrics_table.add_column("Değer", style="bold white", justify="right")

    metrics_table.add_row("Macro AUC", f"{macro_auc:.4f}")
    metrics_table.add_row("Micro AUC", f"{micro_auc:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Macro F1", f"{macro_f1:.4f}")
    metrics_table.add_row("Micro F1", f"{micro_f1:.4f}")
    metrics_table.add_row("Weighted F1", f"{weighted_f1:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Macro Precision", f"{macro_prec:.4f}")
    metrics_table.add_row("Macro Recall", f"{macro_rec:.4f}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Sample Hit Rate", f"{hit_rate:.4f}")
    metrics_table.add_row("Aktif Sınıf (test)", f"{n_active} / {NUM_CLASSES}")
    metrics_table.add_row("", "")
    metrics_table.add_row("Toplam Süre", f"{total_time:.1f}s")
    metrics_table.add_row("Ort. Inference", f"{total_time/n*1000:.2f} ms/ECG")
    metrics_table.add_row("Throughput", f"{n/total_time:.0f} ECG/s")

    console.print(metrics_table)

    # ── Per-class AUC ──
    per_class_table = Table(box=box.ROUNDED, title="[bold]Sınıf Bazlı AUC (INT8 TFLite)[/]",
                            border_style="cyan")
    per_class_table.add_column("#", style="dim", width=4)
    per_class_table.add_column("Kondisyon", style="cyan", width=14)
    per_class_table.add_column("AUC", style="bold white", justify="right", width=7)
    per_class_table.add_column("Destek", style="yellow", justify="right", width=7)
    per_class_table.add_column("Bar", style="green", width=22)

    class_aucs = {}
    class_rows = []
    for i in range(NUM_CLASSES):
        support = int(Y_test[:, i].sum())
        if support == 0:
            continue
        try:
            auc_i = roc_auc_score(Y_test[:, i], preds[:, i])
            class_aucs[CONDITION_NAMES[i]] = round(auc_i, 4)
            class_rows.append((auc_i, CONDITION_NAMES[i], support))
        except Exception:
            pass

    class_rows.sort(key=lambda x: x[0], reverse=True)
    for idx, (auc_val, name, support) in enumerate(class_rows):
        bar_len = int(auc_val * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        color = "green" if auc_val >= 0.95 else "yellow" if auc_val >= 0.85 else "red"
        per_class_table.add_row(
            str(idx + 1), name, f"[{color}]{auc_val:.4f}[/]",
            str(support), bar
        )

    console.print(per_class_table)

    return {
        "macro_auc": round(macro_auc, 4),
        "micro_auc": round(micro_auc, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_f1": round(micro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "sample_hit_rate": round(hit_rate, 4),
        "inference_ms": round(total_time / n * 1000, 2),
        "throughput_ecg_s": round(n / total_time, 1),
        "per_class_auc": class_aucs,
    }


# ═══════════════════════════════════════════════════════════
#  3. BENCHMARK (tüm TFLite varyantları)
# ═══════════════════════════════════════════════════════════
def benchmark_tflite_variants(X_sample):
    """Speed benchmark: INT8 vs Float16 vs Float32."""
    console.print(Panel.fit(
        "[bold white]TFLite HIZ KARŞILAŞTIRMASI[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(0, 4),
    ))

    variants = []
    if os.path.exists(INT8_PATH):
        variants.append(("INT8", INT8_PATH))
    if os.path.exists(FLOAT16_PATH):
        variants.append(("Float16", FLOAT16_PATH))
    if os.path.exists(FLOAT32_PATH):
        variants.append(("Float32", FLOAT32_PATH))

    # Use a small sample for benchmarking
    X_bench = np.transpose(X_sample[:100], (0, 2, 1)).astype(np.float32)
    n_warmup = 10
    n_bench = 100

    bench_table = Table(box=box.ROUNDED, title="[bold]Inference Hızı (100 ECG)[/]",
                        border_style="cyan")
    bench_table.add_column("Model", style="cyan", width=12)
    bench_table.add_column("Boyut", style="yellow", justify="right", width=10)
    bench_table.add_column("Ort.", style="bold white", justify="right", width=10)
    bench_table.add_column("Min", style="green", justify="right", width=10)
    bench_table.add_column("Max", style="red", justify="right", width=10)
    bench_table.add_column("ECG/s", style="bold green", justify="right", width=8)

    results = {}
    for name, path in variants:
        interpreter = tf.lite.Interpreter(model_path=path)
        interpreter.allocate_tensors()
        inp = interpreter.get_input_details()[0]
        out = interpreter.get_output_details()[0]
        inp_dtype = inp['dtype']

        q_params = inp.get('quantization_parameters', {})
        scales = q_params.get('scales', np.array([]))
        zps = q_params.get('zero_points', np.array([]))
        scale = float(scales[0]) if len(scales) > 0 else 1.0
        zp = int(zps[0]) if len(zps) > 0 else 0

        # Warmup
        for i in range(n_warmup):
            sample = X_bench[i % len(X_bench):i % len(X_bench) + 1]
            if inp_dtype == np.int8:
                sample = np.clip(sample / scale + zp, -128, 127).astype(np.int8)
            elif inp_dtype == np.float16:
                sample = sample.astype(np.float16)
            interpreter.set_tensor(inp['index'], sample)
            interpreter.invoke()

        # Benchmark
        times = []
        for i in range(n_bench):
            sample = X_bench[i % len(X_bench):i % len(X_bench) + 1]
            if inp_dtype == np.int8:
                sample = np.clip(sample / scale + zp, -128, 127).astype(np.int8)
            elif inp_dtype == np.float16:
                sample = sample.astype(np.float16)

            t0 = time.perf_counter()
            interpreter.set_tensor(inp['index'], sample)
            interpreter.invoke()
            times.append((time.perf_counter() - t0) * 1000)

        avg = np.mean(times)
        size_kb = os.path.getsize(path) / 1024

        bench_table.add_row(
            name, f"{size_kb:.0f} KB",
            f"{avg:.2f} ms", f"{min(times):.2f} ms", f"{max(times):.2f} ms",
            f"{1000/avg:.0f}"
        )
        results[name] = {"avg_ms": round(avg, 2), "size_kb": round(size_kb, 1)}

    console.print(bench_table)
    return results


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    console.print(Panel.fit(
        "[bold white]ECG INT8 TFLite — Değerlendirme & Analiz[/]\n"
        "[cyan]TÜBİTAK 2209-A — Hayatın Ritmi[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE, padding=(1, 4),
    ))

    # ── 1. Architecture analysis ──
    model_info = analyze_tflite(INT8_PATH, "INT8")

    # ── 2. Load dataset + test split (same as evaluate_model.py) ──
    console.print("\n[bold cyan]💾 Dataset yükleniyor...[/]")
    data = np.load(CACHE_FILE, allow_pickle=True)
    X, Y = data["X"], data["Y"]

    # Clean NaN
    nan_mask = ~np.isfinite(X).reshape(X.shape[0], -1).all(axis=1)
    if nan_mask.any():
        console.print(f"[yellow]⚠  {nan_mask.sum()} NaN kayıt temizlendi[/]")
        X, Y = X[~nan_mask], Y[~nan_mask]

    console.print(f"   [green]✅[/] {X.shape[0]:,} kayıt yüklendi\n")

    # 70/15/15 split — same seed/logic as evaluate_model.py
    indices = np.arange(len(X))
    train_idx, temp_idx = train_test_split(indices, test_size=0.30, random_state=42)
    val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42)

    X_test, Y_test = X[test_idx], Y[test_idx]

    split_table = Table(box=box.SIMPLE_HEAVY, title="[bold]Dataset Split (70/15/15)[/]")
    split_table.add_column("Set", style="cyan")
    split_table.add_column("Kayıt", style="white", justify="right")
    split_table.add_column("Oran", style="yellow", justify="right")
    split_table.add_row("Train", f"{len(train_idx):,}", f"{len(train_idx)/len(X)*100:.1f}%")
    split_table.add_row("Val", f"{len(val_idx):,}", f"{len(val_idx)/len(X)*100:.1f}%")
    split_table.add_row("Test", f"{len(test_idx):,}", f"{len(test_idx)/len(X)*100:.1f}%")
    split_table.add_row("[bold]Toplam[/]", f"[bold]{len(X):,}[/]", "[bold]100%[/]")
    console.print(split_table)

    # ── 3. Evaluate INT8 on test set ──
    metrics = evaluate_tflite(INT8_PATH, model_info, X_test, Y_test)

    # ── 4. Speed benchmark ──
    bench_results = benchmark_tflite_variants(X_test)

    # ── 5. Save results ──
    results = {
        "model": "ecg_model_int8.tflite",
        "architecture": model_info,
        "test_metrics": metrics,
        "speed_benchmark": bench_results,
    }
    # Clean non-serializable fields
    if "input_details" in results["architecture"]:
        del results["architecture"]["input_details"]
    if "output_details" in results["architecture"]:
        del results["architecture"]["output_details"]

    with open(EVAL_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]📄 Sonuçlar kaydedildi: {EVAL_JSON}[/]")
    console.print("\n[bold green]✅ TFLite değerlendirme tamamlandı![/]")


if __name__ == "__main__":
    main()
