#!/usr/bin/env python3
"""
whatsapp_parser.py - Parser avanzato per esportazioni chat di WhatsApp (.txt e .zip)

Supporta:
- Formato iOS: [DD/MM/YY, HH:MM:SS] Nome: Messaggio (con o senza indicatori Unicode \u200e e formato 12h/24h)
- Formato Android: DD/MM/YYYY, HH:MM - Nome: Messaggio (con o senza formato 12h AM/PM)
- File .zip contenenti _chat.txt o file di testo
- Messaggi su più righe
- Filtraggio automatico di messaggi di sistema e notifiche di allegati/media
"""

import os
import sys
import re
import json
import zipfile
import tempfile
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Caratteri invisibili e di direzione inseriti da WhatsApp iOS
UNICODE_TRASH = [
    "\u200e", "\u200f", "\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\ufeff", "\u00a0"
]

# Pattern per l'inizio di un nuovo messaggio
# iOS: [12/03/24, 15:43:21] Nome: ... oppure [12/3/24, 3:43:21 PM] Nome: ...
IOS_PATTERN = re.compile(
    r'^\[(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s+([^:]+?):\s+(.*)$'
)

# Android: 12/03/2024, 15:43 - Nome: ... oppure 12/3/24, 3:43 PM - Nome: ...
ANDROID_PATTERN = re.compile(
    r'^(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*[-–]\s+([^:]+?):\s+(.*)$'
)

# Messaggi di sistema da scartare
SYSTEM_PATTERNS = [
    r'crittografati end-to-end',
    r'end-to-end encrypted',
    r'hai cambiato l\'icona',
    r'ha cambiato l\'icona',
    r'ha cambiato l\'oggetto',
    r'i messaggi effimeri',
    r'disappearing messages',
    r'codice di sicurezza.*cambiato',
    r'security code changed',
    r'ha abbandonato il gruppo',
    r'ha aggiunto',
    r'left the group',
    r'added you'
]

# Indicatori di allegati/media omessi da scartare o normalizzare
MEDIA_PATTERNS = [
    r'^<allegato:.*omesso>$',
    r'^<allegati:.*omessi>$',
    r'^<media omitted>$',
    r'^<file multimediale omesso>$',
    r'^<audio omesso>$',
    r'^<video omesso>$',
    r'^<immagine omessa>$',
    r'^<sticker omesso>$',
    r'^image omitted$',
    r'^audio omitted$',
    r'^video omitted$',
    r'^sticker omitted$',
    r'^document omitted$'
]

def clean_line(line: str) -> str:
    """Rimuove caratteri invisibili WhatsApp e normalizza spazi."""
    for ch in UNICODE_TRASH:
        line = line.replace(ch, "")
    return line.strip()

def is_system_message(text: str) -> bool:
    lower = text.lower()
    for p in SYSTEM_PATTERNS:
        if re.search(p, lower):
            return True
    return False

def is_media_notice(text: str) -> bool:
    lower = text.lower().strip()
    for p in MEDIA_PATTERNS:
        if re.match(p, lower):
            return True
    return False

