// PUBLIC/js/dashboard.js
// =====================

console.log("Dashboard.js is loading...");

// Error handling for broken images and resources
window.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG') {
        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZjNmNGY2Ii8+Cjwvc3ZnPgo=';
        return true;
    }
    console.error('Resource loading error:', e);
}, true);

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    e.preventDefault();
});

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    initializeDashboard();
});

/* ------------------------------------------------------------------
   UTILITIES
------------------------------------------------------------------ */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

const headers = ['system', 'organization', 'framework', 'controls', 'controller', 'status', 'progress', 'deadline', 'evidence'];
const sortDirection = {};
let lastNotificationId = 0;

// Helper function to replace __ID__ in URLs
function withId(urlBase, id) {
    if (!urlBase) return '';
    return urlBase.replace('__ID__', id);
}

// Safe API function with error handling
function api(url, opts = {}) {
    if (!url || url.includes('undefined') || url === '') {
        console.warn('Invalid API URL:', url);
        return Promise.resolve({ success: false, message: 'Invalid URL' });
    }

    const defaultOptions = {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
        }
    };

    // Add CSRF token if available
    if (window.djangoData?.csrfToken) {
        defaultOptions.headers['X-CSRFToken'] = window.djangoData.csrfToken;
    }

    return fetch(url, { ...defaultOptions, ...opts })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('API Error:', error);
            return { success: false, message: error.message };
        });
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 10px 20px;
        border-radius: 4px;
        color: white;
        z-index: 1000;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function hideLoadingScreen() {
    const loadingScreen = $('.loading-screen');
    if (loadingScreen) {
        setTimeout(() => {
            loadingScreen.classList.add('hidden');
            console.log('Loading screen hidden');
        }, 100);
    }
}

/* ------------------------------------------------------------------
   DASHBOARD INITIALIZATION
------------------------------------------------------------------ */
function initializeDashboard() {
    console.log('Initializing dashboard...');

    try {
        // Initialize components in order
        initializeComponents();
        setupEventListeners();
        hookGlobalButtons();
        initializeModals();
        initializeChart();

        // Hide loading screen after initialization
        hideLoadingScreen();

        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Dashboard initialization failed:', error);
        showNotification('Dashboard failed to initialize', 'error');
        hideLoadingScreen();
    }
}

function initializeComponents() {
    // Initialize periodic updates
    setInterval(updateCountdowns, 60000); // Every minute

    // Initialize notifications refresh
    if (window.djangoData?.notificationsPartialUrl) {
        refreshNotifications();
        setInterval(refreshNotifications, 30000); // Every 30 seconds
    }

    // Render initial data
    renderSummaryRows();
    updateCountdowns();
}

function setupEventListeners() {
    console.log('Setting up event listeners...');

    // Search functionality
    const searchInput = $('#searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchTable, 300));
    }

    // Filter functionality
    const filterInputs = ['#systemFilter', '#organizationFilter', '#frameworkFilter', '#statusFilter', '#controllerFilter'];
    filterInputs.forEach(selector => {
        const input = $(selector);
        if (input) {
            input.addEventListener('change', applyFilters);
        }
    });

    // System row expansion
    $$('.system-row').forEach(row => {
        row.addEventListener('click', (e) => {
            if (e.target.classList.contains('expand-icon')) {
                toggleSystemExpansion(row.dataset.systemId);
            }
        });
    });

    // Notification filter
    const notificationFilter = $('#notificationFilter');
    if (notificationFilter) {
        notificationFilter.addEventListener('change', filterNotifications);
    }

    // Table sorting
    $$('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const colIndex = parseInt(th.dataset.sort);
            sortTable(colIndex);
        });
    });
}

function hookGlobalButtons() {
    console.log('Hooking global buttons...');

    // Filter toggle button
    const filterBtn = $('#filterBtn');
    if (filterBtn) {
        filterBtn.addEventListener('click', toggleFilter);
    }

    // Add system button
    const addBtn = $('#addSystemButton');
    if (addBtn) {
        addBtn.addEventListener('click', openAddSystemModal);
    }

    // Clear filters button
    const clearFiltersBtn = $('#clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }

    // Modal close buttons
    $$('.modal .close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = btn.closest('.modal');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Modal background click to close
    $$('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Form submissions
    const addSystemForm = $('#addSystemForm');
    if (addSystemForm) {
        addSystemForm.addEventListener('submit', (e) => {
            e.preventDefault();
            addSystem();
        });
    }
}

function initializeModals() {
    console.log('Initializing modals...');

    // Progress slider
    const progressSlider = $('#editFrameworkProgress');
    if (progressSlider) {
        progressSlider.addEventListener('input', (e) => {
            const progressValue = $('#progressValue');
            if (progressValue) {
                progressValue.textContent = `${e.target.value}%`;
            }
        });
    }

    // Implementation questions
    $$('.implementation-question input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const prevInfo = $('#previouslyImplementedInfo');
            const newInfo = $('#newImplementationInfo');
            if (prevInfo) prevInfo.style.display = radio.value === 'true' ? 'block' : 'none';
            if (newInfo) newInfo.style.display = radio.value === 'false' ? 'block' : 'none';
        });
    });
}

