\## docdiff v0.1



\### Install

python -m venv .venv

\# Windows:

.venv\\Scripts\\activate

pip install -r requirements.txt



\### Input folder structure

input/

&nbsp; GMP/  (one or many PDFs)

&nbsp; BID/  (one or many PDFs)

&nbsp; ADDENDA/ (optional, one or many PDFs)



\### Run

python docdiff.py --gmp ./input/GMP --bid ./input/BID --addenda ./input/ADDENDA --out ./output/changes.xlsx --config ./config.yaml



\### Output

output/changes.xlsx



Tabs:

\- Change\_Queue: triage list with Impact\_Score, Confidence, Auto\_Flags, Before/After snippets

\- Sheets\_Inventory: sheets added/removed between GMP and BID



