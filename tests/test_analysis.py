"""Validate the analysis engine against closed-form beam formulas."""

import math

import pytest

from beam import BeamModel, DistributedLoad, PointLoad, analyze, select_section


def test_central_point_load_reactions_and_moment():
    # Central point load P on span L: reactions P/2, max moment P*L/4.
    p, span = 40.0, 6.0
    beam = BeamModel(span=span, point_loads=[PointLoad(p, span / 2)], samples=401)
    res = analyze(beam)

    assert res.reaction_left == pytest.approx(p / 2, rel=1e-6)
    assert res.reaction_right == pytest.approx(p / 2, rel=1e-6)
    assert res.max_moment == pytest.approx(p * span / 4, rel=1e-3)
    assert res.max_moment_position == pytest.approx(span / 2, abs=span / 400 + 1e-9)


def test_udl_reactions_and_moment():
    # Full-span UDL w: reactions w*L/2, max moment w*L^2/8.
    w, span = 15.0, 6.0
    beam = BeamModel(span=span, distributed_loads=[DistributedLoad(w, 0, span)], samples=401)
    res = analyze(beam)

    assert res.reaction_left == pytest.approx(w * span / 2, rel=1e-6)
    assert res.reaction_right == pytest.approx(w * span / 2, rel=1e-6)
    assert res.max_moment == pytest.approx(w * span ** 2 / 8, rel=1e-3)


def test_udl_central_deflection_matches_formula():
    # Central deflection for full-span UDL: 5 w L^4 / (384 EI).
    w, span = 12.0, 5.0
    e_gpa, i_cm4 = 210.0, 12000.0
    beam = BeamModel(
        span=span,
        distributed_loads=[DistributedLoad(w, 0, span)],
        youngs_modulus_gpa=e_gpa,
        moment_of_inertia_cm4=i_cm4,
        samples=801,
    )
    res = analyze(beam)

    w_nm = w * 1e3  # kN/m -> N/m
    ei = (e_gpa * 1e9) * (i_cm4 * 1e-8)
    expected_m = 5 * w_nm * span ** 4 / (384 * ei)
    expected_mm = expected_m * 1e3

    assert abs(res.max_deflection_mm) == pytest.approx(expected_mm, rel=2e-3)


def test_point_load_central_deflection_matches_formula():
    # Central deflection for central point load: P L^3 / (48 EI).
    p, span = 50.0, 4.0
    e_gpa, i_cm4 = 210.0, 8500.0
    beam = BeamModel(
        span=span,
        point_loads=[PointLoad(p, span / 2)],
        youngs_modulus_gpa=e_gpa,
        moment_of_inertia_cm4=i_cm4,
        samples=801,
    )
    res = analyze(beam)

    p_n = p * 1e3
    ei = (e_gpa * 1e9) * (i_cm4 * 1e-8)
    expected_mm = (p_n * span ** 3 / (48 * ei)) * 1e3

    assert abs(res.max_deflection_mm) == pytest.approx(expected_mm, rel=3e-3)


def test_section_selection_returns_lightest_adequate():
    beam = BeamModel(span=6.0, distributed_loads=[DistributedLoad(20.0, 0, 6.0)], samples=401)
    res = analyze(beam)
    selected, checks = select_section(beam, res.max_moment)

    assert selected is not None
    assert selected.passes
    # Every lighter section in the ordered library must fail at least one limit.
    for c in checks:
        if c.section.mass_per_m < selected.section.mass_per_m:
            assert not c.passes


def test_invalid_span_raises():
    with pytest.raises(ValueError):
        analyze(BeamModel(span=0.0))


def test_load_outside_span_raises():
    with pytest.raises(ValueError):
        analyze(BeamModel(span=4.0, point_loads=[PointLoad(10.0, 5.0)]))
