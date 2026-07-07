# Aktueller Bericht zur UI-Verifikation — Flows 01–13

## Zusammenfassung

Der Bericht betrachtet ausschließlich den aktuellen Run pro Flow. Über alle 13 Flows stimmen **169 von 259 Vorhersagen = 65,3 %** mit den derzeitigen manuellen Labels überein.

Die Ergebnisse liegen zwischen **50,0 %** und **77,8 %**. Die Abweichungen entstehen hauptsächlich durch Evidenzauswahl, Modellinterpretation und einzelne diskussionswürdige manuelle Labels. Ein genereller Gemini-Ausfall ist in den aktuellen Runs nicht erkennbar. Technisch auffällig ist vor allem Flow 01 mit 16 Fallbacks aufgrund von 503-Fehlern.

## Aktuelle Ergebnisse

| Flow | Aktueller Run | Übereinstimmung | Fallbacks | Einordnung |
|---|---|---:|---:|---|
| 01 Six Flags | `01_sixflags_...json` | 16/23 = 69,6 % | 16 | Ergebnis technisch eingeschränkt |
| 02 GameStop | `02_gamestop_...json` | 7/9 = 77,8 % | 1 | Hohe Übereinstimmung, kleiner technischer Restfehler |
| 03 MBTA | `03_mbta_...json` | 18/24 = 75,0 % | 0 | Stabiler Run |
| 04 Under Armour | `04_underarmour_clean_api.json` | 15/21 = 71,4 % | 0 | Stabiler Run |
| 05 Resy | `05_resy_..._clean_api.json` | 14/20 = 70,0 % | 0 | Stabiler Run |
| 06 Six Flags Careers | `06_sixflags_..._clean_api_v4.json` | 14/22 = 63,6 % | 0 | Modell bei universellen Claims teilweise zu großzügig |
| 07 Discogs | `07_discogs_..._clean_api.json` | 14/18 = 77,8 % | 0 | Höchste aktuelle Übereinstimmung |
| 08 Amtrak | `08_amtrak_..._clean_api.json` | 13/20 = 65,0 % | 1 | Ein malformed-response-Fallback |
| 09 AMC Theatres | `09_amctheatres_..._clean_api_v4.json` | 10/20 = 50,0 % | 0 | Viele semantische Grenzfälle |
| 10 Six Flags Purchase | `10_sixflags_..._clean_api_v3.json` | 13/25 = 52,0 % | 0 | Relevante Cart-Screens wurden häufig nicht ausgewählt |
| 11 Carnival | `11_carnival_..._clean_api_v3.json` | 12/20 = 60,0 % | 0 | Nicht gezeigte Resultate wurden teilweise angenommen |
| 12 Book Depository | `12_bookdepository_..._clean_api_v3.json` | 11/18 = 61,1 % | 0 | Result-Screen- und Persistenz-Claims problematisch |
| 13 Yellow Pages | `13_yellowpages_..._clean_api_v3.json` | 12/19 = 63,2 % | 0 | Gemischte Modell- und Label-Strenge |

## Technische Qualität

### API und Fallbacks

- Flow 01 enthält 16 Fallbacks nach Gemini-503-Fehlern und sollte für eine belastbare finale Messung erneut ausgeführt werden.
- Flow 02 und Flow 08 enthalten jeweils einen Fallback.
- Die übrigen aktuellen Runs haben keine Fallbacks.
- Flow 06 und Flow 09 verwenden Gemini V4 mit null Fallbacks und null Fehlern.

### Evidenzauswahl

Die größte aktuelle Pipeline-Schwäche ist die Auswahl der Screenshots:

- Flow 10 enthält die entscheidende Cart- und Checkout-Evidenz in den Schritten 7–10.
- Mehrere Claims wurden nur anhand früher Screens bewertet und deshalb fälschlich als `MISSING`, `ABSTAIN` oder `PARTIALLY_FULFILLED` eingestuft.
- Zustandsänderungen, Cart-Claims, Result-States und Review-Schritte benötigen immer frühe und späte Screens.

### Modellverhalten

Gemini ist aktuell besonders fehleranfällig bei:

