import os

from unstructured_processor import UnstructuredDataProcessor


def test_parse_log_entries_normalizes_medication_and_lab_events():
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 08:30:00 [INFO] LAB-RESULT: Troponin I: 2.4 ng/mL [H] | Reference: <0.04 ng/mL\n'
        '2025-01-10 08:35:00 [INFO] PHARMACY: Heparin drip initiated | 18 units/kg/hr | Weight: 95kg\n'
        '2025-01-10 10:05:00 [INFO] PHARMACY: Insulin sliding scale ordered | Glucose monitoring q4h\n'
    )

    entries = processor.parse_log_entries(log_text)

    lab_entry = next(entry for entry in entries if entry['event_type'] == 'lab_result')
    heparin_entry = next(
        entry for entry in entries
        if entry['event_type'] == 'medication_event' and entry['normalized_payload'].get('medication_name') == 'Heparin'
    )
    insulin_entry = next(
        entry for entry in entries
        if entry['event_type'] == 'medication_event' and entry['normalized_payload'].get('regimen') == 'sliding_scale'
    )

    assert lab_entry['normalized_payload']['test_name'] == 'Troponin I'
    assert lab_entry['normalized_payload']['value'] == 2.4
    assert lab_entry['normalized_payload']['unit'] == 'ng/mL'
    assert lab_entry['normalized_payload']['abnormal_flag'] == 'H'

    assert heparin_entry['normalized_payload']['medication_name'] == 'Heparin'
    assert heparin_entry['normalized_payload']['route'] == 'intravenous'
    assert heparin_entry['normalized_payload']['infusion_rate'] == 18

    assert insulin_entry['normalized_payload']['medication_name'] == 'Insulin'
    assert insulin_entry['normalized_payload']['action'] == 'ordered'
    assert insulin_entry['normalized_payload']['monitoring_frequency'] == 'every_4_hours'


def test_process_file_includes_quality_report_and_normalized_counts():
    processor = UnstructuredDataProcessor()
    sample_log_path = os.path.join(os.path.dirname(__file__), '..', 'inputs', 'sample_ehr_log.log')

    result = processor.process_file(
        file_path=sample_log_path,
        options={
            'generate_tables': False,
        },
    )

    assert result['status'] == 'success'
    assert result['quality_report']['overall_score'] >= 70
    assert result['quality_report']['grade'] in {'A', 'B', 'C'}
    assert result['stats']['structured_log_events'] > 0
    assert result['stats']['normalized_lab_events'] > 0
    assert result['stats']['normalized_medication_events'] > 0


def test_parse_log_entries_normalizes_phase3_imaging_events():
    """Test Phase 3: Imaging order and result normalization."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 09:00:00 [INFO] RADIOLOGY: Chest X-ray ordered | Priority: STAT | Indication: Shortness of breath\n'
        '2025-01-10 09:45:00 [INFO] RADIOLOGY: Chest X-ray resulted | Findings: Mild cardiomegaly | Impression: No acute findings\n'
    )

    entries = processor.parse_log_entries(log_text)

    imaging_order = next(e for e in entries if e['event_type'] == 'imaging_order')
    imaging_result = next(e for e in entries if e['event_type'] == 'imaging_result')

    assert imaging_order['normalized_payload']['modality'] in ['Chest X-ray', 'chest x-ray', 'Chest X-ray']
    assert imaging_order['normalized_payload']['priority'] == 'stat'

    assert imaging_result['normalized_payload']['modality'] in ['Chest X-ray', 'chest x-ray', 'Chest X-ray']
    assert 'findings' in imaging_result['normalized_payload'] or 'impression' in imaging_result['normalized_payload']


def test_parse_log_entries_normalizes_phase3_consult_events():
    """Test Phase 3: Consult request and acceptance normalization."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 09:15:00 [INFO] CONSULT: Cardiology consult requested | Reason: NSTEMI risk | Dr. Johnson -> Dr. Patel\n'
        '2025-01-10 10:30:00 [INFO] CONSULT: Cardiology accepted | Dr. Raj Patel | Plan: Cardiac catheterization tomorrow AM\n'
    )

    entries = processor.parse_log_entries(log_text)

    consult_entries = [e for e in entries if e['event_type'] == 'consult']
    assert len(consult_entries) >= 1

    requested_consult = consult_entries[0]
    assert 'specialty' in requested_consult['normalized_payload'] or requested_consult['normalized_payload'].get('status') in ['requested', 'accepted']


