"""
HuggingFace Repo Kurulum Scripti
=================================
Token .env dosyasından okunur (proje kökünde):
  HF_TOKEN=hf_...

Oluşturulacaklar:
  - adzetto/ecg-arrhythmia-classifier  (model repo)
  - adzetto/sph-ecg-arrhythmia         (dataset card)
  - adzetto/ecg-arrhythmia-demo        (Space — Gradio demo)
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo, upload_file

# ── .env'den token oku ──────────────────────
def _load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()
TOKEN = os.environ.get("HF_TOKEN", "")
if not TOKEN:
    raise EnvironmentError(".env dosyasında HF_TOKEN bulunamadı!")
# ────────────────────────────────────────────

USERNAME  = "adzetto"
MODEL_REPO   = f"{USERNAME}/ecg-arrhythmia-classifier"
DATASET_REPO = f"{USERNAME}/sph-ecg-arrhythmia"
SPACE_REPO   = f"{USERNAME}/ecg-arrhythmia-demo"

api = HfApi(token=TOKEN)

# ─── 1. Model Repo ───────────────────────────
print("📦 Model repo oluşturuluyor...")
create_repo(
    repo_id=MODEL_REPO,
    repo_type="model",
    private=False,
    token=TOKEN,
    exist_ok=True,
)
print(f"   ✅ https://huggingface.co/{MODEL_REPO}")

# Model README
model_readme = """---
license: apache-2.0
language:
  - tr
  - en
tags:
  - ecg
  - arrhythmia
  - 12-lead
  - tflite
  - medical
  - time-series
datasets:
  - adzetto/sph-ecg-arrhythmia
metrics:
  - auc
pipeline_tag: audio-classification
---

# ECG Arrhythmia Classifier (12-Lead DS-CNN)

