# MST-Sensitivität – Toleranzen, Ausfall, Rauschen, dynamischer Baum – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-mst-sensitivity-demo.streamlit.app/)**

Zehntes Stück der **Spannbaum-Reihe** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning". Bisher galten die Kantenkosten als fest. In der Praxis ändern sich Trassenpreise, Leitungen fallen aus, neue Straßen kommen dazu. Die Demo misst drei Dinge am billigsten Baum (MST): **(1) Toleranz** – um wie viel darf eine Baumkante teurer, eine Nichtbaumkante billiger werden, bevor der Baum wechselt; **(2) Ausfall** – fällt eine Baumkante aus, springt die billigste **Ersatzkante** über den Schnitt ein, oder es gibt keine (**Brücke**, der Baum zerfällt); **(3) Update** – reicht es, den Baum anzupassen (Kante einfügen, löschen, Kosten ändern), statt Kruskal von vorn zu rechnen? Dazu die Frage aus der [kruskal-demo](../kruskal-demo), die dort nur ein Zähler war: **"±1 % Rauschen ändert den Baum in 30 % der Läufe"** – sagen die Einzeltoleranzen voraus, wann das passiert?

Alle Kanten haben feste Nummern, verglichen wird (Kosten, Nummer); damit ist der Baum auch bei Gleichständen eindeutig und "der Baum ändert sich" genau prüfbar.

**Einordnung in die Reihe:** geplant waren elf Stücke, alle sind gebaut, dies ist das zehnte:

```
Kruskal (Wurzel)                                                                           [gebaut: kruskal-demo]
 ├─ Prim (Kontrast: wächst von einem Punkt)                                                [gebaut: prim-demo]
 ├─ Borůvka (Kontrast: alle Komponenten parallel)                                          [gebaut: boruvka-demo]
 ├─ Euklidischer MST (keine n²-Kantenliste, Delaunay)                                      [gebaut: euclidean-mst-demo]
 ├─ Gerichteter Spannbaum (Chu-Liu/Edmonds)                                                [gebaut: arborescence-demo]
 ├─ Bottleneck-/Grad-/Hop-beschränkter Spannbaum                                           [gebaut: constrained-mst-demo]
 │    └─ Kapazitierter MST                                                                 [gebaut: cmst-demo]
 ├─ Steiner-Baum                                                                           [gebaut: steiner-tree-demo]
 │    └─ Prize-Collecting Steiner-Baum                                                     [gebaut: pcst-demo]
 ├─ MST-Sensitivität & dynamischer MST                                                     [DIESES STÜCK]
 └─ Zufällige Spannbäume & Kirchhoff                                                       [gebaut: random-spanning-tree-demo]
```

Ergebnis in Kürze: **Der Baum ist nicht durchgehend empfindlich, sondern wegen weniger Kanten: der Spielraum der Baumkanten liegt im Median bei 30 % ihrer Kosten, aber 3.1 % der Baumkanten haben unter 1 % und 12.5 % unter 5 % (Plan mit 30 Filialen, k = 6). Rauschen von ±1 % ändert den Baum in 28 % der Läufe, ±5 % in 74 %, ±10 % in 95 %. Die Einzeltoleranzen sagen das gut, aber nicht exakt voraus: bei ±1 % verpasst die Vorhersage "eine Kante überschreitet ihre Toleranz" 4.0 % der Läufe (14 % der Änderungen – zwei Änderungen zusammen reichen) und schlägt in 12.2 % falschen Alarm. Brücken gibt es nur in dünnen Netzen (k = 3: 68 % der Instanzen). Ein Update kostet im Mittel 2.7 % der Schritte von Kruskal von vorn und 11 % von Kruskal mit gehaltener Sortierung – aber das Löschen einer Baumkante im vollständigen Graphen ist teurer als die Neuberechnung mit gehaltener Sortierung.**

