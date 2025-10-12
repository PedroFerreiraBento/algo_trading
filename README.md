# Forex Backtester

A modular Python framework for backtesting Forex strategies with:

- Live MT5 login to fetch historical candles
- A backtest operation environment to execute signals
- Shared utilities to compute performance metrics and export Markdown reports

---

## Key Features

- **Data Fetching (MT5 Rates):** Download historical candles with a live connection.
- **Backtest Execution:** Place/close trades in a simulated operation environment.
- **Shared Utilities:**
  - `login_live_and_backtest()` – session setup for live + backtest
  - `build_operations_dataframe()` – normalize deals and include costs (swap/commission)
  - `compute_statistics()` – comprehensive performance metrics
  - `render_markdown_report()` and `save_report_markdown()` – export a clean Markdown report
- **Templates and Examples:** Ready to extend and customize.

---

## Project Structure

The most relevant parts of the repository:

```plaintext
scripts/
└── strategies/
    ├── strategy_base.py              # Shared credentials, login, stats, markdown report
    ├── strategy_template.py          # Reusable template to build new strategies
    └── 000001-simple_crossover/
        ├── simple_crossover_backtest.py  # SMA(20/50) crossover for EURUSD M5
        └── README.md

algo_trading/
└── sources/MetaTrader5_source/       # MT5 models, backtest, operation, rates

docs/                                 # Additional docs
notebooks/                            # Exploration notebooks
tests/                                # Automated tests
environment.yml                       # Conda environment
setup.py                              # Packaging metadata
README.md                             # This file
```

---

## Environment Setup (Conda)

- Create the environment:

```bash
conda env create -f environment.yml
```

- Update the environment:

```bash
conda env update --name backtestenv --file environment.yml --prune
```

- Preferred way to run Python commands:

```bash
conda run -n backtestenv <command>
```

---

## How to Run the Example Strategy

Run the SMA crossover example (EURUSD, M5, SMA 20/50):

```bash
conda run -n backtestenv python scripts/strategies/000001-simple_crossover/simple_crossover_backtest.py
```

Outputs:

- Console summary
- Markdown report saved next to the script, e.g.:
  `scripts/strategies/000001-simple_crossover/backtest_results_EURUSD_YYYYMMDD_HHMMSS.md`

---

## Create a New Strategy

- Copy `scripts/strategies/strategy_template.py`
- Implement your signal logic in `generate_signals()`
- Reuse base utilities:
  - `login_live_and_backtest()` for session/backtest
  - `build_operations_dataframe()` for deals normalization + costs
  - `compute_statistics()` for metrics
  - `render_markdown_report()` + `save_report_markdown()` for Markdown reports
- Add custom report sections via the `extra_sections` parameter in `render_markdown_report()`

---

## Configuration and Credentials

- Shared credentials live in `scripts/strategies/strategy_base.py` as `DEFAULT_CREDENTIALS`.
- You can edit them there or adapt to read from environment variables.

---

## Testing

```bash
conda run -n backtestenv pytest
```

---

## License

MIT License. See `LICENSE` for details.
