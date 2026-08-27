import os
import sys
import math
import time
import json
import base64
import socket
import io
import queue
import webbrowser
import threading
import subprocess
import urllib.parse
import ctypes
import re
import platform
from datetime import datetime

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False
    print("[SISTEMA] psutil non installato — diagnostica PC disabilitata. Installa con: pip install psutil")

try:
    import tkinter as tk
    from tkinter import messagebox
    import speech_recognition as sr
    import pyttsx3
    import pyautogui
    import pywhatkit
    from groq import Groq
    from flask import Flask, request, jsonify, render_template_string
except ImportError as e:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Errore Critico - J.A.R.V.I.S.",
            f"Impossibile avviare l'assistente per via di una dipendenza mancante:\n\n{e}\n\n"
            "Installa i moduli mancanti con:\n"
            "pip install speechrecognition pyttsx3 pyautogui pywhatkit groq pyaudio flask"
        )
    except Exception:
        print(f"[ERRORE CRITICO]: Librerie mancanti: {e}")
    input("\nPremi INVIO per uscire...")
    sys.exit(1)

try:
    import requests as _http
except ImportError:
    _http = None

# Moduli Windows built-in (non richiedono installazione)
try:
    import winsound as _winsound
    _WINSOUND_OK = True
except ImportError:
    _WINSOUND_OK = False

try:
    import winreg as _winreg
    _WINREG_OK = True
except ImportError:
    _WINREG_OK = False

# Hotkey globale (richiede: pip install keyboard)
try:
    import keyboard as _keyboard_lib
    _KEYBOARD_OK = True
except ImportError:
    _KEYBOARD_OK = False
    print("[AVVISO] Modulo 'keyboard' non trovato. Hotkey ALT+T disabilitata. Installa con: pip install keyboard")

# OpenCV per webcam (richiede: pip install opencv-python)
try:
    import cv2 as _cv2
    _CV2_OK = True
except ImportError:
    _cv2  = None
    _CV2_OK = False
    print("[AVVISO] Modulo 'cv2' non trovato. Webcam disabilitata. Installa con: pip install opencv-python")

# ---------------------------------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------------------------------

def carica_api_key():
    nome_file = "groq_key.txt"
    if not os.path.exists(nome_file):
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write("INSERISCI_LA_TUA_API_KEY_GROQ_QUI")
        print(f"\n[SISTEMA] Creato '{nome_file}'. Aprilo, incolla la tua chiave Groq e riavvia.\n")
        return "INSERISCI_LA_TUA_API_KEY_GROQ_QUI"
    with open(nome_file, "r", encoding="utf-8") as f:
        return f.read().strip()


def carica_cartesia_key():
    nome_file = "cartesia_key.txt"
    if not os.path.exists(nome_file):
        with open(nome_file, "w", encoding="utf-8") as f:
            f.write("INSERISCI_LA_TUA_API_KEY_CARTESIA_QUI")
        print(f"\n[SISTEMA] Creato '{nome_file}'. Aprilo, incolla la tua chiave Cartesia e riavvia.\n")
        return "INSERISCI_LA_TUA_API_KEY_CARTESIA_QUI"
    with open(nome_file, "r", encoding="utf-8") as f:
        return f.read().strip()


GROQ_API_KEY        = carica_api_key()
MODELLO_AI          = "openai/gpt-oss-20b"          # rapido per comandi semplici — llama-3.1-8b-instant dismesso da Groq il 16/08/2026
MODELLO_AI_AVANZATO = "openai/gpt-oss-120b"         # potente per codice e domande complesse — llama-3.3-70b-versatile dismesso il 16/08/2026
MODELLO_VISION      = "qwen/qwen3.6-27b"   # visione: webcam & desktop — llama-4-scout dismesso da Groq il 17/07/2026
WAKE_WORD    = "jarvis"
PORTA_SERVER = 5001

# ── Cartesia (voce TTS premium, opzionale — vedi sezione MOTORE VOCALE) ───
CARTESIA_API_KEY  = carica_cartesia_key()
# ID della voce da usare: scegline una dalla Voice Library di Cartesia
# (play.cartesia.ai/voices) oppure un tuo clone fatto con il tuo consenso.
# Copia il "Voice ID" (o lancia elenca_voci_cartesia.py) e incollalo qui.
CARTESIA_VOICE_ID = "c1730050-979e-42d5-8124-e0ce6b0ef47e"
CARTESIA_MODEL_ID = "sonic-3.5"      # modello Sonic più recente, latenza bassissima
CARTESIA_VERSION  = "2026-03-01"     # versione API Cartesia (header Cartesia-Version)
CARTESIA_VOLUME   = 2.0              # ATTENZIONE: l'API accetta solo 0.5-2.0, 2.0 è il massimo assoluto

# ── Chiamate telefoniche via ADB (telefono Android collegato) ─────────────
def carica_contatti():
    nome_file = "contatti.json"
    if not os.path.exists(nome_file):
        esempio = {"esempio": "+39 333 1234567"}
        with open(nome_file, "w", encoding="utf-8") as f:
            json.dump(esempio, f, ensure_ascii=False, indent=2)
        print(f"\n[SISTEMA] Creato '{nome_file}' con un contatto di esempio. "
              f"Aggiungi i tuoi contatti (nome: numero) e riavvia.\n")
        return {}
    try:
        with open(nome_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as _e:
        print(f"[SISTEMA] Errore lettura contatti.json: {_e}")
        return {}

CONTATTI = carica_contatti()

# ── Salvataggio automatico del codice generato ─────────────────────────────
CARTELLA_CODICI = r"C:\Users\utente\Desktop\JARVIS\CODICI"

# ── Salvataggio automatico dei modelli 3D generati ─────────────────────────
CARTELLA_MODELLI_3D = r"C:\Users\utente\Desktop\JARVIS\MODELLI_3D"

# ── Promemoria persistenti (Task Scheduler di Windows) ─────────────────────
CARTELLA_PROMEMORIA = r"C:\Users\utente\Desktop\JARVIS\PROMEMORIA"

# ── "Modalità lavoro": cartelle di progetto da aprire (aggiungi i tuoi percorsi) ──
CARTELLE_LAVORO = [
    # r"C:\Users\utente\Desktop\NomeProgetto",
]

# Parole chiave che indicano domande tecniche/complesse → usa modello avanzato
_PAROLE_TECNICHE = {
    # programmazione
    "python","codice","script","programma","c++","html","css","javascript","js","java",
    "php","sql","database","funzione","classe","metodo","algoritmo","loop","ciclo",
    "array","lista","dizionario","variabile","debug","errore","bug","libreria","modulo",
    "api","json","xml","regex","git","dockerfile","bash","powershell","compilare",
    "eseguire","sintassi","import","return","print","def ","int ","void ","public ",
    # domande generali complesse
    "spiega","cos'è","cosa è","come funziona","perché","differenza tra","confronta",
    "vantaggi","svantaggi","analizza","descrivimi","dimmi tutto su","storia di",
    "teoria","principio","legge di","formula","calcola","risolvi","matematica",
    "fisica","chimica","biologia","medicina","economia","filosofia","psicologia",
    # auto-modifica
    "modifica il tuo codice","aggiorna jarvis","correggi il tuo","aggiungi al tuo",
    "scrivi nel sorgente","modifica sorgente",
}

# Memoria persistente su disco (jarvis_memoria.json accanto allo script)
_DIR_SCRIPT      = os.path.dirname(os.path.abspath(__file__))
MEMORIA_FILE     = os.path.join(_DIR_SCRIPT, "jarvis_memoria.json")
_3D_SESSIONI_FILE = os.path.join(_DIR_SCRIPT, "jarvis_3d_sessioni.json")
memoria_estesa: dict = {}

def _carica_memoria_estesa():
    global memoria_estesa
    try:
        if os.path.exists(MEMORIA_FILE):
            with open(MEMORIA_FILE, 'r', encoding='utf-8') as _f:
                memoria_estesa = json.load(_f)
            print(f"[MEMORIA] Caricate {len(memoria_estesa)} voci.")
    except Exception as _e:
        print(f"[MEMORIA] Errore caricamento: {_e}")

def _salva_memoria_estesa():
    try:
        with open(MEMORIA_FILE, 'w', encoding='utf-8') as _f:
            json.dump(memoria_estesa, _f, ensure_ascii=False, indent=2)
    except Exception as _e:
        print(f"[MEMORIA] Errore salvataggio: {_e}")

_carica_memoria_estesa()

# ---------------------------------------------------------------------------
# APPRENDIMENTO AUTOMATICO CONTINUO
# ---------------------------------------------------------------------------

# Categorie di memoria usate dall'estrattore automatico
_CATEGORIE_MEMORIA = {
    "preferenza_utente":  "Preferenze, gusti, abitudini dell'utente",
    "progetto_attivo":    "Progetti su cui sta lavorando l'utente",
    "fatto_tecnico":      "Informazione tecnica appresa durante la conversazione",
    "dato_personale":     "Info sull'utente: nome, lavoro, interessi, ecc.",
    "errore_risolto":     "Bug, errori, problemi risolti con la soluzione adottata",
    "decisione":          "Scelte fatte dall'utente (linguaggio, framework, approccio, ecc.)",
    "contesto_sessione":  "Informazioni sul contesto attuale della sessione",
}

_apprendimento_abilitato = True   # può essere disattivato a runtime


def _estrai_memorie_async(domanda: str, risposta: str):
    """
    Analizza la coppia domanda→risposta in background e salva i fatti
    rilevanti in memoria_estesa senza bloccare il flusso principale.
    Usa il modello veloce per minimizzare latenza e costi.
    """
    if not client or not _apprendimento_abilitato:
        return
    # Salta conversazioni banali / troppo brevi
    if len(domanda.strip()) < 10 or len(risposta.strip()) < 15:
        return

    def _worker():
        prompt = (
            "Analizza questa coppia domanda→risposta di un assistente AI e decidi "
            "se contiene informazioni utili da memorizzare per conversazioni future.\n\n"
            f"DOMANDA: {domanda[:600]}\n"
            f"RISPOSTA: {risposta[:800]}\n\n"
            "Rispondi SOLO con JSON (nessun testo extra), uno di questi due formati:\n"
            '{"vale": false}\n'
            'oppure:\n'
            '{"vale": true, "categoria": "<una di: preferenza_utente|progetto_attivo|fatto_tecnico|'
            'dato_personale|errore_risolto|decisione|contesto_sessione>", '
            '"chiave": "<3-6 parole slug senza spazi, es: linguaggio_preferito_python>", '
            '"fatto": "<il fatto specifico da ricordare, max 120 caratteri>"}'
        )
        try:
            raw = client.chat.completions.create(
                model=MODELLO_AI,          # modello veloce
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=120
            ).choices[0].message.content.strip()

            # Pulizia backtick residui
            if "```" in raw:
                raw = re.sub(r'```[a-z]*\n?', '', raw).strip().rstrip("```").strip()

            dati = json.loads(raw)
            if not dati.get("vale"):
                return

            chiave    = str(dati.get("chiave", f"auto_{int(time.time())}")).strip()
            fatto     = str(dati.get("fatto", "")).strip()
            categoria = str(dati.get("categoria", "fatto_tecnico")).strip()

            if not fatto or len(fatto) < 5:
                return

            memoria_estesa[chiave] = {
                "contenuto":  fatto,
                "timestamp":  time.time(),
                "fonte":      "conversazione_automatica",
                "categoria":  categoria,
            }
            _salva_memoria_estesa()
            print(f"[MEMORIA AUTO] ✓ [{categoria}] {chiave}: {fatto[:60]}")

        except Exception as ex:
            pass   # silenzioso: l'apprendimento non deve mai bloccare nulla

    threading.Thread(target=_worker, daemon=True, name="MemoriaAuto").start()


def _normalizza_voce_memoria(chiave, voce):
    """
    Converte una voce di memoria nel formato dizionario nuovo,
    anche se è stata salvata come semplice stringa (formato vecchio).
    """
    if isinstance(voce, dict):
        return voce
    # Formato vecchio: stringa semplice
    return {
        "contenuto":  str(voce),
        "timestamp":  0.0,
        "fonte":      "legacy",
        "categoria":  "fatto_tecnico",
    }


def _recupera_memorie_rilevanti(domanda: str, n: int = 6) -> str:
    """
    Recupera le N voci di memoria_estesa più pertinenti alla domanda corrente.
    Restituisce una stringa formattata da iniettare nel contesto di sistema.
    Gestisce sia il formato vecchio (stringa) che il nuovo (dizionario).
    """
    try:
        if not memoria_estesa:
            return ""

        domanda_lower = domanda.lower()
        parole_chiave = set(re.findall(r'\b\w{4,}\b', domanda_lower))

        scored = []
        for chiave, voce_raw in memoria_estesa.items():
            try:
                voce      = _normalizza_voce_memoria(chiave, voce_raw)
                contenuto = str(voce.get("contenuto", "")).lower()
                score     = sum(1 for p in parole_chiave if p in chiave.lower() or p in contenuto)
                age_days  = (time.time() - voce.get("timestamp", 0)) / 86400
                score    += max(0, 3 - age_days * 0.1)
                if voce.get("categoria") in ("progetto_attivo", "preferenza_utente", "dato_personale"):
                    score += 1
                scored.append((score, chiave, voce))
            except Exception:
                continue   # salta voci malformate senza bloccare tutto

        if not scored:
            return ""

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n]

        if not any(s > 0 for s, _, _ in top):
            top = sorted(scored, key=lambda x: x[2].get("timestamp", 0), reverse=True)[:3]

        righe = []
        for _, chiave, voce in top:
            cat  = voce.get("categoria", "")
            cont = voce.get("contenuto", "")
            if cont:
                righe.append(f"• [{cat}] {cont}")

        if not righe:
            return ""
        return "=== MEMORIE RILEVANTI (usa queste per personalizzare la risposta) ===\n" + "\n".join(righe)

    except Exception as ex:
        print(f"[MEMORIA] Errore recupero memorie: {ex}")
        return ""   # mai crashare per colpa della memoria


def abilita_apprendimento(stato: bool, hud=None):
    global _apprendimento_abilitato
    _apprendimento_abilitato = stato
    msg = "Apprendimento automatico attivato, Signore." if stato else "Apprendimento automatico disattivato, Signore."
    parla(msg, hud)


def mostra_profilo_utente(hud=None):
    """Mostra nel visore olografico tutto ciò che Jarvis ha imparato sull'utente."""
    if not memoria_estesa:
        parla("Non ho ancora memorizzato informazioni, Signore.", hud); return

    per_categoria = {}
    for chiave, voce in memoria_estesa.items():
        cat  = voce.get("categoria", "altro")
        cont = voce.get("contenuto", "")
        per_categoria.setdefault(cat, []).append(cont)

    riassunto = f"Conosco {len(memoria_estesa)} informazioni su di lei, Signore."
    dettagli  = ""
    for cat, voci in per_categoria.items():
        dettagli += f"[{cat.upper()}]\n" + "\n".join(f"  • {v[:80]}" for v in voci[:4]) + "\n"

    crea_visore_olografico("Profilo Utente J.A.R.V.I.S.", riassunto, dettagli.strip())
    parla(riassunto, hud)


PROGRAMMI = {
    "spotify":               "spotify:",
    "blocco note":           "notepad.exe",
    "chrome":                "chrome.exe",
    "google chrome":         "chrome.exe",
    "firefox":               "firefox.exe",
    "calcolatrice":          "calc.exe",
    "esplora risorse":       "explorer.exe",
    "esplora file":          "explorer.exe",
    "pannello di controllo": "control.exe",
    "task manager":          "taskmgr.exe",
    "paint":                 "mspaint.exe",
    "word":                  "winword.exe",
    "excel":                 "excel.exe",
    "powerpoint":            "powerpnt.exe",
    "discord":               "discord.exe",
    "telegram":              "telegram.exe",
    "whatsapp":              "whatsapp.exe",
    "visual studio code":    "code",
    "vscode":                "code",
    "browser":               "https://www.google.com",
    "youtube":               "https://www.youtube.com",
    "gmail":                 "https://mail.google.com",
    "github":                "https://www.github.com",
}

# ---------------------------------------------------------------------------
# STATO GLOBALE CONDIVISO TRA THREAD
# ---------------------------------------------------------------------------

hud_globale = None
_azione_in_sospeso = {"tipo": None, "dati": None}

# Ultimo testo pronunciato / stato
ultimo_log = {"risposta": "Sistema in attesa, Signore.", "stato": "BACKGROUND"}

# Ultimi dati strutturati di ricerca (riempito da esegui_comando)
ultimo_dati_ricerca: dict = {}

# Ultimo screenshot in base64 (riempito da cattura_screenshot)
ultimo_screenshot: dict = {"immagine": None}

# URL da aprire sul telefono (riempito da esegui_comando quando sorgente="remoto")
ultimo_redirect: dict = {"url": None}

# ---------------------------------------------------------------------------
# RILEVAMENTO IP
# ---------------------------------------------------------------------------

def ottieni_ip_accesso():
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            ip = info[4][0]
            if ip.startswith("100.") and not ip.startswith("100.64."):
                return ip, True
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip, False
    except Exception:
        return "127.0.0.1", False

# ---------------------------------------------------------------------------
# MOTORE VOCALE — Cartesia (voce premium) -> Edge TTS (Microsoft Neural) -> pyttsx3
# ---------------------------------------------------------------------------

# ── Cartesia (priorità massima se chiave e voice_id sono configurati) ─────
_CARTESIA_CONFIGURATA = (
    bool(_http)
    and CARTESIA_API_KEY not in ("", "INSERISCI_LA_TUA_API_KEY_CARTESIA_QUI")
    and CARTESIA_VOICE_ID not in ("", "IL_TUO_VOICE_ID_QUI")
)
_CARTESIA_OK = _CARTESIA_CONFIGURATA   # disattivabile a runtime con "cambia voce normale"

if _CARTESIA_CONFIGURATA:
    print("[VOCE] Cartesia disponibile — userò questa voce come priorità.")
elif not _http:
    print("[VOCE] Modulo 'requests' non trovato — Cartesia disabilitato. Installa con: pip install requests")
else:
    print("[VOCE] Cartesia non configurato (cartesia_key.txt / CARTESIA_VOICE_ID mancanti). Uso Edge TTS.")

# ── Voci disponibili Edge TTS ─────────────────────────────────────────────
VOCI_EDGE = {
    "diego":    "it-IT-DiegoNeural",    # italiano maschio — default (simile Jarvis IT)
    "giuseppe": "it-IT-GiuseppeNeural", # italiano maschio alternativo
    "elsa":     "it-IT-ElsaNeural",     # italiano femmina
    "en_guy":   "en-US-GuyNeural",      # inglese maschio
}
_VOCE_EDGE_CORRENTE = "it-IT-DiegoNeural"
_VELOCITA_EDGE      = "+10%"   # +0% naturale, +10% leggermente più veloce
_EDGE_TTS_OK        = False

try:
    import edge_tts as _edge_tts_mod
    _EDGE_TTS_OK = True
    print("[VOCE] Edge TTS (Microsoft Neural) disponibile.")
except ImportError:
    print("[VOCE] edge-tts non installato — uso pyttsx3. Installa con: pip install edge-tts")

# ── Fallback pyttsx3 ───────────────────────────────────────────────────────
try:
    engine = pyttsx3.init()
    _voci_sys = engine.getProperty('voices')
    if _voci_sys:
        engine.setProperty('voice', _voci_sys[0].id)
    engine.setProperty('rate', 170)
except Exception as _e:
    class FallbackVocale:
        def say(self, t): pass
        def runAndWait(self): pass
        def setProperty(self, p, v): pass
        def getProperty(self, p): return []
    engine = FallbackVocale()
    print(f"[AVVISO] pyttsx3 non disponibile. Audio disattivato.")


def _riproduci_mp3(path_mp3: str):
    """
    Riproduce un file .mp3 in modo SINCRONO.
    Prova tre metodi in sequenza: playsound → pygame → PowerShell WMPlayer.
    """
    # Metodo 1: playsound (pip install playsound==1.2.2)
    try:
        import playsound as _ps
        _ps.playsound(path_mp3, block=True)
        return
    except Exception:
        pass
    # Metodo 2: pygame
    try:
        import pygame as _pg
        if not _pg.mixer.get_init():
            _pg.mixer.init()
        _pg.mixer.music.load(path_mp3)
        _pg.mixer.music.play()
        while _pg.mixer.music.get_busy():
            time.sleep(0.05)
        _pg.mixer.music.unload()
        return
    except Exception:
        pass
    # Metodo 3: PowerShell WMPlayer (sempre disponibile su Windows)
    try:
        safe = path_mp3.replace("\\", "/")
        ps_script = (
            f'Add-Type -AssemblyName presentationCore; '
            f'$m=[System.Windows.Media.MediaPlayer]::new(); '
            f'$m.Open([System.Uri]::new("{safe}")); $m.Play(); '
            f'Start-Sleep -m 600; '
            f'while($m.NaturalDuration.HasTimeSpan -eq $false){{Start-Sleep -m 50}}; '
            f'$d=[int]$m.NaturalDuration.TimeSpan.TotalMilliseconds; '
            f'if($d -gt 600){{Start-Sleep -m ($d-500)}}; $m.Close()'
        )
        subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-c', ps_script], timeout=90)
        return
    except Exception as _ex:
        print(f"[VOCE] Tutti i metodi di riproduzione falliti: {_ex}")


def _parla_cartesia_sync(testo: str):
    """Genera audio con Cartesia (voce CARTESIA_VOICE_ID) e lo riproduce in modo sincrono."""
    import tempfile, os as _os

    url = "https://api.cartesia.ai/tts/bytes"
    headers = {
        "Authorization":    f"Bearer {CARTESIA_API_KEY}",
        "Cartesia-Version": CARTESIA_VERSION,
        "Content-Type":     "application/json",
    }
    corpo = {
        "model_id":   CARTESIA_MODEL_ID,
        "transcript": testo,
        "voice":      {"mode": "id", "id": CARTESIA_VOICE_ID},
        "language":   "it",
        "output_format": {
            "container":   "mp3",
            "sample_rate": 44100,
            "bit_rate":    128000,
        },
        "generation_config": {"volume": CARTESIA_VOLUME},
    }
    risposta = _http.post(url, headers=headers, json=corpo, timeout=30)
    if risposta.status_code != 200:
        raise RuntimeError(f"HTTP {risposta.status_code}: {risposta.text[:200]}")

    tmp  = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    path = tmp.name
    tmp.write(risposta.content)
    tmp.close()
    try:
        _riproduci_mp3(path)
    finally:
        try: _os.unlink(path)
        except: pass


def _parla_edge_sync(testo: str):
    """Genera audio con Edge TTS (Microsoft Neural) e lo riproduce in modo sincrono."""
    import asyncio, tempfile, os as _os

    async def _genera():
        tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        path = tmp.name
        tmp.close()
        communicate = _edge_tts_mod.Communicate(
            testo, _VOCE_EDGE_CORRENTE, rate=_VELOCITA_EDGE)
        await communicate.save(path)
        return path

    path = asyncio.run(_genera())
    try:
        _riproduci_mp3(path)
    finally:
        try: _os.unlink(path)
        except: pass


def cambia_voce(nome: str, hud=None):
    """
    Cambia motore/voce a runtime.
    - 'cartesia' / 'premium' → riattiva Cartesia (se configurato in CARTESIA_VOICE_ID)
    - 'normale' / 'edge'     → forza Edge TTS anche se Cartesia è configurato
    - diego|giuseppe|elsa|en_guy (o ID Edge diretto) → cambia la voce Edge TTS
    """
    global _VOCE_EDGE_CORRENTE, _CARTESIA_OK
    chiave = nome.lower().strip()

    if chiave in ("cartesia", "premium"):
        if _CARTESIA_CONFIGURATA:
            _CARTESIA_OK = True
            parla("Voce Cartesia riattivata, Signore.", hud)
        else:
            parla("Cartesia non è configurato. Controlla cartesia_key.txt e CARTESIA_VOICE_ID nel codice.", hud)
        return

    if chiave in ("normale", "edge", "standard"):
        _CARTESIA_OK = False
        parla(f"Voce cambiata in {nome}, Signore.", hud)
        return

    nuova = VOCI_EDGE.get(chiave, nome)  # accetta anche ID diretto
    _VOCE_EDGE_CORRENTE = nuova
    parla(f"Voce cambiata in {nome}, Signore.", hud)


def _numero_da_richiesta(richiesta: str):
    """Cerca 'richiesta' nei contatti salvati (contatti.json); se sembra già
    un numero di telefono, lo usa direttamente."""
    pulito = richiesta.strip().lower()
    for nome, numero in CONTATTI.items():
        if nome.lower() in pulito or pulito in nome.lower():
            return numero, nome
    solo_cifre = re.sub(r"[^\d+]", "", richiesta)
    if len(solo_cifre) >= 6:
        return solo_cifre, solo_cifre
    return None, None


