"""MST-Sensitivität und dynamischer MST – Toleranzen, Ausfall, Rauschen, Update-Strom - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zehntes Stück der Spannbaum-Reihe der "Konzepte"-Reihe: bisher galten die Kantenkosten als fest. In der Praxis ändern sie sich. Gemessen werden der Spielraum jeder Kante (Toleranz: wie viel darf sie teurer
bzw. billiger werden, bevor der Baum wechselt), was ein Ausfall einer Baumkante kostet (Ersatzkante, Brücken), ob die Einzeltoleranzen vorhersagen, wann Rauschen den Baum ändert, und ob ein Update des Baums
weniger Schritte braucht als die Neuberechnung mit Kruskal.

Lauffähig mit: streamlit run app.py
"""

from dataclasses import replace

import pandas as pd
import streamlit as st

import sens_constants as C
import sens_evaluation as ev
from sens_evaluation import SWEEP_LABELS, SWEEP_TICKS, Settings, analyse
from sens_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    store_from_widget,
    sync_query_params,
)
from sens_visualization import (
    build_failure,
    build_noise,
    build_noise_curve,
    build_steps_curve,
    build_stream_curve,
    build_stream_step,
    build_sweep,
    build_tolerance_hist,
    build_tolerance_map,
)

st.set_page_config(page_title="MST-Sensitivität – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=False)
def _stream(settings):
    return ev.run_stream(ev.instance_of(settings), settings.stream_len, settings.mix)


@st.cache_data(show_spinner=False)
def _sweep(param, base):
    return ev.sweep(param, base)


@st.cache_data(show_spinner=False)
def _noise(base):
    return [{"sigma": s, **ev.noise_experiment(base, s)} for s in C.SIGMA_OPTIONS]


@st.cache_data(show_spinner=False)
def _streams(base):
    return ev.stream_experiment(base)


@st.cache_data(show_spinner=False)
def _steps_curve(base):
    return ev.tolerance_steps_curve(base)


def pct(x):
    return f"{x:.1f} %"


def num(x):
    return f"{x:.2f}"


st.title("📐 MST-Sensitivität – wie stabil ist der billigste Baum?")
st.markdown(
    """
**Zehntes Stück der Spannbaum-Reihe.** Bisher galten die Kantenkosten als fest. In der Praxis ändern sich Trassenpreise, Leitungen fallen aus, neue Straßen kommen dazu. Drei Fragen, alle gemessen:
**(1) Toleranz** - um wie viel darf eine Baumkante teurer, eine Nichtbaumkante billiger werden, bevor der Baum wechselt? **(2) Ausfall** - fällt eine Baumkante aus, springt die billigste Ersatzkante über den
Schnitt ein (oder es gibt keine: eine **Brücke**). **(3) Update** - reicht es, den Baum anzupassen (Kante einfügen, löschen, Kosten ändern), statt Kruskal von vorn zu rechnen?

Außerdem: sagen die **Einzeltoleranzen** voraus, wann **Rauschen** auf allen Kanten den Baum ändert? In der Kruskal-Demo war das nur ein Zähler ("±1 % Rauschen ändert den Baum in 30 % der Läufe"); hier wird es erklärt.
"""
)
st.caption(
    "Setzt auf [kruskal-demo](https://github.com/sebastian-hanisch/kruskal-demo) auf (Instanz, Kruskal, Union-Find, Instabilität ±1 %). Geplanter Nachfolger (nicht gebaut): zufällige Spannbäume und Kirchhoff. "
    "Ausblick nur genannt: Tarjan 1982, Pettie 2005 (schnellere Toleranzen), Holm-de Lichtenberg-Thorup 2001 (dynamischer MST mit polylogarithmischer Zeit)."
)

with st.expander("So funktionieren die Verfahren", expanded=True):
    st.markdown(
        """
1. **Ordnung:** alle Kanten haben feste Nummern; verglichen wird (Kosten, Nummer). Damit ist der billigste Baum auch bei Gleichständen eindeutig, und "der Baum ändert sich" ist genau prüfbar.
2. **Toleranz einer Baumkante:** sie darf teurer werden, bis die **billigste Ersatzkante** über den Schnitt, den sie im Baum aufspannt, gleich teuer ist: Spielraum = Kosten der Ersatzkante − eigene Kosten. Eine
   **Nichtbaumkante** darf billiger werden, bis sie so billig ist wie die **teuerste Baumkante auf ihrem Baumpfad**. Billiger werdende Baumkanten und teurer werdende Nichtbaumkanten ändern den Baum nie.
3. **Berechnung:** *naiv* - je Baumkante den Schnitt suchen und alle Nichtbaumkanten prüfen, je Nichtbaumkante den Pfad suchen; *schnell* (Tarjan-Idee) - Nichtbaumkanten aufsteigend, ein Union-Find kontrahiert die
   Baumpfade und belegt jede unbedeckte Baumkante mit der ersten Nichtbaumkante, die sie überdeckt; das Pfadmaximum liefert der Kruskal-Rekonstruktionsbaum.
4. **Ausfall:** Baumkante weg → Schnitt in zwei Seiten → billigste Kante über den Schnitt springt ein; gibt es keine, ist die Kante eine **Brücke** und der Baum zerfällt.
5. **Update:** *einfügen* - Baumpfad zwischen den Enden suchen, die teuerste Kante darauf fliegt raus, falls teurer als die neue (Kreisregel); *löschen* - Nichtbaumkante: nichts; Baumkante: Ersatzkante suchen;
   *Kosten ändern* - Baumkante teurer oder Nichtbaumkante billiger kann tauschen, sonst ändern sich nur die Kosten. Verglichen wird mit **Kruskal von vorn** (Sortieren + Union-Find) und mit **Kruskal über eine
   gehaltene Sortierung** (nur Union-Find) - in Elementarschritten (ein Näherungsmaß, keine Laufzeit).
        """
    )

if C.PRESETS:
    st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
    preset_names = list(C.PRESETS.keys())
    for row in (preset_names[:3], preset_names[3:6], preset_names[6:]):
        if not row:
            continue
        cols = st.columns(len(row))
        for col, name in zip(cols, row):
            with col:
                st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

ss = st.session_state
with st.sidebar:
    st.header("⚙️ Einstellungen")
    kind = st.radio("Instanz", options=list(C.KINDS), format_func=lambda v: C.KIND_LABELS[v], key="kind_select",
                    help="Depot und Filialen: Karte mit Kandidatengraph. Lehrbuchbeispiel: 5 Knoten, von Hand nachzurechnen.")
    if kind != "textbook":
        n = st.slider("Filialen n", *bounds("n_slider"), value=int(ss["n_slider"]), key="n_widget", on_change=store_from_widget, args=("n_slider",), help="Anzahl der Filialen (das Depot kommt dazu).")
        k = st.select_slider("Kandidaten k (nächste Nachbarn)", options=list(C.K_OPTIONS), value=int(ss["k_select"]), key="k_widget", on_change=store_from_widget, args=("k_select",),
                             format_func=lambda v: "vollständig" if v >= 1000 else str(v), help="Je Knoten die k nächsten Nachbarn als Kandidatenkanten; bei kleinem k gibt es Brücken (Baumkanten ohne Ersatz).")
        terrain = st.select_slider("Geländezuschlag", options=list(C.TERRAIN_OPTIONS), value=float(ss["terrain_select"]), key="terrain_widget", on_change=store_from_widget, args=("terrain_select",),
                                   help="Kosten = Länge x Faktor aus [1, 1 + Zuschlag].")
    else:
        n, k, terrain = C.DEFAULT_N, C.DEFAULT_K, C.DEFAULT_TERRAIN
    sigma = st.select_slider("Rauschen ± Prozent je Kante", options=list(C.SIGMA_OPTIONS), key="sigma_select", format_func=lambda v: f"{v:g} %",
                             help="Schritt 3 und die Kennzahl \"Rauschen\": jede Kantenkosten werden um einen gleichverteilten Faktor aus ±sigma verändert.")
    stream_len = st.select_slider("Länge des Update-Stroms", options=list(C.STREAM_LEN_OPTIONS), key="len_select", help="Schritt 4 und die Kennzahl \"Update\": Zahl der Operationen.")
    mix = st.radio("Art der Updates", options=list(C.MIXES), format_func=lambda v: C.MIX_LABELS[v], key="mix_select",
                   help="Nur Kostenänderungen, gemischt (50 % Kosten, 25 % Einfügen, 25 % Löschen) oder nur Ausfälle (zufällige Baumkante löschen).")
    if kind != "textbook":
        seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), value=int(ss["seed_input"]), key="seed_widget", step=1, on_change=store_from_widget, args=("seed_input",))
        st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    else:
        seed = C.DEFAULT_SEED

