from memory import MemoryLayer
from learning import REMLearningSys
import os

def debug_train():
    print("[*] Debug: Initializing MemoryLayer...")
    mem = MemoryLayer()
    print("[*] Debug: Initializing REMLearningSys...")
    learn = REMLearningSys()
    
    print("[*] Debug: Triggering adapt_memory...")
    success = learn.adapt_memory(mem)
    
    if success:
        print("[+] SUCCESS: Model trained and saved.")
        print(f"[*] Vocab Size: {learn.vocab_size}")
        print(f"[*] Classes: {learn.classes}")
        
        # Test a prediction
        res, conf = learn.predict("test query")
        print(f"[*] Test Prediction: {res} ({round(conf*100, 2)}%)")
    else:
        print("[!] FAILED: adapt_memory returned False (likely < 5 entries or no classes).")

if __name__ == "__main__":
    debug_train()
