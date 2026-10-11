# Shopping agents and Amazon advertising

A reproducible analysis of whether merchants' advertising savings could offset
Amazon's replacement fees when shopping agents replace paid product discovery.

The model uses FY2025 Amazon financial disclosures, an external third-party GMV
estimate, and public seller advertising benchmarks. It reports conditional
scenarios rather than forecast probabilities. Public inputs and illustrative
assumptions are explicitly distinguished in the report.

## Files

- `amazon-advertising-agents.qmd`: self-contained Quarto report with all analysis
  code, equations, sources, assumptions, tables, figures, and limitations.
- `simulate.py`: the original Python simulation used before the Quarto report.
- `requirements.txt`: pinned top-level Python dependencies.
- `validate_analysis.py`: executes the report's Python chunks and compares all
  35 central results with the original simulation, without requiring Quarto.
- `amazon-walmart-scenarios.qmd`: full-agent-takeover extension covering both
  companies' revenue, operating contribution, transferred purchases, and sellers.
- `competitive_scenarios.py`: shared executable model for the competitive report.
- `validate_competition_report.py`: numerical execution and accounting validation
  of the extension, without requiring Quarto or Jupyter.

## Run the report

Install Python 3.12 and [Quarto](https://quarto.org/docs/get-started/), then run:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ipykernel install --sys-prefix --name python3 --display-name "Python 3"
quarto render amazon-advertising-agents.qmd
quarto render amazon-walmart-scenarios.qmd
```

On Windows, activate with `.venv\Scripts\activate`. If needed, set
`QUARTO_PYTHON` to the virtual environment's Python executable.

The report exports numerical data and PNG/PDF charts to `quarto-outputs/` and
renders a standalone HTML report. It requires no live data downloads or account
credentials. Change the documented constants to explore different assumptions.

## Run the original simulation or validation

```bash
python simulate.py
python validate_analysis.py
python competitive_scenarios.py
python validate_competition_report.py
```

Validation runs both analyses in temporary directories, verifies the report's
embedded accounting and boundary checks, and compares all 35 central scenarios.
The Quarto report also generates an 8,748-row deterministic sensitivity grid.
No random seed is needed because there is no random sampling.

The original simulation writes CSV/JSON results and charts beside `simulate.py`.
These outputs are ignored by Git because they can be regenerated from the source.

The competitive model exports four named favorable/adverse cases, a 1,215-row
grid, and charts to `competition-outputs/`. All cases remove every on-site shopping
ad while preserving off-site and television ads. Consumer prices and total goods
spending stay fixed; retailer allocation is an explicit scenario input.

Revenue and profit are calculated separately. Marketplace GMV is not platform
revenue, and Walmart may book advertising as either revenue or reduced cost of
sales. Undisclosed advertising splits and order mixes are assumptions, not
measured facts. Named cases are conditional examples, not forecast bounds.

## Validation status

All 12 Quarto Python chunks have been executed successfully. All 35 central
results match the original simulation, and all embedded validation checks pass.
HTML rendering has not been checked: the original execution environment did not
have the Quarto CLI or Jupyter runtime installed. The numerical validation script
requires only NumPy and Matplotlib; HTML rendering requires the full dependencies.

The competitive report's Python chunks and embedded accounting checks also pass,
including fixed-demand transfers, gross versus net revenue recognition, Walmart
ad booking, fee caps, and profit break-even thresholds. HTML rendering remains
unchecked for both reports.

## Interpretation

The default case removes 80% of relevant advertising, assumes sellers fund 70% of
Amazon ad revenue, assumes 70% of removed revenue becomes lost contribution after
avoidable costs, and transmits 50% of net merchant cost changes to consumer prices.
These are assumptions, not disclosed Amazon parameters. The model does not solve
for demand, Amazon's optimal fees, seller exit, or changes in product selection.

See the report for the full analysis and links to the underlying public evidence.
