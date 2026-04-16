#!/usr/bin/env python3
"""
Smart Data Cleaner - Web Backend (Enhanced)
Flask server providing dataset analysis and cleaning API endpoints.
Supports: CSV, Excel, JSON, and XML files
All 11 cleaning operations from v0.0.7 are fully wired.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import re
import json
import copy
import xml.etree.ElementTree as ET
from datetime import datetime
from difflib import SequenceMatcher
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException
import uuid

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

try:
    from thefuzz import fuzz, process as fuzz_process
    THEFUZZ_AVAILABLE = True
except ImportError:
    THEFUZZ_AVAILABLE = False

try:
    from unstructured_processor import UnstructuredDataProcessor
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

try:
    from review_workflow import ReviewWorkflow, get_review_summary, export_reviewed_entries
    REVIEW_WORKFLOW_AVAILABLE = True
except ImportError:
    REVIEW_WORKFLOW_AVAILABLE = False

try:
    from phase5_production_hardening import BatchProcessor, StructuredLogger, export_for_auditor
    PHASE5_AVAILABLE = True
except ImportError:
    PHASE5_AVAILABLE = False

# Store unstructured processing results in memory
unstructured_store = {}
review_workflows = {}

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    return jsonify({
        "error": e.description,
        "code": e.code,
        "name": e.name
    }), e.code

# Configure inputs folder (all sample/demo data files)
INPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'inputs')
os.makedirs(INPUT_FOLDER, exist_ok=True)
app.config['INPUT_FOLDER'] = INPUT_FOLDER

# Store data in memory for the session
data_store = {}
lineage_store = {}

STANDARD_SCHEMAS = {
    'healthcare': {
        'patient_id': ['patient_id', 'pt_id', 'pid', 'mrn', 'medical_record_number', 'uhid'],
        'patient_name': ['name', 'patient_name', 'pt_name', 'full_name', 'patient_nm'],
        'age': ['age', 'age_years', 'patient_age', 'yrs'],
        'gender': ['gender', 'sex'],
        'diagnosis': ['diagnosis', 'dx', 'condition', 'disease'],
        'admission_date': ['admission_date', 'admit_date', 'visit_date', 'encounter_date'],
        'discharge_date': ['discharge_date', 'release_date'],
        'blood_pressure': ['blood_pressure', 'bp', 'systolic_bp', 'diastolic_bp'],
        'heart_rate': ['heart_rate', 'hr', 'pulse']
    },
    'general': {
        'id': ['id', 'identifier', 'record_id'],
        'name': ['name', 'full_name', 'title'],
        'date': ['date', 'created_date', 'timestamp'],
        'amount': ['amount', 'price', 'cost', 'value'],
        'category': ['category', 'type', 'segment'],
        'status': ['status', 'state']
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Medical Dictionaries & Constants (No external licenses required)
# ─────────────────────────────────────────────────────────────────────────────

# 200+ common medical abbreviations → full forms
MEDICAL_ABBREVIATIONS = {
    # Vitals & Measurements
    'bp': 'Blood Pressure', 'hr': 'Heart Rate', 'rr': 'Respiratory Rate',
    'temp': 'Temperature', 'spo2': 'Oxygen Saturation', 'bmi': 'Body Mass Index',
    'bpm': 'Beats Per Minute', 'mmhg': 'Millimeters of Mercury',
    # Clinical Shorthand
    'dx': 'Diagnosis', 'rx': 'Prescription', 'tx': 'Treatment',
    'hx': 'History', 'sx': 'Symptoms', 'fx': 'Fracture',
    'sob': 'Shortness of Breath', 'cp': 'Chest Pain', 'ha': 'Headache',
    'n/v': 'Nausea/Vomiting', 'abd': 'Abdominal', 'bilat': 'Bilateral',
    'nkda': 'No Known Drug Allergies', 'nka': 'No Known Allergies',
    # Dosage & Frequency
    'prn': 'As Needed', 'bid': 'Twice Daily', 'tid': 'Three Times Daily',
    'qid': 'Four Times Daily', 'qd': 'Once Daily', 'qh': 'Every Hour',
    'q2h': 'Every 2 Hours', 'q4h': 'Every 4 Hours', 'q6h': 'Every 6 Hours',
    'q8h': 'Every 8 Hours', 'q12h': 'Every 12 Hours', 'hs': 'At Bedtime',
    'ac': 'Before Meals', 'pc': 'After Meals', 'stat': 'Immediately',
    # Routes
    'po': 'By Mouth', 'iv': 'Intravenous', 'im': 'Intramuscular',
    'sc': 'Subcutaneous', 'sl': 'Sublingual', 'pr': 'Per Rectum',
    'inh': 'Inhalation', 'top': 'Topical',
    # Diseases & Conditions
    'dm': 'Diabetes Mellitus', 'dm2': 'Diabetes Mellitus Type 2',
    'dm1': 'Diabetes Mellitus Type 1', 'htn': 'Hypertension',
    'cad': 'Coronary Artery Disease', 'chf': 'Congestive Heart Failure',
    'copd': 'Chronic Obstructive Pulmonary Disease', 'ckd': 'Chronic Kidney Disease',
    'uti': 'Urinary Tract Infection', 'dvt': 'Deep Vein Thrombosis',
    'pe': 'Pulmonary Embolism', 'mi': 'Myocardial Infarction',
    'cva': 'Cerebrovascular Accident', 'tia': 'Transient Ischemic Attack',
    'afib': 'Atrial Fibrillation', 'ards': 'Acute Respiratory Distress Syndrome',
    'aki': 'Acute Kidney Injury', 'bph': 'Benign Prostatic Hyperplasia',
    'gerd': 'Gastroesophageal Reflux Disease', 'ibs': 'Irritable Bowel Syndrome',
    'osa': 'Obstructive Sleep Apnea', 'ra': 'Rheumatoid Arthritis',
    'sle': 'Systemic Lupus Erythematosus', 'tb': 'Tuberculosis',
    'hiv': 'Human Immunodeficiency Virus', 'aids': 'Acquired Immunodeficiency Syndrome',
    'ms': 'Multiple Sclerosis', 'gad': 'Generalized Anxiety Disorder',
    'ptsd': 'Post-Traumatic Stress Disorder', 'adhd': 'Attention Deficit Hyperactivity Disorder',
    'ocd': 'Obsessive Compulsive Disorder',
    # Lab & Diagnostic
    'cbc': 'Complete Blood Count', 'bmp': 'Basic Metabolic Panel',
    'cmp': 'Comprehensive Metabolic Panel', 'lfts': 'Liver Function Tests',
    'abg': 'Arterial Blood Gas', 'ekg': 'Electrocardiogram',
    'ecg': 'Electrocardiogram', 'ct': 'Computed Tomography',
    'mri': 'Magnetic Resonance Imaging', 'cxr': 'Chest X-Ray',
    'us': 'Ultrasound', 'eeg': 'Electroencephalogram',
    'echo': 'Echocardiogram', 'emg': 'Electromyography',
    # Lab Values
    'wbc': 'White Blood Cell', 'rbc': 'Red Blood Cell',
    'hgb': 'Hemoglobin', 'hct': 'Hematocrit', 'plt': 'Platelets',
    'inr': 'International Normalized Ratio', 'ptt': 'Partial Thromboplastin Time',
    'esr': 'Erythrocyte Sedimentation Rate', 'crp': 'C-Reactive Protein',
    'hba1c': 'Glycated Hemoglobin', 'a1c': 'Glycated Hemoglobin',
    'tsh': 'Thyroid Stimulating Hormone', 'bun': 'Blood Urea Nitrogen',
    'gfr': 'Glomerular Filtration Rate', 'psa': 'Prostate-Specific Antigen',
    'alt': 'Alanine Transaminase', 'ast': 'Aspartate Transaminase',
    'alp': 'Alkaline Phosphatase', 'bnp': 'Brain Natriuretic Peptide',
    'ldl': 'Low-Density Lipoprotein', 'hdl': 'High-Density Lipoprotein',
    # Departments & Roles
    'er': 'Emergency Room', 'ed': 'Emergency Department',
    'icu': 'Intensive Care Unit', 'nicu': 'Neonatal ICU',
    'picu': 'Pediatric ICU', 'pacu': 'Post-Anesthesia Care Unit',
    # NOTE: 'us', 'or', 'pt', 'ms' removed — too ambiguous (United States, Oregon, Patient, etc.)
    'rn': 'Registered Nurse',
}

# 150+ disease names → ICD-10 code mapping
DISEASE_TO_ICD10 = {
    # Diabetes
    'diabetes': 'E11', 'diabetes mellitus': 'E11', 'diabetes mellitus type 2': 'E11',
    'type 2 diabetes': 'E11', 'type ii diabetes': 'E11', 'dm2': 'E11',
    'diabetes mellitus type 1': 'E10', 'type 1 diabetes': 'E10', 'dm1': 'E10',
    'gestational diabetes': 'O24', 'high blood sugar': 'E11', 'hyperglycemia': 'R73.9',
    # Cardiovascular
    'hypertension': 'I10', 'htn': 'I10', 'high blood pressure': 'I10',
    'heart failure': 'I50', 'chf': 'I50.9', 'congestive heart failure': 'I50.9',
    'coronary artery disease': 'I25.10', 'cad': 'I25.10',
    'myocardial infarction': 'I21', 'heart attack': 'I21',
    'atrial fibrillation': 'I48', 'afib': 'I48', 'angina': 'I20',
    'stroke': 'I63', 'cva': 'I63', 'cerebrovascular accident': 'I63',
    'dvt': 'I82', 'deep vein thrombosis': 'I82',
    'pulmonary embolism': 'I26', 'hyperlipidemia': 'E78.5',
    'high cholesterol': 'E78.0', 'hypotension': 'I95',
    # Respiratory
    'asthma': 'J45', 'copd': 'J44', 'chronic obstructive pulmonary disease': 'J44',
    'pneumonia': 'J18', 'bronchitis': 'J40', 'emphysema': 'J43',
    'tuberculosis': 'A15', 'tb': 'A15',
    'covid': 'U07.1', 'covid-19': 'U07.1', 'coronavirus': 'U07.1',
    'influenza': 'J11', 'flu': 'J11', 'upper respiratory infection': 'J06.9',
    'pharyngitis': 'J02.9', 'sinusitis': 'J32', 'sleep apnea': 'G47.3',
    # Gastrointestinal
    'gerd': 'K21', 'acid reflux': 'K21', 'gastritis': 'K29',
    'peptic ulcer': 'K27', 'ibs': 'K58', 'irritable bowel syndrome': 'K58',
    "crohn's disease": 'K50', 'ulcerative colitis': 'K51', 'cirrhosis': 'K74',
    'hepatitis': 'K75', 'hepatitis b': 'B16', 'hepatitis c': 'B17.1',
    'pancreatitis': 'K85', 'gallstones': 'K80', 'appendicitis': 'K35',
    # Musculoskeletal
    'osteoarthritis': 'M19', 'rheumatoid arthritis': 'M06',
    'osteoporosis': 'M81', 'gout': 'M10', 'back pain': 'M54',
    'low back pain': 'M54.5', 'fibromyalgia': 'M79.7',
    # Neurological
    'epilepsy': 'G40', 'seizure': 'R56', 'migraine': 'G43',
    "parkinson's disease": 'G20', "alzheimer's disease": 'G30', 'dementia': 'F03',
    'multiple sclerosis': 'G35', 'neuropathy': 'G62.9',
    # Renal
    'chronic kidney disease': 'N18', 'ckd': 'N18', 'acute kidney injury': 'N17',
    'urinary tract infection': 'N39.0', 'uti': 'N39.0', 'kidney stones': 'N20',
    # Endocrine
    'hypothyroidism': 'E03', 'hyperthyroidism': 'E05', 'obesity': 'E66',
    # Mental Health
    'depression': 'F32', 'major depression': 'F33', 'anxiety': 'F41',
    'bipolar disorder': 'F31', 'schizophrenia': 'F20', 'ptsd': 'F43.1',
    'insomnia': 'G47.0', 'adhd': 'F90',
    # Infectious
    'sepsis': 'A41', 'cellulitis': 'L03', 'meningitis': 'G03',
    'hiv': 'B20', 'malaria': 'B54', 'dengue': 'A90', 'typhoid': 'A01.0',
    # Dermatological
    'eczema': 'L30.9', 'psoriasis': 'L40', 'acne': 'L70',
    # Oncology
    'breast cancer': 'C50', 'lung cancer': 'C34', 'colon cancer': 'C18',
    'prostate cancer': 'C61', 'leukemia': 'C95', 'lymphoma': 'C85',
    # Hematological
    'anemia': 'D64.9', 'iron deficiency anemia': 'D50',
    'sickle cell disease': 'D57', 'thalassemia': 'D56',
    # Common symptoms mapped to codes
    'fever': 'R50.9', 'cough': 'R05', 'fatigue': 'R53',
    'chest pain': 'R07.9', 'headache': 'R51', 'nausea': 'R11',
    'edema': 'R60', 'dehydration': 'E86',
}

# Common medical misspellings → correct spelling
MEDICAL_SPELL_CORRECTIONS = {
    'diabeties': 'diabetes', 'diabtes': 'diabetes', 'diabetis': 'diabetes',
    'hypertention': 'hypertension', 'hypertenshion': 'hypertension',
    'pnuemonia': 'pneumonia', 'pneumnia': 'pneumonia', 'pnemonia': 'pneumonia',
    'astma': 'asthma', 'asthama': 'asthma',
    'epilepsey': 'epilepsy', 'epilepcy': 'epilepsy',
    'arrythmia': 'arrhythmia', 'arythmia': 'arrhythmia',
    'diarrhoea': 'diarrhea', 'diarhea': 'diarrhea',
    'hemorrage': 'hemorrhage', 'haemorrhage': 'hemorrhage',
    'aneurism': 'aneurysm', 'cathater': 'catheter',
    'excema': 'eczema', 'exzema': 'eczema',
    'hemogloben': 'hemoglobin', 'haemoglobin': 'hemoglobin',
    'influensa': 'influenza', 'luekemia': 'leukemia', 'lukemia': 'leukemia',
    'menigitis': 'meningitis', 'meningitus': 'meningitis',
    'osteoporisis': 'osteoporosis', 'osteoporasis': 'osteoporosis',
    'psorisis': 'psoriasis', 'rhuematoid': 'rheumatoid',
    'schizophrena': 'schizophrenia', 'skizofrenia': 'schizophrenia',
    'tuberclosis': 'tuberculosis', 'tuburculosis': 'tuberculosis',
    'tonsilitis': 'tonsillitis', 'broncitis': 'bronchitis',
    'colestrol': 'cholesterol', 'cholestrol': 'cholesterol',
    'cirrhossis': 'cirrhosis', 'alzhiemers': "alzheimer's",
    'hypothyrodism': 'hypothyroidism', 'gastritus': 'gastritis',
    'appendecitis': 'appendicitis', 'pancreatitus': 'pancreatitis',
    'anaemia': 'anemia', 'thalessemia': 'thalassemia',
    'fibromalgia': 'fibromyalgia', 'nueropathy': 'neuropathy',
    'sepssis': 'sepsis', 'parkinsons': "parkinson's",
}

# ICD-10 format validation
ICD10_PATTERN = re.compile(r'^[A-Z]\d{2}\.?\d{0,4}$', re.IGNORECASE)

# Common LOINC codes for lab tests
COMMON_LOINC_CODES = {
    '2345-7': 'Glucose', '2160-0': 'Creatinine', '3094-0': 'BUN',
    '2951-2': 'Sodium', '2823-3': 'Potassium', '2075-0': 'Chloride',
    '17861-6': 'Calcium', '1751-7': 'Albumin', '1742-6': 'ALT',
    '1920-8': 'AST', '6768-6': 'ALP', '2093-3': 'Total Cholesterol',
    '2571-8': 'Triglycerides', '2085-9': 'HDL', '2089-1': 'LDL',
    '4548-4': 'HbA1c', '718-7': 'Hemoglobin', '4544-3': 'Hematocrit',
    '6690-2': 'WBC', '789-8': 'RBC', '777-3': 'Platelets',
    '6301-6': 'INR', '30341-2': 'ESR', '1988-5': 'CRP',
    '3016-3': 'TSH', '33914-3': 'eGFR', '2947-0': 'PSA',
}

# Medical stopwords
MEDICAL_STOPWORDS = {
    'patient', 'pt', 'the', 'a', 'an', 'is', 'was', 'were', 'are', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
    'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after',
    'between', 'out', 'off', 'over', 'under', 'again', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'no', 'not', 'only',
    'same', 'so', 'than', 'too', 'very', 'just', 'if', 'or', 'and', 'but',
    'because', 'until', 'while', 'noted', 'reports', 'denies', 'states',
    'presents', 'complains', 'approximately', 'about', 'also', 'well',
    'known', 'per', 'upon', 'seen', 'today', 'currently', 'previously',
    'mr', 'mrs', 'ms', 'dr', 'doctor', 'nurse', 'staff', 'being',
}


# ─────────────────────────────────────────────────────────────────────────────
# Data loader functions for JSON and XML
# ─────────────────────────────────────────────────────────────────────────────

def xml_to_dict(element):
    """Convert XML ElementTree to dictionary (recursive)"""
    result = {}
    
    # Add attributes
    if element.attrib:
        result['@attributes'] = element.attrib
    
    # Count child elements to determine if they should be lists
    child_counts = {}
    for child in element:
        child_counts[child.tag] = child_counts.get(child.tag, 0) + 1
    
    # Process children
    for child in element:
        child_text = child.text.strip() if child.text and child.text.strip() else ""
        
        if len(child) == 0:
            # Leaf node
            child_content = child_text
        else:
            # Node with children
            child_content = xml_to_dict(child)
        
        # Use lists for multiple elements
        is_list = child_counts[child.tag] > 1
        if is_list:
            if child.tag not in result:
                result[child.tag] = []
            result[child.tag].append(child_content)
        else:
            result[child.tag] = child_content
    
    return result if result else None


def flatten_json_to_dataframe(data):
    """Convert JSON (dict/list) to pandas DataFrame for tabular analysis"""
    if isinstance(data, list):
        # Already a list of records - convert nested structures to strings
        try:
            # Handle nested lists/dicts by converting to strings
            flattened = []
            for item in data:
                if isinstance(item, dict):
                    flat_item = {}
                    for k, v in item.items():
                        if isinstance(v, (list, dict)):
                            # Convert nested structures to string representation
                            flat_item[k] = json.dumps(v)
                        else:
                            flat_item[k] = v
                    flattened.append(flat_item)
                else:
                    flattened.append(item)
            return pd.DataFrame(flattened)
        except Exception:
            return pd.DataFrame({'data': [str(item) for item in data]})
    
    elif isinstance(data, dict):
        # Find list-like structures
        lists_found = {}
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                lists_found[key] = value
        
        if lists_found:
            # Use the first/largest list
            best_key = max(lists_found, key=lambda k: len(lists_found[k]))
            records = lists_found[best_key]
            try:
                # Handle nested structures
                flattened = []
                for item in records:
                    if isinstance(item, dict):
                        flat_item = {}
                        for k, v in item.items():
                            if isinstance(v, (list, dict)):
                                flat_item[k] = json.dumps(v)
                            else:
                                flat_item[k] = v
                        flattened.append(flat_item)
                    else:
                        flattened.append(item)
                return pd.DataFrame(flattened)
            except Exception:
                return pd.DataFrame({'data': [str(r) for r in records]})
        else:
            # Single record, convert to DataFrame
            try:
                return pd.DataFrame([data])
            except Exception:
                return pd.DataFrame(pd.json_normalize(data))
    
    return pd.DataFrame()


def load_json_file(filepath):
    """Load and parse JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def load_xml_file(filepath):
    """Load and parse XML file"""
    tree = ET.parse(filepath)
    root = tree.getroot()
    return xml_to_dict(root)


