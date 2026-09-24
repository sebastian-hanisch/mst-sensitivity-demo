"""Plotly-Abbildungen: Toleranz-Karte (Baumkanten nach Spielraum eingefärbt, Brücken gestrichelt), Ausfall (Schnitt und Ersatzkante), Rausch-Lauf, Update-Strom, Verteilung der Toleranzen, Schrittkurven, Sweeps.
Karten ohne feste Achsenbereiche (Plotly friert sie beim ersten Zeichnen ein); Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import math

import plotly.graph_objects as go

TREE_COLOR = "#2F6B65"
DEPOT_COLOR = "#2ca02c"
NODE_COLOR = "#4c78a8"
CAND_COLOR = "rgba(150,150,150,0.30)"
RED, ORANGE, YELLOW, GREEN, BLUE = "#d62728", "#ff7f0e", "#e8c13a", "#2F6B65", "#1f4e9c"
SIDE_A, SIDE_B = "#4c78a8", "#e8a13a"
BINS = ((1.0, "unter 1 %", RED), (5.0, "1 bis 5 %", ORANGE), (20.0, "5 bis 20 %", YELLOW), (math.inf, "ab 20 %", GREEN))


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height, legend_y=-0.1):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=legend_y), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _map_axes(fig, height=480):
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, autorange="reversed")
    return _base(fig, height)


def _height(inst):
    return 340 if inst.kind == "textbook" else 480


def _lines(fig, inst, pairs, color, width=2.6, dash="solid", name="", showlegend=False):
    pairs = list(pairs)
    if not pairs:
        return
    xs, ys = [], []
    for u, v in pairs:
        xs += [inst.xy[u][0], inst.xy[v][0], None]
        ys += [inst.xy[u][1], inst.xy[v][1], None]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=width, dash=dash), name=name, hoverinfo="skip", showlegend=showlegend))


def _nodes(fig, inst, colors=None, labels=True):
    n = inst.n
    label = inst.labels if inst.labels is not None else None
    cols = colors if colors is not None else [NODE_COLOR] * n
    rest = [v for v in range(n) if v != inst.depot]
    text = [label[v] for v in rest] if (label is not None and labels) else None
    fig.add_trace(go.Scatter(x=[inst.xy[v][0] for v in rest], y=[inst.xy[v][1] for v in rest], mode="markers+text" if text else "markers", text=text, textposition="top center",
                             marker=dict(size=9 if inst.kind == "depot" else 15, color=[cols[v] for v in rest], line=dict(width=1, color="white")), name="Filiale", hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[inst.xy[inst.depot][0]], y=[inst.xy[inst.depot][1]], mode="markers+text" if label is not None else "markers", text=[label[inst.depot]] if label is not None else None, textposition="top center",
                             marker=dict(size=16, symbol="star", color=DEPOT_COLOR, line=dict(width=1, color="white")), name="Depot", hoverinfo="skip", showlegend=True))


def _edge_labels(fig, inst, texts):
    """Kantenbeschriftungen als Annotationen mit Hinterlegung (nur Lehrbuchbeispiel): {(u, v): Text}."""
    for (u, v), t in texts.items():
        fig.add_annotation(x=(inst.xy[u][0] + inst.xy[v][0]) / 2, y=(inst.xy[u][1] + inst.xy[v][1]) / 2, text=t, showarrow=False, bgcolor="rgba(255,255,255,0.85)", font=dict(size=11))


def _bin(rel):
    for hi, name, color in BINS:
        if rel < hi:
            return name, color
    return BINS[-1][1], BINS[-1][2]


def build_tolerance_map(inst, table, tree, highlight=None):
    """Baumkanten nach Spielraum (rot: unter 1 %, orange: bis 5 %, gelb: bis 20 %, grün: mehr), Brücken blau gestrichelt; Nichtbaumkanten dünn grau, die mit kleinem Spielraum (unter 5 %) rot gepunktet."""
    fig = go.Figure()
    tree = set(tree)
    _lines(fig, inst, [(inst.edges[t.edge][0], inst.edges[t.edge][1]) for t in table if not t.tree and t.rel >= 5.0], CAND_COLOR, 0.9)
    _lines(fig, inst, [(inst.edges[t.edge][0], inst.edges[t.edge][1]) for t in table if not t.tree and t.rel < 5.0], "rgba(214,39,40,0.55)", 1.4, "dot", "Nichtbaumkante kurz vor dem Einwechseln (unter 5 %)", True)
    for hi, name, color in BINS:
        lo = 0.0 if hi == 1.0 else {5.0: 1.0, 20.0: 5.0, math.inf: 20.0}[hi]
        sel = [t for t in table if t.tree and not t.bridge and lo <= t.rel < hi]
        _lines(fig, inst, [tuple(inst.edges[t.edge][:2]) for t in sel], color, 4.2, name=f"Baumkante, Spielraum {name}", showlegend=bool(sel))
    br = [t for t in table if t.tree and t.bridge]
    _lines(fig, inst, [tuple(inst.edges[t.edge][:2]) for t in br], BLUE, 4.4, "dash", "Brücke (keine Ersatzkante)", bool(br))
    if highlight is not None:
        _lines(fig, inst, [tuple(inst.edges[highlight][:2])], "rgba(0,0,0,0.85)", 7.0, "solid", "gewählte Kante", True)
    _nodes(fig, inst)
    if inst.kind == "textbook":
        texts = {}
        for t in table:
            u, v, w = inst.edges[t.edge]
            texts[(u, v)] = f"{w:g}" + ("" if t.bridge else (f" (bis {t.bound:g})"))
        _edge_labels(fig, inst, texts)
    return _map_axes(fig, _height(inst))


def build_failure(inst, tree, f, table=None):
    """Ausfall einer Baumkante: der Baum grau, die ausgefallene Kante rot gestrichelt, die beiden Seiten des Schnitts blau/gelb, die einspringende Ersatzkante orange."""
    fig = go.Figure()
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in range(len(inst.edges)) if i not in set(tree)], CAND_COLOR, 0.9)
    e = f.edge
    keep = [i for i in tree if i != e]
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in keep], "rgba(90,90,90,0.85)", 3.0, name="Baum", showlegend=True)
    _lines(fig, inst, [tuple(inst.edges[e][:2])], RED, 5.0, "dash", "ausgefallene Kante", True)
    if f.rep is not None:
        _lines(fig, inst, [tuple(inst.edges[f.rep][:2])], ORANGE, 5.4, name="Ersatzkante", showlegend=True)
    cols = [SIDE_A if v in f.side else SIDE_B for v in range(inst.n)]
    _nodes(fig, inst, cols)
    if inst.kind == "textbook":
        _edge_labels(fig, inst, {tuple(inst.edges[e][:2]): f"{inst.edges[e][2]:g}"} | ({tuple(inst.edges[f.rep][:2]): f"{inst.edges[f.rep][2]:g}"} if f.rep is not None else {}))
    return _map_axes(fig, _height(inst))


def build_noise(inst, old_tree, new_tree, over_edges, noisy=None):
    """Rausch-Lauf: unveränderte Baumkanten grün, herausgefallene rot gestrichelt, neu hineingekommene orange; Kanten, die ihre Einzeltoleranz überschreiten, violett umrandet (dicker Halo)."""
    fig = go.Figure()
    old, new = set(old_tree), set(new_tree)
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in range(len(inst.edges)) if i not in old and i not in new], CAND_COLOR, 0.9)
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in over_edges], "rgba(123,63,191,0.35)", 9.0, name="überschreitet die Einzeltoleranz", showlegend=bool(over_edges))
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in old & new], TREE_COLOR, 3.6, name="bleibt im Baum", showlegend=True)
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in old - new], RED, 4.4, "dash", "fällt heraus", bool(old - new))
    _lines(fig, inst, [tuple(inst.edges[i][:2]) for i in new - old], ORANGE, 4.6, name="kommt hinein", showlegend=bool(new - old))
    _nodes(fig, inst)
    return _map_axes(fig, _height(inst))


def build_stream_step(inst, stream, i):
    """Zustand nach `i` Operationen des Update-Stroms (0 = Ausgangsbaum): Baum grün; die Kante der letzten Operation hervorgehoben (Einfügen grün dick, Löschen rot gestrichelt, Kostenänderung orange), Tausch: die
    hinzugekommene Kante orange."""
    fig = go.Figure()
    ends = stream.ends
    tree_pairs = stream.start_tree if i == 0 else stream.steps[i - 1].tree
    _lines(fig, inst, [tuple(uv) for uv in ends.values()], CAND_COLOR, 0.9)
    _lines(fig, inst, [tuple(uv) for uv in tree_pairs], TREE_COLOR, 3.6, name="Baum", showlegend=True)
    if i > 0:
        s = stream.steps[i - 1]
        color, dash, name = {"insert": (BLUE, "solid", "eingefügte Kante"), "delete": (RED, "dash", "gelöschte Kante"), "cost": (ORANGE, "solid", "Kante mit neuen Kosten")}[s.kind]
        _lines(fig, inst, [tuple(s.ends)], color, 6.0, dash, name, True)
        if s.swapped_in is not None and s.swapped_in != s.edge:
            _lines(fig, inst, [tuple(ends[s.swapped_in])], ORANGE, 5.0, name="springt in den Baum", showlegend=True)
    _nodes(fig, inst)
    return _map_axes(fig, _height(inst))


def build_tolerance_hist(a):
    """Verteilung des Spielraums (Prozent der Kantenkosten, bei 200 % abgeschnitten) für Baumkanten (ohne Brücken) und Nichtbaumkanten."""
    cap = 200.0
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=[min(v, cap) for v in a.tree_rel()], xbins=dict(start=0, end=cap, size=10), name="Baumkanten", marker_color="rgba(47,107,101,0.70)"))
    fig.add_trace(go.Histogram(x=[min(v, cap) for v in a.nontree_rel()], xbins=dict(start=0, end=cap, size=10), name="Nichtbaumkanten", marker_color="rgba(232,161,58,0.60)"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Spielraum in % der Kantenkosten (ab 200 % zusammengefasst)")
    fig.update_yaxes(title_text="Kanten")
    return _base(fig, 320, legend_y=-0.3)


def build_stream_curve(stream):
    """Kumulierte Elementarschritte über die Operationen: Update, Neuberechnung mit Sortierung, Neuberechnung mit gehaltener Sortierung (logarithmisch)."""
    xs = list(range(1, len(stream.steps) + 1))

    def cum(vals):
        out, s = [], 0
        for v in vals:
            s += v
            out.append(s)
        return out

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=cum(s.recompute_steps for s in stream.steps), mode="lines", line=dict(color="#8c8c8c", width=2.4), name="Neuberechnung (Kruskal von vorn)"))
    fig.add_trace(go.Scatter(x=xs, y=cum(s.presorted_steps for s in stream.steps), mode="lines", line=dict(color="#4c78a8", width=2.4), name="Neuberechnung mit gehaltener Sortierung"))
    fig.add_trace(go.Scatter(x=xs, y=cum(s.update_steps for s in stream.steps), mode="lines", line=dict(color=TREE_COLOR, width=3.2), name="Update"))
    fig.update_xaxes(title_text="Operation")
    fig.update_yaxes(title_text="Elementarschritte (kumuliert)", type="log")
    return _base(fig, 320, legend_y=-0.35)


def build_steps_curve(rows):
    """Elementarschritte der Toleranzberechnung über n: naiv (Schnitt- und Pfadsuche) gegen schnell (Union-Find), logarithmisch."""
    xs = [str(r["n"]) for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[r["naive"] for r in rows], mode="lines+markers", line=dict(color="#8c8c8c", width=2.6), name="naiv"))
    fig.add_trace(go.Scatter(x=xs, y=[r["fast"] for r in rows], mode="lines+markers", line=dict(color=TREE_COLOR, width=2.6), name="schnell (Union-Find)"))
    fig.update_xaxes(title_text="Filialen n", type="category")
    fig.update_yaxes(title_text="Elementarschritte", type="log")
    return _base(fig, 320, legend_y=-0.3)


def build_noise_curve(rows):
    """Über das Rauschen sigma: Anteil der Läufe, in denen sich der Baum ändert, Anteil mit Vorhersage "eine Kante überschreitet", Verpasste und Fehlalarme."""
    xs = [f"{r['sigma']:g} %" for r in rows]
    fig = go.Figure()
    for key, name, color, dash in (("changed", "Baum ändert sich", TREE_COLOR, "solid"), ("predicted", "Vorhersage: eine Kante überschreitet", "#7b3fbf", "dash"), ("missed", "verpasst", RED, "solid"),
                                   ("false_alarm", "Fehlalarm", ORANGE, "solid")):
        fig.add_trace(go.Scatter(x=xs, y=[r[key] for r in rows], mode="lines+markers", line=dict(color=color, width=2.6, dash=dash), name=name))
    fig.update_xaxes(title_text="Rauschen (+- Prozent je Kante)", type="category")
    fig.update_yaxes(title_text="Anteil der Läufe (%)")
    return _base(fig, 340, legend_y=-0.4)


def build_sweep(rows, param_label, series, y_label, tick=None, log_y=False):
    """`series` = [(key, Name, Farbe)]: Median als Linie, 10. bis 90. Perzentil als Band (`<key>_lo`/`<key>_hi`)."""
    xs = [tick(r["value"]) if tick else str(r["value"]) for r in rows]
    fig = go.Figure()
    for key, name, color in series:
        ys = [None if r[key] != r[key] else r[key] for r in rows]
        lo = [None if r.get(f"{key}_lo", r[key]) != r.get(f"{key}_lo", r[key]) else r.get(f"{key}_lo", r[key]) for r in rows]
        hi = [None if r.get(f"{key}_hi", r[key]) != r.get(f"{key}_hi", r[key]) else r.get(f"{key}_hi", r[key]) for r in rows]
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        if all(v is not None for v in lo + hi):
            fig.add_trace(go.Scatter(x=xs + xs[::-1], y=hi + lo[::-1], mode="lines", fill="toself", fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.13)", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=color, width=2.5), name=name, connectgaps=False))
    fig.update_xaxes(title_text=param_label, type="category")
    fig.update_yaxes(title_text=y_label, type="log" if log_y else "linear")
    return _base(fig, 360, legend_y=-0.3)
