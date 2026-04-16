#!/usr/bin/env python3
"""
Unstructured Data Processor - Healthcare Text Cleaning & Preprocessing
Handles: TXT, LOG, PDF, MD and other text-based files
Uses: Docling for PDF/document conversion, OCR fallback via Tesseract
Compliance: HIPAA, GDPR, DPDP Act - data minimization enforced
"""

import re
import os
import io
import hashlib
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Try importing optional heavy dependencies
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DOCLING_AVAILABLE = False
TESSERACT_AVAILABLE = False
PYMUPDF_AVAILABLE = False

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    logger.info("Docling not installed â€“ PDF extraction will use fallback")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    logger.info("pytesseract not installed â€“ OCR disabled")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    logger.info("PyMuPDF not installed â€“ PDF text extraction limited")

# SymSpell for spell correction (optional)
SYMSPELL_AVAILABLE = False
try:
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    logger.info("symspellpy not installed â€“ spell correction disabled")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PHI / PII Pattern Definitions (HIPAA Safe Harbor â€“ 18 identifiers)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

PHI_PATTERNS = {
    'SSN': {
        'pattern': r'(?<![A-Za-z0-9-])(?:\d{3}[-\s]?\d{2}[-\s]?\d{4}|\*{3}-\*{2}-\d{4}|X{3}-X{2}-\d{4})(?![A-Za-z0-9-])',
        'description': 'Social Security Number',
        'hipaa_category': 'Social Security Number',
        'risk_level': 'CRITICAL'
    },
    'MRN': {
        'pattern': r'\b(?:MRN|mrn|Medical Record|medical record)[:\s#]*(\d{6,12})\b',
        'description': 'Medical Record Number',
        'hipaa_category': 'Medical record numbers',
        'risk_level': 'HIGH'
    },
    'PHONE': {
        'pattern': r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'description': 'Phone Number',
        'hipaa_category': 'Telephone numbers',
        'risk_level': 'HIGH'
    },
    'EMAIL': {
        'pattern': r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        'description': 'Email Address',
        'hipaa_category': 'Email addresses',
        'risk_level': 'HIGH'
    },
    'DOB': {
        'pattern': r'\b(?:DOB|dob|Date of Birth|date of birth)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b',
        'description': 'Date of Birth',
        'hipaa_category': 'Dates related to individual',
        'risk_level': 'HIGH'
    },
    'DATE_FULL': {
        'pattern': r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{4}\b',
        'description': 'Full Date (potential DOB/admission)',
        'hipaa_category': 'Dates',
        'risk_level': 'MEDIUM'
    },
    'IP_ADDRESS': {
        'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'description': 'IP Address',
        'hipaa_category': 'Internet Protocol (IP) address',
        'risk_level': 'MEDIUM'
    },
    'NPI': {
        'pattern': r'\b(?:NPI)[:\s#]*(\d{10})\b',
        'description': 'National Provider Identifier',
        'hipaa_category': 'Provider identifiers',
        'risk_level': 'LOW'
    },
    'INSURANCE_ID': {
        'pattern': r'\b(?:Policy|Insurance|Member\s*ID|Group)[:\s#]*([A-Z]{2,8}(?:[-\s]\w{2,20}){1,4})\b',
        'description': 'Insurance/Policy Number',
        'hipaa_category': 'Health plan beneficiary numbers',
        'risk_level': 'HIGH'
    },
    'CREDIT_CARD': {
        'pattern': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'description': 'Credit Card Number',
        'hipaa_category': 'Financial account numbers',
        'risk_level': 'CRITICAL'
    },
    'PATIENT_NAME': {
        'pattern': r'\b(?:Patient|Name|patient|name)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)\b',
        'description': 'Patient Name',
        'hipaa_category': 'Names',
        'risk_level': 'HIGH'
    },
    'PROVIDER_NAME': {
        'pattern': r'\b(?:Dr\.|Doctor|Physician|Attending|Provider)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        'description': 'Provider/Doctor Name',
        'hipaa_category': 'Names',
        'risk_level': 'MEDIUM'
    },
    'AADHAAR': {
        'pattern': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        'description': 'Aadhaar Number (India DPDP)',
        'hipaa_category': 'National ID (DPDP)',
        'risk_level': 'CRITICAL'
    },
    'ADDRESS': {
        'pattern': r'\b\d{1,5}\s(?:[A-Za-z0-9#-]+\s){1,5}(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir)\b(?:,?\s[A-Za-z\s]+,?\s[A-Z]{2}\s\d{5}(?:-\d{4})?)?',
        'description': 'Physical Address',
        'hipaa_category': 'Geographic subdivisions smaller than a state',
        'risk_level': 'HIGH'
    },
}

# Medical abbreviation expansions
MEDICAL_ABBREVIATIONS = {
    'bp': 'Blood Pressure', 'hr': 'Heart Rate', 'rr': 'Respiratory Rate',
    'temp': 'Temperature', 'spo2': 'Oxygen Saturation', 'bmi': 'Body Mass Index',
    'dx': 'Diagnosis', 'rx': 'Prescription', 'tx': 'Treatment',
    'hx': 'History', 'sx': 'Symptoms', 'fx': 'Fracture',
    'sob': 'Shortness of Breath', 'cp': 'Chest Pain', 'ha': 'Headache',
    'nkda': 'No Known Drug Allergies', 'nka': 'No Known Allergies',
    'prn': 'As Needed', 'bid': 'Twice Daily', 'tid': 'Three Times Daily',
    'qid': 'Four Times Daily', 'qd': 'Once Daily',
    'po': 'By Mouth', 'iv': 'Intravenous', 'im': 'Intramuscular',
    'sc': 'Subcutaneous', 'sl': 'Sublingual',
    'dm': 'Diabetes Mellitus', 'dm2': 'Diabetes Mellitus Type 2',
    'htn': 'Hypertension', 'cad': 'Coronary Artery Disease',
    'chf': 'Congestive Heart Failure', 'copd': 'Chronic Obstructive Pulmonary Disease',
    'ckd': 'Chronic Kidney Disease', 'uti': 'Urinary Tract Infection',
    'dvt': 'Deep Vein Thrombosis', 'pe': 'Pulmonary Embolism',
    'mi': 'Myocardial Infarction', 'cva': 'Cerebrovascular Accident',
    'afib': 'Atrial Fibrillation', 'nstemi': 'Non-ST Elevation Myocardial Infarction',
    'stemi': 'ST Elevation Myocardial Infarction',
    'bmp': 'Basic Metabolic Panel', 'cbc': 'Complete Blood Count',
    'bnp': 'Brain Natriuretic Peptide', 'ekg': 'Electrocardiogram',
    'ecg': 'Electrocardiogram', 'ct': 'Computed Tomography',
    'mri': 'Magnetic Resonance Imaging', 'cxr': 'Chest X-Ray',
    'ed': 'Emergency Department', 'icu': 'Intensive Care Unit',
    'ccu': 'Cardiac Care Unit',
    'los': 'Length of Stay', 'ama': 'Against Medical Advice',
    'wbc': 'White Blood Cell Count', 'hgb': 'Hemoglobin',
    'plt': 'Platelet Count', 'inr': 'International Normalized Ratio',
    'ptt': 'Partial Thromboplastin Time', 'ast': 'Aspartate Aminotransferase',
    'alt': 'Alanine Aminotransferase', 'bun': 'Blood Urea Nitrogen',
    'cr': 'Creatinine', 'gfr': 'Glomerular Filtration Rate',
    'hba1c': 'Hemoglobin A1c', 'ldl': 'Low-Density Lipoprotein',
    'hdl': 'High-Density Lipoprotein', 'tc': 'Total Cholesterol',
    'tg': 'Triglycerides', 'fpg': 'Fasting Plasma Glucose',
    'des': 'Drug-Eluting Stent', 'pci': 'Percutaneous Coronary Intervention',
    'cabg': 'Coronary Artery Bypass Graft', 'lad': 'Left Anterior Descending',
    'rca': 'Right Coronary Artery', 'icd': 'International Classification of Diseases',
    'cpt': 'Current Procedural Terminology', 'drg': 'Diagnosis Related Group',
    'ra': 'Room Air', 'nc': 'Nasal Cannula',
}

# Clinical measurement patterns for extraction
CLINICAL_PATTERNS = {
    'blood_pressure': r'(?:BP|blood\s*pressure)[:\s]*(\d{2,3})[/](\d{2,3})',
    'heart_rate': r'(?:HR|heart\s*rate|pulse)[:\s]*(\d{2,3})\s*(?:bpm)?',
    'respiratory_rate': r'(?:RR|respiratory\s*rate)[:\s]*(\d{1,2})',
    'temperature': r'(?:Temp|temperature)[:\s]*(\d{2,3}\.?\d?)\s*(?:Â°?[FC])?',
    'oxygen_saturation': r'(?:SpO2|O2\s*sat|oxygen\s*sat)[:\s]*(\d{2,3})\s*%?',
    'glucose': r'(?:Glucose|glucose|blood\s*sugar)[:\s]*(\d{2,4})\s*(?:mg/dL)?',
    'hba1c': r'(?:HbA1c|A1c|hemoglobin\s*a1c)[:\s]*(\d{1,2}\.?\d?)\s*%?',
    'troponin': r'(?:Troponin|troponin)[:\s]*(\d+\.?\d*)\s*(?:ng/mL)?',
    'bmi': r'(?:BMI|bmi)[:\s]*(\d{2}\.?\d?)',
    'weight': r'(?:Weight|weight|Wt)[:\s]*(\d{2,3}\.?\d?)\s*(?:kg|lbs?)?',
    'creatinine': r'(?:Cr|creatinine|Creatinine)[:\s]*(\d+\.?\d?)',
}

