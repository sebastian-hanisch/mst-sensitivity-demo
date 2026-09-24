"""Korrektheitskette (vor jeder Messung): Toleranzen gegen Neuberechnung des MST, Ersatzkante/Brücke gegen Brute-Force, schnell == naiv, Dynamik == Neuberechnung nach jeder Operation, Buchführung von Hand,
Einzeltoleranz gegen gemeinsame Änderung, Sonderfälle."""

import numpy as np
import pytest

import sens_algorithm as A
import sens_scenario as S
from brute import brute_path_edges, connected, random_graph, ref_mst


def _tolerances(n, edges):
    tree = A.mst(n, edges).tree
    return tree, A.tolerance_table(edges, A.tolerances_fast(n, edges, tree))


def _changed(n, edges, i, new_w):
    e2 = list(edges)
    e2[i] = (edges[i][0], edges[i][1], new_w)
    return ref_mst(n, e2) != ref_mst(n, edges)


# --- 1. Toleranzen direkt gegen Neuberechnung -------------------------------------------------------------------------------------------------------


def test_tolerances_against_recomputation_including_ties():
    rng = np.random.default_rng(1)
    checked = 0
    for it in range(120):
        n = int(rng.integers(3, 9))
        edges = random_graph(rng, n=n, extra=int(rng.integers(0, 6)), wmax=int(rng.choice([3, 8])), integer=bool(it % 2))
        tree, tab = _tolerances(n, edges)
        assert set(tree) == ref_mst(n, edges)
        for t in tab:
            i = t.edge
            w = edges[i][2]
            eps = 1e-6
            if t.bridge:
                for w2 in (0.0, w * 3 + 10):
                    assert not _changed(n, edges, i, w2)
                continue
            b = t.bound
            if t.tree:
                assert not _changed(n, edges, i, max(0.0, b - eps)) and _changed(n, edges, i, b + eps)
                assert not _changed(n, edges, i, 0.0)                                       # billiger ändert nie etwas
                assert _changed(n, edges, i, b) == (not i < t.other)                         # Gleichstand entscheidet die Nummer
                assert t.margin == pytest.approx(b - w) and t.margin >= 0
            else:
                assert not _changed(n, edges, i, b + eps) and (b - eps < 0 or _changed(n, edges, i, b - eps))
                assert not _changed(n, edges, i, w * 5 + 10)                                 # teurer ändert nie etwas
                assert _changed(n, edges, i, b) == (i < t.other)
                assert t.margin == pytest.approx(w - b) and t.margin >= 0
            checked += 1
    assert checked > 400


# --- 2. Ersatzkante und Brücken gegen Brute-Force ---------------------------------------------------------------------------------------------------


def test_failure_replacement_bridges_against_brute_force():
    rng = np.random.default_rng(2)
    bridges = 0
    for it in range(150):
        n = int(rng.integers(3, 9))
        edges = random_graph(rng, n=n, extra=int(rng.integers(0, 5)), wmax=5, integer=bool(it % 2))
        tree = A.mst(n, edges).tree
        base = sum(edges[i][2] for i in tree)
        for e in tree:
            rest = {i: x for i, x in enumerate(edges) if i != e}
            f = A.failure(n, edges, tree, e)
            expected = ref_mst(n, rest)
            assert set(f.new_tree) == expected
            if connected(n, rest):
                assert f.rep is not None and f.delta == pytest.approx(sum(edges[i][2] for i in expected) - base)
                assert f.rel == pytest.approx(100 * f.delta / base)
            else:
                assert f.rep is None and f.delta == float("inf") and len(expected) == len(tree) - 1
                bridges += 1
            assert f.side == {x for x in f.side} and edges[e][0] in f.side and edges[e][1] not in f.side
    assert bridges > 40
    with pytest.raises(ValueError):
        A.failure(3, [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 3.0)], [0, 1], 2)


def test_failure_table_orders_the_critical_edges_first():
    rng = np.random.default_rng(3)
    for _ in range(30):
        n = 8
        edges = random_graph(rng, n=n, extra=4)
        tree = A.mst(n, edges).tree
        tab = A.failure_table(n, edges, tree)
        assert sorted(f.edge for f in tab) == sorted(tree)
        flags = [f.rep is not None for f in tab]
        assert flags == sorted(flags)                                                       # Brücken zuerst
        deltas = [f.delta for f in tab if f.rep is not None]
        assert deltas == sorted(deltas, reverse=True)


# --- 3. schnell == naiv ----------------------------------------------------------------------------------------------------------------------------


