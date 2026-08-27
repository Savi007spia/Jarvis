// Sketch Arduino per aprire una porta tramite relè
// Compilare e caricare su Arduino (es. Uno, Mega, Nano)

#include <Arduino.h>

// Pin digitale collegato al relè (NC/NO)
const uint8_t PIN_RELE = 8;

// Stato della porta: false = chiusa, true = aperta
bool portaAperta = false;

// Funzione per aprire la porta
void apriPorta() {
    // Attiva il relè (assumendo logica HIGH attiva)
    digitalWrite(PIN_RELE, HIGH);
    portaAperta = true;
}

// Funzione per chiudere la porta
void chiudiPorta() {
    digitalWrite(PIN_RELE, LOW);
    portaAperta = false;
}

// Inizializzazione
void setup() {
    // Configura il pin del relè come uscita
    pinMode(PIN_RELE, OUTPUT);
    // Assicura che il relè sia spento all'avvio
    digitalWrite(PIN_RELE, LOW);
    // Avvia la comunicazione seriale per comandi di debug
    Serial.begin(9600);
    while (!Serial) { ; } // Attende apertura della console (solo su board con USB)
    Serial.println(F("Sistema di controllo porta pronto."));
}

// Loop principale
void loop() {
    // Controlla se sono arrivati comandi dalla seriale
    if (Serial.available() > 0) {
        String comando = Serial.readStringUntil('\n');
        comando.trim(); // Rimuove spazi bianchi

        if (comando.equalsIgnoreCase("APRI")) {
            if (!portaAperta) {
                apriPorta();
                Serial.println(F("Porta aperta."));
            } else {
                Serial.println(F("Porta già aperta."));
            }
        } else if (comando.equalsIgnoreCase("CHIUDI")) {
            if (portaAperta) {
                chiudiPorta();
                Serial.println(F("Porta chiusa."));
            } else {
                Serial.println(F("Porta già chiusa."));
            }
        } else {
            Serial.println(F("Comando non riconosciuto. Usa APri o CHIUDI."));
        }
    }

    // Eventuale logica aggiuntiva (es. timeout automatico)
    // Esempio: chiude la porta dopo 10 secondi se rimane aperta
    static unsigned long tempoApertura = 0;
    if (portaAperta && (millis() - tempoApertura >= 10000)) {
        chiudiPorta();
        Serial.println(F("Porta chiusa automaticamente dopo timeout."));
    }
    if (portaAperta && tempoApertura == 0) {
        tempoApertura = millis(); // registra il momento di apertura
    }
    if (!portaAperta) {
        tempoApertura = 0; // resetta il timer
    }
}