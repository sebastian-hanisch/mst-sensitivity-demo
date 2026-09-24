"""Jede Zahl in README und App-Texten (Grenzen-Tabelle, Hypothesen) über die echten Auswertungsfunktionen `ev.*` - nie über ein Ad-hoc-Skript. Bänder mit Sicherheitsabstand; ganzzahlige Aussagen exakt.
Standard: 30 Filialen + Depot, k = 6, Zuschlag 0.3; 50 Instanzen Seeds 200000-200049 (`tolerance_quality`, `noise_experiment`, `stream_experiment`) bzw. 5 feste Instanzen Seeds 100000-100004 (`run_config`)."""

from dataclasses import replace
from functools import lru_cache

import pytest

import sens_constants as C
import sens_evaluation as ev

B = ev.Settings()


@lru_cache(maxsize=None)
def T(**kw):
    return ev.tolerance_quality(replace(B, **kw))


@lru_cache(maxsize=None)
def NZ(sigma=1.0, **kw):
    return ev.noise_experiment(replace(B, **kw), sigma)


@lru_cache(maxsize=None)
def SX(**kw):
    return ev.stream_experiment(replace(B, **kw))


def within(x, lo, hi):
    assert lo <= x <= hi, (x, lo, hi)


# --- 1. Toleranzen: die meisten Kanten haben viel Spielraum, wenige entscheiden ---------------------------------------------------------------------


def test_most_edges_have_a_lot_of_room_and_a_few_decide():
    t = T()
    within(t["tree_med"], 27.0, 34.0), within(t["nontree_med"], 28.0, 35.0)
    within(t["tree_p10"], 3.0, 4.6), within(t["tree_p25"], 10.0, 13.5)
    within(t["frag1"], 2.0, 4.5), within(t["frag5"], 10.0, 15.0)
    assert t["frag1"] < t["frag5"] < 25.0 and t["tree_p10"] < 0.2 * t["tree_med"]


def test_room_is_independent_of_density_and_terrain_but_the_non_tree_room_grows_with_density():
    med = [T(k=k)["tree_med"] for k in (6, 10, 20, 1000)]
    assert max(med) - min(med) < 0.5                                                          # ab k = 6 liegt der Baum in den Kandidaten: derselbe Baum
    non = [T(k=k)["nontree_med"] for k in (3, 4, 6, 10, 20, 1000)]
    assert non == sorted(non) and within(non[0], 18.0, 25.0) is None and within(non[-1], 55.0, 66.0) is None
    for tr in (0.0, 0.6, 1.0):
        within(T(terrain=tr)["tree_med"], 29.0, 36.0)


def test_bridges_appear_only_in_sparse_networks():
    b3, b4, b6 = T(k=3), T(k=4), T()
    within(b3["bridge"], 3.5, 5.6), within(b3["bridge_any"], 58.0, 78.0)
    within(b4["bridge"], 0.1, 1.0), within(b4["bridge_any"], 4.0, 16.0)
    assert b6["bridge"] == 0.0 and b6["bridge_any"] == 0.0 and T(k=1000)["bridge_any"] == 0.0


def test_failure_costs_shrink_with_the_network_size():
    within(T()["fail_med"], 0.8, 1.2), within(T()["fail_max_med"], 3.6, 4.8)
    meds = [T(n=n)["fail_med"] for n in (10, 20, 40, 80)]
    assert meds == sorted(meds, reverse=True)
    within(meds[0], 2.7, 3.8), within(meds[-1], 0.25, 0.5)
    within(T(n=10)["fail_max_med"], 9.0, 14.0), within(T(n=80)["fail_max_med"], 1.5, 2.3)


def test_fast_tolerances_need_fewer_steps_than_naive_ones():
    for n in (10, 40, 80):
        t = T(n=n)
        assert t["steps_fast"] < t["steps_naive"]
    within(T(n=10)["steps_fast"] / T(n=10)["steps_naive"], 0.30, 0.46), within(T()["steps_fast"] / T()["steps_naive"], 0.12, 0.19), within(T(n=80)["steps_fast"] / T(n=80)["steps_naive"], 0.04, 0.09)
    within(T(n=10)["steps_naive"], 650.0, 780.0), within(T()["steps_naive"], 5000.0, 5900.0), within(T(n=80)["steps_naive"], 32000.0, 38500.0)
    within(T(n=10)["steps_fast"], 245.0, 300.0), within(T()["steps_fast"], 760.0, 900.0), within(T(n=80)["steps_fast"], 2050.0, 2450.0)
    ratios = [T(n=n)["steps_fast"] / T(n=n)["steps_naive"] for n in (10, 20, 40, 80)]
    assert ratios == sorted(ratios, reverse=True)                                              # der Vorsprung wächst mit n