# ─────────────────────────────────────────────────────────────────────────────
# Data Analyzer
# ─────────────────────────────────────────────────────────────────────────────


class IntelligentSchemaMapper:
    """Suggest standard schema mappings using fuzzy string matching and aliases."""

    def __init__(self, schemas: dict):
        self.schemas = schemas

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', str(text).lower()).strip('_')

    def detect_domain(self, columns: list) -> str:
        column_text = ' '.join([self._normalize(col) for col in columns])
        healthcare_signals = ['patient', 'diagnosis', 'mrn', 'icd', 'clinical', 'hospital']
        if any(sig in column_text for sig in healthcare_signals):
            return 'healthcare'
        return 'general'

    def map_columns(self, columns: list, domain: str = None) -> dict:
        chosen_domain = domain or self.detect_domain(columns)
        domain_schema = self.schemas.get(chosen_domain, self.schemas['general'])

        suggestions = []
        for source_col in columns:
            source_norm = self._normalize(source_col)
            best_target = None
            best_score = 0.0
            best_reason = 'No close match found'

            for target, aliases in domain_schema.items():
                candidates = [target] + aliases
                for candidate in candidates:
                    candidate_norm = self._normalize(candidate)
                    score = SequenceMatcher(None, source_norm, candidate_norm).ratio()

                    if source_norm == candidate_norm:
                        score = 1.0

                    if score > best_score:
                        best_score = score
                        best_target = target
                        best_reason = f"Matched with '{candidate}'"

            if best_target and best_score >= 0.62:
                suggestions.append({
                    'source': source_col,
                    'suggested': best_target,
                    'confidence': round(best_score, 2),
                    'reason': best_reason
                })

        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return {
            'domain': chosen_domain,
            'suggestions': suggestions
        }