def test_fast_equals_naive_and_brute_force_paths():
    rng = np.random.default_rng(4)
    for it in range(320):
        n = int(rng.integers(2, 12))
        edges = random_graph(rng, n=n, extra=int(rng.integers(0, 14)), wmax=int(rng.choice([2, 4, 20])), integer=bool(it % 3))
        run = A.mst(n, edges)
        naive = A.tolerances_naive(n, edges, run.tree)
        fast = A.tolerances_fast(n, edges, run.tree, order=run.order)
        own = A.tolerances_fast(n, edges, run.tree)
        assert naive.rep == fast.rep == own.rep and naive.pmax == fast.pmax == own.pmax, it
        assert fast.sort_steps == 0 and own.sort_steps > 0 or len(edges) < 2
        for f, g in fast.pmax.items():
            path = brute_path_edges(n, edges, run.tree, edges[f][0], edges[f][1])
            assert g == max(path, key=lambda i: (edges[i][2], i))


def test_fast_rejects_a_disconnected_graph():
    with pytest.raises(ValueError):
        A.tolerances_fast(3, [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 3.0)], [0])


# --- 4. Dynamik == Neuberechnung nach jeder Operation -----------------------------------------------------------------------------------------------


def test_dynamic_tree_equals_recomputation_after_every_operation():
    rng = np.random.default_rng(5)
    ops = 0
    kinds = {"insert": 0, "delete": 0, "cost": 0}
    changed = 0
    for it in range(40):
        n = int(rng.integers(3, 12))
        edges = random_graph(rng, n=n, extra=int(rng.integers(0, 10)), wmax=int(rng.choice([3, 9])), integer=bool(it % 2))
        d = A.DynamicMST(n, edges)
        for _ in range(60):
            before = set(d.tree)
            alive = d.alive()
            r = rng.random()
            if r < 0.3 or not alive:
                u, v = sorted(int(x) for x in rng.choice(n, size=2, replace=False))
                op = d.insert(u, v, float(rng.integers(1, 9)) if it % 2 else float(rng.uniform(0.5, 9)))
            elif r < 0.6:
                op = d.delete(int(rng.choice(alive)))
            else:
                e = int(rng.choice(alive))
                op = d.set_cost(e, float(rng.integers(1, 9)) if it % 2 else float(rng.uniform(0.5, 9)))
            expected = ref_mst(n, {i: (d.ends[i][0], d.ends[i][1], d.w[i]) for i in d.ends})
            assert d.tree == expected, (it, op)
            assert d.cost() == pytest.approx(sum(d.w[i] for i in expected))
            after = set(d.tree)
            assert op.changed == (before != after), (op, before, after)
            assert op.steps >= 1
            kinds[op.kind] += 1
            changed += op.changed
            ops += 1
    assert ops == 2400 and all(v > 400 for v in kinds.values()) and changed > 400


def test_forest_after_a_bridge_failure_and_reconnection():
    edges = [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 5.0)]
    d = A.DynamicMST(3, edges)
    assert d.tree == {0, 1}
    d.delete(1)
    assert d.tree == {0, 2}                                                                # Ersatzkante 0-2 springt ein
    d.delete(2)
    assert d.tree == {0} and d.cost() == 1.0                                              # Brücke: Spannwald
    op = d.insert(1, 2, 7.0)
    assert d.tree == {0, 3} and op.changed and d.cost() == 8.0


# --- 5. Buchführung von Hand (Lehrbuchbeispiel) ------------------------------------------------------------------------------------------------------


def test_textbook_by_hand():
    inst = S.textbook_instance()
    run = A.mst(inst.n, inst.edges)
    assert set(run.tree) == {3, 5, 0, 2} and run.cost == 15.0 and run.connected
    tab = A.tolerance_table(inst.edges, A.tolerances_fast(inst.n, inst.edges, run.tree))
    by = {t.edge: t for t in tab}
    # Baumkanten: B-D (3) bis 5 (+3), C-E (5) bis 7 (+4), A-B (0) bis 5 (+1), B-C (2) bis 7 (+1)
    assert [(e, by[e].bound, by[e].margin, by[e].other) for e in (3, 5, 0, 2)] == [(3, 5.0, 3.0, 1), (5, 7.0, 4.0, 4), (0, 5.0, 1.0, 1), (2, 7.0, 1.0, 4)]
    # Nichtbaumkanten: A-D (1) bis 4 (-1), B-E (4) bis 6 (-1), D-E (6) bis 6 (-2)
    assert [(e, by[e].bound, by[e].margin, by[e].other) for e in (1, 4, 6)] == [(1, 4.0, 1.0, 0), (4, 6.0, 1.0, 2), (6, 6.0, 2.0, 2)]
    assert [round(by[e].rel, 6) for e in (3, 5, 0, 2, 1, 4, 6)] == [150.0, 133.333333, 25.0, 16.666667, 20.0, 14.285714, 25.0]
    f = A.failure(inst.n, inst.edges, run.tree, 3)
    assert f.rep == 1 and f.delta == 3.0 and f.steps == 9 and sorted(f.new_tree) == [0, 1, 2, 5]
    d = A.DynamicMST(inst.n, inst.edges)
    op = d.delete(3)
    assert (op.steps, op.changed, op.swapped_in) == (9, True, 1) and d.cost() == 18.0
    assert d.delete(4).steps == 1 and not d.delete(6).changed
    assert d.set_cost(0, 3.0).steps == 1 and d.cost() == 17.0                              # Baumkante billiger: nur Kosten
    d2 = A.DynamicMST(inst.n, inst.edges)
    assert d2.set_cost(1, 9.0).steps == 1 and d2.tree == {3, 5, 0, 2}                      # Nichtbaumkante teurer: nur Kosten
    assert d2.set_cost(1, 4.5).changed is False                                            # noch nicht unter A-B (Pfadmaximum 4): bleibt draußen
    assert d2.set_cost(1, 3.9).changed is True and d2.tree == {3, 5, 1, 2}