sync_query_params({"kind_select": kind, "n_slider": int(ss["n_slider"]), "k_select": int(ss["k_select"]), "terrain_select": float(ss["terrain_select"]), "seed_input": int(ss["seed_input"]),
                   "sigma_select": float(sigma), "len_select": int(stream_len), "mix_select": mix, "sens_step": int(ss["sens_step"])})

settings = Settings(kind, int(n), int(k), float(terrain), int(seed), float(sigma), int(stream_len), mix)
with st.spinner("Rechne..."):
    a = _analysis(settings)
inst = a.inst
edges = inst.edges
tree = a.tree
labels = inst.labels


def ename(i):
    u, v, _w = edges[i]
    return f"{labels[u]}–{labels[v]}" if labels is not None else f"{u}–{v}"


# --- In Aktion ---------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Der Baum unter Änderungen")
step = st.select_slider("Schritt", options=list(C.STEPS), key="sens_step", format_func=lambda s: C.STEPS[s])

if step == 1:
    fragile_n = sum(1 for t in a.tree_tols if not t.bridge and t.rel < 5.0)
    st.markdown(f"**{inst.n} Knoten, {inst.m} Kandidatenkanten**, der billigste Baum hat **{len(tree)} Kanten** und Kosten **{num(a.cost)}**. Die Farbe einer Baumkante zeigt ihren **Spielraum** (wie viel teurer sie werden darf, "
                f"in Prozent ihrer Kosten): **{fragile_n}** Baumkanten haben weniger als 5 %, **{len(a.bridges)}** sind Brücken." + (" Beschriftung: Kosten (Grenze, bei der der Baum wechselt)." if inst.kind == "textbook" else ""))
    st.plotly_chart(build_tolerance_map(inst, a.table, tree), width="stretch", key="s1_map")
    st.caption("Baumkanten: rot = unter 1 %, orange = bis 5 %, gelb = bis 20 %, grün = mehr; blau gestrichelt = Brücke (keine Ersatzkante); rot gepunktet = Nichtbaumkante, die schon bei unter 5 % billigerer Kosten einwechselt.")
    rows = []
    for t in sorted(a.tree_tols, key=lambda t: (not t.bridge, t.rel))[:10]:
        rows.append({"Baumkante": ename(t.edge), "Kosten": round(t.cost, 2), "Ersatzkante": "Brücke" if t.bridge else ename(t.other), "Grenze": None if t.bridge else round(t.bound, 2),
                     "Spielraum": None if t.bridge else round(t.margin, 2), "Spielraum (%)": None if t.bridge else round(t.rel, 1)})
    st.markdown("**Die zehn empfindlichsten Baumkanten** (Brücken zuerst):")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.plotly_chart(build_tolerance_hist(a), width="stretch", key="tol_hist")
    st.caption("Verteilung des Spielraums (Prozent der Kantenkosten): die meisten Kanten haben viel Spielraum, wenige liegen nahe an der Grenze - und diese wenigen entscheiden, wann der Baum wechselt.")
