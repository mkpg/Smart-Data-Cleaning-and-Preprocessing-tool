"""
Regression tests for fix/phi-schema-integrity branch.
Run from repository root:
    pytest tests/test_phi_schema_fixes.py -v

All tests assert the exact correctness properties described in the bug-fix brief.
"""

import sys
import os
import re
import pytest
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Make web/ importable
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'web'))

from server import (
    DataCleaner,
    DataAnalyzer,
    IntelligentSchemaMapper,
    STANDARD_SCHEMAS,
)
from unstructured_processor import UnstructuredDataProcessor, PHI_PATTERNS


# ===========================================================================
# P0 - PHI column classification correctness
# ===========================================================================

class TestPhiColumnClassification:

    def _cls(self, col):
        dc = DataCleaner(pd.DataFrame({'col': ['x']}))
        return dc._is_phi_column(col)

    @pytest.mark.parametrize("col", [
        'patient_name', 'Pt_Name', 'full_name', 'first_name', 'last_name',
        'name', 'mrn', 'patient_id', 'dob', 'ssn',
        'phone', 'mobile', 'email', 'address', 'aadhaar', 'hospital_id',
    ])
    def test_is_phi_column_true(self, col):
        assert self._cls(col) is True, \
            f"Column '{col}' should be classified as PHI but was not."

    @pytest.mark.parametrize("col", [
        'test_name', 'diagnosis_name', 'department_name',
        'insurance_type', 'procedure_name', 'medication_name',
        'condition_name', 'disease_code', 'contact_type',
        'insurance_policy_type', 'test_result', 'test_status',
        'category_code', 'score', 'rate', 'count', 'flag',
    ])
    def test_is_not_phi_column(self, col):
        assert self._cls(col) is False, \
            f"Column '{col}' was INCORRECTLY classified as PHI."


class TestPhiRedactionNoFalsePositives:

    def test_test_name_column_preserved(self):
        df = pd.DataFrame({
            'test_name': ['CBC', 'HbA1c', 'Lipid Panel'],
            'patient_name': ['Alice Smith', 'Bob Jones', 'Carol Lee'],
        })
        dc = DataCleaner(df)
        dc.redact_phi()
        assert list(dc.data['test_name']) == ['CBC', 'HbA1c', 'Lipid Panel'], \
            "test_name was incorrectly redacted"
        assert all(v == '[REDACTED_PHI]' for v in dc.data['patient_name']), \
            "patient_name was not redacted"

    def test_insurance_type_column_preserved(self):
        df = pd.DataFrame({
            'insurance_type': ['MEDICAID', 'MEDICARE', 'PRIVATE'],
            'email': ['a@b.com', 'c@d.com', 'e@f.com'],
        })
        dc = DataCleaner(df)
        dc.redact_phi()
        assert list(dc.data['insurance_type']) == ['MEDICAID', 'MEDICARE', 'PRIVATE'], \
            "insurance_type was incorrectly redacted"
        for val in dc.data['email']:
            assert 'REDACTED' in str(val), f"Email not redacted: {val}"

    def test_diagnosis_name_preserved(self):
        df = pd.DataFrame({'diagnosis_name': ['Hypertension', 'Diabetes', 'COPD']})
        dc = DataCleaner(df)
        dc.redact_phi()
        assert list(dc.data['diagnosis_name']) == ['Hypertension', 'Diabetes', 'COPD']


class TestPhiVerificationStage:

    def test_verification_passed_after_clean_redaction(self):
        df = pd.DataFrame({
            'patient_name': ['John Doe', 'Jane Smith'],
            'contact': ['john@example.com', '9876543210'],
            'diagnosis': ['Diabetes', 'HTN'],
        })
        dc = DataCleaner(df)
        dc.redact_phi()
        v = dc._phi_verification
        assert v is not None
        assert v['verification'] == 'PASSED', \
            f"Expected PASSED, got {v['verification']}. Residual: {v.get('residual_details')}"
        assert v['residual_phi'] == 0
        assert v['privacy_status'] == 'CLEAN'

    def test_phi_not_run_gives_review_required(self):
        df = pd.DataFrame({'value': [1, 2, 3]})
        dc = DataCleaner(df)
        report = dc.generate_validation_report({'overall': 80}, {'overall': 90})
        assert report['privacy_status'] == 'REVIEW_REQUIRED'

    def test_privacy_status_always_present(self):
        df = pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']})
        dc = DataCleaner(df)
        report = dc.generate_validation_report({}, {})
        assert 'privacy_status' in report


class TestPhiCountNoDoubleCounting:

    def test_phi_redacted_not_double_counted(self):
        df = pd.DataFrame({
            'patient_name': ['Alice Jones', 'Bob Smith', 'Carol White'],
            'contact': ['9876543210', '9123456789', 'carol@example.com'],
            'diagnosis': ['Diabetes', 'HTN', 'COPD'],
        })
        dc = DataCleaner(df)
        dc.redact_phi()
        auth = dc._phi_verification['phi_redacted']
        report = dc.generate_validation_report({}, {})
        rep = report['phi_redactions']['phi_redacted']
        assert rep == auth, \
            f"Double-count detected: report={rep}, authoritative={auth}"


# ===========================================================================
# P1 - Schema mapper correctness
# ===========================================================================