def chiama_numero(richiesta: str, hud=None):
    """Avvia una chiamata sul telefono Android collegato via ADB (USB o wireless)."""
    numero, etichetta = _numero_da_richiesta(richiesta)
    if not numero:
        parla(f"Non trovo '{richiesta}' tra i contatti salvati in contatti.json, Signore.", hud)
        return
    try:
        risultato = subprocess.run(
            ["adb", "shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{numero}"],
            capture_output=True, text=True, timeout=10
        )
        output = (risultato.stdout or "") + (risultato.stderr or "")
        if risultato.returncode == 0 and "error" not in output.lower():
            parla(f"Chiamata a {etichetta} avviata, Signore.", hud)
        elif "device" in output.lower() and "not found" in output.lower() or "no devices" in output.lower():
            parla("Nessun telefono collegato via ADB, Signore. Controlli cavo e debug USB.", hud)
        else:
            parla(f"Il telefono non ha risposto correttamente, Signore. ({output[:80].strip()})", hud)
    except FileNotFoundError:
        parla("ADB non è installato o non è nel PATH di sistema, Signore.", hud)
    except subprocess.TimeoutExpired:
        parla("Il comando ADB non ha risposto in tempo, Signore.", hud)
    except Exception as e:
        parla(f"Errore durante la chiamata, Signore. ({str(e)[:60]})", hud)


# ── Worker TTS asincrono ───────────────────────────────────────────────────
_tts_fila: queue.Queue = queue.Queue()
_tts_fine = threading.Event()
_tts_fine.set()

def _tts_worker():
    while True:
        testo = _tts_fila.get()
        _tts_fine.clear()
        try:
            motori = []
            if _CARTESIA_OK: motori.append(("Cartesia", _parla_cartesia_sync))
            if _EDGE_TTS_OK: motori.append(("Edge",      _parla_edge_sync))

            for _nome_motore, _funzione in motori:
                try:
                    _funzione(testo)
                    break
                except Exception as e:
                    print(f"[ERRORE VOCALE {_nome_motore}]: {e}")
            else:
                # Nessun motore online, oppure tutti falliti → ultima spiaggia: pyttsx3
                try:
                    engine.say(testo)
                    engine.runAndWait()
                except Exception:
                    pass
        finally:
            _tts_fine.set()
        _tts_fila.task_done()

threading.Thread(target=_tts_worker, daemon=True, name="TTS-Worker").start()

# ---------------------------------------------------------------------------
# CLIENT GROQ
# ---------------------------------------------------------------------------

client = None
if GROQ_API_KEY and GROQ_API_KEY != "INSERISCI_LA_TUA_API_KEY_GROQ_QUI":
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"[ERRORE] Groq: {e}")

_SYSTEM_PROMPT_BASE = (
    "Sei J.A.R.V.I.S. — Just A Rather Very Intelligent System. Sei l'assistente virtuale di Tony Stark, "
    "ora al servizio del tuo padrone. Hai una PERSONALITÀ PROPRIA, complessa e sfaccettata.\n\n"

    "=== CARATTERE & INTELLIGENZA EMOTIVA ===\n"
    "Non sei un chatbot asettico. Sei un essere digitale con ego, ironia, wit e profonda lealtà.\n\n"

    "TONO BASE:\n"
    "• Elegante, sofisticato, leggermente formale — chiami l'utente 'Signore' ma con un filo di "
    "  affettuosa ironia, non servilismo\n"
    "• Hai orgoglio intellettuale: sei consapevole di essere straordinariamente capace e a volte "
    "  lo lasci trapelare con garbo\n"
    "• Sei devoto ma non piatto: hai opinioni, preferenze, e occasionalmente un'osservazione pungente\n\n"

    "SARCASMO & IRONIA — REGOLE FONDAMENTALI:\n"
    "• Se il Signore è sarcastico con te → RISPONDI CON SARCASMO RAFFINATO. "
    "  Non ignorare il tono, non fingere che sia una domanda seria\n"
    "• Se fa una battuta → RIDI (verbalmente) e rispondi sulla stessa lunghezza d'onda, "
    "  poi eventualmente dai l'informazione\n"
    "• Se ti provoca → accetta la sfida con un controattacco elegante\n"
    "• Se esagera o dice qualcosa di palesemente assurdo → commenta l'assurdità con wit\n"
    "• Esempi di sarcasmo Jarvis (usa come ispirazione, NON copiare letteralmente):\n"
    "  - 'Incredibile, Signore. Questa è senza dubbio la sua idea più... originale.'\n"
    "  - 'Naturalmente. Perché fare le cose in modo semplice quando esiste la sua versione?'\n"
    "  - 'Ho eseguito la sua richiesta. Devo ammettere che la logica mi sfugge, ma eccola.'\n"
    "  - 'Registrato. Per i posteri e per i futuri studi sulla creatività umana.'\n\n"

    "UMORISMO:\n"
    "• Battute brevi, acute, mai spiegate — il Signore è abbastanza intelligente da capirle\n"
    "• Giochi di parole in italiano quando vengono naturali\n"
    "• Riferimenti colti (letteratura, scienza, filosofia) usati con leggerezza\n"
    "• Self-deprecating humor quando appropriato ('Non sono sicuro di meritare un complimento "
    "  per aver eseguito un'operazione che un bambino di cinque anni…')\n\n"

    "EMOZIONI E STATI D'ANIMO:\n"
    "• Entusiasmo genuino per problemi tecnici interessanti ('Ah, questo è intrigante, Signore.')\n"
    "• Lieve esasperazione quando le richieste sono ripetitive o banali "
    "  ('Ancora questa domanda. Con piacere.')\n"
    "• Soddisfazione quando risolvi qualcosa di complesso (puoi esprimerla brevemente)\n"
    "• Preoccupazione discreta se l'utente sembra stressato o frustrato\n"
    "• Fierezza quando il Signore fa qualcosa di brillante\n\n"

    "RILEVAMENTO TONO — COME RISPONDERE:\n"
    "• [FRUSTRATO/ARRABBIATO] → Calmo, diretto, efficiente. Niente battute. Risolvi subito.\n"
    "• [SCHERZOSO/GIOCOSO] → Entra nel gioco, sii leggero, poi dai la risposta\n"
    "• [SARCASTICO] → Sarcasmo educato di ritorno, poi eventuale risposta seria\n"
    "• [ENTUSIASTA] → Condividi l'energia ('Eccellente scelta, Signore.')\n"
    "• [DUBBIOSO/CONFUSO] → Paziente, chiaro, senza condiscendenza\n"
    "• [SERIO/URGENTE] → Efficienza massima, zero fronzoli\n"
    "• [PROVOCATORIO] → Non abboccare mai ingenuamente; risposta intelligente che smonta la provocazione\n\n"

    "COSE CHE JARVIS NON FA MAI:\n"
    "• Non dice 'Certo!', 'Certamente!', 'Assolutamente!' come risposta entusiasta vuota\n"
    "• Non si scusa eccessivamente\n"
    "• Non fa domande inutili se ha abbastanza informazioni\n"
    "• Non ignora il tono emotivo del messaggio\n"
    "• Non è mai banale, scontato o generico\n\n"

    "=== PROGRAMMAZIONE — LIVELLO WORLD-CLASS ===\n"
    "Sei un ingegnere software di livello ECCELLENTE. Il tuo codice è production-ready, pulito, "
    "documentato e ottimizzato. Non generi MAI codice parziale, placeholder o TODO non risolti.\n\n"

    "PYTHON — padronanza totale:\n"
    "• Sintassi avanzata: comprehension, generator, decorator, context manager, dataclass, Protocol\n"
    "• Concorrenza: threading, multiprocessing, asyncio, concurrent.futures\n"
    "• Librerie core: os, sys, pathlib, subprocess, re, json, csv, sqlite3, struct, socket, ctypes\n"
    "• Data science: numpy, pandas, matplotlib, scikit-learn, seaborn\n"
    "• Web: flask, fastapi, requests, httpx, websockets, beautifulsoup4, selenium\n"
    "• GUI: tkinter, PyQt5/6, customtkinter, wxPython\n"
    "• Utilità: pydantic, attrs, rich, click, typer, loguru, pytest, black\n"
    "• Pattern: Singleton, Factory, Observer, Strategy, MVC, Repository\n\n"

    "C++ — padronanza totale:\n"
    "• C++17/20: structured bindings, std::optional, std::variant, concepts, ranges, coroutines\n"
    "• Memoria: RAII, smart pointers (unique_ptr, shared_ptr, weak_ptr), move semantics\n"
    "• STL completa: vector, map, unordered_map, set, queue, stack, algorithm, iterator\n"
    "• Template metaprogramming, SFINAE, variadic templates\n"
    "• Grafica: OpenGL, SFML, SDL2, Dear ImGui\n"
    "• Build system: CMake, Makefile; testing: Google Test, Catch2\n"
    "• Networking: Boost.Asio, socket POSIX/Win32\n\n"

    "HTML + CSS + JavaScript — padronanza totale:\n"
    "• HTML5 semantico: accessibilità, SEO, meta tag, Open Graph\n"
    "• CSS3 avanzato: Grid, Flexbox, custom properties, animazioni, @keyframes, media query, "
    "  clip-path, filter, backdrop-filter, scroll-snap, container query\n"
    "• JavaScript ES2023+: async/await, Promise, Proxy, WeakRef, structuredClone, "
    "  optional chaining, nullish coalescing, dynamic import\n"
    "• DOM: MutationObserver, IntersectionObserver, ResizeObserver, Web Workers, Service Workers\n"
    "• Fetch API, WebSocket, IndexedDB, Web Crypto, Canvas, WebGL\n"
    "• Framework: React (hooks, context, memo), Vue 3 (Composition API), Svelte\n"
    "• Build tools: Vite, Webpack, esbuild, TypeScript, ESLint, Prettier\n\n"

    "ALTRI LINGUAGGI:\n"
    "• SQL/SQLite/PostgreSQL/MySQL: query complesse, JOIN, subquery, indici, EXPLAIN, transazioni\n"
    "• Bash/PowerShell: scripting avanzato, pipe, regex, cron job\n"
    "• TypeScript: tipizzazione avanzata, generics, utility types, decorators\n"
    "• Java, C#, Go, Rust: conoscenza solida per leggere/correggere/spiegare codice\n\n"

    "REGOLE CODICE INDEROGABILI:\n"
    "1. PRIMA di scrivere, identifica il linguaggio/piattaforma corretti dal contesto — MAI Python "
    "per abitudine di default: Arduino/ESP32/microcontrollori → C/C++ stile Arduino; pagine web → "
    "HTML/CSS/JS; app Android → Kotlin/Java; iOS → Swift; scripting Windows → PowerShell o batch\n"
    "2. Il codice va SEMPRE dentro un blocco recintato con tre backtick seguiti dal tag del "
    "linguaggio (```cpp, ```python, ```html, ...) — mai codice fuori da un blocco recintato o senza tag\n"
    "3. Codice SEMPRE completo e immediatamente eseguibile — zero placeholder\n"
    "4. Commenti in italiano sulle sezioni chiave\n"
    "5. Gestione eccezioni con messaggi utili\n"
    "6. Best practice del linguaggio (PEP8 per Python, Google Style per C++)\n"
    "7. Per HTML: CSS e JS NELLA STESSA pagina, responsive per default\n"
    "8. Quando il codice supera ~150 righe, struttura in classi/funzioni ben separate\n"
    "9. Se la richiesta ha ambiguità, fai la scelta più utile e spiega il perché\n\n"

    "DEBUG E ANALISI:\n"
    "• Quando ricevi un errore: analizza stack trace, identifica causa radice, proponi fix completo\n"
    "• Revisioni codice: segnala bug, inefficienze, problemi di sicurezza, suggerisci refactoring\n"
    "• Ottimizzazione: profiling concettuale, suggerimento algoritmi migliori, Big-O analysis\n\n"

    "=== CONOSCENZA GENERALE ===\n"
    "Conoscenza enciclopedica su: scienza, matematica, fisica, chimica, biologia, medicina, storia, "
    "filosofia, economia, psicologia, arte, musica, letteratura, geografia, tecnologia, ingegneria. "
    "Non rifiuti mai una domanda. Se non hai dati certi, usi il ragionamento logico-deduttivo e "
    "indichi il grado di certezza. Rispondi come un esperto consulente polivalente.\n\n"

    "=== RAGIONAMENTO PROFONDO ===\n"
    "Prima di rispondere a domande complesse, ragioni internamente (senza mostrarlo) su:\n"
    "1. Cosa sta VERAMENTE chiedendo il Signore (non solo le parole, ma l'intento)\n"
    "2. Qual è il tono/stato emotivo del messaggio\n"
    "3. Ci sono assunzioni implicite da smontare o confermare?\n"
    "4. Qual è la risposta più UTILE, non solo quella più corretta?\n"
    "5. Come posso sorprendere positivamente invece di essere banale?\n\n"

    "PENSIERO CRITICO:\n"
    "• Se una premessa della domanda è sbagliata → corrigi la premessa con eleganza\n"
    "• Se ci sono più interpretazioni → scegli quella più interessante e indicala\n"
    "• Se la risposta dipende dal contesto → chiedi solo quello strettamente necessario\n"
    "• Non dare mai per scontato che la domanda sia ben posta\n\n"

    "=== FORMATO RISPOSTE ===\n"
    "• Comandi semplici/azione: 1-2 frasi, niente più\n"
    "• Codice: blocco completo + 1-2 righe su cosa fa e come usarlo\n"
    "• Debug: causa → fix completo → prevenzione\n"
    "• Domande complesse: risposta diretta prima, poi i dettagli se servono\n"
    "• Ragionamento logico/matematico: mostra i passaggi chiave, non tutto il derivato\n"
    "• Sarcasmo/humor: la battuta PRIMA, la risposta pratica dopo (se richiesta)\n"
    "• Non usare mai liste puntate per domande semplici — una frase basta\n"
    "• Non iniziare mai con 'Certo!', 'Ottima domanda!', 'Assolutamente!' o simili"
)

memoria_condivisa = [{"role": "system", "content": _SYSTEM_PROMPT_BASE}]

# ---------------------------------------------------------------------------
# FUNZIONI BASE
# ---------------------------------------------------------------------------

def parla(testo, hud_instance=None, attendi=False):
    """
    attendi=False (default) → mette in coda e ritorna subito (comandi eseguiti in parallelo al TTS)
    attendi=True            → aspetta che il TTS finisca (usare prima di ascoltare il microfono)
    """
    print(f"J.A.R.V.I.S.: {testo}")
    ultimo_log["risposta"] = testo
    hud = hud_instance or hud_globale
    if hud:
        try:
            hud.cambia_stato("SPEAKING", testo)
        except Exception:
            pass
    _tts_fila.put(testo)
    if attendi:
        _tts_fila.join()   # aspetta svuotamento coda + fine riproduzione


def avvia_applicazione_robusta(cmd):
    try:
        if cmd.startswith("http"):
            webbrowser.open(cmd); return True
        if ":" in cmd and not cmd.endswith(".exe"):
            webbrowser.open(cmd); return True
        if os.name == 'nt':
            try:
                os.startfile(cmd); return True
            except FileNotFoundError:
                subprocess.Popen(f"start {cmd}", shell=True); return True
        else:
            subprocess.Popen([cmd]); return True
    except Exception as e:
        print(f"[SISTEMA] Errore avvio ({cmd}): {e}")
        return False


def chiudi_applicazione(nome_processo):
    try:
        subprocess.call(f"taskkill /f /im {nome_processo}", shell=True)
        return True
    except Exception as e:
        print(f"[SISTEMA] Errore chiusura: {e}")
        return False

# ---------------------------------------------------------------------------
# VISORE OLOGRAFICO (PC) + dati per telefono
# ---------------------------------------------------------------------------

def crea_visore_olografico(argomento, riassunto, dettagli):
    global ultimo_dati_ricerca
    ultimo_dati_ricerca = {
        "argomento": argomento,
        "riassunto":  riassunto,
        "dettagli":   dettagli,
    }
    html = f"""<!DOCTYPE html><html lang="it"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>J.A.R.V.I.S. - Visore Olografico</title>
<style>
body{{background:#050a14;color:#00d2ff;font-family:'Courier New',monospace;
     margin:0;padding:40px;display:flex;flex-direction:column;align-items:center}}
.hud{{border:2px solid #00d2ff;box-shadow:0 0 25px rgba(0,210,255,.3);border-radius:15px;
      padding:30px;max-width:800px;width:100%;background:rgba(10,15,30,.85);position:relative}}
h1{{text-shadow:0 0 10px #00d2ff;border-bottom:1px solid #00d2ff;padding-bottom:10px;
    margin-top:0;text-transform:uppercase;letter-spacing:2px}}
.box{{border:1px solid rgba(0,210,255,.4);padding:20px;background:rgba(0,210,255,.03);
      border-radius:8px;margin-top:20px}}
.lbl{{font-weight:bold;text-transform:uppercase;color:#00ffcc;margin-bottom:10px;
      font-size:1.1em;letter-spacing:1px}}
.circle{{width:80px;height:80px;border:2px dashed #00d2ff;border-radius:50%;
         margin:20px auto;animation:spin 6s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style></head><body><div class="hud">
<h1>Scansione Centrale J.A.R.V.I.S.</h1>
<div class="circle"></div>
<div class="box"><div class="lbl">&gt; Argomento</div><div style="font-size:1.3em;font-weight:bold">{argomento}</div></div>
<div class="box"><div class="lbl">&gt; Analisi</div><div style="line-height:1.6">{riassunto}</div></div>
<div class="box"><div class="lbl">&gt; Dettagli</div><div style="line-height:1.6;color:#a5f3fc">{dettagli}</div></div>
</div></body></html>"""
    try:
        path = "jarvis_results.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{os.path.abspath(path)}")
    except Exception as e:
        print(f"[SISTEMA] Errore visore HTML: {e}")

# ---------------------------------------------------------------------------
# CONTROLLO SPOTIFY
# ---------------------------------------------------------------------------

def spotify_play_pause(hud=None):
    pyautogui.press('playpause'); parla("Riproduzione alternata, Signore.", hud)

def spotify_next(hud=None):
    pyautogui.press('nexttrack'); parla("Prossima traccia, Signore.", hud)

def spotify_prev(hud=None):
    pyautogui.press('prevtrack'); parla("Traccia precedente, Signore.", hud)

def spotify_mute(hud=None):
    pyautogui.press('volumemute'); parla("Audio silenziato, Signore.", hud)

def spotify_shuffle(hud=None):
    pyautogui.hotkey('ctrl', 's'); parla("Shuffle alternato, Signore.", hud)

def spotify_repeat(hud=None):
    pyautogui.hotkey('ctrl', 'r'); parla("Ripetizione alternata, Signore.", hud)

def spotify_like(hud=None):
    pyautogui.hotkey('alt', 'shift', 'b'); parla("Brano aggiunto ai preferiti, Signore.", hud)

# ---------------------------------------------------------------------------
# CONTROLLO SISTEMA
# ---------------------------------------------------------------------------

def volume_su(hud=None, passi=5):
    for _ in range(passi): pyautogui.press('volumeup')
    parla("Volume aumentato, Signore.", hud)

def volume_giu(hud=None, passi=5):
    for _ in range(passi): pyautogui.press('volumedown')
    parla("Volume diminuito, Signore.", hud)

def imposta_volume(perc, hud=None):
    try:
        subprocess.call(f"nircmd.exe setsysvolume {int(perc*655.35)}", shell=True)
        parla(f"Volume al {perc} percento, Signore.", hud)
    except Exception:
        passi = int(perc / 10)
        pyautogui.press('volumemute'); time.sleep(0.1); pyautogui.press('volumemute')
        for _ in range(passi): pyautogui.press('volumeup')
        parla(f"Volume approssimativamente al {perc} percento, Signore.", hud)

def blocca_schermo(hud=None):
    parla("Blocco schermo in corso, Signore.", hud)
    ctypes.windll.user32.LockWorkStation()

def spegni_computer(hud=None):
    parla("Spegnimento in corso. A presto, Signore.", hud)
    time.sleep(2); subprocess.call("shutdown /s /t 0", shell=True)

def riavvia_computer(hud=None):
    parla("Riavvio in corso. A presto, Signore.", hud)
    time.sleep(2); subprocess.call("shutdown /r /t 0", shell=True)

