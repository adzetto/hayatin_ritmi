"""
ECG Aritmisi Sınıflandırıcı — Eğitim Scripti
==============================================
Veri: PhysioNet SPH ECG Arrhythmia (45,152 kayıt, 12 derivasyon, 500Hz, 10sn)
Model: Depthwise Separable 1D CNN (~280K param → ~350KB INT8 TFLite)
Hedef: Android backend (TFLite), ~12ms inference

Çalıştır:
  python dataset/train_ecg_model.py

Gereksinimler:
  pip install wfdb scipy tensorflow scikit-learn huggingface_hub
"""

import os
import csv
from pathlib import Path
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras import layers, Model, callbacks
from huggingface_hub import HfApi, upload_file as hf_upload

# ── .env'den token oku ──────────────────────
def _load_env():
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()
# ────────────────────────────────────────────

# ═══════════════════════════════════════════════════════
#  YAPILANDIRMA
# ═══════════════════════════════════════════════════════
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AI_DIR       = os.path.join(PROJECT_ROOT, "ai")
DATASET_PATH = os.path.join(PROJECT_ROOT, "dataset", "ecg-arrhythmia")
MODEL_DIR    = os.path.join(AI_DIR, "models", "checkpoints")
RESULTS_DIR  = os.path.join(AI_DIR, "models", "results")
SNOMED_CSV   = os.path.join(DATASET_PATH, "ConditionNames_SNOMED-CT.csv")
RECORDS_FILE = os.path.join(DATASET_PATH, "RECORDS")

HF_TOKEN   = os.environ.get("HF_TOKEN", "")
HF_REPO_ID = "adzetto/ecg-arrhythmia-classifier"

