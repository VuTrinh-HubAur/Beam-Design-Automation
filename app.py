"""Beam Design Automation web application.

A small Flask service that analyses a simply supported beam, automatically
selects the lightest adequate steel section, and renders the shear-force,
bending-moment and deflection diagrams.
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from beam import BeamModel, DistributedLoad, PointLoad, analyze, select_section
from beam.diagrams import render_diagrams

app = Flask(__name__)


def _parse_request(data: dict) -> tuple[BeamModel, float, float]:
    span = float(data["span"])

    point_loads = [
        PointLoad(magnitude=float(pl["magnitude"]), position=float(pl["position"]))
        for pl in data.get("point_loads", [])
        if pl.get("magnitude") not in (None, "")
    ]
    distributed_loads = [
        DistributedLoad(
            magnitude=float(dl["magnitude"]),
            start=float(dl["start"]),
            end=float(dl["end"]),
        )
        for dl in data.get("distributed_loads", [])
        if dl.get("magnitude") not in (None, "")
    ]

    beam = BeamModel(
        span=span,
        point_loads=point_loads,
        distributed_loads=distributed_loads,
        youngs_modulus_gpa=float(data.get("youngs_modulus_gpa", 210.0)),
        moment_of_inertia_cm4=float(data.get("moment_of_inertia_cm4", 10000.0)),
    )
    allowable_stress = float(data.get("allowable_stress_mpa", 165.0))
    deflection_ratio = float(data.get("deflection_limit_ratio", 360.0))
    return beam, allowable_stress, deflection_ratio


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.route("/api/design", methods=["POST"])
def design():
    data = request.get_json(force=True, silent=True) or {}
    try:
        beam, allowable_stress, deflection_ratio = _parse_request(data)
        result = analyze(beam)
        selected, checks = select_section(
            beam,
            max_moment_knm=result.max_moment,
            allowable_stress_mpa=allowable_stress,
            deflection_limit_ratio=deflection_ratio,
        )
        diagrams = render_diagrams(result)
    except (KeyError, ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "analysis": result.to_dict(),
            "selected_section": selected.to_dict() if selected else None,
            "section_checks": [c.to_dict() for c in checks],
            "diagrams": diagrams,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
