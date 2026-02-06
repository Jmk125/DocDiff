## docdiff (refactored)

Construction document differ focused on scope-relevant text/table/spec changes.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Inputs supported

- Single combined plan set PDF per set
- Discipline-separated PDFs
- Many single-sheet PDFs

### Run examples

Default folder structure (`input/GMP`, `input/BID`, optional `input/ADDENDA`):

```bash
python docdiff.py --out ./output/changes.xlsx --config ./config.yaml
```

Explicit sets with `--set` (recommended):

```bash
python docdiff.py \
  --set GMP=./input/GMP \
  --set BID=./input/BID \
  --set ADDENDA=./input/ADDENDA \
  --out ./output/changes.xlsx \
  --config ./config.yaml
```

Legacy flags still work:

```bash
python docdiff.py --gmp ./input/GMP --bid ./input/BID --addenda ./input/ADDENDA --out ./output/changes.xlsx --config ./config.yaml
```

### What changed in this refactor

- Package modules: `ingest.py`, `identify.py`, `match.py`, `diff_notes.py`, `diff_tables.py`, `diff_specs.py`, `export_excel.py`, `cli.py`.
- Title-block clipping extraction (bottom-right and bottom-center regions configurable in `config.yaml`).
- Sheet ID normalization (`A101`, `A-101`, `A 101` => `A-101`).
- Composite page matching score (sheet ID exact + title similarity + discipline + content fingerprint similarity).
- Matching evidence exported to `Matching` tab.
- Excel tabs now include `Change_Queue`, `Sheets_Inventory`, `Spec_Inventory`, `Table_Diffs`, `Matching`.

### Output

`output/changes.xlsx`

- `Change_Queue`: triage list with confidence, snippets, flags, and impact scoring rationale.
- `Sheets_Inventory`: added/removed sheets between GMP and BID.
- `Matching`: match confidence and reasons.
- `Spec_Inventory`, `Table_Diffs`: placeholders for expanded workflow.


### Windows install troubleshooting (PyMuPDF)

If installation fails on Python 3.13 with an error like `Unable to find Visual Studio`, pip is trying to build `pymupdf` from source.

Use these steps:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install --only-binary=:all: -r requirements.txt
```

Notes:
- `requirements.txt` now uses a newer `pymupdf` range on Python 3.13+ to prefer available wheels.
- If your corporate proxy blocks wheel downloads, either:
  - use Python 3.12 for this project, or
  - install Visual Studio Build Tools (C++ workload) and retry.


### UI (Streamlit)

You can run a simple UI wrapper using Streamlit:

```bash
streamlit run ui_app.py
```

This UI exposes the same inputs as the CLI and writes the Excel output to the configured path.
