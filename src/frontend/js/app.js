/**
 * DataPulse — Enterprise Client-Side Application
 * Handles API integration, state management, scanning orchestration,
 * filtering, modals, masking previews, and evaluation benchmarks.
 */

// Application State
const state = {
  currentView: 'view-overview',
  activeScanRunId: null,
  inventoryPage: 1,
  inventoryPageSize: 15,
  currentTableForRecords: null,
  searchDebounceTimer: null
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initEventHandlers();
  loadSystemStatus();
  loadInventory();
  loadScanHistory();
  loadDiscoveredTables();
});

// Toast notification helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'success' ? 'success' : (type === 'error' ? 'error' : '')}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Navigation Initialization
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetView = item.getAttribute('data-view');
      switchView(targetView);
    });
  });
}

function switchView(viewId) {
  state.currentView = viewId;
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.content-view').forEach(el => el.classList.remove('active'));

  const navEl = document.querySelector(`.nav-item[data-view="${viewId}"]`);
  const viewEl = document.getElementById(viewId);

  if (navEl) navEl.classList.add('active');
  if (viewEl) viewEl.classList.add('active');

  // Update header title based on active view
  const titles = {
    'view-overview': { title: 'Executive Overview', sub: 'Personal data discovery posture, connection status, and key radar metrics' },
    'view-sources': { title: 'Data Sources & Architecture', sub: 'Connected database environments and dynamic schema discovery' },
    'view-scanner': { title: 'Scanner Engine', sub: 'Execute multi-rule personal data discovery and evaluate scan runs' },
    'view-inventory': { title: 'Data Inventory', sub: 'Searchable personal data inventory with declared purpose & retention' },
    'view-gaps': { title: 'Privacy Gaps & Compliance', sub: 'Flagged missing purposes, retention policies, and pending reviews' },
    'view-drift': { title: 'Drift Monitor', sub: 'Track new columns, personal data discoveries, and policy retention changes' },
    'view-evaluation': { title: 'Detection Evaluation', sub: 'Per-class precision and recall benchmarked against ground-truth labels' },
    'view-reports': { title: 'Reports & Export', sub: 'Generate CSV inventories and formatted executive PDF audit documents' }
  };

  if (titles[viewId]) {
    document.getElementById('page-title').textContent = titles[viewId].title;
    document.getElementById('page-subtitle').textContent = titles[viewId].sub;
  }

  // View-specific data fetching
  if (viewId === 'view-overview') loadSystemStatus();
  if (viewId === 'view-sources') loadDiscoveredTables();
  if (viewId === 'view-inventory') loadInventory();
  if (viewId === 'view-gaps') loadPrivacyGaps();
  if (viewId === 'view-drift') loadDriftTimeline();
  if (viewId === 'view-scanner') loadScanHistory();
}

