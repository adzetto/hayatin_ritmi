"""Export combined model to TFLite INT8 with calibration data."""
import os, sys, numpy as np, tensorflow as tf

TFLITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "tflite")
INT8_PATH  = os.path.join(TFLITE_DIR, "ecg_combined_int8.tflite")
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "dataset_cache.npz")

data = np.load(CACHE_FILE, allow_pickle=True)
X = data["X"]

loaded = tf.saved_model.load(TFLITE_DIR)
infer = loaded.signatures["serving_default"]
input_key = list(infer.structured_input_signature[1].keys())[0]
input_spec = infer.structured_input_signature[1][input_key]
print(f"SavedModel input: name={input_key}, shape={input_spec.shape}")

shape = input_spec.shape.as_list()
needs_transpose = len(shape) == 3 and shape[-1] == 12

rng = np.random.RandomState(42)
idx = rng.choice(len(X), size=min(200, len(X)), replace=False)
X_calib = X[idx].astype(np.float32)
if needs_transpose:
    X_calib = np.transpose(X_calib, (0, 2, 1))
    print("Transposed to channels-last")
print(f"Calibration: {X_calib.shape}")

converter = tf.lite.TFLiteConverter.from_saved_model(TFLITE_DIR)
converter.optimizations = [tf.lite.Optimize.DEFAULT]

def representative_dataset():
    for i in range(len(X_calib)):
        yield [X_calib[i:i+1]]

converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.float32

tflite_model = converter.convert()
with open(INT8_PATH, "wb") as f:
    f.write(tflite_model)

size_kb = os.path.getsize(INT8_PATH) / 1024
print(f"INT8 TFLite saved: {INT8_PATH} ({size_kb:.1f} KB)")

interp = tf.lite.Interpreter(model_path=INT8_PATH)
interp.allocate_tensors()
inp_d = interp.get_input_details()[0]
out_d = interp.get_output_details()[0]
print(f"Input:  shape={inp_d['shape']}, dtype={inp_d['dtype']}")
print(f"Output: shape={out_d['shape']}, dtype={out_d['dtype']}")
print("Done!")
