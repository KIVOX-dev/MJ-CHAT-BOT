import sys
import time
from memory import MemoryLayer
from reasoning import ReasoningLayer
from learning import REMLearningSys
from math_tools import solve_math
from config import CONFIDENCE_THRESHOLD

# Initialize global engines
_memory_sys = MemoryLayer()
_learning_sys = REMLearningSys()
_reasoner = ReasoningLayer(learning_sys=_learning_sys)

def autonomous_loop(user_input: str, session_id: str = "default", owner: str = "default") -> dict:
    """
    Main Autonomous Bridge.
    Connects Input -> Local Learning -> Context History -> Agentic Reasoning -> Memory -> UI

    `owner` is the authenticated caller's identity (see auth.py) and scopes
    every memory read/write so one identity's sessions and history stay
    invisible to another (closes the IDOR that used to let any client read
    any session_id). Defaults to "default" for CLI/script callers that have
    no auth context - the same shared bucket pre-auth data already lives in.
    """
    start_time = time.time()
    
    # 0. Quick Human-like Greeting Bypass
    greetings = ["hi", "hello", "hey", "hola", "greetings"]
    if user_input.lower().strip() in greetings:
        return {
            "answer": "Hello! I'm MJ AI, your autonomous researcher. How can I help you today?",
            "source": "Core Logic (Instant Greeting)",
            "confidence": "Perfect",
            "math_used": False,
            "web_used": False,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 0.05 Detect Confirmation Intent (Yes/No) for Pending Memories
    confirmation_map = {
        "yes": True, "yep": True, "yeah": True, "save": True, "confirm": True, "do it": True,
        "no": False, "nope": False, "nah": False, "don't save": False, "stop": False
    }
    
    clean_input = user_input.lower().strip().replace(".", "").replace("!", "")
    if clean_input in confirmation_map:
        if confirmation_map[clean_input]:
            # Commit
            success = _memory_sys.confirm_memory(session_id, owner)
            if success:
                 return {
                    "answer": "✅ Saved successfully. I will remember this for future sessions.",
                    "source": "Core Logic (Memory Commit)",
                    "confidence": "Manual Confirmation",
                    "math_used": False,
                    "web_used": False,
                    "latency_ms": round((time.time() - start_time) * 1000, 2)
                }
        else:
            # Reject
            success = _memory_sys.reject_memory(session_id, owner)
            return {
                "answer": "Okay, not saved. I'll keep our future discussions focused on your direct questions.",
                "source": "Core Logic (Memory Rejection)",
                "confidence": "Manual Rejection",
                "math_used": False,
                "web_used": False,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # If input was a trigger but no pending memory found
        return {
            "answer": "I don't see any pending summaries to save. You can ask me to 'summarize this' if you want to create a memory point.",
            "source": "Core Logic",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 0.1 Fetch History for Context
    history = _memory_sys.get_session_history(session_id, owner)
    history_context = ""
    if history:
        history_context = "\n".join([f"User: {m['input']}\nAI: {m['output']}" for m in history[-3:]]) # Last 3 turns
    
    # 0.2 Lazy Ensemble Check: Skip BERT for confirmations, simple summaries, or RedSage scans
    is_meta_query = clean_input in confirmation_map or \
                   any(k in user_input.lower() for k in ["summarize", "short version", "brief", "redsage", "security audit", "vulnerability"])
    
    local_answer, local_conf = None, 0.0
    if not is_meta_query:
        # 1. Warm up BERT (Pre-loads weights) if ensemble is active
        try:
            if hasattr(_learning_sys, "_init_bert"):
                _learning_sys._init_bert()
        except Exception: pass

        # 2. Local Learning Check (Instant Brain)
        local_answer, local_conf = _learning_sys.predict(user_input)
    
    if local_answer and local_conf >= CONFIDENCE_THRESHOLD:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "answer": local_answer,
            "source": f"Internal Ensemble (Conf: {round(local_conf*100, 1)}%)",
            "confidence": "High (Local Cache)",
            "math_used": False,
            "web_used": False,
            "latency_ms": latency_ms
        }
    
    # 2. Pre-analysis (Math Tool)
    math_result = solve_math(user_input)
    relevant_mems = _memory_sys.find_relevant(user_input, owner)
    
    # Bundle context cleanly
    prompt_parts = []
    if math_result:
        prompt_parts.append(f"<math_analysis>{math_result}</math_analysis>")
    if relevant_mems:
        prompt_parts.append(f"<internal_memory>{relevant_mems[0]['output']}</internal_memory>")
    if history_context:
        prompt_parts.append(f"<chat_history>\n{history_context}\n</chat_history>")
    
    prompt_parts.append(f"<user_query>{user_input}</user_query>")
    augmented_prompt = "\n\n".join(prompt_parts)

    # 4. RedSage Security Audit Trigger
    if any(k in user_input.lower() for k in ["redsage", "security audit", "vulnerability scan"]):
        from redsage import RedSageAgent, RedSageRateLimitError
        try:
            RedSageAgent.check_rate_limit(owner)
        except RedSageRateLimitError as e:
            return {
                "answer": f"⏳ {e}",
                "source": "RedSage Specialist",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

        agent = RedSageAgent()
        report_md = agent.generate_audit_report()

        # Save report as artifact for UI display
        report_filename = f"redsage_audit_{int(time.time())}.md"
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        frontend_dir = os.path.join(base_dir, "frontend")
        with open(os.path.join(frontend_dir, report_filename), "w") as f:
            f.write(report_md)
            
        return {
            "answer": f"RedSage scan complete. I have generated a detailed security audit for the codebase. You can find the high-severity findings in the Eagle Eye report.",
            "source": "RedSage Specialist",
            "report_url": f"/static/{report_filename}"
        }

    # 5. Reasoning Engine (Ollama/Gemini/Research)
    reasoning_output = _reasoner.generate_response(augmented_prompt)
    
    final_answer = reasoning_output["answer"]
    source = reasoning_output["source"]
    web_used = reasoning_output.get("web_used", False)
    latency_ms = round((time.time() - start_time) * 1000, 2)

    # 4. Storage & Training Data
    msg_id = _memory_sys.store(
        input_text=user_input, 
        output_text=final_answer, 
        context="\n".join(prompt_parts[:-1]), # Exclude the user query for storage context
        source=source, 
        confidence="high",
        tags=["pending-confirmation"] if "[MEM_SUMMARY:" in final_answer else (["research-active"] if web_used else ["conversational"]),
        latency_ms=latency_ms,
        session_id=session_id,
        owner=owner
    )

    return {
        "msg_id": msg_id,
        "answer": final_answer,
        "source": source,
        "confidence": "High (Autonomous)" if web_used else "High",
        "math_used": math_result is not None,
        "web_used": web_used,
        "latency_ms": latency_ms
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        res = autonomous_loop(query)
        print(f"\n[MJ AI]: {res['answer']}\n(Source: {res['source']} | Speed: {res['latency_ms']}ms)")
    else:
        print("Usage: python main.py <your query>")