// Event Handlers Initialization
function initEventHandlers() {
  // Quick Scan Header Button
  document.getElementById('btn-quick-scan').addEventListener('click', () => {
    switchView('view-scanner');
  });

  // Refresh Button
  document.getElementById('btn-refresh-data').addEventListener('click', () => {
    loadSystemStatus();
    loadInventory();
    showToast('Dashboard metrics refreshed.', 'success');
  });

  // Scanner Form Launch
  document.getElementById('btn-run-full-scan').addEventListener('click', executeScanner);

  // Test Connection Button
  document.getElementById('btn-test-connection').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.database_connected) {
        showToast('Connection verified: ' + data.database_message, 'success');
      } else {
        showToast('Connection failed: ' + data.database_message, 'error');
      }
    } catch (e) {
      showToast('Error testing connection: ' + e.message, 'error');
    }
  });

  // Discover Schema Button
  document.getElementById('btn-discover-schema').addEventListener('click', loadDiscoveredTables);

  // Inventory Search & Filters
  const searchInput = document.getElementById('inv-search-input');
  searchInput.addEventListener('input', () => {
    clearTimeout(state.searchDebounceTimer);
    state.searchDebounceTimer = setTimeout(() => {
      state.inventoryPage = 1;
      loadInventory();
    }, 300);
  });

  document.getElementById('inv-filter-category').addEventListener('change', () => {
    state.inventoryPage = 1;
    loadInventory();
  });

  document.getElementById('inv-filter-completeness').addEventListener('change', () => {
    state.inventoryPage = 1;
    loadInventory();
  });

  document.getElementById('inv-filter-review').addEventListener('change', () => {
    state.inventoryPage = 1;
    loadInventory();
  });

  document.getElementById('btn-reset-filters').addEventListener('click', () => {
    searchInput.value = '';
    document.getElementById('inv-filter-category').value = 'ALL';
    document.getElementById('inv-filter-completeness').value = 'ALL';
    document.getElementById('inv-filter-review').value = 'ALL';
    state.inventoryPage = 1;
    loadInventory();
  });

  // Pagination
  document.getElementById('btn-inv-prev').addEventListener('click', () => {
    if (state.inventoryPage > 1) {
      state.inventoryPage--;
      loadInventory();
    }
  });

  document.getElementById('btn-inv-next').addEventListener('click', () => {
    state.inventoryPage++;
    loadInventory();
  });

  // Export Filtered CSV button
  document.getElementById('btn-export-inventory-csv').addEventListener('click', () => {
    window.location.href = `/api/export/csv${state.activeScanRunId ? '?scan_run_id=' + state.activeScanRunId : ''}`;
  });

  // Evaluation Buttons
  document.getElementById('btn-eval-holdout').addEventListener('click', runHoldoutEvaluation);
  document.getElementById('btn-eval-dev').addEventListener('click', runDevEvaluation);

  // Drift Comparison Select
  document.getElementById('drift-scan-select').addEventListener('change', (e) => {
    loadDriftTimeline(e.target.value);
  });

  // Edit Metadata Modal Handlers
  document.getElementById('modal-meta-close').addEventListener('click', closeEditModal);
  document.getElementById('btn-cancel-edit').addEventListener('click', closeEditModal);
  document.getElementById('btn-save-edit').addEventListener('click', saveMetadataEdit);

  // Sample Records Modal Handlers
  document.getElementById('modal-sample-close').addEventListener('click', closeSampleModal);
  document.getElementById('btn-close-sample').addEventListener('click', closeSampleModal);
  document.getElementById('chk-unmask-records').addEventListener('change', (e) => {
    if (state.currentTableForRecords) {
      loadSampleRecords(state.currentTableForRecords, e.target.checked);
    }
  });
}