elif step == 2:
    fails = a.failures
    fmax = len(fails) - 1
    if "failure_i" in ss:
        ss["failure_i"] = min(max(0, int(ss["failure_i"])), fmax)
    i = st.slider("Ausfall (kritischste Baumkante zuerst)", 0, fmax, key="failure_i", help="0 = kritischste Baumkante (eine Brücke, sonst der größte Kostenanstieg); bis zur unkritischsten.") if fmax > 0 else 0
    f = fails[i]
    if f.rep is None:
        st.markdown(f"**Ausfall {i + 1} von {len(fails)}: {ename(f.edge)}** ist eine **Brücke**: es gibt keine Ersatzkante, der Baum zerfällt in zwei Teile mit {len(f.side)} und {inst.n - len(f.side)} Knoten.")
    else:
        st.markdown(f"**Ausfall {i + 1} von {len(fails)}: {ename(f.edge)}** (Kosten {num(edges[f.edge][2])}): die Ersatzkante **{ename(f.rep)}** (Kosten {num(edges[f.rep][2])}) springt ein, der Baum wird um **{num(f.delta)}** "
                    f"teurer (**+{f.rel:.2f} %**). Der Schnitt trennt {len(f.side)} von {inst.n - len(f.side)} Knoten.")
    st.plotly_chart(build_failure(inst, tree, f), width="stretch", key=f"s2_map_{i}")
    st.caption("Grau = Baum, rot gestrichelt = ausgefallene Kante, blaue und gelbe Punkte = die zwei Seiten des Schnitts, orange = einspringende Ersatzkante.")
