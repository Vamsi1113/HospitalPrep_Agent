/**
 * Three-Phase Agent Workspace JavaScript
 * Handles form submission, dual output rendering, and UI interactions
 */

// State management
let currentResult = null;

// DOM Elements
const form = document.getElementById('agent-form');
const generateBtn = document.getElementById('generate-btn');
const btnText = document.getElementById('btn-text');
const btnSpinner = document.getElementById('btn-spinner');

const welcomeState = document.getElementById('welcome-state');
const errorState = document.getElementById('error-state');
const successState = document.getElementById('success-state');

const reasoningTrace = document.getElementById('reasoning-trace');
const historyList = document.getElementById('history-list');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadHistory();
});

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Form submission
    form.addEventListener('submit', handleFormSubmit);
    
    // Sample case buttons
    document.querySelectorAll('.btn-sample').forEach(btn => {
        btn.addEventListener('click', handleSampleCaseLoad);
    });
    
    // Copy buttons
    document.getElementById('copy-patient-btn')?.addEventListener('click', () => handleCopy('patient'));
    document.getElementById('copy-clinician-btn')?.addEventListener('click', () => handleCopy('clinician'));
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Disable button and show spinner
    setLoadingState(true);
    
    // Hide all states
    hideAllStates();
    
    // Collect form data
    const formData = new FormData(form);
    
    // Parse comma-separated lists
    const parseCsvList = (value) => {
        if (!value) return [];
        return value.split(',').map(item => item.trim()).filter(item => item);
    };
    
    const intakeData = {
        patient_name: formData.get('patient_name'),
        chief_complaint: formData.get('chief_complaint'),
        symptoms_description: formData.get('symptoms_description') || '',
        current_medications: parseCsvList(formData.get('current_medications')),
        allergies: parseCsvList(formData.get('allergies')),
        age_group: formData.get('age_group') || null,
        prior_conditions: parseCsvList(formData.get('prior_conditions')),
        pregnancy_flag: false,  // Could add checkbox if needed
        appointment_type: formData.get('appointment_type'),
        procedure: formData.get('procedure'),
        clinician_name: formData.get('clinician_name'),
        appointment_datetime: formData.get('appointment_datetime'),
        channel_preference: formData.get('channel_preference')
    };
    
    try {
        // Call THREE-PHASE agent API
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(intakeData)
        });
        
        const result = await response.json();
        
        if (result.error) {
            // Show errors
            showErrors(result.messages || ['An error occurred']);
        } else {
            // Show success with dual outputs
            showSuccess(result);
            
            // Update reasoning trace
            updateReasoningTrace(result.agent_trace || []);
            
            // Reload history
            loadHistory();
        }
    } catch (error) {
        console.error('Request failed:', error);
        showErrors(['Network error. Please check your connection and try again.']);
    } finally {
        setLoadingState(false);
    }
}

/**
 * Handle sample case loading
 */
async function handleSampleCaseLoad(e) {
    const caseId = e.target.dataset.caseId;
    
    try {
        const response = await fetch(`/load-sample-case/${caseId}`);
        const caseData = await response.json();
        
        if (caseData.error) {
            alert('Failed to load sample case');
            return;
        }
        
        // Populate form with case data
        document.getElementById('patient_name').value = caseData.name || '';
        document.getElementById('chief_complaint').value = caseData.chief_complaint || '';
        document.getElementById('symptoms_description').value = caseData.symptoms_description || '';
        document.getElementById('current_medications').value = caseData.current_medications?.join(', ') || '';
        document.getElementById('allergies').value = caseData.allergies?.join(', ') || '';
        document.getElementById('age_group').value = caseData.age_group || '';
        document.getElementById('prior_conditions').value = caseData.prior_conditions?.join(', ') || '';
        document.getElementById('appointment_type').value = caseData.appointment_type || '';
        document.getElementById('procedure').value = caseData.procedure || '';
        document.getElementById('clinician_name').value = caseData.clinician_name || '';
        document.getElementById('appointment_datetime').value = caseData.appointment_datetime || '';
        document.getElementById('channel_preference').value = caseData.channel_preference || '';
    } catch (error) {
        console.error('Failed to load sample case:', error);
        alert('Failed to load sample case');
    }
}

/**
 * Show error state
 */
function showErrors(messages) {
    hideAllStates();
    
    const errorMessages = document.getElementById('error-messages');
    errorMessages.innerHTML = '<ul>' + messages.map(msg => `<li>${escapeHtml(msg)}</li>`).join('') + '</ul>';
    
    errorState.style.display = 'block';
}

/**
 * Show success state with THREE-PHASE outputs
 */
function showSuccess(result) {
    hideAllStates();
    
    currentResult = result;
    
    // Render patient prep (left column)
    renderPatientPrep(result.patient_message);
    
    // Render clinician summary (right column)
    renderClinicianSummary(result.clinician_summary);
    
    successState.style.display = 'block';
}

