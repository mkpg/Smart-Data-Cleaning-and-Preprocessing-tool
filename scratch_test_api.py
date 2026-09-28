import pandas as pd
from web.server import DataCleaner

def test_phi():
    df = pd.DataFrame({'Patient Name': ['John Doe'], 'Age': [45]})
    dc = DataCleaner(df)
    
    # Enable redact_phi
    cfg = {
        'redact_phi': {'checked': True},
        'handle_outliers': {'checked': True}
    }
    
    # Run ops
    dc.handle_outliers('cap')
    dc.redact_phi()
    
    # Get report
    before_scores = dc.calculate_quality_scores(df)
    after_scores = dc.calculate_quality_scores(dc.data)
    report = dc.generate_validation_report(before_scores, after_scores)
    
    print("PHI Redactions:", report.get('phi_redactions'))

if __name__ == '__main__':
    test_phi()
