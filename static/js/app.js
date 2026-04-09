/**
 * Appointment Prep AI Agent - Frontend JavaScript
 * 
 * Handles:
 * - AJAX form submission
 * - Form validation
 * - Sample data loading
 * - Copy to clipboard functionality
 * - UI state management
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const form = document.getElementById('appointment-form');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    
    // Get alert elements
    const errorAlert = document.getElementById('error-alert');
    const errorMessages = document.getElementById('error-messages');
    const successAlert = document.getElementById('success-alert');
    const successMessage = document.getElementById('success-message');
    
    // Get result elements
    const previewCard = document.getElementById('preview-card');
    const previewText = document.getElementById('preview-text');
    const messageCard = document.getElementById('message-card');
    const fullMessage = document.getElementById('full-message');
    const rulesCard = document.getElementById('rules-card');
    const rulesList = document.getElementById('rules-list');
    const agentTraceCard = document.getElementById('agent-trace-card');
    const agentTraceList = document.getElementById('agent-trace-list');
    const llmBadge = document.getElementById('llm-badge');
    const messageIdText = document.getElementById('message-id');
    const copyBtn = document.getElementById('copy-btn');
    
    // Get sample buttons
    const sampleButtons = document.querySelectorAll('[data-sample-id]');
    
    /**
     * Check if sample data is available and disable buttons if not
     * Validates: Requirement 8.9
     */
    async function checkSampleDataAvailability() {
        if (sampleButtons.length === 0) return;
        
        try {
            // Try to load first sample to check availability
            const response = await fetch('/load-sample/0');
            if (!response.ok) {
                // Disable all sample buttons if data not available
                sampleButtons.forEach(button => {
                    button.disabled = true;
                    button.title = 'Sample data not available';
                });
            }
        } catch (error) {
            // Disable buttons on network error
            sampleButtons.forEach(button => {
                button.disabled = true;
                button.title = 'Sample data not available';
            });
        }
    }
    
    // Check sample data availability on page load
    checkSampleDataAvailability();
    
    /**
     * Hide all alerts
     */
    function hideAlerts() {
        errorAlert.style.display = 'none';
        successAlert.style.display = 'none';
    }
    
    /**
     * Show error alert with messages
     * Validates: Requirements 8.1, 8.2
     */
    function showError(messages) {
        hideAlerts();
        
        if (Array.isArray(messages)) {
            errorMessages.innerHTML = messages.map(msg => `<p>${escapeHtml(msg)}</p>`).join('');
        } else {
            errorMessages.innerHTML = `<p>${escapeHtml(messages)}</p>`;
        }
        
        errorAlert.style.display = 'block';
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Show success alert with message
     */
    function showSuccess(message) {
        hideAlerts();
        successMessage.textContent = message;
        successAlert.style.display = 'block';
        successAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    /**
     * Hide result cards
     */
    function hideResults() {
        previewCard.style.display = 'none';
        messageCard.style.display = 'none';
        rulesCard.style.display = 'none';
        agentTraceCard.style.display = 'none';
    }
    
    /**
     * Show result cards with data
     */
    function showResults(result) {
        // Show preview
        previewText.textContent = result.preview;
        previewCard.style.display = 'block';
        
        // Show full message
        fullMessage.textContent = result.full_message;
        messageCard.style.display = 'block';
        
        // Show LLM badge
        if (result.llm_used) {
            llmBadge.textContent = 'AI Enhanced';
            llmBadge.className = 'badge badge-llm';
        } else {
            llmBadge.textContent = 'Template';
            llmBadge.className = 'badge badge-template';
        }
        
        // Show message ID
        if (result.message_id) {
            messageIdText.textContent = `Message ID: ${result.message_id}`;
        } else {
            messageIdText.textContent = 'Not saved';
        }
        
        // Show rules explanation
        rulesList.innerHTML = result.rules_explanation.map(rule => `
            <div class="rule-item">
                <div class="rule-name">${rule.rule}</div>
                <div class="rule-reason">${rule.reason}</div>
            </div>
        `).join('');
        rulesCard.style.display = 'block';
        
        // Show agent reasoning trace
        if (result.agent_trace && result.agent_trace.length > 0) {
            agentTraceList.innerHTML = result.agent_trace.map(step => `
                <div class="trace-item">
                    <div class="trace-step">${escapeHtml(step.step)}</div>
                    <div class="trace-description">${escapeHtml(step.description || '')}</div>
                    <div class="trace-timestamp">${escapeHtml(step.timestamp || '')}</div>
                </div>
            `).join('');
            agentTraceCard.style.display = 'block';
        }
        
        // Scroll to results
        previewCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    /**
     * Set loading state
     */
    function setLoading(loading) {
        if (loading) {
            generateBtn.disabled = true;
            btnText.style.display = 'none';
            btnSpinner.style.display = 'inline-block';
        } else {
            generateBtn.disabled = false;
            btnText.style.display = 'inline';
            btnSpinner.style.display = 'none';
        }
    }
    
    /**
     * Validate form fields
     * Validates: Requirements 8.1, 8.2
     */
    function validateForm() {
        const errors = [];
        
        // Get form data
        const patientName = document.getElementById('patient_name').value.trim();
        const appointmentType = document.getElementById('appointment_type').value;
        const procedure = document.getElementById('procedure').value.trim();
        const clinicianName = document.getElementById('clinician_name').value.trim();
        const appointmentDatetime = document.getElementById('appointment_datetime').value;
        const channelPreference = document.getElementById('channel_preference').value;
        
        // Clear all error highlights first
        clearFieldErrors();
        
        // Validate required fields
        if (!patientName) {
            errors.push('Patient name is required');
            highlightFieldError('patient_name');
        }
        if (!appointmentType) {
            errors.push('Appointment type is required');
            highlightFieldError('appointment_type');
        }
        if (!procedure) {
            errors.push('Procedure is required');
            highlightFieldError('procedure');
        }
        if (!clinicianName) {
            errors.push('Clinician name is required');
            highlightFieldError('clinician_name');
        }
        if (!appointmentDatetime) {
            errors.push('Appointment date and time is required');
            highlightFieldError('appointment_datetime');
        }
        if (!channelPreference) {
            errors.push('Delivery channel is required');
            highlightFieldError('channel_preference');
        }
        
        // Validate field lengths
        if (patientName.length > 100) {
            errors.push('Patient name must be 100 characters or less');
            highlightFieldError('patient_name');
        }
        if (procedure.length > 200) {
            errors.push('Procedure must be 200 characters or less');
            highlightFieldError('procedure');
        }
        if (clinicianName.length > 100) {
            errors.push('Clinician name must be 100 characters or less');
            highlightFieldError('clinician_name');
        }
        
        // Validate future date
        if (appointmentDatetime) {
            const aptDate = new Date(appointmentDatetime);
            const now = new Date();
            if (aptDate <= now) {
                errors.push('Appointment date must be in the future');
                highlightFieldError('appointment_datetime');
            }
        }
        
        return errors;
    }
    
    /**
     * Highlight a form field with error styling
     * Validates: Requirement 8.2
     */
    function highlightFieldError(fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.classList.add('error');
        }
    }
    
    /**
     * Clear all field error highlights
     */
    function clearFieldErrors() {
        const fields = form.querySelectorAll('.form-input, .form-select, .form-textarea');
        fields.forEach(field => field.classList.remove('error'));
    }
    
    /**
     * Get form data as object
     */
    function getFormData() {
        return {
            patient_name: document.getElementById('patient_name').value.trim(),
            appointment_type: document.getElementById('appointment_type').value,
            procedure: document.getElementById('procedure').value.trim(),
            clinician_name: document.getElementById('clinician_name').value.trim(),
            appointment_datetime: document.getElementById('appointment_datetime').value,
            channel_preference: document.getElementById('channel_preference').value,
            special_notes: document.getElementById('special_notes').value.trim()
        };
    }
    
    /**
     * Handle form submission
     * Validates: Requirements 8.1, 8.2, 8.6, 8.7
     */
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Hide previous results and alerts
        hideAlerts();
        hideResults();
        
        // Validate form
        const validationErrors = validateForm();
        if (validationErrors.length > 0) {
            showError(validationErrors);
            return;
        }
        
        // Get form data
        const formData = getFormData();
        
        // Set loading state
        setLoading(true);
        
        try {
            // Send AJAX request
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            // Handle response
            if (response.ok && !result.error) {
                // Success (Requirement 8.6)
                showSuccess('Appointment prep instructions generated successfully!');
                showResults(result);
            } else {
                // Error (Requirement 8.1, 8.2)
                showError(result.messages || ['Failed to generate instructions']);
            }
        } catch (error) {
            // Network or parsing error (Requirement 8.6, 8.7)
            showError('Network error: Failed to connect to server. Please check your connection and try again.');
        } finally {
            // Reset loading state
            setLoading(false);
        }
    });
    
    /**
     * Handle sample data button clicks
     * Validates: Requirements 8.7, 8.9
     */
    sampleButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const sampleId = this.getAttribute('data-sample-id');
            
            // Disable button during load
            const originalText = this.textContent;
            this.disabled = true;
            this.textContent = 'Loading...';
            
            try {
                // Fetch sample data
                const response = await fetch(`/load-sample/${sampleId}`);
                const sample = await response.json();
                
                if (response.ok && !sample.error) {
                    // Populate form with sample data
                    document.getElementById('patient_name').value = sample.patient_name;
                    document.getElementById('appointment_type').value = sample.appointment_type;
                    document.getElementById('procedure').value = sample.procedure;
                    document.getElementById('clinician_name').value = sample.clinician_name;
                    document.getElementById('appointment_datetime').value = sample.appointment_datetime;
                    document.getElementById('channel_preference').value = sample.channel_preference;
                    document.getElementById('special_notes').value = sample.special_notes || '';
                    
                    // Clear any error highlights
                    clearFieldErrors();
                    
                    // Show success message
                    showSuccess('Sample data loaded successfully!');
                    
                    // Hide results
                    hideResults();
                } else {
                    // Handle error (Requirement 8.7, 8.9)
                    showError(sample.messages || ['Failed to load sample data']);
                }
            } catch (error) {
                // Network error (Requirement 8.7)
                showError('Network error: Failed to load sample data. Please try again.');
            } finally {
                // Re-enable button
                this.disabled = false;
                this.textContent = originalText;
            }
        });
    });
    
    /**
     * Handle copy button click
     * Validates: Requirement 8.7
     */
    copyBtn.addEventListener('click', function() {
        const messageText = fullMessage.textContent;
        
        // Copy to clipboard
        navigator.clipboard.writeText(messageText).then(() => {
            // Show success feedback
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            copyBtn.classList.add('btn-success');
            
            // Reset after 2 seconds
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.remove('btn-success');
            }, 2000);
        }).catch(() => {
            // Fallback for older browsers or permission issues
            showError('Failed to copy to clipboard. Please select and copy the text manually.');
        });
    });
    
    /**
     * Add blur validation for form fields
     */
    const formInputs = form.querySelectorAll('.form-input, .form-select, .form-textarea');
    formInputs.forEach(input => {
        input.addEventListener('blur', function() {
            // Remove error class on blur
            this.classList.remove('error');
        });
        
        input.addEventListener('input', function() {
            // Remove error class on input
            this.classList.remove('error');
        });
    });
});
