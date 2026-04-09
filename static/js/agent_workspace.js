/**
 * PrepCare Agent Workspace — JavaScript
 * Carfract CRM dark UI | LangGraph multi-phase agent interface
 */

'use strict';

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
let currentResult    = null;
let currentOutPane   = 'patient';
let chatSessionId    = 'session_' + Date.now();

// DOM shortcuts
const $ = id => document.getElementById(id);

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initNav();
    initForm();
    initOutputTabs();
    initSchedule();
    initChat();
    initRecovery();
    initHistoryView();
    loadHistory();           // sidebar mini history
    loadFullHistory();       // history view table
    setMinDateTime();
});

// ═══════════════════════════════════════════
// SIDEBAR NAVIGATION
// ═══════════════════════════════════════════
const VIEW_META = {
    intake:   { title: 'Patient Intake',          sub: 'Appointment Preparation' },
    schedule: { title: 'Appointment Scheduling',  sub: 'Slot Management' },
    chat:     { title: 'Patient Q&A',             sub: 'AI-Powered Chat' },
    recovery: { title: 'Post-Procedure Recovery', sub: 'Recovery Planning' },
    history:  { title: 'Case History',            sub: 'Audit Log' },
};

function initNav() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

function switchView(view) {
    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const navBtn = document.querySelector(`.nav-item[data-view="${view}"]`);
    if (navBtn) navBtn.classList.add('active');

    // Update views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const viewEl = $(`view-${view}`);
    if (viewEl) viewEl.classList.add('active');

    // Update topbar
    const meta = VIEW_META[view] || {};
    const topTitle = $('topbar-title');
    const topSub   = $('topbar-breadcrumb-sub');
    if (topTitle) topTitle.textContent = meta.title || view;
    if (topSub)   topSub.textContent   = meta.sub   || '';

    // Refresh on history view
    if (view === 'history') loadFullHistory();
}

// ═══════════════════════════════════════════
// FORM & AGENT EXECUTION
// ═══════════════════════════════════════════
function initForm() {
    const form = $('agent-form');
    if (!form) return;

    form.addEventListener('submit', handleFormSubmit);

    // Sample cases
    document.querySelectorAll('.case-chip').forEach(btn => {
        btn.addEventListener('click', () => loadSampleCase(btn.dataset.caseId));
    });

    // Copy & print
    $('copy-current-btn')?.addEventListener('click', handleCopy);
    $('print-btn')?.addEventListener('click', handlePrint);

    // Clear form
    $('clear-form-btn')?.addEventListener('click', () => {
        form.reset();
        showWelcome();
    });
}

