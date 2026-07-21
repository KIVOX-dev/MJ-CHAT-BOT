import json
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory import MemoryLayer
from learning import REMLearningSys

def train_mcq_data():
    print("[*] Initializing Memory Layer and Learning System...")
    memory_sys = MemoryLayer()
    learning_sys = REMLearningSys()

    mcq_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcq_data")
    files_to_import = ["questions.json", "data_interpretation.json", "quantitative.json"]

    total_imported = 0

    print("[*] Reading MCQ data files...")
    for filename in files_to_import:
        file_path = os.path.join(mcq_dir, filename)
        if not os.path.exists(file_path):
            print(f"[!] Warning: File {filename} not found, skipping.")
            continue
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"[*] Importing {len(data)} items from {filename}...")
            for idx, item in enumerate(data):
                # Clean elements
                question = item.get("question", "").strip()
                options = item.get("options", [])
                answer = item.get("answer", "").strip()
                explanation = item.get("explanation", "").strip()

                if not question:
                    continue

                # Format answer text block
                output_text = f"Correct Answer: {answer}\n\nExplanation:\n{explanation}"
                if options:
                    output_text = f"Options:\n" + "\n".join([f"- {opt}" for opt in options]) + "\n\n" + output_text
                
                context = f"Topic: Aptitude / {filename.replace('.json', '').replace('_', ' ').title()}"

                # Store as verified-persistent in the default session
                memory_sys.store(
                    input_text=question,
                    output_text=output_text,
                    context=context,
                    source="MCQ Dataset Import",
                    confidence="high",
                    tags=["verified-persistent"],
                    session_id="default"
                )
                total_imported += 1
                
        except Exception as e:
            print(f"[!] Error processing {filename}: {e}")

    print(f"[+] Successfully loaded {total_imported} MCQ entries into local memory system.")

    # Trigger local ML model training
    print("[*] Adapting internal BERT Ensemble Neural Network and classifiers...")
    success = learning_sys.adapt_memory(memory_sys)
    if success:
        print("[SUCCESS] Local BERT Ensemble MLP and Random Forest trained on MCQ data.")
    else:
        print("[!] Local training skipped or failed (needs at least 5 feedback/memory points).")

if __name__ == "__main__":
    train_mcq_data()
