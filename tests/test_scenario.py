"""Instanz: Kopie treu zur Kruskal-Demo, Aufbau, Dichte, Determinismus, Lehrbuchbeispiel."""

import numpy as np
import pytest

import sens_constants as C
import sens_scenario as S
from brute import connected


def test_copy_matches_the_kruskal_demo():
    """Die Kopie ist treu: derselbe Plan wie in kruskal-demo (Seed 35, 30 Filialen, k = 6, Zuschlag 0.3, exakte Kosten): 113 Kanten, Baumkosten 466.63 (Zahlen aus kruskal-demo)."""
    inst = S.generate(30, 6, 0.3, 35)
    assert inst.m == 113 and inst.n == 31
    from sens_algorithm import mst
    assert mst(inst.n, inst.edges).cost == pytest.approx(466.63, abs=0.01)
    assert S.generate(30, 3, 0.3, 35).m == 59 and S.generate(30, 1000, 0.3, 35).m == 465


@pytest.mark.parametrize("k", [3, 6, 20, 1000])
def test_instance_structure(k):
    inst = S.generate(25, k, 0.4, 3)
    assert inst.n == 26 and inst.depot == 0 and inst.kind == "depot"
    assert all(u < v for u, v, _w in inst.edges) and list(inst.edges) == sorted(inst.edges, key=lambda e: (e[0], e[1]))
    assert all(w > 0 for _u, _v, w in inst.edges) and connected(inst.n, inst.edges)
    assert len({(u, v) for u, v, _w in inst.edges}) == inst.m
    if k >= 1000:
        assert inst.m == 26 * 25 // 2


def test_terrain_only_scales_the_costs_and_seed_changes_the_plan():
    flat, hilly = S.generate(20, 1000, 0.0, 5), S.generate(20, 1000, 1.0, 5)
    assert all(hw >= fw - 1e-12 for (_a, _b, fw), (_c, _d, hw) in zip(flat.edges, hilly.edges))
    assert flat.edges != hilly.edges and S.generate(20, 6, 0.3, 5).edges != S.generate(20, 6, 0.3, 6).edges
    assert S.generate(20, 6, 0.3, 5).edges == S.generate(20, 6, 0.3, 5).edges


def test_textbook_instance():
    inst = S.textbook_instance()
    assert inst.n == 5 and inst.m == 7 and inst.labels == ("A", "B", "C", "D", "E") and inst.kind == "textbook"
    assert [w for _u, _v, w in inst.edges] == [4.0, 5.0, 6.0, 2.0, 7.0, 3.0, 8.0]


def test_constants_are_consistent():
    assert C.DEFAULT_K in C.K_OPTIONS and C.DEFAULT_SIGMA in C.SIGMA_OPTIONS and C.DEFAULT_TERRAIN in C.TERRAIN_OPTIONS and C.DEFAULT_STREAM_LEN in C.STREAM_LEN_OPTIONS
    assert C.N_MIN <= C.DEFAULT_N <= C.N_MAX and C.DEFAULT_MIX in C.MIXES and list(C.STEPS) == [1, 2, 3, 4]
    assert np.isclose(sum(C.SWEEP_SEEDS), 5 * 100002)
