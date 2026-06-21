# Smart Data Cleaner & Preprocessor Test Suite

This directory contains a robust, comprehensive unit test suite for the `clean_dataset(df)` function in `smart_cleaner.py`. The suite is written using **pytest** and utilizes synthetic pandas DataFrames to verify correctness deterministically without requiring external files.

---

## 🚀 Running the Tests

To run the test suite, ensure you have Python 3.x and pandas/numpy/pytest installed, then run one of the following commands in your terminal:

```bash
# Run all tests with verbose output
pytest -v test_smart_cleaner.py

# Run all tests via Python module alias (if pytest is not in system PATH)
python -m pytest -v test_smart_cleaner.py

# Run a specific test case by keyword
python -m pytest -v test_smart_cleaner.py -k test_feature_engineering_order
```

---

## 🔍 Test Coverage Categories

The test suite contains **31 unit tests** validating the pipeline across nine core categories:

### 1. Missing Value Resolution Tests
* **Under 30% Missingness (`test_missing_numeric_under_30`)**: Verifies that a numeric column with $10\%$ missingness is imputed using the median (not dropped) and adds a `<column>_was_missing` boolean flag set to `True` only for the originally missing rows.
* **Over 30% Missingness (`test_missing_numeric_over_30`)**: Confirms that a numeric column with $40\%$ missingness is flagged for manual review, is not imputed, and remains null in the final DataFrame.
* **Negligible Missingness (`test_missing_negligible`)**: Validates that rows with minor missingness ($<2\%$) are dropped and the row count is decreased by exactly the number of dropped rows.
* **Zero Missingness (`test_missing_zero`)**: Assures that columns with $0\%$ nulls are completely untouched and do not receive unnecessary `_was_missing` flags.
* **Nulls Invariant (`test_missing_nulls_invariant`)**: Enforces that all columns in the cleaned output have $0$ nulls except those explicitly listed in `flagged_for_review`.

### 2. Date/Time Processing Tests
* **Consistent Parsing (`test_date_consistent`)**: Verifies standard ISO date strings are correctly converted to a `datetime64[ns]` pandas series.
* **Mixed Format Support (`test_date_mixed`)**: Assures that dates in mixed formats (e.g., American slash and ISO dash formats) parse correctly without warnings.
* **Unparseable Garbage Recovery (`test_date_garbage`)**: Ensures that rows with unparseable string content do not crash the pipeline, but are instead safely converted to `NaT` and reported.
* **Derived Calendar Features (`test_date_derived_columns`)**: Verifies that calendar engineering creates correct integer features (`_year`, `_month`, `_day`, `_day_of_week`) for a known date (e.g., Wednesday = index `2`).
* **Column Replacement (`test_date_original_replaced`)**: Checks that original raw string date columns are replaced in-place by their parsed datetime counterparts rather than being silently discarded.

### 3. Text/Category Standardization Tests
* **Whitespace & Spacing (`test_text_whitespace`)**: Confirms leading/trailing spacing is stripped and duplicate spaces are collapsed to single spaces.
* **Casing Normalization (`test_text_case`)**: Verifies categorical values normalize to title case, preserving specific uppercase exclusions (like `USA`).
* **Fuzzy Label Merging (`test_fuzzy_matching_collapsing`)**: Verifies that typo-ridden categoricals (e.g. `Diabetes` vs `Diabetess`) collapse into the most frequent canonical label.
* **No Semantic Merges (`test_fuzzy_matching_no_false_positive`)**: Assures that distinct but similar categoricals (e.g., `Korea, South` vs `Korea, North`) are kept separate and not incorrectly merged.
* **High-Cardinality Skip (`test_text_high_cardinality_skipped`)**: Assures that text columns with $\ge 50$ unique labels skip category-specific standardizations (like fuzzy matching) to avoid incorrect merges.

### 4. Numeric Validation Tests
* **Negative Count Correction (`test_numeric_negative_correction`)**: Checks that invalid negative values in count columns are replaced with the positive median when $>99\%$ of the column is positive.
* **Logical Violation Check (`test_numeric_logical_violation`)**: Verifies logical relational limits (e.g. Deaths cannot exceed Confirmed, and Recovered cannot exceed Confirmed), correcting Confirmed to match the maximum.
* **IQR Outlier Reporting (`test_numeric_iqr_outlier`)**: Validates that extreme outliers are reported but NOT silently dropped (row count remains intact).
* **Clean Data Integrity (`test_numeric_clean`)**: Ensures correct values don't trigger false flags or warnings.

