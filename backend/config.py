import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json") 

# Model Hyperparameters
CONFIDENCE_THRESHOLD = 0.90 # Minimum confidence to trust internal model summary
TRAIN_INTERVAL = 5           # Train model every N new memories
