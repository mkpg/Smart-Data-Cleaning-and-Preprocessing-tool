/**
 * Smart Data Cleaner — Visualization Module
 * Power BI / Tableau-like interactive dashboard with cross-filtering
 */

class VizDashboard {
    constructor() {
        this.sessionId = null;
        this.meta = null;
        this.cachedData = {};
        this.charts = [];       // { id, config, divId, data }
        this.filters = {};      // { column: value } cross-filter state
        this.chartCounter = 0;
        this.plotlyTheme = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(15,15,25,0.5)',
            font: { family: 'Inter, sans-serif', color: '#c8ccd4', size: 12 },
            colorway: ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#f43f5e', '#84cc16', '#a78bfa', '#fb923c'],
            xaxis: { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)' },
            yaxis: { gridcolor: 'rgba(255,255,255,0.06)', zerolinecolor: 'rgba(255,255,255,0.1)' },
            margin: { t: 40, r: 20, b: 50, l: 60 },
        };
        this.initElements();
        this.initEvents();
    }

    initElements() {
        this.sourceSelect = document.getElementById('viz-source');
        this.rowCount = document.getElementById('viz-row-count');
        this.fieldList = document.getElementById('viz-field-list');
        this.chartType = document.getElementById('viz-chart-type');
        this.xAxis = document.getElementById('viz-x-axis');
        this.yAxis = document.getElementById('viz-y-axis');
        this.colorGroup = document.getElementById('viz-color');
        this.aggSelect = document.getElementById('viz-agg');
        this.addBtn = document.getElementById('viz-add-chart');
        this.chartsGrid = document.getElementById('viz-charts-grid');
        this.activeFilters = document.getElementById('viz-active-filters');
        this.clearFiltersBtn = document.getElementById('viz-clear-filters');
        this.clearDashBtn = document.getElementById('viz-clear-dashboard');
    }

    initEvents() {
        this.sourceSelect.addEventListener('change', () => this.onSourceChange());
        this.addBtn.addEventListener('click', () => this.addChart());
        this.clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        this.clearDashBtn.addEventListener('click', () => this.clearDashboard());
        // Auto-load when visualize tab is shown
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.dataset.tab === 'visualize') this.loadMeta();
            });
        });
    }

    async loadMeta() {
        const sid = window.app?.sessionId;
        if (!sid) return;
        if (this.sessionId === sid && this.meta) return; // already loaded
        this.sessionId = sid;

        try {
            const res = await fetch(`/api/visualize/meta/${sid}`);
            this.meta = await res.json();
            this.cachedData = {};
            this.populateFields();
        } catch (e) {
            console.error('Failed to load viz meta:', e);
        }
    }

    populateFields() {
        const source = this.sourceSelect.value;
        const cols = source === 'cleaned' && this.meta.has_cleaned
            ? this.meta.cleaned_columns : this.meta.original_columns;
        const rows = source === 'cleaned' && this.meta.has_cleaned
            ? this.meta.cleaned_rows : this.meta.original_rows;

        this.rowCount.textContent = `${rows.toLocaleString()} rows`;

        // Field list (like Power BI)
        const typeIcons = { numeric: '🔢', categorical: '🏷️', datetime: '📅' };
        this.fieldList.innerHTML = cols.map(c => `
            <div class="viz-field-item" data-col="${c.name}" data-type="${c.type}" title="${c.dtype} | ${c.unique} unique | ${c.nulls} nulls">
                <span class="viz-field-icon">${typeIcons[c.type] || '📋'}</span>
                <span class="viz-field-name">${c.name}</span>
                <span class="viz-field-type">${c.type}</span>
            </div>
        `).join('');

        // Click to auto-assign fields
        this.fieldList.querySelectorAll('.viz-field-item').forEach(el => {
            el.addEventListener('click', () => {
                const col = el.dataset.col;
                if (!this.xAxis.value) { this.xAxis.value = col; }
                else if (!this.yAxis.value) { this.yAxis.value = col; }
                else { this.xAxis.value = col; }
                el.classList.add('viz-field-selected');
                setTimeout(() => el.classList.remove('viz-field-selected'), 400);
            });
        });

        // Populate dropdowns
        const options = cols.map(c => `<option value="${c.name}">${c.name} (${c.type})</option>`).join('');
        const emptyX = '<option value="">— Select column —</option>';
        const emptyC = '<option value="">— None —</option>';
        this.xAxis.innerHTML = emptyX + options;
        this.yAxis.innerHTML = emptyX + options;
        this.colorGroup.innerHTML = emptyC + options;
    }

    onSourceChange() {
        this.cachedData = {};
        this.populateFields();
        // Re-render all charts with new source
        if (this.charts.length > 0) this.renderAllCharts();
    }

    async fetchData(columns) {
        const key = columns.sort().join('|') + '|' + this.sourceSelect.value;
        if (this.cachedData[key]) return this.cachedData[key];

        const res = await fetch(`/api/visualize/data/${this.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: this.sourceSelect.value, columns })
        });
        const data = await res.json();
        this.cachedData[key] = data;
        return data;
    }

    async addChart() {
        const type = this.chartType.value;
        const x = this.xAxis.value;
        const y = this.yAxis.value;
        const color = this.colorGroup.value;
        const agg = this.aggSelect.value;

        // Validation
        if (type === 'heatmap') {
            // Heatmap needs no specific x/y
        } else if (type === 'histogram' || type === 'pie') {
            if (!x) return alert('Please select X-Axis column');
        } else {
            if (!x) return alert('Please select X-Axis column');
            if (!y && type !== 'histogram') return alert('Please select Y-Axis column');
        }

        const chartId = `viz-chart-${this.chartCounter++}`;
        const config = { type, x, y, color, agg, id: chartId };

        // Remove empty dashboard message
        const emptyMsg = this.chartsGrid.querySelector('.viz-empty-dashboard');
        if (emptyMsg) emptyMsg.remove();

        // Create chart container
        const wrapper = document.createElement('div');
        wrapper.className = 'viz-chart-wrapper';
        wrapper.id = `wrapper-${chartId}`;
        wrapper.innerHTML = `
            <div class="viz-chart-header">
                <span class="viz-chart-title">${this.getChartTitle(config)}</span>
                <button class="viz-chart-remove" data-chart-id="${chartId}">✕</button>
            </div>
            <div id="${chartId}" class="viz-chart-area"></div>
        `;
        this.chartsGrid.appendChild(wrapper);

        // Remove button
        wrapper.querySelector('.viz-chart-remove').addEventListener('click', () => {
            this.charts = this.charts.filter(c => c.id !== chartId);
            wrapper.remove();
            if (this.charts.length === 0) this.showEmptyDashboard();
        });

        // Fetch data and render
        this.charts.push(config);
        await this.renderChart(config);
    }

    getChartTitle(config) {
        const typeNames = {
            bar: 'Bar Chart', scatter: 'Scatter Plot', line: 'Line Chart',
            histogram: 'Histogram', box: 'Box Plot', pie: 'Pie Chart',
            heatmap: 'Correlation Heatmap', violin: 'Violin Plot'
        };
        let title = typeNames[config.type] || config.type;
        if (config.x) title += ` — ${config.x}`;
        if (config.y) title += ` vs ${config.y}`;
        if (config.agg && config.agg !== 'none') title += ` (${config.agg})`;
        return title;
    }

    async renderChart(config, filterOverride = null) {
        const cols = [config.x, config.y, config.color].filter(Boolean);
        if (config.type === 'heatmap') {
            // Fetch all numeric columns
            const source = this.sourceSelect.value;
            const allCols = (source === 'cleaned' && this.meta.has_cleaned
                ? this.meta.cleaned_columns : this.meta.original_columns)
                .filter(c => c.type === 'numeric').map(c => c.name);
            const data = await this.fetchData(allCols);
            this.plotHeatmap(config, data, allCols);
            return;
        }

        const data = await this.fetchData(cols);

        // Apply cross-filters
        const filters = filterOverride || this.filters;
        let indices = null;
        if (Object.keys(filters).length > 0) {
            indices = [];
            const len = data.columns[cols[0]]?.length || 0;
            for (let i = 0; i < len; i++) {
                let match = true;
                for (const [fCol, fVal] of Object.entries(filters)) {
                    if (data.columns[fCol] && String(data.columns[fCol][i]) !== String(fVal)) {
                        match = false;
                        break;
                    }
                }
                if (match) indices.push(i);
            }
        }

        const filtered = {};
        for (const col of cols) {
            if (!data.columns[col]) continue;
            filtered[col] = indices
                ? indices.map(i => data.columns[col][i])
                : data.columns[col];
        }

        const chartDiv = document.getElementById(config.id);
        if (!chartDiv) return;

        switch (config.type) {
            case 'bar': this.plotBar(config, filtered); break;
            case 'scatter': this.plotScatter(config, filtered); break;
            case 'line': this.plotLine(config, filtered); break;
            case 'histogram': this.plotHistogram(config, filtered); break;
            case 'box': this.plotBox(config, filtered); break;
            case 'pie': this.plotPie(config, filtered); break;
            case 'violin': this.plotViolin(config, filtered); break;
        }

        // Attach cross-filter click handler
        chartDiv.on('plotly_click', (eventData) => {
            if (!eventData.points || !eventData.points[0]) return;
            const pt = eventData.points[0];
            const filterCol = config.x;
            const filterVal = pt.x ?? pt.label;
            if (filterCol && filterVal !== undefined) {
                this.applyFilter(filterCol, filterVal, config.id);
            }
        });
    }

    // ── Chart Plotting Methods ──────────────────────

    plotBar(config, data) {
        let traces;
        const x = data[config.x] || [];
        const y = data[config.y] || [];

        if (config.agg !== 'none' && config.agg) {
            const agged = this.aggregate(x, y, config.agg);
            traces = [{
                x: agged.labels, y: agged.values, type: 'bar',
                marker: {
                    color: this.plotlyTheme.colorway[0], opacity: 0.85,
                    line: { color: this.plotlyTheme.colorway[0], width: 1 }
                }
            }];
        } else {
            traces = [{
                x, y, type: 'bar',
                marker: { color: this.plotlyTheme.colorway[0], opacity: 0.85 }
            }];
        }

        Plotly.react(config.id, traces, {
            ...this.plotlyTheme, title: '', xaxis: { ...this.plotlyTheme.xaxis, title: config.x },
            yaxis: { ...this.plotlyTheme.yaxis, title: config.y }
        }, { responsive: true, displayModeBar: true, modeBarButtonsToRemove: ['lasso2d', 'select2d'] });
    }

    plotScatter(config, data) {
        const trace = {
            x: data[config.x] || [], y: data[config.y] || [],
            mode: 'markers', type: 'scatter',
            marker: {
                size: 7, opacity: 0.7, color: this.plotlyTheme.colorway[1],
                line: { width: 1, color: 'rgba(255,255,255,0.3)' }
            }
        };

        if (config.color && data[config.color]) {
            trace.marker.color = data[config.color];
            trace.marker.colorscale = 'Viridis';
            trace.marker.showscale = true;
        }

        Plotly.react(config.id, [trace], {
            ...this.plotlyTheme, title: '',
            xaxis: { ...this.plotlyTheme.xaxis, title: config.x },
            yaxis: { ...this.plotlyTheme.yaxis, title: config.y }
        }, { responsive: true });
    }

    plotLine(config, data) {
        const trace = {
            x: data[config.x] || [], y: data[config.y] || [],
            mode: 'lines+markers', type: 'scatter',
            line: { color: this.plotlyTheme.colorway[4], width: 2 },
            marker: { size: 4 }
        };
        Plotly.react(config.id, [trace], {
            ...this.plotlyTheme, title: '',
            xaxis: { ...this.plotlyTheme.xaxis, title: config.x },
            yaxis: { ...this.plotlyTheme.yaxis, title: config.y }
        }, { responsive: true });
    }

    plotHistogram(config, data) {
        const trace = {
            x: data[config.x] || [], type: 'histogram',
            marker: {
                color: this.plotlyTheme.colorway[2], opacity: 0.8,
                line: { color: 'rgba(255,255,255,0.2)', width: 1 }
            },
            nbinsx: 30
        };
        Plotly.react(config.id, [trace], {
            ...this.plotlyTheme, title: '',
            xaxis: { ...this.plotlyTheme.xaxis, title: config.x },
            yaxis: { ...this.plotlyTheme.yaxis, title: 'Count' },
            bargap: 0.05
        }, { responsive: true });
    }

    plotBox(config, data) {
        const traces = [];
        if (config.x && config.y) {
            const groups = [...new Set(data[config.x] || [])];
            groups.slice(0, 20).forEach((g, i) => {
                const vals = (data[config.y] || []).filter((_, idx) => data[config.x][idx] === g);
                traces.push({
                    y: vals, name: String(g), type: 'box',
                    marker: { color: this.plotlyTheme.colorway[i % 10] }
                });
            });
        } else {
            traces.push({
                y: data[config.y || config.x] || [], type: 'box',
                marker: { color: this.plotlyTheme.colorway[0] }
            });
        }
        Plotly.react(config.id, traces, { ...this.plotlyTheme, title: '', showlegend: traces.length > 1 }, { responsive: true });
    }

    plotPie(config, data) {
        const values = {};
        (data[config.x] || []).forEach(v => {
            // Skip empty, blank, null, NaN, "0", "nan", "None" values
            const str = String(v).trim();
            if (!str || str === '' || str === '0' || str === 'nan' || str === 'NaN' || str === 'None' || str === 'null') return;
            const label = str.length > 30 ? str.substring(0, 27) + '...' : str;  // Truncate long labels
            values[label] = (values[label] || 0) + 1;
        });
        const sorted = Object.entries(values).sort((a, b) => b[1] - a[1]).slice(0, 15);

        if (sorted.length === 0) {
            const div = document.getElementById(config.id);
            if (div) div.innerHTML = '<div class="viz-empty">No valid categories found in this column</div>';
            return;
        }

        Plotly.react(config.id, [{
            labels: sorted.map(s => s[0]), values: sorted.map(s => s[1]),
            type: 'pie', hole: 0.4,
            marker: { colors: this.plotlyTheme.colorway },
            textinfo: 'label+percent', textposition: 'outside',
            textfont: { color: '#c8ccd4', size: 11 }
        }], {
            ...this.plotlyTheme, title: '', showlegend: sorted.length <= 8,
            legend: { font: { color: '#c8ccd4', size: 10 } },
            margin: { t: 20, r: 20, b: 30, l: 20 }
        },
            { responsive: true });
    }

    plotHeatmap(config, data, numericCols) {
        const n = numericCols.length;
        const matrix = [];
        for (let i = 0; i < n; i++) {
            const row = [];
            for (let j = 0; j < n; j++) {
                const a = data.columns[numericCols[i]] || [];
                const b = data.columns[numericCols[j]] || [];
                row.push(this.pearsonCorr(a, b));
            }
            matrix.push(row);
        }
        Plotly.react(config.id, [{
            z: matrix, x: numericCols, y: numericCols,
            type: 'heatmap', colorscale: 'RdBu', zmid: 0,
            text: matrix.map(r => r.map(v => v.toFixed(2))), texttemplate: '%{text}',
            textfont: { size: 10 }
        }], {
            ...this.plotlyTheme, title: '', margin: { t: 20, r: 20, b: 100, l: 100 },
            xaxis: { tickangle: -45 }
        }, { responsive: true });
    }

    plotViolin(config, data) {
        const traces = [];
        if (config.x && config.y) {
            const groups = [...new Set(data[config.x] || [])];
            groups.slice(0, 10).forEach((g, i) => {
                const vals = (data[config.y] || []).filter((_, idx) => data[config.x][idx] === g);
                traces.push({
                    y: vals, name: String(g), type: 'violin', box: { visible: true },
                    meanline: { visible: true }, marker: { color: this.plotlyTheme.colorway[i % 10] }
                });
            });
        } else {
            traces.push({
                y: data[config.y || config.x] || [], type: 'violin',
                box: { visible: true }, meanline: { visible: true }
            });
        }
        Plotly.react(config.id, traces, { ...this.plotlyTheme, title: '', showlegend: traces.length > 1 }, { responsive: true });
    }

    // ── Aggregation Helper ──────────────────────────

    aggregate(xValues, yValues, method) {
        const groups = {};
        xValues.forEach((x, i) => {
            const key = String(x);
            if (!groups[key]) groups[key] = [];
            if (yValues[i] !== undefined && yValues[i] !== null) groups[key].push(Number(yValues[i]));
        });

        const labels = Object.keys(groups);
        const values = labels.map(key => {
            const arr = groups[key];
            if (arr.length === 0) return 0;
            switch (method) {
                case 'count': return arr.length;
                case 'sum': return arr.reduce((a, b) => a + b, 0);
                case 'mean': return arr.reduce((a, b) => a + b, 0) / arr.length;
                case 'median': { const s = [...arr].sort((a, b) => a - b); const m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
                case 'min': return Math.min(...arr);
                case 'max': return Math.max(...arr);
                default: return arr.reduce((a, b) => a + b, 0) / arr.length;
            }
        });
        return { labels, values };
    }

    pearsonCorr(a, b) {
        const n = Math.min(a.length, b.length);
        if (n === 0) return 0;
        let sumA = 0, sumB = 0, sumAB = 0, sumA2 = 0, sumB2 = 0;
        for (let i = 0; i < n; i++) {
            const va = Number(a[i]) || 0, vb = Number(b[i]) || 0;
            sumA += va; sumB += vb; sumAB += va * vb;
            sumA2 += va * va; sumB2 += vb * vb;
        }
        const num = n * sumAB - sumA * sumB;
        const den = Math.sqrt((n * sumA2 - sumA ** 2) * (n * sumB2 - sumB ** 2));
        return den === 0 ? 0 : num / den;
    }

    // ── Cross-Filtering ─────────────────────────────

    applyFilter(column, value, sourceChartId) {
        this.filters[column] = value;
        this.renderFilterUI();
        // Re-render all charts except the source
        this.charts.forEach(config => {
            if (config.id !== sourceChartId) this.renderChart(config);
        });
        // Highlight the source chart's selected element
        this.highlightSourceChart(sourceChartId, column, value);
    }

    highlightSourceChart(chartId, column, value) {
        // Add a visual indicator on the source chart
        const div = document.getElementById(chartId);
        if (!div) return;
        const wrapper = div.closest('.viz-chart-wrapper');
        if (wrapper) {
            wrapper.classList.add('viz-chart-filtered');
            wrapper.dataset.filterInfo = `${column} = ${value}`;
        }
    }

    clearFilters() {
        this.filters = {};
        this.renderFilterUI();
        document.querySelectorAll('.viz-chart-filtered').forEach(el => {
            el.classList.remove('viz-chart-filtered');
            delete el.dataset.filterInfo;
        });
        this.renderAllCharts();
    }

    renderFilterUI() {
        const entries = Object.entries(this.filters);
        if (entries.length === 0) {
            this.activeFilters.innerHTML = '<div class="viz-empty">Click a chart element to cross-filter</div>';
            this.clearFiltersBtn.style.display = 'none';
            return;
        }
        this.activeFilters.innerHTML = entries.map(([col, val]) =>
            `<div class="viz-filter-tag">
                <span class="viz-filter-col">${col}</span>
                <span class="viz-filter-eq">=</span>
                <span class="viz-filter-val">${val}</span>
                <button class="viz-filter-remove" data-col="${col}">✕</button>
            </div>`
        ).join('');
        this.clearFiltersBtn.style.display = 'block';

        // Individual filter remove
        this.activeFilters.querySelectorAll('.viz-filter-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                delete this.filters[btn.dataset.col];
                this.renderFilterUI();
                this.renderAllCharts();
            });
        });
    }

    async renderAllCharts() {
        for (const config of this.charts) {
            await this.renderChart(config);
        }
    }

    clearDashboard() {
        this.charts = [];
        this.filters = {};
        this.chartCounter = 0;
        this.renderFilterUI();
        this.showEmptyDashboard();
    }

    showEmptyDashboard() {
        this.chartsGrid.innerHTML = `
            <div class="viz-empty-dashboard">
                <span class="viz-empty-icon">📊</span>
                <p>Configure a chart on the left and click <strong>"Add Chart"</strong> to start building your dashboard</p>
                <p class="viz-empty-hint">💡 Click on any chart element to cross-filter all other charts</p>
            </div>`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.vizDashboard = new VizDashboard();
});
