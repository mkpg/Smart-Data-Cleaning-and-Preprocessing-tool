# Data Cleaning and Preprocessing Report: covid_19_data.csv
Generated on: 2026-06-21 09:49:19

## 1. Executive Summary
- **Original Shape**: 8509 rows, 8 columns
- **Cleaned Shape**: 8509 rows, 34 columns
- **Exact Duplicates Dropped**: 0 rows
- **Near-Duplicates Identified**: 5738 rows

### Before and After Comparison Table

| Metric | Before Cleaning | After Cleaning |
| :--- | :--- | :--- |
| **Row Count** | 8509 | 8509 |
| **Column Count** | 8 | 34 |
| **Total Null Cells** | 3751 | 0 |
| **Exact Duplicate Rows** | 0 | 0 |

---

## 2. Missing Values Analysis & Imputation Audit

| Column Name | Initial Nulls | Imputation / Action Taken | Audit Column Added? | Remaining Nulls |
| :--- | :--- | :--- | :--- | :--- |
| `SNo` | 0 | None (No missing values) | No | 0 |
| `ObservationDate` | 0 | None (No missing values) | No | 0 |
| `Province/State` | 3751 | Filled with 'Unknown' | `Province/State_was_missing` | 0 |
| `Country/Region` | 0 | None (No missing values) | No | 0 |
| `Last Update` | 0 | None (No missing values) | No | 0 |
| `Confirmed` | 0 | None (No missing values) | No | 0 |
| `Deaths` | 0 | None (No missing values) | No | 0 |
| `Recovered` | 0 | None (No missing values) | No | 0 |

---

## 3. Date / Time Standardization
The following columns were parsed to datetime, standardized to ISO format, and split into year, month, day, and day_of_week:
- **`ObservationDate`** (messy string representation removed)
- **`Last Update`** (messy string representation removed)

---

## 4. Text and Categorical Normalization
Whitespace was trimmed and spaces collapsed on all string columns. Casing was normalized to title case. No synonym mappings were triggered.

---

## 5. Numeric Validation and Outlier Detection
### Outlier Analysis (IQR Method - Capping not applied automatically)
| Column | Outlier Count | Percentage | IQR Bounds | Value Range |
| :--- | :---: | :---: | :--- | :--- |
| `Confirmed` | 1268 | 14.90% | [-205.0, 347.0] | [349.0, 69176.0] |
| `Deaths` | 1379 | 16.21% | [-1.5, 2.5] | [3.0, 6820.0] |
| `Recovered` | 1671 | 19.64% | [-15.0, 25.0] | [26.0, 60324.0] |

### Logical Violations Resolved
- Logical Violation: 3 rows have Deaths exceeding Confirmed.
- Logical Violation: 6 rows have Recovered exceeding Confirmed.

---

## 6. Duplicates Report
- **Exact duplicates**: 0 rows dropped.
- **Near-duplicates**: 5738 rows sharing keys but differing in non-key values.

#### Near-Duplicate Sample Rows:
|   SNo | ObservationDate     | Province/State   | Country/Region   | Last Update         |   Confirmed |   Deaths |   Recovered | Province/State_was_missing   |   ObservationDate_year |   ObservationDate_month |   ObservationDate_day |   ObservationDate_day_of_week |   Last Update_year |   Last Update_month |   Last Update_day |   Last Update_day_of_week |
|------:|:--------------------|:-----------------|:-----------------|:--------------------|------------:|---------:|------------:|:-----------------------------|-----------------------:|------------------------:|----------------------:|------------------------------:|-------------------:|--------------------:|------------------:|--------------------------:|
|     1 | 2020-01-22 00:00:00 | Anhui            | Mainland China   | 2020-01-22 17:00:00 |           1 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |
|     2 | 2020-01-22 00:00:00 | Beijing          | Mainland China   | 2020-01-22 17:00:00 |          14 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |
|     3 | 2020-01-22 00:00:00 | Chongqing        | Mainland China   | 2020-01-22 17:00:00 |           6 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |
|     4 | 2020-01-22 00:00:00 | Fujian           | Mainland China   | 2020-01-22 17:00:00 |           1 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |
|     5 | 2020-01-22 00:00:00 | Gansu            | Mainland China   | 2020-01-22 17:00:00 |           0 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |
|     6 | 2020-01-22 00:00:00 | Guangdong        | Mainland China   | 2020-01-22 17:00:00 |          26 |        0 |           0 | False                        |                   2020 |                       1 |                    22 |                             2 |               2020 |                   1 |                22 |                         2 |

