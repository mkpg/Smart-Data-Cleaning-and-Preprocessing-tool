# Data Cleaning and Preprocessing Report: dataset.csv
Generated on: 2026-06-21 09:53:53

## 1. Executive Summary
- **Original Shape**: 10 rows, 2 columns
- **Cleaned Shape**: 10 rows, 4 columns
- **Exact Duplicates Dropped**: 0 rows
- **Near-Duplicates Identified**: 9 rows

### Before and After Comparison Table

| Metric | Before Cleaning | After Cleaning |
| :--- | :--- | :--- |
| **Row Count** | 10 | 10 |
| **Column Count** | 2 | 4 |
| **Total Null Cells** | 1 | 0 |
| **Exact Duplicate Rows** | 0 | 0 |

---

## 2. Missing Values Analysis & Imputation Audit

| Column Name | Initial Nulls | Imputation / Action Taken | Audit Column Added? | Remaining Nulls |
| :--- | :--- | :--- | :--- | :--- |
| `SNo` | 0 | None (No missing values) | No | 0 |
| `Confirmed` | 1 | Imputed with Median | `Confirmed_was_missing` | 0 |

---

## 3. Date / Time Standardization
No date/time columns were detected.

---

## 4. Text and Categorical Normalization
Whitespace was trimmed and spaces collapsed on all string columns. Casing was normalized to title case. No synonym mappings were triggered.

---

## 5. Numeric Validation and Outlier Detection
No statistical outliers detected in numeric columns.

No logical range or consistency violations detected.

---

## 6. Duplicates Report
- **Exact duplicates**: 0 rows dropped.
- **Near-duplicates**: 9 rows sharing keys but differing in non-key values.

#### Near-Duplicate Sample Rows:
|   SNo |   Confirmed | Confirmed_was_missing   |
|------:|------------:|:------------------------|
|     1 |          10 | False                   |
|     2 |          20 | False                   |
|     4 |          40 | False                   |
|     5 |          50 | False                   |
|     6 |          60 | False                   |
|     7 |          70 | False                   |

---

## 7. Pipeline Execution Log
Below is the chronologically ordered trace of transformations applied during this run:

1. **[Missing Values]** Numeric column 'Confirmed' imputed 1 nulls with median (60.0). Added 'Confirmed_was_missing' audit flag. *(2026-06-21 09:53:53)*
2. **[Duplicates]** No exact duplicate rows found. *(2026-06-21 09:53:53)*
3. **[Duplicates]** Found 9 near-duplicate rows based on keys ['Confirmed_was_missing']. Reported in output report. *(2026-06-21 09:53:53)*
4. **[Feature Engineering]** Created label encoding feature for categorical column 'Confirmed_was_missing'. *(2026-06-21 09:53:53)*
