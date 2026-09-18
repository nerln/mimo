#!/usr/bin/env python3
"""
extract_turns.py - Estrazione e preparazione dataset conversazionale

Legge i dati trasferiti da Paranco e processati da Scriba in ~/.scriba/jobs,
associa l'identità dei parlanti da who-is-who.md e costruisce dataset
in formato standard Chat/Instruction per il fine-tuning locale.
Supporta anche l'importazione di chat WhatsApp e Telegram.
"""

import os
import sys
import json
import glob
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

HOME = Path.home()
PARANCO_ROUTES = HOME / "Library/Application Support/paranco/routes.json"
SCRIBA_JOBS = HOME / ".scriba/jobs"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"

def load_paranco_info() -> Dict[str, Any]:
    """Ispeziona la configurazione di Paranco per identificare sorgenti e destinazioni."""
    routes = []
    if PARANCO_ROUTES.exists():
        try:
            with open(PARANCO_ROUTES, "r", encoding="utf-8") as f:
                routes = json.load(f)
        except Exception as e:
            print(f"Avviso lettura rotte Paranco: {e}", file=sys.stderr)
    return {
        "routes_file": str(PARANCO_ROUTES),
        "routes_count": len(routes),
        "routes": routes
    }

def parse_who_is_who(who_path: Path) -> Dict[str, str]:
    """Estrae la mappa SPEAKER_XX -> Nome dal file who-is-who.md."""
    mapping = {}
    if not who_path.exists():
        return mapping
    try:
        content = who_path.read_text(encoding="utf-8")
        blocks = re.split(r'##\s+(SPEAKER_\d+)', content)
        for i in range(1, len(blocks), 2):
            spk_id = blocks[i].strip()
            block_body = blocks[i+1]
            m = re.search(r'matches\s+\*\*([^\*]+)\*\*', block_body)
            if m:
                mapping[spk_id] = m.group(1).strip()
    except Exception as e:
        print(f"Errore parsing {who_path}: {e}", file=sys.stderr)
    return mapping

def clean_text(t: str) -> str:
    """Pulisce il testo da artefatti evidenti di trascrizione."""
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def extract_scriba_jobs() -> List[Dict[str, Any]]:
    """Estrae tutti i turni conversazionali dai job di Scriba."""
    all_conversations = []
    if not SCRIBA_JOBS.exists():
        print(f"Cartella scriba non trovata in {SCRIBA_JOBS}", file=sys.stderr)
        return all_conversations

    job_dirs = sorted(SCRIBA_JOBS.glob("*"))
    for j in job_dirs:
        if not j.is_dir():
            continue
        turns_file = j / "turns.json"
        who_file = j / "who-is-who.md"
        if not turns_file.exists():
            continue

        spk_map = parse_who_is_who(who_file) if who_file.exists() else {}
        try:
            with open(turns_file, "r", encoding="utf-8") as f:
                raw_turns = json.load(f)
        except Exception:
            continue

        normalized_turns = []
        for t in raw_turns:
            spk_raw = t.get("speaker") or "UNKNOWN"
            speaker_name = spk_map.get(spk_raw, spk_raw)
            text = clean_text(t.get("text", ""))
            if not text:
                continue
            normalized_turns.append({
                "speaker": speaker_name,
                "raw_speaker": spk_raw,
                "text": text,
                "start": t.get("start", 0),
                "end": t.get("end", 0),
                "confidence": t.get("confidence", 1.0)
            })

        # Collassa turni consecutivi dello stesso interlocutore
        merged_turns = []
        for t in normalized_turns:
            if merged_turns and merged_turns[-1]["speaker"] == t["speaker"]:
                merged_turns[-1]["text"] += " " + t["text"]
                merged_turns[-1]["end"] = t["end"]
            else:
                merged_turns.append(t)

        if len(merged_turns) >= 2:
            all_conversations.append({
                "job_id": j.name,
                "turns": merged_turns
            })

    return all_conversations