def parse_whatsapp_text(content: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Estrae i turni e le statistiche dei partecipanti dal testo della chat."""
    lines = content.splitlines()
    turns: List[Dict[str, Any]] = []
    stats: Dict[str, int] = {}

    current_turn: Optional[Dict[str, Any]] = None

    for raw_line in lines:
        line = clean_line(raw_line)
        if not line:
            continue

        match = IOS_PATTERN.match(line) or ANDROID_PATTERN.match(line)
        if match:
            # Salva il messaggio precedente
            if current_turn:
                turns.append(current_turn)
                current_turn = None

            timestamp_str = match.group(1).strip()
            author = match.group(2).strip()
            message_text = match.group(3).strip()

            # Controlla se è un messaggio di sistema WhatsApp (spesso non ha i due punti ma il regex potrebbe catturarlo se contiene ":")
            if is_system_message(message_text) or is_system_message(author):
                continue

            if is_media_notice(message_text):
                continue

            stats[author] = stats.get(author, 0) + 1
            current_turn = {
                "timestamp": timestamp_str,
                "speaker": author,
                "text": message_text
            }
        else:
            # Continuazione del messaggio su più righe
            if current_turn:
                current_turn["text"] += "\n" + line

    if current_turn:
        turns.append(current_turn)

    # Raggruppa turni consecutivi dello stesso parlante
    merged_turns: List[Dict[str, Any]] = []
    for t in turns:
        if not t["text"].strip():
            continue
        if merged_turns and merged_turns[-1]["speaker"] == t["speaker"]:
            merged_turns[-1]["text"] += " " + t["text"]
        else:
            merged_turns.append(t)

    return merged_turns, stats

def parse_whatsapp_file(filepath: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Apre e analizza un file di chat WhatsApp (.txt oppure .zip)."""
    if not filepath.exists():
        raise FileNotFoundError(f"File non trovato: {filepath}")

    if filepath.suffix.lower() == ".zip":
        with zipfile.ZipFile(filepath, 'r') as z:
            txt_files = [n for n in z.namelist() if n.endswith(".txt") and not n.startswith("__MACOSX")]
            if not txt_files:
                raise ValueError("Nessun file .txt trovato all'interno dell'archivio .zip di WhatsApp")
            # Prediligi _chat.txt se presente
            target = "_chat.txt" if "_chat.txt" in txt_files else txt_files[0]
            with z.open(target) as f:
                content = f.read().decode("utf-8", errors="replace")
                return parse_whatsapp_text(content)
    else:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            return parse_whatsapp_text(content)

def convert_to_fine_tuning(turns: List[Dict[str, Any]], target_speaker: str) -> List[Dict[str, Any]]:
    """Converte i turni estratti da WhatsApp in campioni di addestramento chat/instruction."""
    samples = []
    system_prompt = (
        f"Sei {target_speaker}. Rispondi in italiano nello stile esatto dei tuoi messaggi WhatsApp: "
        "naturale, colloquiale, sintetico o prolisso a seconda del contesto, autentico e senza formalismi AI."
    )

    for i in range(len(turns)):
        curr = turns[i]
        if curr["speaker"].lower() == target_speaker.lower():
            history = []
            start_idx = max(0, i - 3)
            for prev in turns[start_idx:i]:
                role = "assistant" if prev["speaker"].lower() == target_speaker.lower() else "user"
                prefix = f"[{prev['speaker']}]: " if role == "user" else ""
                history.append({"role": role, "content": prefix + prev["text"]})

            if not history:
                history = [{"role": "user", "content": "Come va?"}]

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "assistant", "content": curr["text"]})

            samples.append({
                "speaker": target_speaker,
                "source": "whatsapp_export",
                "messages": messages
            })
    return samples

def main():
    parser = argparse.ArgumentParser(description="Parser di esportazioni chat WhatsApp (.txt / .zip)")
    parser.add_argument("file", type=Path, help="Percorso del file .txt o .zip esportato da WhatsApp")
    parser.add_argument("--speaker", default=None, help="Nome del parlante da clonare (opzionale)")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data", help="Cartella di destinazione")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    turns, stats = parse_whatsapp_file(args.file)

    print(f"File analizzato: {args.file.name}")
    print(f"Turni totali estratti: {len(turns)}")
    print("Partecipanti rilevati:")
    for spk, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  - {spk}: {count} messaggi")

    target = args.speaker
    if not target:
        # Suggerisci il parlante più frequente
        target = max(stats.items(), key=lambda x: x[1])[0]
        print(f"\nNessun parlante specificato. Impostato su '{target}' (più attivo).")

    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', target)
    samples = convert_to_fine_tuning(turns, target)
    out_file = args.out_dir / f"dataset_whatsapp_{clean_name}.jsonl"

    with open(out_file, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"Generati {len(samples)} campioni di fine-tuning in: {out_file}")

if __name__ == "__main__":
    main()