elif step == 3:
    if "noise_t" in ss:
        ss["noise_t"] = min(max(0, int(ss["noise_t"])), C.NOISE_TRIALS - 1)
    t_ = st.slider("Rausch-Lauf", 0, C.NOISE_TRIALS - 1, key="noise_t", help="Jeder Lauf ist ein fester Zufallsstrom; 20 Läufe ergeben den Anteil der Läufe, in denen sich der Baum ändert.")
    noisy, new_tree, over = ev.noise_detail(a, float(sigma), t_)
    changed = new_tree != set(tree)
    pred = len(over) > 0
    verdict = ("**Treffer**: die Vorhersage stimmt." if changed == pred else ("**Verpasst**: der Baum ändert sich, obwohl keine Kante ihre Einzeltoleranz überschreitet - gemeinsame Änderungen." if changed else
               "**Fehlalarm**: eine Kante überschreitet ihre Einzeltoleranz, aber der Baum bleibt (die Ersatzkante hat sich ebenfalls bewegt)."))
    st.markdown(f"**Lauf {t_ + 1} von {C.NOISE_TRIALS}, Rauschen ±{sigma:g} %:** der Baum {'**ändert sich** (' + str(len(new_tree - set(tree))) + ' Kante(n) getauscht)' if changed else '**bleibt gleich**'}; "
                f"**{len(over)}** Kante(n) überschreiten ihre Einzeltoleranz. {verdict}")
    st.plotly_chart(build_noise(inst, tree, new_tree, over), width="stretch", key=f"s3_map_{t_}")
    st.caption("Grün = bleibt im Baum, rot gestrichelt = fällt heraus, orange = kommt hinein, violetter Halo = Kante, deren Kostenänderung ihre Einzeltoleranz überschreitet.")
else:
    stream = _stream(settings)
    smax = len(stream.steps)
    if "stream_i" in ss:
        ss["stream_i"] = min(max(0, int(ss["stream_i"])), smax)
    j = st.slider("Operation", 0, smax, key="stream_i", help="0 = Ausgangsbaum; jede weitere Operation ändert die Kanten, der Baum wird angepasst.") if smax > 0 else 0
    if j == 0:
        st.markdown(f"**Operation 0 von {smax}:** der Ausgangsbaum mit Kosten {num(stream.start_cost)}; {C.MIX_LABELS[mix]}.")
    else:
        s = stream.steps[j - 1]
        u, v = s.ends
        nm = f"{u}–{v}" if labels is None else f"{labels[u]}–{labels[v]}"
        role = "Baumkante" if s.on_tree else "Nichtbaumkante"
        if s.kind == "insert":
            what = f"Kante {nm} wird **eingefügt** (Kosten {num(s.new)})"
        elif s.kind == "delete":
            what = f"Kante {nm} wird **gelöscht** ({role}, Kosten {num(s.old)})"
        else:
            what = f"Kosten der Kante {nm} ({role}) ändern sich von {num(s.old)} auf **{num(s.new)}**"
        st.markdown(f"**Operation {j} von {smax}:** {what}. Der Baum {'**ändert sich**' if s.changed else 'bleibt gleich'}; Update **{s.update_steps}** Schritte, Neuberechnung **{s.recompute_steps}** (mit gehaltener Sortierung "
                    f"{s.presorted_steps}); Baumkosten jetzt {num(s.cost)}.")
    st.plotly_chart(build_stream_step(inst, stream, j), width="stretch", key=f"s4_map_{j}")
    if smax > 0:
        st.plotly_chart(build_stream_curve(stream), width="stretch", key="s4_curve")
        ut, rt = stream.totals()
        st.caption(f"Über alle {smax} Operationen: Update {ut} Schritte, Neuberechnung {rt}, mit gehaltener Sortierung {stream.presorted_total()} (Elementarschritte, ein Näherungsmaß). Blau = eingefügt, rot gestrichelt = gelöscht, "
                   "orange = Kosten geändert bzw. in den Baum gesprungen.")

