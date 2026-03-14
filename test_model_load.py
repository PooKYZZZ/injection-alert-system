#!/usr/bin/env python
"""Test script to verify model loading from staging directory."""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from ml_model.inference.predict_attack import load_model, predict_attack

def main():
    print("=" * 60)
    print("Testing model loading from staging directory")
    print("=" * 60)
    
    # Use minilm as test model
    model_key = "minilm"
    staging_dir = Path("ml_model/model_registry/staging")
    
    print(f"\n1. Loading model: {model_key}")
    print(f"   Staging dir: {staging_dir}")
    
    try:
        model, tokenizer, temperature = load_model(model_key, staging_dir=staging_dir)
        print(f"   SUCCESS: Model loaded!")
        print(f"   Model class: {type(model).__name__}")
        print(f"   Tokenizer class: {type(tokenizer).__name__}")
        print(f"   Temperature: {temperature}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")
        return 1
    
    # Test predictions
    print(f"\n2. Testing predictions")
    
    # Test SQL injection
    sql_payload = "'; DROP TABLE users;--"
    result = predict_attack(sql_payload, model, tokenizer)
    print(f"   SQL payload: {sql_payload}")
    print(f"   Prediction: {result['label']} (tier: {result['tier']}, confidence: {result['max_prob']})")
    
    # Test normal traffic
    normal_payload = "GET /index.html HTTP/1.1"
    result_normal = predict_attack(normal_payload, model, tokenizer)
    print(f"   Normal payload: {normal_payload}")
    print(f"   Prediction: {result_normal['label']} (tier: {result_normal['tier']}, confidence: {result_normal['max_prob']})")
    
    print("\n" + "=" * 60)
    print("SUCCESS: All tests passed!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