| Frage | Ergebnis (30 Filialen + Depot, k = 6 nächste Nachbarn, Geländezuschlag 0.3, sofern nicht anders angegeben; **50 Instanzen**, Seeds 200000–200049, bzw. **Median** über 5 feste Instanzen, Seeds 100000–100004; vollständig deterministisch) |
|---|---|
| **Sind die Toleranzen richtig?** | ✅ ja, direkt gegen die Neuberechnung des MST geprüft: knapp innerhalb der Grenze bleibt der Baum, knapp außerhalb ändert er sich (120 Zufallsgraphen mit Gleichständen; am Gleichstand entscheidet die Kantennummer); billiger werdende Baumkanten und teurer werdende Nichtbaumkanten ändern nie etwas; Ersatzkante und Brücke gegen Brute-Force (150 Graphen); schnelle == naive Berechnung auf 320 Graphen, Pfadmaximum gegen Pfadsuche |
| **Wie groß ist der Spielraum?** | Baumkanten: Median **30.4 %** ihrer Kosten (10. Perzentil aller Baumkanten 3.8 %, 25. Perzentil 11.7 %); Nichtbaumkanten 31.6 %; **3.1 %** der Baumkanten unter 1 %, **12.5 %** unter 5 %. Die Vorab-Hypothese "Median nur wenige Prozent" ist **widerlegt** – wenige fragile Kanten erklären die Instabilität |
| **Dichte und Gelände** | Median-Spielraum der Baumkanten bei k = 6/10/20/vollständig: 30.4/30.4/30.4/30.4 % (ab k = 6 liegt der Baum in den Kandidaten); Nichtbaumkanten bei k = 3/4/6/10/20/vollständig: 21.5/25.0/31.6/41.6/55.3/61.0 % (mehr, fernere Kandidaten); Geländezuschlag 0/0.6/1.0: 31.8/32.9/33.3 % – kaum Einfluss |
| **Ausfall und Brücken** | Ausfall einer Baumkante macht den Baum im Median um **1.0 %** teurer, der größte Ausfall im Median um 4.2 %; mit n = 10/20/40/80: 3.3/1.6/0.8/0.4 % (größter 11.8/6.2/3.8/1.9 %) – große Netze sind redundanter. **Brücken**: k = 3 im Mittel 4.5 % der Baumkanten, 68 % der Instanzen mit mindestens einer; k = 4 0.4 % / 10 %; ab k = 6 keine |
| **Rauschen** | Baum ändert sich bei ±0.5/1/2/5/10 %: **16/28/43/74/95 %** der Läufe (getauschte Kanten im Mittel 1.07/1.14/1.30/1.72/2.64); bei n = 10: 6 %, bei n = 80: 50 %; k = 3/vollständig: 28/31 %. Die 20 Läufe je Instanz sind dieselben Zufallsströme wie in der kruskal-demo (dort Median 30 % über die 5 festen Instanzen, hier per Test reproduziert) |
| **Sagen die Einzeltoleranzen das voraus?** | Vorhersage "irgendeine Kante überschreitet ihre Toleranz" bei ±0.5/1/2/5/10 %: 23/36/55/84/97 % der Läufe; **verpasst** (Baum ändert sich, keine Kante über der Grenze) 1.7/4.0/5.0/3.2/1.9 %, **Fehlalarm** 9.0/12.2/17/13/3.7 %. Bei ±1 %: 14 % der Änderungen verpasst, 34 % der Alarme falsch. Fixture von Hand: zwei Änderungen innerhalb ihrer Toleranzen (3.9 statt 2, 2.1 statt 4) ändern das Dreieck trotzdem |
| **Naiv gegen schnell** | Elementarschritte der Toleranzberechnung, schnell/naiv: n = 10/30/80: **38/15/6 %** (714/5437/35 201 gegen 273/827/2229); die Union-Find-Variante liefert dieselben Werte, ihr Vorsprung wächst mit n |
| **Update gegen Neuberechnung** | Gemischter Strom (50 Operationen): Update **2.7 %** der Schritte von Kruskal von vorn, **11 %** von Kruskal mit gehaltener Sortierung (billiger in allen Strömen); je Operation im Mittel: Einfügen 35 Schritte (gehaltene Sortierung 253), Kosten ändern 26, Nichtbaumkante löschen 1, Baumkante löschen 109 (253); der Baum ändert sich bei 14 % der Operationen |
| **Wann lohnt das Update nicht?** | ⚠️ Nur Ausfälle (Baumkante löschen): bei k = 6 kostet das Update im Median 37 % der Neuberechnung mit gehaltener Sortierung (immer billiger), bei k = 20 das **1.13-fache** (billiger in 36 % der Ströme), im **vollständigen Graphen das 1.46-fache** (8 %), bei 60 Filialen vollständig das **2.58-fache** (2 %) – der Scan aller Nichtbaumkanten kostet mehr als ein Union-Find-Durchlauf. Gegen Kruskal von vorn (mit Sortieren) gewinnt das Update immer (Median 9 % im vollständigen Graphen) |

