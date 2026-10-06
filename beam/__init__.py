"""Beam Design Automation core package.

Provides structural analysis (reactions, shear, moment, deflection) and
automated steel-section selection for simply supported beams.
"""

from .analysis import BeamModel, PointLoad, DistributedLoad, AnalysisResult, analyze
from .sections import SECTIONS, Section, select_section, SectionCheck

__all__ = [
    "BeamModel",
    "PointLoad",
    "DistributedLoad",
    "AnalysisResult",
    "analyze",
    "SECTIONS",
    "Section",
    "select_section",
    "SectionCheck",
]
