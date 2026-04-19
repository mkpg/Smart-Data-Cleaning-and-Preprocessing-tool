/**
 * Unstructured Data Processor - Frontend Logic
 * Handles file upload, processing options, and result rendering
 * for TXT, LOG, PDF, MD healthcare files.
 */

(function () {
    'use strict';

    // ── State ──
    let currentSessionId = null;
    let currentFile = null;

    // ── DOM Elements ──
    const fileInput = document.getElementById('unstruct-file-input');
    const fileDisplay = document.getElementById('unstruct-file-name');
    const analyzeBtn = document.getElementById('unstruct-analyze-btn');
    const dropzone = document.getElementById('unstruct-dropzone');
    const resultsSection = document.getElementById('unstruct-results');
    const toggleOptionsBtn = document.getElementById('unstruct-toggle-options');
    const optionsPanel = document.getElementById('unstruct-options-panel');
    const exportBtn = document.getElementById('unstruct-export-btn');
    const loadingOverlay = document.getElementById('loading-overlay');

    if (!fileInput) return; // Tab not present

    window.addEventListener('unstructured:file-selected', (event) => {
        const file = event.detail?.file;
        if (!file) return;
        setFile(file);
    });

    // ── File Selection ──
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) setFile(file);
    });

    function setFile(file) {
        const allowed = ['txt', 'log', 'pdf', 'md', 'text', 'dat', 'rtf'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext)) {
            alert(`Unsupported file type: .${ext}\nSupported: ${allowed.join(', ')}`);
            return;
        }
        currentFile = file;
        fileDisplay.textContent = file.name;
        analyzeBtn.disabled = false;
    }

    // ── Drag & Drop ──
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-active');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('drag-active');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-active');
        const file = e.dataTransfer.files[0];
        if (file) setFile(file);
    });

    // ── Toggle Options ──
    toggleOptionsBtn.addEventListener('click', () => {
        optionsPanel.classList.toggle('collapsed');
        toggleOptionsBtn.classList.toggle('collapsed');
        toggleOptionsBtn.textContent = optionsPanel.classList.contains('collapsed') ? '▶' : '▼';
    });

    // ── Demo Buttons ──
    document.querySelectorAll('.unstruct-demo-btn').forEach(btn => {
        btn.addEventListener('click', () => loadDemo(btn.dataset.demo));
    });

    async function loadDemo(type) {
        showLoading('Loading demo file...');
        try {
            const resp = await fetch('/api/unstructured/demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type })
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Demo load failed');
            currentSessionId = data.session_id;
            renderResults(data);
        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            hideLoading();
        }
    }

    // ── Process File ──
    analyzeBtn.addEventListener('click', processFile);

    async function processFile() {
        if (!currentFile) return;

        showLoading('Processing file...');

        const formData = new FormData();
        formData.append('file', currentFile);

        // Gather options
        const optMap = {
            'normalize_whitespace': 'opt-normalize-whitespace',
            'normalize_line_breaks': 'opt-normalize-linebreaks',
            'remove_control_chars': 'opt-remove-control',
            'fix_encoding_artifacts': 'opt-fix-encoding',
            'normalize_unicode': 'opt-normalize-unicode',
            'standardize_punctuation': 'opt-standardize-punct',
            'remove_empty_lines': 'opt-remove-empty',
            'fix_hyphenation': 'opt-fix-hyphenation',
        };

        for (const [key, id] of Object.entries(optMap)) {
            const el = document.getElementById(id);
            formData.append(key, el ? el.checked : true);
        }

        const redactPhi = document.getElementById('opt-redact-phi');
        formData.append('redact_phi', redactPhi ? redactPhi.checked : true);
        formData.append('redaction_style', document.getElementById('opt-redaction-style')?.value || 'tag');
        formData.append('expand_abbreviations', document.getElementById('opt-expand-abbrev')?.checked ?? true);
        formData.append('spell_correct', document.getElementById('opt-spell-correct')?.checked ?? true);
        formData.append('extract_clinical', document.getElementById('opt-extract-clinical')?.checked ?? true);
        formData.append('extract_sections', document.getElementById('opt-extract-sections')?.checked ?? true);
        formData.append('extract_entities', document.getElementById('opt-extract-entities')?.checked ?? true);
        formData.append('generate_tables', false);
        formData.append('parse_logs', document.getElementById('opt-parse-logs')?.checked ?? true);

        try {
            const resp = await fetch('/api/unstructured/upload', {
                method: 'POST',
                body: formData
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Processing failed');
            currentSessionId = data.session_id;
            renderResults(data);
        } catch (err) {
            alert('Error: ' + err.message);
        } finally {
            hideLoading();
        }
    }

    // ── Export ──
    exportBtn.addEventListener('click', () => {
        if (!currentSessionId) return alert('No processed data to export');
        window.location.href = `/api/unstructured/export/${currentSessionId}`;
    });

    const exportJsonBtn = document.getElementById('unstruct-export-json-btn');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => {
            if (!currentSessionId) return alert('No processed data to export');
            window.location.href = `/api/export/unstructured/${currentSessionId}`;
        });
    }

    // ── Render Results ──
    function renderResults(data) {
        resultsSection.classList.remove('hidden');
        renderStats(data);
        renderPhiResults(data);
        renderComparison(data);
        renderClinicalValues(data);
        renderSections(data);
        renderLogEntries(data);
        renderAbbreviations(data);
        renderSpellReport(data);
        renderEntities(data);
        renderProcessingLog(data);
        renderReviewSummary();

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async function renderReviewSummary() {
        const section = document.getElementById('unstruct-review-section');
        const container = document.getElementById('unstruct-review-summary');
        if (!section || !container) return;

        if (!currentSessionId) {
            section.classList.add('hidden');
            return;
        }

        try {
            const resp = await fetch(`/api/unstructured/review/summary/${encodeURIComponent(currentSessionId)}`);
            const data = await resp.json();

            if (!resp.ok) {
                section.classList.add('hidden');
                return;
            }

            const byConfidence = data.by_confidence_range || {};
            const byType = data.by_event_type || {};
            const topTypes = Object.entries(byType)
                .sort((a, b) => (b[1].flagged || 0) - (a[1].flagged || 0))
                .slice(0, 6);

            const topTypesHtml = topTypes.length
                ? topTypes.map(([type, stats]) => (
                    `<tr>
                        <td>${escapeHTML(formatKey(type))}</td>
                        <td>${escapeHTML(String(stats.total || 0))}</td>
                        <td>${escapeHTML(String(stats.flagged || 0))}</td>
                    </tr>`
                )).join('')
                : '<tr><td colspan="3">No event-type review data yet.</td></tr>';

            container.innerHTML = `
                <div class="unstruct-stats-grid" style="margin-bottom: 12px;">
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(data.total_entries || 0))}</div>
                        <div class="unstruct-stat-label">Total Entries</div>
                    </div>
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(data.flagged_for_review || 0))}</div>
                        <div class="unstruct-stat-label">Flagged For Review</div>
                    </div>
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(byConfidence['critical_0-50'] || 0))}</div>
                        <div class="unstruct-stat-label">Critical (0-50)</div>
                    </div>
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(byConfidence['low_50-70'] || 0))}</div>
                        <div class="unstruct-stat-label">Low (50-70)</div>
                    </div>
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(byConfidence['medium_70-85'] || 0))}</div>
                        <div class="unstruct-stat-label">Medium (70-85)</div>
                    </div>
                    <div class="unstruct-stat-card">
                        <div class="unstruct-stat-value">${escapeHTML(String(byConfidence['high_85-100'] || 0))}</div>
                        <div class="unstruct-stat-label">High (85-100)</div>
                    </div>
                </div>
                <table class="unstruct-log-table">
                    <thead>
                        <tr><th>Event Type</th><th>Total</th><th>Flagged</th></tr>
                    </thead>
                    <tbody>
                        ${topTypesHtml}
                    </tbody>
                </table>
                <div style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted);">
                    Review API Session: ${escapeHTML(currentSessionId)}
                </div>
            `;
            section.classList.remove('hidden');
        } catch (_err) {
            section.classList.add('hidden');
        }
    }

    function renderStats(data) {
        const stats = data.stats || {};
        const cleaning = data.cleaning_report || {};
        const quality = data.quality_report || {};
        const qualitySignals = quality.signals || {};
        const container = document.getElementById('unstruct-stats');

        container.innerHTML = `
            <div class="unstruct-stats-grid">
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.quality_score || 0}</div>
                    <div class="unstruct-stat-label">Quality Score</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${escapeHTML(quality.grade || 'N/A')}</div>
                    <div class="unstruct-stat-label">Quality Grade</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${(stats.original_words || 0).toLocaleString()}</div>
                    <div class="unstruct-stat-label">Original Words</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${(stats.cleaned_words || 0).toLocaleString()}</div>
                    <div class="unstruct-stat-label">Cleaned Words</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.original_lines || 0}</div>
                    <div class="unstruct-stat-label">Original Lines</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.cleaned_lines || 0}</div>
                    <div class="unstruct-stat-label">Cleaned Lines</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.phi_items_found || 0}</div>
                    <div class="unstruct-stat-label">PHI Items Found</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.phi_items_redacted || 0}</div>
                    <div class="unstruct-stat-label">PHI Redacted</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.sections_found || 0}</div>
                    <div class="unstruct-stat-label">Sections Found</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.clinical_measurements || 0}</div>
                    <div class="unstruct-stat-label">Clinical Values</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.abbreviations_expanded || 0}</div>
                    <div class="unstruct-stat-label">Abbreviations Expanded</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.spell_corrections || 0}</div>
                    <div class="unstruct-stat-label">Spell Corrections</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.entities_found || 0}</div>
                    <div class="unstruct-stat-label">Entities Found</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.structured_log_events || 0}</div>
                    <div class="unstruct-stat-label">Structured Log Events</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.normalized_lab_events || 0}</div>
                    <div class="unstruct-stat-label">Normalized Lab Events</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${stats.normalized_medication_events || 0}</div>
                    <div class="unstruct-stat-label">Normalized Medication Events</div>
                </div>
                <div class="unstruct-stat-card">
                    <div class="unstruct-stat-value">${cleaning.size_reduction_pct || 0}%</div>
                    <div class="unstruct-stat-label">Size Reduction</div>
                </div>
            </div>
            <div style="margin-top:12px; font-size:0.8rem; color:var(--text-muted);">
                File: <strong>${escapeHTML(data.metadata?.filename || 'N/A')}</strong> |
                Method: <strong>${escapeHTML(data.metadata?.extraction_method || 'N/A')}</strong> |
                Ops Applied: <strong>${(cleaning.operations_applied || []).length}</strong>
            </div>
            <div style="margin-top:10px; padding:12px; border:1px solid rgba(0,0,0,0.08); border-radius:10px; background:rgba(255,255,255,0.55);">
                <div style="font-size:0.9rem; font-weight:600;">${escapeHTML(quality.summary || 'Quality scoring unavailable.')}</div>
                <div style="margin-top:6px; font-size:0.82rem; color:var(--text-muted);">
                    Normalized events: <strong>${qualitySignals.normalized_log_events || 0}</strong> |
                    Lab results: <strong>${qualitySignals.lab_results || 0}</strong> |
                    Medication events: <strong>${qualitySignals.medication_events || 0}</strong>
                </div>
                ${(quality.issues || []).length ? `<div style="margin-top:8px; font-size:0.82rem; color:#92400e;"><strong>Review:</strong> ${quality.issues.map(issue => escapeHTML(issue)).join(' | ')}</div>` : ''}
            </div>
        `;
    }

    function renderPhiResults(data) {
        const container = document.getElementById('unstruct-phi-results');
        const findings = data.phi_findings || [];
        const report = data.redaction_report || {};
        const summary = data.phi_summary || {};

        if (findings.length === 0) {
            container.innerHTML = '<div class="empty-state">No PHI/PII detected in this document.</div>';
            return;
        }

        const riskSummary = summary.by_risk || {};
        let html = `
            <div class="phi-summary-bar">
                <div class="phi-summary-item">
                    <span class="phi-summary-count" style="color:#f87171">${riskSummary.CRITICAL || 0}</span>
                    <span class="phi-summary-label">Critical</span>
                </div>
                <div class="phi-summary-item">
                    <span class="phi-summary-count" style="color:#fbbf24">${riskSummary.HIGH || 0}</span>
                    <span class="phi-summary-label">High</span>
                </div>
                <div class="phi-summary-item">
                    <span class="phi-summary-count" style="color:#60a5fa">${riskSummary.MEDIUM || 0}</span>
                    <span class="phi-summary-label">Medium</span>
                </div>
                <div class="phi-summary-item">
                    <span class="phi-summary-count" style="color:#34d399">${riskSummary.LOW || 0}</span>
                    <span class="phi-summary-label">Low</span>
                </div>
                <div class="phi-summary-item" style="margin-left:auto;">
                    <span class="phi-summary-count" style="color:var(--accent-primary)">${report.redactions || 0}</span>
                    <span class="phi-summary-label">Total Redacted (${escapeHTML(report.style || 'tag')})</span>
                </div>
            </div>
            <table class="unstruct-phi-table">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Description</th>
                        <th>HIPAA Category</th>
                        <th>Risk</th>
                        <th>Line</th>
                        <th>Preview</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Show max 50 findings
        const displayed = findings.slice(0, 50);
        for (const f of displayed) {
            html += `
                <tr>
                    <td><strong>${escapeHTML(f.type)}</strong></td>
                    <td>${escapeHTML(f.description)}</td>
                    <td>${escapeHTML(f.hipaa_category)}</td>
                    <td><span class="risk-badge ${f.risk_level.toLowerCase()}">${f.risk_level}</span></td>
                    <td>${f.line_number}</td>
                    <td style="font-family:monospace;font-size:0.78rem">${escapeHTML(f.matched_text_preview)}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        if (findings.length > 50) {
            html += `<div style="margin-top:8px;color:var(--text-muted);font-size:0.8rem;">Showing 50 of ${findings.length} findings</div>`;
        }

        container.innerHTML = html;
    }

    function renderComparison(data) {
        const origEl = document.getElementById('unstruct-original-preview');
        const cleanEl = document.getElementById('unstruct-cleaned-preview');
        origEl.textContent = data.original_text_preview || '(No text)';
        cleanEl.textContent = data.cleaned_text_preview || data.cleaned_text || '(No text)';
    }

    function renderClinicalValues(data) {
        const container = document.getElementById('unstruct-clinical-values');
        const clinical = data.clinical_values || {};
        const keys = Object.keys(clinical);

        if (keys.length === 0) {
            container.innerHTML = '<div class="empty-state">No clinical values extracted.</div>';
            return;
        }

        let html = '<div class="unstruct-clinical-grid">';
        for (const key of keys) {
            const values = clinical[key];
            html += `<div class="unstruct-clinical-card"><h5>${formatKey(key)}</h5>`;

            if (Array.isArray(values)) {
                for (const v of values) {
                    if (v.systolic !== undefined) {
                        html += `<div class="clinical-value-item">${v.systolic}/${v.diastolic} mmHg</div>`;
                    } else if (v.value !== undefined) {
                        html += `<div class="clinical-value-item">${v.value}</div>`;
                    } else {
                        html += `<div class="clinical-value-item">${escapeHTML(String(v))}</div>`;
                    }
                }
            } else if (typeof values === 'object') {
                for (const [k, v] of Object.entries(values)) {
                    html += `<div class="clinical-value-item">${escapeHTML(k)}: ${escapeHTML(String(v))}</div>`;
                }
            } else {
                html += `<div class="clinical-value-item">${escapeHTML(String(values))}</div>`;
            }

            html += '</div>';
        }
        html += '</div>';
        container.innerHTML = html;
    }

    function renderSections(data) {
        const container = document.getElementById('unstruct-sections');
        const sections = data.sections || [];

        if (sections.length === 0) {
            container.innerHTML = '<div class="empty-state">No document sections identified.</div>';
            return;
        }

        let html = '';
        for (const s of sections) {
            const preview = (s.content || '').substring(0, 150);
            html += `
                <div class="unstruct-section-item">
                    <div class="unstruct-section-heading">${escapeHTML(s.heading)}</div>
                    <div class="unstruct-section-meta">Line ${s.line_start} · ${s.word_count} words</div>
                    ${preview ? `<div class="unstruct-section-content">${escapeHTML(preview)}${s.content.length > 150 ? '...' : ''}</div>` : ''}
                </div>
            `;
        }
        container.innerHTML = html;
    }

    function renderLogEntries(data) {
        const section = document.getElementById('unstruct-log-section');
        const container = document.getElementById('unstruct-log-entries');
        const entries = data.log_entries || [];

        if (entries.length === 0) {
            section.classList.add('hidden');
            return;
        }

        section.classList.remove('hidden');
        let html = `<table class="unstruct-log-table">
            <thead><tr><th>Timestamp</th><th>Level</th><th>Source</th><th>Event Type</th><th>Details</th></tr></thead>
            <tbody>`;

        const displayed = entries.slice(0, 100);
        for (const e of displayed) {
            const levelClass = (e.level || '').toLowerCase();
            const fields = e.fields || {};
            const normalizedPayload = e.normalized_payload || {};
            const clinicalSnapshot = e.clinical_snapshot || {};
            const detailParts = [];

            if (e.summary) {
                detailParts.push(`<div><strong>Summary:</strong> ${escapeHTML(e.summary)}</div>`);
            }

            const fieldPreview = Object.entries(fields).slice(0, 3);
            if (fieldPreview.length) {
                detailParts.push(`<div><strong>Fields:</strong> ${fieldPreview.map(([key, value]) => `${escapeHTML(formatKey(key))}: ${escapeHTML(String(value))}`).join(' | ')}</div>`);
            }

            const normalizedPreview = Object.entries(normalizedPayload).slice(0, 4);
            if (normalizedPreview.length) {
                detailParts.push(`<div><strong>Normalized:</strong> ${normalizedPreview.map(([key, value]) => `${escapeHTML(formatKey(key))}: ${escapeHTML(renderInlineValue(value))}`).join(' | ')}</div>`);
            }

            const clinicalPreview = Object.entries(clinicalSnapshot).slice(0, 3);
            if (clinicalPreview.length) {
                detailParts.push(`<div><strong>Clinical:</strong> ${clinicalPreview.map(([key, value]) => {
                    if (value && typeof value === 'object' && value.systolic !== undefined) {
                        return `${escapeHTML(formatKey(key))}: ${value.systolic}/${value.diastolic}`;
                    }
                    return `${escapeHTML(formatKey(key))}: ${escapeHTML(String(value))}`;
                }).join(' | ')}</div>`);
            }

            html += `
                <tr>
                    <td style="white-space:nowrap">${escapeHTML(e.timestamp || '-')}</td>
                    <td><span class="log-level-badge ${levelClass}">${escapeHTML(e.level)}</span></td>
                    <td>${escapeHTML(e.source)}</td>
                    <td>
                        <div>${escapeHTML(formatKey(e.event_type || 'log_event'))}</div>
                        <div style="margin-top:4px;color:var(--text-muted);font-size:0.78rem;">Confidence: ${escapeHTML(String(e.parse_confidence ?? '-'))}</div>
                    </td>
                    <td style="max-width:520px;line-height:1.45;">${detailParts.join('') || escapeHTML(e.message)}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        if (entries.length > 100) {
            html += `<div style="margin-top:8px;color:var(--text-muted);font-size:0.8rem;">Showing 100 of ${entries.length} entries</div>`;
        }
        container.innerHTML = html;
    }

    function renderInlineValue(value) {
        if (Array.isArray(value)) {
            return value.join(', ');
        }
        if (value && typeof value === 'object') {
            return Object.entries(value)
                .map(([key, item]) => `${formatKey(key)}=${item}`)
                .join(', ');
        }
        return String(value);
    }

    function renderAbbreviations(data) {
        const container = document.getElementById('unstruct-abbreviations');
        const report = data.abbreviations_report || {};
        const expansions = report.expansions || {};
        const keys = Object.keys(expansions);

        if (keys.length === 0) {
            container.innerHTML = '<div class="empty-state">No medical abbreviations found to expand.</div>';
            return;
        }

        let html = '<div class="unstruct-abbrev-grid">';
        for (const abbrev of keys) {
            const info = expansions[abbrev];
            html += `
                <div class="unstruct-abbrev-item">
                    <span class="abbrev-code">${escapeHTML(abbrev.toUpperCase())}</span>
                    <span class="abbrev-arrow">→</span>
                    <span class="abbrev-full">${escapeHTML(info.expanded_to)}</span>
                    <span class="abbrev-count">×${info.count}</span>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    function renderSpellReport(data) {
        const container = document.getElementById('unstruct-spell-report');
        if (!container) return;

        const report = data.spell_correction_report || {};
        const corrections = Array.isArray(report.corrections)
            ? report.corrections
            : Object.entries(report.corrections || {}).map(([from, info]) => ({
                from,
                to: info.corrected_to,
                count: info.count || 1,
                type: info.layer || 'general',
            }));

        if (!corrections.length) {
            container.innerHTML = '<div class="empty-state">No spelling corrections were needed.</div>';
            return;
        }

        let html = `
            <div style="margin-bottom:10px; font-size:0.85rem; color:var(--text-muted);">
                Total: <strong>${report.total_corrections || corrections.length}</strong>
                (Medical: ${report.medical_fixes || 0}, General: ${report.general_fixes || 0})
            </div>
            <table class="unstruct-phi-table">
                <thead>
                    <tr>
                        <th>Original</th>
                        <th>Corrected</th>
                        <th>Count</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody>
        `;

        const shown = corrections.slice(0, 100);
        for (const c of shown) {
            html += `
                <tr>
                    <td><code>${escapeHTML(c.from || '')}</code></td>
                    <td><code>${escapeHTML(c.to || '')}</code></td>
                    <td>${c.count || 1}</td>
                    <td>${escapeHTML(c.type || 'general')}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        if (corrections.length > shown.length) {
            html += `<div style="margin-top:8px;color:var(--text-muted);font-size:0.8rem;">Showing ${shown.length} of ${corrections.length} corrections</div>`;
        }

        container.innerHTML = html;
    }

    function renderEntities(data) {
        const container = document.getElementById('unstruct-entities');
        if (!container) return;

        const entities = data.entities || [];
        if (!entities.length) {
            container.innerHTML = '<div class="empty-state">No medical entities extracted.</div>';
            return;
        }

        let html = `
            <table class="unstruct-phi-table">
                <thead>
                    <tr>
                        <th>Entity</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Section</th>
                        <th>Context</th>
                    </tr>
                </thead>
                <tbody>
        `;

        const shown = entities.slice(0, 200);
        for (const e of shown) {
            html += `
                <tr>
                    <td><strong>${escapeHTML(e.text || '')}</strong></td>
                    <td>${escapeHTML(e.type || '')}</td>
                    <td>${typeof e.confidence === 'number' ? e.confidence.toFixed(2) : '-'}</td>
                    <td>${escapeHTML(e.section || '-')}</td>
                    <td>${escapeHTML(e.context || '')}</td>
                </tr>
            `;
        }

        html += '</tbody></table>';
        if (entities.length > shown.length) {
            html += `<div style="margin-top:8px;color:var(--text-muted);font-size:0.8rem;">Showing ${shown.length} of ${entities.length} entities</div>`;
        }
        container.innerHTML = html;
    }

    function renderStructuredTables(data) {
        const container = document.getElementById('unstruct-structured-tables');
        if (!container) return;

        const tables = data.structured_tables || {};
        const vitals = Array.isArray(tables.vitals) ? tables.vitals : [];
        const entities = Array.isArray(tables.entities) ? tables.entities : [];
        const metrics = Array.isArray(tables.metrics) ? tables.metrics : [];
        const timeline = Array.isArray(tables.timeline) ? tables.timeline : [];

        if (!vitals.length && !entities.length && !metrics.length && !timeline.length) {
            container.innerHTML = '<div class="empty-state">No structured tables generated.</div>';
            return;
        }

        const csvButton = (label, rows) => rows.length
            ? `<button class="export-btn" style="margin-left:8px;" data-csv-label="${escapeHTML(label)}">Download CSV</button>`
            : '';

        let html = '';

        html += renderTableBlock('Vitals', vitals, ['Measurement', 'Raw_Value', 'Raw_Unit', 'Std_Value', 'Std_Unit', 'Source_Context'])
            .replace('</h4>', `${csvButton('vitals', vitals)}</h4>`);
        html += renderTableBlock('Entities', entities, ['Entity', 'Type', 'Confidence', 'Occurrence_Count', 'Section_ID', 'Section_Context', 'Context_Examples'])
            .replace('</h4>', `${csvButton('entities', entities)}</h4>`);
        html += renderTableBlock('Metrics', metrics, ['Metric', 'Value_Low', 'Value_High', 'Unit', 'Raw_Reference', 'Section_ID', 'Section_Context'])
            .replace('</h4>', `${csvButton('metrics', metrics)}</h4>`);
        html += renderTableBlock('Timeline', timeline, ['Date', 'Section_ID', 'Section', 'Event'])
            .replace('</h4>', `${csvButton('timeline', timeline)}</h4>`);

        container.innerHTML = html;

        container.querySelectorAll('button[data-csv-label]').forEach(btn => {
            btn.addEventListener('click', () => {
                const label = btn.getAttribute('data-csv-label');
                const rows = label === 'vitals'
                    ? vitals
                    : label === 'entities'
                        ? entities
                        : label === 'metrics'
                            ? metrics
                            : timeline;
                downloadCsv(label, rows);
            });
        });
    }

    function renderTableBlock(title, rows, columns) {
        if (!rows.length) {
            return `<div style="margin-bottom:14px;"><h4>${escapeHTML(title)}</h4><div class="empty-state">No rows</div></div>`;
        }

        let html = `<div style="margin-bottom:14px;"><h4>${escapeHTML(title)}</h4><table class="unstruct-phi-table"><thead><tr>`;
        for (const col of columns) {
            html += `<th>${escapeHTML(col)}</th>`;
        }
        html += '</tr></thead><tbody>';

        for (const row of rows.slice(0, 200)) {
            html += '<tr>';
            for (const col of columns) {
                const value = row[col];
                html += `<td>${escapeHTML(value === undefined || value === null ? '' : String(value))}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        return html;
    }

    function downloadCsv(label, rows) {
        if (!rows || !rows.length) return;

        const headerMap = {
            vitals: ['Measurement', 'Raw_Value', 'Raw_Unit', 'Std_Value', 'Std_Unit', 'Source_Context'],
            entities: ['Entity', 'Type', 'Confidence', 'Occurrence_Count', 'Section_ID', 'Section_Context', 'Context_Examples'],
            metrics: ['Metric', 'Value_Low', 'Value_High', 'Unit', 'Raw_Reference', 'Section_ID', 'Section_Context'],
            timeline: ['Date', 'Section_ID', 'Section', 'Event']
        };
        const headers = headerMap[label] || Object.keys(rows[0]);

        const normalizeCellText = (value, key) => {
            if (value === undefined || value === null) return '';
            let s = String(value).replace(/\r\n|\r|\n/g, ' ');
            s = s.replace(/\s+/g, ' ').trim();

            // Keep exported files compact and spreadsheet-friendly for free-text fields.
            const clipLimits = {
                Source_Context: 80,
                Context: 100,
                Context_Examples: 150,
                Section_Context: 120,
                Raw_Reference: 120,
                Event: 140,
            };
            const limit = clipLimits[key];
            if (limit && s.length > limit) {
                s = `${s.slice(0, limit)}...`;
            }
            return s;
        };

        const escapeCsv = (v) => {
            const s = String(v ?? '');
            return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        };

        let csv = headers.join(',') + '\n';
        for (const row of rows) {
            csv += headers.map(h => escapeCsv(normalizeCellText(row[h], h))).join(',') + '\n';
        }

        // Add BOM for better Excel UTF-8 compatibility on Windows.
        const bom = '\uFEFF';
        const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `unstructured_${label}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function renderProcessingLog(data) {
        const container = document.getElementById('unstruct-processing-log');
        const log = data.processing_log || [];

        if (log.length === 0) {
            container.innerHTML = '<div class="empty-state">No processing log entries.</div>';
            return;
        }

        let html = '<div class="unstruct-proc-log">';
        for (const entry of log) {
            html += `<div class="unstruct-log-entry ${escapeHTML(entry.level)}">
                [${escapeHTML(entry.timestamp?.split('T')[1]?.split('.')[0] || '')}] ${escapeHTML(entry.level)}: ${escapeHTML(entry.message)}
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }

    // ── Helpers ──
    function showLoading(msg) {
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
            const p = loadingOverlay.querySelector('p');
            if (p) p.textContent = msg || 'Processing...';
        }
    }

    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }

    function escapeHTML(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

})();