## Was die Demo zeigt

1. **Der Baum unter Änderungen** (Schritt-Slider): **Toleranzen** (Karte mit Baumkanten nach Spielraum eingefärbt – rot unter 1 %, orange bis 5 %, gelb bis 20 %, grün mehr –, Brücken blau gestrichelt, Nichtbaumkanten kurz vor dem Einwechseln rot gepunktet; Tabelle der zehn empfindlichsten Baumkanten; Verteilung des Spielraums; im Lehrbuchbeispiel Kantenbeschriftung "Kosten (bis Grenze)") → **Ausfall** (Slider über die Baumkanten, kritischste zuerst: ausgefallene Kante rot gestrichelt, die zwei Seiten des Schnitts in Blau und Gelb, Ersatzkante orange, Text mit Kostenanstieg oder "Brücke") → **Rauschen** (Slider über die 20 Läufe: bleibt/fällt heraus/kommt hinein, violetter Halo um Kanten über ihrer Einzeltoleranz, Urteil Treffer / Verpasst / Fehlalarm) → **Update-Strom** (Slider über die Operationen: eingefügt / gelöscht / Kosten geändert, Tausch orange; Schritte je Operation und kumulierte Kurve Update gegen Neuberechnung).
2. **Kennzahlen:** Median-Spielraum, Anteil fragiler Kanten, Brücken, Update gegen Neuberechnung.
3. **🔬 Auf Abruf:** Rausch-Experiment (50 Instanzen x 20 Läufe je Stufe, Vorhersage gegen Wirklichkeit), Strom-Experiment (Schritte je Operationsart), Schrittkurve naiv gegen schnell, Sweeps über n / k / Gelände / Rauschen / Art der Updates.

Presets (9): Standardfall, Lehrbuchbeispiel, dünnes Netz (Brücken), fragiler Baum, robust aber Ausfall teuer, verpasste Änderung, Fehlalarm, starkes Rauschen, Update lohnt nicht (dicht).

## Messwerte der Presets

| Preset | Einstellungen | Ergebnis |
|---|---|---|
| **Standardfall** | 30 Filialen, k = 6, Seed 35 | 113 Kandidatenkanten, Baumkosten 466.63; Median-Spielraum 33.5 %, 3 Baumkanten unter 5 % (kleinster 0.77 %), keine Brücke; kritischster Ausfall +3.42 %; ±1 % Rauschen ändert den Baum in 35 % der Läufe |
| **Lehrbuchbeispiel** | 5 Knoten, 7 Kanten | Baumkosten 15; Spielraum B-D 3 (bis 5), C-E 4 (bis 7), A-B 1 (bis 5), B-C 1 (bis 7); Nichtbaumkanten A-D 1 (ab 4), B-E 1 (ab 6), D-E 2 (ab 6); fällt B-D aus, springt A-D ein: Kosten 18 (9 Elementarschritte) |
| **Dünnes Netz** | k = 3, Seed 47 | 57 Kanten, 5 von 30 Baumkanten sind Brücken; ±1 %: 45 % |
| **Fragiler Baum** | Seed 81 | kleinster Spielraum 0.25 % (drei unter 1 %), ±1 % ändert den Baum in 100 % der Läufe, obwohl der Median-Spielraum 47.0 % beträgt |
| **Robust, aber Ausfall teuer** | Seed 129 | kein Spielraum unter 2.7 %, ±1 %: 0 % – der Ausfall der kritischsten Baumkante kostet aber +8.42 % (36.24 mehr) |
| **Verpasste Änderung** | Seed 0, Lauf 2 | keine Kante über ihrer Einzeltoleranz, der Baum ändert sich trotzdem (1 Kante getauscht) |
| **Fehlalarm** | Seed 1, Lauf 1 | eine Kante über ihrer Einzeltoleranz, der Baum bleibt |
| **Starkes Rauschen** | ±5 % | Baum ändert sich in 90 % der Läufe (bei ±1 %: 35 %); Lauf 1: 2 Kanten über der Grenze, 2 getauscht |
| **Update lohnt nicht** | k vollständig (465 Kanten), 50 Ausfälle | Update 22 071 Schritte, Kruskal von vorn 249 229, mit gehaltener Sortierung 19 732 |