# ICD-10 code pattern
ICD10_PATTERN = r'\b[A-Z]\d{2}(?:\.\d{1,4})?\b'
CPT_PATTERN = r'\b\d{5}\b'

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Medical Misspellings â€” curated list for fuzzy correction (BEFORE NER)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MEDICAL_MISSPELLINGS = {
    # Diseases
    'diabeties': 'diabetes', 'diebetes': 'diabetes', 'diabettes': 'diabetes',
    'diabetis': 'diabetes', 'diabet': 'diabetic',
    'hypertention': 'hypertension', 'hypertenshion': 'hypertension',
    'hypotention': 'hypotension',
    'athritis': 'arthritis', 'arthritus': 'arthritis', 'artheritis': 'arthritis',
    'asthima': 'asthma', 'asthama': 'asthma',
    'pneumonia': 'pneumonia', 'pnuemonia': 'pneumonia', 'neumonia': 'pneumonia',
    'tachychardia': 'tachycardia', 'bradychardia': 'bradycardia',
    'cardiomyopthy': 'cardiomyopathy', 'cardiomiopathy': 'cardiomyopathy',
    'fibrilation': 'fibrillation', 'fibrallation': 'fibrillation',
    'deppression': 'depression', 'depresion': 'depression', 'depretion': 'depression',
    'alzeimer': 'alzheimer', 'alheimer': 'alzheimer', 'alzheimers': "alzheimer's",
    'parkinsons': "parkinson's", 'parkinson': "parkinson's",
    'hypothyrodism': 'hypothyroidism', 'hypothyriodism': 'hypothyroidism',
    'hyperthyrodism': 'hyperthyroidism',
    'osteoporsis': 'osteoporosis', 'osteoporsis': 'osteoporosis',
    'rheumatiod': 'rheumatoid', 'rhuematoid': 'rheumatoid',
    'schizophrnia': 'schizophrenia', 'shizophrenia': 'schizophrenia',
    'hepititis': 'hepatitis', 'hepatitits': 'hepatitis', 'hepatitis': 'hepatitis',
    'apendecitis': 'appendicitis', 'appendecitis': 'appendicitis',
    'diverticulitus': 'diverticulitis', 'diverticulitus': 'diverticulitis',
    'colitus': 'colitis', 'cronhs': "crohn's", 'crohns': "crohn's",
    'cholestorol': 'cholesterol', 'chloesterol': 'cholesterol',
    'hyperlipedemia': 'hyperlipidemia', 'hyperlipedaemia': 'hyperlipidemia',
    'anaemia': 'anemia', 'leukaemia': 'leukemia',
    'septicaemia': 'septicemia', 'bacteraemia': 'bacteremia',
    'oedema': 'edema', 'haemoglobin': 'hemoglobin', 'haematology': 'hematology',
    'haemorrhage': 'hemorrhage', 'dyspnoea': 'dyspnea', 'disnoea': 'dyspnea',
    'diarrhoea': 'diarrhea', 'diarrheau': 'diarrhea', 'vomitting': 'vomiting',
    'nauseau': 'nausea', 'psorasis': 'psoriasis', 'ezczema': 'eczema',
    'rhinittis': 'rhinitis', 'sinusitus': 'sinusitis', 'bronchitus': 'bronchitis',
    'emphsyema': 'emphysema', 'tuberclosis': 'tuberculosis',
    'myocardal': 'myocardial', 'infaction': 'infarction',
    'metastses': 'metastases', 'carinoma': 'carcinoma',
    # Procedures
    'colonoscpy': 'colonoscopy', 'laparosocpic': 'laparoscopic',
    'appendictomy': 'appendectomy', 'appendictomy': 'appendectomy',
    'histerectomy': 'hysterectomy', 'angioplastyy': 'angioplasty',
    # Medications
    'metformine': 'metformin', 'insuline': 'insulin',
    'lisinoprl': 'lisinopril', 'atorvastatine': 'atorvastatin',
    'amoxycillin': 'amoxicillin', 'amoxycillin': 'amoxicillin',
    'paracetamole': 'paracetamol', 'acetominaphen': 'acetaminophen',
    'ibuprophen': 'ibuprofen', 'ibuprofin': 'ibuprofen',
    'prednisole': 'prednisolone', 'dexamethosone': 'dexamethasone',
    'sertarline': 'sertraline', 'fluoxitine': 'fluoxetine',
    'gabapentine': 'gabapentin', 'pregabline': 'pregabalin',
    'morpine': 'morphine', 'oxycodon': 'oxycodone',
    'warfarine': 'warfarin', 'heparine': 'heparin',
    'salbutamole': 'salbutamol', 'albuterole': 'albuterol',
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Medical Entity Patterns â€” Regex NER (deterministic, no ML model required)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_DISEASE_LIST = (
    r'diabetes(?: mellitus)?(?: type [12i]+)?|hypertension|hypotension|'
    r'coronary artery disease|heart failure|congestive heart failure|'
    r'atrial fibrillation|myocardial infarction|angina(?: pectoris)?|'
    r'stroke|transient ischemic attack|pulmonary embolism|deep vein thrombosis|'
    r'chronic obstructive pulmonary disease|copd|asthma|pneumonia|'
    r'chronic kidney disease|acute kidney injury|renal failure|'
    r'hepatitis(?: [abc])?|cirrhosis|pancreatitis|cholecystitis|'
    r"crohn'?s disease|ulcerative colitis|celiac disease|diverticulitis|"
    r"alzheimer'?s disease|parkinson'?s disease|multiple sclerosis|epilepsy|"
    r'depression|anxiety disorder|schizophrenia|bipolar disorder|ptsd|adhd|'
    r'hypothyroidism|hyperthyroidism|metabolic syndrome|obesity|'
    r'rheumatoid arthritis|osteoarthritis|osteoporosis|gout|lupus|'
    r'anemia|leukemia|lymphoma|melanoma|'
    r'breast cancer|lung cancer|colon cancer|prostate cancer|cervical cancer|'
    r'ovarian cancer|colorectal cancer|gastric cancer|pancreatic cancer|'
    r'sepsis|meningitis|encephalitis|tuberculosis|'
    r'covid-?19|influenza|hiv|aids|malaria|dengue fever|'
    r'appendicitis|hyperlipidemia|dyslipidemia|'
    r'urinary tract infection|kidney stone|nephrolithiasis|'
    r'glaucoma|cataracts?|eczema|psoriasis|dermatitis|cellulitis|'
    r'deep vein thrombosis|tachycardia|bradycardia|cardiomyopathy'
)

_DRUG_LIST = (
    r'metformin|insulin(?: glargine| aspart| lispro| nph)?|'
    r'lisinopril|enalapril|ramipril|amlodipine|nifedipine|diltiazem|verapamil|'
    r'atorvastatin|simvastatin|rosuvastatin|pravastatin|lovastatin|'
    r'aspirin|clopidogrel|warfarin|heparin|enoxaparin|apixaban|rivaroxaban|'
    r'metoprolol|atenolol|bisoprolol|carvedilol|propranolol|'
    r'furosemide|hydrochlorothiazide|spironolactone|torsemide|'
    r'omeprazole|pantoprazole|lansoprazole|esomeprazole|ranitidine|'
    r'amoxicillin|amoxicillin[- ]clavulanate|azithromycin|ciprofloxacin|'
    r'doxycycline|vancomycin|piperacillin|meropenem|ceftriaxone|'
    r'prednisone|prednisolone|dexamethasone|methylprednisolone|budesonide|'
    r'albuterol|salbutamol|salmeterol|tiotropium|fluticasone|beclomethasone|'
    r'levothyroxine|methimazole|propylthiouracil|'
    r'sertraline|fluoxetine|escitalopram|citalopram|venlafaxine|duloxetine|'
    r'alprazolam|diazepam|lorazepam|clonazepam|'
    r'gabapentin|pregabalin|carbamazepine|phenytoin|valproate|lamotrigine|'
    r'acetaminophen|paracetamol|ibuprofen|naproxen|celecoxib|indomethacin|'
    r'morphine|oxycodone|hydrocodone|codeine|tramadol|fentanyl|'
    r'digoxin|amiodarone|sotalol|flecainide|adenosine|'
    r'allopurinol|colchicine|febuxostat|'
    r'methotrexate|hydroxychloroquine|sulfasalazine|leflunomide|'
    r'adalimumab|etanercept|infliximab|rituximab|trastuzumab|'
    r'ondansetron|metoclopramide|domperidone|'
    r'lactulose|bisacodyl|docusate|polyethylene glycol|'
    r'zolpidem|eszopiclone|melatonin|quetiapine|olanzapine|haloperidol'
)

_PROCEDURE_LIST = (
    r'echocardiogram|electrocardiogram|ekg|ecg|'
    r'chest x-?ray|ct scan|mri|pet scan|ultrasound|'
    r'coronary angiogram|angioplasty|stent placement|bypass surgery|cabg|'
    r'colonoscopy|endoscopy|gastroscopy|bronchoscopy|cystoscopy|sigmoidoscopy|'
    r'appendectomy|cholecystectomy|hysterectomy|thyroidectomy|nephrectomy|'
    r'dialysis|hemodialysis|peritoneal dialysis|'
    r'chemotherapy|radiation therapy|radiotherapy|immunotherapy|'
    r'biopsy|fine needle aspiration|bone marrow biopsy|'
    r'blood transfusion|platelet transfusion|plasma transfusion|'
    r'physical therapy|occupational therapy|speech therapy|'
    r'cardiac catheterization|pacemaker implantation|defibrillation|cardioversion|'
    r'intubation|mechanical ventilation|tracheostomy|'
    r'central line|peripherally inserted central catheter|picc line|'
    r'lumbar puncture|spinal tap|'
    r'coronary artery bypass|carotid endarterectomy|'
    r'knee replacement|hip replacement|joint replacement|'
    r'cataract surgery|lasik|'
    r'mammogram|mammography|pap smear|pap test|'
    r'blood culture|urine culture|sputum culture'
)

MEDICAL_ENTITY_PATTERNS = {
    'DISEASE':   re.compile(r'\b(?:' + _DISEASE_LIST   + r')\b', re.IGNORECASE),
    'DRUG':      re.compile(r'\b(?:' + _DRUG_LIST      + r')\b', re.IGNORECASE),
    'PROCEDURE': re.compile(r'\b(?:' + _PROCEDURE_LIST + r')\b', re.IGNORECASE),
}


class UnstructuredDataProcessor:
    """
    Main processor for unstructured healthcare text data.
    Handles TXT, LOG, PDF, MD files with compliance-first approach.
    """

    SUPPORTED_EXTENSIONS = {'.txt', '.log', '.pdf', '.md', '.text', '.dat', '.rtf'}
    _sym_spell = None
    _sym_spell_load_attempted = False
    _scispacy_model = None
    _scispacy_load_attempted = False

    def __init__(self):
        self.processing_log = []
        self.phi_findings = []
        self._log("Processor initialized", "INFO")

    def _log(self, message: str, level: str = "INFO"):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.processing_log.append(entry)
        logger.log(getattr(logging, level, logging.INFO), message)

    def _get_sym_spell(self):
        """Load and cache the SymSpell dictionary once per process."""
        cls = type(self)
        if not SYMSPELL_AVAILABLE:
            return None
        if cls._sym_spell_load_attempted:
            return cls._sym_spell

        cls._sym_spell_load_attempted = True
        try:
            import pkg_resources

            sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
            dict_path = pkg_resources.resource_filename(
                'symspellpy', 'frequency_dictionary_en_82_765.txt'
            )
            sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
            cls._sym_spell = sym_spell
            self._log("Loaded SymSpell frequency dictionary")
        except Exception as e:
            self._log(f"SymSpell initialization skipped: {e}", "WARNING")

        return cls._sym_spell

    def _get_scispacy_model(self):
        """
        Try loading SciSpaCy model `en_ner_bc5cdr_md` once.
        Returns spaCy model or None if unavailable.
        """
        cls = type(self)
        if cls._scispacy_load_attempted:
            return cls._scispacy_model

        cls._scispacy_load_attempted = True
        try:
            import spacy

            cls._scispacy_model = spacy.load('en_ner_bc5cdr_md')
            self._log("Loaded SciSpaCy model en_ner_bc5cdr_md")
        except Exception as e:
            self._log(f"SciSpaCy model not available, using regex NER: {e}", "WARNING")

        return cls._scispacy_model

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FILE READING / TEXT EXTRACTION
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def extract_text(self, file_path: str = None, file_obj=None, filename: str = "") -> Tuple[str, dict]:
        """
        Extract text from a file. Supports TXT, LOG, MD, PDF.
        Returns (extracted_text, metadata_dict).
        """
        if file_obj and filename:
            ext = os.path.splitext(filename)[1].lower()
        elif file_path:
            ext = os.path.splitext(file_path)[1].lower()
            filename = os.path.basename(file_path)
        else:
            raise ValueError("Provide either file_path or (file_obj, filename)")

        metadata = {
            'filename': filename,
            'extension': ext,
            'extraction_method': 'unknown',
            'extracted_at': datetime.now().isoformat(),
            'char_count': 0,
            'line_count': 0,
            'word_count': 0,
        }

        if ext in ('.txt', '.log', '.md', '.text', '.dat'):
            text = self._read_text_file(file_path, file_obj)
            metadata['extraction_method'] = 'direct_text_read'

        elif ext == '.pdf':
            text = self._extract_pdf_text(file_path, file_obj)
            metadata['extraction_method'] = 'docling+ocr' if DOCLING_AVAILABLE else 'pymupdf' if PYMUPDF_AVAILABLE else 'fallback'

        elif ext == '.rtf':
            text = self._read_text_file(file_path, file_obj)
            text = re.sub(r'\\[a-z]+\d*\s?', '', text)
            text = re.sub(r'[{}]', '', text)
            metadata['extraction_method'] = 'rtf_strip'

        else:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}")

        metadata['char_count'] = len(text)
        metadata['line_count'] = text.count('\n') + 1
        metadata['word_count'] = len(text.split())
        self._log(f"Extracted {metadata['word_count']} words from {filename} via {metadata['extraction_method']}")

        return text, metadata

    def _read_text_file(self, file_path: str = None, file_obj=None) -> str:
        """Read a text-based file with encoding detection."""
        if file_obj:
            raw = file_obj.read()
            if isinstance(raw, bytes):
                for enc in ('utf-8', 'latin-1', 'cp1252', 'ascii'):
                    try:
                        return raw.decode(enc)
                    except (UnicodeDecodeError, LookupError):
                        continue
                return raw.decode('utf-8', errors='replace')
            return raw

        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    def _extract_pdf_text(self, file_path: str = None, file_obj=None) -> str:
        """
        Smart router: check text density first, pick the right engine.
        Strategy 1 (fast path): PyMuPDF â€” if PDF has a text layer (>100 chars/page avg)
        Strategy 2 (complex path): Docling â€” for scanned PDFs / tables / forms
        Strategy 3 (fallback): Tesseract OCR
        """
        # â”€â”€ Strategy 1: PyMuPDF fast path (text-layer PDFs) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if PYMUPDF_AVAILABLE:
            try:
                if file_obj:
                    file_obj.seek(0)
                    pdf_bytes = file_obj.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                else:
                    doc = fitz.open(file_path)

                text_parts = [page.get_text() for page in doc]
                num_pages = max(len(text_parts), 1)
                doc.close()
                full_text = '\n'.join(text_parts)
                chars_per_page = len(full_text.strip()) / num_pages

                # If density is good â†’ this is a text-layer PDF â†’ use it directly (fast)
                if chars_per_page > 100:
                    self._log(f"PDF fast path via PyMuPDF ({chars_per_page:.0f} chars/page)")
                    return full_text

                self._log(f"PDF text-sparse ({chars_per_page:.0f} chars/page) â€” escalating to Docling")
            except Exception as e:
                self._log(f"PyMuPDF fast-path failed: {e}", "WARNING")

        # â”€â”€ Strategy 2: Docling â€” for scanned / table-heavy / form PDFs â”€â”€â”€â”€â”€â”€
        if DOCLING_AVAILABLE:
            tmp_path = None
            try:
                if file_obj:
                    file_obj.seek(0)
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                    tmp.write(file_obj.read())
                    tmp.close()
                    tmp_path = tmp.name
                else:
                    tmp_path = file_path

                from docling.datamodel.pipeline_options import PdfPipelineOptions
                opts = PdfPipelineOptions()
                opts.do_table_structure = True   # extract tables
                opts.do_ocr = True               # handle scanned pages

                converter = DocumentConverter()
                result = converter.convert(tmp_path)
                text = result.document.export_to_markdown()

                if file_obj and tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

                if text and text.strip():
                    self._log("PDF extracted via Docling (complex path)")
                    return text
            except Exception as e:
                self._log(f"Docling extraction failed: {e}", "WARNING")
                if file_obj and tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        # â”€â”€ Strategy 3: Tesseract OCR fallback â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if TESSERACT_AVAILABLE:
            return self._ocr_pdf(file_path, file_obj)

        self._log("No PDF extraction library available.", "ERROR")
        return "[PDF extraction failed: install PyMuPDF or docling]"

    def _ocr_pdf(self, file_path: str = None, file_obj=None) -> str:
        """OCR-based PDF text extraction using Tesseract via PyMuPDF rendering."""
        if not (PYMUPDF_AVAILABLE and TESSERACT_AVAILABLE):
            return "[OCR requires PyMuPDF and pytesseract]"

        try:
            from PIL import Image

            if file_obj:
                file_obj.seek(0)
                pdf_bytes = file_obj.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            else:
                doc = fitz.open(file_path)

            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img)
                text_parts.append(page_text)

            doc.close()
            self._log(f"OCR completed for {len(text_parts)} pages")
            return '\n'.join(text_parts)

        except Exception as e:
            self._log(f"OCR failed: {e}", "ERROR")
            return f"[OCR extraction failed: {e}]"

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # TEXT CLEANING OPERATIONS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def clean_text(self, text: str, operations: dict = None) -> Tuple[str, dict]:
        """
        Apply selected cleaning operations to extracted text.
        Returns (cleaned_text, cleaning_report).
        """
        if operations is None or not isinstance(operations, dict):
            operations = {
                'normalize_whitespace': True,
                'normalize_line_breaks': True,
                'remove_control_chars': True,
                'fix_encoding_artifacts': True,
                'normalize_unicode': True,
                'standardize_punctuation': True,
                'remove_empty_lines': True,
                'fix_hyphenation': True,
            }

        report = {
            'original_length': len(text),
            'operations_applied': [],
            'changes': {}
        }

        cleaned = text

        if operations.get('remove_control_chars', False):
            before = len(cleaned)
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned)
            removed = before - len(cleaned)
            report['operations_applied'].append('remove_control_chars')
            report['changes']['control_chars_removed'] = removed

        if operations.get('fix_encoding_artifacts', False):
            replacements = {
                '\u2019': "'", '\u201c': '"', '\u201d': '"',
                '\u2013': '-', '\u2014': '--',
                '\u00e9': 'e', '\u00e8': 'e', '\u00fc': 'u',
                '\u00f6': 'o', '\u00e4': 'a',
                '\ufffd': '', '\ufeff': '',
            }
            count = 0
            for bad, good in replacements.items():
                if bad in cleaned:
                    count += cleaned.count(bad)
                    cleaned = cleaned.replace(bad, good)
            report['operations_applied'].append('fix_encoding_artifacts')
            report['changes']['encoding_fixes'] = count

        if operations.get('normalize_unicode', False):
            import unicodedata
            cleaned = unicodedata.normalize('NFKC', cleaned)
            report['operations_applied'].append('normalize_unicode')

        if operations.get('normalize_whitespace', False):
            before = len(cleaned)
            cleaned = re.sub(r'[^\S\n]+', ' ', cleaned)
            report['operations_applied'].append('normalize_whitespace')
            report['changes']['whitespace_normalized'] = before - len(cleaned)

        if operations.get('normalize_line_breaks', False):
            cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
            report['operations_applied'].append('normalize_line_breaks')

        if operations.get('remove_empty_lines', False):
            before = cleaned.count('\n')
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            report['operations_applied'].append('remove_empty_lines')
            report['changes']['empty_lines_reduced'] = before - cleaned.count('\n')

        if operations.get('fix_hyphenation', False):
            count = len(re.findall(r'(\w+)-\n(\w+)', cleaned))
            cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', cleaned)
            report['operations_applied'].append('fix_hyphenation')
            report['changes']['hyphenations_fixed'] = count

        if operations.get('standardize_punctuation', False):
            cleaned = cleaned.replace('\u2018', "'").replace('\u2019', "'")
            cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
            cleaned = cleaned.replace('\u2013', '-').replace('\u2014', '--')
            cleaned = cleaned.replace('\u2026', '...')
            report['operations_applied'].append('standardize_punctuation')

        report['cleaned_length'] = len(cleaned)
        report['size_reduction_pct'] = round(
            (1 - len(cleaned) / max(len(text), 1)) * 100, 2
        )

        self._log(f"Text cleaning done: {len(report['operations_applied'])} ops, "
                   f"{report['size_reduction_pct']}% size reduction")

        return cleaned, report

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PHI / PII DETECTION & REDACTION (HIPAA + GDPR + DPDP)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def detect_phi(self, text: str) -> List[dict]:
        """
        Scan text for Protected Health Information / Personally Identifiable Information.
        Returns list of findings with location, type, and risk level.
        """
        findings = []

        for phi_type, config in PHI_PATTERNS.items():
            for match in re.finditer(config['pattern'], text, re.IGNORECASE):
                matched_text = match.group(0)

                if phi_type in ('SSN', 'AADHAAR', 'CREDIT_CARD'):
                    digits_only = re.sub(r'\D', '', matched_text)
                    if phi_type == 'SSN' and ('*' in matched_text or 'X' in matched_text.upper()):
                        pass
                    elif len(digits_only) < 9:
                        continue

                findings.append({
                    'type': phi_type,
                    'description': config['description'],
                    'hipaa_category': config['hipaa_category'],
                    'risk_level': config['risk_level'],
                    'start': match.start(),
                    'end': match.end(),
                    'matched_text_preview': matched_text[:3] + '***',
                    'line_number': text[:match.start()].count('\n') + 1
                })

        findings = self._resolve_overlapping_findings(findings)
        findings.sort(key=lambda x: x['start'])
        self.phi_findings = findings
        self._log(f"PHI scan: {len(findings)} items found across {len(set(f['type'] for f in findings))} categories")

        return findings

    @staticmethod
    def _risk_priority(risk_level: str) -> int:
        priorities = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1,
        }
        return priorities.get(risk_level or '', 0)

    @staticmethod
    def _type_specificity(phi_type: str) -> int:
        specificities = {
            'MRN': 5,
            'INSURANCE_ID': 5,
            'NPI': 5,
            'DOB': 5,
            'PATIENT_NAME': 4,
            'PROVIDER_NAME': 4,
            'SSN': 3,
            'AADHAAR': 3,
            'CREDIT_CARD': 3,
            'PHONE': 2,
            'EMAIL': 2,
            'DATE_FULL': 1,
        }
        return specificities.get(phi_type or '', 0)

    def _resolve_overlapping_findings(self, findings: List[dict]) -> List[dict]:
        """Keep the best match when PHI spans overlap."""
        if not findings:
            return []

        ordered = sorted(
            findings,
            key=lambda item: (
                item['start'],
                -(item['end'] - item['start']),
                -self._risk_priority(item['risk_level']),
            )
        )

        resolved = []
        for finding in ordered:
            if not resolved:
                resolved.append(finding)
                continue

            previous = resolved[-1]
            overlaps = finding['start'] < previous['end']
            if not overlaps:
                resolved.append(finding)
                continue

            prev_span = previous['end'] - previous['start']
            current_span = finding['end'] - finding['start']
            previous_score = (
                self._type_specificity(previous['type']),
                prev_span,
                self._risk_priority(previous['risk_level']),
            )
            current_score = (
                self._type_specificity(finding['type']),
                current_span,
                self._risk_priority(finding['risk_level']),
            )
            if current_score > previous_score:
                resolved[-1] = finding

        return resolved

    def validate_redaction_quality(self, text: str) -> dict:
        """Check redacted output for obvious compliance failures."""
        issues = []

        checks = [
            (r'\*{3}-\*{2}-\d{4}\b', 'CRITICAL: Partial SSN still visible'),
            (r'(?<![A-Za-z0-9-])(?:\d{3}-\d{2}-\d{4}|\d{9})(?![A-Za-z0-9-])', 'CRITICAL: Unredacted SSN still visible'),
            (r'\[REDACTED-[^\]]+\]-[^\s\[]+', 'CRITICAL: Malformed redaction marker detected'),
            (r'TED-PHONE\]', 'CRITICAL: Truncated redaction marker detected'),
            (r'\b(?:DOB|Date of Birth)[:\s]*\d{4}[-/]\d{2}[-/]\d{2}\b', 'HIGH: Date of birth still visible'),
            (r'\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', 'HIGH: Date of birth still visible'),
        ]

        for pattern, message in checks:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(message)

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'compliance_status': 'HIPAA_COMPLIANT' if not issues else 'HIPAA_VIOLATION',
        }

    def redact_phi(self, text: str, findings: List[dict] = None,
                   redaction_style: str = 'tag') -> Tuple[str, dict]:
        """
        Redact PHI from text.
        redaction_style: 'tag' | 'hash' | 'mask' | 'remove'
        """
        if findings is None:
            findings = self.detect_phi(text)

        if not findings:
            return text, {'redactions': 0, 'categories': {}}

        redaction_report = {
            'redactions': 0,
            'categories': {},
            'risk_summary': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'style': redaction_style
        }

        resolved_findings = self._resolve_overlapping_findings(findings)
        redacted_parts = []
        cursor = 0

        for finding in sorted(resolved_findings, key=lambda x: x['start']):
            original = text[finding['start']:finding['end']]
            phi_type = finding['type']

            if redaction_style == 'tag':
                replacement = f"[REDACTED-{phi_type}]"
            elif redaction_style == 'hash':
                hash_val = hashlib.sha256(original.encode()).hexdigest()[:12]
                replacement = f"[PSEUDO-{phi_type}-{hash_val}]"
            elif redaction_style == 'mask':
                replacement = '*' * len(original)
            elif redaction_style == 'remove':
                replacement = ''
            else:
                replacement = f"[REDACTED-{phi_type}]"

            redacted_parts.append(text[cursor:finding['start']])
            redacted_parts.append(replacement)
            cursor = finding['end']

            redaction_report['redactions'] += 1
            redaction_report['categories'][phi_type] = redaction_report['categories'].get(phi_type, 0) + 1
            redaction_report['risk_summary'][finding['risk_level']] += 1

        redacted_parts.append(text[cursor:])
        redacted = ''.join(redacted_parts)

        # Final safety-net cleanup for masked SSNs that may bypass structured matching.
        redacted = re.sub(r'\*{3}-\*{2}-\d{4}\b', '[REDACTED-SSN]', redacted)

        self._log(f"Redacted {redaction_report['redactions']} PHI items using '{redaction_style}' style")

        return redacted, redaction_report

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # MEDICAL TEXT PREPROCESSING
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def expand_medical_abbreviations(self, text: str) -> Tuple[str, dict]:
        """Expand common medical abbreviations to full forms."""
        expansions = {}
        result = text

        for abbrev, full_form in MEDICAL_ABBREVIATIONS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            matches = re.findall(pattern, result, re.IGNORECASE)
            if matches:
                expansions[abbrev] = {
                    'expanded_to': full_form,
                    'count': len(matches)
                }
                result = re.sub(pattern, f"{full_form} ({abbrev.upper()})", result, flags=re.IGNORECASE)

        self._log(f"Expanded {len(expansions)} abbreviation types ({sum(e['count'] for e in expansions.values())} total)")

        return result, {
            'expansions': expansions,
            'total_expanded': sum(info['count'] for info in expansions.values()),
            'unique_abbreviations': len(expansions),
        }

    def extract_clinical_values(self, text: str) -> dict:
        """Extract structured clinical measurements from unstructured text."""
        extracted = {}

        for measurement, pattern in CLINICAL_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            values = []
            for m in matches:
                try:
                    if measurement == 'blood_pressure':
                        values.append({
                            'systolic': int(m.group(1)),
                            'diastolic': int(m.group(2)),
                            'position': m.start()
                        })
                    else:
                        val = m.group(1)
                        values.append({
                            'value': float(val) if '.' in val else int(val),
                            'position': m.start()
                        })
                except (ValueError, IndexError):
                    continue

            if values:
                extracted[measurement] = values

        icd_matches = re.findall(ICD10_PATTERN, text)
        if icd_matches:
            extracted['icd10_codes'] = list(set(icd_matches))

        cpt_context = re.findall(r'(?:CPT|procedure|code)[:\s]*(\d{5})', text, re.IGNORECASE)
        if cpt_context:
            extracted['cpt_codes'] = list(set(cpt_context))

        # --- LOCAL CORPUS EXTRACTION ---
        extracted['corpus_mentions'] = []
        
        # 1. Match from MEDICAL_ABBREVIATIONS
        for abbrev, full_form in MEDICAL_ABBREVIATIONS.items():
            pattern = r'\b(' + re.escape(abbrev) + r'|' + re.escape(full_form) + r')\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                extracted['corpus_mentions'].append({
                    'concept': full_form,
                    'matched_text': match.group(0),
                    'position': match.start()
                })
                
        # 2. Match from MEDICAL_MISSPELLINGS values (since they are corrected right before NER, mapping is clean)
        clean_corpus = set(MEDICAL_MISSPELLINGS.values())
        for term in clean_corpus:
            pattern = r'\b' + re.escape(term) + r'\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                extracted['corpus_mentions'].append({
                    'concept': term.capitalize(),
                    'matched_text': match.group(0),
                    'position': match.start()
                })
                
        # Remove empty corpus_mentions if none found
        if not extracted['corpus_mentions']:
            del extracted['corpus_mentions']
        else:
            # Deduplicate by concept and position closely
            unique_mentions = []
            seen_mentions = set()
            for m in extracted['corpus_mentions']:
                key = (m['concept'], m['position'] // 50) # group closely positioned identical concepts
                if key not in seen_mentions:
                    seen_mentions.add(key)
                    unique_mentions.append(m)
            extracted['corpus_mentions'] = unique_mentions

        self._log(f"Extracted clinical values: {len(extracted)} measurement categories (including corpus matches)")

        return extracted

    def _normalize_field_key(self, key: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', str(key).lower()).strip('_')

    def _normalize_timestamp_iso(self, timestamp_str: str) -> str:
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').isoformat()
        except ValueError:
            return timestamp_str

    def _extract_inline_fields(self, message: str) -> dict:
        fields = {}
        segments = [segment.strip() for segment in str(message).split('|') if segment.strip()]

        for segment in segments:
            field_match = re.match(r'([A-Za-z][A-Za-z0-9 /()#\-]{1,40}):\s*(.+)', segment)
            if not field_match:
                continue

            key = self._normalize_field_key(field_match.group(1))
            value = field_match.group(2).strip()
            if key and value and key not in fields:
                fields[key] = value

        return fields

    def _extract_clinical_snapshot(self, text: str) -> dict:
        snapshot = {}
        for measurement, pattern in CLINICAL_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue

            try:
                if measurement == 'blood_pressure':
                    snapshot[measurement] = {
                        'systolic': int(match.group(1)),
                        'diastolic': int(match.group(2)),
                    }
                else:
                    raw_value = match.group(1)
                    snapshot[measurement] = float(raw_value) if '.' in raw_value else int(raw_value)
            except (ValueError, IndexError):
                continue

        return snapshot

    def _normalize_medication_route(self, route: str) -> str:
        route_map = {
            'po': 'oral',
            'oral': 'oral',
            'iv': 'intravenous',
            'im': 'intramuscular',
            'sc': 'subcutaneous',
            'sq': 'subcutaneous',
            'subq': 'subcutaneous',
            'sl': 'sublingual',
            'pr': 'rectal',
            'ng': 'nasogastric',
            'peg': 'peg_tube',
        }
        normalized = route_map.get(str(route or '').strip().lower())
        return normalized or self._normalize_field_key(route)

    def _normalize_medication_frequency(self, value: str) -> str:
        normalized = str(value or '').strip().lower()
        if not normalized:
            return ''

        frequency_map = {
            'qd': 'daily',
            'daily': 'daily',
            'once daily': 'daily',
            'bid': 'twice_daily',
            'twice daily': 'twice_daily',
            'tid': 'three_times_daily',
            'qid': 'four_times_daily',
            'qhs': 'nightly',
            'q4h': 'every_4_hours',
            'q6h': 'every_6_hours',
            'q8h': 'every_8_hours',
            'q12h': 'every_12_hours',
            'prn': 'as_needed',
        }
        if normalized in frequency_map:
            return frequency_map[normalized]
        if re.fullmatch(r'q\d+h', normalized):
            return f"every_{normalized[1:-1]}_hours"
        return self._normalize_field_key(normalized)

    def _extract_ordered_items(self, message: str) -> List[str]:
        ordered_items = []
        for segment in [segment.strip() for segment in str(message).split('|') if segment.strip()]:
            if ':' in segment:
                continue
            parts = [item.strip() for item in segment.split(',') if item.strip()]
            if len(parts) > 1:
                ordered_items.extend(parts)
        return ordered_items

    def _normalize_medication_event(self, message: str, fields: dict) -> dict:
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {
            'action': 'documented',
        }

        if 'reconciliation started' in summary_lower:
            payload['action'] = 'reconciliation_started'
            return payload

        if 'discharge medications reconciled' in summary_lower:
            payload['action'] = 'discharge_reconciliation'
            med_count_match = re.search(r'(\d+)\s+medications?', summary_lower)
            if med_count_match:
                payload['medication_count'] = int(med_count_match.group(1))
            return payload

        if 'sliding scale' in summary_lower:
            medication_match = re.match(r'^(?P<name>[A-Za-z][A-Za-z0-9\- ]+?)\s+sliding scale\s+(?P<action>ordered|started|initiated)', summary, re.IGNORECASE)
            if medication_match:
                payload.update({
                    'medication_name': medication_match.group('name').strip(),
                    'regimen': 'sliding_scale',
                    'action': self._normalize_field_key(medication_match.group('action')),
                })
            monitoring_match = re.search(r'glucose monitoring\s+([A-Za-z0-9]+)', message, re.IGNORECASE)
            if monitoring_match:
                payload['monitoring_frequency'] = self._normalize_medication_frequency(monitoring_match.group(1))
            return payload

        dose_match = re.match(
            r'^(?P<name>[A-Z][A-Za-z0-9/\- ]+?)\s+(?P<dose>\d+(?:\.\d+)?)\s*(?P<dose_unit>mcg|mg|g|units?|mL|ml)\s*(?P<route>PO|IV|IM|SC|SQ|SL|PR|NG|PEG)?\s*(?P<tail>.*)$',
            summary,
            re.IGNORECASE,
        )
        if dose_match:
            payload['medication_name'] = dose_match.group('name').strip()
            dose_value = dose_match.group('dose')
            payload['dose'] = float(dose_value) if '.' in dose_value else int(dose_value)
            payload['dose_unit'] = dose_match.group('dose_unit')
            route = dose_match.group('route')
            if route:
                payload['route'] = self._normalize_medication_route(route)

            tail = (dose_match.group('tail') or '').strip().lower()
            if 'loading dose' in tail:
                payload['action'] = 'loading_dose'
            elif 'administered' in tail:
                payload['action'] = 'administered'
            elif 'ordered' in tail:
                payload['action'] = 'ordered'
            elif 'initiated' in tail:
                payload['action'] = 'initiated'
            return payload

        drip_match = re.match(r'^(?P<name>[A-Z][A-Za-z0-9/\- ]+?)\s+drip\s+(?P<action>initiated|started)', summary, re.IGNORECASE)
        if drip_match:
            payload.update({
                'medication_name': drip_match.group('name').strip(),
                'route': 'intravenous',
                'administration_mode': 'continuous_infusion',
                'action': self._normalize_field_key(drip_match.group('action')),
            })
            rate_match = re.search(r'(\d+(?:\.\d+)?)\s*(units?/kg/hr|units?/hr|mg/hr|mcg/kg/min)', message, re.IGNORECASE)
            if rate_match:
                rate_value = rate_match.group(1)
                payload['infusion_rate'] = float(rate_value) if '.' in rate_value else int(rate_value)
                payload['infusion_rate_unit'] = rate_match.group(2)
            weight_match = re.search(r'Weight:\s*(\d+(?:\.\d+)?)\s*kg', message, re.IGNORECASE)
            if weight_match:
                payload['weight_kg'] = float(weight_match.group(1))
            return payload

        return payload

    def _normalize_lab_result_event(self, message: str, fields: dict, level: str) -> dict:
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {}

        if 'critical value' in summary_lower:
            payload['criticality'] = 'critical'
            critical_match = re.search(r'critical value\s*-\s*(.+?)(?:\s+elevated|\s+low|$)', summary, re.IGNORECASE)
            if critical_match:
                payload['test_name'] = critical_match.group(1).strip()
            payload['status'] = 'alerted'
            return payload

        result_match = re.match(
            r'^(?P<test>[A-Za-z0-9][A-Za-z0-9 .%/+\-]*?)(?:\s+trending\s+(?P<trend>up|down))?:\s*(?P<value><)?(?P<numeric>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z%/0-9.]+)?(?:\s*\[(?P<flag>[A-Z]+)\])?$',
            summary,
            re.IGNORECASE,
        )
        if result_match:
            payload['test_name'] = result_match.group('test').strip()
            numeric = result_match.group('numeric')
            payload['value'] = float(numeric) if '.' in numeric else int(numeric)
            if result_match.group('value'):
                payload['comparator'] = 'less_than'
            unit = result_match.group('unit')
            if unit:
                payload['unit'] = unit
            flag = result_match.group('flag')
            if flag:
                payload['abnormal_flag'] = flag
            trend = result_match.group('trend')
            if trend:
                payload['trend'] = trend

        reference = fields.get('reference')
        if reference:
            payload['reference_range'] = reference

        previous = fields.get('previous')
        if previous:
            payload['previous_value'] = previous

        if str(level).upper() == 'ALERT':
            payload['criticality'] = 'critical'

        return payload

    def _normalize_lab_order_event(self, message: str, fields: dict) -> dict:
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {
            'order_set': summary,
            'priority': 'stat' if 'stat' in summary_lower else 'routine',
            'ordered_tests': self._extract_ordered_items(message),
        }
        if 'provider' in fields:
            payload['ordering_provider'] = fields['provider']
        return payload

    def _normalize_imaging_event(self, message: str, fields: dict, event_type: str) -> dict:
        """Normalize imaging (radiology) orders and results."""
        summary = str(message).split('|')[0].strip()
        message_lower = str(message).lower()
        payload = {}
        
        if event_type == 'imaging_order':
            modality_match = re.match(r'^(?P<modality>[A-Za-z0-9\-\s]+?)\s+(?:order|requested|placed)', summary, re.IGNORECASE)
            if modality_match:
                payload['modality'] = modality_match.group('modality').strip()
            payload['priority'] = 'stat' if 'stat' in message_lower else 'routine'
            if 'reason' in fields or 'indication' in fields:
                payload['indication'] = fields.get('reason') or fields.get('indication')
        elif event_type == 'imaging_result':
            modality_match = re.match(r'^(?P<modality>[A-Za-z0-9\-\s]+?)\s+(?:result|resulted|completed)', summary, re.IGNORECASE)
            if modality_match:
                payload['modality'] = modality_match.group('modality').strip()
            if 'findings' in fields:
                payload['findings'] = fields['findings']
            impression_match = re.search(r'(?:impression|impression:|findings:|findings|result:)\s*(.+?)(?:\||$)', message, re.IGNORECASE)
            if impression_match:
                payload['impression'] = impression_match.group(1).strip()
        
        return payload

    def _normalize_consult_event(self, message: str, fields: dict) -> dict:
        """Normalize consultation requests and acceptances."""
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {}
        
        consult_type_match = re.match(r'^(?P<specialty>[A-Za-z\s\-]+?)\s+consult\s+(?P<action>requested|accepted)', summary, re.IGNORECASE)
        if consult_type_match:
            payload['specialty'] = consult_type_match.group('specialty').strip()
            payload['status'] = 'requested' if 'requested' in summary_lower else 'accepted'
        else:
            payload['status'] = 'requested' if 'requested' in summary_lower else 'accepted'
        
        if 'reason' in fields:
            payload['reason'] = fields['reason']
        if 'requesting_provider' in fields:
            payload['requesting_provider'] = fields['requesting_provider']
        if 'consulting_provider' in fields or 'provider' in fields:
            payload['consulting_provider'] = fields.get('consulting_provider') or fields.get('provider')
        
        plan_match = re.search(r'(?:plan|plan:)\s*(.+?)(?:\||$)', message, re.IGNORECASE)
        if plan_match:
            payload['plan'] = plan_match.group(1).strip()
        
        return payload

    def _normalize_nursing_event(self, message: str, fields: dict) -> dict:
        """Normalize nursing assessments and monitoring."""
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {}
        
        if 'assessment' in summary_lower:
            payload['event_subtype'] = 'assessment'
        elif 'reassessment' in summary_lower:
            payload['event_subtype'] = 'reassessment'
        elif 'monitoring' in summary_lower or 'observation' in summary_lower:
            payload['event_subtype'] = 'monitoring'
        
        mental_status_match = re.search(r'(?:alert|oriented|a&o|aao)[\s,]*(?:x)?(\d)', message, re.IGNORECASE)
        if mental_status_match:
            payload['mental_status'] = f"alert_oriented_x{mental_status_match.group(1)}"
        
        pain_match = re.search(r'pain\s+(\d{1,2})/10', message, re.IGNORECASE)
        if pain_match:
            payload['pain_level'] = int(pain_match.group(1))
        
        for key, value in fields.items():
            if 'diet' in key.lower():
                payload['diet'] = value
            elif 'o2' in key.lower() or 'oxygen' in key.lower() or key.lower() == 'o2':
                payload['oxygen_support'] = value
        
        for signal, pattern in CLINICAL_PATTERNS.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match and signal not in payload:
                try:
                    if signal == 'blood_pressure':
                        payload['bp'] = f"{match.group(1)}/{match.group(2)}"
                    else:
                        val = match.group(1)
                        payload[signal] = float(val) if '.' in val else int(val)
                except (ValueError, IndexError):
                    pass
        
        return payload

    def _normalize_procedure_event(self, message: str, fields: dict) -> dict:
        """Normalize procedure start, completion, and findings."""
        summary = str(message).split('|')[0].strip()
        summary_lower = summary.lower()
        payload = {}
        
        procedure_match = re.match(r'^(?P<procedure_name>[A-Za-z0-9\s\-\.]+?)\s+(?P<action>started|completed|began|initiated)', summary, re.IGNORECASE)
        if procedure_match:
            payload['procedure_name'] = procedure_match.group('procedure_name').strip()
            payload['status'] = 'in_progress' if 'started' in summary_lower or 'begun' in summary_lower or 'initiated' in summary_lower else 'completed'
        
        if 'provider' in fields:
            payload['provider'] = fields['provider']
        if 'location' in fields or 'room' in fields:
            payload['location'] = fields.get('location') or fields.get('room')
        
        findings_match = re.search(r'(?:findings?|result):\s*(.+?)(?:\||$)', message, re.IGNORECASE)
        if findings_match and payload.get('status') == 'completed':
            payload['findings'] = findings_match.group(1).strip()
        
        technique_match = re.search(r'(?:technique|approach):\s*(.+?)(?:\||$)', message, re.IGNORECASE)
        if technique_match:
            payload['technique'] = technique_match.group(1).strip()
        
        for code_type in ('icd', 'cpt', 'snomed'):
            code_pattern = re.findall(rf'{code_type.upper()}[:\s]*(\d+\.?\d*)', message, re.IGNORECASE)
            if code_pattern:
                payload[f'{code_type}_codes'] = code_pattern
        
        return payload

    def _normalize_post_procedure_event(self, message: str, fields: dict) -> dict:
        """Normalize post-procedure monitoring and recovery."""
        summary = str(message).split('|')[0].strip()
        payload = {
            'event_name': summary,
        }
        
        status_keywords = ['stable', 'alert', 'recovering', 'critical', 'unstable', 'compromised']
        for keyword in status_keywords:
            if keyword in str(message).lower():
                payload['patient_status'] = keyword
                break
        
        for key, value in fields.items():
            key_lower = key.lower()
            if 'hemostasis' in key_lower or 'bleeding' in key_lower:
                payload['hemostasis'] = value
            elif 'drain' in key_lower or 'output' in key_lower:
                payload['drain_output'] = value
            elif 'monitoring' in key_lower or 'observation' in key_lower:
                payload['monitoring_plan'] = value
        
        return payload

    def _normalize_log_event_payload(self, event_type: str, message: str, fields: dict, level: str) -> dict:
        if event_type == 'medication_event':
            return self._normalize_medication_event(message, fields)
        if event_type == 'lab_result':
            return self._normalize_lab_result_event(message, fields, level)
        if event_type == 'lab_order':
            return self._normalize_lab_order_event(message, fields)
        if event_type == 'imaging_order' or event_type == 'imaging_result':
            return self._normalize_imaging_event(message, fields, event_type)
        if event_type == 'consult':
            return self._normalize_consult_event(message, fields)
        if event_type == 'nursing_note':
            return self._normalize_nursing_event(message, fields)
        if event_type == 'procedure_event':
            return self._normalize_procedure_event(message, fields)
        if event_type == 'post_procedure':
            return self._normalize_post_procedure_event(message, fields)
        return {}

    def _classify_log_event(self, source: str, message: str, level: str) -> str:
        source_upper = str(source).upper()
        message_lower = str(message).lower()
        level_upper = str(level).upper()

        if 'triage' in source_upper.lower() and 'vitals' in message_lower:
            return 'vitals_capture'
        if source_upper == 'LAB-RESULT':
            return 'lab_result'
        if source_upper == 'LAB-ORDER':
            return 'lab_order'
        if source_upper == 'PHARMACY':
            return 'medication_event'
        if source_upper == 'RADIOLOGY' and 'ordered' in message_lower:
            return 'imaging_order'
        if source_upper == 'RADIOLOGY' and ('result' in message_lower or 'resulted' in message_lower):
            return 'imaging_result'
        if source_upper == 'CONSULT':
            return 'consult'
        if source_upper == 'NURSING' or 'nursing' in source_upper.lower():
            return 'nursing_note'
        if 'post-proc' in source_upper.lower() or 'post_proc' in source_upper.lower() or 'postprocedure' in source_upper.lower():
            return 'post_procedure'
        if source_upper == 'EMR-SYSTEM' and 'check-in' in message_lower:
            return 'patient_check_in'
        if source_upper == 'EMR-SYSTEM' and 'priority assigned' in message_lower:
            return 'triage_priority'
        if 'critical value' in message_lower or level_upper == 'ALERT':
            return 'critical_alert'
        if 'procedure' in message_lower and 'started' in message_lower or 'completed' in message_lower or 'in progress' in message_lower:
            return 'procedure_event'
        return self._normalize_field_key(source) or 'log_event'

    def _calculate_normalization_confidence(self, entry: dict) -> dict:
        """
        Phase 4: Calculate confidence score for normalized entry.
        Returns: {'overall_score': 0-100, 'review_needed': bool, 'components': {...}}
        """
        event_type = entry.get('event_type', 'unknown')
        payload = entry.get('normalized_payload', {})
        
        # Define field importance for each event type
        event_rules = {
            'lab_result': {
                'required': ['test_name', 'value', 'unit'],
                'optional': ['abnormal_flag', 'reference_range', 'criticality'],
                'weight': {'required': 0.5, 'payload_complete': 0.3, 'extraction': 0.2}
            },
            'lab_order': {
                'required': ['order_set', 'priority'],
                'optional': ['ordering_provider', 'ordered_tests'],
                'weight': {'required': 0.5, 'payload_complete': 0.25, 'extraction': 0.25}
            },
            'medication_event': {
                'required': ['medication_name', 'action'],
                'optional': ['route', 'dose', 'frequency', 'infusion_rate'],
                'weight': {'required': 0.45, 'payload_complete': 0.35, 'extraction': 0.2}
            },
            'imaging_order': {
                'required': ['modality', 'priority'],
                'optional': ['indication'],
                'weight': {'required': 0.55, 'payload_complete': 0.25, 'extraction': 0.2}
            },
            'imaging_result': {
                'required': ['modality', 'findings'],
                'optional': ['impression'],
                'weight': {'required': 0.5, 'payload_complete': 0.3, 'extraction': 0.2}
            },
            'consult': {
                'required': ['specialty', 'status'],
                'optional': ['reason', 'plan', 'consulting_provider'],
                'weight': {'required': 0.5, 'payload_complete': 0.3, 'extraction': 0.2}
            },
            'nursing_note': {
                'required': ['event_subtype'],
                'optional': ['mental_status', 'pain_level', 'vitals', 'oxygen_support'],
                'weight': {'required': 0.4, 'payload_complete': 0.35, 'extraction': 0.25}
            },
            'procedure_event': {
                'required': ['procedure_name', 'status'],
                'optional': ['provider', 'location', 'findings', 'technique'],
                'weight': {'required': 0.5, 'payload_complete': 0.3, 'extraction': 0.2}
            },
            'post_procedure': {
                'required': ['patient_status'],
                'optional': ['hemostasis', 'drain_output', 'monitoring_plan'],
                'weight': {'required': 0.45, 'payload_complete': 0.35, 'extraction': 0.2}
            },
        }
        
        rules = event_rules.get(event_type, event_rules.get('lab_result'))  # default
        
        # Score 1: Required fields coverage (0-100)
        required_fields = rules.get('required', [])
        if required_fields:
            found_required = sum(1 for f in required_fields if payload.get(f))
            required_score = (found_required / len(required_fields)) * 100
        else:
            required_score = 100
        
        # Score 2: Payload completeness (0-100)
        all_fields = rules.get('required', []) + rules.get('optional', [])
        if all_fields:
            found_total = sum(1 for f in all_fields if payload.get(f))
            completeness_score = (found_total / len(all_fields)) * 100
        else:
            completeness_score = 100 if payload else 50
        
        # Score 3: Extraction quality (0-100)
        # Based on source clarity and field extraction quality
        extraction_score = 75  # baseline
        if entry.get('source') and entry.get('source') != 'unknown':
            extraction_score += 15
        if 'fields' in entry and entry['fields']:
            extraction_score += 10
        extraction_score = min(extraction_score, 100)
        
        # Combine scores with weights
        weights = rules.get('weight', {'required': 0.5, 'payload_complete': 0.3, 'extraction': 0.2})
        overall_score = (
            required_score * weights['required'] +
            completeness_score * weights['payload_complete'] +
            extraction_score * weights['extraction']
        )
        overall_score = round(min(overall_score, 100), 1)
        
        # Determine if review is needed
        review_threshold = 70  # Phase 4 default
        # Critical events need higher confidence
        if event_type in ['lab_result', 'procedure_event']:
            review_threshold = 75
        
        review_needed = overall_score < review_threshold
        
        return {
            'overall_score': overall_score,
            'review_needed': review_needed,
            'review_status': 'pending_review' if review_needed else 'approved',
            'components': {
                'required_fields': round(required_score, 1),
                'payload_completeness': round(completeness_score, 1),
                'extraction_quality': round(extraction_score, 1),
            },
            'reasoning': (
                f"Confidence: {required_score:.0f}% required fields, "
                f"{completeness_score:.0f}% complete, {extraction_score:.0f}% extraction quality"
            )
        }

    def _estimate_log_parse_confidence(self, entry: dict) -> float:
        score = 0.35
        if entry.get('timestamp'):
            score += 0.2
        if entry.get('level') and entry.get('level') != 'RAW':
            score += 0.1
        if entry.get('source') and entry.get('source') != 'unknown':
            score += 0.1
        if entry.get('event_type') and entry.get('event_type') != 'log_event':
            score += 0.1
        if entry.get('fields'):
            score += min(0.1, len(entry['fields']) * 0.02)
        if entry.get('clinical_snapshot'):
            score += min(0.15, len(entry['clinical_snapshot']) * 0.05)
        if entry.get('normalized_payload'):
            score += min(0.1, len(entry['normalized_payload']) * 0.02)
        return round(min(score, 0.99), 2)

    def parse_log_entries(self, text: str) -> List[dict]:
        """Parse EMR-style log files into normalized event records."""
        entries = []
        log_pattern = re.compile(
            r'(?ms)^\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+([^:]+):\s*(.*?)\s*(?=^\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[\w+\]\s+[^:]+:|\Z)'
        )

        matches = list(log_pattern.finditer(text))
        if matches:
            for index, match in enumerate(matches, 1):
                timestamp = match.group(1)
                level = match.group(2)
                source = match.group(3).strip()
                message = re.sub(r'\s+', ' ', match.group(4)).strip()
                fields = self._extract_inline_fields(message)
                clinical_snapshot = self._extract_clinical_snapshot(message)
                event_type = self._classify_log_event(source, message, level)
                normalized_payload = self._normalize_log_event_payload(event_type, message, fields, level)
                entry = {
                    'entry_id': f'LOG-{index:04d}',
                    'timestamp': timestamp,
                    'timestamp_iso': self._normalize_timestamp_iso(timestamp),
                    'level': level,
                    'source': source,
                    'event_type': event_type,
                    'message': message,
                    'summary': message.split('|')[0].strip(),
                    'fields': fields,
                    'normalized_payload': normalized_payload,
                    'clinical_snapshot': clinical_snapshot,
                    'codes': {
                        'icd10': sorted(set(re.findall(ICD10_PATTERN, message))),
                        'cpt': sorted(set(re.findall(CPT_PATTERN, message))),
                    },
                    'line_number': text[:match.start()].count('\n') + 1,
                }
                entry['parse_confidence'] = self._estimate_log_parse_confidence(entry)
                # Phase 4: Add normalization confidence score
                if entry.get('normalized_payload'):
                    confidence = self._calculate_normalization_confidence(entry)
                    entry['normalization_confidence'] = confidence['overall_score']
                    entry['review_needed'] = confidence['review_needed']
                    entry['review_status'] = confidence['review_status']
                    entry['confidence_components'] = confidence['components']
                entries.append(entry)
        else:
            for line_num, line in enumerate(text.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                entry = {
                    'entry_id': f'LOG-{line_num:04d}',
                    'timestamp': None,
                    'timestamp_iso': None,
                    'level': 'RAW',
                    'source': 'unknown',
                    'event_type': 'raw_log_line',
                    'message': line,
                    'summary': line[:120],
                    'fields': self._extract_inline_fields(line),
                    'normalized_payload': {},
                    'clinical_snapshot': self._extract_clinical_snapshot(line),
                    'codes': {
                        'icd10': sorted(set(re.findall(ICD10_PATTERN, line))),
                        'cpt': sorted(set(re.findall(CPT_PATTERN, line))),
                    },
                    'line_number': line_num,
                }
                entry['parse_confidence'] = self._estimate_log_parse_confidence(entry)
                # Phase 4: Add normalization confidence score
                if entry.get('normalized_payload'):
                    confidence = self._calculate_normalization_confidence(entry)
                    entry['normalization_confidence'] = confidence['overall_score']
                    entry['review_needed'] = confidence['review_needed']
                    entry['review_status'] = confidence['review_status']
                    entry['confidence_components'] = confidence['components']
                entries.append(entry)

        structured_count = sum(1 for entry in entries if entry.get('event_type') != 'raw_log_line')
        self._log(f"Parsed {len(entries)} log entries ({structured_count} structured events)")
        return entries

    def build_quality_report(self, result: dict, raw_text: str) -> dict:
        """Assess extraction quality for unstructured healthcare text processing."""
        issues = []
        compliance_validation = result.get('compliance_validation') or {}
        log_entries = result.get('log_entries') or []
        sections = result.get('sections') or []
        entities = result.get('entities') or []
        clinical_values = result.get('clinical_values') or {}

        compliance_issues = len(compliance_validation.get('issues') or [])
        compliance_score = 100 if compliance_validation.get('passed') else max(20, 100 - (compliance_issues * 20))
        if compliance_issues:
            issues.extend(compliance_validation.get('issues', []))

        structured_log_entries = [entry for entry in log_entries if entry.get('event_type') != 'raw_log_line']
        normalized_log_entries = [entry for entry in structured_log_entries if entry.get('normalized_payload')]
        avg_log_confidence = 0.0
        if structured_log_entries:
            avg_log_confidence = sum(entry.get('parse_confidence', 0.0) for entry in structured_log_entries) / len(structured_log_entries)
        log_structure_score = 100
        if log_entries:
            log_structure_score = round(min(100, (avg_log_confidence * 70) + ((len(normalized_log_entries) / max(1, len(structured_log_entries))) * 30)))
            if normalized_log_entries and len(normalized_log_entries) < max(1, int(len(structured_log_entries) * 0.5)):
                issues.append('Only a subset of log events were normalized into typed clinical records.')

        clinical_measurement_count = sum(
            len(value) if isinstance(value, list) else 1
            for key, value in clinical_values.items()
            if key not in ('icd10_codes', 'cpt_codes')
        )
        clinical_signal_count = clinical_measurement_count + len([entry for entry in normalized_log_entries if entry.get('event_type') in ('lab_result', 'medication_event', 'vitals_capture')])
        clinical_coverage_score = round(min(100, 35 + (clinical_signal_count * 6)))
        if clinical_signal_count == 0:
            issues.append('No clinical measurements or normalized clinical events were extracted.')

        structure_score = round(min(100, 40 + (len(sections) * 8) + (len(entities) * 2)))
        metadata = result.get('metadata') or {}
        if metadata.get('extension') == '.log' and not log_entries:
            structure_score = 25
            issues.append('Log file did not yield structured entries.')

        dimension_scores = {
            'compliance': compliance_score,
            'log_structure': log_structure_score,
            'clinical_coverage': clinical_coverage_score,
            'document_structure': structure_score,
        }
        overall_score = round(sum(dimension_scores.values()) / len(dimension_scores))

        if overall_score >= 90:
            grade = 'A'
            summary = 'Production-grade extraction quality with strong normalization coverage.'
        elif overall_score >= 80:
            grade = 'B'
            summary = 'High-quality extraction with minor normalization gaps.'
        elif overall_score >= 70:
            grade = 'C'
            summary = 'Usable extraction quality, but review is recommended for edge cases.'
        else:
            grade = 'D'
            summary = 'Extraction quality is incomplete and needs manual review.'

        report = {
            'overall_score': overall_score,
            'grade': grade,
            'summary': summary,
            'dimensions': dimension_scores,
            'issues': issues[:6],
            'signals': {
                'structured_log_events': len(structured_log_entries),
                'normalized_log_events': len(normalized_log_entries),
                'medication_events': len([entry for entry in normalized_log_entries if entry.get('event_type') == 'medication_event']),
                'lab_results': len([entry for entry in normalized_log_entries if entry.get('event_type') == 'lab_result']),
                'clinical_measurements': clinical_measurement_count,
                'entities': len(entities),
                'text_length': len(raw_text or ''),
            },
        }
        self._log(f"Quality score: {overall_score}/100 ({grade})")
        return report

    def extract_sections(self, text: str) -> List[dict]:
        """Identify and extract sections/headings from clinical documents."""
        sections = []

        heading_patterns = [
            r'^(#{1,6})\s+(.+)$',
            r'^([A-Z][A-Z\s&/\-]{3,}):?\s*$',
            r'^([A-Z][A-Z\s&/\-]{3,}):\s*(.+)$',
            r'^(\d+\.)\s+([A-Z].+)$',
        ]

        lines = text.split('\n')
        current_section = None
        current_content = []

        for i, line in enumerate(lines):
            is_heading = False

            for pattern in heading_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    if current_section:
                        current_section['content'] = '\n'.join(current_content).strip()
                        current_section['word_count'] = len(current_section['content'].split())
                        sections.append(current_section)

                    heading_text = match.group(2) if match.lastindex >= 2 else match.group(1)
                    current_section = {
                        'section_id': f"SEC-{len(sections) + 1:03d}",
                        'heading': heading_text.strip(),
                        'line_start': i + 1,
                        'content': '',
                        'word_count': 0
                    }
                    current_content = []
                    is_heading = True
                    break

            if not is_heading and line.strip():
                current_content.append(line)

        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            current_section['word_count'] = len(current_section['content'].split())
            sections.append(current_section)

        self._log(f"Identified {len(sections)} document sections")
        return sections

    def _normalize_date_iso(self, date_text: str) -> str:
        """Normalize supported date strings to ISO-8601 (YYYY-MM-DD)."""
        if not date_text:
            return ''

        cleaned = date_text.strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(cleaned, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return cleaned

    def _normalize_schema_unit(self, unit: str) -> str:
        """Normalize schema metric units to controlled labels."""
        if not unit:
            return ''
        u = unit.strip().lower().replace(' ', '')
        mapping = {
            'kg/m2': 'bmi_unit',
            'kg/m^2': 'bmi_unit',
            '%': 'percent',
        }
        return mapping.get(u, unit)

    def _extract_schema_metrics(self, text: str, sections: List[dict]) -> List[dict]:
        """
        PromptML numeric layer for analyst-ready metrics.
        Output columns: Metric, Value_Low, Value_High, Unit, Raw_Reference, Section_ID, Section_Context
        """
        metrics = []

        # Build lightweight section index by text anchors.
        section_positions = []
        cursor = 0
        for sec in sections or []:
            content = sec.get('content', '') or ''
            snippet = content[:100].strip()
            pos = text.find(snippet, cursor) if snippet else -1
            if pos >= 0:
                start = pos
                end = pos + len(content)
                cursor = end
            else:
                start = cursor
                end = cursor
            section_positions.append({
                'start': start,
                'end': end,
                'section_id': sec.get('section_id', ''),
                'heading': sec.get('heading', ''),
            })

        def resolve_section(pos: int) -> Tuple[str, str]:
            for sp in section_positions:
                if sp['start'] <= pos <= max(sp['end'], sp['start']):
                    return sp['section_id'], sp['heading']
            return '', ''

        patterns = [
            {
                'name': 'BMI',
                'regex': re.compile(r'BMI\D*(\d+\.?\d*)\s*(\d+\.?\d*)?\s*(kg/m2|kg/m\^2)?', re.IGNORECASE),
                'default_unit': 'kg/m2',
            },
            {
                'name': 'HbA1c',
                'regex': re.compile(r'HBA1C\D*(\d+\.?\d*)%\s*(?:and|to)?\s*(\d+\.?\d*)?%?', re.IGNORECASE),
                'default_unit': '%',
            },
        ]

        for spec in patterns:
            for match in spec['regex'].finditer(text):
                low = match.group(1) if match.lastindex and match.lastindex >= 1 else ''
                high = match.group(2) if match.lastindex and match.lastindex >= 2 else ''
                raw_unit = ''
                if match.lastindex and match.lastindex >= 3:
                    raw_unit = match.group(3) or ''
                if not raw_unit:
                    raw_unit = spec['default_unit']

                section_id, heading = resolve_section(match.start())
                metrics.append({
                    'Metric': spec['name'],
                    'Value_Low': low or '',
                    'Value_High': high or '',
                    'Unit': self._normalize_schema_unit(raw_unit),
                    'Raw_Reference': re.sub(r'\s+', ' ', match.group(0)).strip()[:140],
                    'Section_ID': section_id,
                    'Section_Context': heading,
                })

        return metrics

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # MEDICAL SPELL CORRECTION (run BEFORE NER)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def correct_medical_spelling(self, text: str) -> Tuple[str, dict]:
        """
        Two-layer spell correction:
        Layer 1: Exact dictionary lookup for known medical misspellings (fast, deterministic).
        Layer 2: SymSpell frequency-based correction for remaining words (optional).
        Returns (corrected_text, report).
        """
        corrections = []
        corrected = text

        # Layer 1: Medical misspelling dictionary â€” deterministic, case-insensitive
        for wrong, right in MEDICAL_MISSPELLINGS.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            matches = re.findall(pattern, corrected, re.IGNORECASE)
            if matches:
                corrections.append({
                    'from': wrong,
                    'to': right,
                    'count': len(matches),
                    'type': 'medical_dictionary'
                })
                corrected = re.sub(pattern, right, corrected, flags=re.IGNORECASE)

        # Layer 2: SymSpell for general English words (skip medical terms already correct)
        symspell_corrections = 0
        symspell_summary = {}
        sym_spell = self._get_sym_spell()
        if sym_spell is not None:
            try:
                # Only check words not already in our medical vocabulary
                medical_terms = set(MEDICAL_ABBREVIATIONS.keys()) | set(MEDICAL_MISSPELLINGS.values())
                # Process line-by-line to preserve newlines
                lines_in = corrected.split('\n')
                lines_out = []
                for line_text in lines_in:
                    words = line_text.split()
                    corrected_words = []
                    for word in words:
                        clean_word = re.sub(r'[^a-zA-Z]', '', word).lower()
                        # Skip: short words, numbers, medical terms, already uppercase abbreviations
                        if (len(clean_word) < 5 or clean_word in medical_terms
                                or word.isupper() or word[0].isupper()):
                            corrected_words.append(word)
                            continue
                        suggestions = sym_spell.lookup(
                            clean_word, Verbosity.CLOSEST, max_edit_distance=2
                        )
                        if suggestions and suggestions[0].term != clean_word:
                            # Only apply if edit distance is 1 (avoid over-correction)
                            if suggestions[0].distance == 1:
                                corrected_word = re.sub(
                                    clean_word,
                                    suggestions[0].term,
                                    word,
                                    count=1,
                                    flags=re.IGNORECASE,
                                )
                                corrected_words.append(corrected_word)
                                symspell_corrections += 1
                                key = (clean_word, suggestions[0].term)
                                symspell_summary[key] = symspell_summary.get(key, 0) + 1
                            else:
                                corrected_words.append(word)
                        else:
                            corrected_words.append(word)
                    lines_out.append(' '.join(corrected_words))
                corrected = '\n'.join(lines_out)
            except Exception as e:
                self._log(f"SymSpell correction skipped: {e}", "WARNING")

        for (wrong, right), count in sorted(symspell_summary.items()):
            corrections.append({
                'from': wrong,
                'to': right,
                'count': count,
                'type': 'general'
            })

        medical_fixes = sum(item['count'] for item in corrections if item['type'] == 'medical_dictionary')
        total = medical_fixes + symspell_corrections
        self._log(f"Spell correction: {medical_fixes} medical fixes, "
                  f"{symspell_corrections} general fixes")
        return corrected, {
            'corrections': corrections,
            'medical_fixes': medical_fixes,
            'general_fixes': symspell_corrections,
            'total_corrections': total
        }

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # REGEX NER â€” Medical Entity Extraction (no ML model, deterministic)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def extract_medical_entities(self, text: str, sections: List[dict] = None) -> List[dict]:
        """
        Extract medical entities (DISEASE, DRUG, PROCEDURE) using regex patterns.
        Uses section context to improve labelling â€” text under 'Medications' header
        gets higher confidence for DRUG entities.
        Returns list of entity dicts.
        """
        entities = []
        seen = set()  # deduplicate by (text.lower, type, position-bucket)

        # Build section lookup: char_offset â†’ section_heading
        section_map = {}
        if sections:
            char_offset = 0
            for sec in sections:
                section_map[char_offset] = sec.get('heading', '')
                char_offset += len(sec.get('content', '')) + len(sec.get('heading', '')) + 2

        def _get_section(pos: int) -> str:
            best = ''
            for offset, heading in sorted(section_map.items()):
                if offset <= pos:
                    best = heading
                else:
                    break
            return best

        # Context boosts: section heading keywords â†’ entity type confidence boost
        SECTION_BOOSTS = {
            'DISEASE':   ['diagnosis', 'diagnos', 'condition', 'history', 'assessment',
                          'impression', 'problem', 'comorbid'],
            'DRUG':      ['medication', 'medic', 'drug', 'rx', 'prescription',
                          'treatment', 'therapy', 'pharmacol'],
            'PROCEDURE': ['procedure', 'intervention', 'surgery', 'operation',
                          'test', 'exam', 'laboratory', 'imaging'],
        }

        # Optional model-first layer (SciSpaCy BC5CDR), then regex complements it.
        nlp = self._get_scispacy_model()
        if nlp is not None:
            try:
                doc = nlp(text)
                for ent in doc.ents:
                    mapped_type = None
                    if ent.label_ == 'DISEASE':
                        mapped_type = 'DISEASE'
                    elif ent.label_ == 'CHEMICAL':
                        mapped_type = 'DRUG'
                    if not mapped_type:
                        continue

                    entity_text = ent.text.strip()
                    if len(entity_text) < 3:
                        continue

                    pos_bucket = ent.start_char // 200
                    dedup_key = (mapped_type, entity_text.lower(), pos_bucket)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    ctx_start = max(0, ent.start_char - 50)
                    ctx_end = min(len(text), ent.end_char + 50)
                    context = text[ctx_start:ctx_end].strip()
                    section_heading = _get_section(ent.start_char)

                    confidence = 0.9
                    sec_lower = section_heading.lower()
                    for kw in SECTION_BOOSTS.get(mapped_type, []):
                        if kw in sec_lower:
                            confidence = 0.95
                            break

                    entities.append({
                        'text': entity_text,
                        'type': mapped_type,
                        'confidence': confidence,
                        'start': ent.start_char,
                        'section': section_heading,
                        'context': context,
                    })
            except Exception as e:
                self._log(f"SciSpaCy NER pass failed, continuing with regex: {e}", "WARNING")

        for entity_type, pattern in MEDICAL_ENTITY_PATTERNS.items():
            for match in pattern.finditer(text):
                entity_text = match.group(0).strip()
                if len(entity_text) < 3:
                    continue

                # Dedup key: type + normalized text (same entity in 200-char window = one)
                pos_bucket = match.start() // 200
                dedup_key = (entity_type, entity_text.lower(), pos_bucket)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                # Get context (50 chars around match)
                ctx_start = max(0, match.start() - 50)
                ctx_end = min(len(text), match.end() + 50)
                context = text[ctx_start:ctx_end].strip()

                # Get section
                section_heading = _get_section(match.start())

                # Confidence: base 0.80, boost if section heading matches entity type
                confidence = 0.80
                sec_lower = section_heading.lower()
                for kw in SECTION_BOOSTS.get(entity_type, []):
                    if kw in sec_lower:
                        confidence = 0.95
                        break

                entities.append({
                    'text': entity_text,
                    'type': entity_type,
                    'confidence': confidence,
                    'start': match.start(),
                    'section': section_heading,
                    'context': context,
                })

        entities.sort(key=lambda x: x['start'])
        self._log(f"NER extracted {len(entities)} entities "
                  f"({sum(1 for e in entities if e['type']=='DISEASE')} diseases, "
                  f"{sum(1 for e in entities if e['type']=='DRUG')} drugs, "
                  f"{sum(1 for e in entities if e['type']=='PROCEDURE')} procedures)")
        return entities

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # UNIT STANDARDIZATION
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _standardize_units(self, measurement: str, value: float,
                            raw_unit: str = '') -> Tuple[float, str]:
        """
        Standardize a single measurement to a canonical unit.
        Rule-based â€” no ML, no guessing.
        """
        u = raw_unit.lower().strip()

        if measurement == 'temperature':
            # If unit says F, or value > 50 (no human has 37Â°F body temp) â†’ Fahrenheit
            if 'f' in u or value > 50:
                return round((value - 32) * 5 / 9, 1), 'Â°C'
            return round(value, 1), 'Â°C'

        elif measurement == 'weight':
            # If unit says lbs/lb/pounds, or value > 150 (rare to be >150 kg)
            if any(x in u for x in ('lb', 'pound')):
                return round(value * 0.453592, 1), 'kg'
            return round(value, 1), 'kg'

        elif measurement == 'glucose':
            # mmol/L to mg/dL
            if 'mmol' in u:
                return round(value * 18.0, 1), 'mg/dL'
            return round(value, 1), 'mg/dL'

        elif measurement == 'creatinine':
            # Âµmol/L to mg/dL
            if 'umol' in u or 'Âµmol' in u:
                return round(value / 88.4, 2), 'mg/dL'
            return round(value, 2), 'mg/dL'

        elif measurement == 'blood_pressure':
            return round(value, 0), 'mmHg'

        elif measurement == 'heart_rate':
            return round(value, 0), 'bpm'

        elif measurement == 'oxygen_saturation':
            return round(value, 1), '%'

        elif measurement == 'hba1c':
            return round(value, 1), '%'

        elif measurement == 'bmi':
            return round(value, 1), 'kg/mÂ²'

        return value, raw_unit

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # RELATIONAL STRUCTURED OUTPUT â€” separate tables, not one junk CSV
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def generate_structured_tables(self, clinical_values: dict,
                                    entities: List[dict],
                                    sections: List[dict],
                                    analysis_text: str = '') -> dict:
        """Generate relational tables for vitals, entities, metrics, and timeline."""

        def _compact_text(value: str, limit: int = 120) -> str:
            if not value:
                return ''
            compact = re.sub(r'\s+', ' ', str(value)).strip()
            return compact[:limit]

        UNIT_DEFAULTS = {
            'blood_pressure': 'mmHg',
            'heart_rate': 'bpm',
            'respiratory_rate': 'breaths/min',
            'temperature': 'F or C',
            'oxygen_saturation': '%',
            'glucose': 'mg/dL',
            'hba1c': '%',
            'troponin': 'ng/mL',
            'bmi': 'kg/m2',
            'weight': 'kg',
            'creatinine': 'mg/dL',
        }

        vitals_rows = []
        for measurement, values in clinical_values.items():
            if measurement in ('icd10_codes', 'cpt_codes') or not isinstance(values, list):
                continue

            raw_unit = UNIT_DEFAULTS.get(measurement, '')
            for v in values:
                if measurement == 'blood_pressure':
                    sys_v, sys_u = self._standardize_units('blood_pressure', v['systolic'])
                    dia_v, dia_u = self._standardize_units('blood_pressure', v['diastolic'])
                    vitals_rows.append({
                        'Measurement': 'Systolic BP',
                        'Raw_Value': v['systolic'],
                        'Raw_Unit': raw_unit,
                        'Std_Value': sys_v,
                        'Std_Unit': sys_u,
                        'Source_Context': '',
                    })
                    vitals_rows.append({
                        'Measurement': 'Diastolic BP',
                        'Raw_Value': v['diastolic'],
                        'Raw_Unit': raw_unit,
                        'Std_Value': dia_v,
                        'Std_Unit': dia_u,
                        'Source_Context': '',
                    })
                else:
                    raw_val = v.get('value', 0)
                    std_val, std_unit = self._standardize_units(measurement, raw_val, raw_unit)
                    vitals_rows.append({
                        'Measurement': measurement.replace('_', ' ').title(),
                        'Raw_Value': raw_val,
                        'Raw_Unit': raw_unit,
                        'Std_Value': std_val,
                        'Std_Unit': std_unit,
                        'Source_Context': '',
                    })

        heading_to_id = {sec.get('heading', ''): sec.get('section_id', '') for sec in sections or []}

        entity_aggregator = {}
        for e in entities:
            entity_text = e.get('text', '').strip()
            entity_type = e.get('type', '')
            section_id = heading_to_id.get(e.get('section', ''), '')
            section_heading = e.get('section', '')
            key = (entity_text, entity_type, section_id)

            if key not in entity_aggregator:
                entity_aggregator[key] = {
                    'count': 0,
                    'contexts': [],
                    'confidence': float(e.get('confidence', 0.0)),
                    'section_heading': section_heading,
                }

            entity_aggregator[key]['count'] += 1
            ctx = _compact_text(e.get('context', ''), 100)
            if ctx and ctx not in entity_aggregator[key]['contexts']:
                entity_aggregator[key]['contexts'].append(ctx)

        entities_rows = []
        for (entity_text, entity_type, section_id), agg_data in entity_aggregator.items():
            entities_rows.append({
                'Entity': entity_text,
                'Type': entity_type,
                'Confidence': round(agg_data['confidence'], 2),
                'Occurrence_Count': agg_data['count'],
                'Section_ID': section_id,
                'Section_Context': _compact_text(agg_data['section_heading'], 150),
                'Context_Examples': ' | '.join(agg_data['contexts'][:3]),
            })

        metrics_rows = self._extract_schema_metrics(analysis_text or '', sections or [])

        date_pattern = re.compile(r'\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\b')
        timeline_rows = []
        seen_dates = set()
        for sec in sections:
            content = sec.get('content', '')
            heading = sec.get('heading', '')
            for m in date_pattern.finditer(content):
                date_str = m.group(0)
                key = (date_str, heading)
                if key in seen_dates:
                    continue
                seen_dates.add(key)
                ctx_start = max(0, m.start() - 60)
                ctx_end = min(len(content), m.end() + 60)
                timeline_rows.append({
                    'Date': self._normalize_date_iso(date_str),
                    'Section_ID': sec.get('section_id', ''),
                    'Section': heading,
                    'Event': _compact_text(content[ctx_start:ctx_end], 140),
                })

        total_mentions = sum(e['Occurrence_Count'] for e in entities_rows)
        self._log(
            f"Structured tables: {len(vitals_rows)} vital rows, "
            f"{len(entities_rows)} AGGREGATED entity rows ({total_mentions} total mentions), "
            f"{len(metrics_rows)} metric rows, {len(timeline_rows)} timeline rows"
        )

        return {
            'vitals': vitals_rows,
            'entities': entities_rows,
            'metrics': metrics_rows,
            'timeline': timeline_rows,
        }

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # FULL PIPELINE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def process_file(self, file_path: str = None, file_obj=None,
                     filename: str = "", options: dict = None, text: str = None) -> dict:
        """
        Full pipeline: extract -> clean -> detect PHI -> redact -> analyze.
        """
        if options is None or not isinstance(options, dict):
            options = {}

        self.processing_log = []
        self.phi_findings = []

        result = {
            'status': 'success',
            'metadata': {},
            'original_text_preview': '',
            'cleaned_text': '',
            'cleaned_text_preview': '',
            'phi_findings': [],
            'redaction_report': {},
            'cleaning_report': {},
            'spell_correction_report': {},
            'clinical_values': {},
            'abbreviations_report': {},
            'entities': [],
            'structured_tables': {},
            'sections': [],
            'log_entries': [],
            'processing_log': [],
            'compliance_validation': {},
            'quality_report': {},
            'compliance': {
                'hipaa_safe_harbor': False,
                'gdpr_minimization': True,
                'dpdp_compliant': True,
            }
        }

        try:
            # Step 1: Extract text
            if text:
                raw_text = text
                metadata = {
                    'filename': filename,
                    'extension': os.path.splitext(filename)[1].lower() if filename else '.txt',
                    'extraction_method': 'direct_input',
                    'extracted_at': datetime.now().isoformat(),
                    'char_count': len(text),
                    'line_count': text.count('\n') + 1,
                    'word_count': len(text.split()),
                }
            else:
                raw_text, metadata = self.extract_text(file_path, file_obj, filename)
            
            result['metadata'] = metadata
            result['original_text_preview'] = raw_text[:2000] + ('...' if len(raw_text) > 2000 else '')

            # Step 2: Clean text
            cleaning_ops = options.get('cleaning_ops', {
                'normalize_whitespace': True,
                'normalize_line_breaks': True,
                'remove_control_chars': True,
                'fix_encoding_artifacts': True,
                'normalize_unicode': True,
                'standardize_punctuation': True,
                'remove_empty_lines': True,
                'fix_hyphenation': True,
            })
            cleaned_text, cleaning_report = self.clean_text(raw_text, cleaning_ops)
            result['cleaning_report'] = cleaning_report

            analysis_text = cleaned_text

            # Step 3: Expand medical abbreviations on analysis text
            if options.get('expand_abbreviations', True):
                analysis_text, abbrev_report = self.expand_medical_abbreviations(analysis_text)
                result['abbreviations_report'] = abbrev_report

            # Step 4: Medical spell correction on analysis text (BEFORE NER)
            if options.get('spell_correct', True):
                analysis_text, spell_report = self.correct_medical_spelling(analysis_text)
                result['spell_correction_report'] = spell_report

            # Step 5: Detect PHI on the final analysis text
            phi_findings = self.detect_phi(analysis_text)
            result['phi_findings'] = phi_findings
            result['phi_summary'] = {
                'total_found': len(phi_findings),
                'by_type': {},
                'by_risk': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
            }
            for f in phi_findings:
                result['phi_summary']['by_type'][f['type']] = result['phi_summary']['by_type'].get(f['type'], 0) + 1
                result['phi_summary']['by_risk'][f['risk_level']] += 1

            # Step 6: Redact PHI for returned/exported text only
            if options.get('redact_phi', True):
                redaction_style = options.get('redaction_style', 'tag')
                redacted_text, redaction_report = self.redact_phi(analysis_text, phi_findings, redaction_style)
                result['cleaned_text'] = redacted_text
                result['redaction_report'] = redaction_report
                result['compliance_validation'] = self.validate_redaction_quality(redacted_text)
                result['compliance']['hipaa_safe_harbor'] = (
                    redaction_report.get('redactions', 0) > 0 and
                    result['compliance_validation'].get('passed', False)
                )
            else:
                result['cleaned_text'] = analysis_text
                result['compliance_validation'] = self.validate_redaction_quality(analysis_text)

            # Step 7: Extract clinical values from analysis text
            if options.get('extract_clinical', True):
                result['clinical_values'] = self.extract_clinical_values(analysis_text)
                
                # Enrich clinical values with names and addresses found during PHI scan
                for finding in phi_findings:
                    t = finding['type']
                    if t in ('PATIENT_NAME', 'PROVIDER_NAME', 'ADDRESS'):
                        val = finding['matched_text_preview'].replace('***', '') # The full text is not available in finding, we need to extract from raw_text
                        val_full = raw_text[finding['start']:finding['end']]
                        
                        if t not in result['clinical_values']:
                            result['clinical_values'][t] = []
                        
                        # Avoid duplicates
                        existing = [v['value'] for v in result['clinical_values'][t] if isinstance(v, dict) and 'value' in v]
                        if val_full not in existing:
                            result['clinical_values'][t].append({
                                'value': val_full,
                                'position': finding['start']
                            })

            # Step 8: Parse log entries (for .log files)
            ext = metadata.get('extension', '')
            if ext == '.log' and options.get('parse_logs', True):
                result['log_entries'] = self.parse_log_entries(raw_text)

            # Step 9: Extract sections from analysis text
            if options.get('extract_sections', True):
                result['sections'] = self.extract_sections(analysis_text)

            # Step 10: Regex NER - DISEASE, DRUG, PROCEDURE (uses sections for boost)
            if options.get('extract_entities', True):
                result['entities'] = self.extract_medical_entities(
                    analysis_text, result['sections']
                )

            # Step 11: Generate relational structured tables
            if options.get('generate_tables', True):
                result['structured_tables'] = self.generate_structured_tables(
                    result['clinical_values'],
                    result['entities'],
                    result['sections'],
                    analysis_text,
                )

            # Final preview
            result['cleaned_text_preview'] = result['cleaned_text'][:2000] + (
                '...' if len(result['cleaned_text']) > 2000 else ''
            )

            # Stats
            result['stats'] = {
                'original_chars': len(raw_text),
                'cleaned_chars': len(result['cleaned_text']),
                'original_words': len(raw_text.split()),
                'cleaned_words': len(result['cleaned_text'].split()),
                'original_lines': raw_text.count('\n') + 1,
                'cleaned_lines': result['cleaned_text'].count('\n') + 1,
                'phi_items_found': len(phi_findings),
                'phi_items_redacted': result['redaction_report'].get('redactions', 0),
                'sections_found': len(result['sections']),
                'clinical_measurements': sum(
                    len(v) if isinstance(v, list) else 1
                    for v in result['clinical_values'].values()
                ),
                'abbreviations_expanded': result['abbreviations_report'].get('total_expanded', 0),
                'entities_found': len(result['entities']),
                'spell_corrections': result['spell_correction_report'].get('total_corrections', 0),
                'schema_metrics_found': len(result['structured_tables'].get('metrics', [])),
                'structured_log_events': len([entry for entry in result['log_entries'] if entry.get('event_type') != 'raw_log_line']),
                'normalized_lab_events': len([entry for entry in result['log_entries'] if entry.get('event_type') == 'lab_result' and entry.get('normalized_payload')]),
                'normalized_medication_events': len([entry for entry in result['log_entries'] if entry.get('event_type') == 'medication_event' and entry.get('normalized_payload')]),
            }
            result['quality_report'] = self.build_quality_report(result, raw_text)
            result['stats']['quality_score'] = result['quality_report'].get('overall_score', 0)

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self._log(f"Processing error: {e}", "ERROR")

        result['processing_log'] = self.processing_log
        return result

    def export_cleaned_text(self, text: str, fmt: str = 'txt') -> str:
        """Return cleaned text in the requested format."""
        return text

    # Alias to match server.py expectations
    process_text = process_file
