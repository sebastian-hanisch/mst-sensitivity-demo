"""Unabhängige Orakel (anderer Rechenweg als der Demo-Code): scipy.sparse.csgraph (MST-Kosten), networkx (Schnitt nach dem Entfernen einer Baumkante, Pfad im Baum), Neuberechnung des MST
nach jeder Änderung mit einem eigenen Kruskal (Ordnung (Kosten, Nummer)) für Toleranzgrenzen, Ausfall, Rausch-Alarm und dynamischen Baum."""

import math

import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import minimum_spanning_tree

import sens_algorithm as A
import sens_evaluation as ev

nx = pytest.importorskip("networkx")


def _forest(n, items):
    p = list(range(n))

    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    out = set()
    for i, (u, v, w) in sorted(items.items(), key=lambda t: (t[1][2], t[0])):
        a, b = find(u), find(v)
        if a != b:
            p[a] = b
            out.add(i)
    return out


def _graph(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(3, 10))
    pairs = {(int(rng.integers(0, v)), v) for v in range(1, n)}
    for _ in range(int(rng.integers(0, 12))):
        pairs.add(tuple(sorted(int(x) for x in rng.choice(n, 2, replace=False))))
    ties = seed % 2 == 0
    return n, [(u, v, float(rng.integers(1, 6)) if ties else float(rng.uniform(0.5, 6))) for u, v in sorted(pairs)], rng


@pytest.mark.parametrize("seed", range(60))
def test_tolerances_failures_and_cost_equal_recomputation(seed):
    n, edges, rng = _graph(seed)
    items = dict(enumerate(edges))
    run = A.mst(n, edges)
    tree = _forest(n, items)
    mat = coo_matrix(([w for _u, _v, w in edges], ([u for u, _v, _w in edges], [v for _u, v, _w in edges])), shape=(n, n))
    assert set(run.tree) == tree and run.cost == pytest.approx(minimum_spanning_tree(mat).sum())
    tol = A.tolerances_fast(n, edges, run.tree, order=run.order)
    table = A.tolerance_table(edges, tol)
    t_graph = nx.Graph()
    t_graph.add_nodes_from(range(n))
    for i in tree:
        t_graph.add_edge(edges[i][0], edges[i][1], id=i)
    for e in tree:
        cut = t_graph.copy()
        cut.remove_edge(edges[e][0], edges[e][1])
        side = nx.node_connected_component(cut, edges[e][0])
        cross = [f for f in range(len(edges)) if f not in tree and (edges[f][0] in side) != (edges[f][1] in side)]
        best = min(cross, key=lambda f: (edges[f][2], f)) if cross else None
        fail = A.failure(n, edges, run.tree, e)
        assert tol.rep[e] == best == fail.rep and fail.side == side
        after = _forest(n, {i: x for i, x in items.items() if i != e})
        assert set(fail.new_tree) == after
        if best is None:
            assert fail.delta == math.inf
        else:
            assert fail.delta == pytest.approx(sum(edges[i][2] for i in after) - run.cost)
    for f in range(len(edges)):
        if f in tree:
            continue
        path = nx.shortest_path(t_graph, edges[f][0], edges[f][1])
        assert tol.pmax[f] == max((t_graph[a][b]["id"] for a, b in zip(path, path[1:])), key=lambda i: (edges[i][2], i))
    for i, t in enumerate(table):
        probes = [float(rng.uniform(0.1, 8)), edges[i][2], 0.0] + ([] if t.bridge else [t.bound, t.bound - 1e-9, t.bound + 1e-9])
        for new_w in probes:
            if (i in tree and new_w >= edges[i][2]) or (i not in tree and new_w <= edges[i][2]):
                changed = _forest(n, {**items, i: (edges[i][0], edges[i][1], new_w)}) != tree
                assert A.exceeds(edges, table, i, new_w) == changed


@pytest.mark.parametrize("seed", range(25))
def test_dynamic_tree_equals_recomputation_after_every_operation(seed):
    n, edges, rng = _graph(seed + 500)
    d, items = A.DynamicMST(n, edges), dict(enumerate(edges))
    for _ in range(25):
        before, kind, alive = set(d.tree), str(rng.choice(["insert", "delete", "cost", "cost"])), sorted(items)
        if kind == "insert":
            u, v = sorted(int(x) for x in rng.choice(n, 2, replace=False))
            if (u, v) in {(a, b) for a, b, _w in items.values()}:
                continue
            w = float(rng.integers(1, 6))
            op = d.insert(u, v, w)
            items[op.edge] = (u, v, w)
        elif kind == "delete" and alive:
            e = int(rng.choice(alive))
            op = d.delete(e)
            del items[e]
        elif alive:
            e, w = int(rng.choice(alive)), float(rng.integers(1, 6))
            op = d.set_cost(e, w)
            items[e] = (items[e][0], items[e][1], w)
        else:
            continue
        assert d.tree == _forest(n, items) and op.changed == (d.tree != before)


@pytest.mark.parametrize("seed", range(4))
def test_noise_alarm_set_equals_single_edge_recomputation(seed):
    a = ev.analyse(ev.Settings("depot", 12 + seed, 4, 0.3, 880 + seed))
    items, base = dict(enumerate(a.inst.edges)), set(a.tree)
    for sigma in (1.0, 5.0):
        for t in range(6):
            noisy, new_tree, over = ev.noise_detail(a, sigma, t)
            assert new_tree == _forest(a.inst.n, dict(enumerate(noisy)))
            assert sorted(over) == [i for i in range(a.inst.m) if _forest(a.inst.n, {**items, i: noisy[i]}) != base]
