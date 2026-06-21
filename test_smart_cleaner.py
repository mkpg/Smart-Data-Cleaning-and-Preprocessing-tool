import os
import pytest
import numpy as np
import pandas as pd
from smart_cleaner import SmartCleaner, clean_dataset

# =====================================================================
# pytest Fixtures for Shared Setup
# =====================================================================

@pytest.fixture
def base_numeric_df():
    """A small dataframe for numeric tests."""
    return pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        'Deaths': [0.0, 1.0, 2.0, 1.0, 0.0, 2.0, 5.0, 0.0, 1.0, 2.0],
        'Recovered': [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    })

@pytest.fixture
def base_text_df():
    """A small dataframe for text and categorical tests."""
    return pd.DataFrame({
        'Country': ['USA', 'usa', 'Usa', 'France', 'France ', 'Germany', 'Germany', 'Spain', 'Italy', 'Japan'],
        'Category': ['Diabetes', 'Diabetess', 'diabetes ', 'Cancer', 'Cancer', 'Cancer', 'Flu', 'Flu', 'Cold', 'Cold']
    })

# =====================================================================
# 1. MISSING VALUE TESTS
# =====================================================================

def test_missing_numeric_under_30(tmp_path):
    """Numeric column with <30% missing -> imputed with median, not dropped.
    Verify that the '_was_missing' flag column exists and is True/1 for the correct row."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 20.0, np.nan, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]  # 10% missing
    })
    
    cleaner = SmartCleaner(df=df, filename="under_30.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Imputed with median of the remaining values: [10, 20, 40, 50, 60, 70, 80, 90, 100] -> median is 60.0
    assert cleaner.df.loc[2, 'Confirmed'] == 60.0, "Expected missing value to be imputed with median (60.0)"
    assert 'Confirmed_was_missing' in cleaner.df.columns, "Expected audit flag column 'Confirmed_was_missing' to be created"
    assert cleaner.df.loc[2, 'Confirmed_was_missing'] == True, "Audit flag should be True for the missing row"
    assert cleaner.df.loc[0, 'Confirmed_was_missing'] == False, "Audit flag should be False for non-missing rows"
    assert len(cleaner.df) == 10, "Row count should not decrease when missing percentage is under 30%"

def test_missing_numeric_over_30(tmp_path):
    """Numeric column with >30% missing -> flagged for review (not imputed, remains null)."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, np.nan, np.nan, np.nan, 50.0, 60.0, np.nan, 80.0, 90.0, 100.0]  # 40% missing
    })
    
    cleaner = SmartCleaner(df=df, filename="over_30.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'Confirmed' in cleaner.flagged_for_review, "Expected column to be flagged for review"
    assert cleaner.flagged_for_review['Confirmed']['count'] == 4, "Flagged count should match the number of nulls"
    assert pd.isnull(cleaner.df.loc[1, 'Confirmed']), "Expected missing values to remain null when flagged for review"

def test_missing_negligible(tmp_path):
    """Column with <2% missing -> rows dropped, row count decreases by exactly the expected amount."""
    # Create 100 rows, only 1 missing value (1% missing) in 'Country'
    countries = ['USA'] * 99 + [np.nan]
    df = pd.DataFrame({
        'SNo': range(1, 101),
        'Country': countries
    })
    
    cleaner = SmartCleaner(df=df, filename="negligible.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert len(cleaner.df) == 99, "Expected exactly 1 row to be dropped since missingness is <2%"
    assert not cleaner.df['Country'].isnull().any(), "No nulls should remain in Country"

def test_missing_zero(tmp_path):
    """Column with 0% missing -> untouched, no '_was_missing' column added."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Country': ['USA'] * 10
    })
    
    cleaner = SmartCleaner(df=df, filename="zero_missing.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'Country_was_missing' not in cleaner.df.columns, "Should not add audit column if no values were missing"
    assert len(cleaner.df) == 10, "Row count should remain unchanged"

def test_missing_nulls_invariant(tmp_path):
    """Assert after cleaning: all nulls are 0 OR explicitly listed in flagged_for_review."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, np.nan, np.nan, np.nan, 50.0, 60.0, np.nan, 80.0, 90.0, 100.0],  # 40% missing (flagged)
        'Deaths': [0.0, 1.0, np.nan, 1.0, 0.0, 2.0, 5.0, 0.0, 1.0, 2.0]                     # 10% missing (imputed)
    })
    
    cleaner = SmartCleaner(df=df, filename="invariant.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    null_counts = cleaner.df.isnull().sum()
    for col in cleaner.df.columns:
        base_col = col.replace('_was_missing', '')
        if null_counts[col] > 0:
            assert base_col in cleaner.flagged_for_review, f"Null column '{col}' must be explicitly flagged for review"

# =====================================================================
# 2. DATE/TIME TESTS
# =====================================================================

def test_date_consistent(tmp_path):
    """Column with consistent date strings parses to datetime64 dtype."""
    df = pd.DataFrame({
        'SNo': range(1, 6),
        'ObservationDate': ['2020-01-22', '2020-01-23', '2020-01-24', '2020-01-25', '2020-01-26']
    })
    
    cleaner = SmartCleaner(df=df, filename="date_consistent.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert pd.api.types.is_datetime64_any_dtype(cleaner.df['ObservationDate']), "Expected date column to be parsed as datetime"

def test_date_mixed(tmp_path):
    """Column with MIXED formats still parses correctly using format='mixed'."""
    df = pd.DataFrame({
        'SNo': range(1, 6),
        'ObservationDate': ['1/22/2020', '2020-01-23', '01/24/2020', '2020-01-25', '2020-01-26']
    })
    
    cleaner = SmartCleaner(df=df, filename="date_mixed.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert pd.api.types.is_datetime64_any_dtype(cleaner.df['ObservationDate']), "Expected mixed formats to successfully parse"
    assert cleaner.df.loc[0, 'ObservationDate'].year == 2020
    assert cleaner.df.loc[0, 'ObservationDate'].month == 1
    assert cleaner.df.loc[0, 'ObservationDate'].day == 22

def test_date_garbage(tmp_path):
    """Column with some unparseable garbage values does not crash the pipeline."""
    df = pd.DataFrame({
        'SNo': range(1, 6),
        'ObservationDate': ['2020-01-22', 'not_a_date', '2020-01-24', 'garbage', '2020-01-26']
    })
    
    cleaner = SmartCleaner(df=df, filename="date_garbage.csv", output_dir=str(tmp_path))
    # Should run successfully without raising parser errors
    cleaner.execute_pipeline()
    
    # Garbage values should parse to NaT
    assert pd.isna(cleaner.df.loc[1, 'ObservationDate']), "Unparseable dates should be converted to NaT"
    assert pd.isna(cleaner.df.loc[3, 'ObservationDate']), "Unparseable dates should be converted to NaT"

def test_date_derived_columns(tmp_path):
    """Derived year/month/day/day_of_week columns are correct integers for a known date."""
    # 2020-01-22 is a Wednesday (dayofweek = 2 in pandas where Monday=0)
    df = pd.DataFrame({
        'SNo': [1],
        'ObservationDate': ['2020-01-22']
    })
    
    cleaner = SmartCleaner(df=df, filename="date_derived.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert cleaner.df.loc[0, 'ObservationDate_year'] == 2020
    assert cleaner.df.loc[0, 'ObservationDate_month'] == 1
    assert cleaner.df.loc[0, 'ObservationDate_day'] == 22
    assert cleaner.df.loc[0, 'ObservationDate_day_of_week'] == 2

def test_date_original_replaced(tmp_path):
    """Original messy string date column is standardized to datetime, not dropped from the dataframe."""
    df = pd.DataFrame({
        'SNo': [1, 2],
        'ObservationDate': ['2020-01-22', '2020-01-23']
    })
    
    cleaner = SmartCleaner(df=df, filename="date_replaced.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'ObservationDate' in cleaner.df.columns, "Original date column name must be preserved"
    assert pd.api.types.is_datetime64_any_dtype(cleaner.df['ObservationDate']), "Original column should now be datetime dtype"

# =====================================================================
# 3. TEXT/CATEGORY STANDARDIZATION TESTS
# =====================================================================

def test_text_whitespace(tmp_path):
    """Leading/trailing whitespace and double spaces are collapsed."""
    df = pd.DataFrame({
        'SNo': [1, 2],
        'Country': ['  Mainland   China  ', ' France ']
    })
    
    cleaner = SmartCleaner(df=df, filename="text_whitespace.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert cleaner.df.loc[0, 'Country'] == 'Mainland China'
    assert cleaner.df.loc[1, 'Country'] == 'France'

def test_text_case(tmp_path):
    """Case standardization normalizes to title case except for standard upper-case abbreviations."""
    df = pd.DataFrame({
        'SNo': range(1, 6),
        'Country': ['germany', 'GERMANY', 'USA', 'us', 'uk']
    })
    
    cleaner = SmartCleaner(df=df, filename="text_case.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Title-cased for standard strings
    assert cleaner.df.loc[0, 'Country'] == 'Germany'
    assert cleaner.df.loc[1, 'Country'] == 'Germany'
    
    # Preserved uppercase exceptions defined in smart_cleaner
    assert cleaner.df.loc[2, 'Country'] == 'USA'

def test_fuzzy_matching_collapsing(tmp_path):
    """Fuzzy matching collapses near-duplicates to the most frequent variant."""
    # 'Diabetes' appears twice, 'Diabetess' once, 'diabetes ' once
    # Canonical label should be 'Diabetes' (proper title-case and highest frequency)
    df = pd.DataFrame({
        'SNo': range(1, 5),
        'Category': ['Diabetes', 'Diabetess', 'diabetes ', 'Diabetes']
    })
    
    cleaner = SmartCleaner(df=df, filename="fuzzy_collapse.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Check that they all mapped to 'Diabetes'
    assert (cleaner.df['Category'] == 'Diabetes').all(), f"All categories should collapse to 'Diabetes', got {cleaner.df['Category'].tolist()}"

def test_fuzzy_matching_no_false_positive(tmp_path):
    """Negative test: Fuzzy matching does NOT incorrectly merge semantically different but similar strings."""
    df = pd.DataFrame({
        'SNo': range(1, 5),
        'Country': ['Korea, South', 'Korea, North', 'Korea, South', 'Korea, North']
    })
    
    cleaner = SmartCleaner(df=df, filename="fuzzy_negative.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    unique_countries = cleaner.df['Country'].unique()
    assert 'Korea, South' in unique_countries
    assert 'Korea, North' in unique_countries
    assert len(unique_countries) == 2, "Korea, South and Korea, North should remain separate categories"

def test_text_high_cardinality_skipped(tmp_path):
    """Column with >50 unique values is NOT treated as categorical (skipped from fuzzy matching)."""
    # Generate 55 unique values for a column
    unique_vals = [f"Item_{i}" for i in range(55)]
    # Add a variation that would otherwise be fuzzy matched
    unique_vals[1] = "Item_0_variation"
    df = pd.DataFrame({
        'SNo': range(1, 56),
        'TextCol': unique_vals
    })
    
    cleaner = SmartCleaner(df=df, filename="high_cardinality.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Verify that the column is classified under text_cols, not categorical_cols
    assert 'TextCol' in cleaner.text_cols
    assert 'TextCol' not in cleaner.categorical_cols
    assert 'TextCol' not in cleaner.standardization_mappings, "Fuzzy matching should not run on high cardinality columns"

# =====================================================================
# 4. NUMERIC VALIDATION TESTS
# =====================================================================

def test_numeric_negative_correction(tmp_path):
    """Heuristic check: negative value in count column is replaced with the positive median."""
    # 101 rows: 1 negative value, 100 positive values to trigger the >=99% positive heuristic
    confirmed_vals = [float(i) for i in range(1, 101)]
    confirmed_vals[3] = -40.0
    
    df = pd.DataFrame({
        'SNo': range(1, 101),
        'Confirmed': confirmed_vals
    })
    
    cleaner = SmartCleaner(df=df, filename="negative_correction.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Expected median of positive values is 51.0 (since we have 99 positive values from 1 to 100, excluding 4)
    assert cleaner.df.loc[3, 'Confirmed'] == 51.0, "Expected negative value to be replaced by median of positive values"

def test_numeric_logical_violation(tmp_path):
    """Logical violation: Deaths > Confirmed or Recovered > Confirmed is corrected."""
    df = pd.DataFrame({
        'SNo': range(1, 5),
        'Confirmed': [10.0, 20.0, 30.0, 40.0],
        'Deaths': [0.0, 25.0, 0.0, 0.0],       # Row 1: Deaths (25) > Confirmed (20)
        'Recovered': [0.0, 0.0, 35.0, 0.0]     # Row 2: Recovered (35) > Confirmed (30)
    })
    
    cleaner = SmartCleaner(df=df, filename="logical_violation.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Confirmed should be corrected to match Deaths and Recovered
    assert cleaner.df.loc[1, 'Confirmed'] == 25.0, "Confirmed cases should be updated to match Deaths"
    assert cleaner.df.loc[2, 'Confirmed'] == 35.0, "Confirmed cases should be updated to match Recovered"

def test_numeric_iqr_outlier(tmp_path):
    """IQR outlier detection reports extreme outlier and does NOT silently remove the row."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 12.0, 15.0, 11.0, 13.0, 14.0, 12.0, 13.0, 15.0, 1000.0] # 1000.0 is outlier
    })
    
    cleaner = SmartCleaner(df=df, filename="outlier.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'Confirmed' in cleaner.outlier_reports, "Confirmed outliers should be reported"
    assert cleaner.outlier_reports['Confirmed']['count'] == 1
    assert len(cleaner.df) == 10, "Row count should remain unchanged (no silent dropping of outliers)"

def test_numeric_clean(tmp_path):
    """Normal/clean numeric column doesn't report any outliers or logical violations."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 12.0, 14.0, 11.0, 13.0, 14.0, 12.0, 13.0, 15.0, 11.0]
    })
    
    cleaner = SmartCleaner(df=df, filename="clean_numeric.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'Confirmed' not in cleaner.outlier_reports, "Clean columns should not produce outlier reports"
    assert len(cleaner.logical_violations) == 0

# =====================================================================
# 5. DUPLICATE TESTS
# =====================================================================

def test_duplicate_exact(tmp_path):
    """Exact duplicate rows are removed from the dataframe."""
    df = pd.DataFrame({
        'SNo': [1, 2, 2, 3, 4],
        'Confirmed': [10.0, 20.0, 20.0, 30.0, 40.0]
    })
    
    cleaner = SmartCleaner(df=df, filename="exact_dup.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert len(cleaner.df) == 4, "Expected exact duplicate row to be dropped"

def test_duplicate_near(tmp_path):
    """Near-duplicate rows (same key columns, different values elsewhere) are not auto-dropped, but reported."""
    df = pd.DataFrame({
        'ObservationDate': ['2020-01-22', '2020-01-22', '2020-01-23'],
        'Province/State': ['Anhui', 'Anhui', 'Beijing'],
        'Confirmed': [10.0, 20.0, 30.0],  # Confirmed varies, making them near-duplicates rather than exact
        'Deaths': [0.0, 1.0, 0.0]
    })
    
    cleaner = SmartCleaner(df=df, filename="near_dup.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert len(cleaner.df) == 3, "Near-duplicates should not be dropped automatically"
    assert cleaner.near_duplicates_count > 0, "Near-duplicates should be detected and reported"

def test_duplicate_zero(tmp_path):
    """Dataframe with zero duplicates runs cleanly with row count unchanged."""
    df = pd.DataFrame({
        'SNo': [1, 2, 3],
        'Confirmed': [10.0, 20.0, 30.0]
    })
    
    cleaner = SmartCleaner(df=df, filename="zero_dup.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert len(cleaner.df) == 3
    assert cleaner.exact_duplicates_count == 0

# =====================================================================
# 6. FEATURE ENGINEERING ORDER TEST
# =====================================================================

def test_feature_engineering_order(tmp_path):
    """Step Ordering: derived text variables reflect the CLEANED (imputed/filled) values, not nulls."""
    # Country needs to have >= 50 unique values so it is classified as a text column and generates length/word count features
    # Also, missingness must be >= 2% (2/52 = 3.85%) so the null rows are imputed rather than dropped under the <2% negligible missingness rule
    countries = [f"Country_{i}" for i in range(50)] + [np.nan, np.nan]
    df = pd.DataFrame({
        'SNo': range(1, 53),
        'Country': countries
    })
    
    cleaner = SmartCleaner(df=df, filename="feature_order.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    # Assert length is calculated from 'Unknown' (length of 7)
    assert 'Country_length' in cleaner.df.columns
    assert cleaner.df.loc[50, 'Country_length'] == 7, "Length of imputed value 'Unknown' should be 7"
    assert cleaner.df.loc[50, 'Country_word_count'] == 1

# =====================================================================
# 7. OUTPUT / REPORT TESTS
# =====================================================================

def test_output_files_created(tmp_path):
    """Files cleaned_<filename>.csv and cleaning_report_<filename>.md are successfully created and readable."""
    df = pd.DataFrame({
        'SNo': [1, 2],
        'Confirmed': [10.0, 20.0]
    })
    
    clean_dataset(df, filename="test_output.csv", output_dir=str(tmp_path))
    
    cleaned_csv_path = os.path.join(tmp_path, "cleaned_test_output.csv")
    report_md_path = os.path.join(tmp_path, "cleaning_report_test_output.md")
    
    assert os.path.exists(cleaned_csv_path), "Cleaned CSV file was not created"
    assert os.path.exists(report_md_path), "Cleaning report Markdown file was not created"
    
    # Verify CSV is readable
    cleaned_df = pd.read_csv(cleaned_csv_path)
    assert len(cleaned_df) == 2
    
    # Verify Markdown contains expected section headers
    with open(report_md_path, 'r', encoding='utf-8') as f:
        report_content = f.read()
    assert "## 1. Executive Summary" in report_content
    assert "## 2. Missing Values Analysis & Imputation Audit" in report_content
    assert "## 5. Numeric Validation and Outlier Detection" in report_content

# =====================================================================
# 8. INVARIANT / PROPERTY TESTS
# =====================================================================

def test_invariant_row_count(tmp_path):
    """Output row count should always be less than or equal to input row count."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 20.0, np.nan, 40.0, 50.0, np.nan, 70.0, 80.0, 90.0, 100.0]
    })
    
    cleaned_df = clean_dataset(df, filename="inv_row.csv", output_dir=str(tmp_path))
    assert len(cleaned_df) <= len(df), "Cleaning pipeline should never invent/increase row count"

def test_invariant_column_count(tmp_path):
    """Output column count should always be greater than or equal to input column count."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 20.0, np.nan, 40.0, 50.0, np.nan, 70.0, 80.0, 90.0, 100.0]
    })
    
    cleaned_df = clean_dataset(df, filename="inv_col.csv", output_dir=str(tmp_path))
    assert len(cleaned_df.columns) >= len(df.columns), "Cleaned dataset should contain all original + added columns"

def test_invariant_idempotency(tmp_path):
    """Running clean_dataset a second time on already cleaned output should make zero further changes."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 20.0, np.nan, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        'Country': ['USA', 'usa', 'Usa', 'France', np.nan, 'Germany', 'Germany', 'Spain', 'Italy', 'Japan']
    })
    
    # First clean
    cleaned_df_first = clean_dataset(df, filename="idempotency_1.csv", output_dir=str(tmp_path))
    # Second clean on the output of the first clean
    cleaned_df_second = clean_dataset(cleaned_df_first.copy(), filename="idempotency_2.csv", output_dir=str(tmp_path))
    
    # Assert they are identical
    pd.testing.assert_frame_equal(cleaned_df_first, cleaned_df_second, check_dtype=True)

# =====================================================================
# 9. EDGE CASES
# =====================================================================

def test_edge_empty_df(tmp_path):
    """Empty dataframe (0 rows) does not crash the pipeline and raises zero warnings."""
    import warnings
    df = pd.DataFrame(columns=['SNo', 'Confirmed', 'Country'])
    
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")  # Trigger all warnings
        cleaned_df = clean_dataset(df, filename="empty_edge.csv", output_dir=str(tmp_path))
        
        # Filter warnings originating from smart_cleaner
        relevant_warnings = [
            warn for warn in record 
            if "smart_cleaner" in str(warn.filename)
        ]
        
    assert len(cleaned_df) == 0
    assert len(relevant_warnings) == 0, f"Expected 0 warnings from smart_cleaner, got: {[str(w.message) for w in relevant_warnings]}"

def test_edge_single_row_df(tmp_path):
    """Single-row dataframe does not crash the pipeline, handles stats cleanly."""
    df = pd.DataFrame({
        'SNo': [1],
        'Confirmed': [10.0],
        'Country': ['USA']
    })
    
    # Should run successfully without raising stats calculation errors (IQR, median)
    cleaned_df = clean_dataset(df, filename="single_row.csv", output_dir=str(tmp_path))
    assert len(cleaned_df) == 1

def test_edge_all_null_column(tmp_path):
    """Dataframe with one column entirely null is handled per the >30% missing rule (flagged, not crashed)."""
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [np.nan] * 10
    })
    
    cleaner = SmartCleaner(df=df, filename="all_null_col.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert 'Confirmed' in cleaner.flagged_for_review
    assert cleaner.flagged_for_review['Confirmed']['pct'] == 1.0

def test_edge_already_clean_df(tmp_path):
    """Already fully clean dataframe runs successfully without unnecessary modifications."""
    df = pd.DataFrame({
        'SNo': [1, 2, 3],
        'Confirmed': [10.0, 20.0, 30.0],
        'Country': ['Usa', 'France', 'Germany']
    })
    
    cleaner = SmartCleaner(df=df, filename="already_clean.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    
    assert len(cleaner.flagged_for_review) == 0
    assert len(cleaner.outlier_reports) == 0
    assert len(cleaner.df) == 3

# =====================================================================
# 10. MUTATION TESTING KILLERS
# =====================================================================

def test_kill_mutant_4_iqr_multiplier(tmp_path):
    """Kill Mutant 4: Ensure outlier detection uses exactly 1.5 * IQR.
    With multiplier 1.5, 20.0 is an outlier. With 3.0, it is not."""
    # Data: 10, 11, 12, 12, 13, 13, 14, 15, 15, 20.0
    # Q1 = 12.0, Q3 = 14.75, IQR = 2.75.
    # 1.5 multiplier upper bound = 14.75 + 1.5 * 2.75 = 18.875 (20.0 is outlier)
    # 3.0 multiplier upper bound = 14.75 + 3.0 * 2.75 = 23.000 (20.0 is NOT outlier)
    df = pd.DataFrame({
        'SNo': range(1, 11),
        'Confirmed': [10.0, 11.0, 12.0, 12.0, 13.0, 13.0, 14.0, 15.0, 15.0, 20.0]
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_4.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert 'Confirmed' in cleaner.outlier_reports, "20.0 should be detected as an outlier using 1.5 * IQR"
    assert cleaner.outlier_reports['Confirmed']['count'] == 1

def test_kill_mutant_5_zero_preservation(tmp_path):
    """Kill Mutant 5: Ensure 0.0 in a count column is preserved (not corrected).
    If operator >= 0 is mutated to > 0, 0.0 is treated as negative and overwritten."""
    df = pd.DataFrame({
        'SNo': range(1, 101),
        'Confirmed': [0.0] + [10.0]*99  # 99% positive, 0.0 is non-negative
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_5.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert cleaner.df.loc[0, 'Confirmed'] == 0.0, "Value of 0.0 should be preserved, not overwritten"

def test_kill_mutant_6_pos_pct_heuristic(tmp_path):
    """Kill Mutant 6: Ensure negative correction only triggers if positive pct >= 99%.
    If positive pct is 95% (e.g. 19 positive, 1 negative), it should NOT correct the negative."""
    # 20 rows: 1 negative (-5.0), 19 positive. pos_pct = 95%.
    confirmed_vals = [10.0]*19 + [-5.0]
    df = pd.DataFrame({
        'SNo': range(1, 21),
        'Confirmed': confirmed_vals
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_6.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert cleaner.df.loc[19, 'Confirmed'] == -5.0, "Negative value should NOT be corrected if pos_pct is only 95%"

def test_kill_mutant_7_conf_deaths_equal(tmp_path):
    """Kill Mutant 7: Ensure Confirmed == Deaths is not treated as a logical violation.
    If Confirmed < Deaths operator is mutated to <=, then equal values trigger a violation."""
    df = pd.DataFrame({
        'SNo': [1, 2],
        'Confirmed': [10.0, 10.0],
        'Deaths': [10.0, 5.0]
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_7.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert len(cleaner.logical_violations) == 0, "Confirmed == Deaths should not be a violation"

def test_kill_mutant_8_conf_recovered_equal(tmp_path):
    """Kill Mutant 8: Ensure Confirmed == Recovered is not treated as a logical violation.
    If Confirmed < Recovered operator is mutated to <=, then equal values trigger a violation."""
    df = pd.DataFrame({
        'SNo': [1, 2],
        'Confirmed': [10.0, 10.0],
        'Recovered': [10.0, 5.0]
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_8.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert len(cleaner.logical_violations) == 0, "Confirmed == Recovered should not be a violation"

def test_kill_mutant_9_numeric_categorical_boundary(tmp_path):
    """Kill Mutant 9: Ensure numeric column with <10 unique values is classified as categorical.
    If threshold is mutated to 5, a column with 7 unique values would be numeric instead of categorical."""
    df = pd.DataFrame({
        'SNo': range(1, 21),
        'IntCol': [1, 2, 3, 4, 5, 6, 7] * 2 + [1] * 6  # 7 unique values
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_9.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert 'IntCol_encoded' in cleaner.df.columns, "IntCol should be classified as categorical and encoded"

def test_kill_mutant_10_string_categorical_boundary(tmp_path):
    """Kill Mutant 10: Ensure string column with <50 unique values is classified as categorical.
    If threshold is mutated to 20, a column with 30 unique values would be text instead of categorical."""
    # 30 unique values in a string column
    categories = [f"Cat_{i}" for i in range(30)] * 2
    df = pd.DataFrame({
        'SNo': range(1, 61),
        'StrCol': categories
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_10.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert 'StrCol_encoded' in cleaner.df.columns, "StrCol should be classified as categorical and encoded"

def test_kill_mutant_11_numeric_binning_boundary(tmp_path):
    """Kill Mutant 11: Ensure numeric column with >10 unique values is binned.
    If threshold is mutated to 20, a column with 15 unique values would not be binned."""
    # 15 unique values
    df = pd.DataFrame({
        'SNo': range(1, 16),
        'NumCol': [float(i) for i in range(1, 16)]
    })
    cleaner = SmartCleaner(df=df, filename="kill_mut_11.csv", output_dir=str(tmp_path))
    cleaner.execute_pipeline()
    assert 'NumCol_binned' in cleaner.df.columns, "NumCol should be binned because unique count > 10"