### 5. Duplicate Detection Tests
* **Exact Duplicate Drop (`test_duplicate_exact`)**: Confirms exact duplicate rows are removed.
* **Near-Duplicate Flags (`test_duplicate_near`)**: Verifies rows with matching primary/index keys but differing values elsewhere are reported for manual audit and not deleted.
* **No Duplicates (`test_duplicate_zero`)**: Checks that a duplicate-free dataset processes cleanly without row loss or warnings.

### 6. Step Ordering Tests
* **Ordering Check (`test_feature_engineering_order`)**: Ensures missing values are resolved *before* feature engineering so that derived text length/word count properties reflect the imputed strings (e.g. `'Unknown'`) instead of crashing on `NaN`.

### 7. Output/Report Creation Tests
* **Report Structure (`test_output_files_created`)**: Verifies that the cleaning pipeline outputs both a clean CSV and a descriptive Markdown report in the requested directory with expected headers.

### 8. Invariant/Property-Based Tests
* **Rows Invariant (`test_invariant_row_count`)**: Assures output row count $\le$ input row count.
* **Cols Invariant (`test_invariant_column_count`)**: Assures output column count $\ge$ input column count.
* **Idempotency (`test_invariant_idempotency`)**: Checks that running the pipeline a second time on already cleaned output results in no further modifications.

### 9. Edge Cases
* **Empty DataFrame (`test_edge_empty_df`)**: Assures the pipeline gracefully handles $0$-row inputs.
* **Single-Row DataFrame (`test_edge_single_row_df`)**: Verifies statistics do not fail on single-row inputs.
* **All Null Column (`test_edge_all_null_column`)**: Ensures $100\%$ null columns do not crash the pipeline and are flagged for review.
* **Clean Dataset (`test_edge_already_clean_df`)**: Validates that already-clean inputs bypass transformations without error.

---

## 🧪 Mutation Testing

To ensure the test suite is highly sensitive to changes in boundary conditions and operators, mutation testing is executed by mutating key comparison operators and thresholds inside `smart_cleaner.py` and running the tests.

Because native windows mutation libraries can have compatibility issues, a custom Python mutation test runner script is used to automate this.

### Mutation Report
| Line Number | Original Code | Mutated Code | Killed or Survived | Killing Test |
|---|---|---|---|---|
| 158 | `if missing_pct > 0.30:` | `if missing_pct > 0.50:` | **Killed** | test_missing_numeric_over_30 |
| 175 | `if missing_pct < 0.02:` | `if missing_pct < 0.05:` | **Killed** | test_feature_engineering_order |
| 256 | `similar_group = [m[0] for m in matches if m[1] >= 85]` | `similar_group = [m[0] for m in matches if m[1] >= 95]` | **Killed** | test_fuzzy_matching_collapsing |
| 300 | `lower_bound = q1 - 1.5 * iqr ...` | `lower_bound = q1 - 3.0 * iqr ...` | **Killed** | test_kill_mutant_4_iqr_multiplier |
| 286 | `pos_mask = series >= 0` | `pos_mask = series > 0` | **Killed** | test_kill_mutant_5_zero_preservation |
| 288 | `if pos_pct >= 0.99 and pos_pct < 1.0:` | `if pos_pct >= 0.90 and pos_pct < 1.0:` | **Killed** | test_kill_mutant_6_pos_pct_heuristic |
| 328 | `violation_mask = self.df[conf_col] < self.df[death_col]` | `violation_mask = self.df[conf_col] <= self.df[death_col]` | **Killed** | test_kill_mutant_7_conf_deaths_equal |
| 338 | `violation_mask = self.df[conf_col] < self.df[rec_col]` | `violation_mask = self.df[conf_col] <= self.df[rec_col]` | **Killed** | test_kill_mutant_8_conf_recovered_equal |
| 109 | `if self.df[col].nunique() < 10 and not pd.api.types.is_float_dtype(self.df[col]):` | `if self.df[col].nunique() < 5 and not pd.api.types.is_float_dtype(self.df[col]):` | **Killed** | test_kill_mutant_9_numeric_categorical_boundary |
| 137 | `if unique_count < 50:` | `if unique_count < 20:` | **Killed** | test_kill_mutant_10_string_categorical_boundary |
| 391 | `if col in self.df.columns and self.df[col].nunique() > 10:` | `if col in self.df.columns and self.df[col].nunique() > 20:` | **Killed** | test_kill_mutant_11_numeric_binning_boundary |
