import os
import json
import sys
from memory import MemoryLayer

def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + ' ')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + ' ')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

def ingest_factbook(directory):
    memory = MemoryLayer()
    count = 0
    
    print(f"[*] Starting ingestion for: {directory}")
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Extract country name from filename or top key
                    country_code = file.split('.')[0].upper()
                    
                    # Flatten the data into facts
                    facts = flatten_json(data)
                    
                    for key, value in facts.items():
                        # Create a semantic memory entry
                        fact_input = f"{country_code} {key}"
                        fact_output = str(value)
                        
                        # Store in REM Memory
                        memory.store(
                            input_text=fact_input,
                            output_text=fact_output,
                            context=f"Ingested from CIA Factbook: {file}",
                            source="Local Knowledge Base (Factbook)",
                            confidence="high",
                            tags=["cia-factbook", "imported-knowledge", country_code]
                        )
                        count += 1
                        
                except Exception as e:
                    print(f"[!] Error processing {file}: {e}")

    print(f"[+] Ingestion complete. Added {count} facts to REM Memory.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <directory_path>")
    else:
        ingest_factbook(sys.argv[1])