---

## 7. Pipeline Execution Log
Below is the chronologically ordered trace of transformations applied during this run:

1. **[Missing Values]** Categorical/Text column 'Province/State' filled 3751 nulls with 'Unknown'. Added 'Province/State_was_missing' audit flag. *(2026-06-21 09:49:19)*
2. **[Date/Time]** Derived year, month, day, day_of_week from 'ObservationDate' and dropped original messy string format. *(2026-06-21 09:49:19)*
3. **[Date/Time]** Derived year, month, day, day_of_week from 'Last Update' and dropped original messy string format. *(2026-06-21 09:49:19)*
4. **[Numeric Validation]** Detected 1268 outliers (14.90%) in 'Confirmed'. Bounds: [-205.00, 347.00] *(2026-06-21 09:49:19)*
5. **[Numeric Validation]** Detected 1379 outliers (16.21%) in 'Deaths'. Bounds: [-1.50, 2.50] *(2026-06-21 09:49:19)*
6. **[Numeric Validation]** Detected 1671 outliers (19.64%) in 'Recovered'. Bounds: [-15.00, 25.00] *(2026-06-21 09:49:19)*
7. **[Numeric Validation]** Corrected logical violation in 3 rows: Set 'Confirmed' to match 'Deaths' because deaths exceeded confirmed cases. *(2026-06-21 09:49:19)*
8. **[Numeric Validation]** Corrected logical violation in 6 rows: Set 'Confirmed' to match 'Recovered' because recovered cases exceeded confirmed cases. *(2026-06-21 09:49:19)*
9. **[Duplicates]** No exact duplicate rows found. *(2026-06-21 09:49:19)*
10. **[Duplicates]** Found 5738 near-duplicate rows based on keys ['ObservationDate', 'Last Update', 'Province/State_was_missing', 'ObservationDate_year', 'ObservationDate_month', 'ObservationDate_day_of_week', 'Last Update_year', 'Last Update_month', 'Last Update_day_of_week']. Reported in output report. *(2026-06-21 09:49:19)*
11. **[Feature Engineering]** Created text length and word count features for 'Province/State'. *(2026-06-21 09:49:19)*
12. **[Feature Engineering]** Created text length and word count features for 'Country/Region'. *(2026-06-21 09:49:19)*
13. **[Feature Engineering]** Binned numeric column 'SNo' into 5 range intervals. *(2026-06-21 09:49:19)*
14. **[Feature Engineering]** Binned numeric column 'Confirmed' into 5 range intervals. *(2026-06-21 09:49:19)*
15. **[Feature Engineering]** Binned numeric column 'Deaths' into 5 range intervals. *(2026-06-21 09:49:19)*
16. **[Feature Engineering]** Binned numeric column 'Recovered' into 5 range intervals. *(2026-06-21 09:49:19)*
17. **[Feature Engineering]** Binned numeric column 'ObservationDate_day' into 5 range intervals. *(2026-06-21 09:49:19)*
18. **[Feature Engineering]** Binned numeric column 'Last Update_day' into 5 range intervals. *(2026-06-21 09:49:19)*
19. **[Feature Engineering]** Created label encoding feature for categorical column 'Province/State_was_missing'. *(2026-06-21 09:49:19)*
20. **[Feature Engineering]** Created label encoding feature for categorical column 'ObservationDate_year'. *(2026-06-21 09:49:19)*
21. **[Feature Engineering]** Created label encoding feature for categorical column 'ObservationDate_month'. *(2026-06-21 09:49:19)*
22. **[Feature Engineering]** Created label encoding feature for categorical column 'ObservationDate_day_of_week'. *(2026-06-21 09:49:19)*
23. **[Feature Engineering]** Created label encoding feature for categorical column 'Last Update_year'. *(2026-06-21 09:49:19)*
24. **[Feature Engineering]** Created label encoding feature for categorical column 'Last Update_month'. *(2026-06-21 09:49:19)*
25. **[Feature Engineering]** Created label encoding feature for categorical column 'Last Update_day_of_week'. *(2026-06-21 09:49:19)*