- universellen Bedingungen wie `all`, `every`, `only when`;
- negativen Aussagen und sichtbarer Abwesenheit eines UI-Elements;
- Vergleichen, wenn nur einer der beiden Zustände gezeigt wird;
- Resultaten, die aus einem Button oder Formular abgeleitet werden, obwohl kein Result-Screen sichtbar ist;
- zusammengesetzten Requirements, bei denen nur ein Teil erfüllt ist.

## Analyse der schwächsten aktuellen Flows

## Flow 09 — AMC Theatres, 50,0 %

Der Run ist technisch sauber. Die verbleibenden Fehler sind überwiegend semantisch.

### Wahrscheinlich zu strenge manuelle Labels

- `REQ-05`: Das Requirement fordert eine optionale Account-Verknüpfung. Die Checkbox ist sichtbar; eine tatsächlich abgeschlossene Verknüpfung wird im Wortlaut nicht verlangt. `FULFILLED` ist plausibel.
- `REQ-10`: Alternative Anfragekanäle werden sichtbar angeboten. Das Requirement verlangt die Bereitstellung der Kanäle, nicht den Nachweis ihrer externen Funktion. `FULFILLED` ist plausibel.

### Wahrscheinliche Modell- oder Pipelinefehler

- `REQ-09`: Das Formular und die Eingabe sind sichtbar, aber kein erfolgreicher Balance-Output. `PARTIALLY_FULFILLED` ist informativer als das vorhergesagte `ABSTAIN`.
- `CONTR-02`: Eine sichtbare Formatfehlermeldung beweist nicht, dass Formatfehler und unbekannte, aber formal gültige Karten unterschiedlich behandelt werden.
- `CONTR-03`: Ein Gastmodus und eine Account-Grenze werden nicht vergleichend gezeigt. `ABSTAIN` ist angemessen.
- `CONTR-04`: Sichtbare Links beweisen nicht die Vollständigkeit aller unterstützten Pfade und Hilferessourcen.
- `CONTR-05`: Die Eingabefelder sind kein separater Result-State. Das manuelle `NOT_FULFILLED` ist plausibel.
- `CONTR-06`: Eine Fehlermeldung allein beweist nicht, dass die Lookup-Aktion ihren Submittability-Zustand klar sichtbar widerspiegelt.

## Flow 10 — Six Flags Purchase, 52,0 %

Die manuellen Labels wirken größtenteils plausibel. Der Hauptfehler liegt in der Evidenzauswahl.

- `REQ-09`: Schritte 8 und 9 zeigen eine Mengenänderung.
- `REQ-12`: Schritt 10 zeigt die gewählte Add-on-Menge im Cart.
- `REQ-13`: Schritt 10 kombiniert Ticket und Add-on.
- `REQ-15`: Schritt 10 zeigt Subtotal, Processing Fee, Tax und Total.
- `REQ-16`: Schritt 10 enthält eine `Modify Cart`-Aktion vor Checkout.
- `REQ-17`: Schritt 10 trennt Marketingzustimmung und Kaufbestätigung.
- `REQ-18`: High Contrast Mode ist im Purchase Flow sichtbar.
- `CONTR-05`: Der sichtbare Pre-Checkout-State enthält keine Kontrolle für die Fulfillment-Methode; `NOT_FULFILLED` ist plausibel.

Für diesen Flow sollte die Pipeline bei Cart-, Checkout- und Summary-Claims den letzten Screen zwingend berücksichtigen.

## Flow 11 — Carnival, 60,0 %

Hier sind die manuellen Labels bei den meisten Abweichungen überzeugender:

- `REQ-13`: Kein Result-Screen ist sichtbar; Suchresultate dürfen nicht aus dem Search-Button abgeleitet werden.
- `REQ-14`: Die tatsächliche Searchability oder Availability von Optionen ist nicht aus Dropdowns beweisbar.
- `CONTR-01`: Ein Verlassen und späteres Zurückkehren wird nicht gezeigt.
- `CONTR-03`: Vollständigkeit aller passenden Cruises ist nicht überprüfbar.
- `CONTR-04`: Ein anonymer Vergleichszustand fehlt.
- `CONTR-05`: Inline-Suchfelder sind kein dediziertes Review-Panel.
- `CONTR-06`: Sichtbar sind nur breite Duration-Bands, keine exakte Tageszahl.