async function handleFormSubmit(e) {
    e.preventDefault();
    setGenerating(true);
    showLoading();
    resetPipelineNodes();
    setBadge('trace-live-badge', 'RUNNING', 'running');

    const formData = new FormData(e.target);
    const csvList  = v => v ? v.split(',').map(s => s.trim()).filter(Boolean) : [];

    const payload = {
        patient_name:           formData.get('patient_name'),
        chief_complaint:        formData.get('chief_complaint'),
        symptoms_description:   formData.get('symptoms_description') || '',
        current_medications:    csvList(formData.get('current_medications')),
        allergies:              csvList(formData.get('allergies')),
        age_group:              formData.get('age_group') || null,
        prior_conditions:       csvList(formData.get('prior_conditions')),
        pregnancy_flag:         false,
        appointment_type:       formData.get('appointment_type'),
        procedure:              formData.get('procedure'),
        clinician_name:         formData.get('clinician_name'),
        appointment_datetime:   formData.get('appointment_datetime'),
        channel_preference:     formData.get('channel_preference'),
    };

    // Animate loading nodes
    const nodeKeys  = ['lnode-1','lnode-2','lnode-3','lnode-4','lnode-5'];
    const pipeNodes = ['pnode-validate','pnode-rules','pnode-plan','pnode-enhance','pnode-save'];
    animateLoadingNodes(nodeKeys, pipeNodes);

    try {
        const res    = await fetch('/generate', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        const result = await res.json();

        if (result.error) {
            showErrors(result.messages || ['An error occurred.']);
            setBadge('trace-live-badge', 'ERROR', '');
        } else {
            currentResult = result;
            showSuccess(result);
            insertTraceSteps(result.agent_trace || []);
            completeAllPipelineNodes(pipeNodes);
            setBadge('trace-live-badge', 'DONE', 'done');
            loadHistory();
            loadFullHistory();
        }
    } catch (err) {
        console.error(err);
        showErrors(['Network error — please check your connection.']);
        setBadge('trace-live-badge', 'ERROR', '');
    } finally {
        setGenerating(false);
        clearNodeAnimation();
    }
}

// ═══════════════════════════════════════════
// SAMPLE CASE LOADER
// ═══════════════════════════════════════════
async function loadSampleCase(caseId) {
    try {
        const res  = await fetch(`/load-sample-case/${caseId}`);
        const data = await res.json();
        if (data.error) { alert('Failed to load sample case'); return; }

        const set = (id, val) => { const el = $(id); if (el) el.value = val || ''; };

        set('patient_name',           data.name);
        set('chief_complaint',        data.chief_complaint);
        set('symptoms_description',   data.symptoms_description);
        set('current_medications',    (data.current_medications || []).join(', '));
        set('allergies',              (data.allergies || []).join(', '));
        set('age_group',              data.age_group);
        set('prior_conditions',       (data.prior_conditions || []).join(', '));
        set('appointment_type',       data.appointment_type);
        set('procedure',              data.procedure);
        set('clinician_name',         data.clinician_name);
        set('appointment_datetime',   data.appointment_datetime);
        set('channel_preference',     data.channel_preference);
    } catch (err) {
        console.error(err);
        alert('Failed to load sample case');
    }
}

// ═══════════════════════════════════════════
// UI STATE TRANSITIONS
// ═══════════════════════════════════════════
function showWelcome() {
    hideAllOutputStates();
    const ws = $('welcome-state');
    if (ws) ws.style.display = '';
}

function showLoading() {
    hideAllOutputStates();
    const ls = $('loading-state');
    if (ls) ls.style.display = '';
}

function showErrors(messages) {
    hideAllOutputStates();
    const es = $('error-state');
    if (!es) return;
    const el = $('error-messages');
    if (el) {
        el.innerHTML = '<ul>' + messages.map(m => `<li>${escHtml(m)}</li>`).join('') + '</ul>';
    }
    es.style.display = '';
}

function showSuccess(result) {
    hideAllOutputStates();
    const ss = $('success-state');
    if (!ss) return;

    renderPatientPrep(result.patient_message);
    renderClinicianSummary(result.clinician_summary);

    ss.style.display = '';
    // Show patient pane by default
    switchOutPane('patient');
}

function hideAllOutputStates() {
    ['welcome-state','loading-state','error-state','success-state'].forEach(id => {
        const el = $(id);
        if (el) el.style.display = 'none';
    });
}

// ═══════════════════════════════════════════
// OUTPUT RENDERING
// ═══════════════════════════════════════════
function renderPatientPrep(msg) {
    const container = $('patient-prep-content');
    if (!container) return;

    if (!msg) {
        container.innerHTML = '<p class="trace-empty">No patient prep message available.</p>';
        return;
    }

    // Parse message into sections
    const sections = parseMessageSections(msg);
    container.innerHTML = sections.map(renderSection).join('');
}

function parseMessageSections(text) {
    const lines    = text.split('\n');
    const sections = [];
    let current    = null;

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) { if (current) current.body += '\n'; continue; }

        // Detect section headers (ALL CAPS followed by colon, or emoji lines)
        const isHeader = /^[A-Z][A-Z\s&-]{3,}:/.test(trimmed) || /^[📋🍽️💊🎒🕐🚗⚠️🌟✅🏥]+/.test(trimmed);

        if (isHeader) {
            if (current) sections.push(current);
            current = { title: trimmed, body: '', type: detectSectionType(trimmed) };
        } else if (current) {
            current.body += (current.body ? '\n' : '') + trimmed;
        } else {
            current = { title: '', body: trimmed, type: 'default' };
        }
    }
    if (current) sections.push(current);
    return sections.filter(s => s.body || s.title);
}

function detectSectionType(title) {
    const t = title.toUpperCase();
    if (/WARNING|URGENT|IMPORTANT|⚠️/.test(t))      return 'warning';
    if (/SUMMARY|APPOINTMENT/.test(t))               return 'info';
    if (/CLOSING|CONTACT|NOTE|✅/.test(t))           return 'success';
    return 'default';
}

function renderSection(sec) {
    const cls = sec.type !== 'default' ? ` msg-section--${sec.type}` : '';
    const bodyHtml = formatBodyText(sec.body);
    return `
    <div class="msg-section${cls}">
        ${sec.title ? `<div class="msg-section-title">${escHtml(sec.title)}</div>` : ''}
        <div class="msg-section-body">${bodyHtml}</div>
    </div>`;
}

