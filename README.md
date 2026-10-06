# Beam-Design-Automation

A small web application that automates structural design of **simply supported beams**.
It analyses applied loads, draws the shear-force / bending-moment / deflection diagrams,
and automatically selects the lightest adequate steel section from a built-in library.

## Features

- Reactions, shear-force and bending-moment distributions via static equilibrium
- Deflection by double integration of the moment curve (`EI v'' = M`)
- Automated steel-section selection against bending-stress and deflection (`span/n`) limits
- Shear / moment / deflection diagrams rendered server-side (matplotlib)
- Clean, responsive web UI with point loads and distributed loads

## Tech stack

- Python 3.12, Flask (web + JSON API)
- NumPy (numerical integration), Matplotlib (diagrams)
- pytest (engine validated against closed-form beam formulas)

## Getting started

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000.

## Running the tests

```bash
. .venv/bin/activate
pytest -q
```

## API

`POST /api/design` with JSON:

```json
{
  "span": 6,
  "point_loads": [{"magnitude": 40, "position": 3}],
  "distributed_loads": [{"magnitude": 15, "start": 0, "end": 6}],
  "allowable_stress_mpa": 165,
  "deflection_limit_ratio": 360
}
```

Returns the analysis summary, the selected section, the full section-check table,
and base64-encoded diagram images.

`GET /healthz` returns `{"status": "ok"}` for health checks.

## Project layout

```
app.py                 Flask app (routes + request parsing)
beam/analysis.py       Core structural analysis engine
beam/sections.py       Steel section library + automated selection
beam/diagrams.py       Matplotlib SFD / BMD / deflection rendering
templates/index.html   Web UI
static/                Styles and client-side logic
tests/                 Engine unit tests (validated vs. hand formulas)
```
