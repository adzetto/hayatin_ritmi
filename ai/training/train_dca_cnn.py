"""
DCA-CNN — Dynamic Channel-Aware Convolutional Network
======================================================
Araştırma Önerisi §4: Dinamik Kanal Adaptif Derin Öğrenme Mimarisi

Modelin temel yeniliği: tek bir eğitilmiş ağ ile 1, 3 veya 12 kanal
EKG girişini kabul edebilme yeteneği.  ACC (Adaptive Channel Convolution),
öğrenilebilir kapı mekanizması, SE dikkat bloğu ve faz regülarizasyonu
bu esnekliği sağlar.

Çalıştır:
    python ai/training/train_dca_cnn.py

Çıktılar:
    ai/models/checkpoints/ecg_dca_cnn_best.pt
    ai/models/checkpoints/ecg_dca_cnn.onnx
    ai/models/results/training_log_dca_cnn.csv
    ai/models/results/dca_cnn_summary.json
"""

from __future__ import annotations

import os, sys, csv, time, json, glob, hashlib, math
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.amp import GradScaler, autocast
from scipy.signal import butter, filtfilt, resample
import wfdb
from sklearn.metrics import roc_auc_score
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── .env'den token oku ──────────────────────────────────────
def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ═══════════════════════════════════════════════════════════
#  YAPILANDIRMA
# ═══════════════════════════════════════════════════════════
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
DATASET_DIR  = os.path.join(PROJECT_ROOT, "dataset")
SPH_PATH     = os.path.join(DATASET_DIR, "ecg-arrhythmia")
MODEL_DIR    = os.path.join(AI_DIR, "models", "checkpoints")
RESULTS_DIR  = os.path.join(AI_DIR, "models", "results")
TFLITE_DIR   = os.path.join(AI_DIR, "models", "tflite")
CACHE_DIR    = os.path.join(AI_DIR, "cache")
SNOMED_CSV   = os.path.join(SPH_PATH, "ConditionNames_SNOMED-CT.csv")

EXTERNAL_DATASETS = {
    "cpsc2018":         os.path.join(DATASET_DIR, "cpsc2018"),
    "cpsc2018-extra":   os.path.join(DATASET_DIR, "cpsc2018-extra"),
    "georgia":          os.path.join(DATASET_DIR, "georgia"),
    "chapman-shaoxing": os.path.join(DATASET_DIR, "chapman-shaoxing"),
    "ningbo":           os.path.join(DATASET_DIR, "ningbo"),
}

HF_TOKEN   = os.environ.get("HF_TOKEN", "")
HF_REPO_ID = "adzetto/ecg-arrhythmia-classifier"

FS_ORIGINAL = 500
FS_TARGET   = 250
N_SAMPLES   = FS_TARGET * 10   # 2500
N_LEADS     = 12
C_MAX       = 12               # Maksimum kanal sayısı
BATCH_SIZE  = 128
EPOCHS      = 50
LR          = 1e-3
EARLY_STOP  = 10
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Kanal dropout olasılıkları (eğitim)
CHAN_DROP_PROBS = {12: 0.50, 3: 0.25, 1: 0.25}
# Lead I=0, Lead II=1, Lead III=2 (Einthoven)
LEAD_CONFIGS = {
    12: list(range(12)),
    3:  [0, 1, 2],       # I, II, III
    1:  [1],              # Lead II
}

# Kayıp ağırlıkları
LAMBDA_GATE  = 0.01
LAMBDA_PHASE = 0.01

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TFLITE_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  1. SNOMED-CT LABEL MAP
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
#  2. ÖN İŞLEME + VERİ YÜKLEME
# ═══════════════════════════════════════════════════════════
def bandpass(sig, fs=500, lo=0.5, hi=40.0, order=2):
    nyq = fs / 2.0
    b, a = butter(order, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, sig, axis=-1)


