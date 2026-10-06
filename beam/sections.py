"""Steel section library and automated section selection.

Section properties are representative UK Universal Beam (UB) values:

* ``inertia_cm4``        : second moment of area, I (cm^4)
* ``modulus_cm3``        : elastic section modulus, Z (cm^3)
* ``mass_per_m``         : self weight (kg/m)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .analysis import BeamModel, analyze


@dataclass(frozen=True)
class Section:
    name: str
    mass_per_m: float
    inertia_cm4: float
    modulus_cm3: float


# Ordered lightest -> heaviest so selection naturally returns the lightest adequate option.
SECTIONS: List[Section] = [
    Section("203x133x25 UB", 25.1, 2340.0, 230.0),
    Section("254x146x31 UB", 31.1, 4410.0, 351.0),
    Section("305x165x40 UB", 40.3, 8500.0, 560.0),
    Section("356x171x51 UB", 51.0, 14100.0, 896.0),
    Section("406x178x60 UB", 60.1, 21600.0, 1190.0),
    Section("457x191x74 UB", 74.3, 33300.0, 1460.0),
    Section("533x210x92 UB", 92.1, 55200.0, 2070.0),
    Section("610x229x113 UB", 113.0, 87300.0, 2870.0),
]


@dataclass
class SectionCheck:
    section: Section
    bending_stress_mpa: float
    bending_utilization: float
    max_deflection_mm: float
    deflection_limit_mm: float
    deflection_utilization: float
    passes_bending: bool
    passes_deflection: bool

    @property
    def passes(self) -> bool:
        return self.passes_bending and self.passes_deflection

    def to_dict(self) -> dict:
        return {
            "section": self.section.name,
            "mass_per_m": self.section.mass_per_m,
            "inertia_cm4": self.section.inertia_cm4,
            "modulus_cm3": self.section.modulus_cm3,
            "bending_stress_mpa": round(self.bending_stress_mpa, 2),
            "bending_utilization": round(self.bending_utilization, 3),
            "max_deflection_mm": round(self.max_deflection_mm, 3),
            "deflection_limit_mm": round(self.deflection_limit_mm, 3),
            "deflection_utilization": round(self.deflection_utilization, 3),
            "passes_bending": self.passes_bending,
            "passes_deflection": self.passes_deflection,
            "passes": self.passes,
        }


def check_section(
    beam: BeamModel,
    section: Section,
    max_moment_knm: float,
    allowable_stress_mpa: float,
    deflection_limit_ratio: float,
) -> SectionCheck:
    """Check one section against bending-stress and deflection limits."""
    # Bending stress: sigma = M / Z.  M (N*mm) = M(kN*m) * 1e6, Z (mm^3) = Z(cm^3) * 1e3.
    moment_nmm = abs(max_moment_knm) * 1.0e6
    modulus_mm3 = section.modulus_cm3 * 1.0e3
    bending_stress = moment_nmm / modulus_mm3
    bending_util = bending_stress / allowable_stress_mpa

    # Deflection with this section's actual inertia.
    trial = BeamModel(
        span=beam.span,
        point_loads=beam.point_loads,
        distributed_loads=beam.distributed_loads,
        youngs_modulus_gpa=beam.youngs_modulus_gpa,
        moment_of_inertia_cm4=section.inertia_cm4,
        samples=beam.samples,
    )
    result = analyze(trial)
    max_defl = abs(result.max_deflection_mm)
    defl_limit = (beam.span * 1000.0) / deflection_limit_ratio
    defl_util = max_defl / defl_limit if defl_limit else float("inf")

    return SectionCheck(
        section=section,
        bending_stress_mpa=bending_stress,
        bending_utilization=bending_util,
        max_deflection_mm=max_defl,
        deflection_limit_mm=defl_limit,
        deflection_utilization=defl_util,
        passes_bending=bending_util <= 1.0,
        passes_deflection=defl_util <= 1.0,
    )


def select_section(
    beam: BeamModel,
    max_moment_knm: float,
    allowable_stress_mpa: float = 165.0,
    deflection_limit_ratio: float = 360.0,
) -> tuple[Optional[SectionCheck], List[SectionCheck]]:
    """Pick the lightest section that satisfies both bending and deflection.

    Returns ``(selected, all_checks)``. ``selected`` is ``None`` when no library
    section is adequate.
    """
    checks = [
        check_section(beam, s, max_moment_knm, allowable_stress_mpa, deflection_limit_ratio)
        for s in SECTIONS
    ]
    selected = next((c for c in checks if c.passes), None)
    return selected, checks