function initializeChart() {
    const ctx = $('#statusChart')?.getContext('2d');
    if (!ctx) {
        console.warn('Chart context not found');
        return;
    }

    if (typeof Chart === 'undefined') {
        console.warn('Chart.js library not loaded');
        return;
    }

    try {
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Compliant', 'Non-Compliant', 'Partially Compliant', 'Under Review'],
                datasets: [{
                    data: [
                        window.djangoData?.compliant_controls || 0,
                        window.djangoData?.non_compliant_controls || 0,
                        window.djangoData?.partial_count || 0,
                        window.djangoData?.pending_controls || 0
                    ],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#8b5cf6']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' }
                }
            }
        });
    } catch (error) {
        console.error('Chart initialization failed:', error);
    }
}

/* ------------------------------------------------------------------
   UTILITY FUNCTIONS
------------------------------------------------------------------ */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/* ------------------------------------------------------------------
   FEATURE FUNCTIONS
------------------------------------------------------------------ */
function toggleFilter() {
    const filterPanel = $('#filterPanel');
    if (filterPanel) {
        filterPanel.classList.toggle('active');
        filterPanel.style.display = filterPanel.classList.contains('active') ? 'block' : 'none';
    }
}

function applyFilters() {
    const systemFilter = $('#systemFilter')?.value || '';
    const organizationFilter = $('#organizationFilter')?.value || '';
    const frameworkFilter = $('#frameworkFilter')?.value || '';
    const statusFilter = $('#statusFilter')?.value || '';
    const controllerFilter = $('#controllerFilter')?.value || '';

    $$('.framework-row').forEach(row => {
        const systemId = row.classList[1]?.split('-')[1] || '';
        const organization = row.cells[1]?.textContent.trim() || '';
        const framework = row.cells[2]?.textContent.trim() || '';
        const status = $('.status-badge', row)?.className.match(/status-(\w+)/)?.[1] || '';
        const controller = row.cells[4]?.textContent.trim() || '';

        const show =
            (!systemFilter || systemId === systemFilter) &&
            (!organizationFilter || organization === organizationFilter) &&
            (!frameworkFilter || framework === frameworkFilter) &&
            (!statusFilter || status === statusFilter) &&
            (!controllerFilter || controller.includes(controllerFilter));

        row.classList.toggle('hidden', !show);
    });
}

function clearFilters() {
    ['#systemFilter', '#organizationFilter', '#frameworkFilter', '#statusFilter', '#controllerFilter'].forEach(id => {
        const input = $(id);
        if (input) input.value = '';
    });
    applyFilters();
}

function searchTable() {
    const query = $('#searchInput')?.value.toLowerCase() || '';
    $$('.framework-row').forEach(row => {
        const text = Array.from(row.cells || [])
            .slice(0, -1)
            .map(cell => cell?.textContent.toLowerCase() || '')
            .join(' ');
        row.classList.toggle('hidden', query && !text.includes(query));
    });
}

function toggleSystemExpansion(systemId) {
    const rows = $$(`.framework-row.system-${systemId}`);
    if (!rows.length) return;

    const expand = !rows[0].classList.contains('active');
    rows.forEach(r => r.classList.toggle('active', expand));

    const icon = $(`.system-row[data-system-id="${systemId}"] .expand-icon`);
    if (icon) {
        icon.classList.toggle('collapsed', !expand);
        icon.textContent = expand ? '▼' : '▶';
    }
}

function sortTable(colIdx) {
    const table = $('#dataTable');
    const tbody = table?.querySelector('tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('.framework-row'));
    const colName = headers[colIdx];
    const direction = sortDirection[colName] === 'asc' ? 'desc' : 'asc';
    sortDirection[colName] = direction;

    rows.sort((a, b) => {
        const aVal = getCell(a, colIdx);
        const bVal = getCell(b, colIdx);

        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        }

        return direction === 'asc' ?
            aVal.localeCompare(bVal) :
            bVal.localeCompare(aVal);
    });

    rows.forEach(row => tbody.appendChild(row));
}

