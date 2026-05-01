import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", "")
MEMORY_FILE = "memory.json" 

# Model Hyperparameters
CONFIDENCE_THRESHOLD = 0.90 # Minimum confidence to trust internal model summary
TRAIN_INTERVAL = 5           # Train model every N new memories