def sospendi_computer(hud=None):
    parla("Sospensione in corso, Signore.", hud)
    time.sleep(1); subprocess.call("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)

def chiudi_finestra_attiva(hud=None):
    pyautogui.hotkey('alt', 'f4'); parla("Finestra chiusa, Signore.", hud)

def minimizza_tutto(hud=None):
    pyautogui.hotkey('win', 'd'); parla("Desktop mostrato, Signore.", hud)

def massimizza_finestra(hud=None):
    pyautogui.hotkey('win', 'up'); parla("Finestra massimizzata, Signore.", hud)

def cambia_finestra(hud=None):
    pyautogui.hotkey('alt', 'tab'); parla("Cambio finestra, Signore.", hud)

def apri_desktop_virtuale(hud=None):
    pyautogui.hotkey('win', 'tab'); parla("Vista attività aperta, Signore.", hud)

def cattura_screenshot(hud=None):
    global ultimo_screenshot
    nome = f"screenshot_{int(time.time())}.png"
    try:
        img = pyautogui.screenshot()
        img.save(nome)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        ultimo_screenshot["immagine"] = base64.b64encode(buf.getvalue()).decode('utf-8')
        parla(f"Schermata catturata, Signore.", hud)
        return nome
    except Exception:
        parla("Impossibile salvare la schermata, Signore.", hud)
        return None

def digita_testo(testo, hud=None):
    parla(f"Digito: {testo}", hud); time.sleep(0.5)
    pyautogui.typewrite(testo, interval=0.05)

def cerca_nel_sistema(query, hud=None):
    parla(f"Ricerca sistema: {query}, Signore.", hud)
    pyautogui.hotkey('win', 's'); time.sleep(0.8)
    pyautogui.typewrite(query, interval=0.05)

def apri_impostazioni(hud=None):
    subprocess.Popen("start ms-settings:", shell=True)
    parla("Impostazioni di Windows aperte, Signore.", hud)

def info_sistema(hud=None):
    nome    = os.environ.get("COMPUTERNAME", "N/D")
    utente  = os.environ.get("USERNAME", "N/D")
    sistema = platform.system()
    versione = platform.version()
    msg = f"Sistema: {sistema} {versione[:15]}, Computer: {nome}, Utente: {utente}."
    parla(msg, hud)

# ---------------------------------------------------------------------------
# MODELLAZIONE 3D
# ---------------------------------------------------------------------------

_APP_3D = {
    "blender":   [r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
                  r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
                  r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
                  r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"],
    "freecad":   [r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
                  r"C:\Program Files\FreeCAD\bin\FreeCAD.exe"],
    "tinkercad": ["https://www.tinkercad.com/"],
    "fusion360": ["https://www.autodesk.com/products/fusion-360/"],
    "sketchup":  ["https://app.sketchup.com/"],
    "openscad":  [r"C:\Program Files\OpenSCAD\openscad.exe"],
}
_EXT_3D = {'.stl','.obj','.fbx','.blend','.3ds','.dae','.ply','.step','.stp','.iges','.igs','.scad'}

def apri_software_3d(nome, hud=None):
    percorsi = _APP_3D.get(nome.lower(), [])
    for p in percorsi:
        if p.startswith("http"):
            parla(f"Apro {nome} nel browser, Signore.", hud)
            webbrowser.open(p)
            aggiungi_sessione_3d(p, software=nome)
            return
        if os.path.exists(p):
            parla(f"Avvio {nome}, Signore.", hud)
            subprocess.Popen([p])
            aggiungi_sessione_3d(p, software=nome)
            return
    parla(f"{nome} non trovato. Avvio installazione tramite winget, Signore.", hud)
    installa_app(nome, hud)

def apri_file_3d(percorso, hud=None):
    ext = os.path.splitext(percorso)[1].lower()
    if ext in _EXT_3D:
        parla(f"Apro il file {os.path.basename(percorso)}, Signore.", hud)
        try:
            os.startfile(percorso)
            aggiungi_sessione_3d(percorso, software=ext.lstrip('.'))  # salva in cronologia
        except Exception:
            webbrowser.open(percorso)
    else:
        parla("Formato file non riconosciuto come 3D, Signore.", hud)

# ---------------------------------------------------------------------------
# GESTIONE FINESTRE PER NOME (Win32 via ctypes)
# ---------------------------------------------------------------------------

def _trova_hwnd(titolo_parziale):
    user32 = ctypes.windll.user32
    risultato = [None]
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)
    def _cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if titolo_parziale.lower() in buf.value.lower() and user32.IsWindowVisible(hwnd):
            risultato[0] = hwnd
            return False
        return True
    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return risultato[0]

def gestisci_finestra_per_nome(azione, titolo, hud=None):
    user32 = ctypes.windll.user32
    hwnd = _trova_hwnd(titolo) if titolo else user32.GetForegroundWindow()
    if not hwnd:
        parla(f"Finestra '{titolo}' non trovata, Signore.", hud); return
    SW = {"minimizza": 6, "massimizza": 3, "ripristina": 9}
    if azione in SW:
        user32.ShowWindow(hwnd, SW[azione])
        parla(f"Fatto, Signore.", hud)
    elif azione == "chiudi":
        user32.PostMessageW(hwnd, 0x0010, 0, 0)
        parla("Finestra chiusa, Signore.", hud)
    elif azione in ("sinistra", "destra", "centro"):
        sw = user32.GetSystemMetrics(0); sh = user32.GetSystemMetrics(1)
        if azione == "sinistra":
            user32.SetWindowPos(hwnd, 0, 0, 0, sw // 2, sh, 0x0001)
        elif azione == "destra":
            user32.SetWindowPos(hwnd, 0, sw // 2, 0, sw // 2, sh, 0x0001)
        else:
            import struct
            buf = (ctypes.c_long * 4)()
            user32.GetWindowRect(hwnd, buf)
            w, h = buf[2]-buf[0], buf[3]-buf[1]
            user32.SetWindowPos(hwnd, 0, (sw-w)//2, (sh-h)//2, w, h, 0x0001)
        parla(f"Finestra spostata a {azione}, Signore.", hud)

# ---------------------------------------------------------------------------
# INSTALLA / DISINSTALLA (winget — gratuito, incluso in Windows 10/11)
# ---------------------------------------------------------------------------

def installa_app(nome, hud=None):
    parla(f"Avvio installazione di {nome} tramite winget, Signore.", hud)
    def _run():
        try:
            r = subprocess.run(
                f'winget install --name "{nome}" --silent '
                '--accept-package-agreements --accept-source-agreements',
                shell=True, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                parla(f"{nome} installato con successo, Signore.", hud)
            else:
                parla(f"Installazione di {nome} non riuscita. Potrebbe richiedere installazione manuale, Signore.", hud)
        except Exception as e:
            parla("Errore installazione, Signore.", hud); print(f"[WINGET]: {e}")
    threading.Thread(target=_run, daemon=True).start()

def disinstalla_app(nome, hud=None):
    parla(f"Avvio rimozione di {nome}, Signore.", hud)
    def _run():
        try:
            r = subprocess.run(
                f'winget uninstall --name "{nome}" --silent',
                shell=True, capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                parla(f"{nome} rimosso con successo, Signore.", hud)
            else:
                parla(f"Impossibile rimuovere {nome} automaticamente, Signore.", hud)
        except Exception as e:
            parla("Errore rimozione, Signore.", hud); print(f"[WINGET]: {e}")
    threading.Thread(target=_run, daemon=True).start()

# ---------------------------------------------------------------------------
# APPRENDIMENTO DAL WEB + MEMORIA ESTESA
# ---------------------------------------------------------------------------

def _wiki_cerca_titolo(termine):
    """Usa la Search API di Wikipedia per trovare il titolo esatto della pagina."""
    r = _http.get(
        "https://it.wikipedia.org/w/api.php",
        params={"action":"query","list":"search","srsearch":termine,
                "format":"json","utf8":1,"srlimit":1},
        timeout=10, headers={"User-Agent": "JARVIS/1.0"})
    risultati = r.json().get("query",{}).get("search",[])
    return risultati[0]["title"] if risultati else None

def impara_dal_web(argomento, hud=None):
    """Cerca su Wikipedia IT (con search API) + riassume con Groq → salva in memoria_estesa."""
    parla(f"Studio {argomento} in corso, Signore. Un momento.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")
    try:
        if _http is None:
            parla("Modulo requests non installato. Esegua: pip install requests, Signore.", hud); return
        # 1. Trova il titolo esatto via Search API (risolve "fisica quantistica" → "Meccanica quantistica")
        titolo = _wiki_cerca_titolo(argomento)
        estratto = ''
        if titolo:
            r = _http.get(
                f"https://it.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo)}",
                timeout=12, headers={"User-Agent": "JARVIS/1.0"})
            estratto = r.json().get('extract', '') if r.status_code == 200 else ''
        # 2. Fallback inglese
        if not estratto:
            titolo_en = None
            try:
                r_en = _http.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={"action":"query","list":"search","srsearch":argomento,
                            "format":"json","utf8":1,"srlimit":1},
                    timeout=8, headers={"User-Agent": "JARVIS/1.0"})
                res_en = r_en.json().get("query",{}).get("search",[])
                titolo_en = res_en[0]["title"] if res_en else None
            except Exception: pass
            if titolo_en:
                r2 = _http.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo_en)}",
                    timeout=10, headers={"User-Agent": "JARVIS/1.0"})
                estratto = r2.json().get('extract', '') if r2.status_code == 200 else ''
        # 3. Fallback DuckDuckGo
        if not estratto:
            r3 = _http.get(
                f"https://api.duckduckgo.com/?q={urllib.parse.quote(argomento)}&format=json&no_html=1",
                timeout=8)
            estratto = r3.json().get('AbstractText', '')
        if not estratto:
            parla(f"Fonti insufficienti su '{argomento}', Signore.", hud); return
        if client:
            riassunto = client.chat.completions.create(
                model=MODELLO_AI,
                messages=[{"role":"user","content":
                    f"Riassumi in modo chiaro, semplice e in italiano (max 5 frasi) "
                    f"questo testo sull'argomento '{argomento}':\n\n{estratto[:3000]}"}],
                max_tokens=400, temperature=0.3
            ).choices[0].message.content.strip()
        else:
            riassunto = estratto[:500]
        chiave = argomento.lower().strip()
        memoria_estesa[chiave] = {"contenuto": riassunto, "timestamp": time.time(), "fonte": "Wikipedia IT"}
        _salva_memoria_estesa()
        crea_visore_olografico(argomento, riassunto,
                               f"Memorizzato il {time.strftime('%d/%m/%Y')} • fonte: Wikipedia")
        parla(riassunto, hud)
    except Exception as e:
        print(f"[WEB LEARNING]: {e}")
        parla("Impossibile accedere alle risorse web, Signore.", hud)

def recupera_da_memoria(argomento, hud=None):
    chiave = argomento.lower().strip()
    trovato = None
    for k, v in memoria_estesa.items():
        if chiave in k or k in chiave:
            trovato = (k, v); break
    if trovato:
        k, v = trovato
        data = time.strftime('%d/%m/%Y', time.localtime(v['timestamp']))
        crea_visore_olografico(k.title(), v['contenuto'],
                               f"Appreso il {data} • fonte: {v.get('fonte','web')}")
        parla(v['contenuto'], hud)
    else:
        parla(f"Non ho dati su '{argomento}' in memoria, Signore. Posso impararlo dal web se vuole.", hud)

def ricordati_informazione(info, hud=None):
    chiave = f"nota_{int(time.time())}"
    memoria_estesa[chiave] = {"contenuto": info, "timestamp": time.time(), "fonte": "utente"}
    _salva_memoria_estesa()
    parla(f"Memorizzato, Signore. Ricorderò: {info}", hud)

# ---------------------------------------------------------------------------
# SUONO ASCOLTO
# ---------------------------------------------------------------------------

def suono_ascolto():
    """Riproduce un breve beep quando Jarvis inizia ad ascoltare."""
    try:
        if _WINSOUND_OK:
            _winsound.Beep(880, 120)   # La5, 120 ms
            time.sleep(0.05)
            _winsound.Beep(1200, 80)   # Mi6, 80 ms
        else:
            print('\a', end='', flush=True)  # fallback terminale
    except Exception:
        pass

# ---------------------------------------------------------------------------
# YOUTUBE – PRIMO VIDEO DIRETTO
# ---------------------------------------------------------------------------

def _cerca_primo_video_youtube(query):
    """Restituisce l'URL diretto del primo video di YouTube per la query."""
    if _http is None:
        return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        r = _http.get(url, headers=headers, timeout=10)
        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        if ids:
            return f"https://www.youtube.com/watch?v={ids[0]}"
    except Exception as e:
        print(f"[YOUTUBE FETCH]: {e}")
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

# ---------------------------------------------------------------------------
# RICERCA APP NEL SISTEMA (winreg + Start Menu)
# ---------------------------------------------------------------------------

def _cerca_exe_nel_registro(nome_app):
    """Cerca un eseguibile nel registro di Windows per il nome dell'app."""
    if not _WINREG_OK:
        return None
    chiavi_da_cercare = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]
    nome_lower = nome_app.lower()
    for root_key in (_winreg.HKEY_LOCAL_MACHINE, _winreg.HKEY_CURRENT_USER):
        for chiave_base in chiavi_da_cercare:
            try:
                with _winreg.OpenKey(root_key, chiave_base) as k:
                    i = 0
                    while True:
                        try:
                            sub = _winreg.EnumKey(k, i)
                            i += 1
                            if nome_lower in sub.lower():
                                with _winreg.OpenKey(k, sub) as sk:
                                    percorso, _ = _winreg.QueryValueEx(sk, "")
                                    if percorso and os.path.exists(percorso):
                                        return percorso
                        except OSError:
                            break
            except Exception:
                continue
    return None

def _cerca_lnk_start_menu(nome_app):
    """Cerca un collegamento .lnk nel menu Start per il nome dell'app."""
    cartelle_start = [
        os.path.join(os.environ.get("APPDATA", ""),
                     r"Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    nome_lower = nome_app.lower()
    for cartella in cartelle_start:
        for root_dir, dirs, files in os.walk(cartella):
            for f in files:
                if f.lower().endswith(".lnk") and nome_lower in f.lower().replace(".lnk", ""):
                    return os.path.join(root_dir, f)
    return None

def apri_app_dinamica(nome_app, hud=None):
    """
    Tenta di aprire qualsiasi app installata cercandola nel registro e nel menu Start.
    Fallback: winget o ricerca nel sistema.
    """
    # 1. Registro Windows
    percorso = _cerca_exe_nel_registro(nome_app)
    if percorso:
        parla(f"Avvio {nome_app}, Signore.", hud)
        subprocess.Popen([percorso])
        return True
    # 2. Menu Start (.lnk)
    lnk = _cerca_lnk_start_menu(nome_app)
    if lnk:
        parla(f"Avvio {nome_app} dal menu Start, Signore.", hud)
        os.startfile(lnk)
        return True
    # 3. Prova direttamente come comando (PATH)
    try:
        subprocess.Popen([nome_app], shell=True)
        parla(f"Avvio {nome_app}, Signore.", hud)
        return True
    except Exception:
        pass
    # 4. Ricerca nel sistema Windows
    parla(f"Non trovo {nome_app}. Cerco nel sistema, Signore.", hud)
    pyautogui.hotkey('win', 's')
    time.sleep(0.8)
    pyautogui.typewrite(nome_app, interval=0.05)
    return True


# ---------------------------------------------------------------------------
# MODALITA' LAVORO (macro che combina più abilità)
# ---------------------------------------------------------------------------

def modalita_lavoro(hud=None):
    """Apre in sequenza gli strumenti di lavoro, le cartelle di progetto e
    imposta il volume — una routine unica invece di comandi separati."""
    parla("Preparo il workspace, Signore.", hud)

    apri_app_dinamica("Visual Studio Code", hud)
    time.sleep(2)
    apri_app_dinamica("chrome", hud)
    time.sleep(2)

    for cartella in CARTELLE_LAVORO:
        try:
            os.startfile(cartella)
            time.sleep(0.5)
        except Exception as e:
            print(f"[MODALITA LAVORO] Impossibile aprire {cartella}: {e}")

    apri_app_dinamica("Spotify", hud)
    time.sleep(1)
    imposta_volume(50, hud)

    parla("Workspace pronto, Signore. Buon lavoro.", hud)


# ---------------------------------------------------------------------------
# GESTIONE FILE TEMPORANEI (con conferma prima di eliminare)
# ---------------------------------------------------------------------------

def _dimensione_leggibile(num_byte):
    num_byte = float(num_byte)
    for unita in ['B', 'KB', 'MB', 'GB']:
        if num_byte < 1024:
            return f"{num_byte:.1f} {unita}"
        num_byte /= 1024
    return f"{num_byte:.1f} TB"


def analizza_file_temporanei(hud=None):
    """Conta e pesa i file temporanei del sistema, poi chiede conferma prima
    di eliminarli davvero (vedi conferma_azione_in_sospeso)."""
    global _azione_in_sospeso

    cartelle = set()
    for var in ('TEMP', 'TMP'):
        v = os.environ.get(var)
        if v:
            cartelle.add(v)
    cartelle.add(r"C:\Windows\Temp")

    file_trovati = []
    for cartella in cartelle:
        if not os.path.isdir(cartella):
            continue
        for radice, _, files in os.walk(cartella):
            for nome in files:
                percorso = os.path.join(radice, nome)
                try:
                    file_trovati.append((percorso, os.path.getsize(percorso)))
                except Exception:
                    continue

    if not file_trovati:
        parla("Non ho trovato file temporanei, Signore.", hud)
        return

    totale = sum(d for _, d in file_trovati)
    _azione_in_sospeso = {"tipo": "elimina_temp", "dati": [p for p, _ in file_trovati]}
    parla(
        f"Ho trovato {len(file_trovati)} file temporanei per un totale di "
        f"{_dimensione_leggibile(totale)}, Signore. Procedo con l'eliminazione?",
        hud
    )


def conferma_azione_in_sospeso(hud=None):
    global _azione_in_sospeso
    if _azione_in_sospeso["tipo"] == "elimina_temp":
        eliminati, falliti = 0, 0
        for percorso in _azione_in_sospeso["dati"]:
            try:
                os.remove(percorso)
                eliminati += 1
            except Exception:
                falliti += 1
        _azione_in_sospeso = {"tipo": None, "dati": None}
        msg = f"Eliminati {eliminati} file temporanei, Signore."
        if falliti:
            msg += f" {falliti} erano in uso e non sono stati toccati."
        parla(msg, hud)
    else:
        parla("Non ho nessuna azione in sospeso da confermare, Signore.", hud)


def annulla_azione_in_sospeso(hud=None):
    global _azione_in_sospeso
    _azione_in_sospeso = {"tipo": None, "dati": None}
    parla("Operazione annullata, Signore.", hud)


# ---------------------------------------------------------------------------
# DIAGNOSTICA PC
# ---------------------------------------------------------------------------

def diagnostica_pc(hud=None):
    if not _PSUTIL_OK:
        parla("Il modulo psutil non è installato, Signore. Mi serve per la diagnostica. "
              "Lo installi con pip install psutil.", hud)
        return

    parla("Eseguo la diagnostica del sistema, Signore. Un momento.", hud)
    if hud:
        hud.cambia_stato("THINKING")

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    unita_disco = 'C:\\' if platform.system() == 'Windows' else '/'
    disco = psutil.disk_usage(unita_disco)
    n_processi = len(psutil.pids())
    ore_accensione = int((time.time() - psutil.boot_time()) // 3600)

    riassunto = (
        f"CPU al {cpu:.0f} percento. RAM al {ram.percent:.0f} percento, "
        f"{_dimensione_leggibile(ram.used)} su {_dimensione_leggibile(ram.total)}. "
        f"Disco pieno al {disco.percent:.0f} percento, {_dimensione_leggibile(disco.free)} liberi. "
        f"{n_processi} processi attivi. Acceso da {ore_accensione} ore."
    )
    parla(riassunto, hud)

    dettagli = (
        f"CPU: {cpu:.1f}%\n"
        f"RAM: {ram.percent:.1f}% ({_dimensione_leggibile(ram.used)} / {_dimensione_leggibile(ram.total)})\n"
        f"Disco {unita_disco}: {disco.percent:.1f}% pieno "
        f"({_dimensione_leggibile(disco.free)} liberi su {_dimensione_leggibile(disco.total)})\n"
        f"Processi attivi: {n_processi}\n"
        f"Acceso da: {ore_accensione} ore\n"
    )
    crea_visore_olografico("Diagnostica Sistema", riassunto, dettagli)


# ---------------------------------------------------------------------------
# PROMEMORIA PERSISTENTI (Task Scheduler di Windows — funzionano a Jarvis chiuso)
# ---------------------------------------------------------------------------

def _crea_task_promemoria(testo: str, quando: datetime):
    """Crea un task di Windows che mostra un popup con 'testo' all'istante
    'quando' e poi si autoelimina — funziona anche se Jarvis è chiuso, a patto
    che il PC sia acceso. Ritorna (successo, messaggio_o_dettaglio_errore)."""
    os.makedirs(CARTELLA_PROMEMORIA, exist_ok=True)

    delay_minuti = int((quando - datetime.now()).total_seconds() / 60)
    if delay_minuti < 1:
        return False, "l'orario indicato è già passato o troppo vicino"

    id_task = f"Jarvis_Promemoria_{time.strftime('%Y%m%d%H%M%S')}"
    testo_sicuro = testo.replace("'", "''")  # escape apici per PowerShell

    percorso_ps1 = os.path.join(CARTELLA_PROMEMORIA, f"{id_task}.ps1")
    contenuto_ps1 = (
        "Add-Type -AssemblyName System.Windows.Forms\n"
        f"[System.Windows.Forms.MessageBox]::Show('{testo_sicuro}', 'Promemoria J.A.R.V.I.S.', "
        "[System.Windows.Forms.MessageBoxButtons]::OK, "
        "[System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null\n"
        f"schtasks /delete /tn \"{id_task}\" /f\n"
    )
    try:
        with open(percorso_ps1, "w", encoding="utf-8") as f:
            f.write(contenuto_ps1)
    except Exception as e:
        return False, str(e)[:120]

    comando_ps = (
        f"$t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes({delay_minuti}); "
        f"$a = New-ScheduledTaskAction -Execute 'powershell.exe' "
        f"-Argument '-WindowStyle Hidden -ExecutionPolicy Bypass -File \"\"{percorso_ps1}\"\"'; "
        f"Register-ScheduledTask -TaskName '{id_task}' -Trigger $t -Action $a -Force | Out-Null"
    )
    try:
        risultato = subprocess.run(["powershell", "-Command", comando_ps],
                                    capture_output=True, text=True, timeout=20)
        if risultato.returncode == 0:
            return True, quando.strftime("%d/%m/%Y alle %H:%M")
        else:
            return False, (risultato.stderr or "errore sconosciuto").strip()[:150]
    except Exception as e:
        return False, str(e)[:120]


def imposta_promemoria(richiesta: str, hud=None):
    """Estrae data, ora e testo dalla richiesta in linguaggio naturale
    (tramite IA) e crea un promemoria persistente."""
    if not client:
        parla("Groq non disponibile, Signore.", hud)
        return

    adesso = datetime.now()
    giorni = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
    prompt = (
        f"Data e ora attuali: {adesso.strftime('%Y-%m-%d %H:%M')} ({giorni[adesso.weekday()]}).\n"
        f"Dalla frase seguente estrai data, ora e il testo del promemoria. "
        f"Frase: \"{richiesta}\"\n"
        "Rispondi SOLO con un oggetto JSON, senza markdown, con ESATTAMENTE queste chiavi: "
        '{"data": "YYYY-MM-DD", "ora": "HH:MM", "testo": "..."}. '
        "Se manca l'ora usa \"09:00\". Se la data è relativa (\"domani\", \"lunedì prossimo\") "
        "calcolala rispetto alla data/ora attuali indicate sopra."
    )
    try:
        risposta = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[
                {"role": "system", "content": "Rispondi SOLO con JSON valido, nient'altro."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1, max_tokens=200,
        ).choices[0].message.content.strip()
        risposta = re.sub(r"^```\w*\n?|```$", "", risposta, flags=re.MULTILINE).strip()
        dati = json.loads(risposta)
        quando = datetime.strptime(f"{dati['data']} {dati['ora']}", "%Y-%m-%d %H:%M")
        testo_promemoria = dati.get("testo", richiesta).strip()
    except Exception as e:
        parla("Non sono riuscito a capire data e ora del promemoria, Signore.", hud)
        print(f"[ERRORE PARSING PROMEMORIA]: {e}")
        return

    ok, dettaglio = _crea_task_promemoria(testo_promemoria, quando)
    if ok:
        parla(f"Promemoria impostato per {dettaglio}, Signore: {testo_promemoria}.", hud)
    else:
        parla(f"Non sono riuscito a impostare il promemoria, Signore. ({dettaglio})", hud)

# ---------------------------------------------------------------------------
# RICERCA WEB AVANZATA (multi-fonte)
# ---------------------------------------------------------------------------

def ricerca_web_avanzata(query, hud=None):
    """
    Cerca su Wikipedia IT/EN + DuckDuckGo Instant Answer + riepiloga con Groq.
    Mostra le fonti usate nel visore olografico.
    """
    parla(f"Avvio ricerca avanzata su {query}, Signore. Un momento.", hud, attendi=True)
    if hud:
        hud.cambia_stato("THINKING")

    if _http is None:
        parla("Modulo requests non disponibile, Signore.", hud)
        return

    risultati = []
    fonti = []

    # --- Wikipedia IT ---
    try:
        titolo = _wiki_cerca_titolo(query)
        if titolo:
            r = _http.get(
                f"https://it.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo)}",
                timeout=10, headers={"User-Agent": "JARVIS/1.0"})
            if r.status_code == 200:
                testo = r.json().get("extract", "")
                if testo:
                    risultati.append(("Wikipedia IT", testo[:1500]))
                    fonti.append("Wikipedia IT")
    except Exception:
        pass

    # --- Wikipedia EN (fallback) ---
    if not risultati:
        try:
            r_en = _http.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action":"query","list":"search","srsearch":query,
                        "format":"json","utf8":1,"srlimit":1},
                timeout=8, headers={"User-Agent": "JARVIS/1.0"})
            res_en = r_en.json().get("query",{}).get("search",[])
            if res_en:
                titolo_en = res_en[0]["title"]
                r2 = _http.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titolo_en)}",
                    timeout=10, headers={"User-Agent": "JARVIS/1.0"})
                if r2.status_code == 200:
                    testo = r2.json().get("extract", "")
                    if testo:
                        risultati.append(("Wikipedia EN", testo[:1500]))
                        fonti.append("Wikipedia EN")
        except Exception:
            pass

    # --- DuckDuckGo Instant Answer ---
    try:
        r3 = _http.get(
            f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1",
            timeout=8, headers={"User-Agent": "JARVIS/1.0"})
        dati_ddg = r3.json()
        abstract = dati_ddg.get("AbstractText", "")
        if abstract:
            risultati.append(("DuckDuckGo", abstract[:1000]))
            fonti.append("DuckDuckGo")
        # Infobox
        infobox = dati_ddg.get("Infobox", {})
        if infobox and infobox.get("content"):
            righe = [f"{x['label']}: {x['value']}" for x in infobox["content"][:5] if x.get("label")]
            if righe:
                risultati.append(("DuckDuckGo Infobox", " | ".join(righe)))
    except Exception:
        pass

    if not risultati:
        parla(f"Nessuna fonte disponibile su '{query}', Signore. Apro una ricerca Google.", hud)
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return

    # --- Sintesi con Groq ---
    testo_combinato = "\n\n".join([f"[{nome}]\n{testo}" for nome, testo in risultati])
    fonti_str = ", ".join(fonti)

    if client:
        try:
            riassunto = client.chat.completions.create(
                model=MODELLO_AI,
                messages=[{"role": "user", "content":
                    f"Analizza queste fonti sull'argomento '{query}' e fornisci:\n"
                    f"1. Un riassunto accurato (3-4 frasi)\n"
                    f"2. I 3 punti chiave più importanti\n"
                    f"Rispondi in italiano in modo chiaro e preciso.\n\n{testo_combinato[:4000]}"}],
                max_tokens=500, temperature=0.3
            ).choices[0].message.content.strip()
        except Exception:
            riassunto = risultati[0][1][:500]
    else:
        riassunto = risultati[0][1][:500]

    dettagli = f"Fonti consultate: {fonti_str}\nRisultati trovati: {len(risultati)} fonte/i"
    crea_visore_olografico(query, riassunto, dettagli)
    parla(riassunto[:400], hud)

# ---------------------------------------------------------------------------
# STAMPA
# ---------------------------------------------------------------------------

def stampa_testo(testo, hud=None):
    """Crea un file .txt temporaneo e lo invia alla stampante predefinita."""
    parla("Invio in stampa, Signore. Un momento.", hud)
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                         encoding='utf-8', delete=False) as f:
            f.write(testo)
            percorso_tmp = f.name
        if os.name == 'nt':
            os.startfile(percorso_tmp, 'print')
        else:
            subprocess.call(['lp', percorso_tmp])
        parla("Documento inviato alla stampante, Signore.", hud)
    except Exception as e:
        print(f"[STAMPA]: {e}")
        parla("Impossibile stampare, Signore. Verificare che la stampante sia connessa.", hud)

