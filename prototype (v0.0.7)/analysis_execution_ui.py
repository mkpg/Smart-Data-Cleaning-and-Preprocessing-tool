#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Any
import re
import yaml

class EnhancedDataCleaner:
    def __init__(self, root):
        self.root = root
        self.root.title("🏥 Smart Data Cleaner - Enhanced")
        self.root.geometry("1200x900")
        
        self.data = None
        self.cleaned_data = None
        self.column_analysis = {}
        self.user_adjustments = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI with enhanced features"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Data Analysis (READ-ONLY)
        self.setup_analysis_tab(notebook)
        
        # Tab 2: Review & Adjust Operations (USER CAN MODIFY)
        self.setup_review_tab(notebook)
        
        # Tab 3: Execute & Results
        self.setup_execution_tab(notebook)
    
    def setup_analysis_tab(self, notebook):
        """Tab for data loading and analysis"""
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="🔍 Data Analysis")
        
        # File selection
        ttk.Label(analysis_frame, text="Select Dataset:", font=('Arial', 10, 'bold')).grid(
            row=0, column=0, sticky='w', pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Entry(analysis_frame, textvariable=self.file_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(analysis_frame, text="Browse", command=self.browse_file).grid(row=0, column=2)
        ttk.Button(analysis_frame, text="Load & Analyze", command=self.load_and_analyze, 
                  style='Accent.TButton').grid(row=0, column=3)
        
        # Analysis results
        analysis_results = ttk.LabelFrame(analysis_frame, text="Dataset Analysis Results", padding=10)
        analysis_results.grid(row=1, column=0, columnspan=4, sticky='nsew', pady=10)
        
        # Dataset overview
        ttk.Label(analysis_results, text="📊 Dataset Overview:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky='w')
        self.overview_text = scrolledtext.ScrolledText(analysis_results, height=6, width=100, state='disabled')
        self.overview_text.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=5)
        
        # Data quality issues
        ttk.Label(analysis_results, text="⚠️ Data Quality Issues:", font=('Arial', 9, 'bold')).grid(
            row=2, column=0, sticky='w', pady=(10,0))
        self.issues_text = scrolledtext.ScrolledText(analysis_results, height=8, width=100, state='disabled')
        self.issues_text.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=5)
        
        analysis_frame.columnconfigure(1, weight=1)
        analysis_frame.rowconfigure(1, weight=1)
        analysis_results.columnconfigure(0, weight=1)
        analysis_results.rowconfigure(3, weight=1)
    
    def setup_review_tab(self, notebook):
        """Tab where users can REVIEW and ADJUST operations"""
        review_frame = ttk.Frame(notebook)
        notebook.add(review_frame, text="⚙️ Review & Adjust")
        
        # Strategy selection
        strategy_frame = ttk.LabelFrame(review_frame, text="Cleaning Strategy", padding=10)
        strategy_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(strategy_frame, text="Base Strategy:").grid(row=0, column=0, sticky='w')
        self.strategy_var = tk.StringVar(value="auto_smart")
        strategies = ttk.Combobox(strategy_frame, textvariable=self.strategy_var, 
                                 values=["auto_smart", "aggressive", "conservative", "healthcare_specific", "custom_yaml"])
        strategies.grid(row=0, column=1, sticky='w', padx=5)
        strategies.bind('<<ComboboxSelected>>', self.on_strategy_change)
        
        # ADD YAML UPLOAD BUTTON HERE
        self.yaml_btn = ttk.Button(strategy_frame, text="📁 Upload YAML", command=self.upload_yaml_config)
        self.yaml_btn.grid(row=0, column=2, padx=5)
        self.yaml_path = tk.StringVar()
        ttk.Label(strategy_frame, textvariable=self.yaml_path, width=30).grid(row=0, column=3)
        
        # Operations adjustment frame
        self.operations_frame = ttk.LabelFrame(review_frame, text="Adjust Cleaning Operations", padding=10)
        self.operations_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.operation_widgets = {}
        
        # Operations summary
        self.summary_text = scrolledtext.ScrolledText(review_frame, height=8, width=100, state='disabled')
        self.summary_text.pack(fill='x', padx=10, pady=5)
        
        review_frame.columnconfigure(0, weight=1)
        review_frame.rowconfigure(1, weight=1)
    
    def setup_execution_tab(self, notebook):
        """Tab for execution and results"""
        execution_frame = ttk.Frame(notebook)
        notebook.add(execution_frame, text="🚀 Execute & Results")
        
        # Final operations summary
        final_frame = ttk.LabelFrame(execution_frame, text="Final Operations Summary", padding=10)
        final_frame.pack(fill='x', padx=10, pady=10)
        
        self.final_summary_text = scrolledtext.ScrolledText(final_frame, height=6, width=100, state='disabled')
        self.final_summary_text.pack(fill='x')
        
        # Execute button
        ttk.Button(execution_frame, text="🚀 EXECUTE WITH ADJUSTMENTS", command=self.execute_cleaning,
                  style='Accent.TButton').pack(pady=20)
        
        # Results display
        results_frame = ttk.LabelFrame(execution_frame, text="📊 Cleaning Results", padding=10)
        results_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=100, state='normal')
        self.results_text.pack(fill='both', expand=True)
        
        # Export buttons
        export_frame = ttk.Frame(execution_frame)
        export_frame.pack(fill='x', pady=10)
        
        ttk.Button(export_frame, text="💾 Export Cleaned Data", command=self.export_data).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📄 Export Cleaning Report", command=self.export_report).pack(side='left', padx=5)
    
    def browse_file(self):
        """Browse for CSV file"""
        filename = filedialog.askopenfilename(
            title="Select Dataset",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
    
    def load_and_analyze(self):
        """Load data and perform analysis"""
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select a file first")
            return
        
        try:
            # Load data
            if self.file_path.get().endswith('.csv'):
                self.data = pd.read_csv(self.file_path.get())
            else:
                self.data = pd.read_excel(self.file_path.get())
            
            # Perform analysis
            self.analyze_dataset()
            
            # Update review tab
            self.update_review_tab()
            
            messagebox.showinfo("Success", "Data loaded and analyzed! Review operations in the next tab.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def analyze_dataset(self):
        """Perform comprehensive data analysis"""
        self.column_analysis = {}
        
        # Basic overview
        overview = f"""📊 DATASET OVERVIEW:
{'='*50}
• Shape: {self.data.shape[0]} rows × {self.data.shape[1]} columns
• Memory Usage: {self.data.memory_usage(deep=True).sum() / 1024**2:.2f} MB
• Total Cells: {self.data.size:,}
• Data Types: {dict(self.data.dtypes.value_counts())}
"""
        
        self.overview_text.config(state='normal')
        self.overview_text.delete(1.0, tk.END)
        self.overview_text.insert(1.0, overview)
        self.overview_text.config(state='disabled')
        
        # Data quality issues
        issues = ["⚠️ DATA QUALITY ISSUES:", "="*50]
        
        # Enhanced data type analysis
        type_issues = self.analyze_data_types()
        issues.extend(type_issues)
        
        # Missing values
        missing_values = self.data.isnull().sum()
        total_missing = missing_values.sum()
        if total_missing > 0:
            issues.append(f"❌ MISSING VALUES: {total_missing} total missing cells")
            for col in missing_values[missing_values > 0].index:
                percent = (missing_values[col] / len(self.data)) * 100
                issues.append(f"   📍 {col}: {missing_values[col]} missing ({percent:.1f}%)")
        
        # Duplicates
        duplicate_rows = self.data.duplicated().sum()
        if duplicate_rows > 0:
            issues.append(f"❌ DUPLICATE ROWS: {duplicate_rows} duplicate records")
        
        # Column analysis
        for column in self.data.columns:
            col_data = self.data[column]
            col_analysis = {
                'data_type': str(col_data.dtype),
                'missing_count': col_data.isnull().sum(),
                'unique_count': col_data.nunique(),
                'issues': []
            }
            
            # Enhanced issue detection
            if pd.api.types.is_numeric_dtype(col_data):
                if (col_data < 0).any():
                    col_analysis['issues'].append("negative values")
                
                # Outliers
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                if IQR > 0:
                    outliers = col_data[(col_data < (Q1 - 1.5 * IQR)) | (col_data > (Q3 + 1.5 * IQR))]
                    if len(outliers) > 0:
                        col_analysis['issues'].append(f"{len(outliers)} outliers")
            
            elif col_data.dtype == 'object':
                if col_data.str.contains(r'[^\w\s]', na=False).any():
                    col_analysis['issues'].append("special characters")
                if col_data.str.contains(r'\s{2,}', na=False).any():
                    col_analysis['issues'].append("extra spaces")
                # Detect potential formatted numbers
                if self.has_formatted_numbers(col_data):
                    col_analysis['issues'].append("formatted numbers (commas/currency)")
                # Detect potential dates
                if self.has_potential_dates(col_data):
                    col_analysis['issues'].append("potential date strings")
            
            self.column_analysis[column] = col_analysis
            
            # Add to issues
            if col_analysis['issues']:
                issues.append(f"❌ {column}: {', '.join(col_analysis['issues'])}")
        
        self.issues_text.config(state='normal')
        self.issues_text.delete(1.0, tk.END)
        self.issues_text.insert(1.0, "\n".join(issues))
        self.issues_text.config(state='disabled')
    
    def analyze_data_types(self):
        """Enhanced data type analysis"""
        issues = []
        
        for column in self.data.columns:
            col_data = self.data[column]
            
            # Detect formatted numbers
            if col_data.dtype == 'object' and self.has_formatted_numbers(col_data):
                issues.append(f"🔢 {column}: Contains formatted numbers (commas/currency)")
            
            # Detect potential dates
            if col_data.dtype == 'object' and self.has_potential_dates(col_data):
                issues.append(f"📅 {column}: Contains potential date strings")
            
            # Detect mixed types
            if self.has_mixed_types(col_data):
                issues.append(f"🔄 {column}: Contains mixed data types")
        
        return issues
    
    def has_formatted_numbers(self, series):
        """Check if series contains formatted numbers"""
        if series.dtype != 'object':
            return False
        
        # Patterns for formatted numbers
        patterns = [
            r',',  # Commas as thousand separators
            r'\$',  # Currency symbols
            r'%',   # Percentage symbols
        ]
        
        for pattern in patterns:
            if series.astype(str).str.contains(pattern, na=False).any():
                return True
        return False
    
    def has_potential_dates(self, series):
        """Check if series contains potential date strings"""
        if series.dtype != 'object':
            return False
        
        # Common date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY etc.
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD etc.
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # Month names
        ]
        
        for pattern in date_patterns:
            if series.astype(str).str.contains(pattern, na=False).any():
                return True
        return False
    
    def has_mixed_types(self, series):
        """Detect mixed data types in column"""
        if series.dtype != 'object':
            return False
        
        # Check for mixed numeric and text
        numeric_count = pd.to_numeric(series, errors='coerce').notna().sum()
        text_count = len(series) - numeric_count - series.isna().sum()
        
        return numeric_count > 0 and text_count > 0
    
    def on_strategy_change(self, event=None):
        """When user changes strategy"""
        if self.data is not None:
            self.update_review_tab()
    
    def upload_yaml_config(self):
        """Upload and parse YAML configuration"""
        filename = filedialog.askopenfilename(
            title="Select YAML Configuration",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.yaml_config = self.load_yaml_config(filename)
                self.strategy_var.set("custom_yaml")
                self.yaml_path.set(os.path.basename(filename))
                self.update_review_tab()
                messagebox.showinfo("Success", "YAML configuration loaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load YAML: {e}")
    
    def load_yaml_config(self, filepath):
        """Load and validate YAML configuration"""
        with open(filepath, 'r') as file:
            config = yaml.safe_load(file)
        
        # Validate required sections
        required_sections = ['operations']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section: {section}")
        
        return config
    
    def create_custom_operations(self):
        """Create operations based on YAML configuration"""
        if not hasattr(self, 'yaml_config'):
            return
        
        row = 0
        ttk.Label(self.operations_frame, text="🎯 Custom Operations (YAML):", 
                  font=('Arial', 9, 'bold')).grid(row=row, column=0, sticky='w', pady=(0,10))
        row += 1
        
        # Create checkboxes for each operation defined in YAML
        for op_name, op_config in self.yaml_config['operations'].items():
            var = tk.BooleanVar(value=op_config.get('enabled', True))
            cb = ttk.Checkbutton(self.operations_frame, text=op_config['description'], 
                               variable=var, command=self.update_operations_summary)
            cb.grid(row=row, column=0, sticky='w', padx=20)
            
            # Add method selector if options available
            if 'methods' in op_config:
                method_var = tk.StringVar(value=op_config.get('default_method', ''))
                method_cb = ttk.Combobox(self.operations_frame, values=op_config['methods'], 
                                       textvariable=method_var, width=15)
                method_cb.set(op_config.get('default_method', ''))
                method_cb.grid(row=row, column=1, sticky='w')
                method_cb.bind('<<ComboboxSelected>>', self.update_operations_summary)
                self.operation_widgets[op_name] = {'var': var, 'method': method_cb}
            else:
                self.operation_widgets[op_name] = {'var': var}
            
            row += 1
    
    def update_review_tab(self):
        """Update the review tab with operations"""
        for widget in self.operations_frame.winfo_children():
            widget.destroy()
        
        self.operation_widgets = {}
        strategy = self.strategy_var.get()
        
        if strategy == "auto_smart":
            self.create_smart_operations()
        elif strategy == "aggressive":
            self.create_aggressive_operations()
        elif strategy == "conservative":
            self.create_conservative_operations()
        elif strategy == "healthcare_specific":
            self.create_healthcare_operations()
        elif strategy == "custom_yaml":
            self.create_custom_operations()
        
        self.update_operations_summary()
    
    def apply_custom_with_adjustments(self):
        """Apply custom cleaning based on YAML configuration"""
        operations_log = []
        data = self.data.copy()

        for op_name, widgets in self.operation_widgets.items():
            if widgets['var'].get():
                op_config = self.yaml_config['operations'][op_name]
                method = widgets.get('method', ttk.Combobox()).get() if 'method' in widgets else None

                # Map YAML operations to existing methods
                if op_name == "smart_type_conversion":
                    data, log = self.detect_and_convert_data_types(data)
                    operations_log.extend(log)
                elif op_name == "handle_missing":
                    data, log = self.handle_missing_values(data, method or op_config.get('default_method', 'auto'))
                    operations_log.extend(log)
                elif op_name == "feature_engineering":
                    data, log = self.create_derived_features(data)
                    operations_log.extend(log)
                elif op_name == "remove_duplicates":
                    dup_before = len(data)
                    data = data.drop_duplicates()
                    if len(data) < dup_before:
                        operations_log.append(f"✅ Removed {dup_before - len(data)} duplicate rows")
                # Add more mappings as needed

                operations_log.append(f"✅ Custom: {op_config['description']}")
    
        self.cleaned_data = data
        return operations_log
    
    def create_smart_operations(self):
        """Create operations for smart cleaning"""
        row = 0
        
        # Global operations
        ttk.Label(self.operations_frame, text="🌐 Global Operations:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky='w', pady=(0,10))
        row += 1
        
        # Data type conversion
        dtype_var = tk.BooleanVar(value=True)
        dtype_cb = ttk.Checkbutton(self.operations_frame, text="Smart data type conversion", 
                                  variable=dtype_var, command=self.update_operations_summary)
        dtype_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['smart_type_conversion'] = {'var': dtype_var}
        
        # Handle missing values
        missing_var = tk.BooleanVar(value=True)
        missing_cb = ttk.Checkbutton(self.operations_frame, text="Handle missing values", 
                                    variable=missing_var, command=self.update_operations_summary)
        missing_cb.grid(row=row, column=0, sticky='w', padx=20)
        
        missing_method = ttk.Combobox(self.operations_frame, values=["auto", "remove", "fill_median", "fill_mode"], width=15)
        missing_method.set("auto")
        missing_method.grid(row=row, column=1, sticky='w')
        missing_method.bind('<<ComboboxSelected>>', self.update_operations_summary)
        row += 1
        self.operation_widgets['handle_missing'] = {'var': missing_var, 'method': missing_method}
        
        # Remove duplicates
        dup_var = tk.BooleanVar(value=True)
        dup_cb = ttk.Checkbutton(self.operations_frame, text="Remove duplicate rows", 
                                variable=dup_var, command=self.update_operations_summary)
        dup_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['remove_duplicates'] = {'var': dup_var}
        
        # Feature engineering
        feature_var = tk.BooleanVar(value=True)
        feature_cb = ttk.Checkbutton(self.operations_frame, text="Create derived features", 
                                    variable=feature_var, command=self.update_operations_summary)
        feature_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['feature_engineering'] = {'var': feature_var}
        
        # Clean text
        text_var = tk.BooleanVar(value=True)
        text_cb = ttk.Checkbutton(self.operations_frame, text="Clean text formatting", 
                                 variable=text_var, command=self.update_operations_summary)
        text_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['clean_text'] = {'var': text_var}
        
        # Handle outliers
        outlier_var = tk.BooleanVar(value=True)
        outlier_cb = ttk.Checkbutton(self.operations_frame, text="Handle outliers", 
                                    variable=outlier_var, command=self.update_operations_summary)
        outlier_cb.grid(row=row, column=0, sticky='w', padx=20)
        
        outlier_method = ttk.Combobox(self.operations_frame, values=["cap", "remove", "ignore"], width=15)
        outlier_method.set("cap")
        outlier_method.grid(row=row, column=1, sticky='w')
        outlier_method.bind('<<ComboboxSelected>>', self.update_operations_summary)
        row += 1
        self.operation_widgets['handle_outliers'] = {'var': outlier_var, 'method': outlier_method}
    
    def create_aggressive_operations(self):
        """Create operations for aggressive cleaning"""
        self.create_smart_operations()
        row = len(self.operation_widgets) + 5
        
        ttk.Label(self.operations_frame, text="⚡ Aggressive Options:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky='w', pady=(20,10))
        row += 1
        
        high_missing_var = tk.BooleanVar(value=True)
        high_missing_cb = ttk.Checkbutton(self.operations_frame, text="Remove columns with >50% missing values", 
                                         variable=high_missing_var, command=self.update_operations_summary)
        high_missing_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['remove_high_missing'] = {'var': high_missing_var}
    
    def create_conservative_operations(self):
        """Create operations for conservative cleaning"""
        row = 0
        
        ttk.Label(self.operations_frame, text="🛡️ Conservative Operations:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky='w', pady=(0,10))
        row += 1
        
        dtype_var = tk.BooleanVar(value=True)
        dtype_cb = ttk.Checkbutton(self.operations_frame, text="Smart data type conversion", 
                                  variable=dtype_var, command=self.update_operations_summary)
        dtype_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['smart_type_conversion'] = {'var': dtype_var}
        
        dup_var = tk.BooleanVar(value=True)
        dup_cb = ttk.Checkbutton(self.operations_frame, text="Remove exact duplicate rows only", 
                                variable=dup_var, command=self.update_operations_summary)
        dup_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['remove_duplicates'] = {'var': dup_var}
    
    def create_healthcare_operations(self):
        """Create operations for healthcare cleaning"""
        self.create_smart_operations()
        row = len(self.operation_widgets) + 5
        
        ttk.Label(self.operations_frame, text="🏥 Healthcare-Specific:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky='w', pady=(20,10))
        row += 1
        
        phi_var = tk.BooleanVar(value=True)
        phi_cb = ttk.Checkbutton(self.operations_frame, text="Auto-redact PHI (names, emails, phones)", 
                                variable=phi_var, command=self.update_operations_summary)
        phi_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['redact_phi'] = {'var': phi_var}
        
        clinical_var = tk.BooleanVar(value=True)
        clinical_cb = ttk.Checkbutton(self.operations_frame, text="Validate clinical ranges", 
                                     variable=clinical_var, command=self.update_operations_summary)
        clinical_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['validate_clinical'] = {'var': clinical_var}
        
        medical_var = tk.BooleanVar(value=True)
        medical_cb = ttk.Checkbutton(self.operations_frame, text="Standardize medical codes", 
                                    variable=medical_var, command=self.update_operations_summary)
        medical_cb.grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        self.operation_widgets['standardize_medical'] = {'var': medical_var}
    
    def update_operations_summary(self, event=None):
        """Update operations summary"""
        enabled_ops = []
        
        for op_name, widgets in self.operation_widgets.items():
            if widgets['var'].get():
                if 'method' in widgets:
                    enabled_ops.append(f"• {op_name.replace('_', ' ').title()} ({widgets['method'].get()})")
                else:
                    enabled_ops.append(f"• {op_name.replace('_', ' ').title()}")
        
        summary = f"""🔧 OPERATIONS TO BE PERFORMED:
{'='*50}
Strategy: {self.strategy_var.get().replace('_', ' ').title()}
Enabled Operations:
{chr(10).join(enabled_ops) if enabled_ops else "• No operations selected"}
"""
        
        self.summary_text.config(state='normal')
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary)
        self.summary_text.config(state='disabled')
        
        self.update_final_summary()
    
    def update_final_summary(self):
        """Update final summary"""
        self.final_summary_text.config(state='normal')
        self.final_summary_text.delete(1.0, tk.END)
        self.final_summary_text.insert(1.0, self.summary_text.get(1.0, tk.END))
        self.final_summary_text.config(state='disabled')
    
    def execute_cleaning(self):
        """Execute cleaning with user adjustments"""
        if self.data is None:
            messagebox.showerror("Error", "Please load and analyze data first")
            return
        
        try:
            self.cleaned_data = self.data.copy()
            operations_log = []
            
            strategy = self.strategy_var.get()
            
            if strategy == "auto_smart":
                operations_log = self.apply_smart_with_adjustments()
            elif strategy == "aggressive":
                operations_log = self.apply_aggressive_with_adjustments()
            elif strategy == "conservative":
                operations_log = self.apply_conservative_with_adjustments()
            elif strategy == "healthcare_specific":
                operations_log = self.apply_healthcare_with_adjustments()
            elif strategy == "custom_yaml":
                operations_log = self.apply_custom_with_adjustments()
            
            self.show_cleaning_results(operations_log)
            messagebox.showinfo("Success", "Cleaning completed with your adjustments!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Cleaning failed: {e}")
    
    def apply_smart_with_adjustments(self):
        """Apply smart cleaning with adjustments"""
        operations_log = []
        data = self.data.copy()
        
        # 1. Smart data type conversion
        if self.operation_widgets.get('smart_type_conversion', {}).get('var', tk.BooleanVar()).get():
            data, type_log = self.detect_and_convert_data_types(data)
            operations_log.extend(type_log)
        
        # 2. Handle missing values
        if self.operation_widgets.get('handle_missing', {}).get('var', tk.BooleanVar()).get():
            method = self.operation_widgets['handle_missing']['method'].get()
            data, missing_log = self.handle_missing_values(data, method)
            operations_log.extend(missing_log)
        
        # 3. Remove duplicates
        if self.operation_widgets.get('remove_duplicates', {}).get('var', tk.BooleanVar()).get():
            dup_before = len(data)
            data = data.drop_duplicates()
            if len(data) < dup_before:
                operations_log.append(f"✅ Removed {dup_before - len(data)} duplicate rows")
        
        # 4. Feature engineering
        if self.operation_widgets.get('feature_engineering', {}).get('var', tk.BooleanVar()).get():
            data, feature_log = self.create_derived_features(data)
            operations_log.extend(feature_log)
        
        # 5. Clean text
        if self.operation_widgets.get('clean_text', {}).get('var', tk.BooleanVar()).get():
            data, text_log = self.clean_text_data(data)
            operations_log.extend(text_log)
        
        # 6. Handle outliers
        if self.operation_widgets.get('handle_outliers', {}).get('var', tk.BooleanVar()).get():
            method = self.operation_widgets['handle_outliers']['method'].get()
            data, outlier_log = self.handle_outliers(data, method)
            operations_log.extend(outlier_log)
        
        self.cleaned_data = data
        return operations_log
    
    def apply_aggressive_with_adjustments(self):
        """Apply aggressive cleaning"""
        operations_log = self.apply_smart_with_adjustments()
        data = self.cleaned_data.copy()
        
        if self.operation_widgets.get('remove_high_missing', {}).get('var', tk.BooleanVar()).get():
            high_missing_cols = []
            for col in data.columns:
                if data[col].isnull().sum() / len(data) > 0.5:
                    high_missing_cols.append(col)
            
            if high_missing_cols:
                data = data.drop(columns=high_missing_cols)
                operations_log.append(f"✅ Removed {len(high_missing_cols)} columns with >50% missing values")
        
        self.cleaned_data = data
        return operations_log
    
    def apply_conservative_with_adjustments(self):
        """Apply conservative cleaning"""
        operations_log = []
        data = self.data.copy()
        
        if self.operation_widgets.get('smart_type_conversion', {}).get('var', tk.BooleanVar()).get():
            data, type_log = self.detect_and_convert_data_types(data)
            operations_log.extend(type_log)
        
        if self.operation_widgets.get('remove_duplicates', {}).get('var', tk.BooleanVar()).get():
            dup_before = len(data)
            data = data.drop_duplicates()
            if len(data) < dup_before:
                operations_log.append(f"✅ Removed {dup_before - len(data)} exact duplicate rows")
        
        self.cleaned_data = data
        return operations_log
    
    def apply_healthcare_with_adjustments(self):
        """Apply healthcare cleaning"""
        operations_log = self.apply_smart_with_adjustments()
        data = self.cleaned_data.copy()
        
        if self.operation_widgets.get('redact_phi', {}).get('var', tk.BooleanVar()).get():
            data, phi_log = self.enhanced_phi_redaction(data)
            operations_log.extend(phi_log)
        
        if self.operation_widgets.get('validate_clinical', {}).get('var', tk.BooleanVar()).get():
            data, clinical_log = self.validate_clinical_ranges(data)
            operations_log.extend(clinical_log)
        
        if self.operation_widgets.get('standardize_medical', {}).get('var', tk.BooleanVar()).get():
            data, medical_log = self.standardize_medical_codes(data)
            operations_log.extend(medical_log)
        
        self.cleaned_data = data
        return operations_log
    
    # ENHANCED DATA CLEANING METHODS
    
    def detect_and_convert_data_types(self, data):
        """Intelligent data type conversion"""
        converted_data = data.copy()
        conversion_log = []
        
        for column in converted_data.columns:
            col_data = converted_data[column]
            
            # Skip if already proper type
            if pd.api.types.is_numeric_dtype(col_data) or pd.api.types.is_datetime64_any_dtype(col_data):
                continue
                
            # Try numeric conversion
            numeric_converted = self.try_numeric_conversion(col_data)
            if numeric_converted is not None:
                converted_data[column] = numeric_converted
                conversion_log.append(f"🔢 {column}: string → numeric")
                continue
                
            # Try date conversion
            date_converted = self.try_date_conversion(col_data)
            if date_converted is not None:
                converted_data[column] = date_converted
                conversion_log.append(f"📅 {column}: string → datetime")
                continue
                
            # Handle mixed types
            if self.has_mixed_types(col_data):
                standardized = self.handle_mixed_types(col_data)
                converted_data[column] = standardized
                conversion_log.append(f"🔄 {column}: mixed types standardized")
        
        return converted_data, conversion_log
    
    def try_numeric_conversion(self, series):
        """Convert strings to numeric"""
        if series.dtype != 'object':
            return None
            
        # Remove common non-numeric characters
        cleaned = series.astype(str).str.replace(r'[$,%()\s]', '', regex=True)
        
        def convert_value(val):
            if pd.isna(val) or val == '':
                return np.nan
            try:
                if ',' in str(val) and '.' not in str(val):
                    return float(val.replace(',', ''))
                return float(val)
            except (ValueError, TypeError):
                return val
        
        converted = cleaned.apply(convert_value)
        
        # Check if conversion successful
        numeric_count = pd.to_numeric(converted, errors='coerce').notna().sum()
        if numeric_count / len(converted) > 0.8:
            return pd.to_numeric(converted, errors='coerce')
        
        return None
    
    def try_date_conversion(self, series):
        """Convert strings to dates"""
        if series.dtype != 'object':
            return None
            
        date_formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%Y.%m.%d', '%d.%m.%Y', '%m.%d.%Y',
        ]
        
        for fmt in date_formats:
            try:
                converted = pd.to_datetime(series, format=fmt, errors='coerce')
                if converted.notna().sum() / len(converted) > 0.7:
                    return converted
            except:
                continue
        
        # Fallback
        converted = pd.to_datetime(series, errors='coerce')
        if converted.notna().sum() / len(converted) > 0.7:
            return converted
        
        return None
    
    def handle_mixed_types(self, series):
        """Standardize mixed type columns"""
        numeric_converted = pd.to_numeric(series, errors='coerce')
        
        if numeric_converted.notna().sum() / len(series) > 0.5:
            return numeric_converted
        else:
            return series.astype(str)
    
    def handle_missing_values(self, data, method):
        """Handle missing values"""
        missing_log = []
        missing_before = data.isnull().sum().sum()
        
        if method == "remove":
            data = data.dropna()
        elif method == "fill_median":
            for col in data.select_dtypes(include=[np.number]).columns:
                data[col] = data[col].fillna(data[col].median())
        elif method == "fill_mode":
            for col in data.select_dtypes(include=['object']).columns:
                data[col] = data[col].fillna(data[col].mode()[0] if not data[col].mode().empty else 'Unknown')
        else:  # auto
            for col in data.columns:
                if pd.api.types.is_numeric_dtype(data[col]):
                    data[col] = data[col].fillna(data[col].median())
                else:
                    data[col] = data[col].fillna('Unknown')
        
        missing_after = data.isnull().sum().sum()
        if missing_after < missing_before:
            missing_log.append(f"✅ Filled {missing_before - missing_after} missing values using {method}")
        
        return data, missing_log
    
    def create_derived_features(self, data):
        """Create derived features"""
        engineered_data = data.copy()
        feature_log = []
        
        for column in engineered_data.columns:
            col_data = engineered_data[column]
            
            # Date features
            if pd.api.types.is_datetime64_any_dtype(col_data):
                engineered_data, date_log = self.create_date_features(engineered_data, column)
                feature_log.extend(date_log)
            
            # Text features
            elif col_data.dtype == 'object':
                engineered_data, text_log = self.create_text_features(engineered_data, column)
                feature_log.extend(text_log)
            
            # Numeric features
            elif pd.api.types.is_numeric_dtype(col_data):
                engineered_data, num_log = self.create_numeric_features(engineered_data, column)
                feature_log.extend(num_log)
        
        return engineered_data, feature_log
    
    def create_date_features(self, data, date_column):
        """Extract date features"""
        feature_log = []
        
        data[f'{date_column}_year'] = data[date_column].dt.year
        data[f'{date_column}_month'] = data[date_column].dt.month
        data[f'{date_column}_day'] = data[date_column].dt.day
        data[f'{date_column}_dayofweek'] = data[date_column].dt.dayofweek
        
        # Age calculation for birth dates
        if any(keyword in date_column.lower() for keyword in ['birth', 'dob']):
            data[f'{date_column}_age'] = (pd.Timestamp.now() - data[date_column]).dt.days // 365
            feature_log.append(f"🎂 Created age from {date_column}")
        
        feature_log.append(f"📅 Created date features from {date_column}")
        return data, feature_log
    
    def create_text_features(self, data, text_column):
        """Extract text features"""
        feature_log = []
        
        data[f'{text_column}_length'] = data[text_column].astype(str).str.len()
        data[f'{text_column}_word_count'] = data[text_column].astype(str).str.split().str.len()
        
        # Email domain extraction
        if data[text_column].str.contains('@', na=False).any():
            data[f'{text_column}_domain'] = data[text_column].str.split('@').str[1]
            feature_log.append(f"📧 Extracted email domains from {text_column}")
        
        # Categorical encoding for low cardinality
        unique_count = data[text_column].nunique()
        if 2 <= unique_count <= 10:
            data[f'{text_column}_encoded'] = pd.factorize(data[text_column])[0]
            feature_log.append(f"🔤 Encoded {text_column} ({unique_count} categories)")
        
        feature_log.append(f"📝 Created text features from {text_column}")
        return data, feature_log
    
    def create_numeric_features(self, data, numeric_column):
        """Extract numeric features"""
        feature_log = []
        
        # Binning for categorical conversion
        if data[numeric_column].nunique() > 10:
            data[f'{numeric_column}_binned'] = pd.cut(data[numeric_column], bins=5, labels=False)
            feature_log.append(f"📊 Binned {numeric_column} into 5 categories")
        
        # Log transformation for skewed data
        if data[numeric_column].min() > 0:
            skewness = data[numeric_column].skew()
            if abs(skewness) > 1:
                data[f'{numeric_column}_log'] = np.log1p(data[numeric_column])
                feature_log.append(f"📈 Applied log transform to {numeric_column} (skew: {skewness:.2f})")
        
        return data, feature_log
    
    def clean_text_data(self, data):
        """Clean text data"""
        text_log = []
        
        for column in data.select_dtypes(include=['object']).columns:
            # Remove extra whitespace
            data[column] = data[column].astype(str).str.strip()
            data[column] = data[column].str.replace(r'\s+', ' ', regex=True)
            
            # Fix case inconsistencies for categorical text
            if data[column].nunique() < 50:
                data[column] = data[column].str.title()
            
            text_log.append(f"✨ Cleaned text in {column}")
        
        return data, text_log
    
    def handle_outliers(self, data, method):
        """Handle outliers"""
        outlier_log = []
        
        for column in data.select_dtypes(include=[np.number]).columns:
            Q1 = data[column].quantile(0.25)
            Q3 = data[column].quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR > 0:
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
                
                if len(outliers) > 0:
                    if method == "cap":
                        data[column] = data[column].clip(lower=lower_bound, upper=upper_bound)
                        outlier_log.append(f"📏 Capped {len(outliers)} outliers in {column}")
                    elif method == "remove":
                        data = data[~((data[column] < lower_bound) | (data[column] > upper_bound))]
                        outlier_log.append(f"🗑️ Removed {len(outliers)} outliers in {column}")
        
        return data, outlier_log
    
    # HEALTHCARE-SPECIFIC METHODS
    
    def enhanced_phi_redaction(self, data):
        """Redact PHI data"""
        phi_log = []
        
        phi_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        }
        
        for column in data.columns:
            col_lower = column.lower()
            
            # Column-based redaction
            if any(phi_keyword in col_lower for phi_keyword in 
                   ['name', 'address', 'phone', 'email', 'ssn', 'mrn', 'patient_id']):
                data[column] = '[REDACTED_PHI]'
                phi_log.append(f"🔒 Redacted PHI column: {column}")
                continue
            
            # Pattern-based redaction
            if data[column].dtype == 'object':
                for pattern_name, pattern in phi_patterns.items():
                    if data[column].astype(str).str.contains(pattern, na=False).any():
                        data[column] = data[column].astype(str).str.replace(
                            pattern, f'[REDACTED_{pattern_name.upper()}]', regex=True)
                        phi_log.append(f"🔒 Redacted {pattern_name} patterns in {column}")
        
        return data, phi_log
    
    def validate_clinical_ranges(self, data):
        """Validate clinical ranges"""
        clinical_log = []
        
        # Common clinical ranges
        clinical_ranges = {
            'heart_rate': (40, 200),
            'systolic_bp': (70, 250),
            'diastolic_bp': (40, 150),
            'temperature': (35, 42),
            'spo2': (70, 100),
        }
        
        for column in data.select_dtypes(include=[np.number]).columns:
            col_lower = column.lower()
            
            for param, (min_val, max_val) in clinical_ranges.items():
                if param in col_lower:
                    invalid = data[(data[column] < min_val) | (data[column] > max_val)]
                    if len(invalid) > 0:
                        clinical_log.append(f"⚕️ Found {len(invalid)} values outside clinical range in {column}")
                        break
        
        return data, clinical_log
    
    def standardize_medical_codes(self, data):
        """Standardize medical codes"""
        code_log = []
        
        for column in data.columns:
            col_lower = column.lower()
            
            # ICD-10 codes
            if 'icd' in col_lower or 'diagnosis' in col_lower:
                data[column] = data[column].astype(str).str.upper().str.replace('.', '')
                code_log.append(f"🏥 Standardized ICD-10 codes in {column}")
            
            # CPT codes
            elif 'cpt' in col_lower or 'procedure' in col_lower:
                data[column] = data[column].astype(str).str.strip().str.zfill(5)
                code_log.append(f"🏥 Standardized CPT codes in {column}")
        
        return data, code_log
    
    def show_cleaning_results(self, operations_log):
        """Show cleaning results"""
        if self.cleaned_data is None:
            return
        
        results = f"""📊 CLEANING RESULTS:
{'='*50}
Original Data: {self.data.shape[0]} rows × {self.data.shape[1]} columns
Cleaned Data: {self.cleaned_data.shape[0]} rows × {self.cleaned_data.shape[1]} columns
Data Reduction: {((1 - self.cleaned_data.shape[0] / self.data.shape[0]) * 100):.1f}% rows, {((1 - self.cleaned_data.shape[1] / self.data.shape[1]) * 100):.1f}% columns

🔧 OPERATIONS PERFORMED:
{chr(10).join(operations_log) if operations_log else "No operations performed"}

📈 DATA QUALITY IMPROVEMENT:
• Missing values: {self.data.isnull().sum().sum()} → {self.cleaned_data.isnull().sum().sum()}
• Duplicate rows: {self.data.duplicated().sum()} → {self.cleaned_data.duplicated().sum()}
• Memory usage: {self.data.memory_usage(deep=True).sum() / 1024**2:.2f}MB → {self.cleaned_data.memory_usage(deep=True).sum() / 1024**2:.2f}MB

🎯 NEW FEATURES CREATED:
• Total columns: {self.cleaned_data.shape[1]} (+{self.cleaned_data.shape[1] - self.data.shape[1]})
• Data types: {dict(self.cleaned_data.dtypes.value_counts())}
"""
        
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, results)
        self.results_text.config(state='disabled')
    
    def export_data(self):
        """Export cleaned data"""
        if self.cleaned_data is None:
            messagebox.showerror("Error", "No cleaned data to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Cleaned Data",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")]
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    self.cleaned_data.to_csv(filename, index=False)
                else:
                    self.cleaned_data.to_excel(filename, index=False)
                messagebox.showinfo("Success", f"Data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")
    
    def export_report(self):
        """Export cleaning report"""
        if self.cleaned_data is None:
            messagebox.showerror("Error", "No cleaning report to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Cleaning Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.results_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")

def main():
    root = tk.Tk()
    app = EnhancedDataCleaner(root)
    root.mainloop()

if __name__ == "__main__":
    main()