Lightweight **Depthwise Separable 1D CNN** model for 12-lead ECG arrhythmia classification.
Trained on the [Shaoxing People's Hospital (SPH) dataset](https://physionet.org/content/ecg-arrhythmia/1.0.0/) — 45,152 ECG recordings.

## Model Details

| Property | Value |
|---|---|
| Architecture | Depthwise Separable 1D CNN |
| Parameters | ~280K |
| TFLite (INT8) size | ~350 KB |
| Input | (1, 2500, 12) — 10s @ 250Hz, 12 leads |
| Output | 49-class multi-label sigmoid |
| Android latency | ~12ms (mid-range device) |

## Conditions (49 SNOMED-CT labels)
1AVB, 2AVB, 2AVB1, 2AVB2, 3AVB, ABI, ALS, APB, AQW, ARS, AVB, CCR, CR, ERV, FQRS,
IDC, IVB, JEB, JPT, LBBB, LBBBB, LFBBB, LVH, LVQRSAL, LVQRSCL, LVQRSLL, MI, MIBW,
MIFW, MILW, MISW, PRIE, PWC, QTIE, RAH, RBBB, RVH, STDD, STE, STTC, STTU, TWC, TWO,
UW, VB, VEB, VFW, VPB, VPE

## Usage (Android TFLite)

```kotlin
val classifier = EcgClassifier(context)
val predictions = classifier.classify(ecgData12x2500)
// predictions: List<EcgPrediction> (prob > 0.5)
```

## Training

```bash
python dataset/train_ecg_model.py
```

## Project
Part of the **Hayatın Ritmi** wearable ECG project — TÜBİTAK 2209-A research.
"""

api.upload_file(
    path_or_fileobj=model_readme.encode(),
    path_in_repo="README.md",
    repo_id=MODEL_REPO,
    repo_type="model",
    token=TOKEN,
    commit_message="Initial model card",
)
print("   ✅ Model README yüklendi")

# ─── 2. Dataset Repo (Card Only) ─────────────
print("\n📊 Dataset repo oluşturuluyor...")
create_repo(
    repo_id=DATASET_REPO,
    repo_type="dataset",
    private=False,
    token=TOKEN,
    exist_ok=True,
)
print(f"   ✅ https://huggingface.co/datasets/{DATASET_REPO}")

dataset_readme = """---
license: other
license_name: physionet-restricted-health-data
license_link: https://physionet.org/content/ecg-arrhythmia/1.0.0/
language:
  - en
tags:
  - ecg
  - arrhythmia
  - 12-lead
  - wfdb
  - snomed-ct
  - physionet
  - medical
size_categories:
  - 10K<n<100K
task_categories:
  - audio-classification
---

# SPH 12-Lead ECG Arrhythmia Dataset (PhysioNet Mirror Card)

> ⚠️ **License**: This dataset is subject to the 
> [PhysioNet Restricted Health Data License](https://physionet.org/content/ecg-arrhythmia/1.0.0/).
> You must sign the Data Use Agreement on PhysioNet before use.

## Source
**Shaoxing People's Hospital (SPH) 12-Lead ECG Dataset**  
PhysioNet: https://physionet.org/content/ecg-arrhythmia/1.0.0/

## Stats
| Property | Value |
|---|---|
| Records | 45,152 patients |
| Format | WFDB (.mat + .hea) |
| Leads | 12 (I, II, III, aVR, aVL, aVF, V1–V6) |
| Sampling Rate | 500 Hz |
| Duration | 10 seconds / record |
| Labels | 49 SNOMED-CT conditions |

## Download
```bash
# PhysioNet'ten indir (hesap gerekli)
python dataset/download_ecg.py
```

## Usage
```python
import wfdb
import numpy as np

record = wfdb.rdrecord("WFDBRecords/01/010/JS00001")
signal = record.p_signal  # (5000, 12) — 10s x 12 leads
```

## Label Format
Diagnoses in `.hea` files as `#Dx: <SNOMED-CT codes>` (comma-separated multi-label).
Full condition list: [ConditionNames_SNOMED-CT.csv](ConditionNames_SNOMED-CT.csv)
"""

api.upload_file(
    path_or_fileobj=dataset_readme.encode(),
    path_in_repo="README.md",
    repo_id=DATASET_REPO,
    repo_type="dataset",
    token=TOKEN,
    commit_message="Initial dataset card",
)

# SNOMED CSV'yi de yükle
_script_dir = os.path.dirname(os.path.abspath(__file__))
snomed_csv_path = os.path.join(_script_dir, "ecg-arrhythmia", "ConditionNames_SNOMED-CT.csv")
if os.path.exists(snomed_csv_path):
    api.upload_file(
        path_or_fileobj=snomed_csv_path,
        path_in_repo="ConditionNames_SNOMED-CT.csv",
        repo_id=DATASET_REPO,
        repo_type="dataset",
        token=TOKEN,
        commit_message="Add SNOMED-CT condition names",
    )
    print("   ✅ SNOMED-CT CSV yüklendi")

# ─── 3. Space (Gradio Demo) ──────────────────
print("\n🚀 Gradio Space oluşturuluyor...")
create_repo(
    repo_id=SPACE_REPO,
    repo_type="space",
    space_sdk="gradio",
    private=False,
    token=TOKEN,
    exist_ok=True,
)
print(f"   ✅ https://huggingface.co/spaces/{SPACE_REPO}")

space_app = '''import gradio as gr
import numpy as np

CONDITION_NAMES = [
    "1AVB","2AVB","2AVB1","2AVB2","3AVB","ABI","ALS","APB","AQW","ARS","AVB",
    "CCR","CR","ERV","FQRS","IDC","IVB","JEB","JPT","LBBB","LBBBB","LFBBB",
    "LVH","LVQRSAL","LVQRSCL","LVQRSLL","MI","MIBW","MIFW","MILW","MISW",
    "PRIE","PWC","QTIE","RAH","RBBB","RVH","STDD","STE","STTC","STTU","TWC",
    "TWO","UW","VB","VEB","VFW","VPB","VPE"
]

try:
    import tensorflow as tf
    from huggingface_hub import hf_hub_download
    model_path = hf_hub_download(
        repo_id="adzetto/ecg-arrhythmia-classifier",
        filename="ecg_model_int8.tflite"
    )
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    MODEL_LOADED = True
except Exception as e:
    MODEL_LOADED = False
    MODEL_ERROR = str(e)

def classify_ecg(ecg_file):
    if not MODEL_LOADED:
        return f"Model henüz yüklenmedi. Eğitim tamamlandıktan sonra tekrar deneyin.\\nHata: {MODEL_ERROR}"
    if ecg_file is None:
        return "Lütfen bir .mat veya .npy dosyası yükleyin"
    try:
        import wfdb
        record = wfdb.rdrecord(ecg_file.name.replace(".hea",""))
        signal = record.p_signal.T  # (12, 5000)
        signal = signal[:, ::2]     # 500Hz → 250Hz
        signal = (signal - signal.mean(axis=1, keepdims=True)) / (signal.std(axis=1, keepdims=True) + 1e-8)
        inp = signal.T[np.newaxis].astype(np.float32)  # (1, 2500, 12)

        input_details  = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        interpreter.set_tensor(input_details[0]["index"], inp)
        interpreter.invoke()
        probs = interpreter.get_tensor(output_details[0]["index"])[0]  # (49,)

        results = [(CONDITION_NAMES[i], float(probs[i])) for i in range(49) if probs[i] > 0.3]
        results.sort(key=lambda x: -x[1])
        if not results:
            return "Anormal ritim tespit edilmedi (tüm olasılıklar < 0.3)"
        return "\\n".join([f"{'🔴' if p>0.7 else '🟡'} {name}: {p:.1%}" for name, p in results])
    except Exception as e:
        return f"Hata: {e}"

demo = gr.Interface(
    fn=classify_ecg,
    inputs=gr.File(label="ECG .hea dosyası yükle (WFDB format)"),
    outputs=gr.Textbox(label="Tespit Edilen Aritmiler", lines=15),
    title="🫀 ECG Aritmisi Sınıflandırıcı",
    description=(
        "12 derivasyonlu EKG kaydından 49 SNOMED-CT kondisyon sınıflandırması.\\n"
        "Model: Depthwise Separable 1D CNN — TÜBİTAK 2209-A Hayatın Ritmi Projesi"
    ),
    examples=[],
    theme=gr.themes.Soft(),
)

demo.launch()
'''

space_requirements = """gradio>=4.0
tensorflow>=2.16
wfdb
numpy
scipy
huggingface_hub
"""

api.upload_file(
    path_or_fileobj=space_app.encode(),
    path_in_repo="app.py",
    repo_id=SPACE_REPO,
    repo_type="space",
    token=TOKEN,
    commit_message="Initial Gradio app",
)
api.upload_file(
    path_or_fileobj=space_requirements.encode(),
    path_in_repo="requirements.txt",
    repo_id=SPACE_REPO,
    repo_type="space",
    token=TOKEN,
    commit_message="Add requirements",
)
print("   ✅ Space app.py ve requirements.txt yüklendi")

print("\n" + "="*55)
print("✅ TÜM REPOLAR HAZIR!")
print("="*55)
print(f"  Model  : https://huggingface.co/{MODEL_REPO}")
print(f"  Dataset: https://huggingface.co/datasets/{DATASET_REPO}")
print(f"  Space  : https://huggingface.co/spaces/{SPACE_REPO}")
print("="*55)
print("\nSonraki adım: python dataset/train_ecg_model.py")