// 1. Load System Status and High-Level Metrics
async function loadSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const sum = data.summary;

    // Database Status in Sidebar and Overview Card
    const dbDot = document.getElementById('sidebar-db-dot');
    const dbStatusText = document.getElementById('sidebar-db-status');
    const ovConnStatus = document.getElementById('ov-conn-status');
    const ovConnDetail = document.getElementById('ov-conn-detail');
    const sourcesBadge = document.getElementById('sources-db-badge');

    if (data.database_connected) {
      dbDot.className = 'status-dot';
      dbStatusText.textContent = 'SQLite Connected';
      ovConnStatus.textContent = 'Connected';
      ovConnStatus.style.color = 'var(--success)';
      ovConnDetail.textContent = data.database_message;
      sourcesBadge.className = 'badge badge-green';
      sourcesBadge.textContent = 'READ-ONLY CONNECTED';
    } else {
      dbDot.className = 'status-dot offline';
      dbStatusText.textContent = 'DB Disconnected';
      ovConnStatus.textContent = 'Disconnected';
      ovConnStatus.style.color = 'var(--danger)';
      ovConnDetail.textContent = data.database_message;
      sourcesBadge.className = 'badge badge-red';
      sourcesBadge.textContent = 'DISCONNECTED';
    }

    document.getElementById('sources-path-display').textContent = data.database_path;

    // Numerical Metrics
    document.getElementById('ov-tables-count').textContent = sum.discovered_tables || 0;
    document.getElementById('ov-columns-count').textContent = sum.inspected_columns || 0;
    document.getElementById('ov-personal-count').textContent = sum.personal_columns || 0;
    document.getElementById('ov-missing-purpose').textContent = sum.missing_purpose || 0;
    document.getElementById('ov-missing-retention').textContent = sum.missing_retention || 0;

    // Scan Status Card
    if (sum.latest_scan) {
      state.activeScanRunId = sum.latest_scan.id;
      document.getElementById('ov-scan-target').textContent = sum.latest_scan.source_id;
      document.getElementById('ov-scan-time').textContent = sum.latest_scan.completed_at
        ? new Date(sum.latest_scan.completed_at).toLocaleString()
        : 'In Progress';
      document.getElementById('ov-scan-status-badge').textContent = sum.latest_scan.status;
      document.getElementById('ov-scan-status-badge').className =
        sum.latest_scan.status === 'COMPLETED' ? 'badge badge-green' : 'badge badge-red';

      const totalCols = sum.inspected_columns || 0;
      const piiCols = sum.personal_columns || 0;
      const pct = totalCols > 0 ? Math.round((piiCols / totalCols) * 100) : 0;

      document.getElementById('ov-coverage-ratio').textContent = `${piiCols} of ${totalCols} columns classified as personal data`;
      document.getElementById('ov-coverage-pct').textContent = `${pct}% Ratio`;
      document.getElementById('ov-coverage-bar').style.width = `${pct}%`;
    }

    // Category Distribution
    renderCategoryDistribution(sum.category_distribution || {});

  } catch (err) {
    console.error('Failed to load system status:', err);
  }
}