FS_ORIGINAL  = 500     # Orijinal örnekleme frekansı (Hz)
FS_TARGET    = 250     # Hedef örnekleme frekansı (downsample)
DURATION_S   = 10      # Saniye
N_SAMPLES    = FS_TARGET * DURATION_S   # 2500
N_LEADS      = 12
BATCH_SIZE   = 64
EPOCHS       = 50

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════
#  1. SNOMED-CT LABEL MAP
# ═══════════════════════════════════════════════════════
def load_snomed_map():
    codes, names = [], []
    with open(SNOMED_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes.append(int(row["Snomed_CT"]))
            names.append(row["Acronym Name"])
    code_to_idx = {code: i for i, code in enumerate(codes)}
    return code_to_idx, names

SNOMED_MAP, CONDITION_NAMES = load_snomed_map()
NUM_CLASSES = len(SNOMED_MAP)  # 49
print(f"✅ {NUM_CLASSES} SNOMED-CT kondisyon yüklendi: {CONDITION_NAMES[:5]}...")

# ═══════════════════════════════════════════════════════
#  2. SİNYAL ÖN İŞLEME
# ═══════════════════════════════════════════════════════
def bandpass_filter(signal, fs=500, lowcut=0.5, highcut=40.0, order=2):
    """Butterworth bandpass: 0.5–40 Hz (baseline wander + yüksek frekans gürültüsü kaldır)"""
    nyq = fs / 2.0
    b, a = butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return filtfilt(b, a, signal, axis=-1)

def preprocess_signal(sig_12xN):
    """
    Girdi : (12, 5000) — 500Hz
    Çıktı : (2500, 12) — 250Hz, normalize edilmiş
    """
    # Bandpass filtre
    sig = bandpass_filter(sig_12xN, fs=FS_ORIGINAL)
    # Downsample: 500Hz → 250Hz
    sig = sig[:, ::2]  # (12, 2500)
    # Per-lead z-score normalizasyonu
    mean = sig.mean(axis=1, keepdims=True)
    std  = sig.std(axis=1, keepdims=True) + 1e-8
    sig  = (sig - mean) / std
    # (12, 2500) → (2500, 12) — model için
    return sig.T.astype(np.float32)

# ═══════════════════════════════════════════════════════
#  3. KAYIT YÜKLEME
# ═══════════════════════════════════════════════════════
def parse_dx_from_hea(hea_path):
    """Header dosyasından #Dx: satırını oku, SNOMED kodlarını döndür"""
    codes = []
    try:
        with open(hea_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#Dx:"):
                    for c in line.split(":")[1].strip().split(","):
                        try:
                            codes.append(int(c.strip()))
                        except ValueError:
                            pass
    except Exception:
        pass
    return codes

def load_record(record_path):
    """Tek bir WFDB kaydını yükle → (signal, label)"""
    record = wfdb.rdrecord(record_path)
    sig = record.p_signal  # (5000, 12)
    if sig.shape != (5000, 12):
        return None, None

    sig_T = sig.T  # (12, 5000)
    x = preprocess_signal(sig_T)  # (2500, 12)

    dx_codes = parse_dx_from_hea(record_path + ".hea")
    label = np.zeros(NUM_CLASSES, dtype=np.float32)
    for code in dx_codes:
        if code in SNOMED_MAP:
            label[SNOMED_MAP[code]] = 1.0

    return x, label

def load_all_records(max_records=None, verbose=True):
    """
    Tüm dataset'i yükle.
    max_records: test için küçük boyut kullan (None = hepsi)
    """
    with open(RECORDS_FILE, encoding="utf-8") as f:
        folders = [line.strip() for line in f if line.strip()]

    X_list, Y_list = [], []
    skipped = 0
    total_folders = len(folders) if not max_records else max_records

    for i, folder in enumerate(folders):
        if max_records and len(X_list) >= max_records:
            break

        folder_path = os.path.join(DATASET_PATH, folder)
        if not os.path.isdir(folder_path):
            continue

        for fname in sorted(os.listdir(folder_path)):
            if fname.endswith(".hea"):
                rec_path = os.path.join(folder_path, fname[:-4])
                try:
                    x, y = load_record(rec_path)
                    if x is not None:
                        X_list.append(x)
                        Y_list.append(y)
                except Exception:
                    skipped += 1

        if verbose and i % 5 == 0:
            print(f"  [{i+1}/{total_folders} klasör] {len(X_list)} kayıt yüklendi, {skipped} atlandı", end="\r")

    print(f"\n✅ Toplam: {len(X_list)} kayıt, {skipped} atlanan")
    return np.array(X_list, dtype=np.float32), np.array(Y_list, dtype=np.float32)

# ═══════════════════════════════════════════════════════
#  4. MODEL MİMARİSİ — Depthwise Separable 1D CNN
# ═══════════════════════════════════════════════════════
def ds_conv_block(x, filters, kernel_size=7, strides=1, dilation_rate=1):
    """Depthwise Separable 1D Conv + BN + ReLU"""
    x = layers.DepthwiseConv1D(
        kernel_size, strides=strides, padding='same',
        dilation_rate=dilation_rate, use_bias=False
    )(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU(6.0)(x)  # ReLU6 — mobil dostu
    x = layers.Conv1D(filters, 1, use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU(6.0)(x)
    return x

def build_ecg_model(input_shape=(N_SAMPLES, N_LEADS), num_classes=NUM_CLASSES):
    """
    DS-1D-CNN: ~280K parametre, INT8 sonrası ~350KB
    Girdi : (batch, 2500, 12)
    Çıktı : (batch, 49) — sigmoid multi-label
    """
    inputs = layers.Input(shape=input_shape, name="ecg_input")

    # Giriş bloğu
    x = layers.Conv1D(32, 15, strides=2, padding='same', use_bias=False, name="stem_conv")(inputs)
    x = layers.BatchNormalization(name="stem_bn")(x)
    x = layers.ReLU(6.0, name="stem_relu")(x)
    # → (1250, 32)

    # DS bloklar (giderek derinleşen)
    x = ds_conv_block(x, 64,  kernel_size=7,  strides=2)   # → (625,  64)
    x = ds_conv_block(x, 128, kernel_size=7,  strides=2)   # → (313, 128)
    x = ds_conv_block(x, 128, kernel_size=5,  strides=2)   # → (157, 128)
    x = ds_conv_block(x, 256, kernel_size=5,  strides=2)   # → (79,  256)
    x = ds_conv_block(x, 256, kernel_size=3,  strides=2)   # → (40,  256)

    # Classifier head
    x = layers.GlobalAveragePooling1D(name="gap")(x)        # → (256,)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation=None, name="fc1")(x)
    x = layers.BatchNormalization(name="fc1_bn")(x)
    x = layers.ReLU(6.0)(x)
    outputs = layers.Dense(num_classes, activation='sigmoid', name="predictions")(x)

    model = Model(inputs, outputs, name="EcgDSCNN_v1")
    return model

# ═══════════════════════════════════════════════════════
#  5. EĞİTİM
# ═══════════════════════════════════════════════════════
def train(X, Y):
    print(f"\n🔀 Train/val bölme (85/15)...")
    X_train, X_val, Y_train, Y_val = train_test_split(
        X, Y, test_size=0.15, random_state=42
    )
    print(f"   Train: {len(X_train)}, Val: {len(X_val)}")

    model = build_ecg_model()
    model.summary()

    # Sınıf dengesizliği için pozitif ağırlık
    pos_counts = Y_train.sum(axis=0) + 1
    neg_counts = len(Y_train) - pos_counts + 1
    pos_weight = (neg_counts / pos_counts).mean()
    print(f"   Ortalama pozitif ağırlık: {pos_weight:.2f}")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=tf.keras.losses.BinaryCrossentropy(label_smoothing=0.05),
        metrics=[
            tf.keras.metrics.AUC(multi_label=True, num_labels=NUM_CLASSES, name="auc"),
            tf.keras.metrics.BinaryAccuracy(name="acc", threshold=0.5),
        ]
    )

    cb_list = [
        callbacks.ReduceLROnPlateau(monitor="val_auc", patience=4, factor=0.5,
                                     mode="max", min_lr=1e-6, verbose=1),
        callbacks.EarlyStopping(monitor="val_auc", patience=10,
                                 mode="max", restore_best_weights=True, verbose=1),
        callbacks.ModelCheckpoint(
            filepath=os.path.join(MODEL_DIR, "ecg_best.keras"),
            monitor="val_auc", mode="max", save_best_only=True, verbose=1
        ),
        callbacks.CSVLogger(os.path.join(RESULTS_DIR, "training_log.csv")),
        callbacks.TensorBoard(log_dir=os.path.join(RESULTS_DIR, "tensorboard"), histogram_freq=0),
    ]

    print(f"\n🚂 Eğitim başlıyor... (epoch={EPOCHS}, batch={BATCH_SIZE})")
    history = model.fit(
        X_train, Y_train,
        validation_data=(X_val, Y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=cb_list,
        verbose=1,
    )

    val_auc = max(history.history["val_auc"])
    print(f"\n🏆 En iyi val AUC: {val_auc:.4f}")
    return model, X_val, Y_val

# ═══════════════════════════════════════════════════════
#  6. TFLite EXPORT (INT8 Quantization)
# ═══════════════════════════════════════════════════════
def export_tflite(model, X_rep, output_path):
    """Full INT8 quantization — Android'de en hızlı çalışır"""
    print("\n📦 TFLite INT8 export ediliyor...")

    def representative_dataset():
        indices = np.random.choice(len(X_rep), 300, replace=False)
        for i in indices:
            yield [X_rep[i:i+1]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type  = tf.float32
    converter.inference_output_type = tf.float32

    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"   ✅ Kaydedildi: {output_path}")
    print(f"   📏 Boyut: {size_kb:.1f} KB")
    return output_path

# ═══════════════════════════════════════════════════════
#  7. HUGGINGFace'E YÜKLEMEdef push_to_hub(model_path, tflite_path, token):
# ═══════════════════════════════════════════════════════
def push_to_hub(model_path, tflite_path, token):
    if token.startswith("hf_xxx"):
        print("⚠️  HF_TOKEN ayarlanmadı, yükleme atlandı.")
        return

    print(f"\n🤗 HuggingFace'e yükleniyor: {HF_REPO_ID}")
    api = HfApi(token=token)

    # Keras model
    api.upload_file(path_or_fileobj=model_path,   path_in_repo="ecg_best.keras",
                    repo_id=HF_REPO_ID, repo_type="model", token=token,
                    commit_message="Upload trained Keras model")
    # TFLite model
    api.upload_file(path_or_fileobj=tflite_path,  path_in_repo="ecg_model_int8.tflite",
                    repo_id=HF_REPO_ID, repo_type="model", token=token,
                    commit_message="Upload INT8 TFLite model for Android")
    # SNOMED CSV (Android label mapping için)
    api.upload_file(path_or_fileobj=SNOMED_CSV,   path_in_repo="ConditionNames_SNOMED-CT.csv",
                    repo_id=HF_REPO_ID, repo_type="model", token=token,
                    commit_message="Upload SNOMED-CT label names")
    print(f"   ✅ Yüklendi: https://huggingface.co/{HF_REPO_ID}")

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    # GPU varsa kullan
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        tf.config.experimental.set_memory_growth(gpus[0], True)
        print(f"🖥️  GPU: {gpus[0].name}")
    else:
        print("❗ GPU bulunamadı — CPU ile eğitim (yavaş olabilir)")
        print("   TF-DirectML: pip install tensorflow-directml-plugin")

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(" ECG ARİTMİ EĞİTİMİ BAŞLIYOR")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── Veri yükle ──────────────────────────
    print("\n📂 Dataset yükleniyor (45K kayıt ~5-10dk sürebilir)...")
    # Hızlı test için: max_records=500 kullan, tam eğitim için None
    X, Y = load_all_records(max_records=None)
    print(f"   X: {X.shape}, Y: {Y.shape}")
    print(f"   Pozitif etiket oranı: {Y.mean():.3f}")

    # ── Eğit ────────────────────────────────
    model, X_val, Y_val = train(X, Y)

    # ── TFLite export ───────────────────────
    tflite_path = os.path.join(AI_DIR, "models", "tflite", "ecg_model_int8.tflite")
    model_path  = os.path.join(MODEL_DIR, "ecg_best.keras")
    export_tflite(model, X_val, tflite_path)

    # ── HuggingFace'e yükle ─────────────────
    push_to_hub(model_path, tflite_path, HF_TOKEN)

    print("\n✅ TAMAMLANDI!")
    print(f"   Keras model : {model_path}")
    print(f"   TFLite model: {tflite_path}")
    print(f"   HF Model    : https://huggingface.co/{HF_REPO_ID}")