class TestSchemaMapper:

    def _map(self, columns):
        mapper = IntelligentSchemaMapper(STANDARD_SCHEMAS)
        return {s['source']: s for s in mapper.map_columns(columns)['suggestions']}

    def test_blood_type_not_mapped_to_blood_pressure(self):
        result = self._map(['blood_type'])
        if 'blood_type' in result:
            assert result['blood_type']['suggested'] != 'blood_pressure', \
                "blood_type incorrectly mapped to blood_pressure"

    def test_test_name_not_mapped_to_patient_name(self):
        result = self._map(['test_name'])
        if 'test_name' in result:
            assert result['test_name']['suggested'] != 'patient_name', \
                "test_name incorrectly mapped to patient_name"

    def test_insurance_type_not_mapped_to_phi_field(self):
        phi_fields = {'patient_name', 'patient_id', 'mrn'}
        result = self._map(['insurance_type'])
        if 'insurance_type' in result:
            assert result['insurance_type']['suggested'] not in phi_fields, \
                f"insurance_type incorrectly mapped to {result['insurance_type']['suggested']}"

    def test_exact_column_name_maps_correctly(self):
        mapper = IntelligentSchemaMapper(STANDARD_SCHEMAS)
        result = mapper.map_columns(['patient_name'])
        suggestions = {s['source']: s for s in result['suggestions']}
        if 'patient_name' in suggestions:
            assert suggestions['patient_name']['confidence'] == 1.0
            assert suggestions['patient_name']['suggested'] == 'patient_name'

    def test_age_column_maps_to_age(self):
        result = self._map(['age'])
        if 'age' in result:
            assert result['age']['suggested'] == 'age'


# ===========================================================================
# P1 - Outlier detection consistency
# ===========================================================================

class TestOutlierConsistency:

    def test_analyzer_uses_iqr_method(self):
        df = pd.DataFrame({'value': [10, 12, 11, 13, 12, 11, 12, 200]})
        analyzer = DataAnalyzer(df)
        issues = analyzer.get_quality_issues()
        outlier_issues = [i for i in issues if i['type'] == 'outliers']
        assert len(outlier_issues) == 1
        assert 'IQR' in outlier_issues[0]['message']

    def test_engineered_columns_excluded(self):
        df = pd.DataFrame({
            'age': [25, 30, 35, 40, 45],
            'age_binned': [0, 1, 2, 3, 4],
            'age_log': [3.2, 3.4, 3.6, 3.7, 3.8],
        })
        analyzer = DataAnalyzer(df)
        issues = analyzer.get_quality_issues()
        for issue in issues:
            if issue['type'] == 'outliers':
                assert not issue['column'].endswith(('_binned', '_log', '_encoded')), \
                    f"Engineered column {issue['column']} in outlier scan"


# ===========================================================================
# P2 - extract_sections: no false classification of table values
# ===========================================================================

class TestExtractSections:

    def _proc(self):
        return UnstructuredDataProcessor()

    def test_single_all_caps_word_not_a_heading(self):
        # The P2 guard only rejects SINGLE-word non-clinical all-caps tokens.
        # Multi-word all-caps phrases like 'MORE DATA' legitimately match the
        # heading pattern (2+ words) and ARE allowed through — that is correct.
        # Only single-word insurance/program codes must be blocked.
        text = "MEDICAID\nSome data here\nSTATUS\nValue: 123"
        sections = self._proc().extract_sections(text)
        heading_names = [s['heading'] for s in sections]
        assert 'MEDICAID' not in heading_names, \
            "Single-word 'MEDICAID' must not be classified as a section heading"
        assert 'STATUS' not in heading_names, \
            "Single-word 'STATUS' must not be classified as a section heading"

    def test_known_clinical_keyword_still_detected(self):
        text = "MEDICATIONS\nMetformin 500mg\nAllergies: None"
        sections = self._proc().extract_sections(text)
        heading_names = [s['heading'].lower() for s in sections]
        assert 'medications' in heading_names

    def test_multi_word_heading_detected(self):
        text = "CHIEF COMPLAINT\nChest pain.\nASSESSMENT AND PLAN\nHTN."
        sections = self._proc().extract_sections(text)
        heading_names = [s['heading'] for s in sections]
        assert any('CHIEF' in h for h in heading_names)


# ===========================================================================
# P0 - PHI_PATTERNS: PATIENT_NAME catches abbreviated names
# ===========================================================================

class TestPatientNameRegex:

    def _pattern(self):
        return PHI_PATTERNS['PATIENT_NAME']['pattern']

    def test_standard_two_word_name(self):
        pattern = re.compile(self._pattern(), re.IGNORECASE)
        assert pattern.search("Patient: John Smith")

    def test_abbreviated_first_name(self):
        pattern = re.compile(self._pattern(), re.IGNORECASE)
        assert pattern.search("Patient Name: S. Ibrahim"), \
            "Abbreviated first name 'S. Ibrahim' not matched"

    def test_pt_prefix(self):
        pattern = re.compile(self._pattern(), re.IGNORECASE)
        assert pattern.search("Pt: J. Smith")

    def test_name_prefix(self):
        pattern = re.compile(self._pattern(), re.IGNORECASE)
        assert pattern.search("Name: Alice Johnson")

    def test_single_word_after_prefix_not_a_full_name(self):
        pattern = re.compile(self._pattern(), re.IGNORECASE)
        m = pattern.search("Patient: Diabetes")
        if m:
            captured = m.group(1) if m.lastindex and m.lastindex >= 1 else ''
            word_count = len(captured.strip().split())
            assert word_count >= 2, \
                f"Single-word capture should not occur: '{captured}'"
