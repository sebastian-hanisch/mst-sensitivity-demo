"""Auswertung: wie stabil ist der billigste Baum, was kostet ein Ausfall, und was spart ein Update gegenüber der Neuberechnung?

- **Toleranz** (`rel`) = Spielraum einer Kante in Prozent ihrer Kosten: Baumkanten dürfen so viel teurer, Nichtbaumkanten so viel billiger werden, bevor der Baum wechselt; Brücken haben keine Grenze.
- **fragil** = Baumkante (keine Brücke) mit Toleranz unter 1 % bzw. 5 %.
- **Ausfall** = Baumkante fällt aus: Kostenanstieg des Baums in Prozent (Brücke: der Baum zerfällt).
- **Rauschen** (`noise_experiment`): jede Kante zufällig um +-sigma Prozent (gleichverteilt) verändert; wie oft ändert sich der Baum, und sagt "irgendeine Kante überschreitet ihre Einzeltoleranz" das voraus?
- **Strom** (`run_stream`): Update-Operationen (Kosten ändern, Einfügen, Löschen) gegen Neuberechnung mit Kruskal von vorn, in Elementarschritten (Näherungsmaß, nicht Laufzeit).
Alles deterministisch: Kennzahlen laufen über 5 feste Instanzen (Seeds 100000-100004), Median mit 10./90. Perzentil."""

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

import sens_algorithm as A
import sens_constants as C
import sens_scenario as S

INF = float("inf")


@dataclass(frozen=True)
class Settings:
    kind: str = "depot"
    n: int = C.DEFAULT_N
    k: int = C.DEFAULT_K
    terrain: float = C.DEFAULT_TERRAIN
    seed: int = C.DEFAULT_SEED
    sigma: float = C.DEFAULT_SIGMA
    stream_len: int = C.DEFAULT_STREAM_LEN
    mix: str = C.DEFAULT_MIX


@lru_cache(maxsize=256)
def instance_of(settings):
    if settings.kind == "textbook":
        return S.textbook_instance()
    return S.generate(settings.n, settings.k, settings.terrain, settings.seed)


def _median(values):
    values = [v for v in values if v is not None and v == v and v != INF]
    return float(np.median(values)) if values else float("nan")


@dataclass
class Analysis:
    settings: Settings
    inst: object
    run: object                        # KruskalRun
    naive: object                      # Tolerances
    fast: object                       # Tolerances (mit der Ordnung aus dem Kruskal-Lauf)
    table: list                        # Tol je Kante
    failures: list                     # Failure, kritischste zuerst

    @property
    def tree(self):
        return self.run.tree

    @property
    def cost(self):
        return self.run.cost

    @property
    def tree_tols(self):
        return [t for t in self.table if t.tree]

    @property
    def nontree_tols(self):
        return [t for t in self.table if not t.tree]

    @property
    def bridges(self):
        return [t.edge for t in self.tree_tols if t.bridge]

    @property
    def bridge_share(self):
        return 100.0 * len(self.bridges) / len(self.tree)

    def tree_rel(self):
        return [t.rel for t in self.tree_tols if not t.bridge]

    def nontree_rel(self):
        return [t.rel for t in self.nontree_tols]

    def fragile(self, pct):
        """Anteil der Baumkanten ohne Brücken mit Toleranz unter `pct` Prozent (an allen Baumkanten gemessen: Brücken zählen nicht als fragil)."""
        vals = self.tree_rel()
        return 100.0 * sum(v < pct for v in vals) / len(self.tree)

    def fail_rel(self):
        return [f.rel for f in self.failures if f.rep is not None]

    @property
    def steps_ratio(self):
        return self.fast.steps / self.naive.steps if self.naive.steps else 1.0


def analyse(settings):
    inst = instance_of(settings)
    run = A.mst(inst.n, inst.edges)
    naive = A.tolerances_naive(inst.n, inst.edges, run.tree)
    fast = A.tolerances_fast(inst.n, inst.edges, run.tree, order=run.order)
    table = A.tolerance_table(inst.edges, fast)
    return Analysis(settings, inst, run, naive, fast, table, A.failure_table(inst.n, inst.edges, run.tree))


# --- Rauschen -------------------------------------------------------------------------------------------------------------------------------------


def noisy_edges(edges, sigma, rng):
    """Jede Kante um +-sigma Prozent (gleichverteilt) verändert (wie kruskal-demo `instability`)."""
    eps = sigma / 100.0
    return [(u, v, w * (1.0 + eps * float(rng.uniform(-1.0, 1.0)))) for u, v, w in edges]