st.markdown("---")

# --- Kennzahlen --------------------------------------------------------------------------------------------------------------------------------

st.markdown("## ⚙️ Wie stabil ist der Baum?")
tree_rel = a.tree_rel()
stream_sum = ev.stream_summary(_stream(settings))
instab = ev.instability(a, float(sigma))
m1, m2, m3, m4 = st.columns(4)
m1.metric("Spielraum (Median)", pct(ev._median(tree_rel)) if tree_rel else "-", delta=f"kleinster {pct(min(tree_rel))}" if tree_rel else "nur Brücken", delta_color="off")
m2.metric("Fragil (< 5 %)", pct(a.fragile(5.0)), delta=f"< 1 %: {pct(a.fragile(1.0))}", delta_color="off")
m3.metric("Brücken", f"{len(a.bridges)} von {len(tree)}", delta="ohne Ersatzkante", delta_color="off")
m4.metric("Update / Neuberechnung", f"{stream_sum['ratio_presorted'] * 100:.0f} %" if stream_sum["n_ops"] else "-", delta="gegen gehaltene Sortierung", delta_color="off")
fr = a.fail_rel()
st.caption(f"Spielraum = Toleranz in Prozent der Kantenkosten. Ausfall einer Baumkante kostet im Median {pct(ev._median(fr)) if fr else '-'} mehr (größter {pct(max(fr)) if fr else '-'}). Rauschen ±{sigma:g} % ändert den Baum in "
           f"{instab:.0f} % von {C.NOISE_TRIALS} Läufen. Toleranzen: naiv {a.naive.steps} Schritte, schnell {a.fast.steps}. Update-Strom ({stream_sum['n_ops']} Operationen, {C.MIX_LABELS[mix]}): {stream_sum['update_steps']} Schritte gegen "
           f"{stream_sum['recompute_steps']} bei Neuberechnung, {stream_sum['presorted_steps']} mit gehaltener Sortierung; {stream_sum['changed_share']:.0f} % der Operationen ändern den Baum.")

st.markdown("---")

# --- Experimente auf Abruf ---------------------------------------------------------------------------------------------------------------------