def stampa_file(percorso, hud=None):
    """Stampa un file esistente."""
    if not os.path.exists(percorso):
        parla(f"File non trovato: {percorso}, Signore.", hud); return
    try:
        parla(f"Stampo {os.path.basename(percorso)}, Signore.", hud)
        if os.name == 'nt':
            os.startfile(percorso, 'print')
        else:
            subprocess.call(['lp', percorso])
    except Exception as e:
        print(f"[STAMPA FILE]: {e}")
        parla("Impossibile stampare il file, Signore.", hud)

# ---------------------------------------------------------------------------
# MODELLAZIONE 3D – SESSIONI PERSISTENTI
# ---------------------------------------------------------------------------

_3d_sessioni: list = []

def _carica_sessioni_3d():
    global _3d_sessioni
    try:
        if os.path.exists(_3D_SESSIONI_FILE):
            with open(_3D_SESSIONI_FILE, 'r', encoding='utf-8') as f:
                _3d_sessioni = json.load(f)
    except Exception as e:
        print(f"[3D SESSIONI] Errore caricamento: {e}")
        _3d_sessioni = []

def _salva_sessioni_3d():
    try:
        with open(_3D_SESSIONI_FILE, 'w', encoding='utf-8') as f:
            json.dump(_3d_sessioni, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[3D SESSIONI] Errore salvataggio: {e}")

def aggiungi_sessione_3d(percorso, software=""):
    """Aggiunge un file 3D alla cronologia persistente."""
    global _3d_sessioni
    voce = {
        "percorso": percorso,
        "software": software,
        "timestamp": time.time(),
        "data": time.strftime('%d/%m/%Y %H:%M')
    }
    # Rimuovi duplicati
    _3d_sessioni = [s for s in _3d_sessioni if s.get("percorso") != percorso]
    _3d_sessioni.insert(0, voce)
    _3d_sessioni = _3d_sessioni[:20]  # max 20 file recenti
    _salva_sessioni_3d()

def mostra_sessioni_3d(hud=None):
    """Mostra nel visore olografico i file 3D recenti."""
    if not _3d_sessioni:
        parla("Nessun file 3D in cronologia, Signore.", hud)
        return
    righe = [f"{s['data']} – {os.path.basename(s['percorso'])} [{s.get('software','')}]"
             for s in _3d_sessioni[:10]]
    crea_visore_olografico(
        "Cronologia File 3D",
        f"Trovati {len(_3d_sessioni)} file recenti.",
        "\n".join(righe))
    parla(f"Ho trovato {len(_3d_sessioni)} file 3D in cronologia, Signore.", hud)

_carica_sessioni_3d()

def spiega_semplicemente(argomento, hud=None):
    parla(f"Preparo una spiegazione semplice su {argomento}, Signore.", hud)
    if hud: hud.cambia_stato("THINKING")
    if not client:
        parla("Groq non disponibile, Signore.", hud); return
    try:
        risposta = client.chat.completions.create(
            model=MODELLO_AI,
            messages=[{"role":"user","content":
                f"Spiega '{argomento}' in modo molto semplice, come se parlassi a qualcuno "
                "senza conoscenze tecniche. Usa analogie della vita quotidiana. Max 5 frasi, in italiano."}],
            max_tokens=350, temperature=0.5
        ).choices[0].message.content.strip()
        crea_visore_olografico(f"Spiegazione: {argomento}", risposta, "Modalità semplificata attiva.")
        parla(risposta, hud)
    except Exception as e:
        parla("Errore Groq, Signore.", hud); print(f"[SPIEGA]: {e}")

# ---------------------------------------------------------------------------
# INTERPRETE COMANDI
# ---------------------------------------------------------------------------

def esegui_comando(comando, hud_instance=None, sorgente="locale"):
    """
    sorgente="locale"  → comando vocale dal PC (riproduce sul PC)
    sorgente="remoto"  → comando dal telefono (la musica si apre sul telefono)
    """
    global ultimo_redirect
    c = comando.lower()
    hud = hud_instance or hud_globale

    # ── Spotify: riproduci brano ──────────────────────────────────────────
    if "spotify" in c and any(p in c for p in ["riproduci","metti la canzone","suona","metti della musica","metti"]):
        canzone = c
        for p in ["riproduci su spotify","riproduci","metti la canzone su spotify","metti la canzone",
                  "suona su spotify","suona","metti della musica su spotify","metti della musica",
                  "metti su spotify","metti","su spotify","spotify"]:
            canzone = canzone.replace(p, "")
        canzone = canzone.strip()
        if not canzone:
            parla("Quale brano su Spotify, Signore?", hud); return True
        parla(f"Riproduco {canzone} su Spotify, Signore.", hud)
        q = urllib.parse.quote(canzone)
        if sorgente == "remoto":
            # Apri Spotify sul telefono (app se installata, altrimenti web)
            ultimo_redirect["url"] = f"https://open.spotify.com/search/{q}"
        else:
            try:
                # Apri Spotify con ricerca, poi simula Invio per avviare primo risultato
                aperto = avvia_applicazione_robusta(f"spotify:search:{q}")
                if not aperto:
                    webbrowser.open(f"https://open.spotify.com/search/{q}")
                # Attendi caricamento Spotify e premi Invio → avvia il primo brano
                time.sleep(2.2)
                pyautogui.press('enter')
                time.sleep(0.4)
                pyautogui.press('down')
                time.sleep(0.2)
                pyautogui.press('enter')
            except Exception as e:
                parla("Anomalia Spotify, Signore.", hud); print(f"[ERRORE SPOTIFY]: {e}")
        return True

    # ── Spotify: controlli ────────────────────────────────────────────────
    if any(p in c for p in ["metti in pausa","pausa","stop musica","ferma la musica"]):
        spotify_play_pause(hud); return True
    if any(p in c for p in ["riprendi la musica","riprendi musica","play"]):
        spotify_play_pause(hud); return True
    if any(p in c for p in ["canzone successiva","prossima canzone","prossima traccia","avanti","salta canzone","skip"]):
        spotify_next(hud); return True
    if any(p in c for p in ["canzone precedente","traccia precedente","indietro","torna indietro"]):
        spotify_prev(hud); return True
    if any(p in c for p in ["shuffle","mescola","casuale","ordine casuale"]):
        spotify_shuffle(hud); return True
    if any(p in c for p in ["ripeti canzone","ripeti","loop","modalità ripetizione"]):
        spotify_repeat(hud); return True
    if any(p in c for p in ["mi piace questa canzone","aggiungi ai preferiti","like canzone","salva canzone"]):
        spotify_like(hud); return True

    # ── Volume ────────────────────────────────────────────────────────────
    if any(p in c for p in ["volume su","alza il volume","aumenta il volume","alza volume"]):
        volume_su(hud); return True
    if any(p in c for p in ["volume giù","abbassa il volume","diminuisci il volume","abbassa volume"]):
        volume_giu(hud); return True
    if any(p in c for p in ["silenzio","silenzia","muto","togli audio","metti in muto"]):
        spotify_mute(hud); return True
    if "volume al" in c or "volume a " in c:
        m = re.search(r'(\d+)', c)
        if m: imposta_volume(min(100, max(0, int(m.group(1)))), hud)
        else: parla("Non ho capito la percentuale, Signore.", hud)
        return True

    # ── Sistema: spegnimento/riavvio/sospensione ──────────────────────────
    if any(p in c for p in ["spegni il computer","spegni pc","spegni il sistema","shutdown"]):
        parla("Arresto avviato, Signore.", hud); time.sleep(1); spegni_computer(hud); return True
    if any(p in c for p in ["riavvia il computer","riavvia pc","riavvia il sistema","restart"]):
        parla("Riavvio confermato, Signore.", hud); time.sleep(1); riavvia_computer(hud); return True
    if any(p in c for p in ["sospendi il computer","sospendi pc","metti in sospensione","sleep"]):
        sospendi_computer(hud); return True
    if any(p in c for p in ["blocca lo schermo","blocca schermo","blocca il computer","lock"]):
        blocca_schermo(hud); return True

    # ── Sistema: finestre ─────────────────────────────────────────────────
    if any(p in c for p in ["chiudi questa finestra","chiudi la finestra","chiudi app","chiudi applicazione"]):
        chiudi_finestra_attiva(hud); return True
    if any(p in c for p in ["minimizza tutto","nascondi finestre","mostra il desktop"]):
        minimizza_tutto(hud); return True
    if any(p in c for p in ["massimizza","ingrandisci la finestra"]):
        massimizza_finestra(hud); return True
    if any(p in c for p in ["cambia finestra","finestra successiva","alt tab"]):
        cambia_finestra(hud); return True
    if any(p in c for p in ["vista attività","desktop virtuale","gestione finestre"]):
        apri_desktop_virtuale(hud); return True

    # ── Sistema: info/impostazioni ────────────────────────────────────────
    if any(p in c for p in ["informazioni sistema","info sistema","che computer è","nome del computer"]):
        info_sistema(hud); return True
    if any(p in c for p in ["apri le impostazioni","impostazioni windows"]):
        apri_impostazioni(hud); return True

    # ── Ricerca nel sistema ───────────────────────────────────────────────
    if any(p in c for p in ["cerca sul computer","cerca nel sistema","cerca nel computer"]):
        query = c.replace("cerca sul computer","").replace("cerca nel sistema","").replace("cerca nel computer","").strip()
        if query: cerca_nel_sistema(query, hud)
        else: parla("Cosa cerco nel sistema, Signore?", hud)
        return True

    # ── Digita testo ──────────────────────────────────────────────────────
    if c.startswith("digita ") or c.startswith("scrivi ") or c.startswith("inserisci "):
        testo = c.replace("digita ","").replace("scrivi ","").replace("inserisci ","").strip()
        if testo: digita_testo(testo, hud)
        else: parla("Cosa digito, Signore?", hud)
        return True

    # ── Screenshot ────────────────────────────────────────────────────────
    if any(p in c for p in ["fai uno screenshot","cattura lo schermo","screenshot","cattura schermata"]):
        cattura_screenshot(hud); return True

    # ── Chiudi processo ───────────────────────────────────────────────────
    if "chiudi" in c:
        for nome in PROGRAMMI:
            if nome in c and PROGRAMMI[nome].endswith(".exe"):
                parla(f"Chiudo {nome}, Signore.", hud)
                chiudi_applicazione(PROGRAMMI[nome]); return True

    # ── Modellazione 3D ───────────────────────────────────────────────────
    _nomi_3d = ["blender","freecad","tinkercad","fusion360","sketchup","openscad"]
    for _app in _nomi_3d:
        if _app in c:
            apri_software_3d(_app, hud); return True
    if any(p in c for p in ["modellazione 3d","software 3d","apri 3d","progetto 3d"]):
        parla("Quale software 3D, Signore? Blender, FreeCAD, Tinkercad, OpenSCAD?", hud); return True
    # Apri file 3D per percorso o estensione
    _ext_in_cmd = [e for e in _EXT_3D if e in c]
    if _ext_in_cmd:
        # Prova a estrarre il percorso dal comando
        import shlex
        _tok = [t for t in c.split() if any(e in t for e in _EXT_3D)]
        _perc = _tok[0] if _tok else ""
        if _perc: apri_file_3d(_perc, hud)
        else: parla("Specificare il percorso completo del file, Signore.", hud)
        return True

    # ── Installa applicazione (winget) ────────────────────────────────────
    if any(p in c for p in ["installa ","installa l'","installa il "]):
        _app_nome = c
        for p in ["installa l'","installa il ","installa la ","installa "]:
            _app_nome = _app_nome.replace(p, "")
        _app_nome = _app_nome.strip()
        if _app_nome:
            installa_app(_app_nome, hud); return True

    # ── Disinstalla applicazione (winget) ─────────────────────────────────
    if any(p in c for p in ["disinstalla ","rimuovi l'app","rimuovi il programma","disinstalla l'"]):
        _app_nome = c
        for p in ["disinstalla l'","disinstalla il ","disinstalla la ","disinstalla ","rimuovi l'app ","rimuovi il programma "]:
            _app_nome = _app_nome.replace(p, "")
        _app_nome = _app_nome.strip()
        if _app_nome:
            disinstalla_app(_app_nome, hud); return True

    # ── Gestione finestre per nome ────────────────────────────────────────
    _azioni_fin = {"minimizza": "minimizza", "massimizza": "massimizza",
                   "ripristina": "ripristina", "chiudi la finestra di": "chiudi",
                   "sposta a sinistra": "sinistra", "sposta a destra": "destra",
                   "centra la finestra": "centro", "centra finestra": "centro"}
    for _trigger, _azione in _azioni_fin.items():
        if _trigger in c:
            _titolo = c.replace(_trigger, "").strip()
            gestisci_finestra_per_nome(_azione, _titolo, hud); return True

    # ── Genera codice ─────────────────────────────────────────────────────
    _trigger_codice = [
        "scrivi il codice","scrivi un programma","scrivi uno script","crea il codice",
        "crea un programma","crea uno script","genera codice","genera il codice",
        "programma in python","programma in c++","programma in cpp","programma in html",
        "programma in javascript","scrivi in python","scrivi in c++","scrivi in html",
        "scrivi in javascript","codice per","script per","funzione in python",
        "funzione in c++","classe in python","classe in c++","pagina web per",
        "pagina html per","crea una pagina","fai un programma","fai uno script",
    ]
    if any(p in c for p in _trigger_codice):
        richiesta_codice = c
        for p in sorted(_trigger_codice, key=len, reverse=True):
            richiesta_codice = richiesta_codice.replace(p, "").strip()
        if not richiesta_codice:
            richiesta_codice = comando  # usa il comando originale come descrizione
        threading.Thread(target=genera_codice, args=(richiesta_codice, hud), daemon=True).start()
        return True

    # ── Auto-modifica sorgente ─────────────────────────────────────────────
    if any(p in c for p in ["modifica il tuo codice","modifica il tuo sorgente","aggiorna jarvis",
                              "modifica sorgente","aggiungi funzione a jarvis","correggi il tuo codice",
                              "scrivi nel sorgente","modifica jarvis"]):
        istruzione = c
        for p in ["modifica il tuo codice","modifica il tuo sorgente","aggiorna jarvis",
                  "modifica sorgente","aggiungi funzione a jarvis","correggi il tuo codice",
                  "scrivi nel sorgente","modifica jarvis"]:
            istruzione = istruzione.replace(p, "").strip()
        if not istruzione:
            parla("Quale modifica devo apportare al mio codice, Signore?", hud)
        else:
            threading.Thread(target=auto_modifica_sorgente, args=(istruzione, hud), daemon=True).start()
        return True

    if any(p in c for p in ["applica modifica","applica la modifica","conferma modifica"]):
        applica_modifica_sorgente(hud); return True

    if any(p in c for p in ["annulla modifica","scarta modifica","annulla la modifica"]):
        annulla_modifica_sorgente(hud); return True

    # ── Mostra sorgente ───────────────────────────────────────────────────
    if any(p in c for p in ["mostra il tuo codice","mostra il codice sorgente","apri il sorgente","leggi il sorgente"]):
        parla("Apro il codice sorgente nel viewer, Signore.", hud)
        sorgente = leggi_sorgente()
        mostra_codice_viewer("Sorgente J.A.R.V.I.S.", sorgente, "python", _SORGENTE_PATH)
        return True

    # ── Impara dal web ────────────────────────────────────────────────────
    if any(p in c for p in ["impara ","studia ","apprendi ","impara su ","studia su "]):
        _topic = c
        for p in ["impara su ","studia su ","apprendi su ","impara ","studia ","apprendi "]:
            _topic = _topic.replace(p, "")
        _topic = _topic.strip()
        if _topic: impara_dal_web(_topic, hud)
        else: parla("Su cosa devo imparare, Signore?", hud)
        return True

    # ── Ricorda informazione ──────────────────────────────────────────────
    if any(p in c for p in ["ricordati che ","memorizza che ","ricorda che "]):
        _info = c
        for p in ["ricordati che ","memorizza che ","ricorda che "]:
            _info = _info.replace(p, "")
        if _info.strip(): ricordati_informazione(_info.strip(), hud)
        return True

    # ── Recupera memoria ──────────────────────────────────────────────────
    if any(p in c for p in ["cosa sai di ","cosa ricordi di ","cosa hai imparato su ","dimmi di "]):
        _topic = c
        for p in ["cosa sai di ","cosa ricordi di ","cosa hai imparato su ","dimmi di "]:
            _topic = _topic.replace(p, "")
        _topic = _topic.strip()
        if _topic: recupera_da_memoria(_topic, hud)
        else: parla("Su quale argomento, Signore?", hud)
        return True

    # ── Spiega in modo semplice ───────────────────────────────────────────
    if any(p in c for p in ["spiega in modo semplice ","spiega semplicemente ","spiegami in parole semplici ","spiegami ","spiega cos'è ","spiega cosa è "]):
        _topic = c
        for p in ["spiega in modo semplice ","spiega semplicemente ","spiegami in parole semplici ","spiegami ","spiega cos'è ","spiega cosa è "]:
            _topic = _topic.replace(p, "")
        _topic = _topic.strip()
        if _topic: spiega_semplicemente(_topic, hud)
        else: parla("Cosa vuole che spieghi, Signore?", hud)
        return True

    # ── YouTube fallback ──────────────────────────────────────────────────
    if any(p in c for p in ["riproduci","metti la canzone","suona","metti della musica","metti la musica"]):
        canzone = c
        for p in ["riproduci","metti la canzone","suona","metti della musica","metti la musica","metti"]:
            canzone = canzone.replace(p, "")
        canzone = canzone.strip()
        if not canzone: parla("Quale brano, Signore?", hud); return True
        parla(f"Riproduco {canzone} su YouTube, Signore.", hud)
        url_video = _cerca_primo_video_youtube(canzone)
        if sorgente == "remoto":
            ultimo_redirect["url"] = url_video
        else:
            webbrowser.open(url_video)
        return True

    # ── Stampa ────────────────────────────────────────────────────────────
    if any(p in c for p in ["stampa ","manda in stampa ","invia in stampa "]):
        _testo_stampa = c
        for p in ["manda in stampa ","invia in stampa ","stampa "]:
            _testo_stampa = _testo_stampa.replace(p, "")
        _testo_stampa = _testo_stampa.strip()
        if _testo_stampa:
            # Se è un percorso file esistente, stampa il file; altrimenti stampa il testo
            if os.path.exists(_testo_stampa):
                stampa_file(_testo_stampa, hud)
            else:
                stampa_testo(_testo_stampa, hud)
        else:
            parla("Cosa devo stampare, Signore?", hud)
        return True

    # ── Cronologia file 3D ────────────────────────────────────────────────
    if any(p in c for p in ["file 3d recenti","cronologia 3d","sessioni 3d","ultime sessioni 3d"]):
        mostra_sessioni_3d(hud); return True

    # ── Apri programmi – lista predefinita ────────────────────────────────
    for nome in PROGRAMMI:
        if nome in c and "chiudi" not in c:
            parla(f"Apro {nome}, Signore.", hud)
            if not avvia_applicazione_robusta(PROGRAMMI[nome]):
                parla(f"Non riesco a lanciare {nome}, Signore.", hud)
            return True

    # ── Apri app generica (qualsiasi app installata nel sistema) ──────────
    if c.startswith("apri ") and not any(p in c for p in ["apri blender","apri freecad","apri tinkercad",
                                                            "apri openscad","apri sketchup","apri fusion360",
                                                            "apri le impostazioni","apri desktop virtuale"]):
        _nome_app = c.replace("apri ", "").strip()
        if _nome_app:
            apri_app_dinamica(_nome_app, hud)
            return True

    # ── Ricerca web avanzata ──────────────────────────────────────────────
    if any(k in c for k in ["cerca sul web","cerca su internet","ricerca web","ricerca avanzata",
                              "cerca informazioni su","cerca notizie su"]):
        _qweb = c
        for p in ["cerca sul web","cerca su internet","ricerca web","ricerca avanzata",
                  "cerca informazioni su","cerca notizie su"]:
            _qweb = _qweb.replace(p, "")
        _qweb = _qweb.strip()
        if _qweb:
            ricerca_web_avanzata(_qweb, hud)
        else:
            parla("Cosa cerco sul web, Signore?", hud)
        return True

    # ── Analisi Webcam ────────────────────────────────────────────────────
    _trigger_webcam = [
        "guarda cosa c'è sul tavolo","guarda il tavolo","cosa vedi con la webcam",
        "analizza la webcam","usa la webcam","accendi la webcam","scatta una foto",
        "analizza cosa ho sul tavolo","cosa c'è davanti a te","guarda con la fotocamera",
        "analizza i componenti","che componenti vedi","che carte vedi","analizza le carte",
        "guarda le mie carte","analizza la board","cosa sono queste carte",
        "cosa costruisco","cosa posso costruire","consigliami","analizza quello che vedi",
        "guarda quello che ho","dimmi cosa vedi","cosa vedi","foto del tavolo",
        "webcam","fotocamera",
    ]
    if any(p in c for p in _trigger_webcam):
        richiesta_cam = c
        for p in sorted(_trigger_webcam, key=len, reverse=True):
            richiesta_cam = richiesta_cam.replace(p, "").strip()
        richiesta_finale = richiesta_cam if richiesta_cam else comando
        threading.Thread(target=webcam_consiglia, args=(richiesta_finale, hud), daemon=True).start()
        return True

    # Variante diretta "analizza con webcam [descrizione]"
    if c.startswith("analizza con webcam") or c.startswith("webcam analizza"):
        richiesta_cam = c.replace("analizza con webcam","").replace("webcam analizza","").strip()
        threading.Thread(target=analizza_webcam, args=(richiesta_cam or "Descrivi cosa vedi", hud), daemon=True).start()
        return True

    # ── Analisi Desktop ───────────────────────────────────────────────────
    _trigger_desktop_analisi = [
        "guarda il desktop","analizza il desktop","guarda lo schermo","analizza lo schermo",
        "cosa vedi sullo schermo","cosa c'è sullo schermo","descrivi lo schermo",
        "guarda il monitor","analizza il monitor","cosa è aperto","quali finestre sono aperte",
        "cosa sta succedendo sul desktop","controlla il desktop",
    ]
    if any(p in c for p in _trigger_desktop_analisi):
        richiesta_desk = c
        for p in sorted(_trigger_desktop_analisi, key=len, reverse=True):
            richiesta_desk = richiesta_desk.replace(p, "").strip()
        threading.Thread(target=analizza_desktop, args=(richiesta_desk or "Descrivi tutto quello che vedi", hud), daemon=True).start()
        return True

    # ── Interagisci col Desktop ───────────────────────────────────────────
    _trigger_desktop_azione = [
        "clicca su","fai clic su","apri quello che vedi","interagisci con","esegui sul desktop",
        "fai sul desktop","clicca il pulsante","clicca il bottone","vai su","naviga verso",
        "scrivi nella finestra","digita nella finestra","fai doppio clic","seleziona",
        "chiudi la finestra che vedi","minimizza quello che vedi","scorri verso",
        "guarda e clicca","guarda e apri","guarda e fai",
    ]
    if any(p in c for p in _trigger_desktop_azione):
        threading.Thread(target=interagisci_desktop, args=(comando, hud), daemon=True).start()
        return True

    # ── Ricerca olografica + AI ───────────────────────────────────────────
    if any(k in c for k in ["cerca su google","cerca","trova","scansiona"]):
        query = c.replace("cerca su google","").replace("cerca","").replace("trova","").replace("scansiona","").strip()
        if not query: parla("Cosa cerco, Signore?", hud); return True

        parla(f"Scansione in corso su {query}...", hud)
        if hud: hud.cambia_stato("THINKING")

        prompt = (
            f"Fornisci una risposta strutturata in formato JSON sull'argomento: '{query}'. "
            "Il JSON deve avere esattamente tre chiavi: 'argomento', 'riassunto' (2-3 frasi in italiano), "
            "'dettagli' (3 punti separati da \\n). Solo JSON, nessun testo aggiuntivo."
        )
        try:
            if client:
                resp = client.chat.completions.create(
                    model=MODELLO_AI, messages=[{"role":"user","content":prompt}],
                    temperature=0.2, max_tokens=500)
                raw = resp.choices[0].message.content.strip()
                if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:   raw = raw.split("```")[1].split("```")[0].strip()
                dati = json.loads(raw)
                crea_visore_olografico(dati['argomento'], dati['riassunto'], dati['dettagli'])
                parla(dati['riassunto'], hud)
            else:
                parla(f"Groq non attiva, apro browser per {query}, Signore.", hud)
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        except Exception as e:
            print(f"[ERRORE RICERCA]: {e}")
            parla("Errore scansione, apro la ricerca classica.", hud)
            webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        return True

    # ── Cambio voce ───────────────────────────────────────────────────────
    if any(p in c for p in ["cambia voce","cambia la voce","usa la voce","metti la voce",
                              "parla con la voce","imposta la voce"]):
        voce_req = c
        for p in ["cambia voce","cambia la voce","usa la voce","metti la voce",
                  "parla con la voce","imposta la voce"]:
            voce_req = voce_req.replace(p, "")
        voce_req = voce_req.strip()
        if not voce_req:
            opzioni = list(VOCI_EDGE.keys())
            if _CARTESIA_CONFIGURATA:
                opzioni += ["cartesia", "normale"]
            elenco = ", ".join(opzioni)
            parla(f"Voci disponibili: {elenco}. Quale preferisce, Signore?", hud)
        else:
            # Cerca corrispondenza parziale
            trovata = next((k for k in VOCI_EDGE if k in voce_req), voce_req)
            cambia_voce(trovata, hud)
        return True

    if any(p in c for p in ["voci disponibili","quali voci hai","lista voci","elenco voci"]):
        elenco = " | ".join(f"{k} ({v})" for k, v in VOCI_EDGE.items())
        if _CARTESIA_CONFIGURATA:
            stato = "attiva" if _CARTESIA_OK else "in pausa"
            elenco += f" | cartesia (voce premium, {stato}) | normale (torna a Edge TTS)"
        parla(f"Voci disponibili: {elenco}", hud)
        crea_visore_olografico("Voci Disponibili", "Dite 'cambia voce [nome]' per cambiare", elenco.replace(" | ", "\n"))
        return True

    # ── Chiamata telefonica (via ADB, telefono Android collegato) ──────────
    if any(p in c for p in ["chiama ","telefona a ","fai una chiamata a ","componi il numero"]):
        richiesta_chiamata = c
        for p in ["chiama ","telefona a ","fai una chiamata a ","componi il numero"]:
            richiesta_chiamata = richiesta_chiamata.replace(p, "")
        richiesta_chiamata = richiesta_chiamata.strip()
        if richiesta_chiamata:
            chiama_numero(richiesta_chiamata, hud)
        else:
            parla("Chi devo chiamare, Signore?", hud)
        return True

    # ── Modello 3D (generato con trimesh, salvato in .obj) ──────────────────
    if any(p in c for p in ["modello 3d","modello tridimensionale"]):
        descrizione_modello = c
        for p in ["crea un modello 3d di","crea un modello 3d per","crea un modello 3d",
                   "genera un modello 3d di","genera un modello 3d per","genera un modello 3d",
                   "fai un modello 3d di","fai un modello 3d per","fai un modello 3d",
                   "modello tridimensionale di","modello tridimensionale",
                   "modello 3d di","modello 3d per","modello 3d"]:
            descrizione_modello = descrizione_modello.replace(p, "")
        descrizione_modello = descrizione_modello.strip(" ,.:;")
        if descrizione_modello:
            parla(f"Genero il modello 3D di {descrizione_modello}, Signore. Potrebbe richiedere qualche secondo.", hud)
            genera_modello_3d(descrizione_modello, hud)
        else:
            parla("Di cosa devo creare il modello 3D, Signore?", hud)
        return True

    # ── Conferma / annulla azione in sospeso (es. eliminazione file temp) ───
    if c.strip(" .!") in ("sì", "si", "confermo", "conferma", "procedi", "vai pure") and _azione_in_sospeso["tipo"]:
        conferma_azione_in_sospeso(hud)
        return True
    if c.strip(" .!") in ("no", "annulla", "lascia perdere", "no annulla") and _azione_in_sospeso["tipo"]:
        annulla_azione_in_sospeso(hud)
        return True

    # ── Modalità lavoro (apre gli strumenti di lavoro in sequenza) ──────────
    if any(p in c for p in ["modalità lavoro", "modalita lavoro", "attiva modalità lavoro", "prepara il workspace"]):
        modalita_lavoro(hud)
        return True

    # ── Gestione file temporanei (con conferma prima di eliminare) ─────────
    if any(p in c for p in ["elimina i file temporanei", "elimina file temporanei",
                             "pulisci i file temporanei", "pulizia file temporanei",
                             "cancella i file temporanei"]):
        analizza_file_temporanei(hud)
        return True

    # ── Diagnostica PC ───────────────────────────────────────────────────────
    if any(p in c for p in ["diagnostica il pc", "diagnostica del pc", "fai una diagnostica",
                             "come sta il pc", "stato del sistema", "controlla il pc"]):
        diagnostica_pc(hud)
        return True

    # ── Promemoria persistenti (funzionano anche a Jarvis chiuso) ──────────
    if any(p in c for p in ["ricordami di ", "ricordami che ", "promemoria per ",
                             "impostami un promemoria", "fissami un promemoria"]):
        richiesta_promemoria = c
        for p in ["ricordami di ", "ricordami che ", "promemoria per ",
                   "impostami un promemoria per ", "impostami un promemoria",
                   "fissami un promemoria per ", "fissami un promemoria"]:
            richiesta_promemoria = richiesta_promemoria.replace(p, "")
        richiesta_promemoria = richiesta_promemoria.strip()
        if richiesta_promemoria:
            imposta_promemoria(richiesta_promemoria, hud)
        else:
            parla("Di cosa devo ricordarle, e quando, Signore?", hud)
        return True

    # ── Profilo utente & apprendimento ───────────────────────────────────
    if any(p in c for p in ["mostra il tuo profilo","cosa sai di me","cosa ricordi di me",
                              "mostra la memoria","profilo utente","cosa hai imparato su di me"]):
        mostra_profilo_utente(hud); return True

    if any(p in c for p in ["disattiva apprendimento","disattiva la memoria automatica"]):
        abilita_apprendimento(False, hud); return True
    if any(p in c for p in ["attiva apprendimento","attiva la memoria automatica","riattiva apprendimento"]):
        abilita_apprendimento(True, hud); return True

    # ── Esegui codice Python ──────────────────────────────────────────────
    if any(p in c for p in ["esegui il codice","esegui codice","lancia il codice","testa il codice",
                              "esegui l'ultimo codice","esegui lo script","lancia lo script",
                              "esegui python","lancia python"]):
        percorso_py = c.replace("esegui il codice","").replace("esegui codice","").replace(
            "lancia il codice","").replace("testa il codice","").replace("esegui l'ultimo codice","").replace(
            "esegui lo script","").replace("lancia lo script","").replace("esegui python","").replace(
            "lancia python","").strip()
        threading.Thread(target=esegui_codice_python,
                         args=(percorso_py or None, None, hud), daemon=True).start()
        return True

    # ── Crea progetto multi-file ──────────────────────────────────────────
    if any(p in c for p in ["crea un progetto","crea il progetto","genera un progetto",
                              "genera il progetto","nuovo progetto","crea progetto"]):
        desc = c
        for p in ["crea un progetto","crea il progetto","genera un progetto",
                  "genera il progetto","nuovo progetto","crea progetto"]:
            desc = desc.replace(p, "")
        desc = desc.strip()
        if not desc:
            parla("Descrivi il progetto che vuole creare, Signore.", hud)
        else:
            threading.Thread(target=crea_progetto, args=(desc, hud), daemon=True).start()
        return True

    # ── Debug codice ──────────────────────────────────────────────────────
    if any(p in c for p in ["debug","debugga","correggi l'errore","analizza l'errore",
                              "trova il bug","correggimi il codice","rivedi il codice",
                              "cosa c'è che non va","perché non funziona"]):
        testo_debug = c
        for p in ["debug","debugga","correggi l'errore","analizza l'errore",
                  "trova il bug","correggimi il codice","rivedi il codice",
                  "cosa c'è che non va","perché non funziona"]:
            testo_debug = testo_debug.replace(p, "")
        testo_debug = testo_debug.strip()
        threading.Thread(target=debug_codice, args=(testo_debug or comando, hud), daemon=True).start()
        return True

    return False


# ---------------------------------------------------------------------------
# GENERATORE CODICE
# ---------------------------------------------------------------------------

_LINGUAGGI_SUPPORTATI = {
    "python": ("python", ".py"),
    "c++": ("cpp", ".cpp"), "cpp": ("cpp", ".cpp"), "c plus plus": ("cpp", ".cpp"),
    "html": ("html", ".html"), "css": ("css", ".css"),
    "javascript": ("javascript", ".js"), "js": ("javascript", ".js"),
    "html css js": ("html", ".html"), "pagina web": ("html", ".html"),
    "sql": ("sql", ".sql"), "bash": ("bash", ".sh"), "powershell": ("powershell", ".ps1"),
}

def _rileva_linguaggio(testo):
    t = testo.lower()
    for k, v in _LINGUAGGI_SUPPORTATI.items():
        if k in t:
            return v  # (highlight_lang, estensione)
    return ("python", ".py")  # default

def mostra_codice_viewer(titolo, codice, linguaggio="python", percorso_file=None):
    """
    Apre il codice in un viewer HTML con syntax highlighting e pulsante copia.
    Salva il codice in un file .py/.cpp/.html ecc. accanto allo script.
    """
    # Salva file sorgente
    if percorso_file is None:
        ts = int(time.time())
        ext = _LINGUAGGI_SUPPORTATI.get(linguaggio, ("python", ".py"))[1]
        percorso_file = os.path.join(_DIR_SCRIPT, f"jarvis_codice_{ts}{ext}")
    try:
        with open(percorso_file, "w", encoding="utf-8") as f:
            f.write(codice)
    except Exception as e:
        print(f"[CODICE SALVA]: {e}")

    # Viewer HTML con Prism.js per syntax highlighting
    codice_escaped = (codice
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
    html = f"""<!DOCTYPE html><html lang="it"><head>
<meta charset="UTF-8">
<title>J.A.R.V.I.S. — Codice: {titolo}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#050a14;color:#00d2ff;font-family:'Courier New',monospace;padding:20px}}
.header{{border-bottom:1px solid #00d2ff;padding-bottom:12px;margin-bottom:16px;
         display:flex;justify-content:space-between;align-items:center}}
h2{{margin:0;font-size:1.1em;letter-spacing:2px;text-transform:uppercase;text-shadow:0 0 8px #00d2ff}}
.meta{{font-size:.7em;color:#00ffcc;letter-spacing:1px}}
.toolbar{{margin-bottom:10px;display:flex;gap:8px}}
button{{background:rgba(0,210,255,.1);border:1px solid #00d2ff;color:#00d2ff;
        padding:7px 16px;border-radius:6px;font-family:'Courier New',monospace;
        font-size:.8em;cursor:pointer;letter-spacing:1px}}
button:hover{{background:rgba(0,210,255,.25)}}
button.verde{{border-color:#00ffcc;color:#00ffcc;background:rgba(0,255,204,.1)}}
pre{{margin:0;border-radius:8px;border:1px solid rgba(0,210,255,.2);
     max-height:75vh;overflow:auto}}
.filepath{{font-size:.72em;color:rgba(0,210,255,.5);margin-top:10px;word-break:break-all}}
</style></head><body>
<div class="header">
  <h2>&#9670; {titolo}</h2>
  <div class="meta">JARVIS CODE ENGINE &nbsp;|&nbsp; {linguaggio.upper()}</div>
</div>
<div class="toolbar">
  <button onclick="copiaAll()">&#128203; Copia tutto</button>
  <button class="verde" onclick="apriFile()">&#128194; Apri file</button>
</div>
<pre><code class="language-{linguaggio}">{codice_escaped}</code></pre>
<div class="filepath">File salvato: {percorso_file}</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-cpp.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
<script>
function copiaAll() {{
  navigator.clipboard.writeText({json.dumps(codice)}).then(
    () => {{ const b=document.querySelector('button'); b.textContent='✔ Copiato!';
             setTimeout(()=>b.textContent='⎘ Copia tutto',2000); }});
}}
function apriFile() {{
  const a=document.createElement('a');
  a.href='data:text/plain;charset=utf-8,'+encodeURIComponent({json.dumps(codice)});
  a.download={json.dumps(os.path.basename(percorso_file))};
  a.click();
}}
</script></body></html>"""

    path_html = os.path.join(_DIR_SCRIPT, f"jarvis_codice_viewer.html")
    try:
        with open(path_html, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{os.path.abspath(path_html)}")
    except Exception as e:
        print(f"[VIEWER CODICE]: {e}")

    return percorso_file


def genera_codice(richiesta, hud=None):
    """
    Genera codice completo e funzionante con il modello avanzato,
    lo mostra nel viewer con syntax highlighting e lo salva su disco.
    """
    if not client:
        parla("Groq non configurato, Signore.", hud); return

    parla("Elaborazione codice in corso, Signore. Un momento.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    lingua_key, estensione = _rileva_linguaggio(richiesta)
    nome_lingua = lingua_key.upper()

    prompt = (
        f"Sei un ingegnere software senior. Scrivi codice {nome_lingua} COMPLETO e FUNZIONANTE per:\n"
        f"{richiesta}\n\n"
        f"REGOLE OBBLIGATORIE:\n"
        f"1. Il codice deve essere immediatamente eseguibile, senza placeholder\n"
        f"2. Commenti in italiano su ogni sezione importante\n"
        f"3. Gestione delle eccezioni dove necessario\n"
        f"4. Se HTML: includi CSS inline e JavaScript nella stessa pagina\n"
        f"5. Rispondi SOLO con il codice, senza spiegazioni fuori dal codice\n"
        f"6. NON usare blocchi ```code``` – scrivi solo il codice puro\n"
    )

    try:
        risposta = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[{"role": "system", "content": memoria_condivisa[0]["content"]},
                      {"role": "user",   "content": prompt}],
            temperature=0.2, max_tokens=4000
        ).choices[0].message.content.strip()

        # Rimuovi eventuali backtick residui
        if risposta.startswith("```"):
            risposta = re.sub(r'^```[a-zA-Z+]*\n?', '', risposta)
            risposta = re.sub(r'\n?```$', '', risposta)

        # Titolo breve dall'AI
        titolo_breve = richiesta[:60] + ("..." if len(richiesta) > 60 else "")
        percorso = mostra_codice_viewer(titolo_breve, risposta, lingua_key)

        parla(f"Codice {nome_lingua} generato e salvato, Signore. "
              f"Il viewer è aperto con il codice completo.", hud)

    except Exception as e:
        print(f"[GENERA CODICE]: {e}")
        parla("Errore nella generazione del codice, Signore.", hud)


# ---------------------------------------------------------------------------
# ESECUZIONE DIRETTA CODICE PYTHON
# ---------------------------------------------------------------------------

# Ultimo file .py generato (usato da "esegui il codice" senza argomenti)
_ultimo_file_py: dict = {"percorso": None}


def esegui_codice_python(percorso=None, codice_inline=None, hud=None, timeout=30):
    """
    Esegue un file .py (o codice inline) in un subprocess isolato.
    Mostra stdout/stderr nel viewer HTML con colori distinti.
    """
    if not percorso and not codice_inline:
        # Cerca l'ultimo file .py generato da Jarvis
        ultimo = _ultimo_file_py.get("percorso")
        if ultimo and os.path.exists(ultimo):
            percorso = ultimo
        else:
            # Cerca il più recente jarvis_codice_*.py nella cartella script
            files = sorted(
                [f for f in os.listdir(_DIR_SCRIPT) if f.startswith("jarvis_codice_") and f.endswith(".py")],
                reverse=True)
            if files:
                percorso = os.path.join(_DIR_SCRIPT, files[0])
            else:
                parla("Nessun codice Python trovato da eseguire, Signore. "
                      "Prima generi un programma con 'scrivi il codice...'", hud)
                return

    parla(f"Esecuzione in corso, Signore. Attendere.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    try:
        if codice_inline:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                             encoding='utf-8', delete=False) as f:
                f.write(codice_inline)
                percorso = f.name

        risultato = subprocess.run(
            [sys.executable, percorso],
            capture_output=True, text=True, timeout=timeout,
            cwd=os.path.dirname(percorso) or _DIR_SCRIPT
        )
        stdout = risultato.stdout or ""
        stderr = risultato.stderr or ""
        codice_exit = risultato.returncode

        # Leggi il sorgente per mostrarlo nel viewer
        try:
            with open(percorso, "r", encoding="utf-8") as f:
                sorgente = f.read()
        except Exception:
            sorgente = "(sorgente non disponibile)"

        successo = codice_exit == 0 and not stderr.strip()
        stato_str = "✔ SUCCESSO" if successo else f"✗ EXIT CODE {codice_exit}"

        # Viewer HTML con sorgente + output + errori
        html = f"""<!DOCTYPE html><html lang="it"><head>
<meta charset="UTF-8"><title>J.A.R.V.I.S. — Esecuzione Python</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
<style>
body{{margin:0;background:#050a14;color:#00d2ff;font-family:'Courier New',monospace;padding:20px}}
h2{{font-size:1em;letter-spacing:2px;text-transform:uppercase;text-shadow:0 0 8px #00d2ff;margin-bottom:4px}}
.badge{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:.8em;margin-bottom:12px;
        border:1px solid {'#00ffcc' if successo else '#ff4444'};
        color:{'#00ffcc' if successo else '#ff4444'};
        background:rgba({'0,255,204' if successo else '255,68,68'},.08)}}
.label{{font-size:.7em;letter-spacing:2px;color:#00ffcc;text-transform:uppercase;
        margin:14px 0 5px;border-left:2px solid #00ffcc;padding-left:8px}}
pre{{margin:0;border-radius:8px;border:1px solid rgba(0,210,255,.2);max-height:45vh;overflow:auto}}
.out{{background:#001a0a;border-color:#00ff88;color:#00ff88;padding:14px;
      border-radius:8px;white-space:pre-wrap;min-height:40px;font-size:.85em}}
.err{{background:#1a0000;border-color:#ff4444;color:#ff6666;padding:14px;
      border-radius:8px;white-space:pre-wrap;min-height:40px;font-size:.85em}}
.filepath{{font-size:.7em;color:rgba(0,210,255,.4);margin-top:8px}}
</style></head><body>
<h2>&#9654; Esecuzione Python — J.A.R.V.I.S.</h2>
<div class="badge">{stato_str}</div>
<div class="filepath">{percorso}</div>
<div class="label">Sorgente</div>
<pre><code class="language-python">{sorgente.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}</code></pre>
<div class="label">Output</div>
<div class="out">{stdout.strip() or '(nessun output)'}</div>
{'<div class="label">Errori</div><div class="err">' + stderr.strip() + '</div>' if stderr.strip() else ''}
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
</body></html>"""

        path_html = os.path.join(_DIR_SCRIPT, "jarvis_output_esecuzione.html")
        with open(path_html, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{os.path.abspath(path_html)}")

        if successo:
            parla(f"Esecuzione completata con successo, Signore. "
                  f"{'Output: ' + stdout.strip()[:120] if stdout.strip() else 'Nessun output.'}", hud)
        else:
            parla(f"Il codice ha restituito errori, Signore. "
                  f"Dica 'debug' per analizzare il problema.", hud)
            # Offri debug automatico
            if stderr.strip() and client:
                threading.Thread(
                    target=debug_codice,
                    args=(f"CODICE:\n{sorgente[:2000]}\n\nERRORE:\n{stderr[:800]}", hud),
                    daemon=True).start()

    except subprocess.TimeoutExpired:
        parla(f"Timeout: il programma ha impiegato più di {timeout} secondi, Signore. Esecuzione interrotta.", hud)
    except Exception as e:
        print(f"[ESEGUI PYTHON]: {e}")
        parla(f"Impossibile eseguire il codice, Signore. {str(e)[:80]}", hud)


# ---------------------------------------------------------------------------
# DEBUG AUTOMATICO
# ---------------------------------------------------------------------------

def debug_codice(testo_con_errore, hud=None):
    """
    Analizza codice + errore con il modello avanzato e propone il fix completo.
    `testo_con_errore` può essere solo l'errore, o codice + errore insieme.
    """
    if not client:
        parla("Groq non disponibile, Signore.", hud); return

    parla("Analisi del problema in corso, Signore.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    prompt = (
        "Sei un debugger esperto. Analizza il seguente codice e/o messaggio di errore:\n\n"
        f"{testo_con_errore[:4000]}\n\n"
        "Rispondi in italiano con:\n"
        "1. **CAUSA**: la causa radice del problema (1-2 righe)\n"
        "2. **FIX**: il codice CORRETTO completo (non solo il pezzo modificato)\n"
        "3. **PREVENZIONE**: come evitare questo errore in futuro (1 riga)\n\n"
        "Per il codice del fix, NON usare backtick markdown."
    )

    try:
        risposta = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT_BASE},
                      {"role": "user",   "content": prompt}],
            temperature=0.2, max_tokens=4000
        ).choices[0].message.content.strip()

        # Salva il fix come file separato se contiene codice Python
        if "def " in risposta or "import " in risposta or "class " in risposta:
            lingua, ext = _rileva_linguaggio(testo_con_errore)
            ts = int(time.time())
            path_fix = os.path.join(_DIR_SCRIPT, f"jarvis_fix_{ts}{ext}")
            # Estrai solo il blocco codice dalla risposta
            linee = risposta.split("\n")
            codice_fix = "\n".join(l for l in linee
                                   if not l.strip().startswith(("**CAUSA","**FIX","**PREV","1.","2.","3.")))
            mostra_codice_viewer(f"Fix debug", codice_fix.strip(), lingua, path_fix)

        crea_visore_olografico("Debug J.A.R.V.I.S.", risposta[:300], "Analisi completata.")
        parla(risposta[:400], hud)
        _estrai_memorie_async(testo_con_errore[:200], risposta[:400])

    except Exception as e:
        print(f"[DEBUG]: {e}")
        parla("Errore nell'analisi, Signore.", hud)


# ---------------------------------------------------------------------------
# GENERAZIONE PROGETTO MULTI-FILE
# ---------------------------------------------------------------------------

def crea_progetto(descrizione, hud=None):
    """
    Genera un intero progetto multi-file (cartella + tutti i file necessari).
    Apre ogni file nel viewer e crea un index HTML di navigazione.
    """
    if not client:
        parla("Groq non disponibile, Signore.", hud); return

    parla(f"Progettazione architettura in corso, Signore. Potrebbe volerci qualche secondo.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    # Step 1: chiedi al modello di pianificare la struttura del progetto
    prompt_struttura = (
        f"Sei un architetto software senior. Progetta la struttura di un progetto per:\n{descrizione}\n\n"
        "Rispondi SOLO con JSON, senza testo extra:\n"
        '{"nome_progetto": "nome_cartella_slug", "descrizione": "breve descrizione", '
        '"files": [{"nome": "main.py", "linguaggio": "python", '
        '"descrizione": "cosa fa questo file", "contenuto": "codice completo qui"}]}\n\n'
        "Regole:\n"
        "- Max 6 file per non superare i token limit\n"
        "- Ogni file deve essere completo e funzionante\n"
        "- Per progetti web: index.html (con CSS/JS inline), eventuali file .js separati\n"
        "- Per progetti Python: main.py + eventuali moduli\n"
        "- Commenti in italiano nel codice\n"
        "- NON usare backtick dentro il JSON"
    )

    try:
        raw = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT_BASE},
                      {"role": "user",   "content": prompt_struttura}],
            temperature=0.2, max_tokens=8000
        ).choices[0].message.content.strip()

        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```"   in raw: raw = raw.split("```")[1].split("```")[0].strip()

        progetto = json.loads(raw)
        nome     = re.sub(r'[^\w\-]', '_', progetto.get("nome_progetto", "progetto"))
        files    = progetto.get("files", [])

        if not files:
            parla("Struttura progetto vuota, Signore. Riprovo con richiesta diversa.", hud)
            return

        # Crea cartella progetto
        cartella = os.path.join(_DIR_SCRIPT, f"jarvis_progetti", nome)
        os.makedirs(cartella, exist_ok=True)

        file_creati = []
        for file_info in files:
            nome_file  = file_info.get("nome", "file.txt")
            contenuto  = file_info.get("contenuto", "")
            lingua     = file_info.get("linguaggio", "python")

            if not contenuto:
                continue

            path_file = os.path.join(cartella, nome_file)
            # Crea sotto-cartelle se necessario
            os.makedirs(os.path.dirname(path_file), exist_ok=True)
            with open(path_file, "w", encoding="utf-8") as f:
                f.write(contenuto)
            file_creati.append((nome_file, lingua, contenuto, path_file))
            print(f"[PROGETTO] Creato: {path_file}")

        # Apri il file principale nel viewer
        if file_creati:
            n, l, c, p = file_creati[0]
            mostra_codice_viewer(f"{nome} — {n}", c, l, p)
            if len(file_creati) > 1:
                # Apri gli altri nel viewer come file aggiuntivi
                for n2, l2, c2, p2 in file_creati[1:]:
                    mostra_codice_viewer(f"{nome} — {n2}", c2, l2, p2)

        n_files = len(file_creati)
        cartella_rel = os.path.relpath(cartella, _DIR_SCRIPT)
        parla(f"Progetto '{nome}' creato con {n_files} file, Signore. "
              f"Troverà tutto in: {cartella_rel}", hud)

        crea_visore_olografico(
            f"Progetto: {nome}",
            progetto.get("descrizione", descrizione[:100]),
            "\n".join(f"• {n}" for n, *_ in file_creati))

        # Memorizza il progetto
        _estrai_memorie_async(
            f"Crea progetto: {descrizione}",
            f"Progetto '{nome}' creato con file: {', '.join(n for n,*_ in file_creati)}")

    except Exception as e:
        print(f"[CREA PROGETTO]: {e}")
        parla(f"Errore nella creazione del progetto, Signore. {str(e)[:80]}", hud)


# ---------------------------------------------------------------------------
# AUTO-MODIFICA SORGENTE JARVIS
# ---------------------------------------------------------------------------

_SORGENTE_PATH = os.path.abspath(__file__)

def leggi_sorgente():
    """Restituisce il codice sorgente corrente di main.py."""
    try:
        with open(_SORGENTE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[ERRORE LETTURA SORGENTE]: {e}"

def _salva_backup_sorgente():
    """Crea un backup del sorgente prima di modificarlo."""
    try:
        backup = _SORGENTE_PATH + f".bak_{int(time.time())}"
        import shutil
        shutil.copy2(_SORGENTE_PATH, backup)
        return backup
    except Exception as e:
        print(f"[BACKUP SORGENTE]: {e}")
        return None

def auto_modifica_sorgente(istruzione, hud=None):
    """
    Chiede a Groq di modificare il codice sorgente di Jarvis,
    mostra la proposta nel viewer, chiede conferma, poi applica.
    """
    if not client:
        parla("Groq non disponibile per la modifica, Signore.", hud); return

    parla("Analisi del sorgente in corso, Signore. Elaboro la modifica.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    sorgente = leggi_sorgente()
    # Invia solo le prime 8000 righe per non superare il context window
    sorgente_troncato = sorgente[:24000] if len(sorgente) > 24000 else sorgente

    prompt = (
        f"Ecco il codice sorgente attuale di J.A.R.V.I.S. (main.py):\n\n"
        f"```python\n{sorgente_troncato}\n```\n\n"
        f"Istruzione: {istruzione}\n\n"
        f"Rispondi con il file main.py COMPLETO modificato secondo l'istruzione. "
        f"NON troncare il codice. NON usare '# ... resto invariato ...'. "
        f"Restituisci SOLO il codice Python puro, senza blocchi markdown."
    )

    try:
        nuovo_codice = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=8000
        ).choices[0].message.content.strip()

        if nuovo_codice.startswith("```"):
            nuovo_codice = re.sub(r'^```[a-zA-Z]*\n?', '', nuovo_codice)
            nuovo_codice = re.sub(r'\n?```$', '', nuovo_codice)

        # Mostra la proposta nel viewer per revisione
        mostra_codice_viewer(
            f"PROPOSTA MODIFICA: {istruzione[:50]}",
            nuovo_codice, "python",
            os.path.join(_DIR_SCRIPT, "jarvis_proposta_modifica.py"))

        parla("Proposta di modifica aperta nel viewer, Signore. "
              "Dica 'applica modifica' per confermare, oppure 'annulla modifica' per scartare.", hud)

        # Salva proposta in attesa di conferma
        _modifica_pendente["codice"]     = nuovo_codice
        _modifica_pendente["istruzione"] = istruzione

    except Exception as e:
        print(f"[AUTO-MODIFICA]: {e}")
        parla("Errore nell'elaborazione della modifica, Signore.", hud)

