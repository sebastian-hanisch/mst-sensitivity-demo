"""Konstanten der Sensitivitäts-Demo: Instanz-Geometrie, Regler, gemessene Werte, Presets."""
AREA = 100.0                     # Kantenlänge des Gebiets in km
DEPOT_XY = (15.0, 50.0)          # Lage des Depots (Werk) am linken Rand, Filialen zufällig im Gebiet
N_MIN, N_MAX, DEFAULT_N = 8, 100, 30                            # Filialen (ohne Depot)
K_OPTIONS = (3, 4, 5, 6, 8, 10, 15, 20, 1000)                   # nächste Nachbarn je Knoten; 1000 = vollständiger Graph
DEFAULT_K = 6
TERRAIN_OPTIONS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0)
DEFAULT_TERRAIN = 0.3
SEED_MAX = 999999
DEFAULT_SEED = 35
KINDS = ("depot", "textbook")
KIND_LABELS = {"depot": "Depot und Filialen (Karte)", "textbook": "Lehrbuchbeispiel (5 Knoten)"}
SIGMA_OPTIONS = (0.5, 1.0, 2.0, 5.0, 10.0)                      # Rauschen in Prozent der Kantenkosten (gleichverteilt +-sigma)
DEFAULT_SIGMA = 1.0
STREAM_LEN_OPTIONS = (10, 20, 50, 100)
DEFAULT_STREAM_LEN = 50
MIXES = ("costs", "mixed", "failures")
MIX_LABELS = {"costs": "nur Kostenänderungen", "mixed": "gemischt (Einfügen, Löschen, Kosten)", "failures": "nur Ausfälle (Baumkanten löschen)"}
DEFAULT_MIX = "mixed"
VIEWS = ("tolerance", "failure", "stream")
SWEEP_SEEDS = tuple(range(100000, 100005))
FEAS_SEEDS = tuple(range(200000, 200050))
N_SWEEP = (10, 20, 40, 80)
STEPS = {1: "1 · Toleranzen", 2: "2 · Ausfall", 3: "3 · Rauschen", 4: "4 · Update-Strom"}
NOISE_TRIALS = 20
_BASE = {"kind": "depot", "n": 30, "k": 6, "terrain": 0.3, "seed": 35, "sigma": 1.0, "stream_len": 50, "mix": "mixed", "step": 1, "noise_t": 0, "failure_i": 0, "stream_i": 0}
PRESETS = {
    "Standardfall (Voreinstellung)": dict(_BASE),
    "Lehrbuchbeispiel": {**_BASE, "kind": "textbook"},
    "Dünnes Netz (Brücken)": {**_BASE, "k": 3, "seed": 47, "step": 2},
    "Fragiler Baum": {**_BASE, "seed": 81, "step": 3},
    "Robust, aber Ausfall teuer": {**_BASE, "seed": 129, "step": 2},
    "Verpasste Änderung": {**_BASE, "seed": 0, "step": 3, "noise_t": 1},
    "Fehlalarm": {**_BASE, "seed": 1, "step": 3, "noise_t": 0},
    "Starkes Rauschen (5 %)": {**_BASE, "sigma": 5.0, "step": 3},
    "Update lohnt nicht (dicht)": {**_BASE, "k": 1000, "mix": "failures", "step": 4, "stream_i": 50},
}
PRESET_HELP = {
    "Standardfall (Voreinstellung)": "30 Filialen + Depot, k = 6 Nachbarn, Seed 35: 113 Kandidatenkanten, der billigste Baum kostet 466.63. Der Spielraum der Baumkanten liegt im Median bei 33.5 %, aber 3 Baumkanten haben unter 5 % (eine unter 1 %, kleinster 0.77 %); keine Brücke. Fällt die kritischste Baumkante aus, wird der Baum 3.42 % teurer. Rauschen von ±1 % ändert den Baum in 35 % der 20 Läufe.",
    "Lehrbuchbeispiel": "Fünf Knoten A bis E, sieben Kanten, Baumkosten 15: Spielraum der Baumkanten B-D 3 (bis 5), C-E 4 (bis 7), A-B 1 (bis 5), B-C 1 (bis 7); Nichtbaumkanten A-D 1 (ab 4), B-E 1 (ab 6), D-E 2 (ab 6) - von Hand nachzurechnen. Fällt B-D aus, springt A-D ein: Baumkosten 18 (9 Elementarschritte).",
    "Dünnes Netz (Brücken)": "Nur die 3 nächsten Nachbarn als Kandidaten (57 Kanten), Seed 47: 5 von 30 Baumkanten sind Brücken - fällt eine aus, gibt es keine Ersatzkante und der Baum zerfällt. Rauschen von ±1 % ändert den Baum in 45 % der Läufe.",
    "Fragiler Baum": "Seed 81: eine Baumkante mit nur 0.25 % Spielraum (drei unter 1 %); Rauschen von ±1 % ändert den Baum in 100 % der 20 Läufe - obwohl der Median-Spielraum 47.0 % beträgt. Lauf 1: 3 Kanten überschreiten ihre Einzeltoleranz, 1 Kante wird getauscht.",
    "Robust, aber Ausfall teuer": "Seed 129: keine Baumkante unter 2.7 % Spielraum, Rauschen von ±1 % ändert den Baum in 0 % der Läufe - aber der Ausfall der kritischsten Baumkante macht den Baum 8.42 % teurer (Ersatzkante 36.24 mehr). Stabil gegen Rauschen heißt nicht billig bei Ausfall.",
    "Verpasste Änderung": "Seed 0, Rausch-Lauf 2: keine einzige Kante überschreitet ihre Einzeltoleranz, trotzdem ändert sich der Baum (1 Kante getauscht) - zwei kleine Änderungen zusammen reichen. Die Einzeltoleranzen sind nur für EINE Änderung ein Maß.",
    "Fehlalarm": "Seed 1, Rausch-Lauf 1: eine Kante überschreitet ihre Einzeltoleranz, der Baum bleibt trotzdem gleich - die Ersatzkante hat sich im selben Lauf mitbewegt.",
    "Starkes Rauschen (5 %)": "Standardinstanz mit ±5 % Rauschen: der Baum ändert sich in 90 % der 20 Läufe (bei ±1 %: 35 %); Lauf 1: 2 Kanten überschreiten ihre Einzeltoleranz, 2 werden getauscht.",
    "Update lohnt nicht (dicht)": "Vollständiger Graph (465 Kanten), 50 Ausfälle (zufällige Baumkante löschen): das Update braucht 22071 Elementarschritte, Kruskal von vorn 249229 - aber mit gehaltener Sortierung nur 19732: das Löschen einer Baumkante scannt alle Nichtbaumkanten, im dichten Graphen ist das teurer als ein Union-Find-Durchlauf.",
}
# Beobachtete Spannweite der Kennzahl (MEDIAN über die 5 festen Instanzen Seeds 100000-100004) je Preset, mit Sicherheitsabstand: (Kennzahl, untere, obere Grenze).
PRESET_EXPECTED_BANDS = {
    "Standardfall (Voreinstellung)": ("tree_rel", 25.0, 40.0),
    "Dünnes Netz (Brücken)": ("bridge_share", 0.0, 6.0),
    "Fragiler Baum": ("tree_rel", 25.0, 40.0),
    "Robust, aber Ausfall teuer": ("tree_rel", 25.0, 40.0),
    "Verpasste Änderung": ("tree_rel", 25.0, 40.0),
    "Fehlalarm": ("tree_rel", 25.0, 40.0),
    "Starkes Rauschen (5 %)": ("instab", 60.0, 100.0),
    "Update lohnt nicht (dicht)": ("stream_ratio_presorted", 1.0, 2.5),
}
