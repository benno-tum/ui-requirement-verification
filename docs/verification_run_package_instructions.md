# Verification Runs 01–13 — Übersicht und Anleitung

## Aktuelle Ergebnisse

| Flow | Übereinstimmung | Technischer Status |
|---|---:|---|
| 01 Six Flags | 16/23 = 69,6 % | Gemini; 16 Fallbacks wegen 503-Fehlern |
| 02 GameStop | 7/9 = 77,8 % | Gemini; 1 Fallback |
| 03 MBTA | 18/24 = 75,0 % | Gemini; keine Fallbacks |
| 04 Under Armour | 15/21 = 71,4 % | Gemini; keine Fallbacks |
| 05 Resy | 14/20 = 70,0 % | Gemini; keine Fallbacks |
| 06 Six Flags Careers | 14/22 = 63,6 % | Gemini V4; keine Fallbacks |
| 07 Discogs | 14/18 = 77,8 % | Gemini; keine Fallbacks |
| 08 Amtrak | 13/20 = 65,0 % | Gemini; 1 Fallback |
| 09 AMC Theatres | 10/20 = 50,0 % | Gemini V4; keine Fallbacks |
| 10 Six Flags Purchase | 13/25 = 52,0 % | Gemini V3; keine Fallbacks |
| 11 Carnival | 12/20 = 60,0 % | Gemini V3; keine Fallbacks |
| 12 Book Depository | 11/18 = 61,1 % | Gemini V3; keine Fallbacks |
| 13 Yellow Pages | 12/19 = 63,2 % | Gemini V3; keine Fallbacks |

Über alle 13 aktuellen Runs stimmen **169 von 259 Labels = 65,3 %** mit den derzeitigen manuellen Labels überein.

Die wichtigsten aktuellen Fehlerquellen sind:

- fehlende oder unpassende Evidenz-Screens;
- zu großzügige Modellentscheidungen bei `all`, `every`, `only when` und anderen universellen Aussagen;
- Ableitung nicht gezeigter Resultate aus Buttons oder Eingabeformularen;
- einzelne manuelle Labels, deren Strenge nicht exakt zum Requirement-Text passt.

Die ausführliche Analyse befindet sich in `LANGFASSUNG.md`.

## Inhalt

- `README.md`: aktuelle Ergebnisübersicht und Installationsanleitung
- `LANGFASSUNG.md`: ausführlicher Bericht für Flows 01–13
- `runs/`: 13 aktuelle Run-JSONs

## Entpacken und Kopieren

```bash
unzip verification_results_01-13.zip
cd verification_results_01-13

PROJECT=/path/to/ui-requirement-verification

mkdir -p "$PROJECT/data/generated/ui_verification_runs"
cp runs/*.json "$PROJECT/data/generated/ui_verification_runs/"

mkdir -p "$PROJECT/docs"
cp LANGFASSUNG.md "$PROJECT/docs/accuracy_analysis_2026-06-25.md"
```

Anschließend Backend und Frontend wie gewohnt starten. Im gewünschten Flow unter **Verification run** den neuesten Run auswählen.

## Übertragung und Sicherheit

Die Run-Dateien werden über dieses ZIP übertragen, da `data/generated/` im Repository absichtlich von Git ignoriert wird. Bericht und README können separat über Git versioniert werden.

Das Paket enthält keine `.env`-Datei, API-Schlüssel oder Verifier-Caches. Die Zeitstempel im ZIP kennzeichnen ausschließlich den Export des Pakets.