function formatBodyText(text) {
    if (!text) return '';
    return text.split('\n').map(line => {
        const t = line.trim();
        if (!t) return '';
        if (t.startsWith('•') || t.startsWith('-') || t.startsWith('*')) {
            return `<div style="padding-left:12px; position:relative; margin:2px 0;">
                <span style="position:absolute;left:0;color:var(--accent)">•</span>
                ${escHtml(t.replace(/^[•\-\*]\s*/, ''))}
            </div>`;
        }
        if (/⚠️/.test(t)) {
            return `<div class="warning-line">${escHtml(t)}</div>`;
        }
        return `<div style="margin:2px 0;">${escHtml(t)}</div>`;
    }).join('');
}

function renderClinicianSummary(summary) {
    const container = $('clinician-summary-content');
    if (!container) return;
    if (!summary) {
        container.innerHTML = '<p class="trace-empty">No clinician summary available.</p>';
        return;
    }
    container.innerHTML = `<pre style="white-space:pre-wrap;font-size:11.5px;line-height:1.65;color:var(--text-muted);">${escHtml(summary)}</pre>`;
}

// ═══════════════════════════════════════════
// OUTPUT TABS
// ═══════════════════════════════════════════
function initOutputTabs() {
    document.querySelectorAll('.out-tab[data-out]').forEach(btn => {
        btn.addEventListener('click', () => switchOutPane(btn.dataset.out));
    });
}

function switchOutPane(pane) {
    currentOutPane = pane;
    document.querySelectorAll('.out-tab[data-out]').forEach(b => {
        b.classList.toggle('active', b.dataset.out === pane);
    });
    document.querySelectorAll('.out-pane').forEach(p => {
        p.classList.toggle('active', p.id === `pane-${pane}`);
    });
}

// ═══════════════════════════════════════════
// COPY & PRINT
// ═══════════════════════════════════════════
function handleCopy() {
    if (!currentResult) return;
    const text = currentOutPane === 'patient'
        ? (currentResult.patient_message || '')
        : (currentResult.clinician_summary || '');

    if (!text) { alert('Nothing to copy.'); return; }

    navigator.clipboard.writeText(text).then(() => {
        const btn = $('copy-current-btn');
        if (!btn) return;
        const orig = btn.innerHTML;
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }).catch(() => alert('Failed to copy'));
}

function handlePrint() {
    if (!currentResult) return;
    const text = currentOutPane === 'patient'
        ? (currentResult.patient_message || '')
        : (currentResult.clinician_summary || '');
    const win = window.open('', '_blank');
    win.document.write(`<pre style="font-family:system-ui;white-space:pre-wrap;padding:24px;">${text}</pre>`);
    win.document.close();
    win.print();
}

// ═══════════════════════════════════════════
// PIPELINE NODE ANIMATION
// ═══════════════════════════════════════════
const NODE_TO_STEP = {
    'pnode-validate': 'validate_input',
    'pnode-rules':    'apply_rules',
    'pnode-plan':     'build_prep_plan',
    'pnode-enhance':  'enhance_message',
    'pnode-save':     'save_output',
};

let nodeAnimInterval = null;

function animateLoadingNodes(loadingNodeIds, pipelineNodeIds) {
    let i = 0;
    loadingNodeIds.forEach(id => {
        const el = $(id);
        if (el) el.className = 'lnode';
    });
    pipelineNodeIds.forEach(id => setNodeStatus(id, 'idle'));

    nodeAnimInterval = setInterval(() => {
        if (i > 0) {
            const el = $(loadingNodeIds[i - 1]);
            if (el) el.className = 'lnode done';
            setNodeStatus(pipelineNodeIds[i - 1], 'done');
        }
        if (i < loadingNodeIds.length) {
            const el = $(loadingNodeIds[i]);
            if (el) el.className = 'lnode active';
            setNodeStatus(pipelineNodeIds[i], 'active');
            i++;
        } else {
            clearNodeAnimation();
        }
    }, 700);
}

function clearNodeAnimation() {
    if (nodeAnimInterval) {
        clearInterval(nodeAnimInterval);
        nodeAnimInterval = null;
    }
}

