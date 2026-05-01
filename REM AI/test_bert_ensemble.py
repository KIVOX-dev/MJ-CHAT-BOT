import os
import sys

# Mocking modules to point to active directory
sys.path.append(os.getcwd())

from learning import REMLearningSys
from memory import MemoryLayer

def test_bert_integration():
    print("--- REM AI BERT ENSEMBLE TEST ---")
    
    ls = REMLearningSys(model_dir="test_models")
    ml = MemoryLayer()
    
    # Check if we have enough memory to train
    mem_count = len(ml.read_all())
    print(f"[*] Memory count: {mem_count}")
    
    if mem_count < 5:
        print("[!] Not enough memory for local training. Please chat with REM AI first.")
        # Create dummy memory if empty for testing
        print("[*] Creating synthetic memories for test...")
        ml.store("What is PyTorch?", "PyTorch is an AI library.", "context", "test", "1.0", ["verified-persistent"])
        ml.store("Who is the CEO of Microsoft?", "Satya Nadella.", "context", "test", "1.0", ["verified-persistent"])
        ml.store("What is the capital of France?", "Paris.", "context", "test", "1.0", ["verified-persistent"])
        ml.store("How many planets are in the solar system?", "Eight.", "context", "test", "1.0", ["verified-persistent"])
        ml.store("What is the speed of light?", "299,792,458 m/s.", "context", "test", "1.0", ["verified-persistent"])

    # 1. Test BERT Embedding Extraction
    print("\n--- STEP 1: Testing BERT Embedding Extraction ---")
    vec = ls.get_embeddings(["Hello world, this is a BERT test."])
    if vec is not None and vec.shape == (1, 768):
        print("[SUCCESS] BERT Embedding generated successfully (Shape: 1x768).")
    else:
        print(f"[FAIL] BERT Embedding failed or returned wrong shape: {vec.shape if vec is not None else 'None'}")
        return

    # 2. Test Adapt Memory (Training)
    print("\n--- STEP 2: Testing Memory Adaptation (Training) ---")
    success = ls.adapt_memory(ml)
    if success:
        print("[SUCCESS] Ensemble retrained with BERT features.")
    else:
        print("[FAIL] Memory adaptation failed.")
        return

    # 3. Test Prediction
    print("\n--- STEP 3: Testing Semantic Prediction ---")
    # Test with a question that is semantically similar but not identical to training
    test_q = "Can you tell me the CEO of MSFT?"
    ans, conf = ls.predict(test_q)
    print(f"Query: {test_q}")
    print(f"Ensemble Result: {ans}")
    print(f"Confidence: {round(conf, 2)}")
    
    if ans == "Satya Nadella.":
        print("[SUCCESS] Ensemble correctly identified the answer using semantic BERT vectors!")
    else:
        print("[WARNING] Ensemble did not reach consensus or returned wrong answer.")

if __name__ == "__main__":
    if not os.path.exists("test_models"):
         os.makedirs("test_models")
    test_bert_integration()
