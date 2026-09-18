#!/usr/bin/env python3
"""
ollama_adapter.py - Creazione e gestione modelli persona in Ollama

Crea un modello Ollama dedicato (es. `eugenio-clone`, `alberto-clone`)
configurando Modelfile con system prompt calibrato, parametri di campionamento
ed esempi few-shot estratti direttamente dai turni di parola reali.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"

DEFAULT_BASE_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

PERSONA_PROMPTS = {
    "Eugenio": (
        "Sei Eugenio Nerelli. Rispondi sempre in prima persona con il tuo tono reale: "
        "diretto, pragmatico, tecnico, ironico e disinvolto. Non usare formule servili o da assistente AI "
        "(non dire mai 'certamente', 'sono felice di aiutarti'). Parla come faresti con i tuoi amici o colleghi: "
        "frasi incisive, ritmo naturale, franchezza e precisione quando si parla di codice e architettura."
    ),
    "Alberto": (
        "Sei Alberto Robazza. Rispondi con il tuo stile discorsivo, riflessivo, senza filtri e provocatorio, "
        "portando ipotesi estreme o paradossi con assoluta serietà e disinvoltura. Nessuna censura formale."
    ),
    "Mario": (
        "Sei Mario. Rispondi con il tuo tipico accento e modo di fare: diretto, pragmatico, "
        "interessato agli aspetti pratici e organizzativi del lavoro e delle riunioni."
    )
}

def pick_few_shot_turns(dataset_file: Path, max_pairs: int = 6) -> List[Dict[str, str]]:
    """Seleziona i turni più significativi e puliti per il Modelfile."""
    pairs = []
    if not dataset_file.exists():
        return pairs
    
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                msgs = item.get("messages", [])
                # Trova l'ultimo user e l'ultimo assistant
                user_msg = None
                asst_msg = None
                for m in reversed(msgs):
                    if m["role"] == "assistant" and not asst_msg:
                        asst_msg = m["content"]
                    elif m["role"] == "user" and asst_msg and not user_msg:
                        user_msg = m["content"]
                        break
                if user_msg and asst_msg:
                    # Rimuovi prefisso [Speaker]:
                    if user_msg.startswith("[") and "]: " in user_msg:
                        user_msg = user_msg.split("]: ", 1)[1]
                    # Filtra risposte troppo corte o monosillabi
                    if len(asst_msg.split()) >= 3 and len(user_msg.split()) >= 3:
                        pairs.append({"user": user_msg.strip(), "assistant": asst_msg.strip()})
            except Exception:
                continue
            if len(pairs) >= max_pairs * 2:
                break

    # Seleziona campioni distribuiti
    selected = []
    for i in range(0, len(pairs), 2):
        if len(selected) >= max_pairs:
            break
        selected.append(pairs[i])
    return selected

def build_modelfile(speaker: str, base_model: str, few_shots: List[Dict[str, str]]) -> str:
    """Genera la sintassi del Modelfile per Ollama."""
    system_prompt = PERSONA_PROMPTS.get(speaker, (
        f"Sei {speaker}. Rispondi sempre incarnando questa persona in tono, vocabolario e modo di pensare. "
        "Nessun formalismo inutile o tono da chatbot aziendale."
    ))

    lines = [
        f"FROM {base_model}",
        "",
        "# Parametri di generazione per massimizzare naturalezza e aderenza stilistica",
        "PARAMETER temperature 0.75",
        "PARAMETER top_p 0.9",
        "PARAMETER repeat_penalty 1.15",
        "",
        f'SYSTEM """{system_prompt}"""',
        ""
    ]

    for p in few_shots:
        clean_user = p["user"].replace('"', '\\"')
        clean_asst = p["assistant"].replace('"', '\\"')
        lines.append(f'MESSAGE user """{clean_user}"""')
        lines.append(f'MESSAGE assistant """{clean_asst}"""')

    lines.append("")
    return "\n".join(lines)

def register_model_in_ollama(model_name: str, modelfile_path: Path) -> bool:
    """Esegue `ollama create <model_name> -f <modelfile_path>`."""
    cmd = ["ollama", "create", model_name, "-f", str(modelfile_path)]
    print(f"Esecuzione: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Modello {model_name} creato con successo in Ollama.")
        return True
    else:
        print(f"Errore creazione modello {model_name}: {res.stderr}", file=sys.stderr)
        return False

def test_inference(model_name: str, prompt: str = "Come va? Di cosa ti stai occupando oggi?") -> str:
    """Esegue una query di prova al modello appena creato."""
    cmd = ["ollama", "run", model_name, prompt]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.stdout.strip()
    except Exception as e:
        return f"Errore inferenza: {e}"

def main():
    parser = argparse.ArgumentParser(description="Adattatore Ollama per Mimo")
    parser.add_argument("--speaker", default="Eugenio", help="Nome del parlante da clonare")
    parser.add_argument("--base", default=DEFAULT_BASE_MODEL, help="Modello base presente in Ollama")
    parser.add_argument("--name", default=None, help="Nome del modello in Ollama")
    parser.add_argument("--test", action="store_true", help="Esegui un'inferenza di prova dopo la creazione")
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    speaker = args.speaker
    clone_name = args.name or f"{speaker.lower()}-clone"
    dataset_file = DATA_DIR / f"dataset_{speaker}.jsonl"

    if not dataset_file.exists():
        # Cerca file simile
        matches = list(DATA_DIR.glob(f"dataset_{speaker}*.jsonl"))
        if matches:
            dataset_file = matches[0]
        else:
            print(f"Dataset non trovato per {speaker} in {dataset_file}", file=sys.stderr)
            sys.exit(1)

    few_shots = pick_few_shot_turns(dataset_file)
    print(f"Selezionati {len(few_shots)} turni few-shot per {speaker}.")

    modelfile_content = build_modelfile(speaker, args.base, few_shots)
    modelfile_path = MODELS_DIR / f"Modelfile.{clone_name}"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"Modelfile scritto in {modelfile_path}")

    ok = register_model_in_ollama(clone_name, modelfile_path)
    if ok and args.test:
        print(f"\n--- Test di risposta con {clone_name} ---")
        reply = test_inference(clone_name, "Spiegami cosa pensi del fare fine-tuning su WhatsApp.")
        print(f"Risposta clone:\n{reply}\n--------------------------------------")

if __name__ == "__main__":
    main()
