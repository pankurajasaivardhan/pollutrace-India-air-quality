# Legacy files (kept for provenance, not used)

The original course-project notebooks, preserved unchanged in `notebooks/`.

- Several results in them are hardcoded or were produced with leakage (gap filling and scaling before the split, a random split for XGBoost). Do not quote their numbers. Notebooks 07 and 08 contain typed-in metrics that do not match notebook 03's own output.
- The notebooks keep their original executed outputs so the old runs stay readable. I checked them: they hold 5-row `head()` previews, array shapes, training logs, a 10-row top-anomaly list per city, and 17 figures. No output holds a substantial extract of the data.
- The original trained model files (`src/models/*.keras`, XGBoost JSON, and Git LFS pointer text files named `*.pkl`) are **not** part of this tree. They were trained on the same dataset whose reuse terms are unresolved (see the root README, "Data"), so they are left out of this release. They remain in the original repository history, up to commit `a9f599f` on `main`.

Notebook paths such as `../src/models/` point to those removed files. The current pipeline is in `pipeline/`.