def preprocess(sig_12xN, original_fs=500):
    """(12, N) → (12, 2500) normalized float32. Returns None on bad signal."""
    n_leads, n_samples = sig_12xN.shape
    if original_fs != 500:
        target_samples = int(n_samples * 500 / original_fs)
        sig_12xN = resample(sig_12xN, target_samples, axis=1)
        n_samples = target_samples
    if n_samples < 5000:
        sig_12xN = np.pad(sig_12xN, ((0, 0), (0, 5000 - n_samples)), mode="constant")
    elif n_samples > 5000:
        sig_12xN = sig_12xN[:, :5000]
    sig = bandpass(sig_12xN, fs=500)
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    sig = sig[:, ::2]  # 500→250 Hz → (12, 2500)
    std = sig.std(axis=1, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    sig = (sig - sig.mean(axis=1, keepdims=True)) / std
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    out = sig.astype(np.float32)
    if not np.isfinite(out).all():
        return None
    return out


def preprocess_with_overlap(sig_12xN, original_fs=500, window_sec=10, overlap_sec=5):
    """(12, N) → list of (12, 2500) windows with overlap. §4: 10s windows, 5s overlap."""
    n_leads, n_samples = sig_12xN.shape
    if original_fs != 500:
        target_samples = int(n_samples * 500 / original_fs)
        sig_12xN = resample(sig_12xN, target_samples, axis=1)
        n_samples = target_samples

    sig = bandpass(sig_12xN, fs=500)
    sig = np.nan_to_num(sig, nan=0.0, posinf=0.0, neginf=0.0)
    sig = sig[:, ::2]  # 500→250 Hz
    n_ds = sig.shape[1]

    win_samples = FS_TARGET * window_sec   # 2500
    step_samples = FS_TARGET * (window_sec - overlap_sec)  # 1250

    if n_ds < win_samples:
        sig = np.pad(sig, ((0, 0), (0, win_samples - n_ds)), mode="constant")
        n_ds = win_samples

    windows = []
    start = 0
    while start + win_samples <= n_ds:
        w = sig[:, start:start + win_samples].copy()
        std = w.std(axis=1, keepdims=True)
        std = np.where(std < 1e-6, 1.0, std)
        w = (w - w.mean(axis=1, keepdims=True)) / std
        w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        if np.isfinite(w).all():
            windows.append(w)
        start += step_samples
    return windows


def parse_dx(hea_path: str) -> list[int]:
    """Extract SNOMED codes from .hea — handles '# Dx:' and '#Dx:'."""
    codes: list[int] = []
    try:
        with open(hea_path, encoding="utf-8") as f:
            for line in f:
                ls = line.strip()
                if ls.startswith("#") and "Dx" in ls:
                    idx = ls.find("Dx:")
                    if idx >= 0:
                        for c in ls[idx + 3:].strip().split(","):
                            c = c.strip()
                            if c.isdigit():
                                codes.append(int(c))
    except Exception:
        pass
    return codes


def load_dataset_records(dataset_path: str, max_records: int | None = None,
                         use_overlap: bool = False):
    """Load ECG records from any CinC 2021 WFDB dataset.
    §4: use_overlap=True applies 10s windows with 5s overlap for longer recordings.
    """
    hea_files = glob.glob(os.path.join(dataset_path, "**", "*.hea"), recursive=True)
    X_list, Y_list = [], []
    skipped = 0
    desc = os.path.basename(dataset_path)
    for hea in tqdm(hea_files[:max_records] if max_records else hea_files,
                    desc=f"  Loading {desc}", unit="rec"):
        try:
            rec_path = hea[:-4]
            record = wfdb.rdrecord(rec_path)
            sig = record.p_signal
            if sig is None or sig.shape[1] < 12:
                skipped += 1
                continue
            sig = sig[:, :12].T
            fs = record.fs

            codes = parse_dx(hea)
            if not codes:
                skipped += 1
                continue
            label = np.zeros(NUM_CLASSES, dtype=np.float32)
            has_known = False
            for code in codes:
                if code in SNOMED_MAP:
                    label[SNOMED_MAP[code]] = 1.0
                    has_known = True
            if not has_known:
                skipped += 1
                continue

            if use_overlap:
                windows = preprocess_with_overlap(sig, original_fs=fs)
                for w in windows:
                    X_list.append(w)
                    Y_list.append(label)
            else:
                x = preprocess(sig, original_fs=fs)
                if x is None:
                    skipped += 1
                    continue
                X_list.append(x)
                Y_list.append(label)
        except Exception:
            skipped += 1
    if X_list:
        X = np.array(X_list, dtype=np.float32)
        Y = np.array(Y_list, dtype=np.float32)
    else:
        X = np.zeros((0, 12, 2500), dtype=np.float32)
        Y = np.zeros((0, NUM_CLASSES), dtype=np.float32)
    console.print(f"    → [green]{len(X_list):,}[/] windows, [yellow]{skipped:,}[/] skipped"
                  + (f" [dim](overlap={use_overlap})[/]" if use_overlap else ""))
    return X, Y


def load_combined_dataset():
    """Load all 6 datasets and create combined train/val splits."""
    console.print("\n[bold cyan]📦 Veri setleri yükleniyor...[/]\n")

    # ── SPH ──
    sph_cache = os.path.join(CACHE_DIR, "dataset_cache.npz")
    if os.path.exists(sph_cache):
        data = np.load(sph_cache, allow_pickle=True)
        X_sph, Y_sph = data["X"], data["Y"]
        valid = np.isfinite(X_sph).reshape(X_sph.shape[0], -1).all(axis=1)
        X_sph, Y_sph = X_sph[valid], Y_sph[valid]
        console.print(f"  [green]SPH cache:[/] {len(X_sph):,} records")
    else:
        X_sph, Y_sph = load_dataset_records(SPH_PATH)

    # SPH 70/15/15 split
    n = len(X_sph)
    rng = np.random.RandomState(42)
    idx = rng.permutation(n)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)
    sph_train_idx = idx[:n_train]
    sph_val_idx = idx[n_train:n_train + n_val]

    X_train = X_sph[sph_train_idx]
    Y_train = Y_sph[sph_train_idx]
    X_val = X_sph[sph_val_idx]
    Y_val = Y_sph[sph_val_idx]

    # ── External datasets ──
    for ds_name, ds_path in EXTERNAL_DATASETS.items():
        if not os.path.exists(ds_path):
            console.print(f"  [yellow]{ds_name} bulunamadı, atlanıyor.[/]")
            continue
        cache_file = os.path.join(CACHE_DIR, f"cache_{ds_name}.npz")
        if os.path.exists(cache_file):
            data = np.load(cache_file, allow_pickle=True)
            X_ext, Y_ext = data["X"], data["Y"]
            console.print(f"  [green]{ds_name} cache:[/] {len(X_ext):,} records")
        else:
            X_ext, Y_ext = load_dataset_records(ds_path)
            if len(X_ext) > 0:
                np.savez_compressed(cache_file, X=X_ext, Y=Y_ext)

        if len(X_ext) == 0:
            continue
        n_ext = len(X_ext)
        n_ext_train = int(n_ext * 0.85)
        perm = np.random.RandomState(42).permutation(n_ext)
        X_train = np.concatenate([X_train, X_ext[perm[:n_ext_train]]])
        Y_train = np.concatenate([Y_train, Y_ext[perm[:n_ext_train]]])
        X_val = np.concatenate([X_val, X_ext[perm[n_ext_train:]]])
        Y_val = np.concatenate([Y_val, Y_ext[perm[n_ext_train:]]])

    # Shuffle
    perm = np.random.RandomState(42).permutation(len(X_train))
    X_train, Y_train = X_train[perm], Y_train[perm]

    console.print(f"\n  [bold green]Combined:[/] train={len(X_train):,}, val={len(X_val):,}")
    return X_train, Y_train, X_val, Y_val


