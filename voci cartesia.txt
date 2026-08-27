# -*- coding: utf-8 -*-
"""
elenca_voci_cartesia.py
------------------------
Piccola utility indipendente da Jarvis: stampa le voci disponibili nel tuo
account Cartesia (libreria pubblica + eventuali cloni/voci create da te)
insieme al loro Voice ID.

Uso:
    1. Avvia una volta CODICE_SORGENTE.txt (anche se poi lo chiudi) così
       viene creato il file 'cartesia_key.txt' accanto allo script, oppure
       crealo tu a mano e incolla dentro la tua chiave API (inizia con "sk_car_").
    2. pip install requests
    3. python elenca_voci_cartesia.py

Copia il Voice ID che preferisci e incollalo nella costante
CARTESIA_VOICE_ID dentro CODICE_SORGENTE.txt.
"""
import os
import sys

try:
    import requests
except ImportError:
    print("Manca il modulo 'requests'. Installa con: pip install requests")
    sys.exit(1)

NOME_FILE_CHIAVE  = "cartesia_key.txt"
VERSIONE_API      = "2026-03-01"


def carica_chiave():
    if not os.path.exists(NOME_FILE_CHIAVE):
        print(f"Non trovo '{NOME_FILE_CHIAVE}'. Avvia prima Jarvis una volta "
              f"(crea il file automaticamente) oppure crealo a mano con dentro "
              f"la tua API key Cartesia (play.cartesia.ai/keys).")
        sys.exit(1)
    with open(NOME_FILE_CHIAVE, "r", encoding="utf-8") as f:
        chiave = f.read().strip()
    if not chiave or chiave == "INSERISCI_LA_TUA_API_KEY_CARTESIA_QUI":
        print(f"Apri '{NOME_FILE_CHIAVE}' e incolla la tua vera API key Cartesia.")
        sys.exit(1)
    return chiave


def main():
    chiave = carica_chiave()
    resp = requests.get(
        "https://api.cartesia.ai/voices",
        headers={
            "Authorization":    f"Bearer {chiave}",
            "Cartesia-Version": VERSIONE_API,
        },
        params={"limit": 100},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Errore HTTP {resp.status_code}: {resp.text[:300]}")
        print("Nota: se l'endpoint risulta cambiato, controlla la documentazione"
              " aggiornata su docs.cartesia.ai.")
        sys.exit(1)

    corpo = resp.json()
    voci  = corpo.get("data", corpo if isinstance(corpo, list) else [])
    if not voci:
        print("Nessuna voce trovata nel tuo account.")
        return

    print(f"\nTrovate {len(voci)} voci nel tuo account Cartesia:\n")
    print(f"{'NOME':<28} {'LINGUA':<8} VOICE ID")
    print("-" * 70)
    for v in voci:
        nome     = v.get("name", "?")
        lingua   = v.get("language", "?")
        voice_id = v.get("id", "?")
        print(f"{nome:<28} {lingua:<8} {voice_id}")

    print("\nCopia il Voice ID scelto in CARTESIA_VOICE_ID dentro CODICE_SORGENTE.txt.")
    print("Libreria voci consultabile anche su: https://play.cartesia.ai/voices")


if __name__ == "__main__":
    main()