base = replace(settings, seed=0)
if kind != "textbook":
    st.subheader("🎲 Sagen die Einzeltoleranzen das Rauschen voraus?")
    st.caption("50 Instanzen x 20 Läufe mit den Einstellungen der Seitenleiste (nur der Seed wechselt): wie oft ändert sich der Baum, wie oft überschreitet irgendeine Kante ihre Einzeltoleranz, wie oft liegt die Vorhersage falsch?")
    if st.button("Rausch-Experiment (1000 Läufe je Stufe, dauert einige Sekunden)", key="noise_start"):
        ss["noise_done"] = ss.get("noise_done", set()) | {base}
    if base in ss.get("noise_done", set()):
        with st.spinner("Rechne..."):
            rows_n = _noise(base)
        cur = next(r for r in rows_n if r["sigma"] == float(sigma))
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Baum ändert sich", f"{cur['changed']:.0f} %", delta=f"±{sigma:g} %: im Mittel {cur['swaps']:.1f} Kanten getauscht", delta_color="off")
        q2.metric("Vorhersage: überschreitet", f"{cur['predicted']:.0f} %", delta=f"im Mittel {cur['over_mean']:.1f} Kanten", delta_color="off")
        q3.metric("Verpasst", f"{cur['missed']:.1f} %", delta=f"{cur['missed_share']:.0f} % der Änderungen", delta_color="off")
        q4.metric("Fehlalarm", f"{cur['false_alarm']:.1f} %", delta=f"{cur['false_share']:.0f} % der Alarme", delta_color="off")
        st.plotly_chart(build_noise_curve(rows_n), width="stretch", key="noise_curve")
        st.caption("Verpasst = der Baum ändert sich, obwohl jede Kante innerhalb ihrer Einzeltoleranz blieb (zwei Änderungen zusammen reichen); Fehlalarm = eine Kante überschreitet, der Baum bleibt trotzdem (die Ersatzkante hat sich mitbewegt).")
    st.markdown("---")

    st.subheader("🔁 Spart das Update Schritte?")
    st.caption("50 Instanzen mit den Einstellungen der Seitenleiste (Länge und Art des Stroms wie eingestellt): Elementarschritte des Updates gegen Kruskal von vorn und gegen Kruskal mit gehaltener Sortierung, je Operationsart.")
    if st.button("Strom-Experiment über 50 Instanzen (dauert einige Sekunden)", key="stream_start"):
        ss["stream_done"] = ss.get("stream_done", set()) | {base}
    if base in ss.get("stream_done", set()):
        with st.spinner("Rechne..."):
            r = _streams(base)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Update / Neuberechnung", f"{r['ratio_total'] * 100:.1f} %", delta="Kruskal von vorn", delta_color="off")
        s2.metric("Update / gehaltene Sortierung", f"{r['ratio_presorted_total'] * 100:.0f} %", delta=f"billiger in {r['cheaper_presorted_share']:.0f} % der Ströme", delta_color="off")
        s3.metric("Baum ändert sich", f"{r['changed_share']:.0f} %", delta="der Operationen", delta_color="off")
        s4.metric("Baumkante löschen", f"{r['delete_tree_update']:.0f}" if r["delete_tree_update"] == r["delete_tree_update"] else "-", delta=f"gehaltene Sortierung {r['delete_tree_presorted']:.0f}" if r["delete_tree_presorted"] == r["delete_tree_presorted"] else "", delta_color="off")
        rows_s = []
        for key, nm in (("cost", "Kosten ändern"), ("insert", "Einfügen"), ("delete_nontree", "Nichtbaumkante löschen"), ("delete_tree", "Baumkante löschen")):
            if r[f"{key}_update"] == r[f"{key}_update"]:
                rows_s.append({"Operation": nm, "im Mittel je Strom": round(r[f"{key}_n"], 1), "Update": round(r[f"{key}_update"], 1), "Neuberechnung": round(r[f"{key}_recompute"], 1), "mit gehaltener Sortierung": round(r[f"{key}_presorted"], 1)})
        st.dataframe(pd.DataFrame(rows_s), hide_index=True, width="stretch")
        st.caption("Mittlere Elementarschritte je Operation. Das Löschen einer Baumkante ist die teure Operation: die Ersatzkante wird durch Scannen aller Nichtbaumkanten gefunden.")
    st.markdown("---")

    st.subheader("⏱️ Naiv oder schnell?")
    st.caption("Elementarschritte der Toleranzberechnung über die Größe (Median über 5 feste Instanzen, sonst die Einstellungen der Seitenleiste).")
    if st.button("Schrittkurve berechnen (dauert einige Sekunden)", key="steps_start"):
        ss["steps_done"] = ss.get("steps_done", set()) | {base}
    if base in ss.get("steps_done", set()):
        with st.spinner("Rechne..."):
            rows_c = _steps_curve(base)
        st.plotly_chart(build_steps_curve(rows_c), width="stretch", key="steps_curve")
        st.caption("Beide liefern dieselben Toleranzen (Test); die schnelle Variante braucht weniger Schritte, weil sie jede Baumkante nur einmal belegt und nicht je Baumkante alle Nichtbaumkanten scannt.")
    st.markdown("---")

    st.subheader("📐 Sweeps")
    sweep_param = st.selectbox("Welcher Regler soll durchgefahren werden?", list(SWEEP_LABELS), format_func=lambda v: SWEEP_LABELS[v], key="sweep_select")
    metric_opts = {"tol": "Spielraum der Kanten", "fragile": "Fragile Baumkanten und Brücken", "fail": "Kostenanstieg beim Ausfall", "noise": "Baum ändert sich bei Rauschen", "stream": "Update gegen Neuberechnung", "steps": "Schritte der Toleranzberechnung"}
    if ss.get("sweep_metric") not in metric_opts:
        ss.pop("sweep_metric", None)
    metric = st.radio("Kennzahl", options=list(metric_opts), format_func=lambda v: metric_opts[v], key="sweep_metric", horizontal=True)
    if st.button("Sweep über 5 feste Instanzen berechnen (kann einige Sekunden dauern)", key="sweep_start"):
        ss["sweep_done"] = ss.get("sweep_done", set()) | {(sweep_param, base)}
    if (sweep_param, base) in ss.get("sweep_done", set()):
        with st.spinner("Rechne den Sweep über 5 feste Instanzen..."):
            rows_w = _sweep(sweep_param, base)
        series = {
            "tol": ([("tree_rel", "Baumkanten (Median)", "#2F6B65"), ("nontree_rel", "Nichtbaumkanten (Median)", "#e8a13a")], "Spielraum in % der Kantenkosten"),
            "fragile": ([("fragile1", "Baumkanten mit Spielraum < 1 %", "#d62728"), ("fragile5", "Baumkanten mit Spielraum < 5 %", "#ff7f0e"), ("bridge_share", "Brücken", "#1f4e9c")], "Anteil der Baumkanten (%)"),
            "fail": ([("fail_rel", "Ausfall: Median", "#2F6B65"), ("fail_rel_max", "Ausfall: größter", "#d62728")], "Kostenanstieg des Baums (%)"),
            "noise": ([("instab", "Rausch-Läufe mit Baumänderung", "#7b3fbf")], "Anteil der Läufe (%)"),
            "stream": ([("stream_ratio", "gegen Kruskal von vorn", "#8c8c8c"), ("stream_ratio_presorted", "gegen gehaltene Sortierung", "#4c78a8")], "Update-Schritte / Neuberechnung"),
            "steps": ([("naive_steps", "naiv", "#8c8c8c"), ("fast_steps", "schnell", "#2F6B65")], "Elementarschritte"),
        }[metric]
        st.plotly_chart(build_sweep(rows_w, SWEEP_LABELS[sweep_param], series[0], series[1], tick=SWEEP_TICKS.get(sweep_param), log_y=metric == "steps"), width="stretch", key="sweep_chart")
        st.caption("Median über 5 feste Instanzen (Seeds 100000–100004), Band = 10. bis 90. Perzentil. Die übrigen Regler stehen wie in der Seitenleiste.")
    st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Der Baum ist empfindlich gegen kleine Kostenänderungen** | Nur wegen weniger Kanten: der Spielraum der Baumkanten liegt im Median bei 30 % ihrer Kosten (Plan mit 30 Filialen, k = 6), aber 3.1 % der Baumkanten haben unter 1 % und 12.5 % unter 5 %; das 10. Perzentil aller Baumkanten liegt bei 3.8 %. Wenige fragile Kanten entscheiden, wann der Baum wechselt. | - |
