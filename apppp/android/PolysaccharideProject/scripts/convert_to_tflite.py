"""
convert_to_tflite.py
====================
Part 5 — Train a Keras proxy model and convert it to TFLite for Android.
Updated for Clinical Mode (20-feature normalized schema).
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import joblib

# Suppress only sklearn/TF warnings, not all
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", message=".*ConvergenceWarning.*")

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR   = os.path.join(BASE_DIR, "models", "clinical")
ASSET_DIR   = os.path.join(BASE_DIR, "app_assets")
MASTER_DATA = os.path.join(BASE_DIR, "datasets", "processed", "master_clinical_dataset.csv")

def convert():
    print("=" * 60)
    print("POLYSACCHARIDE PROJECT — PART 5: TFLITE CONVERSION (CLINICAL)")
    print("=" * 60)
    try:
        import tensorflow as tf
    except ImportError:
        print("ERROR: TensorFlow not installed. Run: pip install tensorflow")
        return

    os.makedirs(ASSET_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    # ─── Load sklearn artifacts ───────────────────────────────────────────────
    pipeline  = joblib.load(os.path.join(MODEL_DIR, "clinical_model_pipeline.joblib"))
    target_le = joblib.load(os.path.join(MODEL_DIR, "clinical_label_encoders.pkl"))

    with open(os.path.join(MODEL_DIR, "model_manifest.json"), "r") as f:
        manifest = json.load(f)

    feature_cols = manifest["feature_names"]
    target_col   = "category"
    num_classes  = len(target_le.classes_)
    num_features = len(feature_cols)

    print(f"  Features: {num_features}, Classes: {num_classes} → {target_le.classes_.tolist()}")

    # ─── Prepare training data ────────────────────────────────────────────────
    df = pd.read_csv(MASTER_DATA, encoding="utf-8")
    df = df[df[target_col].notna() & (df[target_col].astype(str) != "Unknown")]
    known = set(target_le.classes_)
    df = df[df[target_col].isin(known)].copy()

    # Pre-fill structural unknowns for the pipeline
    for col in feature_cols:
        if col not in df.columns:
            df[col] = np.nan
            
    X_raw = df[feature_cols].copy()
    y = target_le.transform(df[target_col].astype(str)).astype(np.int32)
    
    preprocessor = pipeline.named_steps["preprocessor"]
    X_scaled = preprocessor.transform(X_raw).astype(np.float32)

    print(f"  Training data shape: X={X_scaled.shape}, y={y.shape}")

    # ─── Build Keras model ────────────────────────────────────────────────────
    tf.random.set_seed(42)
    keras_model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(num_features,)),
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ], name="polysaccharide_classifier")

    keras_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    print("  Training Keras model (100 epochs)...")
    history = keras_model.fit(
        X_scaled, y,
        epochs=100,
        batch_size=min(32, len(X_scaled)),
        validation_split=0.15,
        verbose=0,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(patience=15, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(patience=8, factor=0.5, min_lr=1e-5),
        ]
    )
    final_acc = history.history["accuracy"][-1]
    print(f"  ✓ Keras training done. Final accuracy: {final_acc:.4f}")

    # ─── Convert to TFLite ────────────────────────────────────────────────────
    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    # Save to models/
    tflite_model_path = os.path.join(MODEL_DIR, "trained_model.tflite")
    with open(tflite_model_path, "wb") as f:
        f.write(tflite_model)
    print(f"  ✓ TFLite model saved → {tflite_model_path} ({len(tflite_model):,} bytes)")

    # Copy to app_assets/
    asset_tflite_path = os.path.join(ASSET_DIR, "trained_model.tflite")
    with open(asset_tflite_path, "wb") as f:
        f.write(tflite_model)

    # Copy feature_columns.json to app_assets/
    asset_fc_path = os.path.join(ASSET_DIR, "feature_columns.json")
    with open(asset_fc_path, "w") as f:
        json.dump(feature_cols, f, indent=2)

    # Save label_classes.json for Android inference
    label_classes_path = os.path.join(ASSET_DIR, "label_classes.json")
    with open(label_classes_path, "w") as f:
        json.dump(target_le.classes_.tolist(), f, indent=2)

    print(f"  ✓ Assets updated in: {ASSET_DIR}")
    print(f"    trained_model.tflite")
    print(f"    feature_columns.json")
    print(f"    label_classes.json")

    # ─── Quick TFLite inference test ─────────────────────────────────────────
    print("\n  Running TFLite inference test...")
    interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
    interpreter.allocate_tensors()
    in_details  = interpreter.get_input_details()
    out_details = interpreter.get_output_details()

    test_input = X_scaled[0:1]
    interpreter.set_tensor(in_details[0]["index"], test_input)
    interpreter.invoke()
    output = interpreter.get_tensor(out_details[0]["index"])
    pred_class = target_le.classes_[np.argmax(output)]
    confidence = float(np.max(output))
    print(f"  TFLite test prediction: {pred_class} (confidence={confidence:.4f})")

    print("\n✅ Part 5 complete — convert_to_tflite.py finished.")

if __name__ == "__main__":
    convert()