/**
 * Render patient-facing preparation message
 */
function renderPatientPrep(patientMessage) {
    const container = document.getElementById('patient-prep-content');
    
    if (!patientMessage) {
        container.innerHTML = '<p class="no-content">No patient prep message available</p>';
        return;
    }
    
    // Format the message with proper line breaks and structure
    const formatted = formatText(patientMessage);
    container.innerHTML = `<div class="patient-message">${formatted}</div>`;
}

/**
 * Render clinician-facing summary
 */
function renderClinicianSummary(clinicianSummary) {
    const container = document.getElementById('clinician-summary-content');
    
    if (!clinicianSummary) {
        container.innerHTML = '<p class="no-content">No clinician summary available</p>';
        return;
    }
    
    // Format as preformatted text to preserve structure
    container.innerHTML = `<pre class="clinician-summary">${escapeHtml(clinicianSummary)}</pre>`;
}

/**
 * Update reasoning trace panel
 */
function updateReasoningTrace(steps) {
    if (!steps || steps.length === 0) {
        reasoningTrace.innerHTML = '<p class="trace-empty">No reasoning trace available</p>';
        return;
    }
    
    const stepsHtml = steps.map(step => {
        const phaseClass = step.phase ? `phase-${step.phase}` : '';
        const phaseLabel = step.phase ? `<span class="phase-badge">Phase ${step.phase}</span>` : '';
        
        return `
            <div class="trace-step ${phaseClass}">
                ${phaseLabel}
                <div class="trace-step-title">${escapeHtml(step.step || 'Unknown step')}</div>
                <div class="trace-step-desc">${escapeHtml(step.description || '')}</div>
                <div class="trace-step-time">${formatTimestamp(step.timestamp)}</div>
            </div>
        `;
    }).join('');
    
    reasoningTrace.innerHTML = stepsHtml;
}

/**
 * Load history
 */
async function loadHistory() {
    try {
        const response = await fetch('/history?limit=10');
        const result = await response.json();
        
        if (result.error || !result.history || result.history.length === 0) {
            historyList.innerHTML = '<p class="history-empty">No history yet</p>';
            return;
        }
        
        const historyHtml = result.history.map(item => `
            <div class="history-item" data-id="${item.id}">
                <div class="history-item-title">${escapeHtml(item.patient_name)} - ${escapeHtml(item.procedure)}</div>
                <div class="history-item-meta">${formatTimestamp(item.created_at)}</div>
            </div>
        `).join('');
        
        historyList.innerHTML = historyHtml;
    } catch (error) {
        console.error('Failed to load history:', error);
        historyList.innerHTML = '<p class="history-empty">Failed to load history</p>';
    }
}

/**
 * Handle copy action
 */
function handleCopy(type) {
    if (!currentResult) return;
    
    let text = '';
    
    if (type === 'patient') {
        text = stripHtml(currentResult.patient_message || '');
    } else if (type === 'clinician') {
        text = currentResult.clinician_summary || '';
    }
    
    if (!text) {
        alert('No content to copy');
        return;
    }
    
    // Copy to clipboard
    navigator.clipboard.writeText(text).then(() => {
        // Show feedback
        const btn = type === 'patient' ? 
            document.getElementById('copy-patient-btn') : 
            document.getElementById('copy-clinician-btn');
        
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.style.background = '#48bb78';
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

/**
 * Utility: Set loading state
 */
function setLoadingState(loading) {
    generateBtn.disabled = loading;
    btnText.style.display = loading ? 'none' : 'inline';
    btnSpinner.style.display = loading ? 'inline-block' : 'none';
}

/**
 * Utility: Hide all states
 */
function hideAllStates() {
    welcomeState.style.display = 'none';
    errorState.style.display = 'none';
    successState.style.display = 'none';
}

/**
 * Utility: Format text (convert newlines to <br>, preserve formatting)
 */
function formatText(text) {
    if (!text) return '';
    
    // Escape HTML first
    let formatted = escapeHtml(text);
    
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Make section headers bold (lines ending with :)
    formatted = formatted.replace(/^([A-Z][A-Z\s]+:)/gm, '<strong>$1</strong>');
    
    // Highlight warnings
    formatted = formatted.replace(/(⚠️[^<]+)/g, '<span class="warning-text">$1</span>');
    
    return formatted;
}

/**
 * Utility: Strip HTML tags
 */
function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Utility: Format timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    
    try {
        const date = new Date(timestamp);
        return date.toLocaleString();
    } catch (e) {
        return timestamp;
    }
}


// ============================================================================
// NEW FEATURES: Scheduling, Chat, Post-Procedure
// ============================================================================

/**
 * Tab Navigation
 */
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        // Remove active from all tabs
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active to clicked tab
        e.target.classList.add('active');
        const tabId = 'tab-' + e.target.dataset.tab;
        document.getElementById(tabId).classList.add('active');
    });
});

