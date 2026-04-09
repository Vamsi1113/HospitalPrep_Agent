/**
 * Agent Workspace JavaScript
 * Handles form submission, response rendering, and UI interactions
 */

// State management
let currentPrepPlan = null;

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
    
    // Sample buttons
    document.querySelectorAll('.btn-sample').forEach(btn => {
        btn.addEventListener('click', handleSampleLoad);
    });
    
    // Action buttons
    document.getElementById('copy-btn')?.addEventListener('click', handleCopy);
    document.getElementById('print-btn')?.addEventListener('click', handlePrint);
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
    const appointmentData = {
        patient_name: formData.get('patient_name'),
        appointment_type: formData.get('appointment_type'),
        procedure: formData.get('procedure'),
        clinician_name: formData.get('clinician_name'),
        appointment_datetime: formData.get('appointment_datetime'),
        channel_preference: formData.get('channel_preference'),
        special_notes: formData.get('special_notes') || ''
    };
    
    try {
        // Call agent API
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(appointmentData)
        });
        
        const result = await response.json();
        
        if (result.error) {
            // Show errors
            showErrors(result.messages || ['An error occurred']);
        } else {
            // Show success
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
 * Handle sample data loading
 */
async function handleSampleLoad(e) {
    const sampleId = e.target.dataset.sampleId;
    
    try {
        const response = await fetch(`/load-sample/${sampleId}`);
        const sampleData = await response.json();
        
        if (sampleData.error) {
            alert('Failed to load sample data');
            return;
        }
        
        // Populate form
        document.getElementById('patient_name').value = sampleData.patient_name || '';
        document.getElementById('appointment_type').value = sampleData.appointment_type || '';
        document.getElementById('procedure').value = sampleData.procedure || '';
        document.getElementById('clinician_name').value = sampleData.clinician_name || '';
        document.getElementById('appointment_datetime').value = sampleData.appointment_datetime || '';
        document.getElementById('channel_preference').value = sampleData.channel_preference || '';
        document.getElementById('special_notes').value = sampleData.special_notes || '';
    } catch (error) {
        console.error('Failed to load sample:', error);
        alert('Failed to load sample data');
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
 * Show success state with prep plan
 */
function showSuccess(result) {
    hideAllStates();
    
    currentPrepPlan = result;
    
    // For now, render the full_message as a single block
    // TODO: Render structured sections when prep_plan_builder is implemented
    if (result.prep_sections) {
        renderStructuredSections(result.prep_sections);
    } else {
        // Fallback: render full_message
        renderFallbackMessage(result.full_message);
    }
    
    successState.style.display = 'block';
}

/**
 * Render structured prep sections
 */
function renderStructuredSections(sections) {
    // Appointment Summary
    document.getElementById('appointment-summary').innerHTML = formatText(sections.appointment_summary);
    
    // Fasting Plan
    if (sections.fasting_plan) {
        document.getElementById('fasting-plan').innerHTML = formatText(sections.fasting_plan);
        document.getElementById('fasting-section').style.display = 'block';
    } else {
        document.getElementById('fasting-section').style.display = 'none';
    }
    
    // Diet Guidance
    if (sections.diet_guidance) {
        document.getElementById('diet-guidance').innerHTML = formatText(sections.diet_guidance);
        document.getElementById('diet-section').style.display = 'block';
    } else {
        document.getElementById('diet-section').style.display = 'none';
    }
    
    // Medication Instructions
    document.getElementById('medication-instructions').innerHTML = formatText(sections.medication_instructions);
    
    // Items to Bring
    const itemsList = sections.items_to_bring.map(item => `<li>${escapeHtml(item)}</li>`).join('');
    document.getElementById('items-to-bring').innerHTML = `<ul>${itemsList}</ul>`;
    
    // Arrival Instructions
    document.getElementById('arrival-instructions').innerHTML = formatText(sections.arrival_instructions);
    
    // Transport Instructions
    if (sections.transport_instructions) {
        document.getElementById('transport-instructions').innerHTML = formatText(sections.transport_instructions);
        document.getElementById('transport-section').style.display = 'block';
    } else {
        document.getElementById('transport-section').style.display = 'none';
    }
    
    // Red Flag Warnings
    const warningsList = sections.red_flag_warnings.map(warning => `<li>${escapeHtml(warning)}</li>`).join('');
    document.getElementById('red-flag-warnings').innerHTML = `<ul>${warningsList}</ul>`;
    
    // Closing Note
    document.getElementById('closing-note').innerHTML = formatText(sections.closing_note);
}

/**
 * Render fallback message (when structured sections not available)
 */
function renderFallbackMessage(message) {
    // Parse the message and try to extract sections
    // For now, just show in appointment summary
    document.getElementById('appointment-summary').innerHTML = formatText(message);
    
    // Hide optional sections
    document.getElementById('fasting-section').style.display = 'none';
    document.getElementById('diet-section').style.display = 'none';
    document.getElementById('transport-section').style.display = 'none';
    
    // Show generic content in other sections
    document.getElementById('medication-instructions').innerHTML = '<p>Follow your regular medication schedule unless instructed otherwise by your clinician.</p>';
    document.getElementById('items-to-bring').innerHTML = '<ul><li>Photo ID</li><li>Insurance Card</li><li>List of current medications</li></ul>';
    document.getElementById('arrival-instructions').innerHTML = '<p>Please arrive 15 minutes before your scheduled appointment time.</p>';
    document.getElementById('red-flag-warnings').innerHTML = '<ul><li>Severe pain or discomfort</li><li>High fever (>101°F)</li><li>Difficulty breathing</li><li>Unusual symptoms</li></ul>';
    document.getElementById('closing-note').innerHTML = '<p>If you have any questions or concerns, please contact the clinic. We look forward to seeing you!</p>';
}

/**
 * Update reasoning trace panel
 */
function updateReasoningTrace(steps) {
    if (!steps || steps.length === 0) {
        reasoningTrace.innerHTML = '<p class="trace-empty">No reasoning trace available</p>';
        return;
    }
    
    const stepsHtml = steps.map(step => `
        <div class="trace-step">
            <div class="trace-step-title">${escapeHtml(step.step || 'Unknown step')}</div>
            <div class="trace-step-desc">${escapeHtml(step.description || '')}</div>
            <div class="trace-step-time">${formatTimestamp(step.timestamp)}</div>
        </div>
    `).join('');
    
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
function handleCopy() {
    if (!currentPrepPlan) return;
    
    // Create text version of prep plan
    const text = createTextVersion(currentPrepPlan);
    
    // Copy to clipboard
    navigator.clipboard.writeText(text).then(() => {
        alert('Prep plan copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy to clipboard');
    });
}

/**
 * Handle print action
 */
function handlePrint() {
    window.print();
}

/**
 * Create text version of prep plan
 */
function createTextVersion(result) {
    if (result.prep_sections) {
        const sections = result.prep_sections;
        let text = '=== APPOINTMENT PREPARATION PLAN ===\n\n';
        
        text += 'APPOINTMENT SUMMARY\n' + stripHtml(sections.appointment_summary) + '\n\n';
        
        if (sections.fasting_plan) {
            text += 'FASTING INSTRUCTIONS\n' + stripHtml(sections.fasting_plan) + '\n\n';
        }
        
        if (sections.diet_guidance) {
            text += 'DIET GUIDANCE\n' + stripHtml(sections.diet_guidance) + '\n\n';
        }
        
        text += 'MEDICATION INSTRUCTIONS\n' + stripHtml(sections.medication_instructions) + '\n\n';
        
        text += 'WHAT TO BRING\n' + sections.items_to_bring.map(item => '• ' + item).join('\n') + '\n\n';
        
        text += 'ARRIVAL INSTRUCTIONS\n' + stripHtml(sections.arrival_instructions) + '\n\n';
        
        if (sections.transport_instructions) {
            text += 'TRANSPORTATION REQUIREMENTS\n' + stripHtml(sections.transport_instructions) + '\n\n';
        }
        
        text += 'WHEN TO CALL THE CLINIC\n' + sections.red_flag_warnings.map(w => '• ' + w).join('\n') + '\n\n';
        
        text += stripHtml(sections.closing_note);
        
        return text;
    } else {
        return stripHtml(result.full_message);
    }
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
    return escapeHtml(text).replace(/\n/g, '<br>');
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
