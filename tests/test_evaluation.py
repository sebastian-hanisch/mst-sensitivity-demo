"""Auswertung: Analyse, Toleranz-Kennzahlen, Rauschen (Zufallsströme wie kruskal-demo), Ströme, run_config, Sweeps, Schrittkurve."""

from dataclasses import replace

import pytest

import sens_algorithm as A
import sens_constants as C
import sens_evaluation as ev
from brute import ref_mst

FAST = ev.Settings(n=12, k=5, seed=3)


def test_analyse_is_consistent():
    a = ev.analyse(FAST)
    assert set(a.tree) == ref_mst(a.inst.n, a.inst.edges) and len(a.tree) == a.inst.n - 1
    assert a.naive.rep == a.fast.rep and a.naive.pmax == a.fast.pmax
    assert len(a.table) == a.inst.m and len(a.tree_tols) == len(a.tree) and len(a.nontree_tols) == a.inst.m - len(a.tree)
    assert len(a.failures) == len(a.tree) and a.bridge_share == pytest.approx(100.0 * len(a.bridges) / len(a.tree))
    assert all(v >= 0 for v in a.tree_rel() + a.nontree_rel()) and 0.0 <= a.fragile(5.0) <= 100.0 and a.fragile(1.0) <= a.fragile(5.0)
    assert a.steps_ratio == pytest.approx(a.fast.steps / a.naive.steps)


def test_bridges_do_not_count_as_fragile_and_are_excluded_from_the_relative_lists():
    a = ev.analyse(ev.Settings(n=30, k=3, seed=47))
    assert len(a.bridges) == 5 and len(a.tree_rel()) == len(a.tree) - 5
    assert a.fragile(1e9) == pytest.approx(100.0 * (len(a.tree) - 5) / len(a.tree))
    assert a.failures[0].rep is None and all(f.rep is None for f in a.failures[:5]) and all(f.rep is not None for f in a.failures[5:])


def test_instability_reproduces_the_kruskal_demo():
    """Dieselben Zufallsströme und dieselbe Definition wie kruskal-demo: Median über die 5 festen Instanzen (30 Filialen, k = 6, Zuschlag 0.3) 30 %, je Instanz 0/60/30/0/30 %."""
    vals = [ev.instability(ev.analyse(replace(ev.Settings(), seed=s)), 1.0) for s in C.SWEEP_SEEDS]
    assert vals == [0.0, 60.0, 30.0, 0.0, 30.0]


def test_noise_detail_and_trial_agree():
    a = ev.analyse(ev.Settings())
    for t in range(6):
        noisy, new_tree, over = ev.noise_detail(a, 2.0, t)
        assert new_tree == set(A.mst(a.inst.n, noisy).tree)
        ch, sw, pred, n_over = ev.noise_trial(a, 2.0, t)
        assert ch == (new_tree != set(a.tree)) and sw == len(new_tree - set(a.tree)) and pred == bool(over) and n_over == len(over)
        assert all(abs(noisy[i][2] / a.inst.edges[i][2] - 1.0) <= 0.02 + 1e-12 for i in range(a.inst.m))
    assert ev.noise_trial(a, 2.0, 0) == ev.noise_trial(a, 2.0, 0)


def test_noise_prediction_facts():
    """Eine einzelne Änderung jenseits der Toleranz ändert den Baum immer; Verpasst und Fehlalarm kommen bei Rauschen auf allen Kanten vor."""
    r = ev.noise_experiment(ev.Settings(n=20), 2.0, seeds=range(200000, 200015), trials=10)
    assert r["n_runs"] == 150 and 0 <= r["changed"] <= 100 and r["missed"] > 0 and r["false_alarm"] > 0
    assert r["changed"] == pytest.approx(r["predicted"] - r["false_alarm"] + r["missed"])
    assert r["missed_share"] == pytest.approx(100 * r["missed"] / r["changed"]) and r["swaps"] >= 1.0
    low, high = ev.noise_experiment(ev.Settings(n=20), 0.5, seeds=range(200000, 200015), trials=10), ev.noise_experiment(ev.Settings(n=20), 10.0, seeds=range(200000, 200015), trials=10)
    assert low["changed"] < r["changed"] < high["changed"]


def test_stream_matches_recomputation_step_by_step():
    for mix in C.MIXES:
        inst = ev.instance_of(replace(FAST, n=15))
        st = ev.run_stream(inst, 40, mix, verify=True)
        assert 0 < len(st.steps) <= 40
        for s in st.steps:
            assert s.update_steps >= 1 and s.recompute_steps > s.presorted_steps >= 0 and len(s.tree) <= inst.n - 1
        assert st.totals()[0] == sum(s.update_steps for s in st.steps)
        if mix == "failures":
            assert all(s.kind == "delete" and s.on_tree and s.changed for s in st.steps)
        if mix == "costs":
            assert all(s.kind == "cost" for s in st.steps)
    a = ev.run_stream(inst, 30, "mixed"), ev.run_stream(inst, 30, "mixed")
    assert [s.ends for s in a[0].steps] == [s.ends for s in a[1].steps] and a[0].start_cost == a[1].start_cost


def test_stream_summary_and_experiment():
    inst = ev.instance_of(FAST)
    sm = ev.stream_summary(ev.run_stream(inst, 40, "mixed"))
    assert sm["n_ops"] == 40 and sm["ratio"] == pytest.approx(sm["update_steps"] / sm["recompute_steps"]) and sm["ratio_presorted"] == pytest.approx(sm["update_steps"] / sm["presorted_steps"])
    assert sm["insert_n"] + sm["delete_n"] + sm["cost_n"] == 40 and sm["delete_tree_n"] + sm["delete_nontree_n"] == sm["delete_n"]
    ex = ev.stream_experiment(FAST, seeds=range(200000, 200006))
    assert ex["n_runs"] == 6 and 0 < ex["ratio_total"] < 1 and ex["cheaper_share"] == 100.0


def test_run_config_and_sweeps():
    out = ev.run_config(FAST)
    assert out["n_runs"] == 5
    for key in ("tree_rel", "nontree_rel", "fragile1", "fragile5", "bridge_share", "fail_rel", "instab", "stream_ratio", "stream_ratio_presorted", "steps_ratio", "naive_steps", "fast_steps"):
        assert f"{key}_lo" in out and f"{key}_hi" in out and out[f"{key}_lo"] <= out[key] + 1e-9 <= out[f"{key}_hi"] + 2e-9
    for param, values in (("n", (8, 12)), ("k", (3, 1000)), ("terrain", (0.0, 1.0)), ("sigma", (0.5, 5.0)), ("mix", C.MIXES)):
        rows = ev.sweep(param, FAST, values)
        assert [r["value"] for r in rows] == list(values)
    assert set(ev.SWEEP_VALUES) == set(ev.SWEEP_LABELS)


def test_tolerance_steps_curve_fast_beats_naive():
    rows = ev.tolerance_steps_curve(FAST, ns=(10, 20))
    assert [r["n"] for r in rows] == [10, 20] and all(r["fast"] < r["naive"] for r in rows)


def test_instance_of_textbook():
    assert ev.instance_of(ev.Settings(kind="textbook")).kind == "textbook"
    a = ev.analyse(ev.Settings(kind="textbook"))
    assert set(a.tree) == {0, 2, 3, 5} and a.cost == 15.0