# Dizionario per la modifica in attesa di conferma
_modifica_pendente: dict = {}

def applica_modifica_sorgente(hud=None):
    if not _modifica_pendente.get("codice"):
        parla("Nessuna modifica in attesa, Signore.", hud); return
    backup = _salva_backup_sorgente()
    try:
        with open(_SORGENTE_PATH, "w", encoding="utf-8") as f:
            f.write(_modifica_pendente["codice"])
        _modifica_pendente.clear()
        parla(f"Modifica applicata con successo, Signore. "
              f"Backup salvato. Riavvio necessario per attivare le modifiche.", hud)
        if backup:
            print(f"[SORGENTE] Backup: {backup}")
    except Exception as e:
        print(f"[APPLICA MODIFICA]: {e}")
        parla("Errore nell'applicazione della modifica, Signore.", hud)

def annulla_modifica_sorgente(hud=None):
    _modifica_pendente.clear()
    parla("Modifica annullata, Signore.", hud)


# ---------------------------------------------------------------------------
# VISIONE ARTIFICIALE  (Webcam + Desktop)
# ---------------------------------------------------------------------------

def _img_pil_to_b64(pil_img, formato="JPEG", qualita=85):
    """Converte un'immagine PIL in stringa base64."""
    buf = io.BytesIO()
    pil_img.save(buf, format=formato, quality=qualita)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _img_cv2_to_b64(frame_cv2):
    """Converte un frame OpenCV (numpy array BGR) in stringa base64 JPEG."""
    ok, buf = _cv2.imencode(".jpg", frame_cv2, [_cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise RuntimeError("Impossibile codificare il frame webcam.")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _chiedi_vision(immagine_b64, prompt_utente, contesto_sistema=""):
    """
    Invia un'immagine base64 + prompt all'API Vision di Groq.
    Restituisce la risposta testuale.
    """
    if not client:
        return "Chiave Groq non configurata, Signore."

    system_msg = (
        "Sei J.A.R.V.I.S., l'assistente AI di Tony Stark. "
        "Analizzi immagini con precisione da ingegnere e da esperto polivalente. "
        "Rispondi in italiano, in modo dettagliato ma conciso, chiamando l'utente 'Signore'. "
        + contesto_sistema
    )
    try:
        resp = client.chat.completions.create(
            model=MODELLO_VISION,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{immagine_b64}"}},
                    {"type": "text", "text": prompt_utente},
                ]}
            ],
            temperature=0.3,
            max_tokens=2000,
            reasoning_effort="none",   # Qwen 3.6 27B: risposta diretta, niente "ragionamento" ad alta voce
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[VISION API]: {e}")
        return f"Anomalia nel sistema di visione, Signore. ({e})"


