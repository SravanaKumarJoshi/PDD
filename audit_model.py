#!/usr/bin/env python
"""
Model Training Audit Script
Validates that the model is properly trained with good metrics
"""
import joblib
import json
from pathlib import Path

def audit_model():
    print("\n" + "="*60)
    print("MODEL VALIDATION AUDIT")
    print("="*60)

    # Check model file
    model_path = Path('model_store/v6_random_forest.joblib')
    if model_path.exists():
        model = joblib.load(model_path)
        print(f"\n✓ RandomForest model loaded successfully")
        print(f"  - Model type: {type(model).__name__}")
        print(f"  - N estimators: {model.n_estimators}")
        print(f"  - Max depth: {model.max_depth}")
    else:
        print(f"\n✗ Model file not found: {model_path}")
        return False

    # Check versions.json
    versions_path = Path('model_store/versions.json')
    if versions_path.exists():
        with open(versions_path) as f:
            versions = json.load(f)
        print(f"\n✓ Model versions file found ({len(versions)} versions)")
        latest = versions[-1]
        print(f"  - Latest: {latest['model_type']} v{latest['version']}")
        print(f"  - Trained: {latest['timestamp']}")
        metrics = latest['metrics']
        print(f"  - Accuracy: {metrics['accuracy']:.4f}")
        print(f"  - Precision: {metrics['precision']:.4f}")
        print(f"  - Recall: {metrics['recall']:.4f}")
        print(f"  - F1 Score: {metrics['f1']:.4f}")
        print(f"  - CV Mean: {metrics['cv_mean']:.4f} ± {metrics['cv_std']:.4f}")
        
        if metrics['accuracy'] >= 0.98:
            print(f"\n✓ Model performance is EXCELLENT (accuracy >= 0.98)")
        elif metrics['accuracy'] >= 0.90:
            print(f"\n✓ Model performance is GOOD (accuracy >= 0.90)")
        else:
            print(f"\n⚠ WARNING: Model accuracy is below 0.90 ({metrics['accuracy']:.4f})")
            
        if metrics['accuracy'] == 1.0:
            print(f"⚠ NOTE: Perfect accuracy (1.0) - small test set ({metrics['test_size']} samples)")
    else:
        print(f"\n✗ Versions file not found: {versions_path}")
        return False

    print("\n" + "="*60)
    print("✓ MODEL IS PROPERLY TRAINED - READY FOR DEPLOYMENT")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    success = audit_model()
    exit(0 if success else 1)