function resetPipelineNodes() {
    Object.keys(NODE_TO_STEP).forEach(id => setNodeStatus(id, 'idle'));
    ['pnode-validate','pnode-rules','pnode-plan','pnode-enhance','pnode-save'].forEach(id => {
        const node = $(id);
        if (node) {
            node.querySelector('.pnode-meta').textContent = META_DEFAULT[id] || '';
        }
    });
}

const META_DEFAULT = {
    'pnode-validate': 'Awaiting input',
    'pnode-rules':    'Deterministic engine',
    'pnode-plan':     'Structured sections',
    'pnode-enhance':  'LLM tone rewrite',
    'pnode-save':     'SQLite persistence',
};

function setNodeStatus(nodeId, status) {
    const el = $(nodeId);
    if (el) el.dataset.status = status;
}

function completeAllPipelineNodes(pipelineNodeIds) {
    pipelineNodeIds.forEach(id => setNodeStatus(id, 'done'));
    ['lnode-1','lnode-2','lnode-3','lnode-4','lnode-5'].forEach(id => {
        const el = $(id);
        if (el) el.className = 'lnode done';
    });
}

// ═══════════════════════════════════════════
// REASONING TRACE
// ═══════════════════════════════════════════
function insertTraceSteps(steps) {
    const container = $('reasoning-trace');
    if (!container) return;

    if (!steps || steps.length === 0) {
        container.innerHTML = '<p class="trace-empty">No trace data returned.</p>';
        return;
    }

    container.innerHTML = steps.map((step, idx) => {
        const phaseNum = step.phase || Math.min(Math.floor(idx / 2) + 1, 3);
        const cls      = `trace-step trace-step--phase${phaseNum}`;
        const metaTags = buildMetaTags(step);

        return `
        <div class="${cls}">
            <div class="trace-step-name">${escHtml(step.step || 'step')}</div>
            <div class="trace-step-desc">${escHtml(step.description || '')}</div>
            ${metaTags ? `<div class="trace-step-meta">${metaTags}</div>` : ''}
            <div class="trace-step-time">${formatTs(step.timestamp)}</div>
        </div>`;
    }).join('');
}

function buildMetaTags(step) {
    const skip = new Set(['step','description','timestamp','phase']);
    return Object.entries(step)
        .filter(([k]) => !skip.has(k))
        .slice(0, 5)
        .map(([k, v]) => `<span class="trace-meta-tag">${escHtml(k)}: ${escHtml(String(v))}</span>`)
        .join('');
}

// ═══════════════════════════════════════════
// HISTORY (SIDEBAR MINI)
// ═══════════════════════════════════════════
async function loadHistory() {
    const container = $('history-list');
    if (!container) return;

    try {
        const res    = await fetch('/history?limit=8');
        const result = await res.json();

        if (result.error || !result.history || result.history.length === 0) {
            container.innerHTML = '<p class="trace-empty">No cases yet</p>';
            return;
        }

        container.innerHTML = result.history.map(item => {
            const initials = getInitials(item.patient_name);
            return `
            <div class="history-row" title="${escHtml(item.patient_name)} — ${escHtml(item.procedure)}">
                <div class="history-row-avatar">${initials}</div>
                <div class="history-row-info">
                    <div class="history-row-name">${escHtml(item.patient_name)}</div>
                    <div class="history-row-meta">${escHtml(item.procedure || '')} · ${formatTs(item.created_at)}</div>
                </div>
            </div>`;
        }).join('');
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p class="trace-empty">Failed to load</p>';
    }
}

// ═══════════════════════════════════════════
// HISTORY VIEW (full table)
// ═══════════════════════════════════════════
function initHistoryView() {
    $('refresh-history-btn')?.addEventListener('click', loadFullHistory);
}

async function loadFullHistory() {
    const container = $('history-full-list');
    const countEl   = $('history-count');
    if (!container) return;

    try {
        const res    = await fetch('/history?limit=50');
        const result = await res.json();

        if (result.error || !result.history || result.history.length === 0) {
            container.innerHTML = '<p class="trace-empty" style="padding:20px;">No history yet.</p>';
            if (countEl) countEl.textContent = '0 records';
            return;
        }

        const items = result.history;
        if (countEl) countEl.textContent = `${items.length} record${items.length !== 1 ? 's' : ''}`;

        container.innerHTML = items.map(item => {
            const typeClass = getTypeBadgeClass(item.appointment_type);
            return `
            <div class="history-table-row">
                <span>${escHtml(item.patient_name || '—')}</span>
                <span>${escHtml(item.procedure || '—')}</span>
                <span><span class="history-badge ${typeClass}">${escHtml(item.appointment_type || '—')}</span></span>
                <span>${formatTs(item.created_at)}</span>
            </div>`;
        }).join('');
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p class="trace-empty" style="padding:20px;">Failed to load history.</p>';
    }
}

