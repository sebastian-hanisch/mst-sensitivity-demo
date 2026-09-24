"""Presets: gültige Werte, Bänder (Median über die 5 festen Instanzen), und jede Zahl im Hilfetext gegen die echten Auswertungsfunktionen."""

import pytest

import sens_constants as C
import sens_evaluation as ev
from sens_presets import PRESET_KEYS, SETTING_SPECS, STEP_SLIDERS


def _settings(p):
    return ev.Settings(p["kind"], p["n"], p["k"], p["terrain"], p["seed"], p["sigma"], p["stream_len"], p["mix"])


def _analysis(name):
    return ev.analyse(_settings(C.PRESETS[name]))


def _has(name, *values):
    text = C.PRESET_HELP[name]
    for v in values:
        assert v in text, (name, v)


def test_every_preset_has_valid_values_and_a_help_text():
    assert list(C.PRESETS) == list(C.PRESET_HELP) and len(C.PRESETS) == 9
    for name, p in C.PRESETS.items():
        assert set(p) == set(PRESET_KEYS), name
        for key, state_key in PRESET_KEYS.items():
            if state_key in STEP_SLIDERS:
                assert isinstance(p[key], int) and p[key] >= 0
                continue
            spec = SETTING_SPECS[state_key]
            assert spec.caster(p[key]) == p[key], (name, key)
            if spec.lo is not None:
                assert spec.lo <= p[key] <= spec.hi, (name, key)
        assert C.PRESET_HELP[name].strip(), name
        if p["noise_t"]:
            assert p["step"] == 3 and p["noise_t"] < C.NOISE_TRIALS                        # Regler nur zusammen mit dem passenden Schritt setzen
        if p["stream_i"]:
            assert p["step"] == 4 and p["stream_i"] <= p["stream_len"]
        if p["failure_i"]:
            assert p["step"] == 2


@pytest.mark.parametrize("name", [n for n in C.PRESET_EXPECTED_BANDS])
def test_preset_bands_over_the_five_fixed_instances(name):
    metric, lo, hi = C.PRESET_EXPECTED_BANDS[name]
    assert lo <= ev.run_config(_settings(C.PRESETS[name]))[metric] <= hi


def test_help_standard():
    a = _analysis("Standardfall (Voreinstellung)")
    tr = a.tree_rel()
    assert (a.inst.n, a.inst.m, len(a.bridges), sum(v < 5 for v in tr), sum(v < 1 for v in tr)) == (31, 113, 0, 3, 1)
    assert a.cost == pytest.approx(466.63, abs=0.005) and min(tr) == pytest.approx(0.77, abs=0.005) and ev._median(tr) == pytest.approx(33.5, abs=0.05)
    assert a.failures[0].rel == pytest.approx(3.42, abs=0.005) and ev.instability(a, 1.0) == 35.0
    _has("Standardfall (Voreinstellung)", "466.63", "33.5 %", "3.42 %", "0.77 %", "35 %")


def test_help_textbook():
    a = _analysis("Lehrbuchbeispiel")
    by = {t.edge: t for t in a.table}
    assert [by[e].margin for e in (3, 5, 0, 2)] == [3.0, 4.0, 1.0, 1.0] and [by[e].margin for e in (1, 4, 6)] == [1.0, 1.0, 2.0] and a.cost == 15.0
    f = next(x for x in a.failures if x.edge == 3)
    assert f.rep == 1 and f.delta == 3.0 and f.steps == 9
    _has("Lehrbuchbeispiel", "Baumkosten 15", "18", "9 Elementarschritte", "B-D 3 (bis 5)")


def test_help_thin_network():
    a = _analysis("Dünnes Netz (Brücken)")
    assert (a.inst.m, len(a.bridges), len(a.tree)) == (57, 5, 30) and ev.instability(a, 1.0) == 45.0
    _has("Dünnes Netz (Brücken)", "57 Kanten", "5 von 30", "45 %")


def test_help_fragile_tree():
    a = _analysis("Fragiler Baum")
    tr = a.tree_rel()
    assert min(tr) == pytest.approx(0.25, abs=0.005) and sum(v < 1 for v in tr) == 3 and ev._median(tr) == pytest.approx(47.0, abs=0.05) and ev.instability(a, 1.0) == 100.0
    _, new_tree, over = ev.noise_detail(a, 1.0, 0)
    assert len(over) == 3 and len(new_tree - set(a.tree)) == 1
    _has("Fragiler Baum", "0.25 %", "100 %", "47.0 %", "3 Kanten", "1 Kante")


def test_help_robust_but_costly():
    a = _analysis("Robust, aber Ausfall teuer")
    assert min(a.tree_rel()) == pytest.approx(2.72, abs=0.005) and ev.instability(a, 1.0) == 0.0
    f = a.failures[0]
    assert f.rel == pytest.approx(8.42, abs=0.005) and f.delta == pytest.approx(36.24, abs=0.005)
    _has("Robust, aber Ausfall teuer", "2.7 %", "0 %", "8.42 %", "36.24")


def test_help_missed_change_and_false_alarm():
    a = _analysis("Verpasste Änderung")
    _, new_tree, over = ev.noise_detail(a, 1.0, C.PRESETS["Verpasste Änderung"]["noise_t"])
    assert new_tree != set(a.tree) and over == [] and len(new_tree - set(a.tree)) == 1
    assert C.PRESETS["Verpasste Änderung"]["noise_t"] == 1
    b = _analysis("Fehlalarm")
    _, new_tree, over = ev.noise_detail(b, 1.0, C.PRESETS["Fehlalarm"]["noise_t"])
    assert new_tree == set(b.tree) and len(over) == 1
    _has("Verpasste Änderung", "Rausch-Lauf 2", "keine einzige Kante"), _has("Fehlalarm", "Rausch-Lauf 1", "eine Kante überschreitet")


def test_help_strong_noise():
    a = _analysis("Starkes Rauschen (5 %)")
    assert ev.instability(a, 5.0) == 90.0 and ev.instability(a, 1.0) == 35.0
    _, new_tree, over = ev.noise_detail(a, 5.0, 0)
    assert len(over) == 2 and len(new_tree - set(a.tree)) == 2
    _has("Starkes Rauschen (5 %)", "90 %", "35 %", "2 Kanten")


def test_help_dense_updates_lose_against_a_kept_sorting():
    p = C.PRESETS["Update lohnt nicht (dicht)"]
    a = _analysis("Update lohnt nicht (dicht)")
    assert a.inst.m == 465
    sm = ev.stream_summary(ev.run_stream(a.inst, p["stream_len"], p["mix"]))
    assert sm["n_ops"] == 50 and sm["update_steps"] == 22071 and sm["presorted_steps"] == 19732 and sm["update_steps"] > sm["presorted_steps"]
    assert sm["recompute_steps"] == pytest.approx(249229, rel=0.02) and sm["changed_share"] == 100.0
    _has("Update lohnt nicht (dicht)", "465 Kanten", "22071", "19732", "249229")


def test_steps_and_sliders_reference_the_right_ranges():
    assert set(C.STEPS) == {1, 2, 3, 4} and C.NOISE_TRIALS == 20 and all(p["stream_i"] <= C.STREAM_LEN_OPTIONS[-1] for p in C.PRESETS.values())