function renderCategoryDistribution(dist) {
  const container = document.getElementById('ov-category-breakdown');
  const entries = Object.entries(dist);

  if (entries.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No personal data columns detected yet. Run a database scan to view distribution.</div>`;
    return;
  }

  let html = '';
  const total = entries.reduce((acc, [, count]) => acc + count, 0);

  entries.forEach(([cat, count]) => {
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    const badgeColor = getCategoryBadgeClass(cat);
    html += `
      <div>
        <div style="display: flex; justify-content: space-between; font-size: 12.5px; font-weight: 600; margin-bottom: 4px;">
          <span class="badge ${badgeColor}">${cat}</span>
          <span style="color: var(--text-muted);">${count} col (${pct}%)</span>
        </div>
        <div class="progress-bar-container" style="margin: 0; height: 6px;">
          <div class="progress-bar-fill" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

// 2. Load Discovered Tables
async function loadDiscoveredTables() {
  const container = document.getElementById('sources-tables-container');
  try {
    const res = await fetch('/api/tables');
    const data = await res.json();

    if (!data.tables || data.tables.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No user tables discovered in SQLite database.</div>';
      return;
    }

    let html = '';
    data.tables.forEach(tbl => {
      const colPills = tbl.columns.map(c => `
        <span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; background: #fff; border: 1px solid var(--border); border-radius: 4px; font-size: 11px;">
          ${c.name} <span style="color: var(--text-muted); font-size: 10px;">(${c.type})</span>
          ${c.pk ? '<span style="color: var(--primary); font-weight: 700;">PK</span>' : ''}
        </span>
      `).join(' ');

      html += `
        <div style="background-color: var(--bg-app); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div>
              <span style="font-weight: 700; font-size: 14px; color: var(--navy);">${tbl.table_name}</span>
              <span class="badge badge-gray" style="margin-left: 8px;">${tbl.row_count} rows</span>
              <span class="badge badge-blue" style="margin-left: 4px;">${tbl.columns.length} columns</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="openSampleModal('${tbl.table_name}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              View Masked Records
            </button>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            ${colPills}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger); font-size: 13px;">Failed to inspect database tables: ${err.message}</div>`;
  }
}

// 3. Scanner Execution
async function executeScanner() {
  const targetSelect = document.getElementById('scan-target-select');
  const policySelect = document.getElementById('scan-policy-select');
  const targetVal = targetSelect.value;
  const policyVal = policySelect.value;

  const btnScan = document.getElementById('btn-run-full-scan');
  const statusText = document.getElementById('scan-status-text');
  const progressBox = document.getElementById('scan-progress-box');
  const progressBar = document.getElementById('scan-progress-bar');
  const progressPct = document.getElementById('scan-progress-pct');
  const progressLabel = document.getElementById('scan-progress-label');
  const logBox = document.getElementById('scan-log-box');

  btnScan.disabled = true;
  progressBox.style.display = 'block';
  logBox.innerHTML = '';

  const addLog = (msg, color = '#f8fafc') => {
    const time = new Date().toLocaleTimeString();
    logBox.innerHTML += `<div style="color: ${color};">[${time}] ${msg}</div>`;
    logBox.scrollTop = logBox.scrollHeight;
  };

  addLog(`[*] Starting DataPulse Engine for target: ${targetVal}...`, '#93c5fd');
  progressBar.style.width = '20%';
  progressPct.textContent = '20%';
  progressLabel.textContent = 'Connecting to data source & verifying read-only access...';

  try {
    let payload = {};
    if (targetVal === 'sqlite') {
      payload = { source_type: 'sqlite', policy_version: policyVal };
    } else if (targetVal === 'csv_collection_v1') {
      payload = { source_type: 'csv_collection', policy_version: 'v1' };
    } else if (targetVal === 'csv_collection_v2') {
      payload = { source_type: 'csv_collection', policy_version: 'v2' };
    }

    addLog(`[+] Requesting scan with policy: ${payload.policy_version}...`);
    progressBar.style.width = '45%';
    progressPct.textContent = '45%';
    progressLabel.textContent = 'Discovering schema and inspecting sample values...';

    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.status === 'COMPLETED') {
      progressBar.style.width = '100%';
      progressPct.textContent = '100%';
      progressLabel.textContent = 'Scan completed successfully!';

      addLog(`[✓] Discovered ${result.tables_scanned} tables & inspected ${result.columns_scanned} columns.`, '#86efac');
      addLog(`[✓] Identified ${result.personal_data_columns} personal data fields.`, '#86efac');
      addLog(`[!] Privacy Gaps: ${result.missing_purpose_count} missing purpose, ${result.missing_retention_count} missing retention.`, '#fde047');
      if (result.drift_events_count !== undefined) {
        addLog(`[⚡] Drift Detection: ${result.drift_events_count} drift events recorded.`, '#93c5fd');
      }

      showToast(`Scan complete: ${result.personal_data_columns} personal data columns found.`, 'success');
      state.activeScanRunId = result.scan_run_id;

      // Reload dependent data
      loadSystemStatus();
      loadScanHistory();
      loadInventory();
      loadPrivacyGaps();
      loadDriftTimeline();
    } else {
      progressBar.style.width = '100%';
      progressBar.style.backgroundColor = 'var(--danger)';
      progressLabel.textContent = 'Scan failed.';
      addLog(`[✗] Scan Error: ${result.error}`, '#fca5a5');
      showToast('Scan failed: ' + result.error, 'error');
    }
  } catch (err) {
    addLog(`[✗] Network/Execution Error: ${err.message}`, '#fca5a5');
    showToast('Scan failed: ' + err.message, 'error');
  } finally {
    btnScan.disabled = false;
  }
}

// 4. Load Scan History
async function loadScanHistory() {
  try {
    const res = await fetch('/api/scan/history');
    const data = await res.json();
    const tbody = document.getElementById('scan-history-tbody');

    if (!data.scans || data.scans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 24px;">No scan runs recorded yet.</td></tr>`;
      return;
    }

    let html = '';
    data.scans.forEach(s => {
      const statusBadge = s.status === 'COMPLETED' ? 'badge badge-green' : 'badge badge-red';
      const gapsTotal = (s.missing_purpose_count || 0) + (s.missing_retention_count || 0);

      html += `
        <tr>
          <td><b>#${s.id}</b></td>
          <td style="font-family: monospace; font-size: 11px;">${s.source_id}</td>
          <td><span class="${statusBadge}">${s.status}</span></td>
          <td>${new Date(s.started_at).toLocaleTimeString()}</td>
          <td>${s.completed_at ? new Date(s.completed_at).toLocaleTimeString() : '-'}</td>
          <td>${s.tables_discovered || 0}</td>
          <td>${s.columns_inspected || 0}</td>
          <td><b>${s.personal_columns_detected || 0}</b></td>
          <td>${gapsTotal > 0 ? `<span class="badge badge-amber">${gapsTotal} gaps</span>` : '<span class="badge badge-green">0</span>'}</td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  } catch (e) {
    console.error('Failed to load scan history:', e);
  }
}

// 5. Load Data Inventory
async function loadInventory() {
  const tbody = document.getElementById('inventory-tbody');
  const search = document.getElementById('inv-search-input').value;
  const category = document.getElementById('inv-filter-category').value;
  const completeness = document.getElementById('inv-filter-completeness').value;
  const review = document.getElementById('inv-filter-review').value;

  const params = new URLSearchParams({
    page: state.inventoryPage,
    page_size: state.inventoryPageSize,
    search: search || '',
    category: category,
    completeness: completeness,
    review_status: review
  });

  if (state.activeScanRunId) {
    params.set('scan_run_id', state.activeScanRunId);
  }

  try {
    const res = await fetch(`/api/inventory?${params.toString()}`);
    const data = await res.json();

    document.getElementById('inv-pagination-info').textContent =
      `Showing ${data.items.length} of ${data.total_items} items (Page ${data.page} of ${data.total_pages})`;
    document.getElementById('inv-page-display').textContent = `${data.page} / ${data.total_pages}`;

    document.getElementById('btn-inv-prev').disabled = data.page <= 1;
    document.getElementById('btn-inv-next').disabled = data.page >= data.total_pages;

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 32px;">No matching inventory findings. Try adjusting filters or run a scan.</td></tr>`;
      return;
    }

    let html = '';
    data.items.forEach(item => {
      const isPII = item.detected_category !== 'NONE';
      const catBadge = getCategoryBadgeClass(item.detected_category);
      const compBadge = getCompletenessBadgeClass(item.completeness_status);
      const confPct = Math.round(item.confidence * 100);

      html += `
        <tr>
          <td><span style="font-weight: 600;">${item.table_name}</span></td>
          <td><code style="color: var(--primary);">${item.column_name}</code></td>
          <td style="color: var(--text-muted); font-size: 11px;">${item.data_type}</td>
          <td><span class="badge ${catBadge}">${item.detected_category}</span></td>
          <td>
            <div style="font-size: 11px; font-weight: 600;">${confPct}%</div>
            <div style="font-size: 10px; color: var(--text-muted);">${item.detection_method}</div>
          </td>
          <td>${item.declared_purpose ? `<span style="font-size: 12px;">${item.declared_purpose}</span>` : '<span style="color: var(--danger); font-size: 11px; font-weight: 600;">[MISSING PURPOSE]</span>'}</td>
          <td>${item.retention_rule ? `<span style="font-size: 12px;">${item.retention_rule}</span>` : '<span style="color: var(--danger); font-size: 11px; font-weight: 600;">[MISSING POLICY]</span>'}</td>
          <td><span class="badge ${getReviewStatusBadge(item.review_status)}">${item.review_status}</span></td>
          <td><span class="badge ${compBadge}">${item.completeness_status}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-secondary btn-sm" onclick='openEditModal(${JSON.stringify(item)})' title="Edit Purpose, Retention & Status">
                Edit
              </button>
              <button class="btn btn-secondary btn-sm" onclick="openSampleModal('${item.table_name}')" title="Preview Masked Records">
                Samples
              </button>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--danger); padding: 24px;">Failed to load inventory: ${err.message}</td></tr>`;
  }
}

// 6. Load Privacy Gaps
async function loadPrivacyGaps() {
  const tbody = document.getElementById('gaps-tbody');
  const badge = document.getElementById('gaps-count-badge');
  try {
    const url = state.activeScanRunId ? `/api/gaps?scan_run_id=${state.activeScanRunId}` : '/api/gaps';
    const res = await fetch(url);
    const data = await res.json();

    badge.textContent = `${data.total_gaps} Gaps Flagged`;
    badge.className = data.total_gaps > 0 ? 'badge badge-amber' : 'badge badge-green';

    if (!data.gaps || data.gaps.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--success); padding: 32px;">All personal data columns have complete purpose & retention declarations and verified status!</td></tr>`;
      return;
    }

    let html = '';
    data.gaps.forEach(g => {
      const catBadge = getCategoryBadgeClass(g.detected_category);
      const compBadge = getCompletenessBadgeClass(g.completeness_status);

      html += `
        <tr>
          <td><b>${g.table_name}</b></td>
          <td><code>${g.column_name}</code></td>
          <td><span class="badge ${catBadge}">${g.detected_category}</span></td>
          <td><span class="badge ${compBadge}">${g.completeness_status}</span></td>
          <td>${g.declared_purpose || '<span style="color: var(--danger); font-size: 11px;">Not specified</span>'}</td>
          <td>${g.retention_rule || '<span style="color: var(--danger); font-size: 11px;">Not specified</span>'}</td>
          <td><span class="badge ${getReviewStatusBadge(g.review_status)}">${g.review_status}</span></td>
          <td>
            <button class="btn btn-primary btn-sm" onclick='openEditModal(${JSON.stringify(g)})'>
              Remediate
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger); padding: 24px;">Failed to load privacy gaps: ${err.message}</td></tr>`;
  }
}

// 7. Load Drift Timeline
async function loadDriftTimeline(selectedRunId = null) {
  const timeline = document.getElementById('drift-timeline');
  const select = document.getElementById('drift-scan-select');

  try {
    const runParam = selectedRunId ? `?current_run_id=${selectedRunId}` : '';
    const res = await fetch(`/api/drift${runParam}`);
    const data = await res.json();

    // Populate scan options dropdown if empty
    if (select.children.length === 0 && data.available_scans) {
      data.available_scans.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = `Scan #${s.id} - ${s.source_id} (${new Date(s.started_at).toLocaleTimeString()})`;
        select.appendChild(opt);
      });
      if (data.current_run_id) {
        select.value = data.current_run_id;
      }
    }

    if (!data.events || data.events.length === 0) {
      timeline.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No drift detected for this scan run compared to previous baseline.</div>`;
      return;
    }

    let html = '';
    data.events.forEach(ev => {
      let dotClass = '';
      if (ev.event_type === 'NEW_PERSONAL_DATA' || ev.event_type === 'CATEGORY_DRIFT') dotClass = 'danger';
      else if (ev.event_type === 'POLICY_RETENTION_CHANGED' || ev.event_type === 'METADATA_COMPLETENESS_DRIFT') dotClass = 'warning';
      else if (ev.event_type === 'NEW_TABLE' || ev.event_type === 'NEW_COLUMN') dotClass = 'teal';

      html += `
        <div class="timeline-item">
          <div class="timeline-dot ${dotClass}"></div>
          <div class="timeline-header">
            <span class="timeline-title">${ev.event_type.replace(/_/g, ' ')}</span>
            <span class="timeline-time">${new Date(ev.detected_at).toLocaleString()}</span>
          </div>
          <div class="timeline-desc">
            ${ev.table_name ? `<b>Target:</b> <code>${ev.table_name}${ev.column_name ? '.' + ev.column_name : ''}</code> — ` : ''}
            ${ev.details}
          </div>
        </div>
      `;
    });

    timeline.innerHTML = html;
  } catch (err) {
    timeline.innerHTML = `<div style="color: var(--danger); font-size: 13px;">Failed to load drift timeline: ${err.message}</div>`;
  }
}

// 8. Evaluation Benchmarking
async function runHoldoutEvaluation() {
  document.getElementById('eval-dataset-title').textContent = 'Holdout Test Evaluation (labels/holdout_ground_truth.csv)';
  document.getElementById('eval-metrics-tbody').innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Computing per-class precision and recall against holdout ground truth...</td></tr>`;

  try {
    const res = await fetch('/api/evaluation/holdout');
    const data = await res.json();
    renderEvaluationResults(data);
    showToast('Holdout evaluation completed.', 'success');
  } catch (err) {
    showToast('Evaluation failed: ' + err.message, 'error');
  }
}

async function runDevEvaluation() {
  document.getElementById('eval-dataset-title').textContent = 'Development Dataset Evaluation (labels/development_expected_columns.csv)';
  document.getElementById('eval-metrics-tbody').innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Computing evaluation across 84 development columns...</td></tr>`;

  try {
    const res = await fetch('/api/evaluation/development');
    const data = await res.json();
    renderEvaluationResults(data);
    showToast('Development evaluation completed.', 'success');
  } catch (err) {
    showToast('Evaluation failed: ' + err.message, 'error');
  }
}

function renderEvaluationResults(data) {
  const metricsTbody = document.getElementById('eval-metrics-tbody');
  const predsTbody = document.getElementById('eval-predictions-tbody');

  if (data.error) {
    metricsTbody.innerHTML = `<tr><td colspan="7" style="color: var(--danger);">${data.error}</td></tr>`;
    return;
  }

  // Class metrics table
  let metricsHtml = '';
  data.class_metrics.forEach(m => {
    metricsHtml += `
      <tr>
        <td><b>${m.class_name}</b></td>
        <td><span class="badge badge-green">${m.tp}</span></td>
        <td><span class="badge ${m.fp > 0 ? 'badge-red' : 'badge-gray'}">${m.fp}</span></td>
        <td><span class="badge ${m.fn > 0 ? 'badge-amber' : 'badge-gray'}">${m.fn}</span></td>
        <td><b>${(m.precision * 100).toFixed(1)}%</b></td>
        <td><b>${(m.recall * 100).toFixed(1)}%</b></td>
        <td><b>${(m.f1_score * 100).toFixed(1)}%</b></td>
      </tr>
    `;
  });
  metricsTbody.innerHTML = metricsHtml;

  // Individual predictions table
  if (data.predictions) {
    let predsHtml = '';
    data.predictions.forEach(p => {
      const matchBadge = p.is_match ? 'badge badge-green' : 'badge badge-red';
      const matchText = p.is_match ? 'MATCH' : 'MISMATCH';
      predsHtml += `
        <tr>
          <td style="font-size: 11px; font-family: monospace;">${p.source}</td>
          <td><code>${p.column}</code></td>
          <td><span class="badge ${getCategoryBadgeClass(p.true_class)}">${p.true_class}</span></td>
          <td><span class="badge ${getCategoryBadgeClass(p.predicted_class)}">${p.predicted_class}</span></td>
          <td><span class="${matchBadge}">${matchText}</span></td>
          <td>${Math.round(p.confidence * 100)}%</td>
          <td style="font-size: 11px; color: var(--text-muted);">${p.method}</td>
        </tr>
      `;
    });
    predsTbody.innerHTML = predsHtml;
  } else {
    predsTbody.innerHTML = `<tr><td colspan="7" style="color: var(--text-muted); text-align: center;">Summary: ${data.predictions_summary}</td></tr>`;
  }
}

// 9. Masked Sample Records Modal
async function openSampleModal(tableName) {
  state.currentTableForRecords = tableName;
  document.getElementById('modal-sample-title').textContent = `Sample Records: ${tableName} (Masked by Default)`;
  document.getElementById('chk-unmask-records').checked = false;
  document.getElementById('modal-sample-records').classList.add('active');
  loadSampleRecords(tableName, false);
}

async function loadSampleRecords(tableName, unmask = false) {
  const thead = document.getElementById('sample-records-thead');
  const tbody = document.getElementById('sample-records-tbody');
  thead.innerHTML = '';
  tbody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 20px;">Fetching records...</td></tr>';

  try {
    const res = await fetch(`/api/tables/${tableName}/records?unmask=${unmask}&limit=20`);
    const data = await res.json();

    if (!data.records || data.records.length === 0) {
      tbody.innerHTML = '<tr><td style="text-align: center; color: var(--text-muted); padding: 20px;">Table contains no records.</td></tr>';
      return;
    }

    const cols = Object.keys(data.records[0]);
    thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr>`;

    let rowsHtml = '';
    data.records.forEach(r => {
      rowsHtml += `<tr>${cols.map(c => `<td>${r[c] !== null ? r[c] : '<span style="color:#94a3b8">NULL</span>'}</td>`).join('')}</tr>`;
    });
    tbody.innerHTML = rowsHtml;
  } catch (err) {
    tbody.innerHTML = `<tr><td style="color: var(--danger); padding: 20px;">Failed to load records: ${err.message}</td></tr>`;
  }
}

function closeSampleModal() {
  document.getElementById('modal-sample-records').classList.remove('active');
  state.currentTableForRecords = null;
}

// 10. Edit Metadata Modal
function openEditModal(item) {
  document.getElementById('edit-item-id').value = item.id;
  document.getElementById('edit-target-label').textContent = `${item.table_name}.${item.column_name}`;
  document.getElementById('edit-category-label').textContent = item.detected_category;
  document.getElementById('edit-purpose-input').value = item.declared_purpose || '';
  document.getElementById('edit-retention-input').value = item.retention_rule || '';
  document.getElementById('edit-review-select').value = item.review_status || 'pending';
  document.getElementById('edit-notes-input').value = item.notes || '';

  document.getElementById('modal-edit-metadata').classList.add('active');
}

function closeEditModal() {
  document.getElementById('modal-edit-metadata').classList.remove('active');
}

async function saveMetadataEdit() {
  const itemId = document.getElementById('edit-item-id').value;
  const purpose = document.getElementById('edit-purpose-input').value;
  const retention = document.getElementById('edit-retention-input').value;
  const review = document.getElementById('edit-review-select').value;
  const notes = document.getElementById('edit-notes-input').value;

  try {
    const res = await fetch(`/api/inventory/${itemId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        purpose: purpose,
        retention_rule: retention,
        review_status: review,
        notes: notes
      })
    });

    const result = await res.json();
    if (result.success) {
      showToast('Metadata successfully updated and saved in local inventory.', 'success');
      closeEditModal();
      loadInventory();
      loadPrivacyGaps();
      loadSystemStatus();
    } else {
      showToast('Update failed: ' + (result.detail || 'Unknown error'), 'error');
    }
  } catch (err) {
    showToast('Failed to update metadata: ' + err.message, 'error');
  }
}

// Badge Helpers
function getCategoryBadgeClass(cat) {
  switch (cat) {
    case 'PERSON_NAME': return 'badge-blue';
    case 'EMAIL': return 'badge-teal';
    case 'PHONE': return 'badge-purple';
    case 'DATE_OF_BIRTH': return 'badge-amber';
    case 'GOVERNMENT_ID': return 'badge-red';
    default: return 'badge-gray';
  }
}

function getCompletenessBadgeClass(comp) {
  switch (comp) {
    case 'COMPLETE': return 'badge-green';
    case 'MISSING_PURPOSE': return 'badge-amber';
    case 'MISSING_RETENTION': return 'badge-amber';
    case 'MISSING_BOTH': return 'badge-red';
    default: return 'badge-gray';
  }
}

function getReviewStatusBadge(status) {
  switch (status) {
    case 'verified': return 'badge-green';
    case 'rejected': return 'badge-red';
    case 'dismissed': return 'badge-gray';
    default: return 'badge-amber';
  }
}