/**
 * Scheduling Feature
 */
document.getElementById('get-slots-btn')?.addEventListener('click', async () => {
    const appointmentType = document.getElementById('schedule-type').value;
    
    try {
        const response = await fetch('/api/slots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ appointment_type: appointmentType })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Failed to get slots: ' + result.messages.join(', '));
            return;
        }
        
        displaySlots(result.slots);
    } catch (error) {
        console.error('Get slots error:', error);
        alert('Failed to get available slots');
    }
});

function displaySlots(slots) {
    const container = document.getElementById('slots-container');
    const slotsList = document.getElementById('slots-list');
    
    if (!slots || slots.length === 0) {
        slotsList.innerHTML = '<p>No available slots found</p>';
        container.style.display = 'block';
        return;
    }
    
    slotsList.innerHTML = slots.map(slot => `
        <div class="slot-card">
            <div class="slot-time">${escapeHtml(slot.start_formatted)}</div>
            <div class="slot-doctor">${escapeHtml(slot.doctor)}</div>
            <div class="slot-location">${escapeHtml(slot.location)}</div>
            <button class="btn-book" data-slot='${JSON.stringify(slot)}'>Book This Slot</button>
        </div>
    `).join('');
    
    container.style.display = 'block';
    
    // Add book button listeners
    document.querySelectorAll('.btn-book').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const slot = JSON.parse(e.target.dataset.slot);
            bookSlot(slot);
        });
    });
}

async function bookSlot(slot) {
    const patientName = prompt('Enter patient name:');
    if (!patientName) return;
    
    try {
        const response = await fetch('/api/book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                slot: slot,
                patient_name: patientName,
                appointment_type: document.getElementById('schedule-type').value,
                procedure: 'General Appointment'
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Booking failed: ' + result.messages.join(', '));
            return;
        }
        
        // Show confirmation
        document.getElementById('slots-container').style.display = 'none';
        document.getElementById('booking-details').textContent = 
            `Appointment booked for ${patientName} on ${slot.start_formatted}`;
        document.getElementById('booking-confirmation').style.display = 'block';
        
        setTimeout(() => {
            document.getElementById('booking-confirmation').style.display = 'none';
        }, 5000);
    } catch (error) {
        console.error('Booking error:', error);
        alert('Failed to book appointment');
    }
}

/**
 * Chat Feature
 */
let chatSessionId = 'session_' + Date.now();

document.getElementById('chat-send-btn')?.addEventListener('click', sendChatMessage);
document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Add user message to chat
    addChatMessage('patient', question);
    input.value = '';
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                session_id: chatSessionId,
                appointment_type: 'General',
                procedure: 'General'
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            addChatMessage('agent', 'Sorry, I encountered an error. Please try again.');
            return;
        }
        
        // Add agent response
        addChatMessage('agent', result.response);
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('agent', 'Sorry, I encountered an error. Please try again.');
    }
}

function addChatMessage(role, content) {
    const messagesContainer = document.getElementById('chat-messages');
    
    // Remove welcome message if present
    const welcome = messagesContainer.querySelector('.chat-welcome');
    if (welcome) welcome.remove();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message chat-${role}`;
    messageDiv.innerHTML = `
        <div class="chat-avatar">${role === 'patient' ? '👤' : '🤖'}</div>
        <div class="chat-bubble">${escapeHtml(content)}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Post-Procedure Recovery Feature
 */
document.getElementById('get-recovery-btn')?.addEventListener('click', async () => {
    const procedure = document.getElementById('recovery-procedure').value;
    
    try {
        const response = await fetch('/api/post-procedure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                procedure: procedure,
                patient_name: 'Patient'
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Failed to get recovery plan: ' + result.messages.join(', '));
            return;
        }
        
        displayRecoveryPlan(result.recovery_plan);
    } catch (error) {
        console.error('Recovery plan error:', error);
        alert('Failed to get recovery plan');
    }
});

function displayRecoveryPlan(plan) {
    const container = document.getElementById('recovery-plan');
    
    container.innerHTML = `
        <div class="recovery-content">
            <h3>Recovery Instructions</h3>
            <pre>${escapeHtml(plan.instructions)}</pre>
            
            ${plan.activity_restrictions && plan.activity_restrictions.length > 0 ? `
                <h4>Activity Restrictions</h4>
                <ul>
                    ${plan.activity_restrictions.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
            ` : ''}
            
            ${plan.warning_signs && plan.warning_signs.length > 0 ? `
                <h4 class="warning-header">⚠️ Warning Signs - Call Doctor If:</h4>
                <ul class="warning-list">
                    ${plan.warning_signs.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                </ul>
            ` : ''}
        </div>
    `;
    
    container.style.display = 'block';
}