def noise_detail(a, sigma, t):
    """Rausch-Lauf t: (verrauschte Kanten, neuer Baum als Menge, Nummern der Kanten, die ihre Einzeltoleranz überschreiten)."""
    inst = a.inst
    rng = np.random.default_rng([inst.seed, 31, t])
    noisy = noisy_edges(inst.edges, sigma, rng)
    new_tree = set(A.mst(inst.n, noisy).tree)
    over = [i for i in range(inst.m) if A.exceeds(inst.edges, a.table, i, noisy[i][2])]
    return noisy, new_tree, over


def noise_trial(a, sigma, t):
    """Ein Rausch-Lauf: (Baum geändert?, Zahl getauschter Kanten, Vorhersage "irgendeine Kante überschreitet ihre Einzeltoleranz", Zahl der überschreitenden Kanten)."""
    _noisy, new_tree, over = noise_detail(a, sigma, t)
    old = set(a.tree)
    return new_tree != old, len(new_tree - old), len(over) > 0, len(over)


def instability(a, sigma=1.0, trials=20):
    """Anteil der Läufe (Prozent), in denen das Rauschen den Baum ändert; gleiche Zufallsströme wie kruskal-demo."""
    return 100.0 * sum(noise_trial(a, sigma, t)[0] for t in range(trials)) / trials


def noise_experiment(base, sigma=None, seeds=C.FEAS_SEEDS, trials=20):
    """Über `seeds` Instanzen x `trials` Rausch-Läufe: Änderungsrate, mittlere Zahl getauschter Kanten (bei Änderung), Trefferquote der Einzeltoleranz-Vorhersage: Verpasst = Baum ändert sich, obwohl jede Kante
    innerhalb ihrer Toleranz blieb (gemeinsame Änderungen); Fehlalarm = eine Kante überschreitet, der Baum bleibt trotzdem."""
    sigma = base.sigma if sigma is None else sigma
    tot = changed = predicted = missed = false_alarm = swaps = 0
    over_sum = 0
    for seed in seeds:
        a = analyse(replace(base, seed=seed))
        for t in range(trials):
            ch, sw, pred, over = noise_trial(a, sigma, t)
            tot += 1
            changed += ch
            predicted += pred
            missed += ch and not pred
            false_alarm += pred and not ch
            swaps += sw if ch else 0
            over_sum += over
    return {"n_runs": tot, "changed": 100.0 * changed / tot, "predicted": 100.0 * predicted / tot, "missed": 100.0 * missed / tot, "false_alarm": 100.0 * false_alarm / tot,
            "swaps": swaps / changed if changed else 0.0, "missed_share": 100.0 * missed / changed if changed else 0.0, "false_share": 100.0 * false_alarm / predicted if predicted else 0.0,
            "over_mean": over_sum / tot}


# --- Update-Strom -----------------------------------------------------------------------------------------------------------------------------------


@dataclass
class StreamStep:
    kind: str                          # "insert" | "delete" | "cost"
    edge: int
    ends: tuple
    old: object                        # alte Kosten (None beim Einfügen)
    new: object                        # neue Kosten (None beim Löschen)
    update_steps: int
    recompute_steps: int
    presorted_steps: int               # Neuberechnung mit gehaltener Sortierung (nur Union-Find)
    changed: bool
    on_tree: bool                      # die Kante lag vor der Operation im Baum (Löschen/Kosten) bzw. liegt danach im Baum (Einfügen)
    cost: float                        # Baumkosten danach
    tree: list                         # Baumkanten danach als Paare (u, v)
    swapped_out: object
    swapped_in: object


@dataclass
class Stream:
    steps: list
    ends: dict                         # alle je vorhandenen Kanten: Nummer -> (u, v)
    start_tree: list
    start_cost: float

    def totals(self):
        return sum(s.update_steps for s in self.steps), sum(s.recompute_steps for s in self.steps)

    def presorted_total(self):
        return sum(s.presorted_steps for s in self.steps)


