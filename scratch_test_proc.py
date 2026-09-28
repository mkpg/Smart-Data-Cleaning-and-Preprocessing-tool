import sys
from web.unstructured_processor import UnstructuredDataProcessor

def test():
    processor = UnstructuredDataProcessor()
    res = processor.process_file("patient_intake_reportCLD.pdf", filename="patient_intake_reportCLD.pdf")
    
    print("STATUS:", res['status'])
    print("PHI FINDINGS:")
    for f in res.get('phi_findings', []):
        print(f" - {f['type']}: '{f['matched_text_preview']}'")
        
    print("\nCOMPLIANCE:", res.get('compliance_validation', {}))
    print("PRIVACY STATUS:", res.get('redaction_report', {}).get('privacy_status'))
    
if __name__ == "__main__":
    test()
