import os
import threading
import json
from collections import Counter
from typing import List, Dict, Any
from memory import MemoryLayer
from config import MODEL_FILENAME

# Lazy loading helpers
def get_torch():
    import torch
    import torch.nn as nn
    import torch.optim as optim
    return torch, nn, optim

def get_sklearn():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.cluster import KMeans
    import joblib
    import numpy as np
    return RandomForestClassifier, KMeans, joblib, np

def get_bert():
    from transformers import AutoTokenizer, AutoModel
    import torch
    return AutoTokenizer, AutoModel, torch

class EnsembleBrain:
    """Consensus-based Deep Learning Engine (Lazy Initialized)."""
    @staticmethod
    def get_model_class():
        torch, nn, optim = get_torch()
        class Brain(nn.Module):
            def __init__(self, input_size, num_classes):
                super(Brain, self).__init__()
                self.l1 = nn.Linear(input_size, 128)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(0.2)
                self.l2 = nn.Linear(128, 64)
                self.l3 = nn.Linear(64, num_classes)
                self.softmax = nn.Softmax(dim=1)
            def forward(self, x):
                out = self.l1(x)
                out = self.relu(out)
                out = self.dropout(out)
                out = self.l2(out)
                out = self.relu(out)
                out = self.l3(out)
                return self.softmax(out)
        return Brain

class REMLearningSys:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, MODEL_FILENAME)
        self.lock = threading.Lock()
        
        # State
        self.brain = None
        self.forest = None
        self.kmeans = None
        self.tokenizer = None
        self.bert_model = None
        self.classes = []
        self.vocab_size = 768 # BERT base hidden size
        
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        # Attempt minimal load (only if files exist)
        try:
            self.load()
        except Exception:
            pass

    def save(self):
        _, nn, _ = get_torch()
        _, _, joblib, _ = get_sklearn()
        import torch
        with self.lock:
            state = {
                "brain_state": self.brain.state_dict() if self.brain else None,
                "classes": self.classes,
                "vocab_size": self.vocab_size
            }
            if self.brain:
                torch.save(state, self.model_path)
            if self.forest:
                joblib.dump(self.forest, os.path.join(self.model_dir, "forest.joblib"))

    def load(self):
        if not os.path.exists(self.model_path): return
        import torch
        _, _, joblib, _ = get_sklearn()
        
        # Secure Load (RedSage Patch: CWE-502)
        try:
            state = torch.load(self.model_path, map_location=torch.device('cpu'), weights_only=True)
            self.classes = state["classes"]
            self.vocab_size = state["vocab_size"]
            BrainClass = EnsembleBrain.get_model_class()
            self.brain = BrainClass(self.vocab_size, len(self.classes))
            self.brain.load_state_dict(state["brain_state"])
            self.brain.eval()

            f_path = os.path.join(self.model_dir, "forest.joblib")
            if os.path.exists(f_path): self.forest = joblib.load(f_path)
        except Exception as e:
            print(f"[!] Ensemble Load Warning: {e}")

    def _init_bert(self):
        """Loads BERT tokenizer and model if not already in memory."""
        if self.tokenizer and self.bert_model:
            return
        
        try:
            tokenizer_class, model_class, torch = get_bert()
            model_name = "distilbert-base-uncased"
            print(f"[*] Loading {model_name} for embeddings...")
            self.tokenizer = tokenizer_class.from_pretrained(model_name)
            self.bert_model = model_class.from_pretrained(model_name)
            self.bert_model.eval()
        except Exception as e:
            print(f"[!] BERT Init Error: {e}")

    def get_embeddings(self, texts: List[str]):
        """Converts a list of texts into BERT embeddings."""
        self._init_bert()
        if not self.bert_model or not self.tokenizer:
            return None
        
        import torch
        try:
            inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=128)
            with torch.no_grad():
                outputs = self.bert_model(**inputs)
            # Use [CLS] token embedding (first token)
            embeddings = outputs.last_hidden_state[:, 0, :].numpy()
            return embeddings
        except Exception as e:
            print(f"[!] Embedding Error: {e}")
            return None

    def adapt_memory(self, memory: MemoryLayer):
        torch, nn, optim = get_torch()
        RF, KM, joblib, np = get_sklearn()
        
        data = memory.read_all()
        if len(data) < 5: return False
        
        with self.lock:
            enriched_data = []
            for entry in data:
                enriched_data.append(entry)
                if entry.get("feedback") == "up":
                    enriched_data.extend([entry] * 2) 

            texts = [e.get("input", "").lower() for e in enriched_data]
            labels = [e.get("output", "") for e in enriched_data]
            unique_classes = list(set(labels))
            
            if len(unique_classes) < 2: return False
            self.classes = unique_classes
            y_encoded = [self.classes.index(l) for l in labels]

            # BERT Vectorization
            print("[*] Performing BERT vectorization on memory...")
            X_vec = self.get_embeddings(texts)
            if X_vec is None: return False
            
            # Random Forest
            print("[*] Training Random Forest consensus...")
            self.forest = RF(n_estimators=100)
            self.forest.fit(X_vec, y_encoded)
            self.vocab_size = X_vec.shape[1]

            # K-Means
            print("[*] Clustering semantic space with K-Means...")
            self.kmeans = KM(n_clusters=min(len(data), 10), n_init='auto')
            self.kmeans.fit(X_vec)

            # Brain (Deep NN)
            print("[*] Training BERT-MLP reasoning head...")
            X_tensor = torch.tensor(X_vec, dtype=torch.float32)
            y_tensor = torch.tensor(y_encoded, dtype=torch.long)
            
            BrainClass = EnsembleBrain.get_model_class()
            self.brain = BrainClass(self.vocab_size, len(self.classes))
            optimizer = optim.Adam(self.brain.parameters(), lr=0.001)
            criterion = nn.CrossEntropyLoss()
            
            for epoch in range(200):
                optimizer.zero_grad()
                outputs = self.brain(X_tensor)
                loss = criterion(outputs, y_tensor)
                loss.backward()
                optimizer.step()

            self.save()
            print("[SUCCESS] BERT Ensemble updated.")
            return True

    def predict(self, text: str):
        import torch
        _, _, _, np = get_sklearn()
        
        if not self.brain:
            return None, 0.0

        try:
            vec = self.get_embeddings([text])
            if vec is None: return None, 0.0
            
            vec_tensor = torch.tensor(vec, dtype=torch.float32)

            self.brain.eval()
            with torch.no_grad():
                b_out = self.brain(vec_tensor)
                b_conf, b_pred = torch.max(b_out, 1)

            f_probs = self.forest.predict_proba(vec)[0] if self.forest else None
            f_conf = np.max(f_probs) if f_probs is not None else 0.0
            f_pred = np.argmax(f_probs) if f_probs is not None else -1

            consensus_conf = (b_conf.item() + f_conf) / 2
            if self.forest and b_pred.item() == f_pred:
                return self.classes[b_pred.item()], consensus_conf
            elif b_conf.item() > 0.85:
                return self.classes[b_pred.item()], b_conf.item() * 0.8 # Penalty for no forest consensus
            return None, 0.0
        except Exception as e:
            print(f"[!] Prediction Error: {e}")
            return None, 0.0