# --- 6. Einzeltoleranz gegen gemeinsame Änderung ----------------------------------------------------------------------------------------------------


def test_two_changes_inside_their_tolerances_can_still_change_the_tree():
    edges = [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 4.0)]
    tree, tab = _tolerances(3, edges)
    assert set(tree) == {0, 1} and tab[1].bound == 4.0 and tab[2].bound == 2.0
    e2 = list(edges)
    e2[1] = (1, 2, 3.9)                                                                     # innerhalb der Toleranz (bis 4.0)
    assert ref_mst(3, e2) == {0, 1}
    e3 = list(edges)
    e3[2] = (0, 2, 2.1)                                                                     # innerhalb der Toleranz (bis 2.0 runter)
    assert ref_mst(3, e3) == {0, 1}
    e2[2] = (0, 2, 2.1)                                                                     # beide zugleich: die Nichtbaumkante ist billiger als die Baumkante
    assert ref_mst(3, e2) == {0, 2}
    assert not A.exceeds(edges, tab, 1, 3.9) and not A.exceeds(edges, tab, 2, 2.1)
    assert A.exceeds(edges, tab, 1, 4.1) and A.exceeds(edges, tab, 2, 1.9)
    assert not A.exceeds(edges, tab, 1, 0.1) and not A.exceeds(edges, tab, 2, 50.0)


def test_one_change_beyond_the_tolerance_always_changes_the_tree():
    rng = np.random.default_rng(6)
    for it in range(60):
        n = 7
        edges = random_graph(rng, n=n, extra=5, wmax=7, integer=bool(it % 2))
        tree, tab = _tolerances(n, edges)
        for t in tab:
            for w2 in (t.cost * 0.5, t.cost * 2.5, t.cost + 3.0, max(0.0, t.cost - 3.0)):
                assert A.exceeds(edges, tab, t.edge, w2) == _changed(n, edges, t.edge, w2)


# --- 7. Sonderfälle ---------------------------------------------------------------------------------------------------------------------------------


def test_special_cases():
    one = [(0, 1, 2.0)]
    tree, tab = _tolerances(2, one)
    assert tree == [0] and tab[0].bridge and tab[0].margin == float("inf") and tab[0].rel == float("inf") and tab[0].bound is None
    path = [(0, 1, 1.0), (1, 2, 2.0), (2, 3, 3.0)]
    assert all(t.bridge for t in _tolerances(4, path)[1])
    f = A.failure(4, path, [0, 1, 2], 1)
    assert f.rep is None and f.new_tree == [0, 2] and f.delta == float("inf")
    full = [(u, v, 1.0) for u in range(5) for v in range(u + 1, 5)]
    tree, tab = _tolerances(5, full)
    assert set(tree) == ref_mst(5, full) and all(t.margin == 0.0 for t in tab)              # alle Kosten gleich: Toleranz 0, die Nummer entscheidet
    zero = [(0, 1, 0.0), (1, 2, 0.0), (0, 2, 0.0)]
    tree, tab = _tolerances(3, zero)
    assert all(t.rel == float("inf") or t.margin == 0.0 for t in tab)


def test_determinism_and_instance_ties():
    inst = S.generate(20, 6, 0.3, 4)
    a, b = A.mst(inst.n, inst.edges), A.mst(inst.n, S.generate(20, 6, 0.3, 4).edges)
    assert a.tree == b.tree and a.order == b.order
    assert set(a.tree) == ref_mst(inst.n, inst.edges) and len(a.tree) == inst.n - 1
