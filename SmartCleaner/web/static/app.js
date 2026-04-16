/**
 * Smart Data Cleaner - Frontend Application (v0.0.7)
 * All 11 cleaning operations wired.
 */

class SmartDataCleaner {
    constructor() {
        this.sessionId = null;
        this.currentFile = null;
        this.currentStrategy = 'auto_smart';
        this.operations = {};
        this.yamlConfig = null;
        this.recommendations = [];  // Phase 3: Smart recommendations
        this.schemaMapping = null;
        this.executionLineage = null;
        this.executionProgressInterval = null;
        this.isUnstructured = false; // Track if current file is unstructured
        this.initElements();
        this.initEventListeners();
        this.renderOperations(); // Initialize operations for default strategy
    }

    initElements() {
        // Consent modal elements
        this.consentModal = document.getElementById('consent-modal');
        this.consentCheck = document.getElementById('consent-check');
        this.consentAcceptBtn = document.getElementById('consent-accept-btn');
        this.consentDeclineBtn = document.getElementById('consent-decline-btn');
        this.appContainer = document.getElementById('app-container');

        // Tab elements
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabPanels = document.querySelectorAll('.tab-panel');

        // Upload elements
        this.fileInput = document.getElementById('file-input');
        this.fileDisplay = document.getElementById('file-name');
        this.analyzeBtn = document.getElementById('analyze-btn');
        this.dropzone = document.getElementById('dropzone');

        // Result elements
        this.overviewContent = document.getElementById('overview-content');
        this.issuesContent = document.getElementById('issues-content');
        this.demoBtn = document.getElementById('load-demo-btn');
        this.schemaMappingContainer = document.getElementById('schema-mapping-container');

        // Loading
        this.loadingOverlay = document.getElementById('loading-overlay');

        // Review tab elements
        this.strategySelect = document.getElementById('strategy-select');
        this.yamlInput = document.getElementById('yaml-input');
        this.yamlFilename = document.getElementById('yaml-filename');
        this.yamlInfoPanel = document.getElementById('yaml-info-panel');
        this.operationsContainer = document.getElementById('operations-container');
        this.summaryStrategy = document.getElementById('summary-strategy');
        this.summaryOperations = document.getElementById('summary-operations');

        // Execute tab elements
        this.finalStrategy = document.getElementById('final-strategy');
        this.finalOperationsList = document.getElementById('final-operations-list');
        this.executeBtn = document.getElementById('execute-btn');
        this.executeStatus = document.getElementById('execute-status');
        this.resultsSection = document.getElementById('results-section');
        this.originalStats = document.getElementById('original-stats');
        this.cleanedStats = document.getElementById('cleaned-stats');
        this.dataReduction = document.getElementById('data-reduction');
        this.opsPerformedList = document.getElementById('ops-performed-list');
        this.qualityMetrics = document.getElementById('quality-metrics');
        this.exportDataBtn = document.getElementById('export-data-btn');
        this.exportReportBtn = document.getElementById('export-report-btn');
        this.exportLineageBtn = document.getElementById('export-lineage-btn');
        this.executionProgress = document.getElementById('execution-progress');
        this.comparisonContainer = document.getElementById('comparison-mode-container');
        this.lineageContainer = document.getElementById('lineage-container');

        // Unstructured data specific elements
        this.unstructuredOptions = document.getElementById('unstructured-options');
        this.unstructuredResults = document.getElementById('unstructured-results');
        this.unstructOriginalPreview = document.getElementById('unstruct-original-preview');
        this.unstructCleanedPreview = document.getElementById('unstruct-cleaned-preview');
        this.unstructPhiResults = document.getElementById('unstruct-phi-results');
        this.unstructClinicalValues = document.getElementById('unstruct-clinical-values');
        this.unstructSections = document.getElementById('unstruct-sections');
    }

    initEventListeners() {
        // Consent modal
        this.consentCheck.addEventListener('change', () => {
            this.consentAcceptBtn.disabled = !this.consentCheck.checked;
        });

        this.consentAcceptBtn.addEventListener('click', () => {
            this.consentModal.classList.add('hidden');
            this.appContainer.classList.remove('hidden');
        });

        this.consentDeclineBtn.addEventListener('click', () => {
            document.body.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;height:100vh;background:#0a0a0f;color:#ef4444;font-family:Inter,sans-serif;text-align:center;flex-direction:column;gap:16px;">
                    <span style="font-size:4rem;">🚫</span>
                    <h2>Access Denied</h2>
                    <p style="color:rgba(255,255,255,0.6);">You must accept the data responsibility notice to use this application.</p>
                    <button onclick="location.reload()" style="margin-top:20px;padding:12px 24px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border:none;border-radius:8px;color:white;cursor:pointer;font-size:1rem;">Try Again</button>
                </div>`;
        });

        // Tab navigation
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Analyze button
        this.analyzeBtn.addEventListener('click', () => this.analyzeDataset());
        if (this.demoBtn) {
            this.demoBtn.addEventListener('click', () => this.loadDemoDataset());
        }

        // Drag and drop
        this.dropzone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropzone.addEventListener('dragleave', () => this.handleDragLeave());
        this.dropzone.addEventListener('drop', (e) => this.handleDrop(e));

        // Strategy selection
        this.strategySelect.addEventListener('change', (e) => this.handleStrategyChange(e));

        // YAML upload
        this.yamlInput.addEventListener('change', (e) => this.handleYamlUpload(e));

        // Execute button
        this.executeBtn.addEventListener('click', () => this.executeCleaning());

        // Export buttons
        this.exportDataBtn.addEventListener('click', () => this.exportCleanedData());
        this.exportReportBtn.addEventListener('click', () => this.exportReport());
        if (this.exportLineageBtn) {
            this.exportLineageBtn.addEventListener('click', () => this.exportLineageReport());
        }

        this.initKeyboardShortcuts();
    }

    switchTab(tabId) {
        // Update buttons
        this.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });

        // Update panels
        this.tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tabId}-tab`);
        });

