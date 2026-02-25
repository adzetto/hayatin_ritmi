"""
ECG Model — TFLite INT8 Quantization with Calibration Data
===========================================================
Uses real ECG samples from the dataset cache as calibration data
for representative dataset quantization.
"""

import os, sys
import numpy as np
import tensorflow as tf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR  = os.path.join(SCRIPT_DIR, "models")
TFLITE_DIR = os.path.join(MODEL_DIR, "tflite")
SAVED_MODEL_DIR = TFLITE_DIR  # onnx2tf saves SavedModel here
CACHE_FILE = os.path.join(MODEL_DIR, "dataset_cache.npz")
INT8_PATH = os.path.join(TFLITE_DIR, "ecg_model_int8.tflite")

N_CALIB = 200  # number of calibration samples

def main():
    # Load calibration data from cache
    if not os.path.exists(CACHE_FILE):
        print("ERROR: dataset_cache.npz not found")
        sys.exit(1)

    print("Loading calibration data...")
    data = np.load(CACHE_FILE, allow_pickle=True)
    X = data["X"]  # (N, 12, 2500)

    # onnx2tf converts to channels-last: check saved model input shape
    # Load the SavedModel to inspect
    loaded = tf.saved_model.load(SAVED_MODEL_DIR)
    infer = loaded.signatures["serving_default"]
    input_key = list(infer.structured_input_signature[1].keys())[0]
    input_spec = infer.structured_input_signature[1][input_key]
    print(f"SavedModel input: name={input_key}, shape={input_spec.shape}, dtype={input_spec.dtype}")

    # Determine if we need to transpose (channels-first vs channels-last)
    shape = input_spec.shape.as_list()
    needs_transpose = False
    if len(shape) == 3 and shape[-1] == 12:
        # channels-last: (batch, 2500, 12) — need to transpose our (N, 12, 2500)
        needs_transpose = True
        print("Detected channels-last format — will transpose calibration data")

    # Sample calibration subset
    rng = np.random.RandomState(42)
    indices = rng.choice(len(X), size=min(N_CALIB, len(X)), replace=False)
    X_calib = X[indices].astype(np.float32)

    if needs_transpose:
        X_calib = np.transpose(X_calib, (0, 2, 1))  # (N, 2500, 12)

    print(f"Calibration data: {X_calib.shape}, dtype={X_calib.dtype}")

    # Convert with INT8 quantization
    print("\nConverting SavedModel to INT8 TFLite...")
    converter = tf.lite.TFLiteConverter.from_saved_model(SAVED_MODEL_DIR)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    def representative_dataset():
        for i in range(len(X_calib)):
            yield [X_calib[i:i+1]]

    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.float32  # keep output as float for AUC thresholds

    tflite_model = converter.convert()

    with open(INT8_PATH, "wb") as f:
        f.write(tflite_model)

    size_kb = os.path.getsize(INT8_PATH) / 1024
    print(f"\n✅ INT8 TFLite saved: {INT8_PATH}")
    print(f"   Size: {size_kb:.1f} KB")

    # Quick verification
    print("\nVerifying INT8 model...")
    interpreter = tf.lite.Interpreter(model_path=INT8_PATH)
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    print(f"   Input:  shape={inp['shape']}, dtype={inp['dtype']}")
    print(f"   Output: shape={out['shape']}, dtype={out['dtype']}")

    # Test inference
    sample = X_calib[0:1]
    if inp['dtype'] == np.int8:
        scale, zero_point = inp['quantization']
        sample = (sample / scale + zero_point).astype(np.int8)
    interpreter.set_tensor(inp['index'], sample)
    interpreter.invoke()
    output = interpreter.get_tensor(out['index'])
    print(f"   Test output range: [{output.min():.4f}, {output.max():.4f}]")
    print("\n✅ INT8 quantization complete!")

if __name__ == "__main__":
    main()