# --- 2. Rauschen und Vorhersage --------------------------------------------------------------------------------------------------------------------


def test_noise_changes_the_tree_more_often_the_stronger_it_is():
    ch = [NZ(s)["changed"] for s in C.SIGMA_OPTIONS]
    assert ch == sorted(ch)
    within(ch[0], 12.0, 20.0), within(ch[1], 24.0, 32.0), within(ch[2], 38.0, 48.0), within(ch[3], 69.0, 79.0), within(ch[4], 91.0, 98.0)
    sw = [NZ(s)["swaps"] for s in C.SIGMA_OPTIONS]
    within(sw[1], 1.0, 1.3), within(sw[4], 2.3, 3.0)


def test_single_tolerances_predict_the_change_well_but_not_perfectly():
    for s, (pl, ph), (ml, mh), (fl, fh) in ((0.5, (19, 28), (0.8, 2.8), (6.5, 11.5)), (1.0, (32, 41), (2.8, 5.2), (9.5, 15.0)), (2.0, (50, 60), (3.5, 6.5), (13.0, 21.0)), (5.0, (80, 89), (2.0, 4.6), (10.0, 16.5)),
                                            (10.0, (94, 99), (0.8, 3.0), (2.0, 5.5))):
        r = NZ(s)
        within(r["predicted"], pl, ph), within(r["missed"], ml, mh), within(r["false_alarm"], fl, fh)
        assert r["changed"] == pytest.approx(r["predicted"] - r["false_alarm"] + r["missed"])
    r = NZ(1.0)
    within(r["missed_share"], 10.0, 19.0), within(r["false_share"], 28.0, 40.0), within(r["over_mean"], 0.4, 0.62)


def test_noise_depends_on_the_network_size_and_barely_on_the_density():
    n10, n80 = NZ(1.0, n=10), NZ(1.0, n=80)
    within(n10["changed"], 3.0, 10.0), within(n80["changed"], 44.0, 55.0)
    within(NZ(1.0, k=3)["changed"], 23.0, 32.0), within(NZ(1.0, k=1000)["changed"], 26.0, 36.0)


# --- 3. Update gegen Neuberechnung --------------------------------------------------------------------------------------------------------------------


def test_updates_cost_a_few_percent_of_a_full_recomputation():
    mixed, costs = SX(), SX(mix="costs")
    within(mixed["ratio_total"], 0.02, 0.04), within(costs["ratio_total"], 0.018, 0.035)
    assert mixed["cheaper_share"] == 100.0 and costs["cheaper_share"] == 100.0
    within(mixed["changed_share"], 10.0, 18.0), within(costs["changed_share"], 10.0, 18.0)
    for n in (10, 20, 40, 80):
        within(SX(n=n)["ratio_total"], 0.02, 0.045)


def test_against_a_kept_sorting_updates_still_win_on_average():
    mixed = SX()
    within(mixed["ratio_presorted_total"], 0.08, 0.14)
    within(mixed["insert_update"], 30.0, 41.0), within(mixed["insert_presorted"], 220.0, 290.0)
    within(mixed["cost_update"], 21.0, 30.0), assert_eq(mixed["delete_nontree_update"], 1.0)
    within(mixed["delete_tree_update"], 90.0, 130.0), within(mixed["delete_tree_presorted"], 220.0, 290.0)
    assert SX(n=80)["ratio_presorted_total"] < SX(n=10)["ratio_presorted_total"] < 0.3


def assert_eq(x, y):
    assert x == y


def test_deleting_tree_edges_loses_in_dense_graphs():
    sparse, k20, dense, dense60 = SX(mix="failures"), SX(mix="failures", k=20), SX(mix="failures", k=1000), SX(mix="failures", k=1000, n=60)
    within(sparse["ratio_presorted_median"], 0.30, 0.45), assert_eq(sparse["cheaper_presorted_share"], 100.0)
    within(k20["ratio_presorted_median"], 1.0, 1.3), within(k20["cheaper_presorted_share"], 25.0, 48.0)
    within(dense["ratio_presorted_median"], 1.25, 1.7), within(dense["cheaper_presorted_share"], 2.0, 16.0)
    within(dense60["ratio_presorted_median"], 2.2, 3.0), within(dense60["cheaper_presorted_share"], 0.0, 8.0)
    within(dense["ratio_median"], 0.06, 0.12)                                                  # gegen Kruskal von vorn (mit Sortieren) gewinnt das Update immer
    assert dense["ratio_median"] < 0.15 and dense["cheaper_share"] == 100.0
    assert dense["delete_tree_update"] > dense["delete_tree_presorted"] and sparse["delete_tree_update"] < sparse["delete_tree_presorted"]