        // Sync execute tab when switching to it
        if (tabId === 'execute') {
            this.updateFinalSummary();
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.setFile(file);
        }
    }

    handleDragOver(e) {
        e.preventDefault();
        this.dropzone.classList.add('dragover');
    }

    handleDragLeave() {
        this.dropzone.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropzone.classList.remove('dragover');

        const file = e.dataTransfer.files[0];
        if (file) {
            this.setFile(file);
        }
    }

    setFile(file) {
        // Validate file type
        const structuredTypes = ['.csv', '.xlsx', '.xls', '.json', '.xml'];
        const unstructuredTypes = ['.txt', '.log', '.pdf', '.md', '.text', '.dat', '.rtf'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!structuredTypes.includes(ext) && !unstructuredTypes.includes(ext)) {
            alert('Unsupported file type. Supported: CSV, Excel, JSON, XML, TXT, LOG, PDF, MD');
            return;
        }

        if (unstructuredTypes.includes(ext)) {
            this.isUnstructured = true;
            this.currentFile = file;
            this.fileDisplay.textContent = file.name;
            this.fileDisplay.parentElement.classList.add('has-file');
            this.analyzeBtn.disabled = true;

            window.dispatchEvent(new CustomEvent('unstructured:file-selected', {
                detail: { file }
            }));
            this.switchTab('unstructured');
            return;
        }

        this.isUnstructured = false;
        if (this.unstructuredOptions) this.unstructuredOptions.classList.add('hidden');
        if (this.operationsContainer) this.operationsContainer.classList.remove('hidden');

        this.currentFile = file;
        this.fileDisplay.textContent = file.name;
        this.fileDisplay.parentElement.classList.add('has-file');
        this.analyzeBtn.disabled = false;
    }

    showLoading() {
        this.loadingOverlay.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }

    async analyzeDataset() {
        if (!this.currentFile) return;

        if (this.isUnstructured) {
            window.dispatchEvent(new CustomEvent('unstructured:file-selected', {
                detail: { file: this.currentFile }
            }));
            this.switchTab('unstructured');
            return;
        }

        this.showLoading();

        try {
            const formData = new FormData();
            formData.append('file', this.currentFile);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.error) {
                throw new Error(result.error);
            }
            this.processAnalysisResult(result);

        } catch (error) {
            console.error('Analysis failed:', error);
            alert('Failed to analyze dataset: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadDemoDataset() {
        this.showLoading();
        try {
            const response = await fetch('/api/demo/load', {
                method: 'POST'
            });
            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }

            this.currentFile = null;
            this.fileDisplay.textContent = result.filename || 'demo_healthcare_dataset.csv';
            this.fileDisplay.parentElement.classList.add('has-file');
            this.processAnalysisResult(result);
            this.showNotification('Demo dataset loaded successfully', 'success');
        } catch (error) {
            console.error('Demo load failed:', error);
            alert('Failed to load demo data: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    processAnalysisResult(result) {
        this.sessionId = result.session_id;
        this.isUnstructured = result.is_unstructured || false;

        // If unstructured, we might want to skip some structured-only renders
        if (this.isUnstructured) {
            this.renderUnstructuredAnalysis(result);
        }

        this.renderOverview(result.overview);
        this.renderQualityIssues(result.quality_issues);

        if (result.preview) {
            previewTable = new DataPreviewTable('data-preview-container');
            previewTable.render(result.preview.rows, result.preview.quality);
        }

        if (result.quality_score) {
            this.renderQualityScore(result.quality_score);
        }

        if (result.recommendations) {
            this.recommendations = result.recommendations;
            this.renderRecommendations(result.recommendations);
        }

        if (result.schema_mapping) {
            this.schemaMapping = result.schema_mapping;
            this.renderSchemaMapping(result.schema_mapping);
        }

        this.updateFinalSummary();
    }

    renderUnstructuredAnalysis(result) {
        // Prepare the UI for unstructured analysis
        if (!this.unstructuredOptions) return;
        
        // Show unstructured options in Review tab
        this.unstructuredOptions.classList.remove('hidden');
        
        // Populate unstructured results placeholders in Execute tab
        if (this.unstructuredResults) {
            this.unstructuredResults.classList.remove('hidden');
        }
    }

    renderOverview(overview) {
        const { rows, columns, memory_usage_mb, total_cells, data_types } = overview;

        // Format data types
        const dtypeStr = Object.entries(data_types)
            .map(([type, count]) => `${type}: ${count}`)
            .join(', ');

        this.overviewContent.innerHTML = `
            <div class="overview-stats">
                <div class="overview-header" style="color: var(--accent-primary); font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">
                    📊 DATASET OVERVIEW:
                </div>
                <div style="border-bottom: 2px solid var(--border-color); margin-bottom: 12px;"></div>
                <div class="stat-line">
                    <span class="stat-label">Shape:</span>
                    <span class="stat-value">${rows.toLocaleString()} rows × ${columns} columns</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Memory Usage:</span>
                    <span class="stat-value">${memory_usage_mb} MB</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Total Cells:</span>
                    <span class="stat-value">${total_cells.toLocaleString()}</span>
                </div>
                <div class="stat-line">
                    <span class="stat-label">Data Types:</span>
                    <span class="stat-value">{${dtypeStr}}</span>
                </div>
            </div>
        `;
    }

    renderQualityIssues(issues) {
        if (!issues || issues.length === 0) {
            this.issuesContent.innerHTML = `
                <div class="empty-state" style="color: var(--success);">
                    ✅ No data quality issues detected!
                </div>
            `;
            return;
        }

        let html = `
            <div class="issues-list">
                <div class="issue-header">
                    <span>⚠️</span>
                    <span>DATA QUALITY ISSUES:</span>
                </div>
                <div style="border-bottom: 2px solid var(--border-color); margin-bottom: 8px;"></div>
        `;

        issues.forEach(issue => {
            const indentClass = issue.indent ? 'indent' : '';
            const typeClass = issue.type === 'missing_header' || issue.type === 'duplicates' ? 'error' : 'warning';

            html += `
                <div class="issue-item ${indentClass} ${typeClass}">
                    <span class="issue-icon">${issue.icon}</span>
                    <span class="issue-column">${issue.column}:</span>
                    <span class="issue-message">${issue.message}</span>
                </div>
            `;
        });

        html += '</div>';
        this.issuesContent.innerHTML = html;
    }

    renderQualityScore(scores) {
        /**
         * Render data quality score dashboard (Phase 3 Enhancement)
         * Shows overall score and 5 dimensional scores with visual indicators
         */
        const container = document.getElementById('quality-score-container');
        if (!container) {
            // Create container if it doesn't exist
            const overviewCard = document.querySelector('.result-card');
            if (overviewCard) {
                const scoreCard = document.createElement('div');
                scoreCard.className = 'result-card';
                scoreCard.innerHTML = `
                    <div class="card-header">
                        <span class="card-icon">📈</span>
                        <h3>Data Quality Score:</h3>
                    </div>
                    <div id="quality-score-container" class="card-content"></div>
                `;
                overviewCard.parentNode.insertBefore(scoreCard, overviewCard.nextSibling);
            }
        }

        const getScoreColor = (score) => {
            if (score >= 80) return '#10b981'; // green
            if (score >= 60) return '#f59e0b'; // yellow
            return '#ef4444'; // red
        };

        const getScoreEmoji = (score) => {
            if (score >= 80) return '✅';
            if (score >= 60) return '⚠️';
            return '🔴';
        };

        const scoreName = {
            'completeness': 'Completeness',
            'consistency': 'Consistency',
            'validity': 'Validity',
            'uniqueness': 'Uniqueness',
            'accuracy': 'Accuracy'
        };

        const finalContainer = document.getElementById('quality-score-container') || container;
        finalContainer.innerHTML = `
            <div class="quality-score-card">
                <div class="overall-score">
                    <h2>Data Quality Score</h2>
                    <div class="score-display" style="color: ${getScoreColor(scores.overall)}">
                        <span class="score-number">${scores.overall}</span>
                        <span class="score-max">/100</span>
                        <span class="score-emoji">${getScoreEmoji(scores.overall)}</span>
                    </div>
                </div>
                
                <div class="dimension-scores">
                    ${Object.entries(scores).filter(([key]) => key !== 'overall').map(([dimension, score]) => `
                        <div class="dimension-score-item">
                            <div class="dimension-header">
                                <span class="dimension-name">${scoreName[dimension] || dimension}</span>
                                <span class="dimension-value" style="color: ${getScoreColor(score)}">${score}/100 ${getScoreEmoji(score)}</span>
                            </div>
                            <div class="dimension-progress-bar">
                                <div class="dimension-progress-fill" style="width: ${score}%; background: ${getScoreColor(score)}"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderRecommendations(recommendations) {
        /**
         * Render smart recommendations engine (Phase 3 Enhancement)
         * AI-powered analysis with actionable insights
         */
        const container = document.getElementById('recommendations-analysis-container');
        if (!container) {
            // Create container if it doesn't exist
            const issuesCard = document.querySelector('.issues-card');
            if (issuesCard) {
                const recCard = document.createElement('div');
                recCard.className = 'result-card recommendations-card';
                recCard.innerHTML = `
                    <div class="card-header">
                        <span class="card-icon">🤖</span>
                        <h3>Smart Recommendations:</h3>
                    </div>
                    <div id="recommendations-analysis-container" class="card-content"></div>
                `;
                issuesCard.parentNode.insertBefore(recCard, issuesCard.nextSibling);
            }
        }

        const finalContainer = document.getElementById('recommendations-analysis-container') || container;

        if (!recommendations || recommendations.length === 0) {
            finalContainer.innerHTML = `
                <div class="empty-state" style="color: var(--success);">
                    ✅ No critical issues detected! Your data quality is excellent.
                </div>
            `;
            return;
        }

        const priorityColors = {
            'HIGH': '#ef4444',
            'MEDIUM': '#f59e0b',
            'LOW': '#3b82f6'
        };

        const priorityIcons = {
            'HIGH': '🔴',
            'MEDIUM': '🟡',
            'LOW': '🔵'
        };

        finalContainer.innerHTML = `
            <div class="recommendations-header">
                <h3>🧠 AI-Powered Insights</h3>
                <p>I analyzed your dataset and found <strong>${recommendations.length}</strong> recommended improvements:</p>
            </div>
            <div class="recommendations-list">
                ${recommendations.map((rec, index) => `
                    <div class="recommendation-card priority-${rec.priority.toLowerCase()}" data-rec-index="${index}">
                        <div class="rec-header">
                            <span class="rec-priority" style="background: ${priorityColors[rec.priority]}">
                                ${priorityIcons[rec.priority]} ${rec.priority}
                            </span>
                            <span class="rec-confidence">${(rec.confidence * 100).toFixed(0)}% confidence</span>
                        </div>
                        <h4 class="rec-title">${rec.title}</h4>
                        <p class="rec-reason"><strong>Why:</strong> ${rec.reason}</p>
                        <p class="rec-impact"><strong>Impact:</strong> ${rec.impact}</p>
                        <div class="rec-config">
                            <strong>Suggested config:</strong>
                            <code>${JSON.stringify(rec.suggested_config, null, 2)}</code>
                        </div>
                        <button class="apply-rec-btn" onclick="app.applyRecommendation(${index})">
                            ✅ Apply This Recommendation
                        </button>
                    </div>
                `).join('')}
            </div>
            <div class="recommendations-footer">
                <button class="btn-secondary" onclick="app.applyAllRecommendations()">
                    ⚡ Apply All High Priority
                </button>
                <button class="btn-secondary" onclick="app.dismissRecommendations()">
                    Skip Recommendations
                </button>
            </div>
        `;
    }

    applyRecommendation(index) {
        /**
         * Apply a single recommendation to the cleaning strategy
         */
        if (!this.recommendations || !this.recommendations[index]) {
            console.error('Recommendation not found');
            return;
        }

        const rec = this.recommendations[index];
        
        // Switch to review tab
        this.switchTab('review');
        
        // Enable the recommended operation
        const checkbox = document.getElementById(`op-${rec.operation}`);
        if (checkbox) {
            checkbox.checked = true;
            this.operations[rec.operation] = { enabled: true };
            
            // Apply suggested config
            if (rec.suggested_config) {
                Object.entries(rec.suggested_config).forEach(([key, value]) => {
                    const configInput = document.getElementById(`${rec.operation}-${key}`);
                    if (configInput) {
                        configInput.value = value;
                        if (!this.operations[rec.operation].config) {
                            this.operations[rec.operation].config = {};
                        }
                        this.operations[rec.operation].config[key] = value;
                    }
                });
            }
            
            this.updateSummary();
            
            // Show success message
            this.showNotification(`✅ Applied: ${rec.title}`, 'success');
        } else {
            this.showNotification(`⚠️ Operation "${rec.operation}" not found`, 'warning');
        }
    }

    applyAllRecommendations() {
        /**
         * Apply all HIGH priority recommendations
         */
        const highPriority = this.recommendations.filter(rec => rec.priority === 'HIGH');
        
        if (highPriority.length === 0) {
            this.showNotification('No high priority recommendations to apply', 'info');
            return;
        }

        highPriority.forEach((rec, index) => {
            const fullIndex = this.recommendations.indexOf(rec);
            this.applyRecommendation(fullIndex);
        });

        this.showNotification(`✅ Applied ${highPriority.length} high priority recommendations`, 'success');
    }

    dismissRecommendations() {
        /**
         * Dismiss recommendations and proceed to review tab
         */
        this.switchTab('review');
        this.showNotification('You can manually configure operations in the Review tab', 'info');
    }

    showNotification(message, type = 'info') {
        /**
         * Show temporary notification to user
         */
        const colors = {
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'info': '#3b82f6'
        };

        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    renderSchemaMapping(mapping) {
        if (!this.schemaMappingContainer || !mapping) return;

        if (!mapping.suggestions || mapping.suggestions.length === 0) {
            this.schemaMappingContainer.innerHTML = '<div class="empty-state">No schema mapping suggestions found for this dataset.</div>';
            return;
        }

        this.schemaMappingContainer.innerHTML = `
            <div class="schema-map-header">
                <h4>Detected Domain: <span>${mapping.domain}</span></h4>
                <p>Suggested standardized columns for cleaner downstream analytics.</p>
            </div>
            <div class="schema-map-list">
                ${mapping.suggestions.slice(0, 12).map(s => `
                    <div class="schema-map-item">
                        <div class="schema-map-cols">
                            <code>${s.source}</code>
                            <span>→</span>
                            <code>${s.suggested}</code>
                        </div>
                        <div class="schema-map-meta">
                            <span class="schema-conf">${Math.round(s.confidence * 100)}% confidence</span>
                            <span>${s.reason}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    initKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            if (event.target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) {
                return;
            }

            if (event.key === '?') {
                event.preventDefault();
                this.showShortcutsHelp();
                return;
            }

            if (!event.ctrlKey) return;

            const key = event.key.toLowerCase();
            if (key === 'u') {
                event.preventDefault();
                this.fileInput.click();
            } else if (key === 'a') {
                event.preventDefault();
                if (this.currentFile) this.analyzeDataset();
            } else if (key === 'e') {
                event.preventDefault();
                this.switchTab('execute');
            } else if (key === 's') {
                event.preventDefault();
                this.exportCleanedData();
            } else if (key === 'v') {
                event.preventDefault();
                this.switchTab('visualize');
            }
        });
    }

    showShortcutsHelp() {
        alert('Keyboard Shortcuts\n\nCtrl+U: Upload file\nCtrl+A: Analyze dataset\nCtrl+E: Open Execute tab\nCtrl+S: Export cleaned CSV\nCtrl+V: Open Visualize tab\n?: Show this help');
    }

    // ============================================
    // REVIEW & ADJUST TAB FUNCTIONALITY
    // ============================================

    handleStrategyChange(e) {
        this.currentStrategy = e.target.value;

        // Show/hide YAML info panel
        if (this.currentStrategy === 'custom_yaml') {
            this.yamlInfoPanel.classList.remove('hidden');
        } else {
            this.yamlInfoPanel.classList.add('hidden');
        }

        this.renderOperations();
        this.updateSummary();
    }

    handleYamlUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                // Basic YAML parsing (for simple configs)
                const content = event.target.result;
                this.yamlConfig = this.parseYaml(content);
                this.yamlFilename.textContent = file.name;
                this.strategySelect.value = 'custom_yaml';
                this.currentStrategy = 'custom_yaml';
                this.renderOperations();
                this.updateSummary();
            } catch (error) {
                alert('Failed to parse YAML file: ' + error.message);
            }
        };
        reader.readAsText(file);
    }

    parseYaml(content) {
        // Simple YAML parser for our use case
        const config = { operations: {} };
        const lines = content.split('\n');
        let currentOp = null;

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;

            // Check for operation name (indented under operations:)
            if (line.startsWith('  ') && !line.startsWith('    ') && trimmed.includes(':')) {
                currentOp = trimmed.replace(':', '');
                config.operations[currentOp] = { enabled: true };
            }
            // Check for operation properties
            else if (line.startsWith('    ') && currentOp) {
                const [key, ...valueParts] = trimmed.split(':');
                let value = valueParts.join(':').trim();

                // Parse value
                if (value === 'true') value = true;
                else if (value === 'false') value = false;
                else if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1);
                else if (value.startsWith('[') && value.endsWith(']')) {
                    value = value.slice(1, -1).split(',').map(v => v.trim().replace(/"/g, ''));
                }

                config.operations[currentOp][key.trim()] = value;
            }
        }

        return config;
    }

    getOperationsForStrategy(strategy) {
        const strategies = {
            auto_smart: {
                global: [
                    { id: 'smart_type_conversion', label: 'Smart data type conversion', checked: true },
                    { id: 'handle_missing', label: 'Handle missing values', checked: true, method: 'auto', methods: ['auto', 'remove', 'fill_median', 'fill_mode'] },
                    { id: 'ml_impute_missing', label: 'ML-based missing value imputation', checked: false },
                    { id: 'remove_duplicates', label: 'Remove duplicate rows', checked: true },
                    { id: 'feature_engineering', label: 'Create derived features', checked: true },
                    { id: 'clean_text', label: 'Clean text formatting', checked: true },
                    { id: 'handle_outliers', label: 'Handle outliers', checked: true, method: 'cap', methods: ['cap', 'remove', 'ignore'] },
                    { id: 'validate_ranges', label: 'Validate numeric ranges (3×IQR)', checked: false }
                ]
            },
            aggressive: {
                global: [
                    { id: 'smart_type_conversion', label: 'Smart data type conversion', checked: true },
                    { id: 'handle_missing', label: 'Handle missing values', checked: true, method: 'auto', methods: ['auto', 'remove', 'fill_median', 'fill_mode'] },
                    { id: 'ml_impute_missing', label: 'ML-based missing value imputation', checked: true },
                    { id: 'remove_duplicates', label: 'Remove duplicate rows', checked: true },
                    { id: 'feature_engineering', label: 'Create derived features', checked: true },
                    { id: 'clean_text', label: 'Clean text formatting', checked: true },
                    { id: 'handle_outliers', label: 'Handle outliers', checked: true, method: 'cap', methods: ['cap', 'remove', 'ignore'] },
                    { id: 'validate_ranges', label: 'Validate numeric ranges (3×IQR)', checked: true }
                ],
                aggressive: [
                    { id: 'remove_high_missing', label: 'Remove columns with >50% missing values', checked: true }
                ]
            },
            conservative: {
                conservative: [
                    { id: 'smart_type_conversion', label: 'Smart data type conversion', checked: true },
                    { id: 'remove_duplicates', label: 'Remove exact duplicate rows only', checked: true }
                ]
            },
            healthcare_specific: {
                global: [
                    { id: 'smart_type_conversion', label: 'Smart data type conversion', checked: true },
                    { id: 'handle_missing', label: 'Handle missing values', checked: true, method: 'auto', methods: ['auto', 'remove', 'fill_median', 'fill_mode'] },
                    { id: 'ml_impute_missing', label: 'ML-based missing value imputation', checked: true },
                    { id: 'remove_duplicates', label: 'Remove duplicate rows', checked: true },
                    { id: 'feature_engineering', label: 'Create derived features', checked: true },
                    { id: 'clean_text', label: 'Clean text formatting', checked: true },
                    { id: 'handle_outliers', label: 'Handle outliers', checked: true, method: 'cap', methods: ['cap', 'remove', 'ignore'] }
                ],
                healthcare: [
                    { id: 'redact_phi', label: 'Auto-redact PHI (names, emails, phones, Aadhaar)', checked: true },
                    { id: 'validate_clinical', label: 'Validate clinical ranges', checked: true },
                    { id: 'standardize_codes', label: 'Standardize medical codes (ICD-10/CPT/LOINC)', checked: true },
                    { id: 'normalize_clinical_text', label: 'Normalize clinical text (abbreviations, spelling)', checked: true },
                    { id: 'validate_ranges', label: 'Validate numeric ranges (3×IQR)', checked: true },
                    { id: 'remove_high_missing', label: 'Remove columns with >50% missing values', checked: false }
                ]
            },
            custom_yaml: {
                // Will be populated from YAML config
            }
        };

        if (strategy === 'custom_yaml' && this.yamlConfig) {
            const customOps = { custom: [] };
            for (const [opId, opConfig] of Object.entries(this.yamlConfig.operations || {})) {
                customOps.custom.push({
                    id: opId,
                    label: opConfig.description || opId.replace(/_/g, ' '),
                    checked: opConfig.enabled !== false,
                    method: opConfig.default_method,
                    methods: opConfig.methods
                });
            }
            return customOps;
        }

        return strategies[strategy] || {};
    }

    renderOperations() {
        const strategyOps = this.getOperationsForStrategy(this.currentStrategy);
        this.operations = {};

        const groupLabels = {
            global: { icon: '🌐', title: 'Global Operations' },
            aggressive: { icon: '⚡', title: 'Aggressive Options' },
            conservative: { icon: '🛡️', title: 'Conservative Operations' },
            healthcare: { icon: '🏥', title: 'Healthcare-Specific' },
            custom: { icon: '🎯', title: 'Custom Operations (YAML)' }
        };

        let html = '';

        for (const [groupId, operations] of Object.entries(strategyOps)) {
            const group = groupLabels[groupId] || { icon: '📋', title: groupId };

            html += `
                <div class="operations-group">
                    <div class="operations-group-header">
                        <span class="group-icon">${group.icon}</span>
                        <span class="group-title">${group.title}:</span>
                    </div>
            `;

            for (const op of operations) {
                this.operations[op.id] = { ...op };

                html += `
                    <div class="operation-item" data-op-row="${op.id}">
                        <label class="operation-checkbox">
                            <input type="checkbox" 
                                   id="op-${op.id}" 
                                   data-op-id="${op.id}"
                                   ${op.checked ? 'checked' : ''}>
                            <span>${op.label}</span>
                        </label>
                `;

                if (op.methods && op.methods.length > 0) {
                    html += `
                        <select class="operation-method" 
                                data-op-id="${op.id}">
                            ${op.methods.map(m => `<option value="${m}" ${m === op.method ? 'selected' : ''}>${m}</option>`).join('')}
                        </select>
                    `;
                }

                html += `
                    <div class="pipeline-order-controls">
                        <button type="button" class="btn-pipeline-order" data-move-op="${op.id}" data-direction="up">↑</button>
                        <button type="button" class="btn-pipeline-order" data-move-op="${op.id}" data-direction="down">↓</button>
                    </div>
                `;

                html += '</div>';
            }

            html += '</div>';
        }

        if (this.currentStrategy === 'custom_yaml' && !this.yamlConfig) {
            html = `
                <div class="empty-state">
                    Please upload a YAML configuration file to define custom operations
                </div>
            `;
        }

        this.operationsContainer.innerHTML = html;

        // Add event listeners for checkboxes and method selects
        this.operationsContainer.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const opId = e.target.dataset.opId;
                if (this.operations[opId]) {
                    this.operations[opId].checked = e.target.checked;
                }
                this.updateSummary();
            });
        });

        this.operationsContainer.querySelectorAll('select.operation-method').forEach(select => {
            select.addEventListener('change', (e) => {
                const opId = e.target.dataset.opId;
                if (this.operations[opId]) {
                    this.operations[opId].method = e.target.value;
                }
                this.updateSummary();
            });
        });

        this.operationsContainer.querySelectorAll('button.btn-pipeline-order').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const opId = e.target.dataset.moveOp;
                const direction = e.target.dataset.direction;
                this.moveOperation(opId, direction);
            });
        });

        this.updateSummary();
    }

    moveOperation(opId, direction) {
        const row = this.operationsContainer.querySelector(`[data-op-row="${opId}"]`);
        if (!row) return;

        if (direction === 'up' && row.previousElementSibling) {
            row.parentNode.insertBefore(row, row.previousElementSibling);
        }
        if (direction === 'down' && row.nextElementSibling) {
            row.parentNode.insertBefore(row.nextElementSibling, row);
        }
        this.updateSummary();
    }

    updateSummary() {
        // Update strategy display
        const strategyLabels = {
            auto_smart: 'Auto Smart',
            aggressive: 'Aggressive',
            conservative: 'Conservative',
            healthcare_specific: 'Healthcare Specific',
            custom_yaml: 'Custom Yaml'
        };
        this.summaryStrategy.textContent = strategyLabels[this.currentStrategy] || this.currentStrategy;

        // Update operations list
        const enabledOps = Object.values(this.operations)
            .filter(op => op.checked)
            .map(op => {
                let text = op.label.replace(/^(Smart |Remove |Handle |Clean |Create |Auto-|Validate |Standardize )/, '');
                text = text.charAt(0).toUpperCase() + text.slice(1);
                if (op.method) {
                    text += ` (${op.method})`;
                }
                return text;
            });

        if (enabledOps.length === 0) {
            this.summaryOperations.innerHTML = '<li>No operations selected</li>';
        } else {
            this.summaryOperations.innerHTML = enabledOps.map(op => `<li>${op}</li>`).join('');
        }
    }

    // Get current configuration for execution
    getConfiguration() {
        return {
            strategy: this.currentStrategy,
            operations: this.operations,
            consentGiven: this.consentCheck.checked
        };
    }

    getOperationSequence() {
        return Array.from(this.operationsContainer.querySelectorAll('[data-op-row]')).map(row => row.dataset.opRow);
    }

    // ============================================
    // EXECUTE & RESULTS TAB FUNCTIONALITY
    // ============================================

    updateFinalSummary() {
        // Update strategy display
        const strategyLabels = {
            auto_smart: 'Auto Smart',
            aggressive: 'Aggressive',
            conservative: 'Conservative',
            healthcare_specific: 'Healthcare Specific',
            custom_yaml: 'Custom Yaml'
        };
        this.finalStrategy.textContent = strategyLabels[this.currentStrategy] || this.currentStrategy;

        // Update operations list
        const enabledOps = Object.values(this.operations)
            .filter(op => op.checked)
            .map(op => {
                let text = op.label;
                if (op.method) {
                    text += ` (${op.method})`;
                }
                return text;
            });

        if (enabledOps.length === 0) {
            this.finalOperationsList.innerHTML = '<li>No operations configured</li>';
            this.executeBtn.disabled = true;
            this.executeStatus.textContent = 'Configure operations in Review tab';
        } else {
            this.finalOperationsList.innerHTML = enabledOps.map(op => `<li>${op}</li>`).join('');
            this.executeBtn.disabled = !this.sessionId;
            this.executeStatus.textContent = this.sessionId ? '' : 'Upload a dataset first';
        }
    }

    getUnstructuredOptions() {
        // Collect options from the unstructured checkboxes in Review tab
        const options = {
            redact_phi: document.getElementById('unstruct-redact-phi')?.checked ?? true,
            redaction_style: document.getElementById('unstruct-redaction-style')?.value ?? 'tag',
            expand_abbreviations: document.getElementById('unstruct-expand-abbrev')?.checked ?? true,
            spell_correct: document.getElementById('unstruct-spell-correct')?.checked ?? true,
            extract_clinical: document.getElementById('unstruct-extract-clinical')?.checked ?? true,
            extract_entities: document.getElementById('unstruct-extract-entities')?.checked ?? true,
            generate_tables: document.getElementById('unstruct-gen-tables')?.checked ?? true,
            parse_logs: document.getElementById('unstruct-parse-logs')?.checked ?? true,
            extract_sections: document.getElementById('unstruct-extract-sections')?.checked ?? true,
            cleaning_ops: {
                normalize_whitespace: document.getElementById('unstruct-norm-whitespace')?.checked ?? true,
                normalize_line_breaks: document.getElementById('unstruct-norm-lines')?.checked ?? true,
                remove_control_chars: document.getElementById('unstruct-rem-control')?.checked ?? true,
                fix_encoding_artifacts: document.getElementById('unstruct-fix-encoding')?.checked ?? true,
                normalize_unicode: document.getElementById('unstruct-norm-unicode')?.checked ?? true,
                standardize_punctuation: document.getElementById('unstruct-std-punc')?.checked ?? true,
                remove_empty_lines: document.getElementById('unstruct-rem-empty')?.checked ?? true,
                fix_hyphenation: document.getElementById('unstruct-fix-hyphen')?.checked ?? true
            }
        };
        return options;
    }

    async executeCleaning() {
        if (!this.sessionId) {
            alert('Please upload a dataset first.');
            return;
        }

        const enabledOps = Object.entries(this.operations)
            .filter(([, op]) => op.checked)
            .map(([opId]) => opId);
        this.startExecutionProgress(enabledOps);

        this.showLoading();
        this.executeBtn.disabled = true;
        this.executeStatus.textContent = 'Processing...';

        try {
            const body = {
                session_id: this.sessionId,
                operations: this.isUnstructured ? this.getUnstructuredOptions() : this.operations,
                operation_sequence: this.isUnstructured ? [] : this.getOperationSequence()
            };

            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            const result = await response.json();

            if (result.error) {
                throw new Error(result.error);
            }

            if (result.is_unstructured) {
                this.renderUnstructuredResults(result);
            } else {
                this.renderResults(result);
            }
            this.executionLineage = result.lineage || null;
            this.executeStatus.textContent = '✅ Cleaning complete!';

        } catch (error) {
            console.error('Execution failed:', error);
            this.executeStatus.textContent = '❌ ' + error.message;
            alert('Cleaning failed: ' + error.message);
        } finally {
            this.stopExecutionProgress();
            this.hideLoading();
            this.executeBtn.disabled = false;
        }
    }

    renderResults(result) {
        // Show results section
        this.resultsSection.classList.remove('hidden');

        // Data comparison
        this.originalStats.textContent = result.original_stats;
        this.cleanedStats.textContent = result.cleaned_stats;
        this.dataReduction.textContent = result.data_reduction;

        // Operations performed
        if (result.operations_performed && result.operations_performed.length > 0) {
            this.opsPerformedList.innerHTML = result.operations_performed
                .map(op => `<li><span class="op-icon">${op.icon}</span> ${op.text}</li>`)
                .join('');
        } else {
            this.opsPerformedList.innerHTML = '<li>No operations were needed</li>';
        }

        // Quality improvement
        const qi = result.quality_improvement;
        let qiHtml = `
            <div class="quality-metric">
                • Missing values: <span class="before">${qi.missing_values.before}</span> → <span class="after">${qi.missing_values.after}</span>
            </div>
        `;
        if (qi.duplicates) {
            qiHtml += `
                <div class="quality-metric">
                    • Duplicate rows: <span class="before">${qi.duplicates.before}</span> → <span class="after">${qi.duplicates.after}</span>
                </div>
            `;
        }
        if (qi.new_features && qi.new_features > 0) {
            qiHtml += `
                <div class="quality-metric">
                    • New features created: <span class="after">+${qi.new_features}</span>
                </div>
            `;
        }
        this.qualityMetrics.innerHTML = qiHtml;

        // Accuracy comparison
        const acc = result.accuracy;
        this.updateAccuracyBars('completeness', acc.before.completeness, acc.after.completeness);
        this.updateAccuracyBars('consistency', acc.before.consistency, acc.after.consistency);
        this.updateAccuracyBars('quality', acc.before.overall, acc.after.overall);

        this.renderComparisonMode(result.comparison);
        this.renderLineageSummary(result.lineage);
        this.renderValidationReport(result.validation_report);
    }

    renderValidationReport(report) {
        const card = document.getElementById('validation-report-card');
        const container = document.getElementById('validation-report-content');
        if (!card || !container) return;
        if (!report) {
            card.style.display = 'none';
            return;
        }

        card.style.display = '';
        const phi = report.phi_redactions || {};
        const icd = report.icd10_mappings || {};
        const txt = report.text_corrections || {};
        const types = report.type_conversions || {};
        const quality = report.overall_quality || {};
        const qualityDelta = ((quality.after || 0) - (quality.before || 0)).toFixed(1);
        const qualityColor = qualityDelta >= 0 ? '#10b981' : '#ef4444';

        container.innerHTML = `
            <div class="validation-grid">
                <div class="validation-stat-card phi">
                    <div class="stat-value">${phi.total || 0}</div>
                    <div class="stat-label">PHI Redacted</div>
                </div>
                <div class="validation-stat-card exact">
                    <div class="stat-value">${icd.exact || 0}</div>
                    <div class="stat-label">ICD-10 Exact Matches</div>
                </div>
                <div class="validation-stat-card fuzzy">
                    <div class="stat-value">${icd.fuzzy || 0}</div>
                    <div class="stat-label">ICD-10 Fuzzy Matches</div>
                </div>
                <div class="validation-stat-card unrecognized">
                    <div class="stat-value">${icd.unrecognized || 0}</div>
                    <div class="stat-label">Unrecognized Codes</div>
                </div>
                <div class="validation-stat-card missing">
                    <div class="stat-value">${report.missing_values_handled || 0}</div>
                    <div class="stat-label">Missing Values Handled</div>
                </div>
                <div class="validation-stat-card duplicates">
                    <div class="stat-value">${report.duplicates_removed || 0}</div>
                    <div class="stat-label">Duplicates Removed</div>
                </div>
                <div class="validation-stat-card outliers">
                    <div class="stat-value">${report.outliers_clipped || 0}</div>
                    <div class="stat-label">Outliers Clipped</div>
                </div>
                <div class="validation-stat-card quality ${qualityDelta >= 0 ? 'good' : 'bad'}">
                    <div class="stat-value">${quality.before || 0}% → ${quality.after || 0}%</div>
                    <div class="stat-label">Quality Score (${qualityDelta >= 0 ? '+' : ''}${qualityDelta})</div>
                </div>
            </div>
            <div class="validation-footer">
                <strong>Text Corrections:</strong> ${txt.abbreviations_expanded || 0} abbreviations expanded, ${txt.misspellings_fixed || 0} misspellings fixed<br>
                <strong>Type Conversions:</strong> ${types.date_columns || 0} date columns, ${types.numeric_columns || 0} numeric columns<br>
                <strong>Clinical Validations:</strong> ${report.clinical_validations || 0} out-of-range values flagged<br>
                <strong>Fuzzy Matching:</strong> ${report.fuzzy_matching_available ? '✅ Enabled (thefuzz)' : '⚠️ Disabled (install thefuzz)'}<br>
                <strong>Total Operations:</strong> ${report.total_operations || 0}
            </div>
        `;
    }

    renderComparisonMode(comparison) {
        if (!this.comparisonContainer) return;
        if (!comparison || !comparison.before_preview || !comparison.after_preview) {
            this.comparisonContainer.innerHTML = '<div class="empty-state">Comparison preview is not available.</div>';
            return;
        }

        const beforeRow = comparison.before_preview[0] || {};
        const afterRow = comparison.after_preview[0] || {};
        const keys = Object.keys(beforeRow).slice(0, 6);

        this.comparisonContainer.innerHTML = `
            <div class="comparison-mode-grid">
                <div class="comparison-panel">
                    <h4>Before Cleaning</h4>
                    ${keys.map(k => `<div class="comparison-cell"><span>${k}</span><code>${beforeRow[k] ?? 'null'}</code></div>`).join('')}
                </div>
                <div class="comparison-panel">
                    <h4>After Cleaning</h4>
                    ${keys.map(k => `<div class="comparison-cell"><span>${k}</span><code>${afterRow[k] ?? 'null'}</code></div>`).join('')}
                </div>
            </div>
            <p class="comparison-hint">Showing first row snapshot over ${comparison.preview_rows} preview rows.</p>
        `;
    }

    renderLineageSummary(lineage) {
        if (!this.lineageContainer) return;
        if (!lineage || !lineage.transformations) {
            this.lineageContainer.innerHTML = '<div class="empty-state">No lineage data yet. Execute cleaning to generate lineage.</div>';
            return;
        }

        this.lineageContainer.innerHTML = `
            <div class="lineage-header-row">
                <h4>Transformation Lineage</h4>
                <span>${lineage.transformations.length} steps</span>
            </div>
            <div class="lineage-list">
                ${lineage.transformations.map(step => `
                    <div class="lineage-item">
                        <div class="lineage-step">#${step.step} ${step.operation}</div>
                        <div class="lineage-meta">Rows: ${step.before.rows} → ${step.after.rows} | Missing: ${step.before.missing_cells} → ${step.after.missing_cells}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    startExecutionProgress(enabledOps) {
        if (!this.executionProgress) return;
        const total = Math.max(enabledOps.length, 1);
        let current = 0;

        this.executionProgress.classList.remove('hidden');
        this.executionProgress.innerHTML = `
            <div class="exec-progress-header">Execution Progress</div>
            <div class="exec-progress-bar"><div id="exec-progress-fill" style="width: 5%"></div></div>
            <div id="exec-progress-text">Starting cleaning pipeline...</div>
        `;

        this.executionProgressInterval = setInterval(() => {
            const fill = document.getElementById('exec-progress-fill');
            const text = document.getElementById('exec-progress-text');
            if (!fill || !text) return;

            current = Math.min(current + 1, total);
            const pct = Math.min(95, Math.round((current / total) * 100));
            fill.style.width = `${pct}%`;
            const opName = enabledOps[Math.max(0, current - 1)] || 'Finalizing';
            text.textContent = `Running: ${opName.replace(/_/g, ' ')}`;
        }, 700);
    }

    stopExecutionProgress() {
        if (!this.executionProgress) return;
        if (this.executionProgressInterval) {
            clearInterval(this.executionProgressInterval);
            this.executionProgressInterval = null;
        }

        const fill = document.getElementById('exec-progress-fill');
        const text = document.getElementById('exec-progress-text');
        if (fill) fill.style.width = '100%';
        if (text) text.textContent = 'Pipeline completed';
    }

    renderUnstructuredResults(result) {
        // Show results section
        this.resultsSection.classList.remove('hidden');
        if (this.unstructuredResults) this.unstructuredResults.classList.remove('hidden');
        
        // Hide structured-specific stats/comparison if they were visible
        if (this.comparisonContainer) this.comparisonContainer.classList.add('hidden');

        // Render Previews (Comparison)
        if (this.unstructOriginalPreview) this.unstructOriginalPreview.textContent = result.original_preview;
        if (this.unstructCleanedPreview) this.unstructCleanedPreview.textContent = result.cleaned_preview;

        // Render PHI findings
        if (this.unstructPhiResults) {
            if (result.phi_findings && result.phi_findings.length > 0) {
                this.unstructPhiResults.innerHTML = result.phi_findings.map(phi => `
                    <div class="phi-item priority-${phi.risk_level.toLowerCase()}">
                        <span class="phi-type">${phi.type}</span>
                        <span class="phi-text">${phi.matched_text_preview}</span>
                        <span class="phi-line">Line ${phi.line_number}</span>
                    </div>
                `).join('');
            } else {
                this.unstructPhiResults.innerHTML = '<div class="empty-state">No PHI detected.</div>';
            }
        }

        // Render Clinical Values
        if (this.unstructClinicalValues) {
            if (result.clinical_values && Object.keys(result.clinical_values).length > 0) {
                this.unstructClinicalValues.innerHTML = Object.entries(result.clinical_values).map(([key, val]) => `
                    <div class="clinical-item">
                        <span class="clinical-label">${key.replace(/_/g, ' ').toUpperCase()}:</span>
                        <span class="clinical-value">${val}</span>
                    </div>
                `).join('');
            } else {
                this.unstructClinicalValues.innerHTML = '<div class="empty-state">No clinical values extracted.</div>';
            }
        }

        // Render Sections
        if (this.unstructSections) {
            if (result.sections && result.sections.length > 0) {
                this.unstructSections.innerHTML = result.sections.map(sec => `
                    <div class="section-item">
                        <span class="section-title">${sec.title}</span>
                        <span class="section-preview">${sec.preview}...</span>
                    </div>
                `).join('');
            } else {
                this.unstructSections.innerHTML = '<div class="empty-state">No distinct sections identified.</div>';
            }
        }

        // Update basic stats
        this.originalStats.textContent = `${result.original_stats.rows} lines`;
        this.cleanedStats.textContent = `${result.cleaned_stats.rows} lines`;
        this.dataReduction.textContent = `${result.results.phi_count} PHI redacted, ${result.results.clinical_count} clinical values`;
    }

    updateAccuracyBars(metric, beforeValue, afterValue) {
        document.getElementById(`${metric}-before`).style.width = `${beforeValue}%`;
        document.getElementById(`${metric}-before-val`).textContent = `${beforeValue}%`;
        document.getElementById(`${metric}-after`).style.width = `${afterValue}%`;
        document.getElementById(`${metric}-after-val`).textContent = `${afterValue}%`;
    }

    exportCleanedData() {
        if (!this.sessionId) {
            alert('No data to export');
            return;
        }
        window.open(`/api/export/${this.sessionId}`, '_blank');
    }

    exportReport() {
        // Generate text report
        const strategy = this.finalStrategy.textContent;
        const ops = Array.from(this.opsPerformedList.querySelectorAll('li'))
            .map(li => li.textContent).join('\n');

        const report = `Smart Data Cleaner - Cleaning Report
========================================
Date: ${new Date().toLocaleString()}
Strategy: ${strategy}

Original: ${this.originalStats.textContent}
Cleaned: ${this.cleanedStats.textContent}
Reduction: ${this.dataReduction.textContent}

Operations Performed:
${ops}
`;

        const blob = new Blob([report], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'cleaning_report.txt';
        a.click();
        URL.revokeObjectURL(url);
    }

    exportLineageReport() {
        if (!this.sessionId) {
            alert('No session available for lineage export');
            return;
        }
        window.open(`/api/export/lineage/${this.sessionId}`, '_blank');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SmartDataCleaner();
});
