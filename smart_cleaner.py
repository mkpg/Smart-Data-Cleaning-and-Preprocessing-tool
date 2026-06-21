import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from thefuzz import fuzz, process

class SmartCleaner:
    def __init__(self, file_path=None, df=None, filename=None, output_dir=None):
        self.file_path = file_path
        self.output_dir = output_dir
        if file_path is not None:
            self.filename = os.path.basename(file_path)
            self.df = pd.read_csv(file_path)
        elif df is not None:
            self.filename = filename if filename else "in_memory.csv"
            self.df = df.copy()
        else:
            raise ValueError("Either file_path or df must be provided.")
        self.original_df = self.df.copy()
        
        # Metadata / Tracking
        self.transformations = []
        self.flagged_for_review = {}
        self.removed_null_rows_info = []
        self.standardization_mappings = {}
        
        # Classification
        self.date_cols = []
        self.numeric_cols = []
        self.categorical_cols = []
        self.text_cols = []
        self.other_cols = []
        
    def log_transformation(self, category, description):
        self.transformations.append({
            'category': category,
            'description': description,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    def run_inspection(self):
        """Perform initial inspection and print results."""
        print("="*60)
        print(f" INITIAL DATA QUALITY INSPECTION FOR: {self.filename}")
        print("="*60)
        print(f"Shape: {self.df.shape[0]} rows, {self.df.shape[1]} columns\n")
        
        # 1. Classify columns
        self.classify_columns()
        
        # 2. Print columns and types
        print("1. COLUMN METADATA:")
        null_counts = self.df.isnull().sum()
        for col in self.df.columns:
            if len(self.df) == 0:
                null_pct = 0.0
            else:
                null_pct = (null_counts[col] / len(self.df)) * 100
            col_type = "Numeric" if col in self.numeric_cols else \
                       "Date/Time" if col in self.date_cols else \
                       "Categorical" if col in self.categorical_cols else \
                       "Text/String" if col in self.text_cols else "Other"
            print(f" - {col:<25} | Type: {str(self.df[col].dtype):<8} | Role: {col_type:<12} | Nulls: {null_counts[col]:<5} ({null_pct:.2f}%)")
        
        # 3. Print duplicates
        print("\n2. DUPLICATES:")
        exact_dups = self.df.duplicated().sum()
        print(f" - Exact duplicate rows: {exact_dups}")
        
        # 4. Categorical columns samples
        print("\n3. CATEGORICAL COLUMN SAMPLES (<50 unique values):")
        has_cat = False
        for col in self.categorical_cols:
            has_cat = True
            unique_vals = self.df[col].dropna().unique()
            print(f" - {col:<25} ({len(unique_vals)} unique values):")
            print(f"   Samples: {list(unique_vals[:10])}")
        if not has_cat:
            print(" - No columns classified as categorical (<50 unique values).")
            
        print("\n" + "="*60 + "\n")

    def classify_columns(self):
        """Classify columns dynamically based on types and patterns."""
        # Keep track of date columns we already identified and parsed
        old_date_cols = list(self.date_cols)
        self.date_cols = []
        self.numeric_cols = []
        self.categorical_cols = []
        self.text_cols = []
        self.other_cols = []
        
        date_keywords = ['date', 'time', 'update', 'created', 'dob', 'admission', 'discharge']
        
        for col in self.df.columns:
            # Skip engineered columns from classification to ensure idempotency
            if col.endswith('_encoded') or col.endswith('_binned') or col.endswith('_length') or col.endswith('_word_count') or col.endswith('_was_missing'):
                continue
                
            col_lower = col.lower()
            
            # If we already identified this column as datetime and processed it, keep it as date
            if col in old_date_cols or pd.api.types.is_datetime64_any_dtype(self.df[col]):
                self.date_cols.append(col)
                continue
                
            # Check if column is already numeric
            if pd.api.types.is_numeric_dtype(self.df[col]):
                # If numeric but has very low unique values, check if it's acting as categorical
                # Excluding float continuous data
                if self.df[col].nunique() < 10 and not pd.api.types.is_float_dtype(self.df[col]):
                    self.categorical_cols.append(col)
                else:
                    self.numeric_cols.append(col)
                continue
                
            # Check if column is datetime
            if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                self.date_cols.append(col)
                continue
                
            # Check if string column matches date patterns
            is_date_by_name = any(kw in col_lower for kw in date_keywords)
            non_null_vals = self.df[col].dropna()
            
            if len(non_null_vals) > 0:
                # Try parsing sample values as date
                sample_size = min(len(non_null_vals), 100)
                parsed_dates = pd.to_datetime(non_null_vals.sample(sample_size, random_state=42), errors='coerce', format='mixed')
                parsed_pct = parsed_dates.notna().sum() / sample_size
                
                if parsed_pct > 0.7 or (is_date_by_name and parsed_pct > 0.3):
                    self.date_cols.append(col)
                    continue
            
            # Object/String columns
            if self.df[col].dtype == 'object':
                unique_count = self.df[col].nunique()
                if unique_count < 50:
                    self.categorical_cols.append(col)
                else:
                    self.text_cols.append(col)
            else:
                self.other_cols.append(col)

    def clean_missing_values(self):
        """Rule 1: Resolve missing values with audit flags and review thresholds."""
        print("Executing Step 1: Missing Values Resolution...")
        null_counts = self.df.isnull().sum()
        
        for col in self.df.columns:
            missing_count = null_counts[col]
            if missing_count == 0:
                continue
                
            missing_pct = missing_count / len(self.df)
            
            # 1. Numeric column handling
            if col in self.numeric_cols:
                if missing_pct > 0.30:
                    # Flag for review
                    self.flagged_for_review[col] = {
                        'reason': f'High missing percentage ({missing_pct*100:.1f}%)',
                        'count': int(missing_count),
                        'pct': missing_pct
                    }
                    self.log_transformation('Missing Values', f"Numeric column '{col}' has high missingness ({missing_pct*100:.1f}%) - flagged for review, not auto-imputed.")
                else:
                    # Impute with median
                    median_val = self.df[col].median()
                    self.df[f'{col}_was_missing'] = self.df[col].isnull()
                    self.df[col] = self.df[col].fillna(median_val)
                    self.log_transformation('Missing Values', f"Numeric column '{col}' imputed {missing_count} nulls with median ({median_val}). Added '{col}_was_missing' audit flag.")
            
            # 2. Categorical / Text column handling
            elif col in self.categorical_cols or col in self.text_cols or col in self.date_cols:
                if missing_pct < 0.02:
                    # Negligible missingness, justified drop
                    before_rows = len(self.df)
                    self.df = self.df.dropna(subset=[col])
                    dropped_count = before_rows - len(self.df)
                    self.removed_null_rows_info.append(f"Dropped {dropped_count} rows due to negligible missingness (<2%) in '{col}'.")
                    self.log_transformation('Missing Values', f"Dropped {dropped_count} rows with nulls in '{col}' (missingness {missing_pct*100:.2f}% is negligible <2%).")
                else:
                    # Fill with 'Unknown' or relevant fallback
                    fallback = 'Unknown'
                    self.df[f'{col}_was_missing'] = self.df[col].isnull()
                    self.df[col] = self.df[col].fillna(fallback)
                    self.log_transformation('Missing Values', f"Categorical/Text column '{col}' filled {missing_count} nulls with '{fallback}'. Added '{col}_was_missing' audit flag.")

    def parse_datetime_columns(self):
        """Rule 2: Parse, standardize dates, derive parts, and drop original messy strings."""
        print("Executing Step 2: Date/Time Processing...")
        
        # We re-run classification to update state after missing values handling
        self.classify_columns()
        
        for col in list(self.date_cols):
            # Parse to datetime
            original_series = self.df[col].copy()
            # If filled with 'Unknown', handle it
            if original_series.dtype == 'object':
                # Convert 'Unknown' to NaT temporarily for parsing
                temp_series = original_series.replace('Unknown', pd.NaT)
                parsed_dates = pd.to_datetime(temp_series, errors='coerce', format='mixed')
            else:
                parsed_dates = pd.to_datetime(original_series, errors='coerce', format='mixed')
            
            # Derive useful parts (handling NaT cleanly - parts will be float/int with NaN or we can fill with -1)
            self.df[f'{col}_year'] = parsed_dates.dt.year.fillna(-1).astype(int)
            self.df[f'{col}_month'] = parsed_dates.dt.month.fillna(-1).astype(int)
            self.df[f'{col}_day'] = parsed_dates.dt.day.fillna(-1).astype(int)
            self.df[f'{col}_day_of_week'] = parsed_dates.dt.dayofweek.fillna(-1).astype(int)
            
            # Keep the standardized datetime object as the column value.
            # Convert to datetime64[ns] so it remains a datetime column in subsequent steps.
            self.df[col] = parsed_dates
            
            self.log_transformation('Date/Time', f"Derived year, month, day, day_of_week from '{col}' and dropped original messy string format.")

    def standardize_categories_and_text(self):
        """Rule 3: Clean whitespace, fix casing, and resolve categorical synonyms using fuzzy matching."""
        print("Executing Step 3: Text and Category Standardization...")
        self.classify_columns()
        
        # 1. Clean whitespace and collapse spaces on all text/categorical columns
        for col in self.categorical_cols + self.text_cols:
            if col in self.df.columns and self.df[col].dtype == 'object':
                # Preserve audit string 'Unknown'
                self.df[col] = self.df[col].astype(str).str.strip()
                self.df[col] = self.df[col].str.replace(r'\s+', ' ', regex=True)
                
                # Check for casing consistency
                if col in self.categorical_cols:
                    # Keep human-readable proper Title Case, except for standard codes
                    self.df[col] = self.df[col].apply(lambda x: x.title() if x not in ('Unknown', 'US', 'USA', 'UK', 'UN', 'EU') else x)
        
        # 2. Fuzzy mapping for categorical columns to standardize near-duplicates
        for col in self.categorical_cols:
            if col not in self.df.columns or self.df[col].dtype != 'object':
                continue
                
            unique_vals = [v for v in self.df[col].unique() if v not in ('Unknown', '', 'nan')]
            if len(unique_vals) <= 1:
                continue
            
            mapping = {}
            val_counts = self.df[col].value_counts()
            
            # Use fuzzy matching to find variations
            already_mapped = set()
            for val in unique_vals:
                if val in already_mapped:
                    continue
                    
                # Find similar values in the rest of unique values
                matches = process.extract(val, unique_vals, scorer=fuzz.ratio)
                similar_group = [m[0] for m in matches if m[1] >= 85]
                
                if len(similar_group) > 1:
                    # Determine the canonical label as the most frequent variant in the dataset
                    canonical = max(similar_group, key=lambda x: val_counts.get(x, 0))
                    for sim_val in similar_group:
                        if sim_val != canonical:
                            mapping[sim_val] = canonical
                            already_mapped.add(sim_val)
                    already_mapped.add(canonical)
            
            if mapping:
                self.standardization_mappings[col] = mapping
                self.df[col] = self.df[col].replace(mapping)
                details = ", ".join([f"'{k}' -> '{v}'" for k, v in mapping.items()])
                self.log_transformation('Text/Category Standardization', f"Standardized categorical synonyms in '{col}': {details}")

    def validate_numeric_values(self):
        """Rule 4: Validate numeric logic, check for impossible values, and report outliers."""
        print("Executing Step 4: Numeric Validation...")
        self.classify_columns()
        
        self.outlier_reports = {}
        self.logical_violations = []
        
        if len(self.df) == 0:
            return
            
        for col in self.numeric_cols:
            series = self.df[col]
            
            # 1. Check for negative values in columns that should only be positive
            # Heuristics: if >99% of values are positive, negative values are likely errors
            pos_mask = series >= 0
            pos_pct = pos_mask.sum() / len(series)
            if pos_pct >= 0.99 and pos_pct < 1.0:
                neg_count = (~pos_mask).sum()
                # Correct: set to NaN and impute with median
                median_val = series[pos_mask].median()
                self.df.loc[~pos_mask, col] = median_val
                self.log_transformation('Numeric Validation', f"Corrected {neg_count} impossible negative values in '{col}' by replacing them with the positive median ({median_val}).")
            
            # 2. IQR Outlier Detection (Report only, do not cap/remove silently)
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                outlier_count = len(outliers)
                if outlier_count > 0:
                    self.outlier_reports[col] = {
                        'count': outlier_count,
                        'pct': outlier_count / len(series) * 100,
                        'bounds': (lower_bound, upper_bound),
                        'min_outlier': outliers.min(),
                        'max_outlier': outliers.max()
                    }
                    self.log_transformation('Numeric Validation', f"Detected {outlier_count} outliers ({outlier_count/len(series)*100:.2f}%) in '{col}'. Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
        
        # 3. Logical Violations (e.g. Confirmed < Deaths or Recovered in COVID data)
        # Check standard clinical or COVID-19 rules if columns exist
        cols_lower = [c.lower() for c in self.df.columns]
        
        # Check COVID columns: Confirmed, Deaths, Recovered
        has_confirmed = 'confirmed' in cols_lower
        has_deaths = 'deaths' in cols_lower
        has_recovered = 'recovered' in cols_lower
        
        if has_confirmed and (has_deaths or has_recovered):
            conf_col = self.df.columns[cols_lower.index('confirmed')]
            
            if has_deaths:
                death_col = self.df.columns[cols_lower.index('deaths')]
                violation_mask = self.df[conf_col] < self.df[death_col]
                viol_count = violation_mask.sum()
                if viol_count > 0:
                    self.logical_violations.append(f"Logical Violation: {viol_count} rows have {death_col} exceeding {conf_col}.")
                    # Correct: set Confirmed to Deaths where it's less
                    self.df.loc[violation_mask, conf_col] = self.df.loc[violation_mask, death_col]
                    self.log_transformation('Numeric Validation', f"Corrected logical violation in {viol_count} rows: Set '{conf_col}' to match '{death_col}' because deaths exceeded confirmed cases.")
            
            if has_recovered:
                rec_col = self.df.columns[cols_lower.index('recovered')]
                violation_mask = self.df[conf_col] < self.df[rec_col]
                viol_count = violation_mask.sum()
                if viol_count > 0:
                    self.logical_violations.append(f"Logical Violation: {viol_count} rows have {rec_col} exceeding {conf_col}.")
                    # Correct: set Confirmed to Recovered
                    self.df.loc[violation_mask, conf_col] = self.df.loc[violation_mask, rec_col]
                    self.log_transformation('Numeric Validation', f"Corrected logical violation in {viol_count} rows: Set '{conf_col}' to match '{rec_col}' because recovered cases exceeded confirmed cases.")

    def handle_duplicates(self):
        """Rule 5: Check exact and near-duplicates and report before dropping."""
        print("Executing Step 5: Duplicate Analysis...")
        
        # 1. Exact duplicates
        self.exact_duplicates_count = self.df.duplicated().sum()
        if self.exact_duplicates_count > 0:
            self.df = self.df.drop_duplicates()
            self.log_transformation('Duplicates', f"Dropped {self.exact_duplicates_count} exact duplicate rows.")
        else:
            self.log_transformation('Duplicates', "No exact duplicate rows found.")
            
        # 2. Near-duplicates
        # Let's define key columns as date columns + categorical columns
        key_cols = [c for c in (self.date_cols + self.categorical_cols) if c in self.df.columns]
        
        self.near_duplicates_count = 0
        self.near_duplicates_sample = pd.DataFrame()
        
        if len(key_cols) > 0 and len(self.df.columns) > len(key_cols):
            # Find rows with identical keys but different non-key values
            dups_mask = self.df.duplicated(subset=key_cols, keep=False)
            all_dups = self.df[dups_mask]
            
            # Exclude exact duplicates (which have already been dropped)
            # The remaining ones are near-duplicates
            if len(all_dups) > 0:
                self.near_duplicates_count = len(all_dups)
                self.near_duplicates_sample = all_dups.sort_values(by=key_cols).head(6)
                self.log_transformation('Duplicates', f"Found {self.near_duplicates_count} near-duplicate rows based on keys {key_cols}. Reported in output report.")
        
    def perform_feature_engineering(self):
        """Rule 6: Feature engineering applied ONLY after steps 1-5 are done."""
        print("Executing Step 6: Feature Engineering...")
        self.classify_columns()
        
        # Text/String Columns derived features
        for col in self.text_cols:
            if col in self.df.columns and self.df[col].dtype == 'object':
                self.df[f'{col}_length'] = self.df[col].astype(str).str.len()
                self.df[f'{col}_word_count'] = self.df[col].astype(str).str.split().str.len()
                self.log_transformation('Feature Engineering', f"Created text length and word count features for '{col}'.")
                
        # Numeric Columns binned ranges
        for col in self.numeric_cols:
            if col in self.df.columns and self.df[col].nunique() > 10:
                try:
                    # Bin into 5 groups
                    self.df[f'{col}_binned'] = pd.cut(self.df[col], bins=5, labels=False)
                    self.log_transformation('Feature Engineering', f"Binned numeric column '{col}' into 5 range intervals.")
                except Exception as e:
                    self.log_transformation('Feature Engineering', f"Failed to bin '{col}': {e}")
                    
        # Categorical Columns label encodings
        for col in self.categorical_cols:
            if col in self.df.columns:
                self.df[f'{col}_encoded'] = pd.factorize(self.df[col])[0]
                self.log_transformation('Feature Engineering', f"Created label encoding feature for categorical column '{col}'.")

    def assert_no_nulls(self):
        """Ensure no unexplained nulls exist in the dataset."""
        null_counts = self.df.isnull().sum()
        has_nulls = False
        self.unexplained_nulls = {}
        
        for col in self.df.columns:
            if null_counts[col] > 0:
                # Check if it was flagged for review (intentionally left null)
                base_col = col.replace('_was_missing', '')
                if base_col in self.flagged_for_review:
                    continue
                has_nulls = True
                self.unexplained_nulls[col] = int(null_counts[col])
                
        if has_nulls:
            print(f"WARNING: Unexplained null values remaining: {self.unexplained_nulls}")
        else:
            print("Assertion Passed: All columns have 0 unexplained nulls!")

    def save_output_and_report(self):
        """Rule 7: Save output cleaned dataset and generate before/after report."""
        print("Executing Step 7: Saving Cleaned Dataset and Generating Report...")
        
        # Save CSV
        if self.output_dir is not None:
            dir_name = self.output_dir
        elif self.file_path is not None:
            dir_name = os.path.dirname(self.file_path)
        else:
            dir_name = "."
            
        output_filename = f"cleaned_{self.filename}"
        output_path = os.path.join(dir_name, output_filename)
        self.df.to_csv(output_path, index=False)
        print(f"Cleaned dataset saved to: {output_path}")
        
        # Build Markdown Report
        report_path = os.path.join(dir_name, f"cleaning_report_{self.filename.replace('.csv', '')}.md")
        
        report_content = f"""# Data Cleaning and Preprocessing Report: {self.filename}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. Executive Summary
- **Original Shape**: {self.original_df.shape[0]} rows, {self.original_df.shape[1]} columns
- **Cleaned Shape**: {self.df.shape[0]} rows, {self.df.shape[1]} columns
- **Exact Duplicates Dropped**: {self.exact_duplicates_count} rows
- **Near-Duplicates Identified**: {self.near_duplicates_count} rows

### Before and After Comparison Table

| Metric | Before Cleaning | After Cleaning |
| :--- | :--- | :--- |
| **Row Count** | {self.original_df.shape[0]} | {self.df.shape[0]} |
| **Column Count** | {self.original_df.shape[1]} | {self.df.shape[1]} |
| **Total Null Cells** | {self.original_df.isnull().sum().sum()} | {self.df.isnull().sum().sum()} |
| **Exact Duplicate Rows** | {self.exact_duplicates_count} | 0 |

---

## 2. Missing Values Analysis & Imputation Audit

| Column Name | Initial Nulls | Imputation / Action Taken | Audit Column Added? | Remaining Nulls |
| :--- | :--- | :--- | :--- | :--- |
"""
        
        orig_nulls = self.original_df.isnull().sum()
        final_nulls = self.df.isnull().sum()
        
        for col in self.original_df.columns:
            init_n = orig_nulls[col]
            fin_n = final_nulls.get(col, 0)
            
            if init_n == 0:
                action = "None (No missing values)"
                audit = "No"
            elif col in self.flagged_for_review:
                action = f"Flagged for Review (>30% missing: {self.flagged_for_review[col]['pct']*100:.1f}%)"
                audit = "No"
            elif col in self.removed_null_rows_info:
                action = "Dropped rows (<2% missing)"
                audit = "No"
            else:
                if col in self.numeric_cols:
                    action = "Imputed with Median"
                else:
                    action = "Filled with 'Unknown'"
                audit = f"`{col}_was_missing`"
                
            report_content += f"| `{col}` | {init_n} | {action} | {audit} | {fin_n} |\n"
            
        report_content += "\n"
        
        if self.flagged_for_review:
            report_content += "### ⚠️ Flagged Columns (Intentionally Left Null)\n"
            for col, info in self.flagged_for_review.items():
                report_content += f"- **`{col}`**: {info['count']} missing values ({info['pct']*100:.1f}%). Exceeds 30% threshold. Requires manual verification.\n"
            report_content += "\n"
            
        if self.removed_null_rows_info:
            report_content += "### 🗑️ Negligible Missing Row Drops\n"
            for item in self.removed_null_rows_info:
                report_content += f"- {item}\n"
            report_content += "\n"

        report_content += """---

## 3. Date / Time Standardization
"""
        if self.date_cols:
            report_content += "The following columns were parsed to datetime, standardized to ISO format, and split into year, month, day, and day_of_week:\n"
            for col in self.date_cols:
                report_content += f"- **`{col}`** (messy string representation removed)\n"
        else:
            report_content += "No date/time columns were detected.\n"
            
        report_content += """
---

## 4. Text and Categorical Normalization
"""
        if self.standardization_mappings:
            report_content += "Identified near-matches and spelling inconsistencies. Mapped to canonical labels:\n\n"
            for col, mapping in self.standardization_mappings.items():
                report_content += f"### Column: `{col}`\n"
                for k, v in mapping.items():
                    report_content += f"- '{k}' ➔ '{v}'\n"
                report_content += "\n"
        else:
            report_content += "Whitespace was trimmed and spaces collapsed on all string columns. Casing was normalized to title case. No synonym mappings were triggered.\n"

        report_content += """
---

## 5. Numeric Validation and Outlier Detection
"""
        if self.outlier_reports:
            report_content += "### Outlier Analysis (IQR Method - Capping not applied automatically)\n"
            report_content += "| Column | Outlier Count | Percentage | IQR Bounds | Value Range |\n"
            report_content += "| :--- | :---: | :---: | :--- | :--- |\n"
            for col, info in self.outlier_reports.items():
                report_content += f"| `{col}` | {info['count']} | {info['pct']:.2f}% | [{info['bounds'][0]:.1f}, {info['bounds'][1]:.1f}] | [{info['min_outlier']}, {info['max_outlier']}] |\n"
            report_content += "\n"
        else:
            report_content += "No statistical outliers detected in numeric columns.\n\n"
            
        if self.logical_violations:
            report_content += "### Logical Violations Resolved\n"
            for violation in self.logical_violations:
                report_content += f"- {violation}\n"
        else:
            report_content += "No logical range or consistency violations detected.\n"

        report_content += """
---

## 6. Duplicates Report
"""
        report_content += f"- **Exact duplicates**: {self.exact_duplicates_count} rows dropped.\n"
        report_content += f"- **Near-duplicates**: {self.near_duplicates_count} rows sharing keys but differing in non-key values.\n"
        
        if not self.near_duplicates_sample.empty:
            report_content += "\n#### Near-Duplicate Sample Rows:\n"
            report_content += self.near_duplicates_sample.to_markdown(index=False)
            report_content += "\n"

        report_content += """
---

## 7. Pipeline Execution Log
Below is the chronologically ordered trace of transformations applied during this run:

"""
        for step, trans in enumerate(self.transformations, 1):
            report_content += f"{step}. **[{trans['category']}]** {trans['description']} *({trans['timestamp']})*\n"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"Detailed cleaning report saved to: {report_path}")

    def execute_pipeline(self):
        """Execute the entire 7-step pipeline in order."""
        self.run_inspection()
        self.clean_missing_values()
        self.parse_datetime_columns()
        self.standardize_categories_and_text()
        self.validate_numeric_values()
        self.handle_duplicates()
        self.perform_feature_engineering()
        self.assert_no_nulls()
        self.save_output_and_report()

def clean_dataset(df: pd.DataFrame, filename: str = "dataset.csv", output_dir: str = None) -> pd.DataFrame:
    """Standalone wrapper function to execute the SmartCleaner pipeline on an in-memory DataFrame."""
    cleaner = SmartCleaner(df=df, filename=filename, output_dir=output_dir)
    cleaner.execute_pipeline()
    return cleaner.df

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python smart_cleaner.py <path_to_csv>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: file '{csv_path}' does not exist.")
        sys.exit(1)
        
    cleaner = SmartCleaner(csv_path)
    cleaner.execute_pipeline()