## Modell und Verfahren

- **Instanz** (`sens_scenario.py`): die Karte der kruskal-demo (Depot + Filialen, Kosten = Länge x Geländefaktor, k nächste Nachbarn oder vollständig; per Test gegen deren Zahlen geprüft: 113 Kanten, Baumkosten 466.63), Kanten mit fester Nummer.
- **Toleranzen** (`sens_algorithm.py`): Baumkante: Spielraum = Kosten der billigsten Ersatzkante über den Schnitt − eigene Kosten (unendlich bei einer Brücke); Nichtbaumkante: Kosten − Kosten der teuersten Baumkante auf dem Baumpfad. `tolerances_naive`: je Baumkante Schnittsuche + Scan aller Nichtbaumkanten, je Nichtbaumkante Pfadsuche. `tolerances_fast` (Tarjan-Idee): Kruskal-Rekonstruktionsbaum für das Pfadmaximum, Nichtbaumkanten aufsteigend, ein Union-Find kontrahiert die Baumpfade und belegt jede unbedeckte Baumkante mit der ersten Nichtbaumkante, die sie überdeckt.
- **Ausfall** (`failure`, `failure_table`): Schnitt per Suche im Baum ohne die Kante, billigste Kante über den Schnitt springt ein.
- **Dynamik** (`DynamicMST`): hält einen Spannwald; Einfügen per Kreisregel (Pfadsuche, teuerste Kante raus), Löschen (Nichtbaumkante: nichts, Baumkante: Ersatzkante per Schnittsuche und Scan), Kosten ändern (Baumkante teurer / Nichtbaumkante billiger kann tauschen). Nach jeder Operation ist der gehaltene Baum gleich der Neuberechnung mit Kruskal (Test: 2400 Operationen).
- **Vergleichsgrößen:** Kruskal von vorn (Sortier-Vergleiche + Union-Find) und Kruskal über eine **gehaltene Sortierung** (nur Union-Find) – die stärkere Basislinie. Alle Schritte sind Elementarschritte (Nachbareinträge, gescannte Kanten, Vergleiche, Zeiger), ein Näherungsmaß.
- **Rauschen:** jede Kante wird mit einem gleichverteilten Faktor aus ±sigma verändert (dieselbe Definition und Zufallsströme wie in der kruskal-demo); **Vorhersage** "eine Kante überschreitet ihre Einzeltoleranz" verglichen mit "Baum ändert sich".

## Was nicht funktioniert hat / Grenzen