# ═══════════════════════════════════════════════════════════
#  3. VERİ ARTIRMA (Data Augmentation)
# ═══════════════════════════════════════════════════════════
class EcgAugDataset(Dataset):
    """Dataset with on-the-fly augmentation and channel dropout."""

    def __init__(self, X: np.ndarray, Y: np.ndarray, augment: bool = True):
        self.X = torch.from_numpy(X)
        self.Y = torch.from_numpy(Y)
        self.augment = augment

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        x = self.X[idx].clone()   # (12, 2500)
        y = self.Y[idx]

        if self.augment:
            x = self._augment(x)

        return x, y

    def _augment(self, x: torch.Tensor) -> torch.Tensor:
        """Apply augmentations per-sample."""
        # 1) Gaussian noise — σ = 0.05
        if torch.rand(1).item() < 0.5:
            x = x + torch.randn_like(x) * 0.05

        # 2) Baseline wander — low-freq sinusoid
        if torch.rand(1).item() < 0.3:
            T = x.shape[-1]
            freq = torch.empty(1).uniform_(0.1, 0.5).item()
            amp = torch.empty(1).uniform_(0.1, 0.3).item()
            phase = torch.empty(1).uniform_(0.0, 2 * math.pi).item()
            t = torch.linspace(0, 10.0, T)
            wander = amp * torch.sin(2 * math.pi * freq * t + phase)
            # random subset of leads
            n_leads = torch.randint(1, 5, (1,)).item()
            leads = torch.randperm(12)[:n_leads]
            x[leads] = x[leads] + wander.unsqueeze(0)

        # 3) Time scaling — resample by ±10%
        if torch.rand(1).item() < 0.2:
            T = x.shape[-1]
            scale = torch.empty(1).uniform_(0.9, 1.1).item()
            new_T = int(T * scale)
            x_rs = F.interpolate(x.unsqueeze(0), size=new_T, mode="linear",
                                 align_corners=False).squeeze(0)
            if new_T > T:
                x = x_rs[:, :T]
            else:
                pad = T - new_T
                x = F.pad(x_rs, (0, pad))

        # 4) Random individual lead dropout (p=0.1 per lead)
        if torch.rand(1).item() < 0.3:
            mask = torch.rand(12) > 0.1
            x = x * mask.unsqueeze(1).float()

        return x