function getCell(row, idx) {
    if (!row?.cells?.[idx]) return '';
    const text = row.cells[idx].textContent.trim();

    if (idx === 6) { // Progress column
        return parseFloat(text.replace('%', '')) || 0;
    }

    if (idx === 7) { // Deadline column
        if (text === 'Overdue') return -Infinity;
        const match = text.match(/(\d+)d\s*(\d+)h\s*(\d+)m/);
        if (match) {
            return parseInt(match[1]) * 1440 + parseInt(match[2]) * 60 + parseInt(match[3]);
        }
        return 0;
    }

    return text;
}

function updateCountdowns() {
    $$('.countdown').forEach(span => {
        const controlStatusId = span.dataset.controlStatusId;
        if (!controlStatusId) return;

        const url = `/compliance/deadline_countdown/${controlStatusId}/`;
        api(url)
            .then(data => {
                if (data.success !== false) {
                    span.classList.remove('warning', 'overdue');

                    if (data.is_overdue) {
                        span.textContent = 'Overdue';
                        span.classList.add('overdue');
                    } else {
                        const deadline = new Date(data.deadline);
                        const now = new Date();
                        const diffMs = deadline - now;

                        if (diffMs <= 0) {
                            span.textContent = 'Overdue';
                            span.classList.add('overdue');
                        } else {
                            const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                            const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                            const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

                            span.textContent = `${days}d ${hours}h ${minutes}m`;

                            if (diffMs <= 24 * 60 * 60 * 1000) {
                                span.classList.add('warning');
                            }
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Countdown error:', error);
                span.textContent = 'Error';
                span.classList.add('overdue');
            });
    });
}

function refreshNotifications() {
    if (!window.djangoData?.notificationsPartialUrl) return;

    api(window.djangoData.notificationsPartialUrl)
        .then(data => {
            if (data.success === false) return;

            const notificationList = $('#notificationList');
            if (!notificationList || !data.notifications) return;

            notificationList.innerHTML = '';
            data.notifications.forEach(notification => {
                const div = document.createElement('div');
                div.className = `notification ${notification.type || ''}`;
                div.innerHTML = `
                    <span>${notification.title || ''}</span>: ${notification.message || ''}
                    <small>${new Date(notification.created_at).toLocaleString()}</small>
                `;
                notificationList.appendChild(div);
            });
        })
        .catch(error => {
            console.error('Notifications error:', error);
        });
}

function filterNotifications() {
    const filter = $('#notificationFilter')?.value || 'all';
    $$('.notification').forEach(notification => {
        const show = filter === 'all' || notification.dataset.notificationType === filter;
        notification.style.display = show ? 'block' : 'none';
    });
}

function renderSummaryRows() {
    const summary = $('#summaryRow');
    if (!summary) return;

    summary.innerHTML = '';

    const systems = {};
    $$('.system-row').forEach(row => {
        const id = row.dataset.systemId;
        const name = row.querySelector('strong')?.textContent || '';
        if (id && name) {
            systems[id] = { name, frameworks: 0, compliant: 0 };
        }
    });

    $$('.framework-row').forEach(row => {
        const systemId = row.classList[1]?.split('-')[1];
        if (systems[systemId]) {
            systems[systemId].frameworks++;
            const badge = row.querySelector('.status-badge');
            if (badge?.textContent.trim() === 'Compliant') {
                systems[systemId].compliant++;
            }
        }
    });

    Object.values(systems).forEach(system => {
        const percentage = system.frameworks ?
            ((system.compliant / system.frameworks) * 100).toFixed(1) : '0';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td colspan="9">
                System: <strong>${system.name}</strong> — 
                ${system.frameworks} frameworks, ${percentage}% compliant
            </td>
        `;
        summary.appendChild(tr);
    });
}

function openAddSystemModal() {
    const modal = $('#addSystemModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function addSystem() {
    const form = $('#addSystemForm');
    if (!form) return;

    const formData = new FormData(form);

    if (window.djangoData?.addSystemUrl) {
        api(window.djangoData.addSystemUrl, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.success) {
                showNotification('System added successfully', 'success');
                $('#addSystemModal')?.classList.remove('active');
                setTimeout(() => location.reload(), 1000);
            } else {
                showNotification(response.message || 'Failed to add system', 'error');
            }
        })
        .catch(error => {
            console.error('Add system error:', error);
            showNotification('Failed to add system', 'error');
        });
    } else {
        showNotification('Add system URL not configured', 'error');
    }
}

// Export functions for global access
window.dashboardFunctions = {
    toggleFilter,
    applyFilters,
    clearFilters,
    searchTable,
    sortTable,
    openAddSystemModal,
    addSystem,
    toggleSystemExpansion,
    updateCountdowns,
    refreshNotifications
};

console.log("Dashboard.js loaded completely");