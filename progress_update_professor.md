# Progress Update zur Bachelorarbeit

**Thema:** Automated UI requirement verification from ordered screenshot sequences  
**Stand:** 08.05.2026

## Kurzueberblick

Die Arbeit untersucht, wie textuelle UI-Requirements gegen geordnete Screenshot-Flows ueberprueft werden koennen. Der Fokus liegt auf nachvollziehbarer Verifikation: Ein Requirement soll nicht nur ein Label wie `FULFILLED` oder `NOT_FULFILLED` erhalten, sondern durch konkrete sichtbare UI-Evidenz aus dem Flow begruendet werden.

Die zentrale Abgrenzung ist: Bewertet wird die sichtbare UI. Nicht sichtbare Eigenschaften wie echte Persistenz, Backend-Korrektheit, E-Mail-Zustellung, Payment oder Security werden nicht aus Screenshots inferiert.

## Methodische Entscheidungen

Das Label-Schema trennt zwei Fragen: Erstens, ob ein Requirement aus Screenshots ueberhaupt ueberpruefbar ist (`UI_VERIFIABLE`, `PARTIALLY_UI_VERIFIABLE`, `NOT_UI_VERIFIABLE`). Zweitens, welches Verifikationslabel auf Basis der sichtbaren Evidenz vergeben wird (`FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, `ABSTAIN`).

Wichtig ist die konservative Entscheidung, dass `NOT_FULFILLED` sichtbare Gegen-Evidenz braucht. Fehlende Evidenz allein fuehrt nicht automatisch zu einer Verletzung, sondern eher zu `PARTIALLY_FULFILLED` oder `ABSTAIN`. Dadurch vermeidet die Evaluation ueberstarke Aussagen.

Requirements werden ausserdem in Claims zerlegt. Diese Claims werden einzeln mit Evidenzstatus wie `SUPPORTED`, `MISSING`, `HIDDEN` oder `CONTRADICTED` annotiert. Das macht spaetere Fehlentscheidungen besser analysierbar als ein reines Gesamtlabel.

Dabei muss zwischen zwei Claim-Arten unterschieden werden. Die Claims in der Gold-Datenbasis sind manuell gepruefte Referenz-Claims. Sie beschreiben, welche Teilbedingungen ein Requirement enthaelt und dienen als Ground Truth fuer die Evaluation. Der Verifier selbst soll spaeter ebenfalls automatisch Claims aus dem Requirement erzeugen. Diese automatisch erzeugten Claims sind Predicted Claims und damit Teil des Modelloutputs. Diese Trennung ist methodisch wichtig: Der Verifier bekommt im Hauptsetting nur Requirement und Screenshot-Flow; die Gold Claims werden erst danach zur Bewertung verwendet.

Die Einordnung ist durch zwei Beobachtungen motiviert. Erstens sind Requirements in der Praxis haeufig mehrdeutig, zusammengesetzt oder teilweise nicht direkt beobachtbar; das ist ein bekanntes Problem in Requirements Engineering und wird in Related Work zu Requirements Ambiguity diskutiert. Zweitens muss ein Verifier bei unsicherer oder unvollstaendiger Evidenz ablehnen koennen, statt ein scheinbar sicheres Label zu erzwingen. Deshalb gibt es `ABSTAIN`, UI-Evaluability und explizite Uncertainty Reasons. Die Claim-Zerlegung ist der Versuch, diese Unsicherheit nicht nur im Endlabel zu verstecken, sondern auf der Ebene einzelner Requirement-Teile sichtbar zu machen.

## Aktueller Stand der Anwendung

Im Repository existiert ein lauffaehiger Prototyp fuer die Daten- und Review-Pipeline. Das Backend stellt Flows, Screenshots, Candidate Requirements, Gold Requirements und Verification-Gold-Items ueber eine API bereit. Zusaetzlich gibt es Funktionen zur Candidate-Generierung, zum Review, zur Promotion in Gold-Daten und zur modellbasierten Verifikation.

Das React-Frontend dient als Annotation Workbench. Es zeigt Screenshot-Flows, Candidate Requirements und Gold-/Verification-Items zusammen an. Reviewer koennen Requirements bearbeiten, akzeptieren oder ablehnen, Labels setzen, UI Evaluability eintragen, Claims annotieren und Evidence Steps auswaehlen. Die Website ist damit nicht nur Demo, sondern methodisches Werkzeug zur Erstellung einer nachvollziehbaren Gold-Datenbasis.

Das Setup und die lokalen Startschritte sind im `README.md` dokumentiert. Dort ist beschrieben, wie die Mind2Web-Flows exportiert werden, wie Backend und Frontend gestartet werden und welche Daten versioniert bzw. lokal generiert sind.

Versioniert sind aktuell Candidate- und Gold-Daten fuer 13 Mind2Web-Flows. Im Repo liegen 100 Candidate Requirements und 173 Gold Requirements. Die Gold Requirements sind dabei die menschlich zu pruefenden Benchmark-Items. Intern gibt es dafuer im Code eine detailliertere Struktur fuer Verification-Gold-Items, weil dort zusaetzlich Claims, Evidence Steps, Verification Labels und Uncertainty Reasons gespeichert werden. Fuer den Bericht kann man diese aber als eine Ebene betrachten: Gold Requirements sind die finalen bzw. zu finalisierenden Benchmark-Requirements. Der Review-Status `needs_review` markiert Items, bei denen Claims, Evidenz und Label noch geprueft werden muessen; nach dieser Pruefung wird der Status auf `accepted` gesetzt.

Candidate Requirements sind dagegen Vorschlaege, die aus einem Flow abgeleitet oder umformuliert wurden. Sie sind noch keine finale Ground Truth. Im Review werden sie entweder verworfen, ueberarbeitet oder als Gold Requirement uebernommen. Diese Trennung ist wichtig, weil die automatische Generierung sonst direkt zur Evaluationsgrundlage wuerde. Die Gold-Ebene dient deshalb als manuell kontrollierte Referenz fuer die spaetere Modellbewertung.

Mit Contrastive Requirements sind gezielt abgewandelte Requirements gemeint, die aus bestehenden Gold Requirements abgeleitet werden. Sie sollen schwerere Faelle erzeugen, z. B. indem ein sichtbares Requirement um eine versteckte Persistenzforderung, eine staerkere Vollstaendigkeitsforderung oder eine im Flow fehlende Bedingung erweitert wird. Dadurch entstehen bewusst `PARTIALLY_FULFILLED`, `NOT_FULFILLED` oder `ABSTAIN`-Faelle. Das ist wichtig, damit die Evaluation nicht nur einfache positive Beispiele enthaelt. Auch diese contrastive Requirements muessen manuell geprueft werden; ihr automatisch erzeugtes intended label ist nur ein Vorschlag.

PURE ist bereits technisch vorbereitet, u. a. ueber Loader, Annotation Sheet und Tests. Der aktuelle Hauptpfad der Anwendung bleibt aber die Arbeit mit UI Screenshot Flows, da diese direkt zum Verifikationsproblem passen. Claims sind fuer PURE besonders nuetzlich, weil PURE Requirements tendenziell laenger, detaillierter und staerker aus Dokumentkontext formuliert sind. Durch die Claim-Zerlegung kann man sichtbare UI-Kerne von nicht beobachtbaren Dokument- oder Systemannahmen trennen.

## Bedienung der Review-Website

Die Website ist als Arbeitsoberflaeche fuer die Annotation gedacht. Links wird ein Flow ausgewaehlt. Danach zeigt die Hauptansicht die geordnete Screenshot-Sequenz, die zugehoerigen Candidate Requirements und die bereits angelegten Gold Requirements. Im Single-Screen-Review werden Requirements direkt neben einzelnen Screens angezeigt; im Multi-Screen-Review werden Requirements betrachtet, die Evidenz ueber mehrere Screens benoetigen. Die Overview-Ansicht dient zur schnellen Kontrolle aller offenen Items und ist meiner Meinung nach am nützlichsten (zusammen mit Single-Screen Review in einem zweiten Fenster).

Ein typischer Review-Schritt ist: Flow auswaehlen, Requirement oeffnen, Text bei Bedarf korrigieren, UI-Evaluability setzen, Evidence Steps markieren, Claims anlegen oder ueberarbeiten, pro Claim den Status setzen und danach das finale Verification Label vergeben. Wenn alles konsistent ist, wird der Review-Status von `needs_review` auf `accepted` gesetzt. Zentrale Features sind damit Screenshot-Navigation, Zoom auf Screenshots, Candidate-Promotion, Claim-Editor, Evidence-Step-Auswahl, Label-Auswahl und Dokumentation von Rationale bzw. Uncertainty Reasons.

## Beispiel fuer Claim-Zerlegung

Ein Requirement wird nicht nur als Ganzes bewertet, sondern in kleinere Claims zerlegt. Beispiel:

Requirement: `The system shall preserve previously entered gift-card configuration data while the shopper continues completing later fields.`

Moegliche Claims:

1. Previously entered recipient details are preserved while later fields are completed.
2. Previously entered sender and amount details are preserved while later fields are completed.

Beide Claims koennen dann getrennt mit Evidence Steps verbunden werden. Wenn die Screenshots zeigen, dass fruehere Eingaben in spaeteren Schritten weiterhin sichtbar sind, erhalten die Claims den Status `SUPPORTED`. Wenn ein Claim sichtbar widersprochen wird, waere `CONTRADICTED` passend. Wenn ein Teil zwar relevant ist, aber im Flow nicht beobachtbar ist, wird er als `MISSING`, `HIDDEN` oder `AMBIGUOUS` markiert.

Ein zweites Beispiel:

Requirement: `The system shall allow shoppers to navigate from the main storefront into a dedicated gift-card area.`

Moegliche Claims:

1. The storefront provides access to a dedicated gift-card area.
2. The flow reaches a page or state dedicated to gift cards.

Hier kann der zweite Claim durch einen Screenshot der Gift-Card-Seite gestuetzt sein. Der erste Claim kann unsicher bleiben, wenn der konkrete Navigationsausloeser nur schwach sichtbar ist. Dadurch kann das Gesamtlabel z. B. `PARTIALLY_FULFILLED` sein, obwohl es sichtbare positive Evidenz gibt.

## Aktuelle Einschaetzung

Der Fortschritt liegt momentan vor allem in der sauberen Problemdefinition und im Aufbau der Infrastruktur: Label-Schema, Claim-/Evidence-Struktur, Datenablage, API und Review-UI sind vorhanden. Eine vollstaendige Evaluation der Modellperformance ist noch nicht der aktuelle Stand.

Die wichtigste naechste Aufgabe ist, aus dem vorhandenen Prototyp eine kleine, aber konsistente Verification-Gold-Datenbasis zu erzeugen. Danach koennen erste Baselines und Metriken fuer Labelqualitaet und Evidenzqualitaet sinnvoll ausgewertet werden.

## Naechste Schritte

1. Annotationen fuer mehrere Flows vervollstaendigen.
2. Claim-, Evidence- und Uncertainty-Konsistenz pruefen.
3. Die eigentliche Verifier-Pipeline explizit modellieren: Requirement und geordnete Screenshot-Sequenz als Input, automatische Claim-Zerlegung, UI-Evaluability pro Claim, Evidence Retrieval aus dem Screenshot-Flow, Claim-Level-Entscheidung, Aggregation zum finalen Verification Label und Ausgabe mit Evidenz, Rationale und Unsicherheitsgruenden.
