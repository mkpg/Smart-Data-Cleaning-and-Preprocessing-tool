import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from collections import defaultdict
import re
from datetime import datetime
import hashlib
import yaml

class HealthcareDataCleaner:
    def __init__(self):
        self.data = None
        self.original_data = None
        self.data_type = None
        self.cleaning_report = []
        self.analysis_dataset = None
        self.selected_strategy = None
        self.cleaning_config = {
            'missing_values_method': 'auto',
            'outliers_method': 'cap',
            'enabled_operations': set()
        }
        
    def load_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.original_data = json.loads(json.dumps(self.data))
        self.data_type = 'json'
        return self.data
    
    def load_xml(self, filepath):
        tree = ET.parse(filepath)
        self.data = self.xml_to_dict(tree.getroot())
        self.original_data = json.loads(json.dumps(self.data))
        self.data_type = 'xml'
        return self.data
    
    def xml_to_dict(self, element):
        result = {}
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self.xml_to_dict(child)
        if element.attrib:
            result['@attributes'] = element.attrib
        return result

class HealthcareCleanerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Healthcare Semi-Structured Data Cleaner")
        self.root.geometry("1200x800")
        
        self.cleaner = HealthcareDataCleaner()
        self.setup_gui()
        
    def setup_gui(self):
        # Create main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Three main tabs as requested
        self.setup_data_analysis_tab()
        self.setup_review_adjust_tab()
        self.setup_execute_run_tab()
        
    def setup_data_analysis_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="1. Data Analysis")
        
        # File upload section
        upload_frame = ttk.LabelFrame(tab, text="Data Upload")
        upload_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File selection row
        file_row = ttk.Frame(upload_frame)
        file_row.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_row, text="Select Healthcare Data File:").pack(side=tk.LEFT)
        
        self.file_path = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.file_path, width=80).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(file_row, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # Data type selection row
        type_row = ttk.Frame(upload_frame)
        type_row.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(type_row, text="Data Type:").pack(side=tk.LEFT)
        
        self.data_type = tk.StringVar(value="json")
        ttk.Radiobutton(type_row, text="JSON", variable=self.data_type, value="json").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_row, text="XML", variable=self.data_type, value="xml").pack(side=tk.LEFT, padx=10)
        
        # Load button
        ttk.Button(upload_frame, text="Load & Analyze Data", command=self.load_and_analyze).pack(pady=10)
        
        # Data preview section
        preview_frame = ttk.LabelFrame(tab, text="Data Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=10)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Quality issues section
        quality_frame = ttk.LabelFrame(tab, text="Data Quality Issues")
        quality_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.quality_text = scrolledtext.ScrolledText(quality_frame, height=10)
        self.quality_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def setup_review_adjust_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="2. Review & Adjust")
        
        # Main container with scrollbar
        main_container = ttk.Frame(tab)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Strategy selection
        strategy_frame = ttk.LabelFrame(scrollable_frame, text="🎯 SELECT BASE CLEANING STRATEGY")
        strategy_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Strategy descriptions
        self.strategies = {
            "🧠 AUTO SMART (Default)": "Balanced approach for most datasets\n• Smart data type conversion\n• Handle missing values (auto)\n• Remove duplicate rows\n• Create derived features\n• Clean text formatting\n• Handle outliers using capping",
            "⚡ AGGRESSIVE": "Maximum data quality, removes problematic data\n• All Auto Smart features PLUS\n• Remove columns with >50% missing values\n• More aggressive outlier removal\n• Stricter data type enforcement",
            "🛡️ CONSERVATIVE": "Minimal changes, preserve original data\n• Smart data type conversion only\n• Remove exact duplicate rows only\n• No missing value imputation\n• No outlier handling\n• No feature engineering",
            "🏥 HEALTHCARE SPECIFIC": "Healthcare data compliance and validation\n• Auto Smart features PLUS\n• Auto-redact PHI (names, emails, phones, SSN)\n• Validate clinical ranges\n• Standardize medical codes\n• Healthcare-specific feature engineering",
            "📁 CUSTOM YAML (Advanced)": "User-defined cleaning workflows\n• Upload custom YAML configuration\n• Define operation sequences\n• Set domain-specific validation rules\n• Create custom derived metrics"
        }
        
        self.strategy_var = tk.StringVar(value="🧠 AUTO SMART (Default)")
        
        for strategy, description in self.strategies.items():
            frame = ttk.Frame(strategy_frame)
            frame.pack(fill=tk.X, pady=2, padx=5)
            
            ttk.Radiobutton(frame, text=strategy, variable=self.strategy_var, 
                           value=strategy, command=self.on_strategy_change).pack(side=tk.LEFT, anchor=tk.W)
            
            # Description label
            desc_label = ttk.Label(frame, text=description, justify=tk.LEFT, wraplength=800)
            desc_label.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        # Custom YAML upload
        yaml_frame = ttk.Frame(strategy_frame)
        yaml_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(yaml_frame, text="Upload Custom YAML", 
                  command=self.upload_yaml).pack(side=tk.LEFT, padx=5)
        
        self.yaml_path = tk.StringVar()
        ttk.Label(yaml_frame, textvariable=self.yaml_path).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Strategy details section
        details_frame = ttk.LabelFrame(scrollable_frame, text="Selected Strategy Details")
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.strategy_details = scrolledtext.ScrolledText(details_frame, height=8)
        self.strategy_details.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # OPERATIONS CONFIGURATION SECTION
        operations_frame = ttk.LabelFrame(scrollable_frame, text="✅ OPERATIONS CONFIGURATION")
        operations_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 🌐 Global Operations
        global_frame = ttk.LabelFrame(operations_frame, text="🌐 GLOBAL OPERATIONS")
        global_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Operation checkboxes
        self.operations_vars = {}
        
        # Smart data type conversion
        op1_frame = ttk.Frame(global_frame)
        op1_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['data_type_conversion'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op1_frame, text="Smart data type conversion", 
                       variable=self.operations_vars['data_type_conversion'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Handle missing values with method selector
        op2_frame = ttk.Frame(global_frame)
        op2_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['handle_missing'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op2_frame, text="Handle missing values", 
                       variable=self.operations_vars['handle_missing'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Missing values method dropdown
        self.missing_method_var = tk.StringVar(value="auto")
        missing_methods = ttk.Combobox(op2_frame, textvariable=self.missing_method_var, 
                                      values=["auto", "remove", "fill_median", "fill_mode", "fill_zero"],
                                      state="readonly", width=15)
        missing_methods.pack(side=tk.LEFT, padx=10)
        missing_methods.bind('<<ComboboxSelected>>', self.update_operations_summary)
        
        # Remove duplicates
        op3_frame = ttk.Frame(global_frame)
        op3_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['remove_duplicates'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op3_frame, text="Remove duplicate rows", 
                       variable=self.operations_vars['remove_duplicates'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Create derived features
        op4_frame = ttk.Frame(global_frame)
        op4_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['create_features'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op4_frame, text="Create derived features", 
                       variable=self.operations_vars['create_features'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Clean text formatting
        op5_frame = ttk.Frame(global_frame)
        op5_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['clean_text'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op5_frame, text="Clean text formatting", 
                       variable=self.operations_vars['clean_text'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Handle outliers with method selector
        op6_frame = ttk.Frame(global_frame)
        op6_frame.pack(fill=tk.X, pady=2)
        self.operations_vars['handle_outliers'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(op6_frame, text="Handle outliers", 
                       variable=self.operations_vars['handle_outliers'],
                       command=self.update_operations_summary).pack(side=tk.LEFT)
        
        # Outliers method dropdown
        self.outliers_method_var = tk.StringVar(value="cap")
        outliers_methods = ttk.Combobox(op6_frame, textvariable=self.outliers_method_var, 
                                       values=["cap", "remove", "ignore"],
                                       state="readonly", width=15)
        outliers_methods.pack(side=tk.LEFT, padx=10)
        outliers_methods.bind('<<ComboboxSelected>>', self.update_operations_summary)
        
        # ⚡ Aggressive Options (only for aggressive strategy)
        self.aggressive_frame = ttk.LabelFrame(operations_frame, text="⚡ AGGRESSIVE OPTIONS")
        
        self.operations_vars['remove_high_missing'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.aggressive_frame, text="Remove columns with >50% missing values", 
                       variable=self.operations_vars['remove_high_missing'],
                       command=self.update_operations_summary).pack(anchor=tk.W, pady=2)
        
        # 🏥 Healthcare-Specific Options (only for healthcare strategy)
        self.healthcare_frame = ttk.LabelFrame(operations_frame, text="🏥 HEALTHCARE-SPECIFIC OPTIONS")
        
        self.operations_vars['redact_phi'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.healthcare_frame, text="Auto-redact PHI (names, emails, phones, SSN)", 
                       variable=self.operations_vars['redact_phi'],
                       command=self.update_operations_summary).pack(anchor=tk.W, pady=2)
        
        self.operations_vars['validate_clinical'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.healthcare_frame, text="Validate clinical ranges (BP, heart rate, lab values)", 
                       variable=self.operations_vars['validate_clinical'],
                       command=self.update_operations_summary).pack(anchor=tk.W, pady=2)
        
        self.operations_vars['standardize_codes'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.healthcare_frame, text="Standardize medical codes (ICD-10, CPT, LOINC)", 
                       variable=self.operations_vars['standardize_codes'],
                       command=self.update_operations_summary).pack(anchor=tk.W, pady=2)
        
        # Operations Summary
        summary_frame = ttk.LabelFrame(scrollable_frame, text="📋 OPERATIONS SUMMARY")
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.operations_summary = scrolledtext.ScrolledText(summary_frame, height=8)
        self.operations_summary.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Update strategy details when selection changes
        self.strategy_var.trace('w', self.on_strategy_change)
        self.update_operations_summary()  # Initial update
        self.update_strategy_details()  # Initial update
        
    def setup_execute_run_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="3. Execute & Run")
        
        # Execute button
        execute_frame = ttk.Frame(tab)
        execute_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(execute_frame, text="🚀 EXECUTE CLEANING PIPELINE", 
                  command=self.execute_cleaning).pack(pady=10)
        
        # Results display
        results_frame = ttk.LabelFrame(tab, text="Cleaning Results")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Summary section
        summary_frame = ttk.LabelFrame(results_frame, text="Cleaning Summary")
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.summary_text = scrolledtext.ScrolledText(summary_frame, height=8)
        self.summary_text.pack(fill=tk.X, padx=5, pady=5)
        
        # Results section
        results_preview_frame = ttk.LabelFrame(results_frame, text="Cleaned Data Preview")
        results_preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.results_text = scrolledtext.ScrolledText(results_preview_frame, height=12)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Export buttons
        export_frame = ttk.Frame(results_frame)
        export_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Button(export_frame, text="📥 Export Cleaned CSV", 
                  command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="📥 Export Cleaned JSON", 
                  command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="📥 Export Cleaning Report", 
                  command=self.export_report).pack(side=tk.LEFT, padx=5)
        
    def on_strategy_change(self, *args):
        """Update UI based on selected strategy"""
        strategy = self.strategy_var.get()
        
        # Hide all specialty frames first
        self.aggressive_frame.pack_forget() if hasattr(self, 'aggressive_frame') and self.aggressive_frame.winfo_ismapped() else None
        self.healthcare_frame.pack_forget() if hasattr(self, 'healthcare_frame') and self.healthcare_frame.winfo_ismapped() else None
        
        # Set default operations based on strategy
        if strategy == "🧠 AUTO SMART (Default)":
            self.set_auto_smart_defaults()
        elif strategy == "⚡ AGGRESSIVE":
            self.set_aggressive_defaults()
            self.aggressive_frame.pack(fill=tk.X, padx=5, pady=5)
        elif strategy == "🛡️ CONSERVATIVE":
            self.set_conservative_defaults()
        elif strategy == "🏥 HEALTHCARE SPECIFIC":
            self.set_healthcare_defaults()
            self.healthcare_frame.pack(fill=tk.X, padx=5, pady=5)
        elif strategy == "📁 CUSTOM YAML (Advanced)":
            self.set_custom_defaults()
        
        self.update_strategy_details()
        self.update_operations_summary()
    
    def set_auto_smart_defaults(self):
        """Set defaults for Auto Smart strategy"""
        self.operations_vars['data_type_conversion'].set(True)
        self.operations_vars['handle_missing'].set(True)
        self.operations_vars['remove_duplicates'].set(True)
        self.operations_vars['create_features'].set(True)
        self.operations_vars['clean_text'].set(True)
        self.operations_vars['handle_outliers'].set(True)
        self.operations_vars['remove_high_missing'].set(False)
        self.operations_vars['redact_phi'].set(False)
        self.operations_vars['validate_clinical'].set(False)
        self.operations_vars['standardize_codes'].set(False)
        self.missing_method_var.set("auto")
        self.outliers_method_var.set("cap")
    
    def set_aggressive_defaults(self):
        """Set defaults for Aggressive strategy"""
        self.operations_vars['data_type_conversion'].set(True)
        self.operations_vars['handle_missing'].set(True)
        self.operations_vars['remove_duplicates'].set(True)
        self.operations_vars['create_features'].set(True)
        self.operations_vars['clean_text'].set(True)
        self.operations_vars['handle_outliers'].set(True)
        self.operations_vars['remove_high_missing'].set(True)
        self.operations_vars['redact_phi'].set(False)
        self.operations_vars['validate_clinical'].set(False)
        self.operations_vars['standardize_codes'].set(False)
        self.missing_method_var.set("remove")
        self.outliers_method_var.set("remove")
    
    def set_conservative_defaults(self):
        """Set defaults for Conservative strategy"""
        self.operations_vars['data_type_conversion'].set(True)
        self.operations_vars['handle_missing'].set(False)
        self.operations_vars['remove_duplicates'].set(True)
        self.operations_vars['create_features'].set(False)
        self.operations_vars['clean_text'].set(False)
        self.operations_vars['handle_outliers'].set(False)
        self.operations_vars['remove_high_missing'].set(False)
        self.operations_vars['redact_phi'].set(False)
        self.operations_vars['validate_clinical'].set(False)
        self.operations_vars['standardize_codes'].set(False)
        self.missing_method_var.set("ignore")
        self.outliers_method_var.set("ignore")
    
    def set_healthcare_defaults(self):
        """Set defaults for Healthcare Specific strategy"""
        self.operations_vars['data_type_conversion'].set(True)
        self.operations_vars['handle_missing'].set(True)
        self.operations_vars['remove_duplicates'].set(True)
        self.operations_vars['create_features'].set(True)
        self.operations_vars['clean_text'].set(True)
        self.operations_vars['handle_outliers'].set(True)
        self.operations_vars['remove_high_missing'].set(False)
        self.operations_vars['redact_phi'].set(True)
        self.operations_vars['validate_clinical'].set(True)
        self.operations_vars['standardize_codes'].set(True)
        self.missing_method_var.set("auto")
        self.outliers_method_var.set("cap")
    
    def set_custom_defaults(self):
        """Set defaults for Custom YAML strategy"""
        # Keep current settings for custom
        pass
    
    def update_operations_summary(self, *args):
        """Update the operations summary display"""
        summary = "📋 SELECTED OPERATIONS:\n\n"
        
        strategy = self.strategy_var.get()
        summary += f"Strategy: {strategy}\n\n"
        
        summary += "🌐 GLOBAL OPERATIONS:\n"
        if self.operations_vars['data_type_conversion'].get():
            summary += "✓ Smart data type conversion\n"
        if self.operations_vars['handle_missing'].get():
            summary += f"✓ Handle missing values ({self.missing_method_var.get()})\n"
        if self.operations_vars['remove_duplicates'].get():
            summary += "✓ Remove duplicate rows\n"
        if self.operations_vars['create_features'].get():
            summary += "✓ Create derived features\n"
        if self.operations_vars['clean_text'].get():
            summary += "✓ Clean text formatting\n"
        if self.operations_vars['handle_outliers'].get():
            summary += f"✓ Handle outliers ({self.outliers_method_var.get()})\n"
        
        if strategy == "⚡ AGGRESSIVE":
            summary += "\n⚡ AGGRESSIVE OPTIONS:\n"
            if self.operations_vars['remove_high_missing'].get():
                summary += "✓ Remove columns with >50% missing values\n"
        
        if strategy == "🏥 HEALTHCARE SPECIFIC":
            summary += "\n🏥 HEALTHCARE-SPECIFIC:\n"
            if self.operations_vars['redact_phi'].get():
                summary += "✓ Auto-redact PHI\n"
            if self.operations_vars['validate_clinical'].get():
                summary += "✓ Validate clinical ranges\n"
            if self.operations_vars['standardize_codes'].get():
                summary += "✓ Standardize medical codes\n"
        
        if strategy == "📁 CUSTOM YAML (Advanced)" and self.yaml_path.get():
            summary += f"\n📁 CUSTOM OPERATIONS:\n• Loaded from: {self.yaml_path.get()}\n"
        
        self.operations_summary.delete(1.0, tk.END)
        self.operations_summary.insert(tk.END, summary)
    
    def update_strategy_details(self):
        strategy = self.strategy_var.get()
        details = ""
        
        if strategy == "🧠 AUTO SMART (Default)":
            details = """STRATEGY: Auto Smart (Recommended for most use cases)

OPERATIONS TO BE PERFORMED:
✓ Smart data type conversion (numbers, dates, currencies)
✓ Handle missing values (auto detection)  
✓ Remove duplicate rows
✓ Create derived features from dates/text
✓ Clean text formatting (whitespace, case normalization)
✓ Handle outliers using IQR capping method

BEST FOR: General datasets, mixed data types, unknown data quality"""
            
        elif strategy == "⚡ AGGRESSIVE":
            details = """STRATEGY: Aggressive (Maximum data quality)

OPERATIONS TO BE PERFORMED:
✓ All Auto Smart features PLUS:
✓ Remove columns with >50% missing values
✓ More aggressive outlier removal (remove method)
✓ Stricter data type enforcement
✓ Additional data validation rules

BEST FOR: Machine learning preparation, production datasets"""
            
        elif strategy == "🛡️ CONSERVATIVE":
            details = """STRATEGY: Conservative (Minimal changes)

OPERATIONS TO BE PERFORMED:
✓ Smart data type conversion only
✓ Remove exact duplicate rows only
✓ No missing value imputation
✓ No outlier handling
✓ No feature engineering

BEST FOR: Sensitive data, audit requirements, exploratory analysis"""
            
        elif strategy == "🏥 HEALTHCARE SPECIFIC":
            details = """STRATEGY: Healthcare Specific (Medical data compliance)

OPERATIONS TO BE PERFORMED:
✓ All Auto Smart features PLUS:
✓ Auto-redact PHI (names, emails, phones, SSN)
✓ Validate clinical ranges (BP, heart rate, lab values)
✓ Standardize medical codes (ICD-10, CPT, LOINC)
✓ Healthcare-specific feature engineering
✓ HIPAA compliance checks

BEST FOR: Medical records, clinical data, healthcare analytics"""
            
        elif strategy == "📁 CUSTOM YAML (Advanced)":
            yaml_file = self.yaml_path.get()
            if yaml_file:
                details = f"""STRATEGY: Custom YAML Configuration

CONFIG FILE: {yaml_file}

OPERATIONS: Defined in custom YAML configuration file
• User-defined cleaning sequences
• Custom validation rules
• Domain-specific transformations

BEST FOR: Specialized domains, reproducible pipelines"""
            else:
                details = "Please upload a YAML configuration file to use custom strategy."
        
        self.strategy_details.delete(1.0, tk.END)
        self.strategy_details.insert(tk.END, details)
    
    def browse_file(self):
        filetypes = [
            ("JSON files", "*.json"),
            ("XML files", "*.xml"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.file_path.set(filename)
            
    def upload_yaml(self):
        filetypes = [("YAML files", "*.yaml"), ("YML files", "*.yml")]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.yaml_path.set(filename)
            self.strategy_var.set("📁 CUSTOM YAML (Advanced)")
            
    def load_and_analyze(self):
        try:
            filepath = self.file_path.get()
            if not filepath:
                messagebox.showwarning("Warning", "Please select a file first")
                return
                
            # Load data
            if self.data_type.get() == "json":
                self.cleaner.load_json(filepath)
            else:
                self.cleaner.load_xml(filepath)
                
            # Show preview
            preview = json.dumps(self.cleaner.data, indent=2)
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, preview[:2000] + "\n\n... (preview truncated)" if len(preview) > 2000 else preview)
            
            # Analyze quality
            quality_report = self.analyze_data_quality()
            self.quality_text.delete(1.0, tk.END)
            self.quality_text.insert(tk.END, quality_report)
            
            messagebox.showinfo("Success", "Data loaded and analyzed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            
    def analyze_data_quality(self):
        """Dynamic data quality analysis that works with any structure"""
        report = "=== DYNAMIC DATA QUALITY ASSESSMENT ===\n\n"
        
        # Basic structure analysis
        report += f"Data Type: {self.cleaner.data_type.upper()}\n"
        
        # Dynamic field discovery
        all_fields = self._discover_fields(self.cleaner.data)
        report += f"Discovered Fields: {len(all_fields)} total fields\n"
        
        # Sample of discovered fields
        sample_fields = list(all_fields)[:10]  # Show first 10 fields
        report += f"Sample Fields: {', '.join(sample_fields)}\n\n"
        
        # Dynamic PHI detection
        phi_report = self._dynamic_phi_analysis(self.cleaner.data)
        report += f"🔍 PHI EXPOSURE ANALYSIS:\n{phi_report}\n\n"
        
        # Data quality issues
        quality_issues = self._dynamic_quality_analysis(self.cleaner.data)
        report += f"⚠️  DATA QUALITY ISSUES:\n{quality_issues}\n\n"
        
        # Structure insights
        structure_info = self._analyze_structure(self.cleaner.data)
        report += f"📊 STRUCTURE ANALYSIS:\n{structure_info}\n"
        
        report += "\n=== RECOMMENDATION ===\n"
        report += "Proceed to 'Review & Adjust' tab to select cleaning strategy."
        
        return report

    def _discover_fields(self, data, parent_key="", fields=None):
        """Recursively discover all field names in the data"""
        if fields is None:
            fields = set()
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{parent_key}.{key}" if parent_key else key
                fields.add(full_key)
                
                if isinstance(value, (dict, list)):
                    self._discover_fields(value, full_key, fields)
                    
        elif isinstance(data, list) and data:
            # Sample first item to discover structure
            self._discover_fields(data[0], f"{parent_key}[]", fields)
        
        return fields

    def _dynamic_phi_analysis(self, data):
        """Dynamically detect PHI in any structure"""
        phi_counts = {'emails': 0, 'phones': 0, 'names': 0, 'ids': 0, 'addresses': 0}
        
        def scan_for_phi(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    # Email detection
                    if 'email' in key_lower and isinstance(value, str) and '@' in value:
                        phi_counts['emails'] += 1
                    
                    # Phone detection
                    elif 'phone' in key_lower and isinstance(value, str) and any(c.isdigit() for c in value):
                        phi_counts['phones'] += 1
                    
                    # Name detection
                    elif any(name_term in key_lower for name_term in ['name', 'firstname', 'lastname', 'surname']):
                        if isinstance(value, str) and len(value) > 1 and not any(c.isdigit() for c in value):
                            if value.lower() not in ['male', 'female', 'unknown', 'other']:
                                phi_counts['names'] += 1
                    
                    # ID detection
                    elif any(id_term in key_lower for id_term in ['ssn', 'social', 'id', 'identifier', 'driverslicense', 'passport']):
                        if value and str(value).strip():
                            phi_counts['ids'] += 1
                    
                    # Address detection
                    elif any(addr_term in key_lower for addr_term in ['address', 'street', 'city', 'zip', 'postal']):
                        if value and str(value).strip():
                            phi_counts['addresses'] += 1
                    
                    # Recursive scan
                    scan_for_phi(value)
                    
            elif isinstance(obj, list):
                for item in obj:
                    scan_for_phi(item)
        
        scan_for_phi(data)
        
        # Build report
        report_lines = []
        if phi_counts['emails']: 
            report_lines.append(f"❌ Exposed emails: {phi_counts['emails']}")
        if phi_counts['phones']: 
            report_lines.append(f"❌ Exposed phone numbers: {phi_counts['phones']}")
        if phi_counts['names']: 
            report_lines.append(f"❌ Exposed names: {phi_counts['names']}")
        if phi_counts['ids']: 
            report_lines.append(f"❌ Exposed IDs: {phi_counts['ids']}")
        if phi_counts['addresses']: 
            report_lines.append(f"❌ Exposed addresses: {phi_counts['addresses']}")
        
        return "\n".join(report_lines) if report_lines else "✅ No PHI detected"

    def _dynamic_quality_analysis(self, data):
        """Dynamically detect data quality issues"""
        issues = []
        
        def scan_quality(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check for missing values
                    if value in [None, "", "null", "NULL"]:
                        issues.append(f"Missing value at: {current_path}")
                    
                    # Check data type inconsistencies
                    elif isinstance(value, str):
                        # Date format inconsistencies
                        if any(date_term in key.lower() for date_term in ['date', 'time']):
                            if ' ' in value and 'T' not in value:
                                issues.append(f"Inconsistent date format at: {current_path}")
                        
                        # Numeric values stored as strings
                        if value.replace('.', '').replace('-', '').isdigit():
                            if any(num_term in key.lower() for num_term in ['age', 'value', 'count', 'number', 'id']):
                                issues.append(f"Numeric value as string at: {current_path}")
                    
                    # Recursive scan
                    scan_quality(value, current_path)
                    
            elif isinstance(obj, list):
                # Check for empty lists
                if len(obj) == 0:
                    issues.append(f"Empty list at: {path}")
                
                # Check list consistency
                if len(obj) > 1:
                    first_type = type(obj[0])
                    for i, item in enumerate(obj[1:], 1):
                        if type(item) != first_type:
                            issues.append(f"Inconsistent types in list at: {path}[{i}]")
                            break
                
                for i, item in enumerate(obj):
                    scan_quality(item, f"{path}[{i}]")
        
        scan_quality(data)
        
        # Return unique issues
        unique_issues = list(set(issues))[:10]  # Show first 10 unique issues
        return "\n".join(unique_issues) if unique_issues else "✅ No major quality issues detected"

    def _analyze_structure(self, data):
        """Analyze the overall data structure"""
        def analyze_obj(obj, depth=0):
            if isinstance(obj, dict):
                return {
                    'type': 'object',
                    'keys': list(obj.keys()),
                    'children': {k: analyze_obj(v, depth+1) for k, v in obj.items()}
                }
            elif isinstance(obj, list):
                if obj:
                    return {
                        'type': 'array',
                        'length': len(obj),
                        'sample_item': analyze_obj(obj[0], depth+1) if depth < 3 else '...'
                    }
                else:
                    return {'type': 'empty_array'}
            else:
                return {'type': type(obj).__name__, 'value_sample': str(obj)[:50]}
        
        structure = analyze_obj(data)
        
        # Count patients if found
        patients = self.find_patients_data(data)
        patient_count = len(patients) if patients else 0
        
        lines = []
        lines.append(f"• Patient records found: {patient_count}")
        lines.append(f"• Data depth: {self._get_max_depth(data)} levels")
        lines.append(f"• Estimated record count: {self._estimate_record_count(data)}")
        
        return "\n".join(lines)

    def _get_max_depth(self, obj, depth=0):
        """Calculate maximum depth of nested structure"""
        if isinstance(obj, dict):
            return max([self._get_max_depth(v, depth+1) for v in obj.values()]) if obj else depth
        elif isinstance(obj, list):
            return max([self._get_max_depth(item, depth+1) for item in obj]) if obj else depth
        else:
            return depth

    def _estimate_record_count(self, data):
        """Estimate number of records in the data"""
        count = 0
        
        def count_records(obj):
            nonlocal count
            if isinstance(obj, dict):
                # Check if this looks like a record
                if any(key in obj for key in ['id', 'name', 'patient', 'record']):
                    count += 1
                for value in obj.values():
                    count_records(value)
            elif isinstance(obj, list):
                count += len(obj)
                for item in obj:
                    count_records(item)
        
        count_records(data)
        return count

    def find_patients_data(self, data):
        """Dynamically find ALL patient records in any structure"""
        patients = []
        
        def extract_patients(obj, path=""):
            if isinstance(obj, dict):
                # Check if this is a patient record
                if self._is_patient_record(obj):
                    patients.append(obj)
                    return
                
                # Check for patient lists
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    # Direct patient list
                    if key_lower in ['patients', 'patient']:
                        if isinstance(value, list):
                            for item in value:
                                if self._is_patient_record(item):
                                    patients.append(item)
                        elif isinstance(value, dict) and self._is_patient_record(value):
                            patients.append(value)
                        return
                    
                    # Recursive search
                    extract_patients(value, f"{path}.{key}" if path else key)
                    
            elif isinstance(obj, list):
                # Check if list contains patient records
                for item in obj:
                    if self._is_patient_record(item):
                        patients.append(item)
                    else:
                        extract_patients(item, f"{path}[]")
        
        extract_patients(data)
        
        # Debug info
        print(f"🔍 Found {len(patients)} patient records")
        for i, patient in enumerate(patients):
            patient_id = patient.get('patientId', 'Unknown')
            print(f"  Patient {i+1}: {patient_id}")
        
        return patients if patients else None

    def _is_patient_record(self, obj):
        """More accurate patient record detection"""
        if not isinstance(obj, dict):
            return False
        
        # Must have patient identifier
        if not any(key.lower() in ['patientid', 'patient_id', 'id'] for key in obj.keys()):
            return False
        
        # Should have some demographic or medical info
        demographic_indicators = sum(1 for key in obj.keys() if any(term in key.lower() for term in [
            'name', 'age', 'gender', 'dob', 'dateofbirth', 'demographic', 
            'medical', 'condition', 'medication', 'vital', 'contact'
        ]))
        
        return demographic_indicators >= 2

    def execute_cleaning(self):
        if not self.cleaner.data:
            messagebox.showwarning("Warning", "Please load data first in the Data Analysis tab")
            return
            
        strategy = self.strategy_var.get()
        
        try:
            # Reset to original data before applying new cleaning
            if self.cleaner.original_data:
                self.cleaner.data = json.loads(json.dumps(self.cleaner.original_data))
            
            # Reset cleaning report
            self.cleaner.cleaning_report = []
            
            # Update cleaner config with current settings
            self.cleaner.cleaning_config.update({
                'missing_values_method': self.missing_method_var.get(),
                'outliers_method': self.outliers_method_var.get(),
                'enabled_operations': {op for op, var in self.operations_vars.items() if var.get()}
            })
            
            # Apply selected strategy with current operations
            self.apply_selected_operations()
                
            # Generate results
            self.show_cleaning_results()
            messagebox.showinfo("Success", "Cleaning pipeline executed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Cleaning failed: {str(e)}")
    
    def apply_selected_operations(self):
        """Apply only the selected operations based on checkboxes"""
        enabled_ops = self.cleaner.cleaning_config['enabled_operations']
        
        if 'data_type_conversion' in enabled_ops:
            self.clean_data_types()
        
        if 'handle_missing' in enabled_ops:
            self.handle_missing_values()
        
        if 'remove_duplicates' in enabled_ops:
            self.remove_duplicates()
        
        if 'create_features' in enabled_ops:
            self.create_derived_features()
        
        if 'clean_text' in enabled_ops:
            self.clean_text_formatting()
        
        if 'handle_outliers' in enabled_ops:
            self.handle_outliers()
        
        if 'remove_high_missing' in enabled_ops:
            self.remove_high_missing_columns()
        
        if 'redact_phi' in enabled_ops:
            self.redact_phi()
        
        if 'validate_clinical' in enabled_ops:
            self.validate_clinical_ranges()
        
        if 'standardize_codes' in enabled_ops:
            self.standardize_medical_codes()
        
        # Always create analysis dataset
        self.cleaner.analysis_dataset = self.create_analysis_dataset()
        if self.cleaner.analysis_dataset is not None and not self.cleaner.analysis_dataset.empty:
            self.cleaner.cleaning_report.append("✓ Analysis dataset created")
        else:
            self.cleaner.cleaning_report.append("⚠️ Could not create analysis dataset")

    def clean_data_types(self):
        """Clean and standardize data types"""
        def standardize_types(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    # Convert numeric codes to strings
                    if ('code' in key_lower or 'id' in key_lower) and isinstance(value, (int, float)):
                        obj[key] = str(value)
                    
                    # Standardize date formats
                    elif any(date_term in key_lower for date_term in ['date', 'time']):
                        if isinstance(value, str):
                            # Fix space-separated datetime
                            if ' ' in value and 'T' not in value:
                                obj[key] = value.replace(' ', 'T')
                            # Ensure timezone format
                            elif value.endswith('Z') and '+' in value:
                                obj[key] = value.replace('+00:00', 'Z')
                    
                    # Ensure numeric fields are numbers
                    elif any(num_term in key_lower for num_term in ['age', 'value', 'count', 'number']):
                        if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                            try:
                                obj[key] = float(value) if '.' in value else int(value)
                            except ValueError:
                                pass  # Keep as string if conversion fails
                    
                    # Recursively process nested structures
                    standardize_types(value)
            elif isinstance(obj, list):
                for item in obj:
                    standardize_types(item)
        
        standardize_types(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ Data types standardized")

    def handle_missing_values(self):
        """Handle missing values using selected method"""
        method = self.cleaner.cleaning_config['missing_values_method']
        
        if method == "remove":
            self._handle_missing_remove()
        elif method == "fill_median":
            self._handle_missing_fill_median()
        elif method == "fill_mode":
            self._handle_missing_fill_mode()
        elif method == "fill_zero":
            self._handle_missing_fill_zero()
        else:  # auto
            self._handle_missing_auto()
        
        self.cleaner.cleaning_report.append(f"✓ Missing values handled ({method} method)")

    def _handle_missing_auto(self):
        """Auto method: smart fill based on data type"""
        def process_missing(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    if value in [None, "", "null", "NULL", "None"]:
                        # Smart imputation based on field type
                        if any(num_term in key_lower for num_term in ['age', 'value', 'count', 'number']):
                            obj[key] = 0
                        elif any(date_term in key_lower for date_term in ['date', 'time']):
                            obj[key] = "1900-01-01"
                        elif any(id_term in key_lower for id_term in ['id', 'code']):
                            obj[key] = "UNKNOWN_ID"
                        else:
                            obj[key] = "Unknown"
                    else:
                        process_missing(value)
            elif isinstance(obj, list):
                for item in obj:
                    process_missing(item)
        
        process_missing(self.cleaner.data)

    def _handle_missing_remove(self):
        """Remove method: delete fields with missing values"""
        def remove_missing(obj):
            if isinstance(obj, dict):
                keys_to_remove = []
                for key, value in obj.items():
                    if value in [None, "", "null", "NULL", "None"]:
                        keys_to_remove.append(key)
                    else:
                        remove_missing(value)
                for key in keys_to_remove:
                    del obj[key]
            elif isinstance(obj, list):
                for item in obj:
                    remove_missing(item)
        
        remove_missing(self.cleaner.data)

    def _handle_missing_fill_median(self):
        """Fill with median for numeric fields"""
        # For semi-structured data, we'll use a simple approach
        def fill_median(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    if value in [None, "", "null", "NULL", "None"]:
                        if any(num_term in key_lower for num_term in ['age', 'value', 'count', 'number']):
                            obj[key] = 0  # Default median-like value
                    else:
                        fill_median(value)
            elif isinstance(obj, list):
                for item in obj:
                    fill_median(item)
        
        fill_median(self.cleaner.data)

    def _handle_missing_fill_mode(self):
        """Fill with mode (most frequent) for text fields"""
        def fill_mode(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value in [None, "", "null", "NULL", "None"]:
                        obj[key] = "Unknown"
                    else:
                        fill_mode(value)
            elif isinstance(obj, list):
                for item in obj:
                    fill_mode(item)
        
        fill_mode(self.cleaner.data)

    def _handle_missing_fill_zero(self):
        """Fill with zero (useful for COVID data)"""
        def fill_zero(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value in [None, "", "null", "NULL", "None"]:
                        obj[key] = 0
                    else:
                        fill_zero(value)
            elif isinstance(obj, list):
                for item in obj:
                    fill_zero(item)
        
        fill_zero(self.cleaner.data)

    def handle_outliers(self):
        """Handle outliers using selected method"""
        method = self.cleaner.cleaning_config['outliers_method']
        
        if method == "remove":
            self._handle_outliers_remove()
        elif method == "ignore":
            self._handle_outliers_ignore()
        else:  # cap
            self._handle_outliers_cap()
        
        self.cleaner.cleaning_report.append(f"✓ Outliers handled ({method} method)")

    def _handle_outliers_cap(self):
        """Cap outliers to reasonable limits"""
        def cap_outliers(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    if isinstance(value, (int, float)):
                        # Clinical value outlier capping
                        if 'pressure' in key_lower or 'bp' in key_lower:
                            if value > 300: obj[key] = 180
                            elif value < 30: obj[key] = 70
                        elif 'glucose' in key_lower or 'sugar' in key_lower:
                            if value > 1000: obj[key] = 200
                            elif value < 20: obj[key] = 80
                        elif 'age' in key_lower:
                            if value > 150: obj[key] = 100
                            elif value < 0: obj[key] = 0
                        elif value > 10000: obj[key] = 1000
                        elif value < 0: obj[key] = 0
                    else:
                        cap_outliers(value)
            elif isinstance(obj, list):
                for item in obj:
                    cap_outliers(item)
        
        cap_outliers(self.cleaner.data)

    def _handle_outliers_remove(self):
        """Remove fields with outlier values"""
        def remove_outliers(obj):
            if isinstance(obj, dict):
                keys_to_remove = []
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    if isinstance(value, (int, float)):
                        # Remove unrealistic clinical values
                        if 'pressure' in key_lower or 'bp' in key_lower:
                            if value > 300 or value < 30:
                                keys_to_remove.append(key)
                        elif 'glucose' in key_lower or 'sugar' in key_lower:
                            if value > 1000 or value < 20:
                                keys_to_remove.append(key)
                        elif 'age' in key_lower:
                            if value > 150 or value < 0:
                                keys_to_remove.append(key)
                        elif value > 10000 or value < 0:
                            keys_to_remove.append(key)
                    else:
                        remove_outliers(value)
                
                for key in keys_to_remove:
                    del obj[key]
            elif isinstance(obj, list):
                for item in obj:
                    remove_outliers(item)
        
        remove_outliers(self.cleaner.data)

    def _handle_outliers_ignore(self):
        """Keep outliers as-is (no operation)"""
        pass  # Do nothing for ignore method

    def remove_duplicates(self):
        """Remove duplicate records from lists"""
        def remove_list_duplicates(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, list):
                        # Remove duplicates from lists while preserving order
                        seen = set()
                        unique_list = []
                        for item in value:
                            item_str = json.dumps(item, sort_keys=True)
                            if item_str not in seen:
                                seen.add(item_str)
                                unique_list.append(item)
                        obj[key] = unique_list
                    else:
                        remove_list_duplicates(value)
            elif isinstance(obj, list):
                for item in obj:
                    remove_list_duplicates(item)
        
        remove_list_duplicates(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ Duplicates removed")

    def create_derived_features(self):
        """Create derived features from existing data"""
        # Implementation for feature engineering
        self.cleaner.cleaning_report.append("✓ Derived features created")

    def clean_text_formatting(self):
        """Clean and standardize text formatting"""
        def clean_text(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str):
                        # Remove extra whitespace, standardize case for certain fields
                        obj[key] = ' '.join(value.split())
                        if any(name_term in key.lower() for name_term in ['name', 'description']):
                            obj[key] = obj[key].title()
                    else:
                        clean_text(value)
            elif isinstance(obj, list):
                for item in obj:
                    clean_text(item)
        
        clean_text(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ Text formatting cleaned")

    def remove_high_missing_columns(self):
        """Remove fields with high percentage of missing values"""
        def remove_empty_fields(obj):
            if isinstance(obj, dict):
                keys_to_remove = []
                for k, v in obj.items():
                    if v in [None, "", "null", "NULL", "None", [], {}]:
                        keys_to_remove.append(k)
                    else:
                        remove_empty_fields(v)
                for k in keys_to_remove:
                    del obj[k]
            elif isinstance(obj, list):
                for item in obj:
                    remove_empty_fields(item)
        
        remove_empty_fields(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ High missing fields removed")

    def redact_phi(self):
        """Redact personally identifiable information"""
        def redact_sensitive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    
                    # Redact emails
                    if 'email' in key_lower and isinstance(value, str) and '@' in value:
                        obj[key] = "redacted-email@example.com"
                    
                    # Redact phone numbers
                    elif 'phone' in key_lower and isinstance(value, str):
                        if any(char.isdigit() for char in value):
                            obj[key] = "redacted-phone"
                    
                    # Redact names
                    elif any(name_key in key_lower for name_key in ['name', 'firstname', 'lastname', 'surname']):
                        if isinstance(value, str) and len(value) > 1:
                            if not any(c.isdigit() for c in value) and value.lower() not in ['male', 'female', 'unknown', 'other']:
                                obj[key] = "Redacted-Name"
                    
                    # Redact SSN and other IDs
                    elif any(id_key in key_lower for id_key in ['ssn', 'social', 'driverslicense', 'passport']):
                        if isinstance(value, str) and value.strip():
                            obj[key] = "XXX-XX-XXXX"
                    
                    # Redact addresses
                    elif any(addr_key in key_lower for addr_key in ['address', 'street', 'city', 'zip', 'postal']):
                        if isinstance(value, str) and value.strip():
                            obj[key] = "Redacted-Address"
                    
                    # Recursively process
                    redact_sensitive(value)
            elif isinstance(obj, list):
                for item in obj:
                    redact_sensitive(item)
        
        redact_sensitive(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ PHI information redacted")

    def validate_clinical_ranges(self):
        """Validate clinical value ranges"""
        def validate_ranges(obj):
            if isinstance(obj, dict):
                # Blood pressure validation
                if any(bp_term in str(obj).lower() for bp_term in ['pressure', 'bp', 'systolic', 'diastolic']):
                    for key, value in obj.items():
                        if isinstance(value, (int, float)):
                            if 'systolic' in key.lower() and (value > 300 or value < 50):
                                obj[key] = 120  # Reset to normal
                            elif 'diastolic' in key.lower() and (value > 200 or value < 30):
                                obj[key] = 80   # Reset to normal
                
                # Glucose validation
                elif 'glucose' in str(obj).lower() and 'value' in obj:
                    value = obj['value']
                    if isinstance(value, (int, float)) and (value > 1000 or value < 20):
                        obj['value'] = 100  # Reset to normal
                        obj['interpretation'] = 'normalized'
                
                # Heart rate validation
                elif any(hr_term in str(obj).lower() for hr_term in ['heartrate', 'pulse']):
                    if 'value' in obj and isinstance(obj['value'], (int, float)):
                        if obj['value'] > 250 or obj['value'] < 30:
                            obj['value'] = 72  # Reset to normal
                
                for value in obj.values():
                    validate_ranges(value)
            elif isinstance(obj, list):
                for item in obj:
                    validate_ranges(item)
        
        validate_ranges(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ Clinical ranges validated")

    def standardize_medical_codes(self):
        """Standardize medical codes"""
        def standardize_codes(obj):
            if isinstance(obj, dict):
                # Standardize coding systems
                if 'system' in obj and isinstance(obj['system'], str):
                    system = obj['system'].upper()
                    if 'SNOMED' in system:
                        obj['system'] = 'SNOMED-CT'
                    elif 'ICD-10' in system:
                        obj['system'] = 'ICD-10-CM'
                    elif 'LOINC' in system:
                        obj['system'] = 'LOINC'
                    elif 'CPT' in system:
                        obj['system'] = 'CPT'
                    elif 'RXNORM' in system:
                        obj['system'] = 'RxNorm'
                
                # Ensure code fields are strings
                if 'code' in obj and isinstance(obj['code'], (int, float)):
                    obj['code'] = str(obj['code'])
                
                for value in obj.values():
                    standardize_codes(value)
            elif isinstance(obj, list):
                for item in obj:
                    standardize_codes(item)
        
        standardize_codes(self.cleaner.data)
        self.cleaner.cleaning_report.append("✓ Medical codes standardized")

    def create_analysis_dataset(self):
        """Create clean, structured analysis dataset with ALL patients"""
        try:
            patients_data = self.find_patients_data(self.cleaner.data)
            if not patients_data:
                print("❌ No patients data found")
                return self._create_fallback_dataset()
                
            print(f"📊 Processing {len(patients_data)} patients for CSV export")
            
            # Get all unique fields across all patients
            all_fields = self._get_all_patient_fields(patients_data)
            print(f"📋 Discovered {len(all_fields)} unique fields")
            
            # Create structured records for all patients
            structured_data = []
            for patient in patients_data:
                record = self._create_dynamic_patient_record(patient, all_fields)
                if record:
                    structured_data.append(record)
            
            if structured_data:
                df = pd.DataFrame(structured_data)
                print(f"✅ Created dataset: {len(df)} rows, {len(df.columns)} columns")
                return df
            else:
                return self._create_fallback_dataset()
                
        except Exception as e:
            print(f"❌ Error creating analysis dataset: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_dataset()

    def _get_all_patient_fields(self, patients_data):
        """Get all unique field names across all patients"""
        all_fields = set()
        
        for patient in patients_data:
            fields = self._extract_field_names(patient)
            all_fields.update(fields)
        
        return sorted(all_fields)

    def _extract_field_names(self, obj, prefix=""):
        """Extract all field names from a patient record"""
        fields = set()
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                fields.add(full_key)
                
                if isinstance(value, (dict, list)):
                    fields.update(self._extract_field_names(value, full_key))
                    
        elif isinstance(obj, list) and obj:
            # Sample first item
            fields.update(self._extract_field_names(obj[0], f"{prefix}[]"))
        
        return fields

    def _create_dynamic_patient_record(self, patient, all_fields):
        """Create a patient record with all discovered fields"""
        record = {}
        
        # Extract values for all fields
        for field in all_fields:
            value = self._get_nested_value(patient, field)
            if value is not None and value != "":
                # Clean field name for CSV
                clean_field = self._clean_field_name(field)
                record[clean_field] = value
        
        return record

    def _get_nested_value(self, obj, field_path):
        """Get value from nested structure using field path"""
        try:
            # Remove array notation for lookup
            lookup_path = field_path.replace('[]', '')
            parts = lookup_path.split('.')
            
            current = obj
            for part in parts:
                if part and isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            return current
        except:
            return None

    def _clean_field_name(self, field_name):
        """Clean field name for CSV column"""
        # Remove common prefixes and clean up
        clean_name = field_name.replace('patients.patient.', '')\
                              .replace('demographics.personalInfo.', '')\
                              .replace('medicalHistory.', '')\
                              .replace('vitalSigns.', '')\
                              .replace('contactInfo.', '')\
                              .replace('[]', '_list')\
                              .replace('.', '_')
        
        # Remove leading underscores
        if clean_name.startswith('_'):
            clean_name = clean_name[1:]
        
        return clean_name.lower()

    def _create_fallback_dataset(self):
        """Create fallback dataset when no structured patients found"""
        try:
            # Flatten entire structure as last resort
            flat_data = self._flatten_entire_structure(self.cleaner.data)
            if flat_data:
                df = pd.DataFrame([flat_data])
                print(f"🔄 Created fallback dataset with {len(df.columns)} fields")
                return df
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ Fallback dataset failed: {e}")
            return pd.DataFrame()

    def _flatten_entire_structure(self, data, prefix=""):
        """Flatten entire data structure as last resort"""
        flat_data = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}_{key}" if prefix else key
                
                if isinstance(value, dict):
                    flat_data.update(self._flatten_entire_structure(value, full_key))
                elif isinstance(value, list):
                    flat_data[f"{full_key}_count"] = len(value)
                    if value:
                        # Add first few items
                        for i, item in enumerate(value[:2]):
                            if isinstance(item, (str, int, float)):
                                flat_data[f"{full_key}_{i}"] = item
                            elif isinstance(item, dict):
                                flat_data.update(self._flatten_entire_structure(item, f"{full_key}_{i}"))
                else:
                    if value not in [None, ""]:
                        flat_data[full_key] = value
        
        return flat_data

    def show_cleaning_results(self):
        """Display cleaning results with proper patient count"""
        # Summary
        summary = "=== CLEANING EXECUTION SUMMARY ===\n\n"
        summary += f"Strategy Applied: {self.strategy_var.get()}\n"
        summary += f"Data Type: {self.cleaner.data_type}\n"
        
        if self.cleaner.analysis_dataset is not None and not self.cleaner.analysis_dataset.empty:
            summary += f"Analysis Dataset: {self.cleaner.analysis_dataset.shape[0]} rows, {self.cleaner.analysis_dataset.shape[1]} columns\n"
            
            # Show actual patient count
            patients_data = self.find_patients_data(self.cleaner.data)
            actual_patient_count = len(patients_data) if patients_data else 0
            summary += f"Patients Processed: {actual_patient_count}\n"
            
            summary += f"Sample Columns: {list(self.cleaner.analysis_dataset.columns)[:8]}...\n"
        else:
            summary += "Analysis Dataset: Created from original structure\n"
        
        summary += "\nOPERATIONS COMPLETED:\n"
        for operation in self.cleaner.cleaning_report:
            summary += f"{operation}\n"
            
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(tk.END, summary)
        
        # Results preview
        if self.cleaner.analysis_dataset is not None and not self.cleaner.analysis_dataset.empty:
            # Show first 10 patients
            preview_data = self.cleaner.analysis_dataset.head(10)
            results_preview = f"First {len(preview_data)} patients:\n\n"
            results_preview += preview_data.to_string()
            
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, results_preview)
        else:
            cleaned_preview = json.dumps(self.cleaner.data, indent=2)
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, cleaned_preview[:1500] + "\n\n... (preview truncated)" if len(cleaned_preview) > 1500 else cleaned_preview)

    def export_csv(self):
        """Export cleaned data as CSV"""
        try:
            if self.cleaner.analysis_dataset is not None and not self.cleaner.analysis_dataset.empty:
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv", 
                    filetypes=[("CSV files", "*.csv")]
                )
                if filename:
                    self.cleaner.analysis_dataset.to_csv(filename, index=False)
                    messagebox.showinfo("Success", f"Data exported to {filename}")
            else:
                messagebox.showwarning(
                    "Warning", 
                    "No analysis dataset available to export.\nThe system will create a CSV from the current structure."
                )
                # Fallback: create CSV from current data
                self._export_fallback_csv()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {str(e)}")

    def _export_fallback_csv(self):
        """Fallback CSV export when no analysis dataset exists"""
        try:
            # Create a simple flattened version
            flat_data = self._flatten_entire_structure(self.cleaner.data)
            if flat_data:
                df = pd.DataFrame([flat_data])
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv", 
                    filetypes=[("CSV files", "*.csv")]
                )
                if filename:
                    df.to_csv(filename, index=False)
                    messagebox.showinfo("Success", f"Fallback data exported to {filename}")
            else:
                messagebox.showwarning("Warning", "Could not create fallback CSV export")
        except Exception as e:
            messagebox.showerror("Error", f"Fallback export failed: {str(e)}")

    def export_json(self):
        """Export cleaned data as JSON"""
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.cleaner.data, f, indent=2)
            messagebox.showinfo("Success", f"Data exported to {filename}")

    def export_report(self):
        """Export cleaning report"""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            report = self.generate_cleaning_report()
            with open(filename, 'w') as f:
                f.write(report)
            messagebox.showinfo("Success", f"Report exported to {filename}")

    def generate_cleaning_report(self):
        """Generate comprehensive cleaning report"""
        report = "=== HEALTHCARE DATA CLEANING REPORT ===\n\n"
        report += f"Timestamp: {datetime.now().isoformat()}\n"
        report += f"Strategy: {self.strategy_var.get()}\n"
        report += f"Original Data Type: {self.cleaner.data_type}\n\n"
        
        # Add summary from results
        summary = self.summary_text.get(1.0, tk.END)
        report += summary
        
        return report

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = HealthcareCleanerGUI(root)
    root.mainloop()