# ═══════════════════════════════════════════════════════════
#  4. MODEL — DCA-CNN (Dynamic Channel-Aware CNN)
# ═══════════════════════════════════════════════════════════

class AdaptiveChannelConv(nn.Module):
    """
    Adaptive Channel Convolution — DCA-CNN temel yapı taşı.
    W_c = W_base + ΔW_c : paylaşılan temel çekirdek + kanal-spesifik offset.
    Öğrenilebilir kapı g_c = σ(α_c) ile aktif/pasif kanal kontrolü.
    """

    def __init__(self, c_max: int, out_ch: int, kernel_size: int, stride: int = 1):
        super().__init__()
        self.c_max = c_max
        self.out_ch = out_ch
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = kernel_size // 2

        # Paylaşılan temel çekirdek: (out_ch, 1, K)
        self.W_base = nn.Parameter(torch.empty(out_ch, 1, kernel_size))
        nn.init.kaiming_normal_(self.W_base, mode="fan_out", nonlinearity="relu")

        # Kanal-spesifik offset: (c_max, out_ch, 1, K)
        self.delta_W = nn.Parameter(torch.zeros(c_max, out_ch, 1, kernel_size))
        nn.init.normal_(self.delta_W, std=0.01)

        # Öğrenilebilir kapı — α başlangıcı 2.0 → σ(2)≈0.88
        self.alpha = nn.Parameter(torch.full((c_max,), 2.0))

        self.bias = nn.Parameter(torch.zeros(out_ch))

    def forward(self, x: torch.Tensor, c_active: int | None = None) -> torch.Tensor:
        """
        x: (B, C, T) where C <= c_max
        c_active: number of active channels (uses x.shape[1] if None)
        Returns: (B, out_ch, T')
        """
        B, C, T = x.shape
        if c_active is None:
            c_active = C

        # Kapı mekanizması
        gates = torch.sigmoid(self.alpha[:C])  # (C,)
        x_gated = x * gates.view(1, C, 1)

        # Efektif ağırlık: W_base(out_ch,1,K) + delta_W[:C](C,out_ch,1,K)
        #   → squeeze+permute → (out_ch, C, K) — standart Conv1d ağırlık formatı
        effective_W = (
            self.W_base.expand(-1, C, -1)
            + self.delta_W[:C].squeeze(2).permute(1, 0, 2)
        )  # (out_ch, C, K)

        return F.conv1d(x_gated, effective_W, self.bias,
                        stride=self.stride, padding=self.padding)

    def gate_reg_loss(self, c_active: int) -> torch.Tensor:
        """L_gate: inaktif kanalların kapı değerlerini sıfıra çek."""
        if c_active >= self.c_max:
            return torch.tensor(0.0, device=self.alpha.device)
        inactive_gates = torch.sigmoid(self.alpha[c_active:])
        return (inactive_gates ** 2).sum()