def run_stream(inst, length, mix, seed=None, verify=False):
    """Führt `length` Operationen aus (Strom aus dem festen Zufallsstrom [seed, 1010]) und rechnet nach jeder Operation Kruskal von vorn für den Schrittvergleich. `verify`: gehaltener Baum == Neuberechnung."""
    seed = inst.seed if seed is None else seed
    rng = np.random.default_rng([int(seed), 1010])
    d = A.DynamicMST(inst.n, inst.edges)
    ends = dict(d.ends)
    steps = []
    start_tree = sorted(d.tree)
    start_cost = d.cost()
    for _ in range(int(length)):
        alive = d.alive()
        kind = None
        if mix == "failures":
            trees = sorted(d.tree)
            if not trees:
                break
            kind = "delete"
            e = int(rng.choice(trees))
        elif mix == "costs":
            kind = "cost"
            e = int(rng.choice(alive))
        else:
            r = rng.random()
            kind = "cost" if r < 0.5 else ("insert" if r < 0.75 else "delete")
            e = int(rng.choice(alive)) if alive else None
        pairs = set(d.ends.values())
        if kind == "insert":
            u = v = None
            for _try in range(60):
                a, b = sorted(int(x) for x in rng.choice(inst.n, size=2, replace=False))
                if (a, b) not in pairs:
                    u, v = a, b
                    break
            if u is None:
                kind = "cost"
            else:
                dist = float(np.hypot(*(inst.xy[u] - inst.xy[v])))
                w = dist * float(rng.uniform(1.0, 1.0 + inst.terrain))
                op = d.insert(u, v, w)
                ends[op.edge] = (u, v)
                old, new, on_tree = None, w, op.edge in d.tree
        if kind == "delete":
            if e is None:
                break
            on_tree = e in d.tree
            old, new = d.w[e], None
            uv = d.ends[e]
            op = d.delete(e)
        if kind == "cost":
            on_tree = e in d.tree
            old = d.w[e]
            new = old * float(rng.uniform(0.6, 1.6))
            uv = d.ends[e]
            op = d.set_cost(e, new)
        ref = A.kruskal(inst.n, d.items())
        by_id = {i: (i, u, v, w) for i, u, v, w in d.items()}
        pre = A.presorted_steps(inst.n, [by_id[i] for i in ref.order])
        if verify:
            assert set(ref.tree) == d.tree
        uv = ends[op.edge]
        steps.append(StreamStep(op.kind, op.edge, uv, old, new, op.steps, ref.steps, pre, op.changed, on_tree, d.cost(), [d.ends[i] for i in sorted(d.tree)], op.swapped_out, op.swapped_in))
    return Stream(steps, ends, [inst.edges[i][:2] for i in start_tree], start_cost)


def stream_summary(st):
    """Elementarschritte je Operationsart: Update, Neuberechnung, Verhältnis; Anteil der Operationen, die den Baum ändern."""
    out = {"n_ops": len(st.steps)}
    ut, rt = st.totals()
    out["update_steps"], out["recompute_steps"] = ut, rt
    out["ratio"] = ut / rt if rt else float("nan")
    pt = st.presorted_total()
    out["presorted_steps"] = pt
    out["ratio_presorted"] = ut / pt if pt else float("nan")
    out["changed_share"] = 100.0 * sum(s.changed for s in st.steps) / len(st.steps) if st.steps else 0.0
    for kind in ("insert", "delete", "cost"):
        rows = [s for s in st.steps if s.kind == kind]
        out[f"{kind}_n"] = len(rows)
        out[f"{kind}_update"] = float(np.mean([s.update_steps for s in rows])) if rows else float("nan")
        out[f"{kind}_recompute"] = float(np.mean([s.recompute_steps for s in rows])) if rows else float("nan")
        out[f"{kind}_presorted"] = float(np.mean([s.presorted_steps for s in rows])) if rows else float("nan")
    for tree_flag, name in ((True, "tree"), (False, "nontree")):
        rows = [s for s in st.steps if s.kind == "delete" and s.on_tree == tree_flag]
        out[f"delete_{name}_n"] = len(rows)
        out[f"delete_{name}_update"] = float(np.mean([s.update_steps for s in rows])) if rows else float("nan")
        out[f"delete_{name}_recompute"] = float(np.mean([s.recompute_steps for s in rows])) if rows else float("nan")
        out[f"delete_{name}_presorted"] = float(np.mean([s.presorted_steps for s in rows])) if rows else float("nan")
    return out


def stream_experiment(base, seeds=C.FEAS_SEEDS):
    """Über `seeds` Instanzen: Gesamtschritte Update gegen Neuberechnung (Median und Summe des Verhältnisses) und mittlere Schritte je Operationsart."""
    sums = [stream_summary(run_stream(instance_of(replace(base, seed=s)), base.stream_len, base.mix)) for s in seeds]
    out = {"n_runs": len(sums), "ratio_median": _median([s["ratio"] for s in sums]), "ratio_total": sum(s["update_steps"] for s in sums) / sum(s["recompute_steps"] for s in sums),
           "changed_share": float(np.mean([s["changed_share"] for s in sums])), "cheaper_share": 100.0 * sum(s["update_steps"] < s["recompute_steps"] for s in sums) / len(sums),
           "ratio_presorted_median": _median([s["ratio_presorted"] for s in sums]), "ratio_presorted_total": sum(s["update_steps"] for s in sums) / sum(s["presorted_steps"] for s in sums),
           "cheaper_presorted_share": 100.0 * sum(s["update_steps"] < s["presorted_steps"] for s in sums) / len(sums)}
    for key in ("insert", "delete", "cost", "delete_tree", "delete_nontree"):
        for what in ("update", "recompute", "presorted"):
            vals = [s[f"{key}_{what}"] for s in sums if s[f"{key}_{what}"] == s[f"{key}_{what}"]]
            out[f"{key}_{what}"] = float(np.mean(vals)) if vals else float("nan")
        out[f"{key}_n"] = float(np.mean([s[f"{key}_n"] for s in sums]))
    return out


