import requests
import json
import time

def test_refined_memory_flow():
    url = "http://127.0.0.1:8086/api/chat"
    session_id = f"test_refined_{int(time.time())}"
    
    # 1. Trigger Summarization
    print("\n--- STEP 1: Triggering Summarization ---")
    q1 = "REM, please remember that the planet Mars is also known as the Red Planet. Save this in memory."
    res1 = requests.post(url, json={"query": q1, "session_id": session_id}, timeout=30)
    answer1 = res1.json().get('answer')
    print(f"AI Response: {answer1}")
    
    if answer1.startswith("[MEM_SUMMARY:"):
        print("[SUCCESS] AI started response with the summary tag.")
    else:
        print("[FAIL] AI response format incorrect.")
        return

    # 2. Confirm Save (Text)
    print("\n--- STEP 2: Confirming Save ---")
    q2 = "save"
    res2 = requests.post(url, json={"query": q2, "session_id": session_id}, timeout=30)
    print(f"AI Response confirmed.")
    
    # 3. Verify Retrieval (Strict Check)
    print("\n--- STEP 3: Verifying Clean Retrieval ---")
    q3 = "What is another name for planet Mars?"
    res3 = requests.post(url, json={"query": q3, "session_id": f"new_clean_test_{int(time.time())}"}, timeout=30)
    answer3 = res3.json().get('answer')
    print(f"AI Response: {answer3}")
    
    if "Red Planet" in answer3:
        if "MEM_SUMMARY" not in answer3 and "Confirm saving" not in answer3:
             print("[SUCCESS] Memory retrieved and it is CLEAN (no tags or prompts)!")
        else:
             print("[WARNING] Memory retrieved but contained metadata/tags.")
    else:
        print("[FAIL] Memory was not retrieved correctly.")

if __name__ == "__main__":
    test_refined_memory_flow()