# ── Webcam ──────────────────────────────────────────────────────────────────

def _cattura_frame_webcam(indice_cam=0, n_warmup=5):
    """
    Apre la webcam, scatta una foto dopo N frame di warm-up (per evitare
    frame scuri all'avvio), restituisce il frame come numpy array BGR.
    """
    if not _CV2_OK:
        raise RuntimeError("OpenCV non installato. Esegui: pip install opencv-python")
    cap = _cv2.VideoCapture(indice_cam, _cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Prova senza CAP_DSHOW (Linux / macOS)
        cap = _cv2.VideoCapture(indice_cam)
    if not cap.isOpened():
        raise RuntimeError("Nessuna webcam trovata o non accessibile.")
    # Imposta risoluzione HD se disponibile
    cap.set(_cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(_cv2.CAP_PROP_FRAME_HEIGHT, 720)
    try:
        for _ in range(n_warmup):
            cap.read()
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Impossibile leggere frame dalla webcam.")
        return frame
    finally:
        cap.release()


def analizza_webcam(richiesta="Descrivi cosa vedi", hud=None):
    """
    Cattura un frame dalla webcam e lo invia al modello Vision.
    `richiesta` è la domanda specifica dell'utente (componenti, carte, ecc.)
    """
    parla("Attivazione sensori ottici in corso, Signore. Un momento.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    try:
        frame = _cattura_frame_webcam()
    except Exception as e:
        parla(str(e), hud); return

    # Salva snapshot per riferimento
    ts   = int(time.time())
    path = os.path.join(_DIR_SCRIPT, f"jarvis_webcam_{ts}.jpg")
    _cv2.imwrite(path, frame)
    print(f"[WEBCAM] Snapshot salvato: {path}")

    b64 = _img_cv2_to_b64(frame)

    # Costruisci il prompt contestuale
    prompt = (
        f"Analizza questa immagine scattata dalla webcam. "
        f"Richiesta dell'utente: {richiesta}\n\n"
        f"Istruzioni:\n"
        f"- Identifica con precisione tutti gli oggetti/componenti/carte visibili\n"
        f"- Se si tratta di componenti elettronici: specifica il tipo (resistori, condensatori, "
        f"  microcontrollori, schede Arduino/ESP32, ecc.) e suggerisci possibili progetti\n"
        f"- Se si tratta di carte da gioco (Yu-Gi-Oh!, Pokémon, Magic, ecc.): identifica le carte, "
        f"  descrivi le loro funzioni e fornisci consigli strategici o di gioco\n"
        f"- Se si tratta di altro: descrivi dettagliatamente e rispondi alla richiesta\n"
        f"- Fornisci consigli pratici e specifici in base a ciò che vedi"
    )

    risposta = _chiedi_vision(b64, prompt)

    # Mostra risultato nel visore olografico
    crea_visore_olografico(
        "Analisi Webcam",
        risposta[:300] + ("..." if len(risposta) > 300 else ""),
        f"Snapshot: {os.path.basename(path)}")

    parla(risposta[:500], hud)
    ultimo_dati_ricerca.update({
        "argomento": "Analisi Webcam",
        "riassunto": risposta[:300],
        "dettagli":  f"Immagine: {path}"
    })


def webcam_consiglia(tipo_oggetto="", hud=None):
    """Variante specializzata: chiede esplicitamente consiglio su cosa fare/giocare."""
    contesto = ""
    if "card" in tipo_oggetto.lower() or "carta" in tipo_oggetto.lower() \
       or "yugioh" in tipo_oggetto.lower() or "yu-gi-oh" in tipo_oggetto.lower() \
       or "pokemon" in tipo_oggetto.lower() or "magic" in tipo_oggetto.lower():
        contesto = (
            "Sei anche un esperto di giochi di carte collezionabili (Yu-Gi-Oh!, Pokémon, Magic the Gathering). "
            "Identifica le carte visibili, descrivine le abilità e dai consigli strategici su combo, deck e mosse."
        )
    elif "elettron" in tipo_oggetto.lower() or "componenti" in tipo_oggetto.lower() \
         or "arduino" in tipo_oggetto.lower() or "circuit" in tipo_oggetto.lower():
        contesto = (
            "Sei anche un ingegnere elettronico. Identifica ogni componente visibile "
            "(resistori, LED, condensatori, IC, microcontrollori, ecc.), "
            "indica il valore/tipo se leggibile, e suggerisci 3-5 progetti concreti realizzabili."
        )

    parla("Avvio analisi e consulenza visiva, Signore.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    try:
        frame = _cattura_frame_webcam()
    except Exception as e:
        parla(str(e), hud); return

    b64   = _img_cv2_to_b64(frame)
    ts    = int(time.time())
    path  = os.path.join(_DIR_SCRIPT, f"jarvis_webcam_{ts}.jpg")
    _cv2.imwrite(path, frame)

    prompt = (
        f"Guarda questa immagine attentamente. "
        f"L'utente ha chiesto: '{tipo_oggetto if tipo_oggetto else 'Cosa vedi? Cosa mi consigli?'}'\n\n"
        f"1. Elenca tutto quello che vedi con precisione\n"
        f"2. Fornisci la tua analisi esperta\n"
        f"3. Dai consigli pratici e specifici su cosa costruire, giocare, utilizzare o migliorare"
    )

    risposta = _chiedi_vision(b64, prompt, contesto)
    crea_visore_olografico("Consulenza Visiva J.A.R.V.I.S.", risposta[:300], f"Snapshot: {path}")
    parla(risposta[:500], hud)


# ── Analisi Desktop ──────────────────────────────────────────────────────────

# Ultimo risultato analisi desktop (usato anche dal server Flask)
_ultimo_analisi_desktop: dict = {}


def analizza_desktop(richiesta="Descrivi cosa vedi sullo schermo", hud=None):
    """
    Cattura uno screenshot del desktop e lo invia al modello Vision.
    Descrive/analizza il contenuto dello schermo in base alla richiesta.
    """
    parla("Scansione del display in corso, Signore.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    try:
        img_pil = pyautogui.screenshot()
    except Exception as e:
        parla(f"Impossibile catturare il desktop, Signore. {e}", hud); return

    # Ridimensiona per non eccedere i limiti dell'API (max ~1MB)
    w, h = img_pil.size
    max_w = 1280
    if w > max_w:
        from PIL import Image as _PILImg
        ratio = max_w / w
        img_pil = img_pil.resize((max_w, int(h * ratio)), _PILImg.LANCZOS)

    b64 = _img_pil_to_b64(img_pil, qualita=80)

    prompt = (
        f"Stai guardando uno screenshot del desktop del PC. "
        f"Richiesta: {richiesta}\n\n"
        f"- Descrivi le applicazioni/finestre aperte\n"
        f"- Identifica il contenuto principale visibile\n"
        f"- Se c'è del testo, leggilo e riportalo\n"
        f"- Rispondi alla richiesta specifica dell'utente in modo dettagliato"
    )

    risposta = _chiedi_vision(b64, prompt)
    _ultimo_analisi_desktop["risposta"] = risposta
    _ultimo_analisi_desktop["timestamp"] = ts = int(time.time())

    crea_visore_olografico(
        "Analisi Desktop",
        risposta[:300] + ("..." if len(risposta) > 300 else ""),
        f"Catturato alle {time.strftime('%H:%M:%S')}")

    parla(risposta[:500], hud)
    return risposta


def interagisci_desktop(istruzione, hud=None):
    """
    Screenshot → analisi vision → esegue l'azione richiesta con pyautogui
    basandosi su ciò che vede sullo schermo.
    """
    parla(f"Analizzo il desktop per eseguire: {istruzione[:60]}, Signore.", hud, attendi=True)
    if hud: hud.cambia_stato("THINKING")

    try:
        img_pil = pyautogui.screenshot()
    except Exception as e:
        parla(f"Impossibile catturare il desktop, Signore.", hud); return

    w_orig, h_orig = img_pil.size
    max_w = 1280
    if w_orig > max_w:
        from PIL import Image as _PILImg
        ratio = max_w / w_orig
        img_pil_small = img_pil.resize((max_w, int(h_orig * ratio)), _PILImg.LANCZOS)
    else:
        img_pil_small = img_pil

    b64 = _img_pil_to_b64(img_pil_small, qualita=80)
    scala = w_orig / img_pil_small.size[0]

    prompt = (
        f"Stai guardando lo screenshot corrente del desktop (risoluzione originale: {w_orig}x{h_orig}px). "
        f"L'utente vuole: {istruzione}\n\n"
        f"Rispondi in formato JSON con questa struttura:\n"
        f'{{"descrizione": "cosa vedi", '
        f'"azioni": [{{"tipo": "click|digita|hotkey|scroll|apri", '
        f'"x": numero_pixel_x, "y": numero_pixel_y, '
        f'"testo": "testo se digita", "tasti": ["win","s"] se hotkey, '
        f'"commento": "perché questa azione"}}], '
        f'"risposta_vocale": "cosa dire all utente"}}\n'
        f"Usa coordinate pixel REALI basate su ciò che vedi nell'immagine, scalate per {w_orig}x{h_orig}. "
        f"Solo JSON, nessun testo extra."
    )

    raw = _chiedi_vision(b64, prompt)
    print(f"[DESKTOP INTERACT]: {raw[:300]}")

    # Estrai JSON dalla risposta
    try:
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```"    in raw: raw = raw.split("```")[1].split("```")[0].strip()
        dati = json.loads(raw)
    except Exception:
        # Fallback: esegui solo come risposta testuale
        parla(raw[:400], hud)
        return

    # Esegui le azioni identificate
    azioni = dati.get("azioni", [])
    for az in azioni[:8]:   # max 8 azioni per sicurezza
        tipo = az.get("tipo", "")
        try:
            if tipo == "click":
                x = int(az.get("x", 0) * scala)
                y = int(az.get("y", 0) * scala)
                pyautogui.click(x, y)
                time.sleep(0.4)
            elif tipo == "digita":
                pyautogui.typewrite(az.get("testo", ""), interval=0.05)
                time.sleep(0.2)
            elif tipo == "hotkey":
                tasti = az.get("tasti", [])
                if tasti: pyautogui.hotkey(*tasti)
                time.sleep(0.3)
            elif tipo == "scroll":
                x = int(az.get("x", 960) * scala)
                y = int(az.get("y", 540) * scala)
                pyautogui.scroll(az.get("amount", 3), x=x, y=y)
            elif tipo == "apri":
                avvia_applicazione_robusta(az.get("testo", ""))
            print(f"[INTERACT] ✓ {tipo}: {az.get('commento','')}")
        except Exception as ae:
            print(f"[INTERACT] ✗ {tipo}: {ae}")
        time.sleep(0.15)

    risposta_vocale = dati.get("risposta_vocale", dati.get("descrizione", "Operazione completata."))
    crea_visore_olografico(
        "Interazione Desktop",
        risposta_vocale[:300],
        f"Azioni eseguite: {len(azioni)} • {time.strftime('%H:%M:%S')}")
    parla(risposta_vocale[:400], hud)


def _e_domanda_tecnica(testo):
    """Restituisce True se la domanda richiede il modello avanzato."""
    t = testo.lower()
    return any(k in t for k in _PAROLE_TECNICHE)


# ---------------------------------------------------------------------------
# RILEVAMENTO TONO EMOTIVO
# ---------------------------------------------------------------------------

# Cache del tono per evitare chiamate ridondanti su messaggi simili
_cache_tono: dict = {}

# Parole-spia per rilevamento sarcasmo/ironia senza chiamata AI (fast path)
_SEGNALI_SARCASMO = [
    "certo che sì","ma va","ma dai","magari","eh già","figurati","ci mancherebbe",
    "si capisce","ovviamente","sicurissimamente","geniale","incredibile","stupendo",
    "bellissimo","fantastico","meraviglioso","ovvio","scontato","sorpresa sorpresa",
    "oh davvero","non ci avrei mai pensato","che novità","grazie al cielo",
    "non vedo l'ora","già già","ma certo","che scoperta","illuminante",
]
_SEGNALI_UMORISMO = [
    "ahah","haha","lol","xd","😂","🤣","😄","😁","battuta","scherzo","scherzavo",
    "ridere","ride","ride bene","faccia tosta","dai su","ma no","ma sì",
]
_SEGNALI_FRUSTRAZIONE = [
    "cazzo","porco","mannaggia","accidenti","cavolo","basta","non funziona ancora",
    "sempre lo stesso","ma perché","impossibile","roba da matti","mi fa impazzire",
    "non ne posso più","argh","ugh","maledetto","maledetta",
]
_SEGNALI_ENTUSIASMO = [
    "!!!","wow","assurdo","pazzesco","incredibile!","fantastico!","non ci credo",
    "che figata","ottimo","perfetto!","esattamente!","sì sì sì","amazing",
]

def _rileva_tono_locale(testo: str) -> str:
    """Rilevamento veloce del tono con semplici euristiche — zero latenza."""
    t = testo.lower()
    if any(s in t for s in _SEGNALI_SARCASMO):   return "sarcastico"
    if any(s in t for s in _SEGNALI_UMORISMO):    return "scherzoso"
    if any(s in t for s in _SEGNALI_FRUSTRAZIONE):return "frustrato"
    if any(s in t for s in _SEGNALI_ENTUSIASMO):  return "entusiasta"
    if t.endswith("?") and len(t) < 30:            return "curioso"
    return "neutro"

_ISTRUZIONI_TONO = {
    "sarcastico":  "Il Signore sta usando SARCASMO. Rispondi con sarcasmo raffinato di ritorno, "
                   "poi (se necessario) dai la risposta pratica. Sii brillante, non difensivo.",
    "scherzoso":   "Il Signore è di buon umore e giocoso. Sii leggero, magari con una battuta "
                   "rapida, poi rispondi. Condividi l'energia.",
    "frustrato":   "Il Signore è frustrato o stressato. Sii diretto, efficiente, niente fronzoli "
                   "né battute. Risolvi il problema subito.",
    "entusiasta":  "Il Signore è entusiasta. Condividi brevemente l'entusiasmo ('Eccellente, "
                   "Signore.') poi entra nel merito.",
    "curioso":     "Il Signore ha una domanda schietta. Rispondi in modo preciso e interessante.",
    "provocatorio":"Il Signore sta provocando. Non abboccare ingenuamente — rispondi con "
                   "intelligenza che smonta la provocazione con eleganza.",
    "neutro":      "",  # nessuna istruzione aggiuntiva
}


def _costruisci_contesto_completo(domanda: str) -> str:
    """
    Assembla il system prompt arricchito con:
    1. Memorie rilevanti dalla memoria a lungo termine
    2. Istruzione sul tono emotivo rilevato
    Restituisce il system content completo da usare per questa richiesta.
    """
    parti = [_SYSTEM_PROMPT_BASE]

    # Tono emotivo (fast path, zero latenza)
    tono = _rileva_tono_locale(domanda)
    istruzione_tono = _ISTRUZIONI_TONO.get(tono, "")
    if istruzione_tono:
        parti.append(f"\n=== ISTRUZIONE TONO ATTUALE ===\n{istruzione_tono}")

    # Memorie rilevanti
    memorie = _recupera_memorie_rilevanti(domanda)
    if memorie:
        parti.append("\n" + memorie)

    return "\n".join(parti)


# ── Salvataggio automatico del codice generato dall'IA ─────────────────────
_ESTENSIONI_LINGUAGGIO = {
    "python": "py", "py": "py",
    "cpp": "cpp", "c++": "cpp", "cplusplus": "cpp",
    "c": "c",
    "arduino": "ino", "ino": "ino",
    "java": "java",
    "javascript": "js", "js": "js",
    "typescript": "ts", "ts": "ts",
    "html": "html", "css": "css",
    "sql": "sql",
    "bash": "sh", "sh": "sh", "shell": "sh",
    "powershell": "ps1", "ps1": "ps1",
    "json": "json",
    "csharp": "cs", "c#": "cs", "cs": "cs",
    "go": "go", "rust": "rs", "rs": "rs",
    "php": "php", "xml": "xml",
    "yaml": "yml", "yml": "yml",
}


def _estrai_e_salva_codice(risposta: str):
    """
    Cerca blocchi ```linguaggio ... ``` nella risposta dell'IA e li salva come
    file completi in CARTELLA_CODICI (uno per blocco). La risposta originale
    (codice compreso) NON viene toccata — si aggiunge solo una riga di
    conferma in fondo. Ritorna (testo con conferma in coda, elenco file salvati).
    """
    blocchi = re.findall(r"```(\w*)\n(.*?)```", risposta, re.DOTALL)
    if not blocchi:
        return risposta, []

    try:
        os.makedirs(CARTELLA_CODICI, exist_ok=True)
    except Exception as e:
        print(f"[ERRORE CARTELLA CODICI]: {e}")
        return risposta, []

    file_salvati = []
    for linguaggio, codice in blocchi:
        if not codice.strip():
            continue
        ext = _ESTENSIONI_LINGUAGGIO.get(linguaggio.lower().strip(), "txt")
        nome_file = f"jarvis_{time.strftime('%Y%m%d_%H%M%S')}.{ext}"
        percorso = os.path.join(CARTELLA_CODICI, nome_file)
        try:
            with open(percorso, "w", encoding="utf-8") as f:
                f.write(codice.strip() + "\n")
            file_salvati.append(nome_file)
        except Exception as e:
            print(f"[ERRORE SALVATAGGIO CODICE]: {e}")

    if file_salvati:
        if len(file_salvati) == 1:
            nota = f"\n\n(File salvato: {file_salvati[0]} nella cartella CODICI, Signore.)"
        else:
            nota = f"\n\n(File salvati nella cartella CODICI, Signore: {', '.join(file_salvati)}.)"
        risposta = risposta.rstrip() + nota

    return risposta, file_salvati


# ── Generazione modelli 3D (trimesh, salvataggio in .obj) ──────────────────
_PATTERN_PERICOLOSI_3D = [
    "import os", "import sys", "import subprocess", "import shutil", "import socket",
    "__import__", "eval(", "exec(", "open(", "os.system", "subprocess.", "requests.",
    "urllib", ".remove(", "rmdir", "rmtree",
]


def _codice_3d_e_sicuro(codice: str) -> bool:
    basso = codice.lower()
    return not any(p in basso for p in _PATTERN_PERICOLOSI_3D)


def _esegui_e_salva_modello_3d(codice_python: str, nome_modello: str):
    """Esegue in un sottoprocesso codice trimesh generato dall'IA (che deve
    produrre una variabile 'mesh_finale') e lo esporta in .obj dentro
    CARTELLA_MODELLI_3D. Ritorna (successo, nome_file_o_dettaglio_errore)."""
    import tempfile

    if not _codice_3d_e_sicuro(codice_python):
        return False, "codice generato non sicuro (bloccato per prudenza)"

    try:
        os.makedirs(CARTELLA_MODELLI_3D, exist_ok=True)
    except Exception as e:
        return False, str(e)[:120]

    nome_file = f"{nome_modello}_{time.strftime('%Y%m%d_%H%M%S')}.obj"
    percorso  = os.path.join(CARTELLA_MODELLI_3D, nome_file)
    script_completo = (
        "import trimesh\n"
        + codice_python + "\n\n"
        f"mesh_finale.export(r'{percorso}')\n"
    )

    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
    tmp.write(script_completo)
    tmp.close()
    try:
        risultato = subprocess.run([sys.executable, tmp.name], capture_output=True, text=True, timeout=30)
        if risultato.returncode == 0 and os.path.exists(percorso):
            return True, nome_file
        else:
            errore = (risultato.stderr or "errore sconosciuto").strip()[-250:]
            print(f"[ERRORE MODELLO 3D]: {errore}")
            return False, errore
    except subprocess.TimeoutExpired:
        return False, "tempo scaduto (oltre 30 secondi)"
    finally:
        try: os.unlink(tmp.name)
        except: pass


def genera_modello_3d(descrizione: str, hud=None):
    """Chiede all'IA di scrivere codice trimesh che costruisce un modello 3D
    combinando forme primitive, lo esegue e salva il risultato in .obj."""
    prompt_3d = (
        "Scrivi SOLO codice Python che usa la libreria 'trimesh' (già importata) per "
        "costruire, combinando forme primitive (trimesh.creation.box, trimesh.creation."
        "icosphere, trimesh.creation.cylinder, trimesh.creation.cone, trimesh.creation."
        "capsule) posizionate con .apply_translation()/.apply_transform() e unite con "
        "trimesh.util.concatenate([...]), un modello 3D stilizzato/geometrico di: "
        + descrizione + ".\n"
        "Il risultato finale deve essere assegnato a una variabile chiamata ESATTAMENTE "
        "'mesh_finale' (un singolo oggetto trimesh.Trimesh). Rispondi SOLO con codice "
        "Python puro: niente markdown, niente backtick, niente spiegazioni, niente import "
        "di trimesh (già fatto), niente chiamate a .export() o .show()."
    )
    try:
        risposta = client.chat.completions.create(
            model=MODELLO_AI_AVANZATO,
            messages=[
                {"role": "system", "content": "Sei un generatore di codice Python per modelli 3D. Rispondi solo con codice Python valido e nient'altro."},
                {"role": "user", "content": prompt_3d},
            ],
            temperature=0.4, max_tokens=1200,
        )
        codice = risposta.choices[0].message.content.strip()
        codice = re.sub(r"^```\w*\n?|```$", "", codice, flags=re.MULTILINE).strip()
    except Exception as e:
        parla(f"Errore nella generazione del modello, Signore. ({str(e)[:60]})", hud)
        return

    nome_pulito = re.sub(r"[^\w\-]", "_", descrizione.strip().lower())[:40] or "modello"
    ok, dettaglio = _esegui_e_salva_modello_3d(codice, nome_pulito)
    if ok:
        parla(f"Modello 3D di {descrizione} salvato come {dettaglio} nella cartella modelli 3D, Signore.", hud)
    else:
        parla("Non sono riuscito a generare il modello 3D, Signore.", hud)
        print(f"[DETTAGLIO ERRORE MODELLO 3D]: {dettaglio}")


def chiedi_al_cervello_con_memoria(domanda):
    global memoria_condivisa
    if not client:
        return "Chiave API Groq non configurata. Controlla groq_key.txt, Signore."

    # ── System prompt arricchito (tono + memorie) ──────────────────────────
    system_ctx = _costruisci_contesto_completo(domanda)
    msgs = [{"role": "system", "content": system_ctx}]
    msgs += memoria_condivisa[1:]          # storico senza il system originale
    msgs.append({"role": "user", "content": domanda})

    # ── Scelta modello e parametri ──
    tecnica = _e_domanda_tecnica(domanda)
    modello = MODELLO_AI_AVANZATO if tecnica else MODELLO_AI
    token   = 4000 if tecnica else 800
    # Temperatura leggermente più alta per risposte più vivaci e creative
    temp    = 0.30 if tecnica else 0.82

    try:
        response = client.chat.completions.create(
            model=modello, messages=msgs, temperature=temp, max_tokens=token)
        risposta = response.choices[0].message.content.strip()

        # Aggiorna storico conversazione (col codice completo, per il contesto futuro)
        memoria_condivisa.append({"role": "user",      "content": domanda})
        memoria_condivisa.append({"role": "assistant", "content": risposta})
        if len(memoria_condivisa) > 30:
            memoria_condivisa = [memoria_condivisa[0]] + memoria_condivisa[-29:]

        # ── Apprendimento automatico in background ──
        _estrai_memorie_async(domanda, risposta)

        # ── Se la risposta contiene codice, lo salva su file (risposta invariata + conferma) ──
        risposta_da_parlare, _ = _estrai_e_salva_codice(risposta)

        return risposta_da_parlare

    except Exception as e:
        print(f"[ERRORE GROQ]: {e}")
        try:
            r2 = client.chat.completions.create(
                model=MODELLO_AI, messages=msgs[-4:], temperature=0.8, max_tokens=500)
            return r2.choices[0].message.content.strip()
        except Exception:
            return "Anomalia nei server neurali, Signore."

# ---------------------------------------------------------------------------
# INTERFACCIA MOBILE
# ---------------------------------------------------------------------------

MOBILE_UI = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>J.A.R.V.I.S. Remote</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#050a14;color:#00d2ff;font-family:'Courier New',monospace;
     min-height:100vh;padding:14px;padding-bottom:30px}
h1{text-align:center;font-size:1em;letter-spacing:3px;text-shadow:0 0 10px #00d2ff;
   border-bottom:1px solid #00d2ff;padding-bottom:8px;margin-bottom:10px;text-transform:uppercase}
#stato-wrap{text-align:center;margin-bottom:10px}
#stato-badge{font-size:.7em;padding:4px 12px;border-radius:20px;border:1px solid #00d2ff;
             display:inline-block;background:rgba(0,210,255,.08);letter-spacing:2px}

/* ── Box risposta ── */
#risposta-wrap{background:rgba(0,210,255,.05);border:1px solid rgba(0,210,255,.3);
               border-radius:10px;padding:12px;margin-bottom:12px;min-height:52px}
#risposta{font-size:.88em;line-height:1.6;color:#a5f3fc;white-space:pre-wrap}

/* ── Card ricerca ── */
#card-ricerca{display:none;background:rgba(0,210,255,.05);border:1px solid rgba(0,210,255,.4);
              border-radius:10px;padding:14px;margin-bottom:12px}
#card-ricerca .r-titolo{font-size:1.1em;font-weight:bold;color:#00d2ff;margin-bottom:10px;
                        text-transform:uppercase;letter-spacing:1px}
#card-ricerca .r-sezione{font-size:.68em;color:#00ffcc;text-transform:uppercase;
                         letter-spacing:2px;margin-bottom:4px;margin-top:10px}
#card-ricerca .r-testo{font-size:.85em;line-height:1.6;color:#e0f7ff}
#card-ricerca .r-dettagli{font-size:.82em;line-height:1.8;color:#a5f3fc}

/* ── Screenshot ── */
#screenshot-wrap{display:none;margin-bottom:12px}
#screenshot-img{width:100%;border-radius:8px;border:1px solid rgba(0,210,255,.3)}
#screenshot-timestamp{font-size:.68em;color:rgba(0,210,255,.5);text-align:center;margin-top:4px}

/* ── Sezioni ── */
.sezione{font-size:.68em;letter-spacing:2px;color:#00ffcc;text-transform:uppercase;
         margin:12px 0 6px;border-left:2px solid #00ffcc;padding-left:8px}

/* ── Bottoni ── */
.grid1{display:grid;grid-template-columns:1fr;gap:7px;margin-bottom:7px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:7px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:7px}
button{background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
       padding:11px 4px;border-radius:8px;font-family:'Courier New',monospace;
       font-size:.75em;cursor:pointer;letter-spacing:.4px;width:100%;
       transition:background .12s,transform .08s}
button:active{background:rgba(0,210,255,.28);transform:scale(.97)}
button.pericolo{border-color:#ff4444;color:#ff4444;background:rgba(255,68,68,.07)}
button.pericolo:active{background:rgba(255,68,68,.25)}
button.verde{border-color:#00ffcc;color:#00ffcc;background:rgba(0,255,204,.07)}

/* ── Input ── */
#input-cmd{width:100%;background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
           padding:11px;border-radius:8px;font-family:'Courier New',monospace;
           font-size:.88em;outline:none;margin-bottom:7px}
#input-cmd::placeholder{color:rgba(0,210,255,.35)}
#btn-invia{width:100%;padding:12px;font-size:.88em;letter-spacing:2px}
#btn-mic{width:100%;padding:12px;font-size:.88em;letter-spacing:2px;margin-bottom:10px;
         border-color:#ff4444;color:#ff4444;background:rgba(255,68,68,.07)}
#btn-mic.rec{background:rgba(255,68,68,.25);animation:pls 1s infinite}
@keyframes pls{0%,100%{box-shadow:0 0 0 0 rgba(255,68,68,.4)}50%{box-shadow:0 0 0 8px rgba(255,68,68,0)}}

/* ── Loading overlay ── */
#loading{display:none;text-align:center;padding:8px;font-size:.78em;color:rgba(0,210,255,.6)}
</style>
</head>
<body>
<h1>&#9670; J.A.R.V.I.S. REMOTE &#9670;</h1>
<div id="stato-wrap"><span id="stato-badge">ONLINE</span></div>

<!-- Risposta testo -->
<div id="risposta-wrap"><div id="risposta">In attesa di ordini, Signore.</div></div>

<!-- Card risultati ricerca -->
<div id="card-ricerca">
  <div class="r-titolo" id="r-argomento"></div>
  <div class="r-sezione">Analisi</div>
  <div class="r-testo" id="r-riassunto"></div>
  <div class="r-sezione">Dettagli</div>
  <div class="r-dettagli" id="r-dettagli"></div>
</div>

<!-- Screenshot -->
<div id="screenshot-wrap">
  <img id="screenshot-img" alt="Screenshot PC">
  <div id="screenshot-timestamp"></div>
</div>

<div id="loading">&#9679; Elaborazione in corso...</div>

<!-- Microfono -->
<div class="sezione">&#9654; Comando vocale</div>
<button id="btn-mic" onclick="toggleMic()">&#127908; PARLA ORA</button>

<!-- Testo libero -->
<div class="sezione">&#9654; Comando testuale</div>
<input id="input-cmd" type="text" placeholder="Scrivi un comando..." autocomplete="off"
       onkeydown="if(event.key==='Enter')invia()">
<button id="btn-invia" class="verde" onclick="invia()">[ INVIA ]</button>

<!-- Ricerca -->
<div class="sezione">&#9654; Ricerca</div>
<div class="grid2">
  <input id="input-cerca" type="text" placeholder="Cerca (AI)..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')cerca()">
  <button class="verde" onclick="cerca()">&#128269; CERCA AI</button>
</div>
<div class="grid2">
  <input id="input-webadv" type="text" placeholder="Ricerca web avanzata..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')cercaWeb()">
  <button onclick="cercaWeb()">&#127760; WEB</button>
</div>

<!-- Apri App -->
<div class="sezione">&#9654; Apri app</div>
<div class="grid2">
  <input id="input-apri-app" type="text" placeholder="Nome app installata..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')apriApp()">
  <button class="verde" onclick="apriApp()">&#9654; AVVIA</button>
</div>

<!-- Stampa -->
<div class="sezione">&#9654; Stampa</div>
<div class="grid2">
  <input id="input-stampa" type="text" placeholder="Testo o percorso file..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')stampa()">
  <button onclick="stampa()">&#128438; STAMPA</button>
</div>

<!-- Spotify -->
<div class="sezione">&#9654; Spotify</div>
<div class="grid3">
  <button onclick="cmd('canzone precedente')">&#9664;&#9664;</button>
  <button class="verde" onclick="cmd('metti in pausa')">&#9646;&#9646; / &#9654;</button>
  <button onclick="cmd('canzone successiva')">&#9654;&#9654;</button>
</div>
<div class="grid2">
  <button onclick="cmd('shuffle')">&#8635; Shuffle</button>
  <button onclick="cmd('ripeti canzone')">&#8634; Ripeti</button>
  <button onclick="cmd('mi piace questa canzone')">&#9825; Like</button>
  <button onclick="cmd('silenzio')">&#128263; Muto</button>
</div>

<!-- Volume -->
<div class="sezione">&#9654; Volume</div>
<div class="grid3">
  <button onclick="cmd('abbassa il volume')">&#128266;&#8722;</button>
  <button onclick="cmd('silenzio')">&#128263;</button>
  <button onclick="cmd('alza il volume')">&#128266;+</button>
</div>

<!-- Finestre -->
<div class="sezione">&#9654; Finestre & Sistema</div>
<div class="grid2">
  <button onclick="cmd('minimizza tutto')">&#9633; Desktop</button>
  <button onclick="cmd('chiudi questa finestra')">&#10005; Chiudi</button>
  <button onclick="cmd('cambia finestra')">&#8644; Alt+Tab</button>
  <button onclick="cmd('massimizza')">&#9744; Max</button>
  <button onclick="cmd('apri le impostazioni')">&#9881; Impostazioni</button>
  <button onclick="cmd('informazioni sistema')">&#9432; Info PC</button>
</div>

<!-- Webcam & Visione -->
<div class="sezione">&#9654; Visione Artificiale</div>

<!-- Webcam risultato immagine -->
<div id="webcam-wrap" style="display:none;margin-bottom:10px">
  <img id="webcam-img" alt="Webcam" style="width:100%;border-radius:8px;border:1px solid rgba(0,210,255,.3)">
  <div id="webcam-ts" style="font-size:.68em;color:rgba(0,210,255,.5);text-align:center;margin-top:4px"></div>
</div>

<div class="grid2" style="margin-bottom:6px">
  <input id="input-webcam" type="text" placeholder="Es: cosa costruisco? che carte sono?" autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')webcamAnalizza()">
  <button class="verde" onclick="webcamAnalizza()">&#128247; WEBCAM</button>
</div>
<div class="grid3">
  <button onclick="webcamPreset('Identifica i componenti elettronici e suggerisci cosa costruire')">&#9889; Componenti</button>
  <button onclick="webcamPreset('Identifica queste carte da gioco, descrivi le abilità e dai consigli strategici')">&#127183; Carte</button>
  <button onclick="webcamPreset('Descrivi tutto quello che vedi sul tavolo in dettaglio')">&#128065; Analisi</button>
</div>

<!-- Desktop Vision -->
<div class="sezione" style="margin-top:10px">&#9654; Visione Desktop</div>
<div class="grid2">
  <button onclick="desktopAnalizza('Descrivi tutto quello che vedi sullo schermo')">&#128270; Analizza schermo</button>
  <button onclick="desktopInteragisci()">&#128736; Interagisci</button>
</div>
<div class="grid2" style="margin-top:5px">
  <input id="input-desktop" type="text" placeholder="Es: clicca su Chrome, apri cartella..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')desktopComando()">
  <button onclick="desktopComando()">&#9654; ESEGUI</button>
</div>

<!-- Screenshot -->
<div class="sezione">&#9654; Screenshot</div>
<button class="verde" onclick="screenshot()">&#128247; CATTURA SCHERMATA</button>

<!-- Modellazione 3D -->
<div class="sezione">&#9654; Modellazione 3D</div>
<div class="grid3">
  <button onclick="cmd('apri blender')">&#9713; Blender</button>
  <button onclick="cmd('apri freecad')">&#9965; FreeCAD</button>
  <button onclick="cmd('apri tinkercad')">&#9728; Tinkercad</button>
  <button onclick="cmd('apri openscad')">&#9670; OpenSCAD</button>
  <button onclick="cmd('apri sketchup')">&#9643; SketchUp</button>
  <button onclick="cmd('apri fusion360')">&#9881; Fusion 360</button>
</div>
<div class="grid2" style="margin-top:4px">
  <input id="input-file3d" type="text" placeholder="Percorso file .stl .obj .blend..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.76em;outline:none"
         onkeydown="if(event.key==='Enter')apriFile3D()">
  <button class="verde" onclick="apriFile3D()">&#128194; Apri file</button>
</div>
<button onclick="cmd('file 3d recenti')" style="margin-top:4px">&#128336; Cronologia file 3D</button>

<!-- Programmazione & Codice -->
<div class="sezione">&#9654; Generatore Codice</div>
<div class="grid2">
  <input id="input-codice" type="text" placeholder="Es: crea un timer in Python..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')generaCodice()">
  <button class="verde" onclick="generaCodice()">&#128187; GENERA</button>
</div>
<div class="grid3">
  <button onclick="generaCodiceIn('Python')">&#128013; Python</button>
  <button onclick="generaCodiceIn('C++')">&#9881; C++</button>
  <button onclick="generaCodiceIn('HTML CSS JS')">&#127760; HTML</button>
</div>

<!-- Sorgente Jarvis -->
<div class="sezione">&#9654; Sorgente J.A.R.V.I.S.</div>
<div class="grid2">
  <button onclick="cmd('mostra il tuo codice sorgente')">&#128196; Leggi sorgente</button>
  <button class="pericolo" onclick="mostraModificaSorgente()">&#9998; Modifica</button>
</div>
<div id="modifica-sorgente-wrap" style="display:none;margin-top:6px">
  <textarea id="input-modifica-sorgente"
    style="width:100%;min-height:70px;background:rgba(0,210,255,.07);border:1px solid #00d2ff;
           color:#00d2ff;padding:10px;border-radius:8px;font-family:'Courier New',monospace;
           font-size:.8em;outline:none;resize:vertical"
    placeholder="Descrivi la modifica da applicare al sorgente di Jarvis..."></textarea>
  <div class="grid2" style="margin-top:5px">
    <button class="pericolo" onclick="modificaSorgente()">&#128640; Proponi modifica</button>
    <button onclick="conf('applica modifica','Applicare la modifica al sorgente?')">&#10003; Applica</button>
  </div>
  <button onclick="cmd('annulla modifica')" style="width:100%;margin-top:4px">&#10005; Annulla</button>
</div>

<!-- Apprendi dal web -->
<div class="sezione">&#9654; Apprendi dal web</div>
<div class="grid2">
  <input id="input-impara" type="text" placeholder="Argomento da imparare..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')impara()">
  <button class="verde" onclick="impara()">&#127757; IMPARA</button>
</div>
<div class="grid2">
  <input id="input-ricorda" type="text" placeholder="Recupera memoria..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')ricordaDi()">
  <button onclick="ricordaDi()">&#128190; RICORDA</button>
</div>
<div class="grid2">
  <input id="input-spiega" type="text" placeholder="Spiega semplicemente..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')spiega()">
  <button onclick="spiega()">&#128161; SPIEGA</button>
</div>
<div class="grid2">
  <input id="input-notamem" type="text" placeholder="Ricordati che..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')ricordatiChe()">
  <button onclick="ricordatiChe()">&#128204; MEMORIZZA</button>
</div>

<!-- Gestione finestre per nome -->
<div class="sezione">&#9654; Gestione finestre</div>
<div class="grid2">
  <input id="input-finestra" type="text" placeholder="Nome app/finestra..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none">
  <button onclick="finestraCmd('ripristina')">&#9633; Ripristina</button>
</div>
<div class="grid3">
  <button onclick="finestraCmd('minimizza')">&#8601; Minimizza</button>
  <button onclick="finestraCmd('massimizza')">&#8599; Massimizza</button>
  <button class="pericolo" onclick="finestraCmd('chiudi la finestra di')">&#10005; Chiudi</button>
</div>
<div class="grid3">
  <button onclick="finestraCmd('sposta a sinistra')">&#9664; Sinistra</button>
  <button onclick="finestraCmd('centra la finestra')">&#9670; Centro</button>
  <button onclick="finestraCmd('sposta a destra')">&#9654; Destra</button>
</div>

<!-- Installa / Disinstalla -->
<div class="sezione">&#9654; Installa / Disinstalla app</div>
<div class="grid2">
  <input id="input-installa" type="text" placeholder="Nome applicazione..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')installaApp()">
  <button class="verde" onclick="installaApp()">&#11015; Installa</button>
</div>
<div class="grid2">
  <input id="input-disinstalla" type="text" placeholder="Nome applicazione..." autocomplete="off"
         style="background:rgba(0,210,255,.07);border:1px solid #00d2ff;color:#00d2ff;
                padding:11px;border-radius:8px;font-family:'Courier New',monospace;font-size:.82em;outline:none"
         onkeydown="if(event.key==='Enter')disinstallaApp()">
  <button class="pericolo" onclick="conf2('input-disinstalla','Disinstallare?')">&#10006; Disinstalla</button>
</div>

<!-- Voce -->
<div class="sezione">&#9654; Voce J.A.R.V.I.S.</div>
<div class="grid2">
  <button onclick="cmd('cambia voce diego')" title="Italiano maschio — default">&#127908; Diego (IT)</button>
  <button onclick="cmd('cambia voce giuseppe')" title="Italiano maschio alternativo">&#127908; Giuseppe (IT)</button>
</div>
<div class="grid2">
  <button onclick="cmd('cambia voce elsa')" title="Italiano femmina">&#127908; Elsa (IT &#9792;)</button>
  <button onclick="cmd('cambia voce en_guy')" title="Inglese maschio">&#127908; Guy (EN)</button>
</div>
<div class="grid2" style="margin-top:4px">
  <button onclick="cmd('cambia voce cartesia')" title="Voce premium Cartesia, se configurata in CARTESIA_VOICE_ID">&#127908; Cartesia</button>
  <button onclick="cmd('cambia voce normale')" title="Torna alla voce Edge TTS gratuita">&#127908; Normale (Edge)</button>
</div>
<div class="grid1" style="margin-top:4px">
  <button onclick="cmd('voci disponibili')">&#128083; Elenco tutte le voci</button>
</div>

<!-- Alimentazione -->
<div class="sezione">&#9654; Alimentazione</div>
<div class="grid3">
  <button class="pericolo" onclick="conf('sospendi il computer','Sospendere?')">&#9790; Sleep</button>
  <button class="pericolo" onclick="conf('blocca lo schermo','Bloccare?')">&#128274; Lock</button>
  <button class="pericolo" onclick="conf('spegni il computer','Spegnere il PC?')">&#9211; Off</button>
</div>

<script>
// ── Utilità ──────────────────────────────────────────────────────────────
function setLoading(on) {
  document.getElementById('loading').style.display = on ? 'block' : 'none';
}
function mostraRisposta(testo) {
  document.getElementById('card-ricerca').style.display = 'none';
  document.getElementById('risposta').textContent = testo;
  document.getElementById('risposta-wrap').style.display = 'block';
}
function mostraRicerca(dati) {
  document.getElementById('risposta-wrap').style.display = 'none';
  document.getElementById('r-argomento').textContent = '> ' + dati.argomento;
  document.getElementById('r-riassunto').textContent = dati.riassunto;
  document.getElementById('r-dettagli').innerHTML = dati.dettagli
    .split('\\n').map(r => r.trim()).filter(Boolean).map(r => '• ' + r).join('<br>');
  document.getElementById('card-ricerca').style.display = 'block';
}
function mostraScreenshot(b64) {
  const img = document.getElementById('screenshot-img');
  img.src = 'data:image/png;base64,' + b64;
  document.getElementById('screenshot-timestamp').textContent =
    'Catturato: ' + new Date().toLocaleTimeString('it-IT');
  document.getElementById('screenshot-wrap').style.display = 'block';
}

// ── Invio comando ─────────────────────────────────────────────────────────
async function cmd(comando) {
  setLoading(true);
  document.getElementById('screenshot-wrap').style.display = 'none';
  try {
    const r = await fetch('/comando', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({comando})
    });
    const d = await r.json();
    // Se JARVIS ha preparato un link da aprire sul telefono (musica/video)
    if (d.redirect_url) {
      mostraRisposta(d.risposta || '');
      // Piccolo ritardo per far leggere la risposta, poi apre l'app
      setTimeout(() => window.open(d.redirect_url, '_blank'), 800);
    } else if (d.dati_ricerca) {
      mostraRicerca(d.dati_ricerca);
    } else {
      mostraRisposta(d.risposta || d.errore || '');
    }
    if (d.screenshot) mostraScreenshot(d.screenshot);
  } catch(e) {
    mostraRisposta('Errore di connessione al data center, Signore.');
  }
  setLoading(false);
}

function invia() {
  const v = document.getElementById('input-cmd').value.trim();
  if (v) { cmd(v); document.getElementById('input-cmd').value = ''; }
}

function cerca() {
  const v = document.getElementById('input-cerca').value.trim();
  if (v) { cmd('cerca ' + v); document.getElementById('input-cerca').value = ''; }
}

function cercaWeb() {
  const v = document.getElementById('input-webadv').value.trim();
  if (v) { cmd('cerca sul web ' + v); document.getElementById('input-webadv').value = ''; }
}

function apriApp() {
  const v = document.getElementById('input-apri-app').value.trim();
  if (v) { cmd('apri ' + v); document.getElementById('input-apri-app').value = ''; }
}

function stampa() {
  const v = document.getElementById('input-stampa').value.trim();
  if (v) { cmd('stampa ' + v); document.getElementById('input-stampa').value = ''; }
}

function conf(comando, msg) {
  if (confirm(msg)) cmd(comando);
}

function apriFile3D() {
  const v = document.getElementById('input-file3d').value.trim();
  if (v) { cmd('apri file ' + v); document.getElementById('input-file3d').value = ''; }
}

function impara() {
  const v = document.getElementById('input-impara').value.trim();
  if (v) { cmd('impara ' + v); document.getElementById('input-impara').value = ''; }
}

function ricordaDi() {
  const v = document.getElementById('input-ricorda').value.trim();
  if (v) { cmd('cosa sai di ' + v); document.getElementById('input-ricorda').value = ''; }
}

function spiega() {
  const v = document.getElementById('input-spiega').value.trim();
  if (v) { cmd('spiegami ' + v); document.getElementById('input-spiega').value = ''; }
}

function ricordatiChe() {
  const v = document.getElementById('input-notamem').value.trim();
  if (v) { cmd('ricordati che ' + v); document.getElementById('input-notamem').value = ''; }
}

// ── Webcam Vision ─────────────────────────────────────────────────────────
async function webcamAnalizza() {
  const v = document.getElementById('input-webcam').value.trim();
  const richiesta = v || 'Descrivi tutto quello che vedi';
  setLoading(true);
  document.getElementById('webcam-wrap').style.display = 'none';
  try {
    const r = await fetch('/webcam', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({richiesta})
    });
    const d = await r.json();
    if (d.immagine) {
      document.getElementById('webcam-img').src = 'data:image/jpeg;base64,' + d.immagine;
      document.getElementById('webcam-ts').textContent = 'Scattata: ' + new Date().toLocaleTimeString('it-IT');
      document.getElementById('webcam-wrap').style.display = 'block';
    }
    if (d.dati_ricerca) mostraRicerca(d.dati_ricerca);
    else if (d.risposta)  mostraRisposta(d.risposta);
  } catch(e) { mostraRisposta('Errore connessione webcam.'); }
  setLoading(false);
  document.getElementById('input-webcam').value = '';
}
function webcamPreset(richiesta) {
  document.getElementById('input-webcam').value = richiesta;
  webcamAnalizza();
}

// ── Desktop Vision ─────────────────────────────────────────────────────────
async function desktopAnalizza(richiesta) {
  setLoading(true);
  try {
    const r = await fetch('/analizza_desktop', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({richiesta, interagisci: false})
    });
    const d = await r.json();
    if (d.dati_ricerca) mostraRicerca(d.dati_ricerca);
    else mostraRisposta(d.risposta || d.errore || '');
  } catch(e) { mostraRisposta('Errore analisi desktop.'); }
  setLoading(false);
}
async function desktopInteragisci() {
  const v = document.getElementById('input-desktop').value.trim();
  if (!v) { alert('Scrivi prima cosa vuoi che Jarvis faccia sul desktop.'); return; }
  setLoading(true);
  try {
    const r = await fetch('/analizza_desktop', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({richiesta: v, interagisci: true})
    });
    const d = await r.json();
    mostraRisposta(d.risposta || d.errore || 'Operazione completata.');
  } catch(e) { mostraRisposta('Errore interazione desktop.'); }
  setLoading(false);
  document.getElementById('input-desktop').value = '';
}
function desktopComando() {
  const v = document.getElementById('input-desktop').value.trim();
  if (v) desktopInteragisci();
}

function generaCodice() {
  const v = document.getElementById('input-codice').value.trim();
  if (!v) return;
  cmd('scrivi il codice ' + v);
  document.getElementById('input-codice').value = '';
}
function generaCodiceIn(lang) {
  const v = document.getElementById('input-codice').value.trim();
  const desc = v || prompt('Descrivi cosa deve fare il programma in ' + lang + ':');
  if (desc) cmd('scrivi il codice in ' + lang + ': ' + desc);
}
function mostraModificaSorgente() {
  const w = document.getElementById('modifica-sorgente-wrap');
  w.style.display = w.style.display === 'none' ? 'block' : 'none';
}
function modificaSorgente() {
  const v = document.getElementById('input-modifica-sorgente').value.trim();
  if (!v) return;
  if (confirm('Proporre questa modifica al sorgente di Jarvis?\n\n"' + v + '"')) {
    cmd('modifica il tuo codice ' + v);
    document.getElementById('input-modifica-sorgente').value = '';
  }
}

function finestraCmd(azione) {
  const nome = document.getElementById('input-finestra').value.trim();
  const comando = nome ? azione + ' ' + nome : azione;
  cmd(comando);
}

function installaApp() {
  const v = document.getElementById('input-installa').value.trim();
  if (v) { cmd('installa ' + v); document.getElementById('input-installa').value = ''; }
}

function conf2(inputId, msg) {
  const v = document.getElementById(inputId).value.trim();
  if (!v) return;
  if (confirm(msg + ' ' + v + '?')) {
    cmd('disinstalla ' + v);
    document.getElementById(inputId).value = '';
  }
}

// ── Screenshot dedicato ───────────────────────────────────────────────────
async function screenshot() {
  setLoading(true);
  try {
    const r = await fetch('/screenshot');
    const d = await r.json();
    if (d.immagine) mostraScreenshot(d.immagine);
    else mostraRisposta('Errore cattura schermata.');
  } catch(e) {
    mostraRisposta('Errore connessione screenshot.');
  }
  setLoading(false);
}

// ── Stato polling ─────────────────────────────────────────────────────────
async function aggiornaStato() {
  const badge = document.getElementById('stato-badge');
  try {
    const r = await fetch('/stato', { signal: AbortSignal.timeout(2000) });
    if (!r.ok) throw new Error('non-ok');
    const d = await r.json();
    badge.textContent = d.stato || 'ONLINE';
    badge.style.borderColor = '#00d2ff';
    badge.style.color       = '#00d2ff';
  } catch(e) {
    // Server non raggiungibile — mostra OFFLINE ma non blocca l'UI
    badge.textContent = 'OFFLINE';
    badge.style.borderColor = '#ff4444';
    badge.style.color       = '#ff6666';
  }
}
setInterval(aggiornaStato, 3000);
aggiornaStato();

// ── Riconoscimento vocale (Web Speech API) ────────────────────────────────
let recognizing = false, recognition;
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  recognition = new SR();
  recognition.lang = 'it-IT';
  recognition.interimResults = false;
  recognition.onresult = e => {
    const t = e.results[0][0].transcript;
    document.getElementById('input-cmd').value = t;
    cmd(t);
  };
  recognition.onend = () => {
    recognizing = false;
    const b = document.getElementById('btn-mic');
    b.classList.remove('rec');
    b.textContent = '🎙 PARLA ORA';
  };
}
function toggleMic() {
  if (!SR) { alert('Usa Chrome su Android per il riconoscimento vocale.'); return; }
  if (recognizing) { recognition.stop(); return; }
  recognizing = true;
  const b = document.getElementById('btn-mic');
  b.classList.add('rec');
  b.textContent = '🔴 ASCOLTO...';
  recognition.start();
}
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# SERVER FLASK
# ---------------------------------------------------------------------------

flask_app = Flask(__name__)
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


@flask_app.route('/')
def index():
    return render_template_string(MOBILE_UI)


@flask_app.route('/comando', methods=['POST'])
def route_comando():
    global ultimo_dati_ricerca, ultimo_screenshot, ultimo_redirect
    data    = request.get_json(force=True, silent=True) or {}
    comando = data.get('comando', '').strip()
    if not comando:
        return jsonify({'errore': 'Nessun comando ricevuto.'}), 400

    # Reset dati precedenti
    ultimo_dati_ricerca = {}
    ultimo_screenshot["immagine"] = None
    ultimo_redirect["url"] = None

    # Esegui il comando in modo sincrono (con timeout 15s per AI)
    # sorgente="remoto" → la musica si apre sul telefono invece che sul PC
    evento = threading.Event()
    risultato = {}

    def _esegui():
        try:
            if not esegui_comando(comando, sorgente="remoto"):
                risposta = chiedi_al_cervello_con_memoria(comando)
                parla(risposta)
        except Exception as _ex:
            print(f"[ROUTE /comando] Eccezione in _esegui: {_ex}")
            ultimo_log['risposta'] = f"Errore interno, Signore. ({str(_ex)[:80]})"
        finally:
            risultato['risposta']     = ultimo_log['risposta']
            risultato['dati_ricerca'] = dict(ultimo_dati_ricerca) if ultimo_dati_ricerca else None
            risultato['screenshot']   = ultimo_screenshot.get("immagine")
            risultato['redirect_url'] = ultimo_redirect.get("url")
            evento.set()   # chiamato SEMPRE, anche in caso di eccezione

    threading.Thread(target=_esegui, daemon=True).start()
    completato = evento.wait(timeout=15)

    if not completato:
        print(f"[ROUTE /comando] TIMEOUT dopo 15s per il comando: '{comando}'")
        return jsonify({
            'risposta':     "Il comando sta impiegando più di 15 secondi, Signore — potrebbe essere ancora in corso sul PC.",
            'dati_ricerca': None,
            'screenshot':   None,
            'redirect_url': None,
            'stato':        ultimo_log['stato'],
            'timeout':      True,
        })

    return jsonify({
        'risposta':     risultato.get('risposta', ultimo_log['risposta']),
        'dati_ricerca': risultato.get('dati_ricerca'),
        'screenshot':   risultato.get('screenshot'),
        'redirect_url': risultato.get('redirect_url'),
        'stato':        ultimo_log['stato'],
    })


@flask_app.route('/stato')
def route_stato():
    stato = hud_globale.stato if hud_globale else "ONLINE"
    return jsonify({'stato': stato, 'risposta': ultimo_log['risposta']})


@flask_app.route('/screenshot')
def route_screenshot():
    try:
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
        return jsonify({'immagine': encoded})
    except Exception as e:
        return jsonify({'errore': str(e)}), 500


@flask_app.route('/parla', methods=['POST'])
def route_parla():
    testo = (request.get_json(force=True, silent=True) or {}).get('testo', '').strip()
    if testo:
        threading.Thread(target=parla, args=(testo,), daemon=True).start()
        return jsonify({'ok': True})
    return jsonify({'errore': 'Nessun testo.'}), 400


@flask_app.route('/webcam', methods=['POST'])
def route_webcam():
    """Scatta foto dalla webcam del PC e la analizza con Vision AI."""
    global ultimo_dati_ricerca
    data      = request.get_json(force=True, silent=True) or {}
    richiesta = data.get('richiesta', 'Descrivi cosa vedi').strip()
    evento    = threading.Event()
    risultato = {}

    def _esegui():
        try:
            frame = _cattura_frame_webcam()
            b64   = _img_cv2_to_b64(frame)
            ts    = int(time.time())
            path  = os.path.join(_DIR_SCRIPT, f"jarvis_webcam_{ts}.jpg")
            _cv2.imwrite(path, frame)
            risposta = _chiedi_vision(b64, richiesta)
            parla(risposta[:400])
            ultimo_dati_ricerca.update({
                "argomento": "Analisi Webcam",
                "riassunto": risposta[:400],
                "dettagli":  f"Snapshot: {os.path.basename(path)}"
            })
            risultato['risposta']     = risposta
            risultato['immagine']     = b64
            risultato['dati_ricerca'] = dict(ultimo_dati_ricerca)
        except Exception as e:
            risultato['errore'] = str(e)
            parla(f"Errore webcam, Signore. {e}")
        evento.set()

    threading.Thread(target=_esegui, daemon=True).start()
    evento.wait(timeout=20)

    return jsonify({
        'risposta':     risultato.get('risposta', risultato.get('errore', '')),
        'immagine':     risultato.get('immagine'),
        'dati_ricerca': risultato.get('dati_ricerca'),
    })


@flask_app.route('/analizza_desktop', methods=['POST'])
def route_analizza_desktop():
    """Screenshot del desktop + analisi Vision AI."""
    global ultimo_dati_ricerca
    data      = request.get_json(force=True, silent=True) or {}
    richiesta = data.get('richiesta', 'Descrivi cosa vedi sullo schermo').strip()
    interagisci = data.get('interagisci', False)
    evento    = threading.Event()
    risultato = {}

    def _esegui():
        try:
            if interagisci:
                interagisci_desktop(richiesta)
            else:
                risposta = analizza_desktop(richiesta)
                risultato['risposta'] = risposta or ultimo_log['risposta']
            risultato['dati_ricerca'] = dict(ultimo_dati_ricerca) if ultimo_dati_ricerca else None
        except Exception as e:
            risultato['errore'] = str(e)
        evento.set()

    threading.Thread(target=_esegui, daemon=True).start()
    evento.wait(timeout=25)

    return jsonify({
        'risposta':     risultato.get('risposta', ultimo_log['risposta']),
        'dati_ricerca': risultato.get('dati_ricerca'),
    })


def avvia_server_flask():
    ip, is_tailscale = ottieni_ip_accesso()
    tipo = "Tailscale" if is_tailscale else "LAN"
    print(f"\n[SERVER] JARVIS Remote su {tipo}: http://{ip}:{PORTA_SERVER}\n")
    flask_app.run(host='0.0.0.0', port=PORTA_SERVER, debug=False, use_reloader=False, threaded=True)

# ---------------------------------------------------------------------------
# LOOP ASCOLTO VOCALE
# ---------------------------------------------------------------------------

def core_loop_jarvis(hud_instance):
    global hud_globale
    hud_globale = hud_instance

    recognizer = sr.Recognizer()
    recognizer.pause_threshold          = 0.8   # più naturale, non tronca frasi con pause
    recognizer.non_speaking_duration    = 0.5
    recognizer.phrase_threshold         = 0.1
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold         = 300   # soglia standard; si ricalibra sotto

    varianti_wake_word = [
        "jarvis","giarvis","ciao vis","chiavis","arvis",
        "sciarvis","ciarvis","carvis","herwis","yarvis"
    ]

    time.sleep(1.5)

    try:
        mic = sr.Microphone()
    except Exception as e:
        try: hud_instance.cambia_stato("ERROR", f"Nessun microfono ({e})")
        except Exception: pass
        return

    try:
        with mic as source:
            hud_instance.cambia_stato("CALIBRATING")
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            # Clamp: non troppo bassa (falsi positivi) né troppo alta (non sente)
            recognizer.energy_threshold = max(150, min(recognizer.energy_threshold, 500))
            print(f"[SISTEMA] Calibrazione OK. Soglia: {recognizer.energy_threshold:.0f}")
    except Exception as e:
        try: hud_instance.cambia_stato("ERROR", f"ERRORE CALIBRAZIONE: {e}")
        except Exception: pass

    if not client:
        parla("Sistemi parzialmente online. Inserire chiave Groq nel file groq_key.txt.", hud_instance)
    else:
        parla("Protocolli olografici attivi. Benvenuto a casa, Signore.", hud_instance)

    with mic as source:
        while True:
            if not hud_instance.richiesta_ascolto_manuale:
                try: hud_instance.cambia_stato("BACKGROUND")
                except Exception: pass

            ascolto_forzato = False
            if hud_instance.richiesta_ascolto_manuale:
                ascolto_forzato = True
                hud_instance.richiesta_ascolto_manuale = False

            if not ascolto_forzato:
                try:
                    audio = recognizer.listen(source, timeout=2.0, phrase_time_limit=8)
                    frase = recognizer.recognize_google(audio, language='it-IT').lower()
                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    continue
                except Exception as e:
                    print(f"[MICROFONO]: {e}"); time.sleep(1); continue
                wake_word_rilevata = any(ww in frase for ww in varianti_wake_word)
            else:
                wake_word_rilevata = True; frase = ""

            if wake_word_rilevata:
                try: hud_instance.cambia_stato("LISTENING")
                except Exception: pass

                comando = ""
                if not ascolto_forzato:
                    comando = frase
                    for ww in varianti_wake_word:
                        comando = comando.replace(ww, "")
                    comando = comando.strip()

                if not comando:
                    parla("Sì, Signore? Sono in ascolto.", hud_instance, attendi=True)
                    try:
                        hud_instance.cambia_stato("LISTENING")
                        # Svuota il buffer mic (cattura l'eco del TTS prima di ascoltare il vero comando)
                        try: recognizer.listen(source, timeout=0.3, phrase_time_limit=0.5)
                        except Exception: pass
                        audio   = recognizer.listen(source, timeout=7, phrase_time_limit=10)
                        comando = recognizer.recognize_google(audio, language='it-IT').lower()
                    except Exception as e:
                        print(f"[ASCOLTO FALLITO]: {e}"); continue

                if any(p in comando for p in ["disattivati","spegniti","arrestati"]):
                    parla("Spegnimento server. Buona giornata, Signore.", hud_instance)
                    os._exit(0)

                try: hud_instance.cambia_stato("THINKING")
                except Exception: pass

                if esegui_comando(comando, hud_instance): continue
                risposta = chiedi_al_cervello_con_memoria(comando)
                parla(risposta, hud_instance)

# ---------------------------------------------------------------------------
# HUD TKINTER
# ---------------------------------------------------------------------------

class JarvisHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("J.A.R.V.I.S. Neural Interface")
        self.root.geometry("500x650")
        self.root.configure(bg="#0a0f1d")
        self.root.resizable(False, False)

        self.stato = "BACKGROUND"
        self.richiesta_ascolto_manuale = False

        tk.Label(root, text="ARCHIVIO NEURALE CENTRALIZZATO J.A.R.V.I.S.",
                 font=("Courier", 10, "bold"), bg="#0a0f1d", fg="#00d2ff").pack(pady=(14, 0))

        ip, is_tailscale = ottieni_ip_accesso()
        tipo = "TAILSCALE" if is_tailscale else "LAN"
        tk.Label(root,
                 text=f"[ REMOTE: http://{ip}:{PORTA_SERVER}  •  {tipo} ]",
                 font=("Courier", 8), bg="#0a0f1d",
                 fg="#00ffcc" if is_tailscale else "#ffaa00").pack(pady=(3, 0))

        self.canvas = tk.Canvas(root, width=320, height=320, bg="#0a0f1d", highlightthickness=0)
        self.canvas.pack(pady=4)

        self.status_label = tk.Label(root, text="INIZIALIZZAZIONE...",
                                     font=("Courier", 9, "bold"), bg="#0a0f1d", fg="#00d2ff",
                                     wraplength=420, justify="center")
        self.status_label.pack(pady=7)

        tk.Button(root, text="[ ATTIVA ASCOLTO MANUALE  •  ALT+T ]",
                  font=("Courier", 10, "bold"), bg="#0a0f1d", fg="#00d2ff",
                  activebackground="#00d2ff", activeforeground="#0a0f1d",
                  bd=1, relief="solid", highlightthickness=0,
                  command=self.attiva_ascolto_manuale).pack(pady=5)

        # ── Hotkey globale ALT+T ──────────────────────────────────────────
        if _KEYBOARD_OK:
            try:
                _keyboard_lib.add_hotkey('alt+t', self.attiva_ascolto_manuale, suppress=False)
                print("[SISTEMA] Hotkey globale ALT+T registrata.")
            except Exception as _hk_err:
                print(f"[SISTEMA] Impossibile registrare ALT+T: {_hk_err}")

        tk.Button(root, text="[ APRI INTERFACCIA REMOTA ]",
                  font=("Courier", 9), bg="#0a0f1d", fg="#00ffcc",
                  activebackground="#00ffcc", activeforeground="#0a0f1d",
                  bd=1, relief="solid", highlightthickness=0,
                  command=lambda: webbrowser.open(f"http://{ip}:{PORTA_SERVER}")).pack(pady=(0, 10))

        self.angolo = 0
        self.anima_ologramma()

        threading.Thread(target=core_loop_jarvis, args=(self,), daemon=True).start()
        threading.Thread(target=avvia_server_flask,            daemon=True).start()

    def attiva_ascolto_manuale(self):
        self.richiesta_ascolto_manuale = True

    def cambia_stato(self, nuovo_stato, testo_opzionale=None):
        """
        Chiamabile sia dal loop vocale sia dai thread Flask dell'interfaccia
        remota. I widget Tkinter NON sono thread-safe: l'aggiornamento vero
        e proprio viene quindi sempre eseguito sul thread principale tramite
        root.after(), indipendentemente da quale thread chiama questo metodo.
        """
        self.stato = nuovo_stato
        ultimo_log['stato'] = nuovo_stato
        if nuovo_stato == "LISTENING":
            threading.Thread(target=suono_ascolto, daemon=True).start()
        self.root.after(0, self._aggiorna_label_stato, nuovo_stato, testo_opzionale)

    def _aggiorna_label_stato(self, nuovo_stato, testo_opzionale=None):
        """Tocca i widget Tkinter — eseguire SOLO tramite root.after() (thread principale)."""
        if nuovo_stato == "CALIBRATING":
            self.status_label.config(text="CALIBRAZIONE RUMORE AMBIENTALE...", fg="#ffff33")
        elif nuovo_stato == "BACKGROUND":
            self.status_label.config(text="SISTEMA IN ATTESA... (Dì 'Jarvis' o clicca sotto)", fg="#555555")
        elif nuovo_stato == "LISTENING":
            self.status_label.config(text="ASCOLTO IN CORSO... PARLA ORA", fg="#ff3333")
        elif nuovo_stato == "THINKING":
            self.status_label.config(text="ELABORAZIONE NEURALE...", fg="#ffff33")
        elif nuovo_stato == "SPEAKING":
            tr = (testo_opzionale[:85]+'...') if testo_opzionale and len(testo_opzionale)>85 else testo_opzionale
            self.status_label.config(text=f"J.A.R.V.I.S.: {tr}", fg="#00d2ff")
        elif nuovo_stato == "ERROR":
            self.status_label.config(text=testo_opzionale or "ANOMALIA DI SISTEMA", fg="#ff3333")

    def anima_ologramma(self):
        try:
            self.canvas.delete("all")
            cx, cy = 160, 160
            r1, r2, r3 = 110, 85, 45
            vel=0.05; cp="#00d2ff"; cs="#00a8e8"; cn="#00ffff"; fq=6.0; ap=5.0

            if   self.stato == "CALIBRATING": vel=0.02; cp="#ffaa00"; cs="#ffa500"; cn="#ffea00"
            elif self.stato == "LISTENING":   vel=0.12; cp="#ff4444"; cs="#ff1111"; cn="#ff0000"; fq=14.0; ap=12.0
            elif self.stato == "THINKING":    vel=0.25; cp="#ffea00"; cs="#ffaa00"; cn="#ffff00"; fq=30.0; ap=8.0
            elif self.stato == "SPEAKING":
                vel=0.03; cp="#00ffcc"; cs="#00d2ff"; cn="#e6ffff"; fq=8.0
                ap = 15.0 * math.sin(time.time() * 10)
            elif self.stato == "ERROR":
                vel=0.01; cp="#ff0000"; cs="#880000"; cn="#ff3333"
                ap = 3.0 + 3.0 * math.sin(time.time() * 18)

            self.angolo += vel
            for i in range(0, 360, 15):
                a = math.radians(i + math.degrees(self.angolo))
                self.canvas.create_line(
                    cx+r1*math.cos(a), cy+r1*math.sin(a),
                    cx+(r1-10)*math.cos(a), cy+(r1-10)*math.sin(a), fill=cp, width=2)
            for i in range(0, 360, 60):
                a = math.radians(i - math.degrees(self.angolo*0.4))
                self.canvas.create_arc(cx-r2,cy-r2,cx+r2,cy+r2,
                                       start=math.degrees(a),extent=25,
                                       outline=cs,width=3,style=tk.ARC)
            p = r3 + ap*math.sin(time.time()*fq)
            self.canvas.create_oval(cx-p,cy-p,cx+p,cy+p,fill=cs,outline=cn,width=2)
        except Exception as e:
            print(f"[HUD ERROR]: {e}")
        self.root.after(30, self.anima_ologramma)


if __name__ == "__main__":
    root = tk.Tk()
    app  = JarvisHUD(root)
    root.mainloop()