# --- Kennzahlen über feste Instanzen ------------------------------------------------------------------------------------------------------------


def _stats(values):
    values = [v for v in values if v is not None and v == v and v != INF]
    if not values:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(values)), float(np.percentile(values, 10)), float(np.percentile(values, 90))


def run_config(base, seeds=C.SWEEP_SEEDS, **changes):
    s0 = replace(base, **changes)
    rows = []
    for seed in seeds:
        a = analyse(replace(s0, seed=seed))
        st = stream_summary(run_stream(a.inst, s0.stream_len, s0.mix))
        fr = a.fail_rel()
        rows.append({"m": a.inst.m, "tree_rel": _median(a.tree_rel()), "nontree_rel": _median(a.nontree_rel()), "fragile1": a.fragile(1.0), "fragile5": a.fragile(5.0), "bridge_share": a.bridge_share,
                     "fail_rel": _median(fr), "fail_rel_max": max(fr) if fr else float("nan"), "naive_steps": a.naive.steps, "fast_steps": a.fast.steps, "steps_ratio": a.steps_ratio,
                     "instab": instability(a, s0.sigma), "stream_ratio": st["ratio"], "stream_ratio_presorted": st["ratio_presorted"], "stream_changed": st["changed_share"], "cost": a.cost})
    out = {"n_runs": len(rows)}
    for key in rows[0]:
        out[key], out[f"{key}_lo"], out[f"{key}_hi"] = _stats([r[key] for r in rows])
    return out


SWEEP_VALUES = {"n": (10, 20, 40, 80), "k": (3, 4, 6, 10, 20, 1000), "terrain": (0.0, 0.2, 0.4, 0.6, 1.0), "sigma": C.SIGMA_OPTIONS, "mix": C.MIXES}
SWEEP_LABELS = {"n": "Filialen n", "k": "Nachbarn k (1000 = vollständig)", "terrain": "Geländezuschlag", "sigma": "Rauschen (%)", "mix": "Art der Updates"}
SWEEP_TICKS = {"mix": lambda v: C.MIX_LABELS[v].split(" (")[0]}


def sweep(param, base=Settings(), values=None):
    values = SWEEP_VALUES[param] if values is None else values
    return [{"value": v, **run_config(base, **{param: v})} for v in values]


def tolerance_steps_curve(base, ns=None):
    """Elementarschritte von naiver und schneller Toleranzberechnung über n (5 feste Instanzen, Median)."""
    ns = ns if ns is not None else C.N_SWEEP
    rows = []
    for n in ns:
        an = [analyse(replace(base, n=n, seed=s)) for s in C.SWEEP_SEEDS]
        rows.append({"n": n, "m": _median([a.inst.m for a in an]), "naive": _median([a.naive.steps for a in an]), "fast": _median([a.fast.steps for a in an])})
    return rows


def tolerance_quality(base, seeds=C.FEAS_SEEDS):
    """Über `seeds` Instanzen mit den Einstellungen von `base` (nur der Seed wechselt): Verteilung des Spielraums (Median der Instanz-Mediane, 10. und 25. Perzentil über alle Baumkanten zusammen),
    Anteil fragiler Baumkanten (< 1 %, < 5 %), Brücken (Anteil der Baumkanten, Anteil der Instanzen mit mindestens einer), Ausfallkosten (Median, größter Ausfall im Median) und Schritte naiv/schnell."""
    an = [analyse(replace(base, seed=s)) for s in seeds]
    pooled = [v for a in an for v in a.tree_rel()]
    fr = [a.fail_rel() for a in an]
    return {"n_runs": len(an), "tree_med": float(np.median([_median(a.tree_rel()) for a in an])), "tree_p10": float(np.percentile(pooled, 10)), "tree_p25": float(np.percentile(pooled, 25)),
            "nontree_med": float(np.median([_median(a.nontree_rel()) for a in an])), "frag1": float(np.mean([a.fragile(1.0) for a in an])), "frag5": float(np.mean([a.fragile(5.0) for a in an])),
            "bridge": float(np.mean([a.bridge_share for a in an])), "bridge_any": 100.0 * float(np.mean([a.bridge_share > 0 for a in an])),
            "fail_med": float(np.median([_median(f) for f in fr])), "fail_max_med": float(np.median([max(f) if f else float("nan") for f in fr])),
            "steps_naive": float(np.median([a.naive.steps for a in an])), "steps_fast": float(np.median([a.fast.steps for a in an])), "m": float(np.median([a.inst.m for a in an]))}