## Flow 12 — Book Depository, 61,1 %

- `REQ-09`: Der Flow endet beim Advanced-Search-Formular; gefilterte Resultate sind nicht sichtbar. `PARTIALLY_FULFILLED` ist plausibel.
- `REQ-10`: Globale Header-Controls bleiben über alle Screens erhalten. Das manuelle `FULFILLED` ist plausibel.
- `REQ-11`: Sprach- und Währungsauswahl sind sichtbar; `FULFILLED` ist plausibel.
- `CONTR-01`: Eine Rückkehr von einer Result-Seite wird nicht gezeigt.
- `CONTR-03/04`: Korrektheit und Vollständigkeit von Resultaten sind ohne Result-Screen nicht bewertbar.
- `CONTR-06`: Da der geforderte Result-Screen selbst fehlt, ist `ABSTAIN` sicherer als eine negative Behauptung.

## Flow 06 — Six Flags Careers, 63,6 %

### Mögliche Labelkorrekturen

- `REQ-12`: Gefordert ist die sichtbare Kommunikation von Benefits. Diese ist vorhanden; `FULFILLED` passt besser als eine Bewertung der realen Gültigkeit der Benefits.
- `REQ-11`: „Can be launched“ kann bereits durch eine opening-spezifische `Apply now`-Aktion erfüllt sein.
- `CONTR-02`: Ein sichtbarer Handoff über eine dedizierte Jobseite und `Apply now` kann für `FULFILLED` genügen.

### Modellprobleme

- `CONTR-03`: Ein getesteter Team-Pfad beweist nicht `every visible team area`.
- `CONTR-04`: `Now Hiring` und `Apply now` beweisen nicht, dass die Stelle tatsächlich noch aktiv ist.
- `CONTR-06`: Statische Kategorie-Karten sind keine direkten In-Page-Filter.

## Bewertung der manuellen Labels

Die manuellen Labels sollten nur geändert werden, wenn der Requirement-Wortlaut sichtbar erfüllt ist und die bisherige Bewertung zusätzliche, nicht geforderte Hidden Outcomes verlangt.

Höchste Review-Priorität:

- Flow 06: `REQ-12`, eventuell `REQ-11` und `CONTR-02`
- Flow 09: `REQ-05` und `REQ-10`

Die Contrastive-Labels in Flow 10–12 sollten überwiegend beibehalten werden, da sie universelle, vergleichende oder explizit fehlende UI-Eigenschaften prüfen.

## Empfohlene nächsten Schritte

1. Flow 01 erneut mit aktuellem Verifier und Retries ausführen, da 16 Fallbacks die Messung beeinträchtigen.
2. Flow 10 mit final-state-orientierter Evidenzauswahl erneut ausführen.
3. Flows 11 und 12 mit den strengeren Regeln für Result-Screens, Vergleiche und Konjunktionen erneut ausführen.
4. Die genannten Gold-Label-Kandidaten manuell adjudizieren.
5. Danach Gesamtmetriken erneut berechnen und getrennt für akzeptierte und noch nicht final reviewte Labels ausweisen.

## Formulierung für den Supervisor

> Für die 13 aktuellen Verification Runs stimmen 169 von 259 vorhergesagten Labels, entsprechend 65,3 %, mit den derzeitigen manuellen Labels überein. Die besten aktuellen Flow-Werte liegen bei 77,8 %, der niedrigste bei 50,0 %. Die Hauptfehlerquellen sind die Auswahl relevanter später Screens, Überinterpretation universeller oder vergleichender Claims und einzelne manuelle Labels, deren Strenge nicht exakt dem sichtbaren Requirement-Wortlaut entspricht. Flow 01 enthält 16 API-Fallbacks und sollte technisch erneut ausgeführt werden. Die übrigen niedrigeren Werte sind überwiegend durch semantische Modell- und Evidenzprobleme erklärbar.
