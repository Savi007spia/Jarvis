# -*- coding: utf-8 -*-
"""
elenca_voci_elevenlabs.py
--------------------------
Piccola utility indipendente da Jarvis: stampa tutte le voci disponibili
nel tuo account ElevenLabs (voci premade della libreria, voci create con
Voice Design, e tuoi eventuali cloni vocali) insieme al loro Voice ID.

Uso:
    1. Avvia una volta CODICE_SORGENTE.txt (anche se poi lo chiudi) così
       viene creato il file 'elevenlabs_key.txt' accanto allo script,
       oppure crealo tu a mano e incolla dentro la tua chiave API.
    2. pip install requests
    3. python elenca_voci_elevenlabs.py

Copia il Voice ID che preferisci e incollalo nella costante
ELEVENLABS_VOICE_ID dentro CODICE_SORGENTE.txt.
"""
import os
import sys

try:
    import requests
except ImportError:
    print("Manca il modulo 'requests'. Installa con: pip install requests")
    sys.exit(1)

NOME_FILE_CHIAVE = "elevenlabs_key.txt"


def carica_chiave():
    if not os.path.exists(NOME_FILE_CHIAVE):
        print(f"Non trovo '{NOME_FILE_CHIAVE}'. Avvia prima Jarvis una volta "
              f"(crea il file automaticamente) oppure crealo a mano con dentro "
              f"la tua API key ElevenLabs.")
        sys.exit(1)
    with open(NOME_FILE_CHIAVE, "r", encoding="utf-8") as f:
        chiave = f.read().strip()
    if not chiave or chiave == "INSERISCI_LA_TUA_API_KEY_ELEVENLABS_QUI":
        print(f"Apri '{NOME_FILE_CHIAVE}' e incolla la tua vera API key ElevenLabs.")
        sys.exit(1)
    return chiave


def main():
    chiave = carica_chiave()
    resp = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": chiave},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Errore HTTP {resp.status_code}: {resp.text[:300]}")
        print("Nota: se l'endpoint risulta cambiato, controlla la documentazione"
              " aggiornata su elevenlabs.io/docs.")
        sys.exit(1)

    voci = resp.json().get("voices", [])
    if not voci:
        print("Nessuna voce trovata nel tuo account.")
        return

    print(f"\nTrovate {len(voci)} voci nel tuo account ElevenLabs:\n")
    print(f"{'NOME':<25} {'CATEGORIA':<15} VOICE ID")
    print("-" * 70)
    for v in voci:
        nome = v.get("name", "?")
        categoria = v.get("category", "?")   # premade | cloned | generated | professional
        voice_id = v.get("voice_id", "?")
        print(f"{nome:<25} {categoria:<15} {voice_id}")

    print("\nCopia il Voice ID scelto in ELEVENLABS_VOICE_ID dentro CODICE_SORGENTE.txt.")


if __name__ == "__main__":
    main()