- **Vorab-Hypothese "Baumkanten haben im Median nur wenige Prozent Spielraum" – widerlegt.** Der Median liegt bei 30 %; die Instabilität kommt von wenigen Kanten (3.1 % unter 1 %, das 10. Perzentil 3.8 %).
- **Einzeltoleranzen sind kein Sicherheitsbereich.** Sie gelten für **eine** Änderung; mehrere Änderungen zugleich können den Baum ändern, obwohl jede innerhalb ihrer Toleranz liegt (verpasst: 14 % der Änderungen bei ±1 %), und eine überschrittene Toleranz löst nicht immer einen Wechsel aus (Fehlalarm: 34 % der Alarme), wenn sich die Ersatzkante mitbewegt.
- **Das Update lohnt nicht immer.** Gegen Kruskal von vorn gewinnt es überall; gegen eine gehaltene Sortierung verliert das Löschen einer Baumkante im dichten Graphen (1.46-faches der Neuberechnung im vollständigen Graphen, 2.58-faches bei 60 Filialen), weil der Scan aller Nichtbaumkanten teurer ist als ein Union-Find-Durchlauf. Gegen den Aufwand "sortiert halten" wird nichts gerechnet (Pflege der Sortierung bei Kostenänderungen ist nicht modelliert).
- **Einfache Verfahren.** Naive und Tarjan-artige Toleranzen (Union-Find statt O(m α)-Feinheiten, Pettie 2005 nur genannt), einfache Update-Strukturen (Pfad-/Schnittsuche statt polylogarithmischer Strukturen: Frederickson 1985, Holm, de Lichtenberg und Thorup 2001 nur genannt).
- **Elementarschritte ≠ Laufzeit.** Die Zählung ist ein Näherungsmaß; Rechenzeit in Python hängt von Konstanten ab, die nicht gemessen werden.
- **Synthetische Instanzen und Rauschen.** Unabhängige, gleichverteilte multiplikative Änderungen; keine korrelierten Preisänderungen, keine Mengenänderungen, keine Kapazitäten. Kanten- und Knotenausfälle nur als einzelne Baumkanten.

## Verifikation

- `tests/test_algorithm.py`: Toleranzen gegen die Neuberechnung des MST (knapp innerhalb/außerhalb, Gleichstand nach Nummer), Ersatzkante/Brücke gegen Brute-Force, schnell == naiv == Pfadsuche (320 Graphen), Dynamik gleich Neuberechnung nach jeder von 2400 Operationen (Einfügen, Löschen, Kosten ändern, auch Spannwald nach Brückenausfall), Buchführung des Lehrbuchbeispiels von Hand, Einzeltoleranz gegen gemeinsame Änderung (Fixture), Sonderfälle (n = 2, Pfad, gleiche Kosten, Kosten 0).
- `tests/test_scenario.py` (Kopie treu zur kruskal-demo), `test_evaluation.py` (u. a. die Instabilität aus der kruskal-demo reproduziert: 0/60/30/0/30 %, Median 30), `test_presets.py` (Bänder + jede Zahl der Hilfetexte), `test_claims.py` (jede Zahl aus README und App über die echten `ev.*`-Funktionen), `test_app.py` (Streamlit-AppTest: Voreinstellung, jedes Preset, jeder Schritt und jede Position der Schritt-Regler, Randwerte, Würfel, Permalink-Grenzen, Instanzwechsel, Experimente und Sweeps auf Abruf, Footer).
- Für die Prüfung genügt **pytest** (Brute-Force und eigenes Kruskal tragen sie).

## Lokal starten

```bash
python -m venv venv && venv/Scripts/activate  # Windows; Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pip install -r requirements-dev.txt` und `python -m pytest tests/ -W error::SyntaxWarning`.

## Literatur

- Tarjan, R. E. (1982). *Sensitivity analysis of minimum spanning trees and shortest path trees.* Information Processing Letters 14(1), 30–33 (Korrigendum IPL 23, 1986, 219).
- Dixon, B., Rauch, M., & Tarjan, R. E. (1992). *Verification and sensitivity analysis of minimum spanning trees in linear time.* SIAM Journal on Computing 21(6), 1184–1192.
- Pettie, S. (2005). *Sensitivity analysis of minimum spanning trees in sub-inverse-Ackermann time.* ISAAC 2005 (nur genannt, nicht gebaut).
- Holm, J., de Lichtenberg, K., & Thorup, M. (2001). *Poly-logarithmic deterministic fully-dynamic algorithms for connectivity, minimum spanning tree, 2-edge, and biconnectivity.* Journal of the ACM 48(4), 723–760 (nur genannt, nicht gebaut).
- Kruskal (1956) und Union-Find (Tarjan 1975) wie in der kruskal-demo.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Spannbäume: vom Kruskal bis zum Zufallsbaum](https://sebastianhanisch.net/konzepte-spannbaum.html).
