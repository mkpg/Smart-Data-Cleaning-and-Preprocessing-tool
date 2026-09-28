import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Patient Intake Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Free text
    elements.append(Paragraph("Patient: J. Kaur. DOB: 2024-09-13", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table
    data = [
        ["ID", "Name", "Age", "Sex", "Blood Pressure (BP)", "MEDICAID", "Insurance Name"],
        ["INT-501", "S. Ibrahim", "45", "M", "155 / 100", "Yes", "BlueCross"],
        ["INT-502", "A. Bianchi", "32", "F", "120 / 80", "No", "Aetna"],
        ["INT-503", "T. Nakamura", "50", "M", "130/85", "Yes", "Medicare"],
        ["INT-504", "N. Abadi", "29", "F", "110/70", "No", "Cigna"],
        ["INT-505", "D. Kowalski", "60", "M", "140 / 90", "Yes", "BlueCross"],
        ["INT-506", "V. Petrov", "40", "M", "125/80", "No", "Humana"],
    ]
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Section
    elements.append(Paragraph("MEDICATIONS", styles['Heading2']))
    elements.append(Paragraph("Patient is on CBC, HbA1c, BlueCross insurance.", styles['Normal']))
    elements.append(Paragraph("Drug Name: Paracetamol", styles['Normal']))
    elements.append(Paragraph("Diagnosis Name: Hypertension", styles['Normal']))
    elements.append(Paragraph("Test Name: Blood Test", styles['Normal']))
    elements.append(Paragraph("Department Name: Cardiology", styles['Normal']))
    
    doc.build(elements)

if __name__ == '__main__':
    create_pdf('patient_intake_reportCLD.pdf')
    print('Created patient_intake_reportCLD.pdf')
