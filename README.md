# tef-map

Generate SVG maps from `mapping.json` with country coloring and provider points focused on Europe.

## Features

- Render SVG maps with Plotly + Kaleido
- Config-driven map styling in `map.py`
- CLI executable: `map`
- TEF modes:
  - `nodes`: color countries by `TEF_member_status`
  - `partners`: show partner points
  - `all`: both country coloring and partner points
  - default (no `--tef`): plain map (no country coloring, no points)

## Requirements

- Python 3.10+
- Chrome installed for Kaleido image export

## Install

### Option 1: using the existing venv

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Option 2: run directly with python

```bash
source .venv/bin/activate
python map.py --help
```

## Usage

```bash
map --help
```

Main arguments:

- `--output` (default: `map.svg`)
- `--mapping` (default: `mapping.json`)
- `--tef` options: `nodes`, `partners`, `all`
- `--resolution` options: `50`, `110` (default: `50`)

## Examples

Plain map (default mode):

```bash
map --output plain.svg
```

Country coloring by member status:

```bash
map --tef nodes --output nodes.svg
```

Partner points only:

```bash
map --tef partners --output partners.svg
```

Both country coloring and partner points:

```bash
map --tef all --output all.svg
```

Use a custom mapping file:

```bash
map --mapping mapping.json --tef all --output custom.svg
```

## Data format

Input file must be a JSON array of country objects in this shape:

```json
[
  {
    "country": "Belgium",
    "code": "BE",
    "country_color": "#1f77b4",
    "TEF_member_status": "Partner",
    "providers": [
      {
        "name": "Provider Name",
        "city": "City",
        "website": null,
        "coordinates": {"latitude": 50.0, "longitude": 4.0}
      }
    ]
  }
]
```

## Notes

- `map.py` contains a `CONFIG` block for map look-and-feel (zoom, colors, coastlines, lakes, etc.).
- If export fails due to Chrome/Kaleido, install Chrome and try again.
