/**
 * Data Preview Table - Interactive Data Exploration
 * Phase 3: Professional UX Enhancement
 */

class DataPreviewTable {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.data = [];
        this.columns = [];
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.currentPage = 0;
        this.rowsPerPage = 100;
        this.searchQuery = '';
        this.qualityInfo = {};
    }

    /**
     * Render the interactive table with quality indicators
     * @param {Array} data - Array of row objects
     * @param {Object} qualityInfo - Column-level quality metrics
     */
    render(data, qualityInfo = {}) {
        if (!this.container) return;

        this.data = data;
        this.qualityInfo = qualityInfo;

        if (data.length === 0) {
            this.container.innerHTML = '<p class="no-data">No data available to preview</p>';
            return;
        }

        this.columns = Object.keys(data[0]);

        // Full render if empty or new data
        const wrapper = this.container.querySelector('.preview-table-wrapper');
        if (!wrapper) {
            this.container.innerHTML = `
                <div class="preview-table-wrapper">
                    <div id="preview-controls-container">${this.renderControls()}</div>
                    <div id="preview-stats-container">${this.renderStats()}</div>
                    <div class="table-scroll-container">
                        <table class="preview-table">
                            <thead>
                                <tr>
                                    <th class="row-number-header">#</th>
                                    ${this.columns.map(col => this.renderColumnHeader(col)).join('')}
                                </tr>
                            </thead>
                            <tbody id="preview-table-body">
                                ${this.renderTableBody()}
                            </tbody>
                        </table>
                    </div>
                    <div id="preview-pagination-container">${this.renderPagination()}</div>
                </div>
            `;
            this.attachPersistentListeners();
            this.attachSortListeners();
        } else {
            // Save focus and cursor position
            const activeEl = document.activeElement;
            const isSearchFocused = activeEl && activeEl.id === 'preview-search';
            const selectionStart = isSearchFocused ? activeEl.selectionStart : null;
            const selectionEnd = isSearchFocused ? activeEl.selectionEnd : null;

            this.updateDataView();

            // Restore focus if it was lost
            if (isSearchFocused) {
                const searchInput = document.getElementById('preview-search');
                if (searchInput && document.activeElement !== searchInput) {
                    searchInput.focus();
                    if (selectionStart !== null) {
                        searchInput.setSelectionRange(selectionStart, selectionEnd);
                    }
                }
            }
        }
    }

    updateDataView() {
        const stats = document.getElementById('preview-stats-container');
        const body = document.getElementById('preview-table-body');
        const pagination = document.getElementById('preview-pagination-container');

        if (stats) stats.innerHTML = this.renderStats();
        if (body) body.innerHTML = this.renderTableBody();
        if (pagination) pagination.innerHTML = this.renderPagination();
    }

    renderControls() {
        return `
            <div class="preview-controls">
                <div class="control-group">
                    <input 
                        type="text" 
                        id="preview-search" 
                        class="preview-search-input"
                        placeholder="🔍 Search across all columns..."
                        value="${this.searchQuery}"
                    >
                    <button class="btn-secondary" onclick="previewTable.resetFilters()">
                        Clear Filters
                    </button>
                </div>
                <div class="control-group">
                    <label>Rows per page:</label>
                    <select id="rows-per-page" class="rows-select">
                        <option value="50">50</option>
                        <option value="100" selected>100</option>
                        <option value="250">250</option>
                        <option value="500">500</option>
                    </select>
                    <button class="btn-secondary" onclick="previewTable.exportCurrentView()">
                        📊 Export View
                    </button>
                </div>
            </div>
        `;
    }

    renderStats() {
        const totalRows = this.data.length;
        const displayedRows = this.getFilteredData().length;
        const currentPageStart = this.currentPage * this.rowsPerPage + 1;
        const currentPageEnd = Math.min((this.currentPage + 1) * this.rowsPerPage, displayedRows);

        return `
            <div class="preview-stats">
                <span>
                    Showing ${currentPageStart}-${currentPageEnd} of ${displayedRows.toLocaleString()} rows
                    ${displayedRows !== totalRows ? `(filtered from ${totalRows.toLocaleString()})` : ''}
                </span>
                <span>${this.columns.length} columns</span>
            </div>
        `;
    }

    renderTableBody() {
        const filteredData = this.getFilteredData();
        const pagedData = this.getPagedData(filteredData);

        if (pagedData.length === 0) {
            return `<tr><td colspan="${this.columns.length + 1}" class="no-data">No matching rows found</td></tr>`;
        }

        return pagedData.map((row, index) => this.renderRow(row, this.currentPage * this.rowsPerPage + index)).join('');
    }

    renderColumnHeader(column) {
        const isSorted = this.sortColumn === column;
        const sortIcon = isSorted
            ? (this.sortDirection === 'asc' ? '▲' : '▼')
            : '⇅';

        const quality = this.getColumnQuality(column);
        const qualityIndicator = this.getQualityIndicator(quality);

        return `
            <th class="sortable-header ${isSorted ? 'active-sort' : ''}" data-column="${column}">
                <div class="header-content">
                    <span class="column-name" title="${column}">${column}</span>
                    <span class="sort-icon">${sortIcon}</span>
                </div>
                ${qualityIndicator ? `<div class="quality-badge">${qualityIndicator}</div>` : ''}
            </th>
        `;
    }

    renderRow(row, index) {
        return `
            <tr class="data-row">
                <td class="row-number">${index + 1}</td>
                ${this.columns.map(col => this.renderCell(row[col], col)).join('')}
            </tr>
        `;
    }

    renderCell(value, column) {
        const quality = this.getCellQuality(value, column);
        const qualityClass = this.getQualityClass(quality);
        const displayValue = this.formatCellValue(value);

        return `
            <td class="data-cell ${qualityClass}" title="${displayValue}">
                ${displayValue}
            </td>
        `;
    }

    renderPagination() {
        const filteredData = this.getFilteredData();
        const totalPages = Math.ceil(filteredData.length / this.rowsPerPage);

        if (totalPages <= 1) return '';

        const pageButtons = [];
        const maxButtons = 7;

        // Always show first page
        pageButtons.push(0);

        if (totalPages <= maxButtons) {
            // Show all pages
            for (let i = 1; i < totalPages; i++) {
                pageButtons.push(i);
            }
        } else {
            // Show pages around current page
            const start = Math.max(1, this.currentPage - 2);
            const end = Math.min(totalPages - 1, this.currentPage + 2);

            if (start > 1) pageButtons.push('...');
            for (let i = start; i < end; i++) {
                pageButtons.push(i);
            }
            if (end < totalPages - 1) pageButtons.push('...');
            pageButtons.push(totalPages - 1);
        }

        return `
            <div class="pagination-controls">
                <button 
                    class="btn-pagination" 
                    ${this.currentPage === 0 ? 'disabled' : ''}
                    onclick="previewTable.goToPage(0)"
                >
                    ⏮ First
                </button>
                <button 
                    class="btn-pagination" 
                    ${this.currentPage === 0 ? 'disabled' : ''}
                    onclick="previewTable.previousPage()"
                >
                    ◀ Previous
                </button>
                
                <div class="page-numbers">
                    ${pageButtons.map(page =>
            page === '...'
                ? '<span class="page-ellipsis">...</span>'
                : `<button 
                                class="btn-page ${page === this.currentPage ? 'active' : ''}" 
                                onclick="previewTable.goToPage(${page})"
                               >
                                ${page + 1}
                               </button>`
        ).join('')}
                </div>

                <button 
                    class="btn-pagination" 
                    ${this.currentPage >= totalPages - 1 ? 'disabled' : ''}
                    onclick="previewTable.nextPage()"
                >
                    Next ▶
                </button>
                <button 
                    class="btn-pagination" 
                    ${this.currentPage >= totalPages - 1 ? 'disabled' : ''}
                    onclick="previewTable.goToPage(${totalPages - 1})"
                >
                    Last ⏭
                </button>
            </div>
        `;
    }

    attachPersistentListeners() {
        // Search input with debouncing
        const searchInput = document.getElementById('preview-search');
        if (searchInput) {
            let debounceTimeout;
            searchInput.addEventListener('input', (e) => {
                const value = e.target.value.toLowerCase();
                this.searchQuery = value;
                this.currentPage = 0;

                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    this.render(this.data, this.qualityInfo);
                }, 150); // 150ms debounce for responsiveness
            });
        }

        // Rows per page selector
        const rowsSelect = document.getElementById('rows-per-page');
        if (rowsSelect) {
            rowsSelect.addEventListener('change', (e) => {
                this.rowsPerPage = parseInt(e.target.value);
                this.currentPage = 0;
                this.render(this.data, this.qualityInfo);
            });
        }
    }

    attachSortListeners() {
        // Column headers for sorting
        document.querySelectorAll('.sortable-header').forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.column;
                this.sortByColumn(column);
            });
        });
    }

    sortByColumn(column) {
        if (this.sortColumn === column) {
            // Toggle direction
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }

        // Sort data
        this.data.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];

            // Handle null/undefined
            if (aVal == null && bVal == null) return 0;
            if (aVal == null) return 1;
            if (bVal == null) return -1;

            // Numeric comparison
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return this.sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
            }

            // String comparison
            const comparison = String(aVal).localeCompare(String(bVal));
            return this.sortDirection === 'asc' ? comparison : -comparison;
        });

        // Re-render the whole table when sorting because headers change (icons)
        const wrapper = this.container.querySelector('.preview-table-wrapper');
        if (wrapper) {
            // Find the table and replace its thead and tbody
            const thead = wrapper.querySelector('thead');
            const tbody = wrapper.querySelector('tbody');
            if (thead) thead.innerHTML = `
                <tr>
                    <th class="row-number-header">#</th>
                    ${this.columns.map(col => this.renderColumnHeader(col)).join('')}
                </tr>
            `;
            if (tbody) tbody.innerHTML = this.renderTableBody();

            // Re-attach sort listeners to new headers
            this.attachSortListeners();
            // Update stats/pagination
            this.updateStats();
        }
    }

    updateStats() {
        const stats = document.getElementById('preview-stats-container');
        const pagination = document.getElementById('preview-pagination-container');
        if (stats) stats.innerHTML = this.renderStats();
        if (pagination) pagination.innerHTML = this.renderPagination();
    }

    getFilteredData() {
        if (!this.searchQuery) return this.data;

        return this.data.filter(row => {
            return this.columns.some(col => {
                const value = row[col];
                if (value == null) return false;
                return String(value).toLowerCase().includes(this.searchQuery);
            });
        });
    }

    getPagedData(filteredData) {
        const start = this.currentPage * this.rowsPerPage;
        const end = start + this.rowsPerPage;
        return filteredData.slice(start, end);
    }

    goToPage(pageNumber) {
        const filteredData = this.getFilteredData();
        const totalPages = Math.ceil(filteredData.length / this.rowsPerPage);
        this.currentPage = Math.max(0, Math.min(pageNumber, totalPages - 1));
        this.render(this.data, this.qualityInfo);
    }

    nextPage() {
        this.goToPage(this.currentPage + 1);
    }

    previousPage() {
        this.goToPage(this.currentPage - 1);
    }

    resetFilters() {
        this.searchQuery = '';
        this.currentPage = 0;
        this.sortColumn = null;
        this.sortDirection = 'asc';

        // Reset input value manually and refocus
        const searchInput = document.getElementById('preview-search');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }

        this.render(this.data, this.qualityInfo);
    }

    getColumnQuality(column) {
        if (!this.qualityInfo || !this.qualityInfo[column]) return null;
        return this.qualityInfo[column].quality_score || null;
    }

    getCellQuality(value, column) {
        // Null/missing values
        if (value == null || value === '') return 'missing';

        // Check column-specific quality
        const colQuality = this.getColumnQuality(column);
        if (colQuality !== null) {
            if (colQuality >= 80) return 'good';
            if (colQuality >= 60) return 'warning';
            return 'poor';
        }

        return 'good';
    }

    getQualityClass(quality) {
        const classes = {
            'good': 'cell-quality-good',
            'warning': 'cell-quality-warning',
            'poor': 'cell-quality-poor',
            'missing': 'cell-quality-missing'
        };
        return classes[quality] || '';
    }

    getQualityIndicator(qualityScore) {
        if (qualityScore === null || qualityScore === undefined) return '';

        if (qualityScore >= 80) return '<span title="High Quality">🟢</span>';
        if (qualityScore >= 60) return '<span title="Medium Quality">🟡</span>';
        return '<span title="Low Quality">🔴</span>';
    }

    formatCellValue(value) {
        if (value == null) return '<span class="null-value">NULL</span>';
        if (value === '') return '<span class="empty-value">EMPTY</span>';

        // Truncate long values
        const str = String(value);
        if (str.length > 100) {
            return str.substring(0, 100) + '...';
        }

        return str;
    }

    exportCurrentView() {
        const filteredData = this.getFilteredData();

        if (filteredData.length === 0) {
            alert('No data to export');
            return;
        }

        // Convert to CSV
        const headers = this.columns.join(',');
        const rows = filteredData.map(row =>
            this.columns.map(col => {
                const value = row[col];
                if (value == null) return '';
                // Escape commas and quotes
                const str = String(value);
                if (str.includes(',') || str.includes('"')) {
                    return `"${str.replace(/"/g, '""')}"`;
                }
                return str;
            }).join(',')
        );

        const csv = [headers, ...rows].join('\n');

        // Download
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `preview_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Global instance (initialized by app.js)
let previewTable = null;