| **Einzeltoleranzen sagen das Rauschen voraus** | Gut, aber nicht exakt: bei ±1 % ändert sich der Baum in 28 % der Läufe, "irgendeine Kante überschreitet ihre Toleranz" sagt 36 % voraus - verpasst 4.0 % der Läufe (14 % der Änderungen: zwei Änderungen zusammen reichen), Fehlalarm in 12.2 % (34 % der Alarme: die Ersatzkante hat sich mitbewegt). Bei ±10 % ändert sich der Baum in 95 %. | - |
| **Jede Baumkante hat eine Ersatzkante** | Nur in dichten Netzen: mit k = 3 hat der Baum im Mittel 4.5 % Brücken und 68 % der Instanzen mindestens eine, bei k = 4 0.4 % und 10 %, ab k = 6 keine. Fällt eine Baumkante aus, wird der Baum im Median 1.0 % teurer (größter Ausfall im Median 4.2 %); bei 10 Filialen 3.3 % (11.8 %), bei 80 nur 0.37 % (1.9 %). | Netzausbau, Redundanz |
| **Das Update lohnt immer** | Gegen Kruskal von vorn kostet es im Mittel 2.7 % der Schritte; gegen Kruskal mit gehaltener Sortierung 11 %. Aber das Löschen einer Baumkante scannt alle Nichtbaumkanten: im vollständigen Graph (30 Filialen, nur Ausfälle) ist es im Median das 1.46-fache der Neuberechnung mit gehaltener Sortierung (billiger nur in 8 % der Ströme), bei 60 Filialen das 2.58-fache. | Dynamische Datenstrukturen (Holm u. a. 2001, nicht gebaut) |
| **Schnelle Toleranzen sind komplizierter, aber nötig** | Die Union-Find-Variante braucht bei 10 Filialen 38 %, bei 30 15 %, bei 80 nur 6 % der Schritte der naiven; beide liefern dieselben Werte (Test auf 320 Instanzen). Der Vorsprung wächst mit der Größe. | Pettie 2005 (nicht gebaut) |
| **Kosten ändern sich unabhängig und gleichverteilt** | Modell: jede Kante bekommt einen eigenen, gleichverteilten Faktor aus ±sigma. Korrelierte Änderungen (Geländeabschnitte, Materialpreise) sind nicht modelliert; Einzeltoleranzen gelten für EINE Änderung. | Echte Preisreihen |
| **Elementarschritte sind Aufwand** | Ein Näherungsmaß (Nachbareinträge, gescannte Kanten, Sortier-Vergleiche, Union-Find-Zeiger), keine Laufzeit; die Update-Strukturen sind einfach (Pfadsuche, Schnittscan), nicht die polylogarithmischen. | - |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Ordnung.** Kanten $e$ mit Kosten $c_e$ und fester Nummer; verglichen wird $(c_e, e)$. Der billigste Baum $T$ ist damit eindeutig (Kruskal).