function getTypeBadgeClass(type) {
    const map = {
        'Surgery':     'history-badge--surgery',
        'Imaging':     'history-badge--imaging',
        'Lab Work':    'history-badge--lab',
        'Consultation':'history-badge--consult',
        'Procedure':   'history-badge--procedure',
    };
    return map[type] || 'history-badge--default';
}

// ═══════════════════════════════════════════
// SCHEDULING FEATURE
// ═══════════════════════════════════════════
function initSchedule() {
    $('get-slots-btn')?.addEventListener('click', fetchSlots);
}

async function fetchSlots() {
    const type      = $('schedule-type')?.value;
    const container = $('slots-container');
    if (!container) return;

    container.innerHTML = '<p class="trace-empty" style="padding:12px;">Searching for slots...</p>';

    try {
        const res    = await fetch('/api/slots', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ appointment_type: type }),
        });
        const result = await res.json();

        if (result.error) {
            container.innerHTML = `<p class="trace-empty" style="color:var(--danger);padding:12px;">Error: ${escHtml((result.messages || []).join(', '))}</p>`;
            return;
        }

        renderSlots(result.slots || []);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p class="trace-empty" style="color:var(--danger);padding:12px;">Failed to fetch slots.</p>';
    }
}

function renderSlots(slots) {
    const container = $('slots-container');
    if (!container) return;

    if (!slots.length) {
        container.innerHTML = '<p class="trace-empty" style="padding:12px;">No available slots found.</p>';
        return;
    }

    container.innerHTML = slots.map(slot => `
    <div class="slot-card">
        <div>
            <div class="slot-time">${escHtml(slot.start_formatted)}</div>
            <div class="slot-doctor">${escHtml(slot.doctor)}</div>
        </div>
        <div class="slot-location">${escHtml(slot.location)}</div>
        <button class="btn-book" data-slot='${JSON.stringify(slot).replace(/'/g, '&apos;')}'>Book</button>
    </div>`).join('');

    container.querySelectorAll('.btn-book').forEach(btn => {
        btn.addEventListener('click', () => {
            try { bookSlot(JSON.parse(btn.dataset.slot)); }
            catch(e) { console.error(e); }
        });
    });
}

async function bookSlot(slot) {
    const patientName = prompt('Enter patient name:');
    if (!patientName) return;

    try {
        const res    = await fetch('/api/book', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                slot,
                patient_name:     patientName,
                appointment_type: $('schedule-type')?.value || 'Consultation',
                procedure:        'General Appointment',
            }),
        });
        const result = await res.json();

        if (result.error) { alert('Booking failed: ' + (result.messages || []).join(', ')); return; }

        $('slots-container').style.display = 'none';
        const conf = $('booking-confirmation');
        if (conf) {
            $('booking-details').textContent = `Booked for ${patientName} on ${slot.start_formatted}`;
            conf.style.display = 'flex';
            setTimeout(() => { conf.style.display = 'none'; $('slots-container').style.display = ''; }, 6000);
        }
    } catch (err) {
        console.error(err);
        alert('Failed to book appointment.');
    }
}

// ═══════════════════════════════════════════
// CHAT FEATURE
// ═══════════════════════════════════════════
function initChat() {
    $('chat-send-btn')?.addEventListener('click', sendChatMessage);
    $('chat-input')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
}

async function sendChatMessage() {
    const input    = $('chat-input');
    if (!input) return;
    const question = input.value.trim();
    if (!question) return;

    addChatBubble('patient', question);
    input.value = '';

    // Typing indicator
    const typingId = addTypingIndicator();

    try {
        const res    = await fetch('/api/chat', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                question,
                session_id:       chatSessionId,
                appointment_type: 'General',
                procedure:        'General',
            }),
        });
        const result = await res.json();
        removeTypingIndicator(typingId);

        addChatBubble('agent', result.error ? 'Sorry, I encountered an error. Please try again.' : result.response);
    } catch (err) {
        console.error(err);
        removeTypingIndicator(typingId);
        addChatBubble('agent', 'Sorry, I encountered a network error. Please try again.');
    }
}