class SqueezeExcite1d(nn.Module):
    """SE (Squeeze-and-Excitation) channel attention for 1D features."""

    def __init__(self, channels: int, reduction: int = 4):
        super().__init__()
        mid = max(channels // reduction, 4)
        self.fc1 = nn.Linear(channels, mid, bias=False)
        self.fc2 = nn.Linear(mid, channels, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, C, T) → (B, C, T) with channel attention."""
        z = x.mean(dim=-1)                          # (B, C) — GAP
        s = torch.sigmoid(self.fc2(F.relu(self.fc1(z))))  # (B, C)
        return x * s.unsqueeze(-1)


class DSConv1d(nn.Module):
    """Depthwise Separable Conv1d: DW → BN → ReLU6 → PW → BN → ReLU6"""

    def __init__(self, in_ch: int, out_ch: int, kernel_size: int = 7, stride: int = 1):
        super().__init__()
        self.dw = nn.Conv1d(in_ch, in_ch, kernel_size, stride=stride,
                            padding=kernel_size // 2, groups=in_ch, bias=False)
        self.bn1 = nn.BatchNorm1d(in_ch)
        self.pw = nn.Conv1d(in_ch, out_ch, 1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.act = nn.ReLU6()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.act(self.bn1(self.dw(x)))
        x = self.act(self.bn2(self.pw(x)))
        return x


class DcaCNN(nn.Module):
    """
    Dynamic Channel-Aware CNN — Araştırma Önerisi §4.

    Girdi : (B, C, 2500)  C ∈ {1, 3, 12}
    Çıktı : (B, 55) raw logits (training) veya sigmoid probs (inference export)
    """

    def __init__(self, c_max: int = C_MAX, n_classes: int = NUM_CLASSES):
        super().__init__()
        self.c_max = c_max
        self.n_classes = n_classes

        # ── Stem: ACC + BN + ReLU6 ──
        self.acc = AdaptiveChannelConv(c_max, 32, kernel_size=15, stride=2)
        self.stem_bn = nn.BatchNorm1d(32)
        self.stem_act = nn.ReLU6()

        # ── 5× DSConv blocks + SE attention ──
        self.blocks = nn.ModuleList([
            DSConv1d(32,  64,  kernel_size=7, stride=2),
            DSConv1d(64,  128, kernel_size=7, stride=2),
            DSConv1d(128, 128, kernel_size=5, stride=2),
            DSConv1d(128, 256, kernel_size=5, stride=2),
            DSConv1d(256, 256, kernel_size=3, stride=2),
        ])
        self.se_blocks = nn.ModuleList([
            SqueezeExcite1d(64,  reduction=4),
            SqueezeExcite1d(128, reduction=4),
            SqueezeExcite1d(128, reduction=4),
            SqueezeExcite1d(256, reduction=4),
            SqueezeExcite1d(256, reduction=4),
        ])

        # ── Classification head ──
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU6(),
            nn.Linear(128, n_classes),
        )

    def forward(self, x: torch.Tensor, c_active: int | None = None) -> torch.Tensor:
        """
        x: (B, C, T) — C can be 1, 3, or 12
        c_active: explicit active channel count (defaults to x.shape[1])
        """
        C = x.shape[1]
        if c_active is None:
            c_active = C

        # Eğer C < c_max, 12'ye zero-pad (export uyumluluğu için)
        if C < self.c_max:
            pad = torch.zeros(x.shape[0], self.c_max - C, x.shape[2],
                              device=x.device, dtype=x.dtype)
            x = torch.cat([x, pad], dim=1)
        # Artık x: (B, c_max, T) — inaktif kanallar sıfır, kapılar da onları bastıracak

        x = self.stem_act(self.stem_bn(self.acc(x, c_active=c_active)))

        for block, se in zip(self.blocks, self.se_blocks):
            x = block(x)
            x = se(x)

        return self.head(x)

    def gate_reg_loss(self, c_active: int) -> torch.Tensor:
        """ACC katmanının kapı regülarizasyonu."""
        return self.acc.gate_reg_loss(c_active)

    def phase_reg_loss(self) -> torch.Tensor:
        """
        Faz regülarizasyonu — konvolüsyon çekirdeklerinin frekans cevabını,
        Butterworth referans filtresine yaklaştır (ilk 3 katman).
        """
        loss = torch.tensor(0.0, device=next(self.parameters()).device)

        kernels = [
            self.acc.W_base.squeeze(1),         # (32, K=15)
            self.blocks[0].dw.weight.squeeze(1), # (32, K=7)
            self.blocks[1].dw.weight.squeeze(1), # (64, K=7)
        ]

        for w in kernels:
            F_out, K = w.shape
            # Çekirdeğin DFT'si
            H = torch.fft.rfft(w, dim=-1)  # (F_out, K//2+1) complex
            H_mag = torch.abs(H)

            # İdeal referans: birim kazanç bandpass (normalize)
            n_freq = H_mag.shape[-1]
            ref = torch.ones_like(H_mag)

            loss = loss + ((H_mag - ref) ** 2).mean()

        return loss


# ═══════════════════════════════════════════════════════════
#  5. KANAL DROPOUT EĞİTİM STRATEJİSİ
# ═══════════════════════════════════════════════════════════
def sample_channel_config() -> int:
    """Eğitim sırasında rastgele kanal konfigürasyonu seç."""
    r = torch.rand(1).item()
    if r < CHAN_DROP_PROBS[12]:       # %50
        return 12
    elif r < CHAN_DROP_PROBS[12] + CHAN_DROP_PROBS[3]:  # +%25
        return 3
    else:                             # %25
        return 1


def apply_channel_mask(x: torch.Tensor, n_channels: int) -> tuple[torch.Tensor, int]:
    """
    Batch'teki tüm örneklere kanal maskesi uygula.
    x: (B, 12, T) → inaktif kanallar sıfırlanır.
    Returns: (masked_x, c_active)
    """
    if n_channels >= 12:
        return x, 12

    active_leads = LEAD_CONFIGS[n_channels]
    mask = torch.zeros(12, device=x.device, dtype=x.dtype)
    for lead in active_leads:
        mask[lead] = 1.0
    x = x * mask.view(1, 12, 1)
    return x, n_channels


# ═══════════════════════════════════════════════════════════
#  6. EĞİTİM DÖNGÜSÜ
# ═══════════════════════════════════════════════════════════
def train_model(X_train: np.ndarray, Y_train: np.ndarray,
                X_val: np.ndarray, Y_val: np.ndarray):
    """DCA-CNN eğitimi — mixed precision, channel dropout, 3-bileşenli kayıp."""

    train_ds = EcgAugDataset(X_train, Y_train, augment=True)
    val_ds   = EcgAugDataset(X_val, Y_val, augment=False)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True, persistent_workers=True,
                              drop_last=True)
    val_loader   = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True, persistent_workers=True)

    model = DcaCNN().to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())

    # ── Config tablosu ──
    info_table = Table(box=box.ROUNDED, title="[bold magenta]⚙️  DCA-CNN Eğitim Konfigürasyonu[/]",
                       border_style="bright_blue")
    info_table.add_column("Parametre", style="cyan")
    info_table.add_column("Değer", style="bold white")
    info_table.add_row("Device", f"{DEVICE}" + (f" ({torch.cuda.get_device_name(0)})" if DEVICE.type == "cuda" else ""))
    info_table.add_row("Train / Val", f"{len(X_train):,} / {len(X_val):,}")
    info_table.add_row("Total Params", f"{total_params:,}")
    info_table.add_row("Batch / Epoch", f"{BATCH_SIZE} / {EPOCHS}")
    info_table.add_row("Learning Rate", f"{LR} (CosineAnnealing T₀=10)")
    info_table.add_row("Loss", f"BCE + λ_g={LAMBDA_GATE} gate + λ_φ={LAMBDA_PHASE} phase")
    info_table.add_row("Optimizer", "AdamW + CosineAnnealingWarmRestarts")
    info_table.add_row("Channel Dropout", f"12ch={CHAN_DROP_PROBS[12]:.0%} / 3ch={CHAN_DROP_PROBS[3]:.0%} / 1ch={CHAN_DROP_PROBS[1]:.0%}")
    info_table.add_row("Mixed Precision", "Yes (AMP)")
    console.print(info_table)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=10, T_mult=2, eta_min=1e-6
    )
    criterion = nn.BCEWithLogitsLoss()
    scaler = GradScaler("cuda")

    best_auc = 0.0
    best_path = os.path.join(MODEL_DIR, "ecg_dca_cnn_best.pt")
    no_impr = 0
    log_rows = []

    console.print("\n[bold green]🚂 DCA-CNN eğitimi başlıyor...[/]\n")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        epoch_loss = 0.0
        epoch_bce = 0.0
        epoch_gate = 0.0
        epoch_phase = 0.0
        n_samples = 0
        t0 = time.time()

        train_bar = tqdm(train_loader,
                         desc=f"  Epoch {epoch:2d}/{EPOCHS} [Train]",
                         leave=False, ncols=110,
                         bar_format="{l_bar}{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        for xb, yb in train_bar:
            xb, yb = xb.to(DEVICE, non_blocking=True), yb.to(DEVICE, non_blocking=True)

            # Kanal dropout
            c_config = sample_channel_config()
            xb_masked, c_active = apply_channel_mask(xb, c_config)

            optimizer.zero_grad(set_to_none=True)

            with autocast(device_type="cuda", enabled=(DEVICE.type == "cuda")):
                logits = model(xb_masked, c_active=c_active)
                l_bce = criterion(logits, yb)
                l_gate = model.gate_reg_loss(c_active)
                l_phase = model.phase_reg_loss()
                loss = l_bce + LAMBDA_GATE * l_gate + LAMBDA_PHASE * l_phase

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()

            bs = len(xb)
            epoch_loss += loss.item() * bs
            epoch_bce += l_bce.item() * bs
            epoch_gate += l_gate.item() * bs
            epoch_phase += l_phase.item() * bs
            n_samples += bs
            train_bar.set_postfix(loss=f"{loss.item():.4f}", ch=c_config)

        scheduler.step()

        epoch_loss /= n_samples
        epoch_bce /= n_samples
        epoch_gate /= n_samples
        epoch_phase /= n_samples

        # ── Validation (always 12-lead) ──
        model.eval()
        all_preds, all_labels = [], []
        val_loss = 0.0
        val_n = 0

        val_bar = tqdm(val_loader,
                       desc=f"  Epoch {epoch:2d}/{EPOCHS} [Val]  ",
                       leave=False, ncols=110,
                       bar_format="{l_bar}{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        with torch.no_grad():
            for xb, yb in val_bar:
                xb, yb = xb.to(DEVICE, non_blocking=True), yb.to(DEVICE, non_blocking=True)
                with autocast(device_type="cuda", enabled=(DEVICE.type == "cuda")):
                    logits = model(xb)  # full 12-lead
                    val_loss += criterion(logits, yb).item() * len(xb)
                all_preds.append(torch.sigmoid(logits).float().cpu().numpy())
                all_labels.append(yb.cpu().numpy())
                val_n += len(xb)

        val_loss /= val_n
        preds_np = np.nan_to_num(np.vstack(all_preds), nan=0.5, posinf=1.0, neginf=0.0)
        labels_np = np.vstack(all_labels)

        valid_cols = labels_np.sum(0) > 0
        val_auc = roc_auc_score(labels_np[:, valid_cols], preds_np[:, valid_cols],
                                average="macro") if valid_cols.sum() > 0 else 0.0

        elapsed = time.time() - t0
        lr_now = optimizer.param_groups[0]["lr"]

        auc_color = "bold green" if val_auc > best_auc else "yellow"
        console.print(
            f"  [bold cyan]Epoch {epoch:3d}/{EPOCHS}[/] │ "
            f"total [red]{epoch_loss:.4f}[/] (bce={epoch_bce:.4f} gate={epoch_gate:.4f} phase={epoch_phase:.4f}) │ "
            f"val [red]{val_loss:.4f}[/] │ "
            f"AUC [{auc_color}]{val_auc:.4f}[/] │ "
            f"lr [dim]{lr_now:.1e}[/] │ "
            f"[dim]{elapsed:.0f}s[/]",
        )

        log_rows.append({
            "epoch": epoch, "train_loss": epoch_loss,
            "train_bce": epoch_bce, "train_gate": epoch_gate, "train_phase": epoch_phase,
            "val_loss": val_loss, "val_auc": val_auc, "lr": lr_now,
        })

        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model.state_dict(), best_path)
            console.print(f"    [bold green]★ Yeni en iyi model![/] AUC={best_auc:.4f}")
            no_impr = 0
        else:
            no_impr += 1
            if no_impr >= EARLY_STOP:
                console.print(f"  [bold red]⏹  Early stopping[/] ({EARLY_STOP} epoch iyileşme yok)")
                break

    # ── Training log ──
    log_path = os.path.join(RESULTS_DIR, "training_log_dca_cnn.csv")
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log_rows[0].keys())
        writer.writeheader()
        writer.writerows(log_rows)

    console.print(f"\n[bold green]🏆 En iyi val AUC: {best_auc:.4f}[/]")

    model.load_state_dict(torch.load(best_path, map_location=DEVICE, weights_only=True))
    return model, best_auc, log_rows


# ═══════════════════════════════════════════════════════════
#  7. ONNX EXPORT
# ═══════════════════════════════════════════════════════════

class _ExportableDcaCNN(nn.Module):
    """
    ONNX-exportable wrapper: ACC'nin dinamik ağırlık inşasını
    standart nn.Conv1d'ye 'pişirerek' tracer uyumlu hale getirir.
    Her zaman 12 kanallı giriş kabul eder.
    """

    def __init__(self, model: DcaCNN):
        super().__init__()
        model.eval()
        acc = model.acc
        C = model.c_max

        # ACC → standart Conv1d'ye dönüştür
        gates = torch.sigmoid(acc.alpha[:C])                          # (C,)
        effective_W = (
            acc.W_base.expand(-1, C, -1)
            + acc.delta_W[:C].squeeze(2).permute(1, 0, 2)
        )  # (out_ch, C, K)
        # Kapıları ağırlıklara katıştır: W_eff[:, c, :] *= gate_c
        effective_W = effective_W * gates.view(1, C, 1)

        self.stem_conv = nn.Conv1d(
            C, acc.out_ch, acc.kernel_size,
            stride=acc.stride, padding=acc.padding, bias=True,
        )
        with torch.no_grad():
            self.stem_conv.weight.copy_(effective_W)
            self.stem_conv.bias.copy_(acc.bias)

        self.stem_bn  = model.stem_bn
        self.stem_act = model.stem_act
        self.blocks   = model.blocks
        self.se_blocks = model.se_blocks
        self.head     = model.head

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem_act(self.stem_bn(self.stem_conv(x)))
        for block, se in zip(self.blocks, self.se_blocks):
            x = block(x)
            x = se(x)
        return torch.sigmoid(self.head(x))


def export_onnx(model: DcaCNN, onnx_path: str):
    """ONNX export — 12 kanallı giriş, sigmoid çıkış."""
    console.print(f"\n[bold cyan]📦 ONNX export:[/] {onnx_path}")
    model.eval().cpu()

    export_model = _ExportableDcaCNN(model)
    export_model.eval()
    dummy = torch.zeros(1, C_MAX, N_SAMPLES)

    torch.onnx.export(
        export_model, dummy, onnx_path,
        input_names=["ecg_input"],
        output_names=["predictions"],
        dynamic_axes={"ecg_input": {0: "batch"}, "predictions": {0: "batch"}},
        opset_version=17,
    )
    import onnx
    onnx.checker.check_model(onnx_path)
    size_kb = os.path.getsize(onnx_path) / 1024
    console.print(f"   [green]✅ ONNX boyutu: {size_kb:.1f} KB[/]")
    return onnx_path


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold white]DCA-CNN EĞİTİMİ[/]\n"
        "[cyan]Dynamic Channel-Aware CNN · PyTorch + CUDA[/]\n"
        "[dim]TÜBİTAK 2209-A — Hayatın Ritmi[/]\n"
        "[dim]Araştırma Önerisi §4: Adaptif Kanal Mimarisi[/]",
        border_style="bright_magenta", box=box.DOUBLE_EDGE,
        padding=(1, 4),
    ))

    if DEVICE.type == "cuda":
        console.print(f"  [bold green]🖥️  GPU:[/] {torch.cuda.get_device_name(0)} "
                      f"([cyan]{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB[/] VRAM)")
    else:
        console.print("  [bold yellow]⚠  CPU modu[/]")
    console.print(f"  [bold green]🏷️  Sınıflar:[/] {NUM_CLASSES} SNOMED-CT kondisyon")

    # ── Param count estimation (before data load) ──
    _tmp = DcaCNN()
    _p = sum(p.numel() for p in _tmp.parameters())
    console.print(f"  [bold green]📐 Model params:[/] {_p:,}")
    del _tmp
    console.print()

    # 1. Dataset yükle
    X_train, Y_train, X_val, Y_val = load_combined_dataset()

    # Dataset stats
    stats_table = Table(box=box.SIMPLE_HEAVY, border_style="cyan",
                        title="[bold]📊 Combined Dataset[/]")
    stats_table.add_column("Metrik", style="cyan")
    stats_table.add_column("Değer", style="bold white")
    stats_table.add_row("Train records", f"{X_train.shape[0]:,}")
    stats_table.add_row("Val records", f"{X_val.shape[0]:,}")
    stats_table.add_row("Leads × Samples", f"{X_train.shape[1]} × {X_train.shape[2]}")
    stats_table.add_row("Classes", str(Y_train.shape[1]))
    stats_table.add_row("Positive rate", f"{Y_train.mean():.4f}")
    stats_table.add_row("X_train memory", f"{X_train.nbytes / 1024**3:.2f} GB")
    console.print(stats_table)

    # 2. Train
    model, best_auc, log_rows = train_model(X_train, Y_train, X_val, Y_val)

    # 3. ONNX export
    onnx_path = os.path.join(MODEL_DIR, "ecg_dca_cnn.onnx")
    export_onnx(model, onnx_path)

    # 4. Save summary JSON
    summary = {
        "model": "DCA-CNN",
        "total_params": sum(p.numel() for p in model.parameters()),
        "best_val_auc": round(best_auc, 6),
        "epochs_run": len(log_rows),
        "best_epoch": max(log_rows, key=lambda r: r["val_auc"])["epoch"],
        "train_records": len(X_train),
        "val_records": len(X_val),
        "num_classes": NUM_CLASSES,
        "channel_configs": [1, 3, 12],
        "lambda_gate": LAMBDA_GATE,
        "lambda_phase": LAMBDA_PHASE,
        "optimizer": "AdamW",
        "scheduler": "CosineAnnealingWarmRestarts(T0=10, Tmult=2)",
        "augmentations": ["gaussian_noise", "baseline_wander", "time_scaling", "channel_dropout"],
    }
    summary_path = os.path.join(RESULTS_DIR, "dca_cnn_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Final table
    result_table = Table(box=box.DOUBLE_EDGE, title="[bold green]✅ DCA-CNN EĞİTİMİ TAMAMLANDI[/]",
                         border_style="green")
    result_table.add_column("Çıktı", style="cyan")
    result_table.add_column("Yol", style="white")
    result_table.add_row("PT model", os.path.join(MODEL_DIR, "ecg_dca_cnn_best.pt"))
    result_table.add_row("ONNX", onnx_path)
    result_table.add_row("Training log", os.path.join(RESULTS_DIR, "training_log_dca_cnn.csv"))
    result_table.add_row("Summary", summary_path)
    result_table.add_row("Val AUC", f"{best_auc:.4f}")
    result_table.add_row("Params", f"{summary['total_params']:,}")
    console.print(result_table)