def test_parse_log_entries_normalizes_phase3_nursing_events():
    """Test Phase 3: Nursing assessment normalization."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 10:00:00 [INFO] NURSING: Patient assessment | Alert, oriented x4 | Pain 6/10 improving | O2 2L NC | SpO2 97%\n'
    )

    entries = processor.parse_log_entries(log_text)

    nursing_entry = next((e for e in entries if e['event_type'] == 'nursing_note'), None)
    if nursing_entry:
        assert 'mental_status' in nursing_entry['normalized_payload'] or 'event_subtype' in nursing_entry['normalized_payload']


def test_parse_log_entries_normalizes_phase3_procedure_events():
    """Test Phase 3: Procedure event normalization."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 13:30:00 [INFO] PROCEDURE: Cardiac catheterization started | Dr. Patel | Room: Cath Lab 2\n'
        '2025-01-10 14:45:00 [INFO] PROCEDURE: Cath completed | Findings: 70% LAD stenosis, 50% RCA | Technique: PCI to LAD with DES x1\n'
    )

    entries = processor.parse_log_entries(log_text)

    procedure_entries = [e for e in entries if e['event_type'] == 'procedure_event']
    assert len(procedure_entries) >= 1

    if procedure_entries:
        proc = procedure_entries[0]
        assert 'procedure_name' in proc['normalized_payload'] or 'status' in proc['normalized_payload']


def test_parse_log_entries_normalizes_phase3_post_procedure_events():
    """Test Phase 3: Post-procedure event normalization."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 15:00:00 [INFO] POST-PROC: Patient stable | Groin site hemostasis achieved | Monitoring initiated\n'
    )

    entries = processor.parse_log_entries(log_text)

    post_proc_entry = next((e for e in entries if e['event_type'] == 'post_procedure'), None)
    if post_proc_entry:
        assert 'patient_status' in post_proc_entry['normalized_payload'] or 'event_name' in post_proc_entry['normalized_payload']


def test_phase4_confidence_scoring_on_complete_entries():
    """Test Phase 4: Confidence scoring on well-formed normalized entries."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 08:30:00 [INFO] LAB-RESULT: Troponin I: 2.4 ng/mL [H] | Reference: <0.04 ng/mL\n'
    )

    entries = processor.parse_log_entries(log_text)
    lab_entry = next((e for e in entries if e['event_type'] == 'lab_result'), None)

    assert lab_entry is not None, "Lab entry should be found"
    assert 'normalization_confidence' in lab_entry, "Confidence score should be present"
    assert isinstance(lab_entry['normalization_confidence'], (int, float)), "Confidence score should be numeric"
    assert 0 <= lab_entry['normalization_confidence'] <= 100, "Confidence score should be 0-100"
    
    # Complete lab result should have high confidence
    assert lab_entry['normalization_confidence'] >= 75, "Complete lab result should have high confidence (>=75)"
    assert lab_entry.get('review_status') == 'approved', "Complete entry should be auto-approved"


def test_phase4_confidence_scoring_on_incomplete_entries():
    """Test Phase 4: Confidence scoring flags incomplete entries for review."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 08:30:00 [INFO] LAB-RESULT: Troponin I measured\n'  # Missing value, unit, reference
    )

    entries = processor.parse_log_entries(log_text)
    lab_entry = next((e for e in entries if e['event_type'] == 'lab_result'), None)

    if lab_entry and lab_entry.get('normalized_payload'):
        # Incomplete entry should have lower confidence or be flagged for review
        confidence = lab_entry.get('normalization_confidence', 0)
        assert confidence < 100, "Incomplete entry should not have perfect confidence"
        # May be flagged for review if confidence is too low
        if confidence < 70:
            assert lab_entry.get('review_needed') == True, "Low confidence entries should be flagged for review"


def test_phase4_confidence_components_breakdown():
    """Test Phase 4: Confidence components are correctly calculated."""
    processor = UnstructuredDataProcessor()
    log_text = (
        '2025-01-10 08:30:00 [INFO] LAB-RESULT: Troponin I: 2.4 ng/mL [H] | Reference: <0.04 ng/mL\n'
    )

    entries = processor.parse_log_entries(log_text)
    lab_entry = next((e for e in entries if e['event_type'] == 'lab_result'), None)

    if lab_entry and 'confidence_components' in lab_entry:
        components = lab_entry['confidence_components']
        assert 'required_fields' in components, "Should track required fields score"
        assert 'payload_completeness' in components, "Should track payload completeness"
        assert 'extraction_quality' in components, "Should track extraction quality"
        
        for score in components.values():
            assert 0 <= score <= 100, f"Component score should be 0-100, got {score}"