function addChatBubble(role, content) {
    const container = $('chat-messages');
    if (!container) return;

    const div = document.createElement('div');
    div.className = `chat-message chat-${role}`;

    const avatarHtml = role === 'agent'
        ? `<div class="msg-avatar msg-avatar--agent"><svg width="12" height="12" viewBox="0 0 24 24" fill="#7c6af7"><path d="M12 2L2 7L12 12L22 7L12 2Z"/></svg></div>`
        : `<div class="msg-avatar msg-avatar--patient">👤</div>`;

    div.innerHTML = `
        ${avatarHtml}
        <div class="msg-bubble msg-bubble--${role}">${escHtml(content)}</div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
    const container = $('chat-messages');
    if (!container) return null;
    const id  = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id        = id;
    div.className = 'chat-message chat-agent';
    div.innerHTML = `
        <div class="msg-avatar msg-avatar--agent"><svg width="12" height="12" viewBox="0 0 24 24" fill="#7c6af7"><path d="M12 2L2 7L12 12L22 7L12 2Z"/></svg></div>
        <div class="msg-bubble msg-bubble--agent" style="color:var(--text-disabled);">Thinking<span style="animation:fade-in-out 1.2s infinite">...</span></div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    if (!id) return;
    const el = $(id);
    if (el) el.remove();
}

// ═══════════════════════════════════════════
// RECOVERY FEATURE
// ═══════════════════════════════════════════
function initRecovery() {
    $('get-recovery-btn')?.addEventListener('click', fetchRecoveryPlan);
}

async function fetchRecoveryPlan() {
    const procedure = $('recovery-procedure')?.value;
    const container = $('recovery-plan');
    if (!container) return;

    container.innerHTML = '<p class="trace-empty">Generating recovery plan...</p>';

    try {
        const res    = await fetch('/api/post-procedure', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ procedure, patient_name: 'Patient' }),
        });
        const result = await res.json();

        if (result.error) {
            container.innerHTML = `<p class="trace-empty" style="color:var(--danger);">Error: ${escHtml((result.messages || []).join(', '))}</p>`;
            return;
        }

        renderRecoveryPlan(result.recovery_plan);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p class="trace-empty" style="color:var(--danger);">Failed to generate recovery plan.</p>';
    }
}

function renderRecoveryPlan(plan) {
    const container = $('recovery-plan');
    if (!container || !plan) return;

    const restrictionsHtml = (plan.activity_restrictions?.length)
        ? `<h4>Activity Restrictions</h4><ul>${plan.activity_restrictions.map(r => `<li>${escHtml(r)}</li>`).join('')}</ul>`
        : '';

    const warningsHtml = (plan.warning_signs?.length)
        ? `<h4 class="warning-header">⚠️ Warning Signs — Call Doctor If:</h4>
           <ul class="warning-list">${plan.warning_signs.map(s => `<li>${escHtml(s)}</li>`).join('')}</ul>`
        : '';

    container.innerHTML = `
    <div class="recovery-content">
        <h3>Recovery Instructions</h3>
        <pre>${escHtml(plan.instructions || '')}</pre>
        ${restrictionsHtml}
        ${warningsHtml}
    </div>`;
}

// ═══════════════════════════════════════════
// BUTTON & BADGE HELPERS
// ═══════════════════════════════════════════
function setGenerating(loading) {
    const btn    = $('generate-btn');
    const text   = $('btn-text');
    const spin   = $('btn-spinner');
    if (!btn) return;
    btn.disabled          = loading;
    if (text) text.style.display  = loading ? 'none' : '';
    if (spin) spin.style.display  = loading ? 'inline-block' : 'none';
}

function setBadge(id, label, cls) {
    const el = $(id);
    if (!el) return;
    el.textContent = label;
    el.className   = 'live-badge' + (cls ? ` ${cls}` : '');
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function escHtml(text) {
    if (text == null) return '';
    const d = document.createElement('div');
    d.textContent = String(text);
    return d.innerHTML;
}

function formatTs(ts) {
    if (!ts) return '';
    try {
        return new Date(ts).toLocaleString(undefined, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    } catch { return String(ts); }
}

function getInitials(name) {
    if (!name) return '?';
    return name.trim().split(/\s+/).slice(0,2).map(w => w[0]).join('').toUpperCase();
}

function setMinDateTime() {
    const dt = $('appointment_datetime');
    if (!dt) return;
    const now = new Date();
    now.setMinutes(now.getMinutes() + 30);
    dt.min = now.toISOString().slice(0,16);
}
