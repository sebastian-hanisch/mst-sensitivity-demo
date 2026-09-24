"""AppTest-Rauchtests: Voreinstellung, jedes Preset, jeder Schritt und jede Position der Schritt-Regler, beide Instanzen, Randwerte, Würfel-Knopf, Permalink-Grenzen, Instanzwechsel, Experimente und Sweeps auf Abruf,
Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import sens_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(step=1, **state):
    at = AppTest.from_file(APP, default_timeout=240)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if step != 1:
        at.select_slider(key="sens_step").set_value(step).run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m for m in at.metric if m.label.startswith(label))


def test_default_run_has_no_exception_and_shows_the_four_metrics():
    at = _run()
    _ok(at)
    assert {"Spielraum (Median)", "Fragil (< 5 %)", "Brücken", "Update / Neuberechnung"} <= {m.label for m in at.metric}
    assert _metric(at, "Spielraum").value == "33.5 %" and _metric(at, "Fragil").value == "10.0 %" and _metric(at, "Brücken").value == "0 von 30" and _metric(at, "Update").value == "10 %"


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    ss = at.session_state
    assert (ss["kind_select"], ss["n_slider"], ss["k_select"], ss["terrain_select"], ss["seed_input"], ss["sigma_select"], ss["len_select"], ss["mix_select"], ss["sens_step"]) == (
        p["kind"], p["n"], p["k"], p["terrain"], p["seed"], p["sigma"], p["stream_len"], p["mix"], p["step"])
    if p["noise_t"]:
        assert ss["noise_t"] == p["noise_t"]
    if p["stream_i"]:
        assert ss["stream_i"] == p["stream_i"]
    assert at.metric and at.get("plotly_chart")


@pytest.mark.parametrize("step", [1, 2, 3, 4])
def test_every_step_runs_for_every_kind(step):
    for kind in C.KINDS:
        for k in (3, 1000):
            at = _run(kind_select=kind, k_select=k, n_slider=15, sens_step=step)
            _ok(at)
            assert at.get("plotly_chart") and at.session_state["sens_step"] == step


def test_failure_slider_walks_through_all_tree_edges():
    at = _run(step=2)
    _ok(at)
    fmax = int(at.slider(key="failure_i").max)
    assert fmax == 29
    for i in (0, 10, fmax):
        at.slider(key="failure_i").set_value(i).run()
        _ok(at)
        assert any(x.value.startswith(f"**Ausfall {i + 1} von {fmax + 1}") for x in at.markdown)
    at.session_state["kind_select"] = "textbook"
    at.run()
    _ok(at)
    assert at.session_state["failure_i"] <= int(at.slider(key="failure_i").max) == 3


def test_thin_network_starts_with_a_bridge():
    at = _run(step=2, k_select=3, seed_input=47)
    _ok(at)
    assert any("Brücke" in x.value and "Ausfall 1 von" in x.value for x in at.markdown)


def test_noise_slider_and_verdicts():
    at = _run(step=3, seed_input=0, noise_t=1)
    _ok(at)
    assert any("**Verpasst**" in x.value for x in at.markdown)
    at2 = _run(step=3, seed_input=1, noise_t=0)
    _ok(at2)
    assert any("**Fehlalarm**" in x.value for x in at2.markdown)
    for t in (0, 10, 19):
        at2.slider(key="noise_t").set_value(t).run()
        _ok(at2)
        assert any(x.value.startswith(f"**Lauf {t + 1} von 20") for x in at2.markdown)


def test_stream_slider_walks_through_all_operations():
    at = _run(step=4)
    _ok(at)
    smax = int(at.slider(key="stream_i").max)
    assert smax == 50
    for j in (0, 25, smax):
        at.slider(key="stream_i").set_value(j).run()
        _ok(at)
        assert any(x.value.startswith(f"**Operation {j} von {smax}") for x in at.markdown)
    for mix in C.MIXES:
        at = _run(step=4, mix_select=mix, len_select=10)
        _ok(at)
        assert at.get("plotly_chart")


@pytest.mark.parametrize("kw", [
    dict(n_slider=C.N_MIN), dict(n_slider=C.N_MAX), dict(n_slider=C.N_MAX, k_select=1000), dict(n_slider=C.N_MIN, k_select=3), dict(kind_select="textbook"), dict(terrain_select=1.0), dict(terrain_select=0.0),
    dict(sigma_select=C.SIGMA_OPTIONS[0]), dict(sigma_select=C.SIGMA_OPTIONS[-1]), dict(len_select=C.STREAM_LEN_OPTIONS[0]), dict(len_select=C.STREAM_LEN_OPTIONS[-1], mix_select="failures"),
])
def test_extreme_settings_run(kw):
    for step in (1, 2, 3, 4):
        _ok(_run(step=step, **kw))


def test_dice_button_changes_the_seed():
    at = _run()
    old = at.session_state["seed_input"]
    next(b for b in at.button if b.label == "🎲 Neue Instanz generieren").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old


def test_permalink_values_are_clamped_and_invalid_choices_fall_back_to_the_default():
    at = AppTest.from_file(APP, default_timeout=240)
    for k, v in dict(n="999", k="7", terrain="0.15", sigma="3.0", len="33", mix="nope", step="9", kind="nope").items():
        at.query_params[k] = v
    at.run()
    _ok(at)
    ss = at.session_state
    assert (ss["n_slider"], ss["k_select"], ss["terrain_select"], ss["sigma_select"], ss["len_select"], ss["mix_select"], ss["sens_step"], ss["kind_select"]) == (
        C.N_MAX, C.DEFAULT_K, C.DEFAULT_TERRAIN, C.DEFAULT_SIGMA, C.DEFAULT_STREAM_LEN, C.DEFAULT_MIX, 1, "depot")


def test_permalink_accepts_valid_values():
    at = AppTest.from_file(APP, default_timeout=240)
    for k, v in dict(kind="depot", n="20", k="1000", terrain="0.6", seed="7", sigma="5.0", len="20", mix="failures", step="3").items():
        at.query_params[k] = v
    at.run()
    _ok(at)
    ss = at.session_state
    assert (ss["n_slider"], ss["k_select"], ss["terrain_select"], ss["seed_input"], ss["sigma_select"], ss["len_select"], ss["mix_select"], ss["sens_step"]) == (20, 1000, 0.6, 7, 5.0, 20, "failures", 3)


def test_sidebar_shows_only_the_controls_that_matter():
    plain = _run()
    assert any(w.key == "n_widget" for w in plain.slider) and any(w.key == "k_widget" for w in plain.select_slider) and any(w.key == "terrain_widget" for w in plain.select_slider)
    assert any(n.key == "seed_widget" for n in plain.number_input) and any(w.key == "sigma_select" for w in plain.select_slider) and any(w.key == "len_select" for w in plain.select_slider)
    tb = _run(kind_select="textbook")
    assert not any(w.key == "n_widget" for w in tb.slider) and not any(w.key in ("k_widget", "terrain_widget") for w in tb.select_slider) and not any(n.key == "seed_widget" for n in tb.number_input)
    assert any(w.key == "sigma_select" for w in tb.select_slider) and any(r.key == "mix_select" for r in tb.radio)              # Rauschen und Strom wirken auch im Lehrbuchbeispiel


def test_textbook_numbers():
    at = _run(kind_select="textbook")
    _ok(at)
    assert _metric(at, "Spielraum").value == "79.2 %" and _metric(at, "Brücken").value == "0 von 4"


def test_changing_the_instance_while_on_later_steps_does_not_crash():
    for step in (2, 3, 4):
        at = _run(step=step)
        _ok(at)
        for kw in (dict(kind_select="textbook"), dict(kind_select="depot", n_slider=8), dict(k_select=3), dict(mix_select="failures")):
            for k, v in kw.items():
                at.session_state[k] = v
            at.run()
            _ok(at)


def test_noise_experiment_runs_on_demand():
    at = _run(n_slider=10)
    next(b for b in at.button if b.key == "noise_start").click().run()
    _ok(at)
    assert {"Baum ändert sich", "Vorhersage: überschreitet", "Verpasst", "Fehlalarm"} <= {m.label for m in at.metric}


def test_stream_experiment_runs_on_demand():
    at = _run(n_slider=10)
    next(b for b in at.button if b.key == "stream_start").click().run()
    _ok(at)
    assert {"Update / gehaltene Sortierung", "Baumkante löschen"} <= {m.label for m in at.metric}


def test_steps_curve_runs_on_demand():
    at = _run(n_slider=10)
    next(b for b in at.button if b.key == "steps_start").click().run()
    _ok(at)
    assert at.get("plotly_chart")


@pytest.mark.parametrize("param", ["n", "k", "terrain", "sigma", "mix"])
@pytest.mark.parametrize("metric", ["tol", "fragile", "fail", "noise", "stream", "steps"])
def test_sweeps_run_on_demand_for_every_metric(param, metric):
    at = _run(n_slider=10, sweep_metric=metric)
    at.selectbox(key="sweep_select").set_value(param).run()
    next(b for b in at.button if b.key == "sweep_start").click().run()
    _ok(at)
    assert at.get("plotly_chart")


def test_the_textbook_has_no_experiments():
    tb = _run(kind_select="textbook")
    assert not any(b.key in ("noise_start", "stream_start", "steps_start", "sweep_start") for b in tb.button)


def test_footer_limits_and_literature_are_present():
    at = _run()
    assert any("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in c.value for c in at.caption)
    assert any("Wo die Annahmen enden" in s.value for s in at.subheader)
    assert any("Tarjan, R. E. (1982)" in m.value and "Dixon, B., Rauch, M., & Tarjan, R. E." in m.value and "Holm, J., de Lichtenberg, K., & Thorup, M. (2001)" in m.value for m in at.markdown)
