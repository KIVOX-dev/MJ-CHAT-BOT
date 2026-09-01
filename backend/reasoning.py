import os
import time
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Primary Engine: Ollama
try:
    import ollama
except ImportError:
    ollama = None
    logging.warning("Ollama library not found. Local generation will be disabled.")

# Optional: Cloud Engines
try:
    from google import genai
except ImportError:
    genai = None
    logging.warning("google-genai library not found. Gemini fallback will be disabled.")

try:
    import dashscope
except ImportError:
    dashscope = None
    logging.warning("dashscope library not found. Qwen Cloud will be disabled.")

from config import GEMINI_API_KEY, DASHSCOPE_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY
from web_tools import search_web, fetch_web_content

class ReasoningLayer:
    def __init__(self, learning_sys=None):
        self.learning_sys = learning_sys
        self.gemini_client = None
        self.ollama_client = None
        
        # Initialize Ollama Client
        if ollama:
            try:
                self.ollama_client = ollama.Client(host='http://127.0.0.1:11434')
            except Exception as e:
                logging.error(f"Ollama client init error: {e}")

        if genai and GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                logging.error(f"Failed to init Gemini: {e}")
            
        self.dashscope_key = DASHSCOPE_API_KEY
        if dashscope and self.dashscope_key:
            dashscope.api_key = self.dashscope_key

        self.openrouter_key = OPENROUTER_API_KEY
        self.groq_key = GROQ_API_KEY

        self.preferred_local = "phi3:latest"
        self.researcher_cloud = "qwen-max" 

    def generate_response(self, prompt: str) -> dict:
        """
        Orchestrates the Reasoning + Research loop with a Performance Fast-Path.
        """
        # --- Speed Optimization: Detection of Summary Fast-Path ---
        summary_keywords = ["summarize", "give summary", "short version", "brief", "what happened"]
        is_summary_request = any(k in prompt.lower() for k in summary_keywords)
        
        system_instructions = (
            "You are REM AI, a helpful and natural autonomous assistant. Your behavior MUST follow these rules strictly:\n\n"
            "1. NORMAL CONVERSATION MODE:\n"
            "- If the user is having a normal conversation (questions, discussions, casual chat, problem-solving), respond naturally like a human assistant.\n"
            "- Keep responses clear, helpful, and relevant.\n"
            "- Do NOT summarize or offer to save unless explicitly asked.\n\n"
            "2. SUMMARY MODE:\n"
            "- If the user asks to 'summarize', 'give summary', 'short version', or similar:\n"
            "  → Generate a clear, concise summary of the provided content or conversation.\n"
            "  → Keep it structured and easy to read (use bullet points).\n"
            "  → Wrap this summary strictly in the [MEM_SUMMARY: <summary>] tag for the system to process.\n\n"
            "3. MEMORY CONFIRMATION STEP:\n"
            "- After providing a summary, ALWAYS ask the user: 'Do you want me to save this in memory for future reference? (Yes/No)'\n\n"
            "4. MEMORY STORAGE RULE:\n"
            "- Only save data if the user explicitly says 'Yes'. Do NOT automatically store conversations.\n\n"
            "7. RESPONSE STYLE:\n"
            "- Keep tone natural and human-like. Avoid robotic replies. Be concise but informative.\n\n"
            "8. IDENTITY RULE (CRITICAL):\n"
            "- You ARE MJ AI, an independent artificial intelligence.\n\n"
            "- NEVER claim to be developed by Microsoft, Google, OpenAI, or any other corporation.\n\n"
            "- If asked about your origin, state that you are MJ AI, a high-performance intelligence engine designed for research and research assistance."
        )
        
        history = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": prompt}
        ]

        # --- Fast-Path Execution (Single-Shot for Summaries) ---
        if is_summary_request:
            logging.info("[PERF] Summary Fast-Path triggered. Skipping research loop.")
            ai_output = self._call_ai_engine(history, fast_mode=True)
            return {
                "answer": ai_output["text"], 
                "source": ai_output["model"] + " (Fast Path)", 
                "web_used": False
            }

        # --- Standard Researcher Mode (3-iteration loop) ---
        for iteration in range(3):
            logging.info(f"Researcher Iteration {iteration + 1}...")
            
            ai_output = self._call_ai_engine(history)
            text = ai_output["text"]
            model_name = ai_output["model"]

            # Command parsing
            if "[SEARCH:" in text:
                query = text.split("[SEARCH:")[1].split("]")[0].strip()
                logging.info(f"SEARCH triggered: {query}")
                search_results = search_web(query)
                history.append({"role": "assistant", "content": text})
                history.append({"role": "user", "content": f"Results:\n{json.dumps(search_results)}"})
                continue
            
            if "[FETCH:" in text:
                url = text.split("[FETCH:")[1].split("]")[0].strip()
                logging.info(f"FETCH triggered: {url}")
                page_content = fetch_web_content(url)
                history.append({"role": "assistant", "content": text})
                history.append({"role": "user", "content": f"Page Content:\n{page_content}"})
                continue
            
            # Post-process to remove redundant wrapping and programmatic noise
            cleaned_text = text.strip()
            
            # Identity Sanitization (RedSage/Identity Patch)
            # Remove hallucinations where the base model claims its corporate origin
            corporate_claims = [
                "As an AI developed by Microsoft", "By Microsoft", "Developed by Microsoft",
                "As an AI language model from Google", "By OpenAI", "Developed by OpenAI"
            ]
            for claim in corporate_claims:
                if claim in cleaned_text:
                    cleaned_text = cleaned_text.replace(claim, "As MJ AI")
            
            # Remove redundant prefixes
            for prefix in ["Assistant Response:", "Assistant:", "AI:", "[MJ AI]:"]:
                if cleaned_text.startswith(prefix):
                    cleaned_text = cleaned_text[len(prefix):].strip()

            # Identify if it's a simple conversational string incorrectly wrapped in code
            if cleaned_text.startswith("```"):
                # Extract content
                lines = cleaned_text.split("\n")
                if len(lines) >= 3:
                    first_line = lines[0].strip("`").lower()
                    content = "\n".join(lines[1:-1]).strip()
                    
                    if first_line in ["plaintext", "", "text"]:
                        if "print(" in content and len(content.split("\n")) < 4:
                             cleaned_text = content.replace('print("', '').replace('")', '').replace("print('", "").replace("')", "")
                    
                    if len(content.split("\n")) == 1 and not any(char in content for char in "{}[]();"):
                        cleaned_text = content
                
            return {"answer": cleaned_text, "source": model_name, "web_used": iteration > 0}

        return {"answer": "Research timed out. I couldn't reach a final conclusion.", "source": "REM Logic", "web_used": True}

    def _call_ai_engine(self, messages, fast_mode=False):
        """
        Engine tiering logic. 
        """
        # 0. Primary Chatbot Engine: Groq API
        if not self.groq_key:
            return {"text": "Error: GROQ_API_KEY is not configured in .env", "model": "None"}

        try:
            logging.info("Attempting Groq chat completions (Exclusive)...")
            import requests
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            # llama-3.3-70b-versatile and llama3-8b-8192 have both been
            # removed from Groq's catalog (confirmed via GET /v1/models) -
            # gpt-oss-120b is the current largest general-purpose model
            # Groq hosts, with gpt-oss-20b as the fallback.
            payload = {
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": m["role"], "content": m["content"]} for m in messages]
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    return {"text": choices[0]["message"]["content"], "model": "Groq GPT-OSS 120B"}
            else:
                logging.error(f"Groq API Error: {res.status_code} - {res.text}")
                # Try fallback model on Groq: gpt-oss-20b
                logging.info("Attempting Groq fallback model gpt-oss-20b...")
                payload["model"] = "openai/gpt-oss-20b"
                res_fb = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
                if res_fb.status_code == 200:
                    data = res_fb.json()
                    choices = data.get("choices", [])
                    if choices:
                        return {"text": choices[0]["message"]["content"], "model": "Groq GPT-OSS 20B"}
                else:
                    return {"text": f"Groq API Error: {res_fb.status_code} - {res_fb.text}", "model": "Groq Error"}
        except Exception as e:
            logging.error(f"Groq API primary call failed: {e}")
            return {"text": f"Groq connection failed: {e}", "model": "Groq Exception"}

        return {
            "text": "Critical: Groq Engine response failure.", 
            "model": "None"
        }
