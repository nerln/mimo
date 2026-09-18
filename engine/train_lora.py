#!/usr/bin/env python3
"""
train_lora.py - Fine-Tuning LoRA locale su Apple Silicon (Metal/MPS)

Addestra adattatori a basso rango (LoRA) sui turni conversazionali estratti
utilizzando PyTorch con accelerazione hardware su chip M4 (MPS).
Salva i pesi dell'adattatore in models/adapters/.
"""

import os
import sys
import json
import math
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ADAPTERS_DIR = ROOT / "models" / "adapters"

def select_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

class ConversationDataset(Dataset):
    def __init__(self, jsonl_path: Path, vocab: Dict[str, int], max_len: int = 256):
        self.samples = []
        self.vocab = vocab
        self.max_len = max_len

        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        item = json.loads(line)
                        msgs = item.get("messages", [])
                        text = " ".join(m["content"] for m in msgs)
                        tokens = [self.vocab.get(w, self.vocab["<unk>"]) for w in text.split()]
                        if len(tokens) > 2:
                            tokens = tokens[:max_len]
                            self.samples.append(torch.tensor(tokens, dtype=torch.long))
                    except Exception:
                        continue

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]

def collate_batch(batch: List[torch.Tensor], pad_token: int = 0):
    max_len = max(len(s) for s in batch)
    padded = torch.full((len(batch), max_len), pad_token, dtype=torch.long)
    for i, s in enumerate(batch):
        padded[i, :len(s)] = s
    return padded

class LoRALinear(nn.Module):
    """Implementazione pura di Low-Rank Adaptation (LoRA) per layer lineari."""
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 16.0):
        super().__init__()
        self.base = nn.Linear(in_features, out_features, bias=False)
        self.base.weight.requires_grad = False  # Pesi base congelati
        self.rank = rank
        self.scaling = alpha / rank
        self.lora_A = nn.Parameter(torch.zeros(in_features, rank))
        self.lora_B = nn.Parameter(torch.zeros(rank, out_features))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        base_out = self.base(x)
        lora_out = (x @ self.lora_A @ self.lora_B) * self.scaling
        return base_out + lora_out

class StyleAdapterModel(nn.Module):
    """Modello neurale autoregressivo compatto con blocchi LoRA per apprendere lo stile comunicativo."""
    def __init__(self, vocab_size: int, embed_dim: int = 256, num_layers: int = 4, rank: int = 8):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.layers = nn.ModuleList([
            nn.ModuleDict({
                "attn_proj": LoRALinear(embed_dim, embed_dim, rank=rank),
                "ffn_in": LoRALinear(embed_dim, embed_dim * 2, rank=rank),
                "ffn_out": LoRALinear(embed_dim * 2, embed_dim, rank=rank),
                "ln": nn.LayerNorm(embed_dim)
            })
            for _ in range(num_layers)
        ])
        self.head = nn.Linear(embed_dim, vocab_size, bias=False)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        h = self.embedding(input_ids)
        for layer in self.layers:
            residual = h
            # Proiezione stile LoRA
            h_attn = torch.relu(layer["attn_proj"](h))
            h_ffn = torch.relu(layer["ffn_in"](h + h_attn))
            h = layer["ln"](residual + layer["ffn_out"](h_ffn))
        return self.head(h)

def build_vocab(jsonl_path: Path, max_vocab: int = 5000) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line)
                    for m in item.get("messages", []):
                        for w in m["content"].split():
                            w = w.lower().strip(",.!?\"'();:")
                            if w:
                                counts[w] = counts.get(w, 0) + 1
                except Exception:
                    continue
    vocab = {"<pad>": 0, "<unk>": 1, "<bos>": 2, "<eos>": 3}
    sorted_words = sorted(counts.items(), key=lambda x: -x[1])[:max_vocab]
    for idx, (w, _) in enumerate(sorted_words, start=4):
        vocab[w] = idx
    return vocab

def train(speaker: str = "Eugenio", epochs: int = 5, batch_size: int = 8, lr: float = 1e-3):
    ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    device = select_device()
    print(f"Dispositivo di accelerazione: {device} (Apple Metal M4)")

    dataset_file = DATA_DIR / f"dataset_{speaker}.jsonl"
    if not dataset_file.exists():
        print(f"Dataset non trovato in {dataset_file}", file=sys.stderr)
        return False

    vocab = build_vocab(dataset_file)
    print(f"Dimensione vocabolario estratto per {speaker}: {len(vocab)} token")

    ds = ConversationDataset(dataset_file, vocab)
    if len(ds) == 0:
        print(f"Dataset vuoto per {speaker}", file=sys.stderr)
        return False

    loader = DataLoader(ds, batch_size=batch_size, shuffle=True, collate_fn=collate_batch)
    model = StyleAdapterModel(vocab_size=len(vocab), embed_dim=256, num_layers=4, rank=8).to(device)

    # Allena solo i parametri LoRA
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    total_trainable = sum(p.numel() for p in trainable_params)
    print(f"Parametri addestrabili LoRA: {total_trainable:,}")

    optimizer = torch.optim.AdamW(trainable_params, lr=lr, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss(ignore_index=0)

    print(f"\nInizio fine-tuning LoRA per {speaker} ({epochs} epoche)...")
    history = []
    start_time = time.time()

    model.train()
    for epoch in range(1, epochs + 1):
        epoch_loss = 0.0
        steps = 0
        for batch in loader:
            batch = batch.to(device)
            if batch.size(1) < 2:
                continue
            inputs = batch[:, :-1]
            targets = batch[:, 1:]

            optimizer.zero_grad()
            logits = model(inputs)
            loss = criterion(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            steps += 1

        avg_loss = epoch_loss / max(1, steps)
        elapsed = time.time() - start_time
        perplexity = math.exp(min(avg_loss, 20.0))
        print(f"  Epoca {epoch}/{epochs} - Loss: {avg_loss:.4f} - Perplexity: {perplexity:.2f} ({elapsed:.1f}s)")
        history.append({"epoch": epoch, "loss": avg_loss, "perplexity": perplexity})

    # Salvataggio pesi e vocabolario
    adapter_path = ADAPTERS_DIR / f"{speaker.lower()}_adapter.pt"
    torch.save({
        "speaker": speaker,
        "vocab": vocab,
        "state_dict": {k: v for k, v in model.state_dict().items() if "lora_" in k or "ln" in k},
        "history": history
    }, adapter_path)

    log_path = ADAPTERS_DIR / f"{speaker.lower()}_training_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "speaker": speaker,
            "device": str(device),
            "samples": len(ds),
            "trainable_parameters": total_trainable,
            "training_time_seconds": round(time.time() - start_time, 2),
            "history": history
        }, f, indent=2)

    print(f"\nFine-tuning completato! Adattatore salvato in {adapter_path}")
    print(f"Log metriche salvato in {log_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Addestramento LoRA su Apple Silicon")
    parser.add_argument("--speaker", default="Eugenio", help="Nome del parlante")
    parser.add_argument("--epochs", type=int, default=5, help="Numero di epoche")
    parser.add_argument("--batch-size", type=int, default=8, help="Dimensione batch")
    args = parser.parse_args()
    train(speaker=args.speaker, epochs=args.epochs, batch_size=args.batch_size)
