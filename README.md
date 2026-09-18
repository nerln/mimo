<div align="center">

# mimo

**Turni di conversazione reali in un clone locale che parla come te.**

Fine-tuning locale su Apple Silicon (Metal/MPS) e creazione automatica di modelli persona in Ollama,
alimentati dalla memoria protetta di macOS (tramite *paranco* e *scriba*) e da sessioni di chat online
condivise su GitHub Pages con sincronizzazione Cloudflare.

[![macOS](https://img.shields.io/badge/macOS-14%2B-black?logo=apple&logoColor=white)](#lapp-macos)
[![Metal MPS](https://img.shields.io/badge/Apple%20Silicon-M4%20MPS-orange)](#fine-tuning-locale)
[![Licence](https://img.shields.io/badge/licence-MIT-green)](#licence)
[![Ollama](https://img.shields.io/badge/Ollama-qwen3-blue)](#inferenza-immediata)

</div>

---

```bash
./build.sh                                     # compila Mimo.app
python3 engine/extract_turns.py                # estrae turni da Paranco e Scriba
python3 engine/train_lora.py --speaker Eugenio # allena LoRA su Apple Silicon M4
python3 engine/ollama_adapter.py --speaker Eugenio --test # registra il clone in Ollama
```

## Perché esiste

Se le grandi piattaforme di messaggistica usano le chat per addestrare i propri modelli proprietari,
allora il controllo del proprio stile linguistico deve rimanere su questa macchina.

**Mimo** chiude il cerchio della flotta:
1. **Paranco** detiene il *Full Disk Access* ed estrae le registrazioni vocali da cartelle protette di macOS senza concedere permessi globali all'interprete.
2. **Scriba** scompone l'audio, calcola le impronte vocali con *pyannote*, diarizza la conversazione e mappa ciascun turno all'identità reale del parlante (`who-is-who.md`).
3. **Mimo Engine** estrae le coppie interattive, genera dataset di istruzione formattati e addestra un adattatore LoRA con accelerazione Metal (MPS) sul chip M4.
4. **Ollama Adapter** compila un *Modelfile* calibrato con system prompt persona e turni *few-shot* reali, rendendo il clone accessibile immediatamente via terminale e API locale a zero latenza.
5. **Mimo.app & Web Client** permettono di conversare in locale con il clone e di aprire stanze web condivise (ospitate su `nerln.github.io/mimo` con relay Cloudflare) per arricchire il dataset con nuove conversazioni online.

```
macOS Protected Storage (Voice Memos, Chat)
                │
         [ paranco lift ]
                │
                ▼
         ~/.scriba/inbox
                │
         [ scriba run ] ──► who-is-who.md + turns.json
                │
                ▼
        engine/extract_turns.py
                │
       ┌────────┴─────────────────────────┐
       ▼                                  ▼
engine/train_lora.py (MPS M4)   engine/ollama_adapter.py
  LoRA weights (.pt)              Modelfile (eugenio-clone)
       │                                  │
       ▼                                  ▼
  Mimo.app (macOS SwiftUI) ◄─────── Ollama API (11434)
       ▲
       │ Sincronizzazione turni
       ▼
Cloudflare Worker (mimo-session) ◄──► Web Client (nerln.github.io/mimo)
```

## L'app macOS

Costruita in SwiftUI puro senza progetti Xcode opachi (`build.sh` usa SwiftPM e assembla il bundle firmandolo ad-hoc per girare immediatamente su macOS 14+):

- **Memoria & Paranco**: ispeziona `routes.json`, controlla i file convogliati e visualizza il conteggio parole per parlante rilevato.
- **Fine-Tuning Locale**: selezione della persona da clonare (`Eugenio`, `Alberto`, `Mario`, ecc.), scelta del modello base (`qwen3:4b-instruct-2507-q4_K_M`, `olivera:q4`), epoche e terminale in tempo reale con tracciamento della loss.
- **Chat col Clone**: interfaccia nativa di messaggistica per dialogare con la replica addestrata.
- **Sessioni Online**: gestione delle stanze condivise e sincronizzazione dei messaggi online nel dataset locale.

## Sessioni Web & Cloudflare

Il client web in `web/` consente a chiunque di partecipare a una sessione online dal browser (desktop o mobile). I messaggi vengono sincronizzati attraverso il worker Cloudflare `mimo-session` persistito su KV e possono essere esportati o sincronizzati direttamente nel pool di addestramento di Mimo.

- URL pubblico: `https://nerln.github.io/mimo/`
- Relay Cloudflare: `https://mimo-session.eugenio-nerelli99.workers.dev`

## Licenza

MIT © Eugenio Nerelli.