**Toleranz.** Für eine Baumkante $e \in T$ sei $r(e)$ die billigste Nichtbaumkante über den Schnitt von $T - e$. Dann bleibt $T$ genau dann billigster Baum, wenn $(c'_e, e) < (c_{r(e)}, r(e))$;
Spielraum $\tau(e) = c_{r(e)} - c_e$ ($\infty$ bei einer Brücke). Für eine Nichtbaumkante $f$ sei $g(f)$ die teuerste Baumkante auf dem Baumpfad zwischen ihren Enden: $T$ bleibt genau dann, wenn
$(c'_f, f) > (c_{g(f)}, g(f))$; Spielraum $\tau(f) = c_f - c_{g(f)}$. Einzeltoleranzen gelten für **eine** Änderung; zwei Änderungen zugleich können den Baum ändern, obwohl jede innerhalb ihrer Toleranz liegt.

**Aufwand.** Naiv $O(n(n + m))$ (Schnittsuche je Baumkante, Pfadsuche je Nichtbaumkante). Schnell: Nichtbaumkanten aufsteigend, Union-Find über den Baum, $O(m\,\alpha(m, n))$ nach der Idee von Tarjan (1982); Pettie (2005) senkt
das weiter (nur genannt).

**Update.** Einfügen $O(n)$ (Pfadsuche), Löschen einer Nichtbaumkante $O(1)$, Löschen einer Baumkante $O(n + m)$ (Schnitt und Scan). Fully-dynamisch mit polylogarithmischer Zeit: Holm, de Lichtenberg und Thorup (2001), nur genannt.

**Literatur.** Tarjan, R. E. (1982). *Sensitivity analysis of minimum spanning trees and shortest path trees.* Information Processing Letters 14(1), 30-33 (Korrigendum IPL 23, 1986, 219). Dixon, B., Rauch, M., & Tarjan, R. E.
(1992). *Verification and sensitivity analysis of minimum spanning trees in linear time.* SIAM Journal on Computing 21(6), 1184-1192. Pettie, S. (2005). *Sensitivity analysis of minimum spanning trees in sub-inverse-Ackermann time.* ISAAC 2005
(nur genannt). Holm, J., de Lichtenberg, K., & Thorup, M. (2001). *Poly-logarithmic deterministic fully-dynamic algorithms for connectivity, minimum spanning tree, 2-edge, and biconnectivity.* Journal of the ACM 48(4), 723-760 (nur genannt).
Kruskal (1956) und Union-Find (Tarjan 1975) wie in der Kruskal-Demo.

Implementiert in `sens_algorithm.py` (Toleranzen, Ausfall, `DynamicMST`), `sens_scenario.py` (Instanzen), `sens_evaluation.py` (Kennzahlen, Rauschen, Ströme, Sweeps).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