def import_whatsapp_chat(filepath: Path) -> List[Dict[str, Any]]:
    """Importa una chat esportata da WhatsApp (.txt)."""
    turns = []
    if not filepath.exists():
        return turns
    
    line_pattern = re.compile(r'^(?:\[?(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–]?\s*)([^:]+):\s*(.*)$')
    
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        current_speaker = None
        current_text = []
        for line in f:
            m = line_pattern.match(line)
            if m:
                if current_speaker and current_text:
                    text_str = clean_text(" ".join(current_text))
                    if text_str and not text_str.startswith("<Media omitted>") and not text_str.startswith("audio omesso"):
                        turns.append({"speaker": current_speaker, "text": text_str})
                current_speaker = m.group(2).strip()
                current_text = [m.group(3).strip()]
            elif current_speaker:
                current_text.append(line.strip())
        if current_speaker and current_text:
            text_str = clean_text(" ".join(current_text))
            if text_str:
                turns.append({"speaker": current_speaker, "text": text_str})
    return turns

def generate_speaker_datasets(conversations: List[Dict[str, Any]], target_speaker: str = "Eugenio") -> List[Dict[str, Any]]:
    """
    Genera campioni di fine-tuning in cui target_speaker risponde agli altri interlocutori.
    Formato: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
    """
    samples = []
    system_prompt = (
        f"Sei {target_speaker}. Rispondi in italiano con il tuo tono naturale, autentico, "
        "diretto e informale, riflettendo il tuo specifico stile di pensiero ed espressione."
    )

    for conv in conversations:
        turns = conv["turns"]
        for i in range(len(turns)):
            curr = turns[i]
            if curr["speaker"] == target_speaker:
                # Cerca il contesto precedente (massimo 3 turni)
                history = []
                start_idx = max(0, i - 3)
                for prev in turns[start_idx:i]:
                    role = "assistant" if prev["speaker"] == target_speaker else "user"
                    prefix = f"[{prev['speaker']}]: " if role == "user" else ""
                    history.append({"role": role, "content": prefix + prev["text"]})

                if not history:
                    history = [{"role": "user", "content": "Dimmi cosa ne pensi."}]

                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history)
                messages.append({"role": "assistant", "content": curr["text"]})
                samples.append({
                    "speaker": target_speaker,
                    "job_id": conv.get("job_id", "external"),
                    "messages": messages
                })
    return samples

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paranco_info = load_paranco_info()
    conversations = extract_scriba_jobs()

    # Controlla eventuali chat esterne caricate in data/imports
    import_dir = OUTPUT_DIR / "imports"
    if import_dir.exists():
        for f in import_dir.glob("*.txt"):
            ext_turns = import_whatsapp_chat(f)
            if ext_turns:
                conversations.append({"job_id": f"whatsapp_{f.stem}", "turns": ext_turns})

    # Calcola statistiche complessive
    stats: Dict[str, Any] = {
        "paranco": paranco_info,
        "total_conversations": len(conversations),
        "speakers": {}
    }

    for conv in conversations:
        for t in conv["turns"]:
            spk = t["speaker"]
            if spk not in stats["speakers"]:
                stats["speakers"][spk] = {"turns": 0, "words": 0, "jobs": set()}
            stats["speakers"][spk]["turns"] += 1
            stats["speakers"][spk]["words"] += len(t["text"].split())
            stats["speakers"][spk]["jobs"].add(conv.get("job_id", ""))

    for spk in stats["speakers"]:
        stats["speakers"][spk]["jobs"] = len(stats["speakers"][spk]["jobs"])

    # Salva i dataset per ciascun parlante rilevante
    prominent_speakers = [s for s, data in stats["speakers"].items() if data["words"] >= 100 and s != "UNKNOWN"]
    if "Eugenio" not in prominent_speakers and "Eugenio" in stats["speakers"]:
        prominent_speakers.append("Eugenio")

    generated_files = {}
    for spk in prominent_speakers:
        samples = generate_speaker_datasets(conversations, target_speaker=spk)
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', spk)
        out_file = OUTPUT_DIR / f"dataset_{clean_name}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        generated_files[spk] = {"samples": len(samples), "file": str(out_file)}

    # Salva summary.json
    summary_path = OUTPUT_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "stats": stats,
            "prominent_speakers": prominent_speakers,
            "generated_datasets": generated_files
        }, f, indent=2, ensure_ascii=False)

    print(f"Estratte {len(conversations)} conversazioni da Paranco/Scriba.")
    print(f"Parlanti principali: {', '.join(prominent_speakers)}")
    for spk, info in generated_files.items():
        print(f" - {spk}: {info['samples']} campioni generati in {info['file']}")

if __name__ == "__main__":
    main()
