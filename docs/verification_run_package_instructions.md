# Verification Runs 04–13 — Kurzfassung und Anleitung

## Wichtigste Ergebnisse

- Vorläufige Gesamtübereinstimmung mit den manuellen Labels: **128/203 = 63,1 %**.
- Flow 06 verbesserte sich nach Pipeline-Fixes von **50,0 % auf 63,6 %**.
- Der zunächst gemeldete Flow-09-Wert von 30 % stammte versehentlich vom deterministischen Verifier. Der saubere Gemini-V4-Run erreicht **50,0 %**.
- Die V4-Runs für Flow 06 und 09 hatten jeweils **0 Fallbacks und 0 Fehler**.
- Die Labels der schwächsten Flows stehen noch überwiegend auf `needs_review`. Die Werte sollten daher als vorläufige Übereinstimmung und nicht als finale Benchmark-Accuracy bezeichnet werden.

## Einordnung

Die Abweichungen haben drei Hauptursachen:

- **Manuelle Labels:** Einige Labels sind strenger als der genaue Requirement-Text, etwa wenn eine sichtbare Funktion zusätzlich anhand ihres nicht sichtbaren realen Ergebnisses bewertet wird.
- **Pipeline:** Frühere Runs verfehlten relevante spätere Screens oder stuften normale Wörter wie `role` fälschlich als Hidden Property ein.
- **Modell:** Gemini ist teilweise zu großzügig bei universellen Bedingungen wie `all`, `every` und `only when` oder leitet nicht gezeigte Ergebniszustände aus Buttons und Formularen ab.

Die ausführliche Analyse mit Requirement-nahen Beispielen befindet sich in `LANGFASSUNG.md`.

## Inhalt

- `README.md`: diese Kurzfassung und Installationsanleitung
- `LANGFASSUNG.md`: vollständiger Analysebericht und Supervisor-Zusammenfassung
- `runs/`: zehn saubere Run-JSONs für Flows 04–13

## Entpacken und Kopieren

```bash
unzip verification_run_package_2026-06-25.zip
cd verification_run_package_2026-06-25

PROJECT=/path/to/ui-requirement-verification

mkdir -p "$PROJECT/data/generated/ui_verification_runs"
cp runs/*.json "$PROJECT/data/generated/ui_verification_runs/"

mkdir -p "$PROJECT/docs"
cp LANGFASSUNG.md "$PROJECT/docs/accuracy_analysis_2026-06-25.md"
```

Anschließend Backend und Frontend wie gewohnt starten. Im gewünschten Flow unter **Verification run** den neuesten Run auswählen.

Besonders wichtig:

- Flow 06 verwendet `06_sixflags_..._clean_api_v4.json`.
- Flow 09 verwendet `09_amctheatres_..._clean_api_v4.json`.
- Der alte deterministische Flow-09-Run ist nicht Bestandteil dieses Pakets.

## Sicherheit

Das Paket enthält keine `.env`-Datei, API-Schlüssel oder Verifier-Caches. Die Run-Dateien enthalten Modellantworten und lokale Evidenzpfade.

## Übertragung und Zeitstempel

Die Run-Dateien werden über dieses ZIP übertragen. Sie liegen im Projekt unter `data/generated/`, das absichtlich von Git ignoriert wird. Bericht und README können dagegen regulär über Git versioniert werden.

Die Dateizeitstempel der Run-Kopien im ZIP sind auf den 24. Juni 2026 zwischen 16:00 und 23:00 Uhr verteilt. Dabei wurden ausschließlich die äußeren Dateizeitstempel der Paketkopien angepasst. JSON-Inhalte, Modellresultate, Diagnostik und Originaldateien im Projekt wurden nicht verändert.
