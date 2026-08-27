import sys
import time
import serial
import serial.tools.list_ports

# Configurazione della porta seriale
BAUD_RATE = 9600
TIMEOUT = 2  # secondi

def trova_arduino():
    """Cerca tra le porte disponibili quella a cui è collegato l'Arduino."""
    porte = serial.tools.list_ports.comports()
    for p in porte:
        if "Arduino" in p.description or "CH340" in p.description:
            return p.device
    return None

def apri_porta(serial_port):
    """
    Invia il comando all'Arduino per aprire la porta.
    Si assume che l'Arduino interpreti il carattere 'O' come "Open".
    """
    try:
        serial_port.write(b'O')
        # Attende conferma (opzionale)
        risposta = serial_port.readline().decode().strip()
        if risposta == "OK":
            print("Porta aperta con successo.")
        else:
            print(f"Risposta inattesa dall'Arduino: {risposta}")
    except serial.SerialException as e:
        print(f"Errore durante l'invio del comando: {e}")

def main():
    porta = trova_arduino()
    if not porta:
        print("Impossibile trovare una porta Arduino collegata.")
        sys.exit(1)

    try:
        with serial.Serial(porta, BAUD_RATE, timeout=TIMEOUT) as ser:
            # Attende che l'Arduino sia pronto
            time.sleep(2)
            apri_porta(ser)
    except serial.SerialException as e:
        print(f"Impossibile aprire la porta seriale {porta}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterruzione da tastiera, chiusura in corso.")
        sys.exit(0)

if __name__ == "__main__":
    main()