class DataAnalyzer:
    """Dataset analysis logic (ported from Tkinter app)"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.column_analysis = {}
    
    def get_overview(self) -> dict:
        """Get dataset overview statistics"""
        dtype_counts = {}
        for dtype in self.data.dtypes.value_counts().items():
            dtype_counts[str(dtype[0])] = int(dtype[1])
        
        return {
            'rows': int(self.data.shape[0]),
            'columns': int(self.data.shape[1]),
            'memory_usage_mb': round(self.data.memory_usage(deep=True).sum() / 1024**2, 2),
            'total_cells': int(self.data.size),
            'data_types': dtype_counts
        }
    
    def has_formatted_numbers(self, series: pd.Series) -> bool:
        """Check if series contains formatted numbers (commas, currency, etc.)"""
        if series.dtype != 'object':
            return False
        
        patterns = [r',', r'\$', r'%']
        for pattern in patterns:
            if series.astype(str).str.contains(pattern, na=False).any():
                return True
        return False
    
    def has_potential_dates(self, series: pd.Series) -> bool:
        """Check if series contains potential date strings"""
        if series.dtype != 'object':
            return False
        
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        ]
        
        for pattern in date_patterns:
            if series.astype(str).str.contains(pattern, na=False, flags=re.IGNORECASE).any():
                return True
        return False
    
    def has_mixed_types(self, series: pd.Series) -> bool:
        """Detect mixed data types in column"""
        if series.dtype != 'object':
            return False
        
        numeric_count = pd.to_numeric(series, errors='coerce').notna().sum()
        text_count = len(series) - numeric_count - series.isna().sum()
        
        return numeric_count > 0 and text_count > 0
    
    def has_special_characters(self, series: pd.Series) -> bool:
        """Check for special characters in text column"""
        if series.dtype != 'object':
            return False
        return series.str.contains(r'[^\w\s]', na=False).any()
    
    def get_quality_issues(self) -> list:
        """Analyze data quality issues"""
        issues = []
        
        # Data type issues
        for column in self.data.columns:
            col_data = self.data[column]
            
            # Detect formatted numbers
            if col_data.dtype == 'object' and self.has_formatted_numbers(col_data):
                issues.append({
                    'type': 'formatted_numbers',
                    'icon': '🔢',
                    'column': column,
                    'message': 'Contains formatted numbers (commas/currency)'
                })
            
            # Detect potential dates
            if col_data.dtype == 'object' and self.has_potential_dates(col_data):
                issues.append({
                    'type': 'date_strings',
                    'icon': '📅',
                    'column': column,
                    'message': 'Contains potential date strings'
                })
            
            # Detect mixed types
            if self.has_mixed_types(col_data):
                issues.append({
                    'type': 'mixed_types',
                    'icon': '🔄',
                    'column': column,
                    'message': 'Contains mixed data types'
                })
        
        # Missing values
        missing_values = self.data.isnull().sum()
        total_missing = int(missing_values.sum())
        if total_missing > 0:
            issues.append({
                'type': 'missing_header',
                'icon': '❌',
                'column': 'MISSING VALUES',
                'message': f'{total_missing} total missing cells'
            })
            
            for col in missing_values[missing_values > 0].index:
                count = int(missing_values[col])
                percent = round((count / len(self.data)) * 100, 1)
                issues.append({
                    'type': 'missing_value',
                    'icon': '📍',
                    'column': col,
                    'message': f'{count} missing ({percent}%)',
                    'indent': True
                })
        
        # Duplicate rows
        duplicate_rows = int(self.data.duplicated().sum())
        if duplicate_rows > 0:
            issues.append({
                'type': 'duplicates',
                'icon': '❌',
                'column': 'DUPLICATE ROWS',
                'message': f'{duplicate_rows} duplicate records'
            })
        
        # Column-specific issues
        for column in self.data.columns:
            col_data = self.data[column]
            col_issues = []
            
            # Special characters
            if col_data.dtype == 'object' and self.has_special_characters(col_data):
                col_issues.append('special characters')
            
            # Formatted numbers
            if col_data.dtype == 'object' and self.has_formatted_numbers(col_data):
                col_issues.append('formatted numbers (commas/currency)')
            
            # Potential dates
            if col_data.dtype == 'object' and self.has_potential_dates(col_data):
                col_issues.append('potential date strings')
            
            # Outliers for numeric columns
            if pd.api.types.is_numeric_dtype(col_data):
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                if IQR > 0:
                    outliers = col_data[(col_data < (Q1 - 1.5 * IQR)) | (col_data > (Q3 + 1.5 * IQR))]
                    if len(outliers) > 0:
                        issues.append({
                            'type': 'outliers',
                            'icon': '❌',
                            'column': column,
                            'message': f'{len(outliers)} outliers'
                        })
            
            if col_issues:
                issues.append({
                    'type': 'column_issues',
                    'icon': '❌',
                    'column': column,
                    'message': ', '.join(col_issues)
                })
        
        return issues
    
    def get_preview_data(self, num_rows: int = 100) -> dict:
        """Get preview data with quality indicators for interactive table"""
        # Get preview rows
        preview_rows = self.data.head(num_rows).replace({np.nan: None}).to_dict('records')
        
        # Calculate column-level quality scores
        quality_info = {}
        for col in self.data.columns:
            col_data = self.data[col]
            
            # Calculate quality score based on multiple factors
            missing_rate = (col_data.isnull().sum() / len(col_data)) * 100
            
            # Type consistency (1 type = good, mixed = bad)
            type_consistency = 100
            if col_data.dtype == 'object':
                if self.has_mixed_types(col_data):
                    type_consistency = 50
            
            # Outlier rate for numeric columns
            outlier_penalty = 0
            if pd.api.types.is_numeric_dtype(col_data):
                try:
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    outlier_rate = (z_scores > 3).sum() / len(col_data) * 100
                    outlier_penalty = min(outlier_rate * 2, 30)  # Max 30 point penalty
                except:
                    pass
            
            # Base score calculation
            quality_score = 100 - missing_rate
            quality_score = (quality_score + type_consistency) / 2  # Average with consistency
            quality_score = max(0, quality_score - outlier_penalty)
            
            quality_info[col] = {
                'quality_score': round(quality_score, 1),
                'missing_rate': round(missing_rate, 1),
                'type_consistency': round(type_consistency, 1)
            }
        
        return {
            'rows': preview_rows,
            'quality': quality_info,
            'total_rows': int(len(self.data))
        }
    
    def calculate_quality_score(self) -> dict:
        """Calculate comprehensive data quality score (0-100)"""
        scores = {}
        
        # 1. COMPLETENESS: % of non-null values
        total_cells = self.data.shape[0] * self.data.shape[1]
        non_null_cells = self.data.count().sum()
        completeness = (non_null_cells / total_cells) * 100 if total_cells > 0 else 100
        scores['completeness'] = round(completeness, 1)
        
        # 2. CONSISTENCY: Type consistency across columns
        type_consistent_cols = 0
        for col in self.data.columns:
            col_data = self.data[col]
            if col_data.dtype != 'object':
                type_consistent_cols += 1
            elif not self.has_mixed_types(col_data):
                type_consistent_cols += 1
        
        consistency = (type_consistent_cols / len(self.data.columns)) * 100 if len(self.data.columns) > 0 else 100
        scores['consistency'] = round(consistency, 1)
        
        # 3. VALIDITY: Data within expected ranges
        valid_data_points = 0
        total_data_points = 0
        
        for col in self.data.select_dtypes(include=[np.number]).columns:
            col_data = self.data[col].dropna()
            if len(col_data) > 0:
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                if IQR > 0:
                    lower_bound = Q1 - 3 * IQR
                    upper_bound = Q3 + 3 * IQR
                    in_range = col_data.between(lower_bound, upper_bound).sum()
                    valid_data_points += in_range
                    total_data_points += len(col_data)
                else:
                    valid_data_points += len(col_data)
                    total_data_points += len(col_data)
        
        validity = (valid_data_points / total_data_points * 100) if total_data_points > 0 else 100
        scores['validity'] = round(validity, 1)
        
        # 4. UNIQUENESS: Low duplicate rate
        duplicate_rate = (self.data.duplicated().sum() / len(self.data)) * 100 if len(self.data) > 0 else 0
        uniqueness = max(0, 100 - duplicate_rate)
        scores['uniqueness'] = round(uniqueness, 1)
        
        # 5. ACCURACY: Low outlier rate
        outlier_count = 0
        total_numeric_values = 0
        
        for col in self.data.select_dtypes(include=[np.number]).columns:
            col_data = self.data[col].dropna()
            if len(col_data) > 0:
                try:
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    outliers = (z_scores > 3).sum()
                    outlier_count += outliers
                    total_numeric_values += len(col_data)
                except:
                    pass
        
        accuracy = 100 - (outlier_count / total_numeric_values * 100) if total_numeric_values > 0 else 100
        scores['accuracy'] = round(accuracy, 1)
        
        # OVERALL SCORE (weighted average)
        weights = {
            'completeness': 0.25,
            'consistency': 0.20,
            'validity': 0.20,
            'uniqueness': 0.15,
            'accuracy': 0.20
        }
        
        overall = sum(scores[dim] * weights[dim] for dim in scores)
        scores['overall'] = round(overall, 1)
        
        return scores
    
    def generate_smart_recommendations(self) -> list:
        """
        Generate intelligent cleaning recommendations based on data analysis
        Returns prioritized list with confidence scores (Phase 3 Enhancement)
        """
        recommendations = []
        
        # Calculate key metrics
        total_rows = len(self.data)
        total_cols = len(self.data.columns)
        missing_percentage = (self.data.isnull().sum().sum() / (total_rows * total_cols)) * 100 if total_rows > 0 else 0
        duplicate_count = self.data.duplicated().sum()
        duplicate_percentage = (duplicate_count / total_rows) * 100 if total_rows > 0 else 0
        
        # RULE 1: Handle high missing data
        if missing_percentage > 20:
            recommendations.append({
                'priority': 'HIGH',
                'operation': 'handle_missing',
                'title': f'Handle {missing_percentage:.1f}% Missing Data',
                'reason': f'Dataset has significant missing values ({missing_percentage:.1f}% of all cells)',
                'suggested_config': {
                    'method': 'interpolate' if missing_percentage < 40 else 'drop_high_missing_rows',
                    'threshold': 0.5
                },
                'impact': f'Could improve data completeness by ~{min(missing_percentage * 0.7, 30):.0f}%',
                'confidence': 0.95
            })
            recommendations.append({
                'priority': 'MEDIUM',
                'operation': 'ml_impute_missing',
                'title': 'Use ML-Based Missing Value Imputation',
                'reason': 'Predictive imputation can preserve feature relationships better than simple median/mode filling',
                'suggested_config': {'method': 'random_forest'},
                'impact': 'Improves completeness while retaining statistical patterns',
                'confidence': 0.82
            })
        elif missing_percentage > 5:
            recommendations.append({
                'priority': 'MEDIUM',
                'operation': 'handle_missing',
                'title': f'Handle {missing_percentage:.1f}% Missing Data',
                'reason': f'Dataset has moderate missing values ({missing_percentage:.1f}%)',
                'suggested_config': {'method': 'auto', 'threshold': 0.5},
                'impact': f'Will improve data quality score by ~{min(missing_percentage * 0.5, 15):.0f} points',
                'confidence': 0.90
            })
        
        # RULE 2: Remove duplicates
        if duplicate_count > 0:
            priority = 'HIGH' if duplicate_percentage > 5 else 'MEDIUM'
            recommendations.append({
                'priority': priority,
                'operation': 'remove_duplicates',
                'title': f'Remove {duplicate_count} Duplicate Rows',
                'reason': f'Found {duplicate_count} duplicate rows ({duplicate_percentage:.1f}% of dataset)',
                'suggested_config': {'subset': None, 'keep': 'first'},
                'impact': f'Will reduce dataset size by {duplicate_percentage:.1f}% and ensure uniqueness',
                'confidence': 1.0
            })
        
        # RULE 3: Detect healthcare data
        healthcare_indicators = ['patient', 'diagnosis', 'icd', 'mrn', 'hospital', 'physician', 'medical', 'clinical']
        col_names_lower = ' '.join(self.data.columns).lower()
        is_healthcare = any(indicator in col_names_lower for indicator in healthcare_indicators)
        
        if is_healthcare:
            recommendations.append({
                'priority': 'HIGH',
                'operation': 'redact_phi',
                'title': 'Protect Patient Privacy (PHI Redaction)',
                'reason': 'Healthcare data detected - HIPAA compliance recommended for data sharing',
                'suggested_config': {
                    'redact_names': True,
                    'redact_ids': True,
                    'redact_dates': False
                },
                'impact': 'Ensures HIPAA compliance and protects patient privacy',
                'confidence': 0.85
            })
            
            recommendations.append({
                'priority': 'MEDIUM',
                'operation': 'standardize_codes',
                'title': 'Standardize Medical Codes',
                'reason': 'Map diagnosis codes to ICD-10 standard and expand abbreviations',
                'suggested_config': {
                    'map_icd10': True,
                    'spell_correct': True
                },
                'impact': 'Improves data interoperability and consistency with medical standards',
                'confidence': 0.90
            })
        
        # RULE 4: Check for outliers in numeric columns
        outlier_count = 0
        outlier_cols = []
        
        for col in self.data.select_dtypes(include=[np.number]).columns:
            col_data = self.data[col].dropna()
            if len(col_data) > 0:
                try:
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    col_outliers = (z_scores > 3).sum()
                    if col_outliers > 0:
                        outlier_count += col_outliers
                        outlier_cols.append(col)
                except:
                    pass
        
        outlier_percentage = (outlier_count / total_rows) * 100 if total_rows > 0 else 0
        
        if outlier_percentage > 5:
            recommendations.append({
                'priority': 'MEDIUM',
                'operation': 'handle_outliers',
                'title': f'Handle {outlier_count} Potential Outliers',
                'reason': f'Detected {outlier_percentage:.1f}% outliers in {len(outlier_cols)} numeric columns',
                'suggested_config': {'method': 'cap', 'threshold': 3},
                'impact': 'Reduces noise in numeric data and improves statistical analysis accuracy',
                'confidence': 0.75
            })
        
        # RULE 5: Text inconsistencies
        text_cols = self.data.select_dtypes(include=['object']).columns
        inconsistent_text_cols = []
        
        for col in text_cols[:10]:  # Check first 10 text columns
            sample = self.data[col].dropna().head(100)
            if len(sample) > 0:
                has_upper = any(str(val).isupper() for val in sample if len(str(val)) > 0)
                has_lower = any(str(val).islower() for val in sample if len(str(val)) > 0)
                has_mixed = any(' ' in str(val) and str(val) != str(val).lower() and str(val) != str(val).upper() 
                              for val in sample if len(str(val)) > 0)
                
                if (has_upper and has_lower) or has_mixed:
                    inconsistent_text_cols.append(col)
        
        if len(inconsistent_text_cols) > 0:
            recommendations.append({
                'priority': 'LOW',
                'operation': 'clean_text',
                'title': 'Standardize Text Formatting',
                'reason': f'Detected inconsistent text casing in {len(inconsistent_text_cols)} columns',
                'suggested_config': {
                    'lowercase': False,
                    'remove_whitespace': True,
                    'remove_special': False
                },
                'impact': 'Improves text consistency for analysis and comparisons',
                'confidence': 0.80
            })
        
        # RULE 6: Mixed data types
        mixed_type_cols = []
        for col in text_cols:
            if self.has_mixed_types(self.data[col]):
                mixed_type_cols.append(col)
        
        if len(mixed_type_cols) > 0:
            recommendations.append({
                'priority': 'HIGH',
                'operation': 'smart_type_conversion',
                'title': 'Convert Mixed Data Types',
                'reason': f'{len(mixed_type_cols)} columns contain mixed data types (numbers stored as text)',
                'suggested_config': {'method': 'auto'},
                'impact': 'Enables proper numeric operations and improves data processing efficiency',
                'confidence': 0.88
            })
        
        # RULE 7: Columns with >50% missing - recommend removal
        high_missing_cols = []
        for col in self.data.columns:
            missing_rate = (self.data[col].isnull().sum() / len(self.data)) * 100
            if missing_rate > 50:
                high_missing_cols.append((col, missing_rate))
        
        if len(high_missing_cols) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'operation': 'remove_high_missing',
                'title': f'Remove {len(high_missing_cols)} Low-Quality Columns',
                'reason': f'{len(high_missing_cols)} columns have >50% missing data and provide little value',
                'suggested_config': {'threshold': 0.5},
                'impact': f'Removes sparse columns, improving data density and processing speed',
                'confidence': 0.70
            })
        
        # Sort by priority and confidence
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        recommendations.sort(key=lambda x: (priority_order[x['priority']], -x['confidence']))
        
        return recommendations


# Routes

@app.route('/')
def index():
    """Serve the landing page"""
    return render_template('landing.html')


@app.route('/app')
def application_interface():
    """Serve the main application interface"""
    return render_template('index.html')


@app.route('/docs')
def documentation():
    """Serve the documentation page"""
    return render_template('docs.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and analysis (supports CSV, Excel, JSON, XML)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    
    try:
        # Parse file based on extension
        if file_ext == 'csv':
            data = pd.read_csv(file)
            data_type = 'CSV'
        
        elif file_ext in ('xlsx', 'xls'):
            data = pd.read_excel(file)
            data_type = 'Excel'
        
        elif file_ext == 'json':
            # Parse JSON and convert to DataFrame
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}.json")
            file.save(temp_path)
            json_data = load_json_file(temp_path)
            data = flatten_json_to_dataframe(json_data)
            data_type = 'JSON'
            os.remove(temp_path)
        
        elif file_ext == 'xml':
            # Parse XML and convert to DataFrame
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4()}.xml")
            file.save(temp_path)
            xml_data = load_xml_file(temp_path)
            data = flatten_json_to_dataframe(xml_data)
            data_type = 'XML'
            os.remove(temp_path)
        
        elif file_ext in ('txt', 'log', 'pdf', 'md', 'text', 'dat', 'rtf'):
            # Unstructured file detection
            if not UNSTRUCTURED_AVAILABLE:
                return jsonify({'error': 'Unstructured processor not available'}), 500
            
            # For analysis phase, we just extract basic info and a preview
            processor = UnstructuredDataProcessor()
            text, metadata = processor.extract_text(file_obj=file, filename=filename)
            
            # Store in unstructured_store with a new session ID
            session_id = str(uuid.uuid4())
            unstructured_store[session_id] = {
                'raw_text': text,
                'metadata': metadata,
                'is_unstructured': True
            }
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'filename': filename,
                'file_type': f'Unstructured ({file_ext.upper()})',
                'is_unstructured': True,
                'overview': {
                    'rows': metadata.get('line_count', 0),
                    'columns': 1,
                    'memory_usage_mb': round(len(text) / 1024**2, 2),
                    'total_cells': metadata.get('word_count', 0),
                    'data_types': {'text': 1}
                },
                'quality_issues': [
                    {'type': 'unstructured', 'icon': '📄', 'column': 'Text', 'message': f'Unstructured {file_ext.upper()} file detected. Use dedicated cleaning options.'}
                ],
                'preview': {
                    'rows': [{'Content': text[:500] + '...'}],
                    'total_rows': 1
                },
                'quality_score': {'overall': 100},  # Default for unstructured analysis
                'recommendations': [],
                'schema_mapping': {'domain': 'unstructured', 'suggestions': []}
            })
        
        else:
            return jsonify({
                'error': f'Unsupported file format (.{file_ext}). Supported: CSV, Excel, JSON, XML, TXT, LOG, PDF, MD.'
            }), 400
        
        # Validate we have data
        if data is None or data.empty:
            return jsonify({'error': 'File is empty or contains no valid data'}), 400
        
        # Generate session ID and store data
        session_id = str(uuid.uuid4())
        data_store[session_id] = data
        lineage_store[session_id] = {
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'filename': filename,
            'transformations': []
        }
        
        # Analyze the data
        analyzer = DataAnalyzer(data)
        overview = analyzer.get_overview()
        quality_issues = analyzer.get_quality_issues()
        preview_data = analyzer.get_preview_data(num_rows=100)
        quality_score = analyzer.calculate_quality_score()
        recommendations = analyzer.generate_smart_recommendations()
        schema_mapper = IntelligentSchemaMapper(STANDARD_SCHEMAS)
        schema_mapping = schema_mapper.map_columns(list(data.columns))
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'filename': filename,
            'file_type': data_type,
            'overview': overview,
            'quality_issues': quality_issues,
            'preview': preview_data,
            'quality_score': quality_score,
            'recommendations': recommendations,
            'schema_mapping': schema_mapping
        })
    
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
    
    except ET.ParseError as e:
        return jsonify({'error': f'Invalid XML format: {str(e)}'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500


@app.route('/api/columns/<session_id>')
def get_columns(session_id):
    """Get column information for a session"""
    if session_id not in data_store:
        return jsonify({'error': 'Session not found'}), 404
    
    data = data_store[session_id]
    columns = []
    
    for col in data.columns:
        columns.append({
            'name': col,
            'dtype': str(data[col].dtype),
            'non_null': int(data[col].notna().sum()),
            'null_count': int(data[col].isnull().sum())
        })
    
    return jsonify({'columns': columns})


@app.route('/api/schema-map/<session_id>')
def get_schema_mapping(session_id):
    """Get AI-powered schema mapping suggestions for a session."""
    if session_id not in data_store:
        return jsonify({'error': 'Session not found'}), 404

    mapper = IntelligentSchemaMapper(STANDARD_SCHEMAS)
    mapping = mapper.map_columns(list(data_store[session_id].columns))
    return jsonify({'success': True, 'schema_mapping': mapping})


@app.route('/api/lineage/<session_id>')
def get_lineage(session_id):
    """Return lineage information for latest cleaning run."""
    if session_id not in lineage_store:
        return jsonify({'error': 'Lineage not found for session'}), 404
    return jsonify({'success': True, 'lineage': lineage_store[session_id]})


@app.route('/api/demo/load', methods=['POST'])
def load_demo_dataset():
    """Load an in-memory demo dataset for quick walkthroughs and presentations."""
    demo_data = pd.DataFrame([
        {'Pt_Name': 'John  Doe', 'Age_Years': 52, 'Dx': 'diabeties', 'BP': '145/95', 'Visit_Date': '2026-02-01', 'Contact_No': '98765 43210'},
        {'Pt_Name': 'Mary Jane', 'Age_Years': np.nan, 'Dx': 'hypertention', 'BP': '170/110', 'Visit_Date': '2026-02-05', 'Contact_No': '91234 56789'},
        {'Pt_Name': 'Akash Rao', 'Age_Years': 67, 'Dx': 'COPD', 'BP': None, 'Visit_Date': '2026-02-10', 'Contact_No': 'akash@example.com'},
        {'Pt_Name': 'John  Doe', 'Age_Years': 52, 'Dx': 'diabetes mellitus type 2', 'BP': '145/95', 'Visit_Date': '2026-02-01', 'Contact_No': '98765 43210'},
        {'Pt_Name': 'Nina Patel', 'Age_Years': 41, 'Dx': 'asthma', 'BP': '120/80', 'Visit_Date': None, 'Contact_No': '9898989898'},
        {'Pt_Name': 'Ravi Shah', 'Age_Years': 77, 'Dx': 'heart attack', 'BP': '210/120', 'Visit_Date': '2026-02-12', 'Contact_No': 'ravi.shah@example.com'},
    ])

    session_id = str(uuid.uuid4())
    data_store[session_id] = demo_data
    lineage_store[session_id] = {
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'filename': 'demo_healthcare_dataset.csv',
        'transformations': []
    }

    analyzer = DataAnalyzer(demo_data)
    schema_mapper = IntelligentSchemaMapper(STANDARD_SCHEMAS)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'filename': 'demo_healthcare_dataset.csv',
        'file_type': 'DEMO',
        'overview': analyzer.get_overview(),
        'quality_issues': analyzer.get_quality_issues(),
        'preview': analyzer.get_preview_data(num_rows=100),
        'quality_score': analyzer.calculate_quality_score(),
        'recommendations': analyzer.generate_smart_recommendations(),
        'schema_mapping': schema_mapper.map_columns(list(demo_data.columns))
    })


class DataCleaner:
    """Data cleaning operations — all 11 from v0.0.7"""
    
    def __init__(self, data: pd.DataFrame):
        self.original_data = data.copy()
        self.data = data.copy()
        self.operations_performed = []
        self.lineage = {
            'started_at': datetime.utcnow().isoformat() + 'Z',
            'transformations': []
        }
    
    def calculate_quality_scores(self, data: pd.DataFrame) -> dict:
        """Calculate quality metrics for a dataset"""
        total_cells = data.size
        missing_cells = data.isnull().sum().sum()
        filled_cells = total_cells - missing_cells
        
        # Completeness: percentage of non-null cells
        completeness = round((filled_cells / total_cells) * 100, 1) if total_cells > 0 else 0
        
        # Consistency: check for duplicates and mixed types
        duplicate_rows = data.duplicated().sum()
        consistency_penalty = (duplicate_rows / len(data)) * 50 if len(data) > 0 else 0
        consistency = max(0, round(100 - consistency_penalty, 1))
        
        # Overall: weighted average
        overall = round((completeness * 0.6 + consistency * 0.4), 1)
        
        return {
            'completeness': completeness,
            'consistency': consistency,
            'overall': overall
        }

    def _snapshot_metrics(self) -> dict:
        """Capture compact metrics used in lineage and comparison."""
        return {
            'rows': int(len(self.data)),
            'columns': int(len(self.data.columns)),
            'missing_cells': int(self.data.isnull().sum().sum()),
            'duplicate_rows': int(self.data.duplicated().sum())
        }

    def _record_lineage_step(self, operation: str, config: dict, before: dict, after: dict):
        """Append one transformation step to lineage."""
        self.lineage['transformations'].append({
            'step': len(self.lineage['transformations']) + 1,
            'operation': operation,
            'config': config,
            'before': before,
            'after': after,
            'rows_affected': before['rows'] - after['rows'],
            'missing_reduced': before['missing_cells'] - after['missing_cells'],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    def ml_based_missing_imputation(self):
        """Impute missing values using model-based prediction with fallback."""
        total_imputed = 0

        for target_col in self.data.columns:
            missing_mask = self.data[target_col].isna()
            missing_count = int(missing_mask.sum())
            if missing_count == 0:
                continue

            feature_cols = [c for c in self.data.columns if c != target_col]
            if not feature_cols:
                continue

            encoded = self.data.copy()
            for col in encoded.columns:
                if encoded[col].dtype == 'object':
                    encoded[col] = encoded[col].astype(str)
                    encoded[col] = pd.factorize(encoded[col])[0]

            train_df = encoded[~missing_mask]
            pred_df = encoded[missing_mask]

            if train_df.empty or pred_df.empty:
                continue

            X_train = train_df[feature_cols].fillna(0)
            X_pred = pred_df[feature_cols].fillna(0)
            y_train = train_df[target_col]

            # For very small training data, fallback to robust statistics.
            if len(train_df) < 20:
                if pd.api.types.is_numeric_dtype(self.data[target_col]):
                    fill_value = self.data[target_col].median()
                else:
                    mode = self.data[target_col].mode()
                    fill_value = mode.iloc[0] if len(mode) > 0 else 'Unknown'
                self.data.loc[missing_mask, target_col] = fill_value
                total_imputed += missing_count
                continue

            if SKLEARN_AVAILABLE:
                try:
                    if pd.api.types.is_numeric_dtype(self.data[target_col]):
                        model = RandomForestRegressor(n_estimators=80, random_state=42)
                    else:
                        y_train = y_train.astype(str)
                        model = RandomForestClassifier(n_estimators=80, random_state=42)

                    model.fit(X_train, y_train)
                    predictions = model.predict(X_pred)
                    self.data.loc[missing_mask, target_col] = predictions
                    total_imputed += missing_count
                    continue
                except Exception:
                    pass

            # Fallback path when sklearn unavailable or model fit fails.
            if pd.api.types.is_numeric_dtype(self.data[target_col]):
                fill_value = self.data[target_col].median()
            else:
                mode = self.data[target_col].mode()
                fill_value = mode.iloc[0] if len(mode) > 0 else 'Unknown'
            self.data.loc[missing_mask, target_col] = fill_value
            total_imputed += missing_count

        if total_imputed > 0:
            algo = 'RandomForest-based' if SKLEARN_AVAILABLE else 'statistical fallback'
            self.operations_performed.append({
                'icon': '🤖',
                'text': f'ML imputation filled {total_imputed} values ({algo})'
            })
    
    # ──────────────────────────────────────────────
    # 1. SMART TYPE CONVERSION
    # ──────────────────────────────────────────────
    def smart_type_conversion(self):
        """Convert data types automatically"""
        # Keywords that indicate numeric columns (currency, amounts, counts)
        numeric_keywords = ['amount', 'price', 'cost', 'bill', 'salary', 'fee', 'rate', 
                          'count', 'total', 'value', 'quantity', 'qty', 'age', 'percent']
        # Keywords that indicate date columns
        date_keywords = ['date', 'time', 'created', 'updated', 'joined', 'birth', 'admission']
        # Common null-like values to replace with NaN
        null_values = ['unknown', 'n/a', 'na', 'none', 'tbd', '########', 'null', 'n/a', 'undefined']
        
        for col in self.data.columns:
            col_lower = col.lower()
            
            if self.data[col].dtype == 'object':
                # STEP 1: Replace null-like values with NaN
                self.data[col] = self.data[col].astype(str).str.lower().replace(null_values, pd.NA)
                
                # PRIORITY 1: Check if column name suggests numeric type
                is_numeric_col = any(keyword in col_lower for keyword in numeric_keywords)
                is_date_col = any(keyword in col_lower for keyword in date_keywords)
                
                # Try numeric conversion
                numeric = pd.to_numeric(
                    self.data[col].astype(str).str.replace(',', '').str.replace('$', '').str.replace('%', ''),
                    errors='coerce'
                )
                numeric_success = numeric.notna().mean() > 0.7
                
                if is_numeric_col and numeric_success:
                    # Column name suggests numeric AND conversion successful
                    self.data[col] = numeric
                    self.operations_performed.append({'icon': '🔢', 'text': f'{col}: string → numeric'})
                    continue
                
                # Try datetime conversion
                if not is_numeric_col:  # Skip datetime if column name suggests numeric
                    try:
                        dates = pd.to_datetime(self.data[col], errors='coerce')
                        if dates.notna().mean() > 0.7:
                            self.data[col] = dates
                            self.operations_performed.append({'icon': '📅', 'text': f'{col}: string → datetime'})
                            continue
                    except Exception:
                        pass
                
                # Fallback: If nothing worked but numeric was successful, use numeric
                if numeric_success and not is_date_col:
                    self.data[col] = numeric
                    self.operations_performed.append({'icon': '🔢', 'text': f'{col}: string → numeric'})
    
    # ──────────────────────────────────────────────
    # 2. HANDLE MISSING VALUES
    # ──────────────────────────────────────────────
    def handle_missing(self, method='auto'):
        """Handle missing values"""
        total_filled = 0
        for col in self.data.columns:
            missing_count = self.data[col].isnull().sum()
            if missing_count > 0:
                if method == 'remove':
                    self.data = self.data.dropna(subset=[col])
                elif method == 'fill_median' and pd.api.types.is_numeric_dtype(self.data[col]):
                    self.data[col] = self.data[col].fillna(self.data[col].median())
                    total_filled += missing_count
                elif method == 'fill_mode':
                    self.data[col] = self.data[col].fillna(
                        self.data[col].mode().iloc[0] if len(self.data[col].mode()) > 0 else 0
                    )
                    total_filled += missing_count
                elif method == 'auto':
                    if pd.api.types.is_numeric_dtype(self.data[col]):
                        self.data[col] = self.data[col].fillna(self.data[col].median())
                    else:
                        mode = self.data[col].mode()
                        self.data[col] = self.data[col].fillna(
                            mode.iloc[0] if len(mode) > 0 else 'Unknown'
                        )
                    total_filled += missing_count
        
        if total_filled > 0:
            self.operations_performed.append({'icon': '✅', 'text': f'Filled {total_filled} missing values using {method}'})
    
    # ──────────────────────────────────────────────
    # 3. REMOVE DUPLICATES
    # ──────────────────────────────────────────────
    def remove_duplicates(self):
        """Remove duplicate rows"""
        before_count = len(self.data)
        self.data = self.data.drop_duplicates()
        removed = before_count - len(self.data)
        if removed > 0:
            self.operations_performed.append({'icon': '🗑️', 'text': f'Removed {removed} duplicate rows'})
    
    # ──────────────────────────────────────────────
    # 4. FEATURE ENGINEERING
    # ──────────────────────────────────────────────
    def feature_engineering(self):
        """Create derived features (date parts, text features, numeric binning)"""
        new_features_count = 0
        
        for col in list(self.data.columns):
            col_data = self.data[col]
            
            # Date features
            if pd.api.types.is_datetime64_any_dtype(col_data):
                self.data[f'{col}_year'] = col_data.dt.year
                self.data[f'{col}_month'] = col_data.dt.month
                self.data[f'{col}_day'] = col_data.dt.day
                self.data[f'{col}_dayofweek'] = col_data.dt.dayofweek
                new_features_count += 4
                self.operations_performed.append({'icon': '📅', 'text': f'Created date features from {col}'})
                
                # Age calculation for birth dates
                if any(kw in col.lower() for kw in ['birth', 'dob']):
                    self.data[f'{col}_age'] = (pd.Timestamp.now() - col_data).dt.days // 365
                    new_features_count += 1
                    self.operations_performed.append({'icon': '🎂', 'text': f'Created age from {col}'})
            
            # Text features
            elif col_data.dtype == 'object':
                self.data[f'{col}_length'] = col_data.astype(str).str.len()
                self.data[f'{col}_word_count'] = col_data.astype(str).str.split().str.len()
                new_features_count += 2
                
                # Email domain extraction
                if col_data.str.contains('@', na=False).any():
                    self.data[f'{col}_domain'] = col_data.str.split('@').str[1]
                    new_features_count += 1
                    self.operations_performed.append({'icon': '📧', 'text': f'Extracted email domains from {col}'})
                
                # Categorical encoding for low cardinality
                unique_count = col_data.nunique()
                if 2 <= unique_count <= 10:
                    self.data[f'{col}_encoded'] = pd.factorize(col_data)[0]
                    new_features_count += 1
                    self.operations_performed.append({'icon': '🔤', 'text': f'Encoded {col} ({unique_count} categories)'})
                
                self.operations_performed.append({'icon': '📝', 'text': f'Created text features from {col}'})
            
            # Numeric features
            elif pd.api.types.is_numeric_dtype(col_data):
                # Binning for high-cardinality numerics
                if col_data.nunique() > 10:
                    try:
                        self.data[f'{col}_binned'] = pd.cut(col_data, bins=5, labels=False)
                        new_features_count += 1
                        self.operations_performed.append({'icon': '📊', 'text': f'Binned {col} into 5 categories'})
                    except Exception:
                        pass
                
                # Log transformation for skewed data
                if col_data.min() > 0:
                    skewness = col_data.skew()
                    if abs(skewness) > 1:
                        self.data[f'{col}_log'] = np.log1p(col_data)
                        new_features_count += 1
                        self.operations_performed.append({'icon': '📈', 'text': f'Log transform {col} (skew: {skewness:.2f})'})
        
        if new_features_count > 0:
            self.operations_performed.append({'icon': '✅', 'text': f'Created {new_features_count} derived features total'})
    
    # ──────────────────────────────────────────────
    # 5. CLEAN TEXT
    # ──────────────────────────────────────────────
    def clean_text(self):
        """Clean text formatting (whitespace, title case for low-cardinality)"""
        for col in self.data.select_dtypes(include=['object']).columns:
            # Remove extra whitespace
            self.data[col] = self.data[col].astype(str).str.strip()
            self.data[col] = self.data[col].str.replace(r'\s+', ' ', regex=True)
            
            # Fix case inconsistencies for categorical text
            if self.data[col].nunique() < 50:
                self.data[col] = self.data[col].str.title()
            
            self.operations_performed.append({'icon': '✨', 'text': f'Cleaned text in {col}'})
    
    # ──────────────────────────────────────────────
    # 6. HANDLE OUTLIERS
    # ──────────────────────────────────────────────
    def handle_outliers(self, method='cap'):
        """Handle outliers in numeric columns"""
        for col in self.data.select_dtypes(include=[np.number]).columns:
            Q1 = self.data[col].quantile(0.25)
            Q3 = self.data[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR > 0:
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                outliers = ((self.data[col] < lower) | (self.data[col] > upper)).sum()
                
                if outliers > 0:
                    if method == 'cap':
                        self.data[col] = self.data[col].clip(lower, upper)
                        self.operations_performed.append({'icon': '📏', 'text': f'Capped {outliers} outliers in {col}'})
                    elif method == 'remove':
                        self.data = self.data[(self.data[col] >= lower) & (self.data[col] <= upper)]
                        self.operations_performed.append({'icon': '🗑️', 'text': f'Removed {outliers} outlier rows from {col}'})
    
    # ──────────────────────────────────────────────
    # 7. REMOVE HIGH MISSING COLUMNS
    # ──────────────────────────────────────────────
    def remove_high_missing(self, threshold=0.5):
        """Remove columns with more than threshold% missing values"""
        missing_pct = self.data.isnull().mean()
        high_missing = missing_pct[missing_pct > threshold].index.tolist()
        
        if high_missing:
            self.data = self.data.drop(columns=high_missing)
            for col in high_missing:
                self.operations_performed.append(
                    {'icon': '🗑️', 'text': f"Removed column '{col}' ({missing_pct[col]*100:.1f}% missing)"}
                )
    
    # ──────────────────────────────────────────────
    # 8. REDACT PHI (Enhanced)
    # ──────────────────────────────────────────────
    def redact_phi(self):
        """Auto-redact Protected Health Information
        Detects and masks: emails, phones (US + India), Aadhaar numbers,
        SSNs, hospital/MRN IDs, names, and addresses.
        """
        phi_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            'phone_in': r'\b[6-9]\d{9}\b',  # Indian 10-digit mobile
            'phone_in_spaced': r'\b[6-9]\d{4}[\s-]\d{5}\b',  # Indian spaced format
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'aadhaar': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Indian Aadhaar (12-digit)
            'hospital_id': r'\b(?:MRN|HID|PAT|UHID)[-.\s]?\d{4,10}\b',  # Hospital IDs like MRN-12345
        }
        
        # Extended column-name keywords for PHI detection
        phi_column_keywords = [
            'name', 'patient_name', 'first_name', 'last_name', 'full_name',
            'address', 'street', 'city', 'zip', 'pincode', 'postal',
            'phone', 'mobile', 'contact', 'telephone', 'cell',
            'email', 'e_mail', 'email_address',
            'ssn', 'social_security', 'aadhaar', 'aadhar', 'uid',
            'mrn', 'patient_id', 'medical_record', 'uhid', 'hospital_id',
            'dob', 'date_of_birth', 'birth_date',
            'insurance_id', 'policy_number', 'beneficiary',
        ]
        
        total_redacted = 0
        
        for col in self.data.columns:
            col_lower = col.lower().replace(' ', '_')
            
            # Column-name based redaction (catches obvious PHI columns)
            if any(kw in col_lower for kw in phi_column_keywords):
                original_count = self.data[col].notna().sum()
                self.data[col] = '[REDACTED_PHI]'
                total_redacted += int(original_count)
                self.operations_performed.append(
                    {'icon': '🔒', 'text': f'Redacted PHI column: {col} ({original_count} values)'}
                )
                continue
            
            # Pattern-based redaction on text columns
            if self.data[col].dtype == 'object':
                col_str = self.data[col].astype(str)
                for pattern_name, pattern in phi_patterns.items():
                    matches = col_str.str.contains(pattern, na=False, flags=re.IGNORECASE)
                    match_count = int(matches.sum())
                    if match_count > 0:
                        self.data[col] = col_str.str.replace(
                            pattern, f'[REDACTED_{pattern_name.upper()}]', regex=True, flags=re.IGNORECASE
                        )
                        col_str = self.data[col].astype(str)  # refresh for next pattern
                        total_redacted += match_count
                        self.operations_performed.append(
                            {'icon': '🔒', 'text': f'Redacted {match_count} {pattern_name} patterns in {col}'}
                        )
        
        if total_redacted > 0:
            self.operations_performed.append(
                {'icon': '✅', 'text': f'Total PHI redactions: {total_redacted} values protected'}
            )
    
    # ──────────────────────────────────────────────
    # 9. VALIDATE CLINICAL RANGES
    # ──────────────────────────────────────────────
    def validate_clinical(self):
        """Validate clinical measurement ranges"""
        clinical_ranges = {
            'heart_rate': (40, 200),
            'systolic_bp': (70, 250),
            'diastolic_bp': (40, 150),
            'temperature': (35, 42),
            'spo2': (70, 100),
        }
        
        for col in self.data.select_dtypes(include=[np.number]).columns:
            col_lower = col.lower()
            for param, (min_val, max_val) in clinical_ranges.items():
                if param in col_lower:
                    invalid = self.data[(self.data[col] < min_val) | (self.data[col] > max_val)]
                    if len(invalid) > 0:
                        self.operations_performed.append(
                            {'icon': '⚕️', 'text': f'Found {len(invalid)} values outside clinical range in {col}'}
                        )
                    break
    
    # ──────────────────────────────────────────────
    # 10. STANDARDIZE MEDICAL CODES (Enhanced)
    # ──────────────────────────────────────────────
    def standardize_codes(self):
        """Standardize medical coding systems (ICD-10, CPT, LOINC)
        - Maps free-text disease names to ICD-10 codes
        - Validates ICD-10 format
        - Normalizes code formatting
        - Validates LOINC codes against known list
        - Zero-pads CPT codes
        """
        for col in self.data.columns:
            col_lower = col.lower()
            
            # ICD-10 code columns
            if any(kw in col_lower for kw in ['icd', 'diagnosis', 'diagnosis_code', 'dx_code']):
                standardized = 0
                mapped_from_text = 0
                fuzzy_matched = 0
                invalid_codes = 0
                _disease_names_list = list(DISEASE_TO_ICD10.keys())  # cache for fuzzy search
                
                def standardize_icd_value(val):
                    nonlocal standardized, mapped_from_text, fuzzy_matched, invalid_codes
                    val_str = str(val).strip()
                    if val_str in ('nan', '', 'None', 'NaN'):
                        return val_str
                    
                    # Try direct ICD-10 format normalization
                    cleaned = val_str.upper().replace(' ', '').replace('.', '')
                    if ICD10_PATTERN.match(cleaned):
                        # Valid ICD-10 format — normalize to standard format (e.g., E119 → E11.9)
                        if len(cleaned) > 3:
                            cleaned = cleaned[:3] + '.' + cleaned[3:]
                        standardized += 1
                        return cleaned
                    
                    # Try mapping free-text disease name to ICD-10
                    val_lower = val_str.lower().strip()
                    # First correct any misspellings
                    for wrong, right in MEDICAL_SPELL_CORRECTIONS.items():
                        val_lower = val_lower.replace(wrong, right)
                    
                    if val_lower in DISEASE_TO_ICD10:
                        mapped_from_text += 1
                        code = DISEASE_TO_ICD10[val_lower]
                        return code
                    
                    # Try partial match (e.g., "type 2 diabetes mellitus unspecified")
                    for disease_name, code in sorted(DISEASE_TO_ICD10.items(), key=lambda x: len(x[0]), reverse=True):
                        if disease_name in val_lower:
                            mapped_from_text += 1
                            return code
                    
                    # Fuzzy match using thefuzz (Levenshtein distance)
                    if THEFUZZ_AVAILABLE and _disease_names_list:
                        result = fuzz_process.extractOne(val_lower, _disease_names_list, scorer=fuzz.ratio, score_cutoff=80)
                        if result:
                            best_match, score = result[0], result[1]
                            fuzzy_matched += 1
                            code = DISEASE_TO_ICD10[best_match]
                            return code
                    
                    # Could not map — flag as unrecognized
                    invalid_codes += 1
                    return val_str.upper()
                
                self.data[col] = self.data[col].apply(standardize_icd_value)
                
                if standardized > 0:
                    self.operations_performed.append(
                        {'icon': '🏥', 'text': f'Normalized {standardized} ICD-10 codes in {col}'}
                    )
                if mapped_from_text > 0:
                    self.operations_performed.append(
                        {'icon': '🔄', 'text': f'Mapped {mapped_from_text} disease names → ICD-10 codes in {col}'}
                    )
                if fuzzy_matched > 0:
                    self.operations_performed.append(
                        {'icon': '🔍', 'text': f'Fuzzy-matched {fuzzy_matched} disease names → ICD-10 codes in {col} (Levenshtein ≥80%)'}
                    )
                if invalid_codes > 0:
                    self.operations_performed.append(
                        {'icon': '⚠️', 'text': f'{invalid_codes} unrecognized codes in {col} (kept as-is)'}
                    )
            
            # Disease name / condition columns (map to ICD-10)
            elif any(kw in col_lower for kw in ['disease', 'condition', 'illness', 'disorder', 'comorbidity']):
                mapped_count = 0
                corrected_count = 0
                fuzzy_corrected = 0
                _disease_names_list = list(DISEASE_TO_ICD10.keys())  # cache for fuzzy search
                
                def normalize_disease_name(val):
                    nonlocal mapped_count, corrected_count, fuzzy_corrected
                    val_str = str(val).strip()
                    if val_str in ('nan', '', 'None', 'NaN'):
                        return val_str
                    
                    val_lower = val_str.lower()
                    
                    # Spell correction
                    for wrong, right in MEDICAL_SPELL_CORRECTIONS.items():
                        if wrong in val_lower:
                            val_lower = val_lower.replace(wrong, right)
                            corrected_count += 1
                    
                    # Normalize to standard terminology
                    if val_lower in DISEASE_TO_ICD10:
                        mapped_count += 1
                        return val_lower.title()
                    
                    # Fuzzy match using thefuzz (Levenshtein distance)
                    if THEFUZZ_AVAILABLE and _disease_names_list:
                        result = fuzz_process.extractOne(val_lower, _disease_names_list, scorer=fuzz.ratio, score_cutoff=80)
                        if result:
                            best_match, score = result[0], result[1]
                            fuzzy_corrected += 1
                            return best_match.title()
                    
                    return val_lower.title()
                
                self.data[col] = self.data[col].apply(normalize_disease_name)
                
                if corrected_count > 0:
                    self.operations_performed.append(
                        {'icon': '✏️', 'text': f'Spell-corrected {corrected_count} disease names in {col}'}
                    )
                if mapped_count > 0:
                    self.operations_performed.append(
                        {'icon': '🏥', 'text': f'Standardized {mapped_count} disease terms in {col}'}
                    )
                if fuzzy_corrected > 0:
                    self.operations_performed.append(
                        {'icon': '🔍', 'text': f'Fuzzy-corrected {fuzzy_corrected} disease names in {col} (Levenshtein ≥80%)'}
                    )
            
            # CPT codes
            elif any(kw in col_lower for kw in ['cpt', 'procedure', 'procedure_code']):
                self.data[col] = self.data[col].astype(str).str.strip().str.zfill(5)
                self.operations_performed.append({'icon': '🏥', 'text': f'Standardized CPT codes in {col}'})
            
            # LOINC codes
            elif any(kw in col_lower for kw in ['loinc', 'lab_code', 'test_code']):
                valid_count = 0
                invalid_count = 0
                
                for idx, val in self.data[col].items():
                    val_str = str(val).strip()
                    if val_str in ('nan', '', 'None'):
                        continue
                    if val_str in COMMON_LOINC_CODES:
                        valid_count += 1
                    else:
                        invalid_count += 1
                
                self.operations_performed.append(
                    {'icon': '🧪', 'text': f'LOINC validation in {col}: {valid_count} valid, {invalid_count} unrecognized'}
                )
    
    # ──────────────────────────────────────────────
    # 11. VALIDATE NUMERIC RANGES
    # ──────────────────────────────────────────────
    def validate_ranges(self):
        """Validate and clip numeric columns to reasonable ranges (3×IQR)"""
        for col in self.data.select_dtypes(include=[np.number]).columns:
            col_data = self.data[col].dropna()
            if len(col_data) == 0:
                continue
            
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR > 0:
                lower = Q1 - 3 * IQR
                upper = Q3 + 3 * IQR
                invalid = self.data[(self.data[col] < lower) | (self.data[col] > upper)]
                if len(invalid) > 0:
                    self.data[col] = self.data[col].clip(lower=lower, upper=upper)
                    self.operations_performed.append(
                        {'icon': '📐', 'text': f"Clipped {len(invalid)} values in '{col}' to [{lower:.1f}, {upper:.1f}]"}
                    )
    
    # ──────────────────────────────────────────────
    # 12. NORMALIZE CLINICAL TEXT (New)
    # ──────────────────────────────────────────────
    def normalize_clinical_text(self):
        """Advanced clinical text normalization
        - Expands medical abbreviations (BP → Blood Pressure)
        - Corrects common medical misspellings
        - Removes medical stopwords (optional)
        - Normalizes terminology
        """
        abbrev_expanded = 0
        spells_corrected = 0
        
        # Columns to SKIP — not medical text
        skip_keywords = [
            'country', 'region', 'state', 'province', 'city', 'district', 'county',
            'nation', 'territory', 'location', 'place', 'area', 'zone',
            'name', 'first_name', 'last_name', 'full_name',
            'date', 'time', 'timestamp', 'update', 'created', 'modified',
            'id', 'code', 'key', 'index', 'sno', 's_no', 'serial',
            'email', 'phone', 'address', 'url', 'link', 'path', 'file',
            'lat', 'lon', 'latitude', 'longitude', 'geo', 'zip', 'pincode',
        ]
        
        for col in self.data.select_dtypes(include=['object']).columns:
            col_lower = col.lower().replace(' ', '_')
            
            # Skip non-medical columns
            if any(kw in col_lower for kw in skip_keywords):
                continue
            
            # Skip columns that were already redacted
            if self.data[col].astype(str).str.contains('REDACTED', na=False).any():
                continue
            
            for idx in self.data.index:
                val = str(self.data.at[idx, col])
                if val in ('nan', '', 'None', 'NaN', '[REDACTED_PHI]'):
                    continue
                
                original_val = val
                
                # Step 1: Expand medical abbreviations
                # Split into words, expand known abbreviations
                words = val.split()
                expanded_words = []
                for word in words:
                    word_clean = word.strip('.,;:!?()').lower()
                    if word_clean in MEDICAL_ABBREVIATIONS:
                        expanded_words.append(MEDICAL_ABBREVIATIONS[word_clean])
                        abbrev_expanded += 1
                    else:
                        expanded_words.append(word)
                val = ' '.join(expanded_words)
                
                # Step 2: Correct medical misspellings
                val_lower = val.lower()
                for wrong, right in MEDICAL_SPELL_CORRECTIONS.items():
                    if wrong in val_lower:
                        val = re.sub(re.escape(wrong), right, val, flags=re.IGNORECASE)
                        spells_corrected += 1
                
                if val != original_val:
                    self.data.at[idx, col] = val
        
        if abbrev_expanded > 0:
            self.operations_performed.append(
                {'icon': '📖', 'text': f'Expanded {abbrev_expanded} medical abbreviations'}
            )
        if spells_corrected > 0:
            self.operations_performed.append(
                {'icon': '✏️', 'text': f'Corrected {spells_corrected} medical misspellings'}
            )
    
    # ──────────────────────────────────────────────
    # VALIDATION REPORT GENERATOR
    # ──────────────────────────────────────────────
    def generate_validation_report(self, before_scores: dict, after_scores: dict) -> dict:
        """Generate a structured JSON validation report summarizing all cleaning actions.
        Parses self.operations_performed to extract counts per category."""
        report = {
            'total_operations': len(self.operations_performed),
            'phi_redactions': {'total': 0},
            'type_conversions': {'date_columns': 0, 'numeric_columns': 0},
            'missing_values_handled': 0,
            'duplicates_removed': 0,
            'icd10_mappings': {'exact': 0, 'fuzzy': 0, 'unrecognized': 0},
            'text_corrections': {'abbreviations_expanded': 0, 'misspellings_fixed': 0},
            'outliers_clipped': 0,
            'clinical_validations': 0,
            'overall_quality': {
                'before': before_scores.get('overall', 0),
                'after': after_scores.get('overall', 0)
            }
        }
        
        for op in self.operations_performed:
            text = op.get('text', '')
            text_lower = text.lower()
            
            # PHI Redactions
            if 'redact' in text_lower or 'phi' in text_lower:
                import re as _re
                count_match = _re.search(r'(\d+)', text)
                count = int(count_match.group(1)) if count_match else 1
                report['phi_redactions']['total'] += count
                # Try to identify the PHI type from the text
                for phi_type in ['ssn', 'email', 'phone', 'aadhaar', 'mrn', 'address', 'name']:
                    if phi_type in text_lower:
                        report['phi_redactions'][phi_type] = report['phi_redactions'].get(phi_type, 0) + count
            
            # Type conversions
            elif 'converted' in text_lower and 'date' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['type_conversions']['date_columns'] += int(count_match.group(1)) if count_match else 1
            elif 'converted' in text_lower and ('numeric' in text_lower or 'number' in text_lower):
                count_match = re.search(r'(\d+)', text)
                report['type_conversions']['numeric_columns'] += int(count_match.group(1)) if count_match else 1
            
            # Missing values
            elif 'missing' in text_lower or 'imput' in text_lower or 'filled' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['missing_values_handled'] += int(count_match.group(1)) if count_match else 0
            
            # Duplicates
            elif 'duplicate' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['duplicates_removed'] += int(count_match.group(1)) if count_match else 0
            
            # ICD-10 mappings
            elif 'fuzzy-matched' in text_lower or 'fuzzy-corrected' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['icd10_mappings']['fuzzy'] += int(count_match.group(1)) if count_match else 0
            elif 'mapped' in text_lower and 'icd' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['icd10_mappings']['exact'] += int(count_match.group(1)) if count_match else 0
            elif 'normalized' in text_lower and 'icd' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['icd10_mappings']['exact'] += int(count_match.group(1)) if count_match else 0
            elif 'unrecognized' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['icd10_mappings']['unrecognized'] += int(count_match.group(1)) if count_match else 0
            
            # Text corrections
            elif 'abbreviation' in text_lower or 'expanded' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['text_corrections']['abbreviations_expanded'] += int(count_match.group(1)) if count_match else 0
            elif 'spell' in text_lower or 'misspelling' in text_lower or 'corrected' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['text_corrections']['misspellings_fixed'] += int(count_match.group(1)) if count_match else 0
            
            # Outliers
            elif 'clip' in text_lower or 'outlier' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['outliers_clipped'] += int(count_match.group(1)) if count_match else 0
            
            # Clinical validations
            elif 'clinical range' in text_lower:
                count_match = re.search(r'(\d+)', text)
                report['clinical_validations'] += int(count_match.group(1)) if count_match else 0
        
        # Add fuzzy matching availability status
        report['fuzzy_matching_available'] = THEFUZZ_AVAILABLE
        
        return report
    
    # ──────────────────────────────────────────────
    # MAIN CLEAN DISPATCHER
    # ──────────────────────────────────────────────
    def clean(self, operations: dict, operation_sequence: list = None) -> dict:
        """Execute cleaning operations, honoring user pipeline order when provided."""
        operation_handlers = {
            'smart_type_conversion': lambda cfg: self.smart_type_conversion(),
            'handle_missing': lambda cfg: self.handle_missing(cfg.get('method', 'auto')),
            'remove_duplicates': lambda cfg: self.remove_duplicates(),
            'feature_engineering': lambda cfg: self.feature_engineering(),
            'clean_text': lambda cfg: self.clean_text(),
            'handle_outliers': lambda cfg: self.handle_outliers(cfg.get('method', 'cap')),
            'remove_high_missing': lambda cfg: self.remove_high_missing(cfg.get('threshold', 0.5)),
            'redact_phi': lambda cfg: self.redact_phi(),
            'validate_clinical': lambda cfg: self.validate_clinical(),
            'standardize_codes': lambda cfg: self.standardize_codes(),
            'standardize_medical': lambda cfg: self.standardize_codes(),
            'validate_ranges': lambda cfg: self.validate_ranges(),
            'normalize_clinical_text': lambda cfg: self.normalize_clinical_text(),
            'ml_impute_missing': lambda cfg: self.ml_based_missing_imputation(),
        }

        default_sequence = [
            'smart_type_conversion',
            'handle_missing',
            'remove_duplicates',
            'feature_engineering',
            'clean_text',
            'handle_outliers',
            'remove_high_missing',
            'redact_phi',
            'validate_clinical',
            'standardize_codes',
            'validate_ranges',
            'normalize_clinical_text',
            'ml_impute_missing',
        ]

        sequence = operation_sequence if operation_sequence else default_sequence

        for op_name in sequence:
            op_cfg = operations.get(op_name, {})
            if not op_cfg.get('checked', False):
                continue
            handler = operation_handlers.get(op_name)
            if handler is None:
                continue

            before = self._snapshot_metrics()
            handler(op_cfg)
            after = self._snapshot_metrics()
            self._record_lineage_step(op_name, {
                k: v for k, v in op_cfg.items() if k not in ['label', 'id']
            }, before, after)

        # Calculate before/after metrics
        before_scores = self.calculate_quality_scores(self.original_data)
        after_scores = self.calculate_quality_scores(self.data)
        
        # Calculate data reduction
        original_rows = len(self.original_data)
        cleaned_rows = len(self.data)
        original_cols = len(self.original_data.columns)
        cleaned_cols = len(self.data.columns)
        
        row_reduction = round(((original_rows - cleaned_rows) / original_rows) * 100, 1) if original_rows > 0 else 0
        col_change = cleaned_cols - original_cols
        
        # Quality improvement
        before_missing = int(self.original_data.isnull().sum().sum())
        after_missing = int(self.data.isnull().sum().sum())
        before_duplicates = int(self.original_data.duplicated().sum())
        after_duplicates = int(self.data.duplicated().sum())
        
        self.lineage['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        self.lineage['quality_improvement'] = {
            'before': before_scores,
            'after': after_scores
        }

        sample_size = min(25, len(self.original_data), len(self.data))
        before_preview = self.original_data.head(sample_size).replace({np.nan: None}).to_dict('records')
        after_preview = self.data.head(sample_size).replace({np.nan: None}).to_dict('records')

        return {
            'success': True,
            'original_stats': f'{original_rows} rows × {original_cols} columns',
            'cleaned_stats': f'{cleaned_rows} rows × {cleaned_cols} columns',
            'data_reduction': f'{row_reduction}% rows, {col_change:+d} columns',
            'operations_performed': self.operations_performed,
            'quality_improvement': {
                'missing_values': {'before': before_missing, 'after': after_missing},
                'duplicates': {'before': before_duplicates, 'after': after_duplicates},
                'new_features': col_change if col_change > 0 else 0
            },
            'accuracy': {
                'before': before_scores,
                'after': after_scores
            },
            'comparison': {
                'before_preview': before_preview,
                'after_preview': after_preview,
                'preview_rows': sample_size
            },
            'lineage': self.lineage,
            'validation_report': self.generate_validation_report(before_scores, after_scores)
        }


@app.route('/api/execute', methods=['POST'])
def execute_cleaning():
    """Execute cleaning operations on the dataset (Unified)"""
    data_json = request.get_json()
    
    session_id = data_json.get('session_id')
    operations = data_json.get('operations', {})
    operation_sequence = data_json.get('operation_sequence', [])
    
    # Handle Unstructured Data
    if session_id in unstructured_store:
        try:
            unstructured_data = unstructured_store[session_id]
            raw_text = unstructured_data['raw_text']
            filename = unstructured_data['metadata'].get('filename', 'document.txt')
            
            processor = UnstructuredDataProcessor()
            result = processor.process_text(text=raw_text, filename=filename, options=operations)
            
            unstructured_store[session_id].update({
                'cleaned_text': result.get('cleaned_text', ''),
                'phi_findings': result.get('phi_findings', []),
                'clinical_values': result.get('clinical_values', {}),
                'sections': result.get('sections', []),
                'processed_at': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'is_unstructured': True,
                'session_id': session_id,
                'filename': filename,
                'original_stats': {'rows': unstructured_data['metadata'].get('line_count')},
                'cleaned_stats': {'rows': result.get('metadata', {}).get('line_count', 0)},
                'phi_findings': result.get('phi_findings', []),
                'clinical_values': result.get('clinical_values', {}),
                'sections': result.get('sections', []),
                'cleaned_preview': result.get('cleaned_text', '')[:2000],
                'original_preview': raw_text[:2000],
                'results': {
                    'phi_count': len(result.get('phi_findings', [])),
                    'clinical_count': len(result.get('clinical_values', {}))
                }
            })
        except Exception as e:
            return jsonify({'error': f'Unstructured processing failed: {str(e)}'}), 500

    if not session_id or session_id not in data_store:
        return jsonify({'error': 'Session not found. Please upload a file first.'}), 404
    
    try:
        original_data = data_store[session_id]
        cleaner = DataCleaner(original_data)
        results = cleaner.clean(operations, operation_sequence=operation_sequence)
        
        # Store cleaned data
        data_store[f'{session_id}_cleaned'] = cleaner.data
        lineage_store[session_id] = {
            'session_id': session_id,
            'filename': lineage_store.get(session_id, {}).get('filename', 'uploaded_file'),
            'upload_timestamp': lineage_store.get(session_id, {}).get('created_at', datetime.utcnow().isoformat() + 'Z'),
            'transformations': results.get('lineage', {}).get('transformations', []),
            'quality_improvement': results.get('lineage', {}).get('quality_improvement', {}),
            'finished_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': f'Cleaning failed: {str(e)}'}), 500


@app.route('/api/export/<session_id>')
def export_data(session_id):
    """Export cleaned data as CSV"""
    cleaned_key = f'{session_id}_cleaned'
    if cleaned_key not in data_store:
        if session_id not in data_store:
            return jsonify({'error': 'Session not found'}), 404
        # If no cleaning done, export original
        data = data_store[session_id]
    else:
        data = data_store[cleaned_key]
    
    csv_data = data.to_csv(index=False)
    return csv_data, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=cleaned_data.csv'}


@app.route('/api/export/unstructured/<session_id>')
def export_unstructured_data(session_id):
    """Export cleaned unstructured data and extracted entities as JSON"""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or no unstructured data processed'}), 404
        
    data = unstructured_store[session_id]
    
    # We don't want to export the entire raw text if we don't need to, 
    # but the user wants the extracted JSON data
    export_payload = {
        'metadata': data.get('metadata', {}),
        'phi_findings': data.get('phi_findings', []),
        'clinical_values': data.get('clinical_values', {}),
        'sections': data.get('sections', []),
        'processed_at': data.get('processed_at', None)
    }
    
    return jsonify(export_payload), 200, {
        'Content-Type': 'application/json',
        'Content-Disposition': f'attachment; filename=unstructured_extraction_{session_id[:8]}.json'
    }


@app.route('/api/export/lineage/<session_id>')
def export_lineage(session_id):
    """Export lineage report as JSON file."""
    if session_id not in lineage_store:
        return jsonify({'error': 'Lineage not found'}), 404

    payload = json.dumps(lineage_store[session_id], indent=2)
    return payload, 200, {
        'Content-Type': 'application/json',
        'Content-Disposition': 'attachment; filename=lineage_report.json'
    }


@app.route('/api/visualize/meta/<session_id>')
def visualize_meta(session_id):
    """Get column metadata for visualization field panel"""
    # Check for cleaned data first, fallback to original
    cleaned_key = f'{session_id}_cleaned'
    has_cleaned = cleaned_key in data_store
    has_original = session_id in data_store
    
    if not has_original:
        if session_id in unstructured_store:
            # Handle Unstructured Data for visualization
            u_data = unstructured_store[session_id]
            clinical = u_data.get('clinical_values', {})
            
            if not clinical:
                return jsonify({
                    'has_original': True,
                    'has_cleaned': True,
                    'is_unstructured': True,
                    'original_columns': [],
                    'cleaned_columns': [],
                    'original_rows': 0,
                    'cleaned_rows': 0
                })
                
            # Convert clinical values dict to a single-row DataFrame for metadata extraction
            df = pd.DataFrame([clinical])
            cols = get_column_meta(df)
            
            return jsonify({
                'has_original': True,
                'has_cleaned': True,
                'is_unstructured': True,
                'original_columns': cols,
                'cleaned_columns': cols,
                'original_rows': 1,
                'cleaned_rows': 1
            })
        return jsonify({'error': 'Session not found'}), 404
    
    def get_column_meta(data):
        columns = []
        for col in data.columns:
            dtype = str(data[col].dtype)
            if pd.api.types.is_numeric_dtype(data[col]):
                col_type = 'numeric'
            elif pd.api.types.is_datetime64_any_dtype(data[col]):
                col_type = 'datetime'
            else:
                col_type = 'categorical'
            
            unique_count = int(data[col].nunique())
            null_count = int(data[col].isnull().sum())
            
            columns.append({
                'name': col,
                'dtype': dtype,
                'type': col_type,
                'unique': unique_count,
                'nulls': null_count,
            })
        return columns
    
    result = {
        'has_original': has_original,
        'has_cleaned': has_cleaned,
        'original_columns': get_column_meta(data_store[session_id]) if has_original else [],
        'cleaned_columns': get_column_meta(data_store[cleaned_key]) if has_cleaned else [],
        'original_rows': len(data_store[session_id]) if has_original else 0,
        'cleaned_rows': len(data_store[cleaned_key]) if has_cleaned else 0,
    }
    return jsonify(result)


@app.route('/api/visualize/data/<session_id>', methods=['POST'])
def visualize_data(session_id):
    """Get column data for chart rendering"""
    req = request.get_json()
    source = req.get('source', 'cleaned')  # 'original' or 'cleaned'
    columns = req.get('columns', [])       # list of column names to fetch
    
    # Pick data source
    key = f'{session_id}_cleaned' if source == 'cleaned' else session_id
    
    if key not in data_store:
        # Check if it's an unstructured session
        if session_id in unstructured_store:
            u_data = unstructured_store[session_id]
            clinical = u_data.get('clinical_values', {})
            # Create a single-row DataFrame from clinical highlights
            data = pd.DataFrame([clinical])
        else:
            return jsonify({'error': 'Data source not found'}), 404
    else:
        data = data_store[key]
    
    # Limit to 5000 rows for browser performance
    sample = data if len(data) <= 5000 else data.sample(5000, random_state=42)
    
    # Build response with requested columns
    result = {'rows': len(sample), 'total_rows': len(data), 'columns': {}}
    
    for col in columns:
        if col not in sample.columns:
            continue
        col_data = sample[col]
        
        # Convert to JSON-safe format
        if pd.api.types.is_datetime64_any_dtype(col_data):
            result['columns'][col] = col_data.astype(str).fillna('').tolist()
        elif pd.api.types.is_numeric_dtype(col_data):
            result['columns'][col] = col_data.fillna(0).tolist()
        else:
            result['columns'][col] = col_data.fillna('').astype(str).tolist()
    
    return jsonify(result)


@app.route('/api/visualize/stats/<session_id>', methods=['POST'])
def visualize_stats(session_id):
    """Get summary statistics for a column"""
    req = request.get_json()
    source = req.get('source', 'cleaned')
    column = req.get('column', '')
    
    key = f'{session_id}_cleaned' if source == 'cleaned' and f'{session_id}_cleaned' in data_store else session_id
    if key not in data_store:
        return jsonify({'error': 'Session not found'}), 404
    
    data = data_store[key]
    if column not in data.columns:
        return jsonify({'error': f'Column {column} not found'}), 404
    
    col_data = data[column]
    stats = {'column': column, 'count': int(col_data.count()), 'nulls': int(col_data.isnull().sum())}
    
    if pd.api.types.is_numeric_dtype(col_data):
        stats.update({
            'mean': round(float(col_data.mean()), 4) if not col_data.empty else 0,
            'median': round(float(col_data.median()), 4) if not col_data.empty else 0,
            'std': round(float(col_data.std()), 4) if not col_data.empty else 0,
            'min': round(float(col_data.min()), 4) if not col_data.empty else 0,
            'max': round(float(col_data.max()), 4) if not col_data.empty else 0,
        })
    else:
        top_values = col_data.value_counts().head(10).to_dict()
        stats['top_values'] = {str(k): int(v) for k, v in top_values.items()}
        stats['unique'] = int(col_data.nunique())
    
    return jsonify(stats)


# Phase 4: Comparison Mode
@app.route('/api/comparison/<session_id>')
def get_comparison_data(session_id):
    """Get before/after comparison data for split-screen mode."""
    original_key = session_id
    cleaned_key = f'{session_id}_cleaned'
    
    if original_key not in data_store:
        return jsonify({'error': 'Session not found'}), 404
    
    original_data = data_store[original_key]
    cleaned_data = data_store.get(cleaned_key, original_data)
    
    sample_size = 25
    original_sample = original_data.head(sample_size).replace({np.nan: None}).to_dict('records')
    cleaned_sample = cleaned_data.head(sample_size).replace({np.nan: None}).to_dict('records')
    
    comparison = {
        'original': {
            'rows': len(original_data),
            'columns': len(original_data.columns),
            'missing_cells': int(original_data.isnull().sum().sum()),
            'duplicate_rows': int(original_data.duplicated().sum()),
            'memory_mb': round(original_data.memory_usage(deep=True).sum() / 1024**2, 2),
            'sample': original_sample
        },
        'cleaned': {
            'rows': len(cleaned_data),
            'columns': len(cleaned_data.columns),
            'missing_cells': int(cleaned_data.isnull().sum().sum()),
            'duplicate_rows': int(cleaned_data.duplicated().sum()),
            'memory_mb': round(cleaned_data.memory_usage(deep=True).sum() / 1024**2, 2),
            'sample': cleaned_sample
        },
        'improvements': {
            'rows_removed': len(original_data) - len(cleaned_data),
            'missing_cells_reduced': int(original_data.isnull().sum().sum()) - int(cleaned_data.isnull().sum().sum()),
            'duplicates_removed': int(original_data.duplicated().sum()) - int(cleaned_data.duplicated().sum()),
            'memory_saved_mb': round(original_data.memory_usage(deep=True).sum() / 1024**2, 2) - round(cleaned_data.memory_usage(deep=True).sum() / 1024**2, 2)
        }
    }
    
    return jsonify(comparison)


# ─────────────────────────────────────────────────────────────────────────────
# UNSTRUCTURED DATA ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/unstructured/upload', methods=['POST'])
def upload_unstructured():
    """Upload and process unstructured text files (TXT, LOG, PDF, MD)."""
    if not UNSTRUCTURED_AVAILABLE:
        return jsonify({'error': 'Unstructured processor not available'}), 500

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    supported = {'txt', 'log', 'pdf', 'md', 'text', 'dat', 'rtf'}
    if file_ext not in supported:
        return jsonify({
            'error': f'Unsupported file type: .{file_ext}',
            'supported': list(supported)
        }), 400

    # Parse options from form data
    options = {
        'redact_phi': request.form.get('redact_phi', 'true').lower() == 'true',
        'redaction_style': request.form.get('redaction_style', 'tag'),
        'expand_abbreviations': request.form.get('expand_abbreviations', 'true').lower() == 'true',
        'spell_correct': request.form.get('spell_correct', 'true').lower() == 'true',
        'extract_clinical': request.form.get('extract_clinical', 'true').lower() == 'true',
        'extract_entities': request.form.get('extract_entities', 'true').lower() == 'true',
        'generate_tables': False,
        'parse_logs': request.form.get('parse_logs', 'true').lower() == 'true',
        'extract_sections': request.form.get('extract_sections', 'true').lower() == 'true',
    }

    # Parse cleaning operations
    cleaning_ops = {}
    for op in ['normalize_whitespace', 'normalize_line_breaks', 'remove_control_chars',
                'fix_encoding_artifacts', 'normalize_unicode', 'standardize_punctuation',
                'remove_empty_lines', 'fix_hyphenation']:
        val = request.form.get(op, 'true')
        cleaning_ops[op] = val.lower() == 'true'
    options['cleaning_ops'] = cleaning_ops

    try:
        processor = UnstructuredDataProcessor()
        result = processor.process_file(file_obj=file, filename=filename, options=options)

        # Store result with session ID for later export
        session_id = str(uuid.uuid4())
        # Only store cleaned text and metadata, not raw text (data minimization)
        unstructured_store[session_id] = {
            'cleaned_text': result.get('cleaned_text', ''),
            'metadata': result.get('metadata', {}),
            'stats': result.get('stats', {}),
            'log_entries': result.get('log_entries', []),
            'quality_report': result.get('quality_report', {}),
            'clinical_values': result.get('clinical_values', {}),
            'phi_findings': result.get('phi_findings', []),
            'sections': result.get('sections', []),
            'stored_at': datetime.now().isoformat(),
        }

        if REVIEW_WORKFLOW_AVAILABLE:
            review_workflows[session_id] = ReviewWorkflow(
                store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id)
            )

        result['session_id'] = session_id
        # Remove full cleaned_text from response to reduce payload
        # Frontend uses the preview; full text available via export
        if len(result.get('cleaned_text', '')) > 5000:
            result['cleaned_text'] = result['cleaned_text'][:5000] + '\n\n[... truncated — use Export to get full text ...]'

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/unstructured/export/<session_id>')
def export_unstructured(session_id):
    """Export cleaned unstructured text as a downloadable file."""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or expired'}), 404

    data = unstructured_store[session_id]
    cleaned_text = data['cleaned_text']
    original_name = data['metadata'].get('filename', 'cleaned_output')
    base_name = os.path.splitext(original_name)[0]

    from flask import Response
    return Response(
        cleaned_text,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{base_name}_cleaned.txt"'
        }
    )


@app.route('/api/unstructured/demo', methods=['POST'])
def load_unstructured_demo():
    """Load a sample unstructured healthcare file for demo."""
    if not UNSTRUCTURED_AVAILABLE:
        return jsonify({'error': 'Unstructured processor not available'}), 500

    demo_type = request.json.get('type', 'txt') if request.is_json else 'txt'

    demo_files = {
        'txt': 'sample_medical_notes.txt',
        'log': 'sample_ehr_log.log',
        'md': 'sample_clinical_trial.md',
    }

    demo_filename = demo_files.get(demo_type, 'sample_medical_notes.txt')
    demo_path = os.path.join(app.config['INPUT_FOLDER'], demo_filename)

    if not os.path.exists(demo_path):
        return jsonify({'error': f'Demo file not found: {demo_filename}'}), 404

    try:
        processor = UnstructuredDataProcessor()
        result = processor.process_file(file_path=demo_path, options={
            'redact_phi': True,
            'redaction_style': 'tag',
            'expand_abbreviations': True,
            'spell_correct': True,
            'extract_clinical': True,
            'extract_entities': True,
            'generate_tables': False,
            'parse_logs': True,
            'extract_sections': True,
        })

        session_id = str(uuid.uuid4())
        unstructured_store[session_id] = {
            'cleaned_text': result.get('cleaned_text', ''),
            'metadata': result.get('metadata', {}),
            'stats': result.get('stats', {}),
            'log_entries': result.get('log_entries', []),
            'quality_report': result.get('quality_report', {}),
            'stored_at': datetime.now().isoformat(),
        }

        if REVIEW_WORKFLOW_AVAILABLE:
            review_workflows[session_id] = ReviewWorkflow(
                store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id)
            )
        result['session_id'] = session_id

        if len(result.get('cleaned_text', '')) > 5000:
            result['cleaned_text'] = result['cleaned_text'][:5000] + '\n\n[... truncated — use Export to get full text ...]'

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Demo loading failed: {str(e)}'}), 500


@app.route('/api/unstructured/review/summary/<session_id>')
def unstructured_review_summary(session_id):
    """Return reviewer workflow summary for a processed unstructured session."""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or expired'}), 404
    if not REVIEW_WORKFLOW_AVAILABLE:
        return jsonify({'error': 'Review workflow module is not available'}), 501

    entries = unstructured_store[session_id].get('log_entries', [])
    workflow = review_workflows.get(session_id)
    if workflow is None:
        workflow = ReviewWorkflow(store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id))
        review_workflows[session_id] = workflow

    summary = get_review_summary(entries, workflow)
    summary['session_id'] = session_id
    return jsonify(summary)


@app.route('/api/unstructured/review/flagged/<session_id>')
def unstructured_review_flagged(session_id):
    """Return entries flagged for manual review based on confidence thresholds."""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or expired'}), 404
    if not REVIEW_WORKFLOW_AVAILABLE:
        return jsonify({'error': 'Review workflow module is not available'}), 501

    threshold = request.args.get('threshold', default=70, type=int)
    entries = unstructured_store[session_id].get('log_entries', [])
    workflow = review_workflows.get(session_id)
    if workflow is None:
        workflow = ReviewWorkflow(store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id))
        review_workflows[session_id] = workflow

    flagged = workflow.list_flagged_entries(entries, review_threshold=threshold)
    return jsonify({
        'session_id': session_id,
        'threshold': threshold,
        'flagged_count': len(flagged),
        'entries': flagged,
    })


@app.route('/api/unstructured/review/decision', methods=['POST'])
def unstructured_review_decision():
    """Record a reviewer decision for a specific normalized entry."""
    if not REVIEW_WORKFLOW_AVAILABLE:
        return jsonify({'error': 'Review workflow module is not available'}), 501

    payload = request.get_json(silent=True) or {}
    session_id = payload.get('session_id')
    entry_id = payload.get('entry_id')
    reviewer_name = payload.get('reviewer_name', 'reviewer')
    decision = payload.get('decision')
    modified_payload = payload.get('modified_payload')
    notes = payload.get('notes', '')

    if not session_id or session_id not in unstructured_store:
        return jsonify({'error': 'Invalid or missing session_id'}), 400
    if not entry_id:
        return jsonify({'error': 'Missing entry_id'}), 400
    if decision not in {'approved', 'rejected', 'modified'}:
        return jsonify({'error': 'decision must be one of: approved, rejected, modified'}), 400

    workflow = review_workflows.get(session_id)
    if workflow is None:
        workflow = ReviewWorkflow(store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id))
        review_workflows[session_id] = workflow

    decision_obj = workflow.record_decision(
        entry_id=entry_id,
        reviewer_name=reviewer_name,
        decision=decision,
        modified_payload=modified_payload,
        notes=notes,
    )

    return jsonify({
        'status': 'success',
        'session_id': session_id,
        'decision': decision_obj.__dict__,
    })


@app.route('/api/unstructured/review/export/<session_id>')
def unstructured_review_export(session_id):
    """Export reviewed entries with audit trail for compliance."""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or expired'}), 404
    if not REVIEW_WORKFLOW_AVAILABLE:
        return jsonify({'error': 'Review workflow module is not available'}), 501

    entries = unstructured_store[session_id].get('log_entries', [])
    workflow = review_workflows.get(session_id)
    if workflow is None:
        workflow = ReviewWorkflow(store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id))
        review_workflows[session_id] = workflow

    reviewed = export_reviewed_entries(entries, workflow)
    reviewed['session_id'] = session_id
    return jsonify(reviewed)


@app.route('/api/unstructured/production/export_audit/<session_id>', methods=['POST'])
def unstructured_export_audit_package(session_id):
    """Phase 5 endpoint: export compliance audit package for a session."""
    if session_id not in unstructured_store:
        return jsonify({'error': 'Session not found or expired'}), 404
    if not (PHASE5_AVAILABLE and REVIEW_WORKFLOW_AVAILABLE):
        return jsonify({'error': 'Phase 5 or review workflow modules are not available'}), 501

    body = request.get_json(silent=True) or {}
    output_dir = body.get('output_dir')
    if not output_dir:
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audit_exports', session_id)

    os.makedirs(output_dir, exist_ok=True)
    logger_obj = StructuredLogger(log_file=os.path.join(output_dir, 'phase5_audit.log'))

    entries = unstructured_store[session_id].get('log_entries', [])
    workflow = review_workflows.get(session_id)
    if workflow is None:
        workflow = ReviewWorkflow(store_path=os.path.join(app.config['UPLOAD_FOLDER'], 'review_store', session_id))
        review_workflows[session_id] = workflow

    export_path = export_for_auditor(entries, workflow, logger_obj, output_dir=output_dir)
    return jsonify({
        'status': 'success',
        'session_id': session_id,
        'export_path': export_path,
    })


@app.route('/api/unstructured/capabilities')
def unstructured_capabilities():
    """Return available unstructured processing capabilities."""
    return jsonify({
        'available': UNSTRUCTURED_AVAILABLE,
        'review_workflow_available': REVIEW_WORKFLOW_AVAILABLE,
        'production_hardening_available': PHASE5_AVAILABLE,
        'supported_formats': ['.txt', '.log', '.pdf', '.md', '.text', '.dat', '.rtf'],
        'pdf_support': {
            'docling': DOCLING_AVAILABLE if UNSTRUCTURED_AVAILABLE else False,
            'pymupdf': PYMUPDF_AVAILABLE if UNSTRUCTURED_AVAILABLE else False,
            'tesseract_ocr': TESSERACT_AVAILABLE if UNSTRUCTURED_AVAILABLE else False,
        } if UNSTRUCTURED_AVAILABLE else {},
        'cleaning_operations': [
            'normalize_whitespace', 'normalize_line_breaks', 'remove_control_chars',
            'fix_encoding_artifacts', 'normalize_unicode', 'standardize_punctuation',
            'remove_empty_lines', 'fix_hyphenation'
        ],
        'phi_detection': list(PHI_PATTERNS.keys()) if UNSTRUCTURED_AVAILABLE else [],
        'redaction_styles': ['tag', 'hash', 'mask', 'remove'],
        'medical_processing': {
            'abbreviation_expansion': UNSTRUCTURED_AVAILABLE,
            'spell_correction': SYMSPELL_AVAILABLE if UNSTRUCTURED_AVAILABLE else False,
            'regex_ner': UNSTRUCTURED_AVAILABLE,
            'structured_tables': False,
        },
        'entity_types': ['DISEASE', 'DRUG', 'PROCEDURE'],
        'compliance': ['HIPAA Safe Harbor', 'GDPR Data Minimization', 'India DPDP Act'],
        'review_api': {
            'summary': '/api/unstructured/review/summary/<session_id>',
            'flagged': '/api/unstructured/review/flagged/<session_id>',
            'decision': '/api/unstructured/review/decision',
            'export': '/api/unstructured/review/export/<session_id>',
        } if REVIEW_WORKFLOW_AVAILABLE else {},
        'phase5_api': {
            'audit_export': '/api/unstructured/production/export_audit/<session_id>',
        } if PHASE5_AVAILABLE else {},
    })


# Expose PHI_PATTERNS for capabilities route
try:
    from unstructured_processor import (
        PHI_PATTERNS,
        DOCLING_AVAILABLE,
        PYMUPDF_AVAILABLE,
        TESSERACT_AVAILABLE,
        SYMSPELL_AVAILABLE,
    )
except ImportError:
    PHI_PATTERNS = {}
    DOCLING_AVAILABLE = False
    PYMUPDF_AVAILABLE = False
    TESSERACT_AVAILABLE = False
    SYMSPELL_AVAILABLE = False


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Smart Data Cleaner Web Server on port {port}...")
    print(f"📍 Access locally at http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

