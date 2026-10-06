"""Structural analysis for a simply supported beam.

All public inputs use engineering-friendly units:

* Length / position : metres (m)
* Point load        : kilonewtons (kN)
* Distributed load  : kilonewtons per metre (kN/m)
* Young's modulus   : gigapascals (GPa)
* Second moment I   : cm^4 (converted internally)

Outputs expose reactions (kN), shear (kN), bending moment (kN*m) and
deflection (mm) sampled along the span.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np


@dataclass
class PointLoad:
    """A downward point load of ``magnitude`` kN at ``position`` m from the left support."""

    magnitude: float
    position: float


@dataclass
class DistributedLoad:
    """A uniformly distributed load of ``magnitude`` kN/m acting over [start, end] m."""

    magnitude: float
    start: float
    end: float

    @property
    def length(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def resultant(self) -> float:
        return self.magnitude * self.length

    @property
    def centroid(self) -> float:
        return 0.5 * (self.start + self.end)


@dataclass
class BeamModel:
    """A simply supported beam with a left (pin) and right (roller) support."""

    span: float
    point_loads: List[PointLoad] = field(default_factory=list)
    distributed_loads: List[DistributedLoad] = field(default_factory=list)
    youngs_modulus_gpa: float = 210.0  # structural steel default
    moment_of_inertia_cm4: float = 10000.0
    samples: int = 201

    def validate(self) -> None:
        if self.span <= 0:
            raise ValueError("Span must be positive.")
        for pl in self.point_loads:
            if not (0.0 <= pl.position <= self.span):
                raise ValueError(
                    f"Point load position {pl.position} m is outside the span [0, {self.span}]."
                )
        for dl in self.distributed_loads:
            if dl.start < 0 or dl.end > self.span or dl.end <= dl.start:
                raise ValueError(
                    f"Distributed load span [{dl.start}, {dl.end}] is invalid for a {self.span} m beam."
                )
        if self.samples < 3:
            raise ValueError("Need at least 3 samples to analyse the beam.")


@dataclass
class AnalysisResult:
    x: np.ndarray
    shear: np.ndarray
    moment: np.ndarray
    deflection_mm: np.ndarray
    reaction_left: float
    reaction_right: float
    max_shear: float
    max_moment: float
    max_moment_position: float
    max_deflection_mm: float
    max_deflection_position: float
    total_load: float

    def to_dict(self) -> dict:
        return {
            "x": self.x.round(4).tolist(),
            "shear": self.shear.round(4).tolist(),
            "moment": self.moment.round(4).tolist(),
            "deflection_mm": self.deflection_mm.round(5).tolist(),
            "reaction_left": round(self.reaction_left, 3),
            "reaction_right": round(self.reaction_right, 3),
            "max_shear": round(self.max_shear, 3),
            "max_moment": round(self.max_moment, 3),
            "max_moment_position": round(self.max_moment_position, 3),
            "max_deflection_mm": round(self.max_deflection_mm, 4),
            "max_deflection_position": round(self.max_deflection_position, 3),
            "total_load": round(self.total_load, 3),
        }


def _reactions(beam: BeamModel) -> tuple[float, float]:
    """Return (R_left, R_right) in kN using static equilibrium about the left support."""
    total_load = sum(pl.magnitude for pl in beam.point_loads)
    total_load += sum(dl.resultant for dl in beam.distributed_loads)

    moment_about_left = sum(pl.magnitude * pl.position for pl in beam.point_loads)
    moment_about_left += sum(dl.resultant * dl.centroid for dl in beam.distributed_loads)

    reaction_right = moment_about_left / beam.span
    reaction_left = total_load - reaction_right
    return reaction_left, reaction_right


def _shear_at(beam: BeamModel, reaction_left: float, x: float) -> float:
    """Internal shear force (kN) just at coordinate ``x``."""
    v = reaction_left
    for pl in beam.point_loads:
        if pl.position <= x:
            v -= pl.magnitude
    for dl in beam.distributed_loads:
        if x > dl.start:
            covered = min(x, dl.end) - dl.start
            v -= dl.magnitude * covered
    return v


def _moment_at(beam: BeamModel, reaction_left: float, x: float) -> float:
    """Internal bending moment (kN*m) at coordinate ``x``."""
    m = reaction_left * x
    for pl in beam.point_loads:
        if pl.position <= x:
            m -= pl.magnitude * (x - pl.position)
    for dl in beam.distributed_loads:
        if x > dl.start:
            b = min(x, dl.end)
            covered = b - dl.start
            resultant = dl.magnitude * covered
            centroid = 0.5 * (dl.start + b)
            m -= resultant * (x - centroid)
    return m


def analyze(beam: BeamModel) -> AnalysisResult:
    """Run a full analysis of the simply supported beam."""
    beam.validate()

    reaction_left, reaction_right = _reactions(beam)
    total_load = reaction_left + reaction_right

    x = np.linspace(0.0, beam.span, beam.samples)
    shear = np.array([_shear_at(beam, reaction_left, xi) for xi in x])
    moment = np.array([_moment_at(beam, reaction_left, xi) for xi in x])

    # Deflection by double integration of the moment curve: EI * v'' = M.
    # E in Pa, I in m^4, M in N*m  ->  v in m.
    e_pa = beam.youngs_modulus_gpa * 1.0e9
    i_m4 = beam.moment_of_inertia_cm4 * 1.0e-8  # cm^4 -> m^4
    ei = e_pa * i_m4
    moment_nm = moment * 1.0e3

    slope_unscaled = _cumulative_trapezoid(moment_nm, x)          # = EI*v' + C1
    deflection_unscaled = _cumulative_trapezoid(slope_unscaled, x)  # = EI*v + C1*x + C2
    # Boundary conditions v(0)=0 and v(span)=0.
    c1 = -deflection_unscaled[-1] / beam.span
    ei_v = deflection_unscaled + c1 * x
    deflection_m = ei_v / ei
    deflection_mm = deflection_m * 1.0e3

    max_shear_idx = int(np.argmax(np.abs(shear)))
    max_moment_idx = int(np.argmax(np.abs(moment)))
    max_defl_idx = int(np.argmax(np.abs(deflection_mm)))

    return AnalysisResult(
        x=x,
        shear=shear,
        moment=moment,
        deflection_mm=deflection_mm,
        reaction_left=reaction_left,
        reaction_right=reaction_right,
        max_shear=float(shear[max_shear_idx]),
        max_moment=float(moment[max_moment_idx]),
        max_moment_position=float(x[max_moment_idx]),
        max_deflection_mm=float(deflection_mm[max_defl_idx]),
        max_deflection_position=float(x[max_defl_idx]),
        total_load=total_load,
    )


def _cumulative_trapezoid(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Cumulative trapezoidal integral of ``y`` over ``x`` with a leading zero."""
    dx = np.diff(x)
    areas = 0.5 * (y[1:] + y[:-1]) * dx
    out = np.zeros_like(y)
    out[1:] = np.cumsum(areas)
    return out
