# Meeting-Agenda, 30 Min

## 1. Aktueller Evaluationsstand, 5 Min

- Flows **01-13** wurden bereits getestet, brauchen aber teilweise noch Review und Label-Feinschliff.
- Flows **01-10** sind aktuell die verlaesslichste Hauptbasis mit **201 manuell geprueften Items**.
- Die manuelle Pruefung ist aufwendig, weil jedes Requirement mit Evidence und Labeldefinition abgeglichen werden muss.

## 2. Wichtigste Ergebnisse, 7 Min

- **One-Prompt Gemini 3.1 Pro:** `81.1%`
- **One-Prompt Gemini Flash Lite:** `76.1%`
- **Batched Top-k Gemini Flash Lite:** `75.1%`
- One-Prompt ist aktuell am staerksten.
- Batched Top-k liegt nah dran und ist als Pipeline-Strategie besser kontrollierbar.

## 3. Aktuelle Bottlenecks, 7 Min

- **Top-k Retrieval:** verpasst teils relevante spaete Screens, z.B. Cart, Checkout oder Result States.
- **Claim Decomposition:** kann Bedeutungen leicht verschieben und ist fuer UI-Verification nicht immer hilfreich.
- Fuer das **PURE-Dataset** kann Claim Decomposition aber nuetzlich sein, weil Requirements dort oft laenger und zusammengesetzter sind.
- **Over-Fulfillment:** Modelle labeln zu oft `FULFILLED`, besonders bei Hidden-/Backend-, Result-, Persistence- oder Vergleichsclaims.

## 4. Hybrid Grouping als Optimierung, 5 Min

- Ziel: Top-k-Fokus behalten, aber Screenshots nicht unnoetig mehrfach hochladen.
- Claims werden nach ueberlappender Screenshot-Evidence gruppiert.
- Dadurch weniger doppelte Uploads und weniger wiederholte Prompt-Instruktionen.
- Moegliche Varianten:
  - kleinen Screenshot-Overlap erlauben
  - pro Gruppe einen Context-Screenshot hinzufuegen
  - bei dichten Flows eher One-Prompt, bei klar getrennten Flows gruppierte Prompts

## 5. Fehlende Instrumentierung, 2 Min

- Fuer finale Runs sollten Laufzeit, Retries/API-Fehler, Tokenverbrauch und Bildanzahl pro Call gespeichert werden.
- Das ist wichtig, um praktische Nutzbarkeit und Stabilitaet der Pipeline zu bewerten.

## 6. Naechste Schritte, 4 Min

- Review fuer Flows **01-13** weiter abschliessen.
- PURE-Dataset als naechsten Datenkontext einbeziehen, besonders fuer Claim Decomposition und Requirement-Struktur.
- Finale Konfigurationen einfrieren:
  - One-Prompt Flash Lite
  - One-Prompt staerkeres Modell
  - Batched Top-k
  - eventuell No-Claim-Decomposition
- Danach finale Tabellen, Fehleranalyse und qualitative Beispiele vorbereiten.
