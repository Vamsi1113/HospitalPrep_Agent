/**
 * PrepCare Agent — Multi-Step Wizard JavaScript
 * Step 1: Intake → Step 2: AI Analysis → Step 3: Confirm → Step 4: Book → Step 5: Results
 */

'use strict';

// ═══════════════════════════════════════════
// GLOBAL STATE
// ═══════════════════════════════════════════
let currentStep      = 1;
let intakeSnapshot   = null;   // patient intake data
let analysisResult   = null;   // /api/analyze response
let selectedDoctor   = null;   // selected doctor object
let selectedSlot     = null;   // selected time slot
let bookingResult    = null;   // /api/book-appointment response
let currentResPane   = 'patient';
let userLocation     = null;   // { lat, lng } from geolocation

const $ = id => document.getElementById(id);

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initQuickCases();
    initAnalyzeBtn();
    initStep2Actions();
    initStep3Actions();
    initResultActions();
    initVoiceIntake();
    showStep(1);
});

// ═══════════════════════════════════════════
// STEP NAVIGATION
// ═══════════════════════════════════════════
const STEP_META = {
    1: { title: 'Patient Intake',     sub: 'Step 1 of 4 — Describe your symptoms' },
    2: { title: 'AI Analysis',        sub: 'Step 2 of 4 — Review recommended doctors & slots' },
    3: { title: 'Confirm Booking',    sub: 'Step 3 of 4 — Review and confirm your selection' },
    4: { title: 'Booking in Progress',sub: 'Step 4 of 4 — The agent is finalizing your appointment' },
    5: { title: 'Appointment Ready',  sub: 'Booking confirmed — Your preparation guide is ready' },
};

function showStep(step) {
    currentStep = step;

    // Hide all panels
    document.querySelectorAll('.wiz-step-panel').forEach(p => p.classList.remove('active'));

    // Show relevant panel
    const panelId = step === 4 ? 'panel-step-4-loading' : `panel-step-${step}`;
    const panel = $(panelId);
    if (panel) panel.classList.add('active');

    // Update sidebar steps
    [1,2,3,4].forEach(s => {
        const nav = $(`step-nav-${s}`);
        const conn = $(`conn-${s}`);
        if (!nav) return;
        nav.classList.remove('active','done');
        if (s < step || (step === 5 && s <= 4)) {
            nav.classList.add('done');
            nav.querySelector('.step-badge').textContent = '✓';
            if (conn) conn.classList.add('done');
        } else if (s === step) {
            nav.classList.add('active');
            nav.querySelector('.step-badge').textContent = s;
        } else {
            nav.querySelector('.step-badge').textContent = s;
            if (conn) conn.classList.remove('done');
        }
    });

    // Step 5 maps to sidebar step 4 "done"
    if (step === 5) {
        const nav4 = $('step-nav-4');
        if (nav4) { nav4.classList.add('done'); nav4.querySelector('.step-badge').textContent = '✓'; }
    }

    // Update topbar
    const meta = STEP_META[step] || {};
    const titleEl = $('wiz-step-title');
    const subEl   = $('wiz-step-sub');
    if (titleEl) titleEl.textContent = meta.title || '';
    if (subEl)   subEl.textContent   = meta.sub   || '';
}

// ═══════════════════════════════════════════
// STEP 1: INTAKE
// ═══════════════════════════════════════════
function gatherIntake() {
    const csvList = v => v ? v.split(',').map(s => s.trim()).filter(Boolean) : [];
    return {
        patient_name:         $('patient_name')?.value || '',
        age_group:            $('age_group')?.value || '',
        chief_complaint:      $('chief_complaint')?.value || '',
        symptoms_description: $('symptoms_description')?.value || '',
        current_medications:  csvList($('current_medications')?.value),
        allergies:            csvList($('allergies')?.value),
        prior_conditions:     csvList($('prior_conditions')?.value),
        appointment_type:     $('appointment_type')?.value || '',
        procedure:            $('procedure')?.value || '',
        channel_preference:   $('channel_preference')?.value || '',
        conversational_query: $('conversational_query')?.value || '',
        input_mode:           $('conversational_query')?.value ? 'voice' : 'text',
    };
}

function initAnalyzeBtn() {
    const btn = $('analyze-btn');
    if (!btn) return;
    btn.addEventListener('click', handleAnalyze);
}

async function handleAnalyze() {
    const intake = gatherIntake();

    // Require at least a complaint or voice query
    if (!intake.chief_complaint && !intake.conversational_query && !intake.symptoms_description) {
        alert('Please describe your symptoms or chief complaint before continuing.');
        return;
    }

    // If voice/conversational query, try to extract complaint from it
    if (!intake.chief_complaint && intake.conversational_query) {
        intake.chief_complaint = intake.conversational_query;
    }

    const btn = $('analyze-btn');
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-sm"></div> Analyzing...';

    // Get user location if not already captured
    if (!userLocation) {
        await captureUserLocation();
    }

    // Attach location to intake if available
    if (userLocation) {
        intake.lat = userLocation.lat;
        intake.lng = userLocation.lng;
    }

    try {
        const res  = await fetch('/api/analyze', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(intake)
        });
        const data = await res.json();

        if (data.error) {
            alert('Analysis failed: ' + (data.messages || []).join(' '));
            return;
        }

        intakeSnapshot = intake;
        analysisResult = data;
        renderStep2(data);
        showStep(2);

    } catch (err) {
        console.error(err);
        alert('Network error — please check your connection and try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

async function captureUserLocation() {
    if (!navigator.geolocation) {
        console.warn('Geolocation not supported');
        return;
    }

    return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                console.log('User location captured:', userLocation);
                resolve();
            },
            (error) => {
                console.warn('Geolocation denied or failed:', error.message);
                // Show inline notice but don't block
                const notice = document.createElement('div');
                notice.style.cssText = 'background:#fef3c7;border:1px solid #f59e0b;padding:8px 12px;border-radius:6px;margin:10px 0;font-size:13px;';
                notice.textContent = '📍 Location access needed for nearby hospitals. You can type your city name instead.';
                const form = document.querySelector('.intake-form');
                if (form) form.insertBefore(notice, form.firstChild);
                resolve();
            },
            { timeout: 5000, enableHighAccuracy: false }
        );
    });
}

// ═══════════════════════════════════════════
// STEP 2: ANALYSIS RESULTS
// ═══════════════════════════════════════════
function renderStep2(data) {
    // Triage banner
    const triage    = data.triage || {};
    const urgency   = triage.urgency || 'routine';
    const specialty = (triage.specialty || 'General').replace(/\b\w/g, c => c.toUpperCase());
    const redFlags  = triage.red_flags || [];

    // Update topbar urgency tag
    const urgTag = $('urgency-tag');
    if (urgTag) {
        urgTag.className = `urgency-tag ${urgency}`;
        urgTag.textContent = urgency.charAt(0).toUpperCase() + urgency.slice(1);
    }

    const icons = { routine: '✅', urgent: '⚡', emergency: '🚨' };
    const labels = { routine: 'Routine', urgent: 'Urgent', emergency: 'Emergency' };
    const descs = {
        routine:   'Your symptoms are suitable for a scheduled appointment.',
        urgent:    'Your symptoms may require an expedited consultation.',
        emergency: 'Serious indicators detected — please seek immediate care if worsening.'
    };

    const bannerContainer = $('triage-banner-container');
    bannerContainer.innerHTML = `
        <div class="triage-banner ${urgency}" style="max-width:880px; margin: 0 auto 20px;">
            <span class="triage-icon">${icons[urgency]}</span>
            <div class="triage-body">
                <div class="triage-label">${labels[urgency]} — ${specialty}</div>
                <div class="triage-desc">${descs[urgency]}${redFlags.length ? ' · ' + redFlags[0] : ''}</div>
            </div>
            <span class="triage-spec">${specialty}</span>
        </div>`;

    // Doctor cards
    const grid = $('doctors-grid');
    grid.innerHTML = `<div class="section-heading">Recommended Specialists & Available Slots</div>`;

    const doctors = data.doctors || [];
    doctors.forEach(doc => {
        const stars = '★'.repeat(Math.round(doc.rating)) + '☆'.repeat(5 - Math.round(doc.rating));
        
        const slotsHtml = (doc.slots || []).slice(0,3).map(s => `
            <button class="slot-btn" 
                data-doctor-id="${doc.id}"
                data-slot-id="${s.slot_id}"
                data-date="${s.datetime_display}"
                data-iso="${s.datetime_iso}"
                data-duration="${s.duration}"
                data-location="${s.location}"
                onclick="selectSlot(this, ${JSON.stringify(doc).replace(/"/g,"&quot;")})">
                📅 ${s.datetime_display} · ${s.duration}
            </button>`).join('');

        const card = document.createElement('div');
        card.className = 'doctor-card';
        card.id = `doc-card-${doc.id}`;
        card.innerHTML = `
            <div class="doc-header">
                <div class="doc-avatar">${doc.image_initial || doc.name[0]}</div>
                <div>
                    <div class="doc-name">${doc.name}</div>
                    <div class="doc-spec">${doc.specialty}</div>
                </div>
            </div>
            <div class="doc-meta">
                <span class="doc-pill star">⭐ ${doc.rating}/5</span>
                <span class="doc-pill hosp">🏥 ${doc.hospital}</span>
                <span class="doc-pill">📍 ${doc.hospital_location}</span>
                <span class="doc-pill">🩺 ${doc.experience}</span>
            </div>
            <div class="slots-section">
                <div class="slots-label">Available Slots</div>
                <div class="slots-grid" id="slots-${doc.id}">${slotsHtml}</div>
            </div>`;
        grid.appendChild(card);
    });

    selectedDoctor = null;
    selectedSlot   = null;
    $('confirm-selection-btn').disabled = true;
}

window.selectSlot = function(btn, doctor) {
    // Deselect all slots
    document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
    document.querySelectorAll('.doctor-card').forEach(c => c.classList.remove('selected'));

    // Select this slot + card
    btn.classList.add('selected');
    const card = $(`doc-card-${doctor.id}`);
    if (card) card.classList.add('selected');

    selectedDoctor = doctor;
    selectedSlot = {
        slot_id:          btn.dataset.slotId,
        datetime_display: btn.dataset.date,
        datetime_iso:     btn.dataset.iso,
        duration:         btn.dataset.duration,
        location:         btn.dataset.location,
    };

    $('confirm-selection-btn').disabled = false;
};

function initStep2Actions() {
    $('back-to-1')?.addEventListener('click', () => {
        $('urgency-tag').className = 'urgency-tag';
        showStep(1);
    });
    $('confirm-selection-btn')?.addEventListener('click', () => {
        if (!selectedDoctor || !selectedSlot) return;
        renderStep3();
        showStep(3);
    });
}

// ═══════════════════════════════════════════
// STEP 3: CONFIRM
// ═══════════════════════════════════════════
function renderStep3() {
    const d = selectedDoctor;
    const s = selectedSlot;
    const patientName = intakeSnapshot?.patient_name || 'Patient';

    const rows = [
        { icon: '👤', key: 'Patient Name',  val: patientName },
        { icon: '👨‍⚕️', key: 'Doctor',        val: d.name },
        { icon: '🩺', key: 'Specialty',     val: d.specialty },
        { icon: '🏥', key: 'Hospital',       val: `${d.hospital}, ${d.hospital_location}` },
        { icon: '📅', key: 'Date & Time',    val: s.datetime_display },
        { icon: '⏱',  key: 'Duration',      val: s.duration },
        { icon: '📍', key: 'Location',       val: s.location },
        { icon: '💬', key: 'Chief Complaint', val: intakeSnapshot?.chief_complaint || intakeSnapshot?.conversational_query || '—' },
    ];

    $('confirm-body').innerHTML = rows.map(r => `
        <div class="confirm-row">
            <div class="confirm-icon" style="font-size:18px;">${r.icon}</div>
            <div>
                <div class="confirm-key">${r.key}</div>
                <div class="confirm-val">${r.val}</div>
            </div>
        </div>`).join('');
}

function initStep3Actions() {
    $('back-to-2')?.addEventListener('click', () => showStep(2));
    $('book-btn')?.addEventListener('click', handleBooking);
}

// ═══════════════════════════════════════════
// STEP 4: BOOKING + AGENT RUN
// ═══════════════════════════════════════════
async function handleBooking() {
    const btn = $('book-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner-sm"></div> Booking...';

    showStep(4);
    animateBookingSteps();

    try {
        const payload = {
            intake_data:     intakeSnapshot,
            selected_doctor: selectedDoctor,
            selected_slot:   selectedSlot,
        };

        const res  = await fetch('/api/book-appointment', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.error) {
            // Show error and go back to step 3
            showStep(3);
            alert('Booking failed: ' + (data.messages || []).join(' '));
            btn.disabled = false;
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg> Confirm & Book Appointment';
            return;
        }

        bookingResult = data;
        setTimeout(() => {
            renderResults(data);
            showStep(5);
        }, 1000); // small pause so user sees "done" state

    } catch (err) {
        console.error(err);
        showStep(3);
        alert('Network error — please try again.');
        btn.disabled = false;
    }
}

function animateBookingSteps() {
    const steps = ['bstep-1','bstep-2','bstep-3','bstep-4','bstep-5'];
    steps.forEach(id => {
        const el = $(id);
        if (el) el.className = 'booking-step-row';
    });
    let i = 0;
    const interval = setInterval(() => {
        if (i > 0 && steps[i-1]) $(steps[i-1])?.classList.add('done');
        if (i < steps.length) {
            $(steps[i])?.classList.add('active');
            i++;
        } else {
            clearInterval(interval);
        }
    }, 900);
}

// ═══════════════════════════════════════════
// STEP 5: RESULTS
// ═══════════════════════════════════════════
function renderResults(data) {
    const booking = data.booking || {};

    // Confirmation banner
    $('bc-id').textContent = booking.confirmation_id || 'PREPCARE-CONFIRMED';
    $('bc-details').innerHTML = `
        <div class="bc-detail-item">
            <div class="bc-detail-label">Doctor</div>
            <div class="bc-detail-val">${booking.doctor_name || '—'}</div>
        </div>
        <div class="bc-detail-item">
            <div class="bc-detail-label">Hospital</div>
            <div class="bc-detail-val">${booking.hospital || '—'}</div>
        </div>
        <div class="bc-detail-item">
            <div class="bc-detail-label">Date & Time</div>
            <div class="bc-detail-val">${booking.date_time || '—'}</div>
        </div>`;

    // Patient prep
    const prepContent = $('patient-prep-output');
    if (prepContent) {
        prepContent.textContent = data.patient_message || 'No preparation guide generated.';
    }

    // Clinician brief
    const clinContent = $('clinician-brief-output');
    if (clinContent) {
        clinContent.textContent = data.clinician_summary || 'No clinical briefing available.';
    }
}

// ═══════════════════════════════════════════
// RESULTS TABS + ACTIONS
// ═══════════════════════════════════════════
function initResultActions() {
    // Tabs
    document.querySelectorAll('.res-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.res-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.res-pane').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const pane = $(`res-${tab.dataset.res}`);
            if (pane) pane.classList.add('active');
            currentResPane = tab.dataset.res;
        });
    });

    // Copy
    $('copy-btn')?.addEventListener('click', () => {
        const text = currentResPane === 'patient'
            ? ($('patient-prep-output')?.textContent || '')
            : ($('clinician-brief-output')?.textContent || '');
        navigator.clipboard.writeText(text).then(() => {
            const btn = $('copy-btn');
            const orig = btn.textContent;
            btn.textContent = '✓ Copied!';
            setTimeout(() => btn.textContent = orig, 1500);
        });
    });

    // Print
    $('print-res-btn')?.addEventListener('click', () => window.print());

    // New patient
    $('new-case-btn')?.addEventListener('click', resetWizard);
}

function resetWizard() {
    intakeSnapshot  = null;
    analysisResult  = null;
    selectedDoctor  = null;
    selectedSlot    = null;
    bookingResult   = null;

    // Clear form
    ['patient_name','age_group','chief_complaint','symptoms_description',
     'current_medications','allergies','prior_conditions','appointment_type',
     'procedure','channel_preference','conversational_query'].forEach(id => {
        const el = $(id);
        if (el) el.value = '';
    });

    $('urgency-tag').className = 'urgency-tag';
    showStep(1);
}

// ═══════════════════════════════════════════
// QUICK CASES
// ═══════════════════════════════════════════
function initQuickCases() {
    document.querySelectorAll('.q-chip').forEach(chip => {
        chip.addEventListener('click', () => loadSampleCase(chip.dataset.caseId));
    });
}

async function loadSampleCase(caseId) {
    try {
        const res  = await fetch(`/load-sample-case/${caseId}`);
        const data = await res.json();
        if (data.error) { return; }

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
        set('channel_preference',     data.channel_preference);
        $('conversational_query').value = '';
    } catch (err) {
        console.error('Failed to load sample case:', err);
    }
}

// ═══════════════════════════════════════════
// VOICE INTAKE - WEB SPEECH API
// ═══════════════════════════════════════════
let recognition = null;
let isRecording  = false;

function initVoiceIntake() {
    const micBtn = $('mic-btn');
    if (!micBtn) return;

    // Check for Web Speech API support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        micBtn.title = 'Speech recognition not supported in this browser';
        micBtn.addEventListener('click', () =>
            alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.'));
        return;
    }

    if (!window.isSecureContext) {
        micBtn.title = 'Microphone requires HTTPS or localhost';
        micBtn.addEventListener('click', () =>
            alert('Microphone access requires http://localhost or HTTPS.'));
        return;
    }

    // Initialize recognition
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.language = 'en-IN';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        isRecording = true;
        setRecordingUI(true, 'Listening...');
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }

        // Show interim results as live caption
        if (interimTranscript) {
            const text = $('rec-status-text');
            if (text) text.textContent = interimTranscript;
        }

        // Process final transcript
        if (finalTranscript) {
            handleTranscript(finalTranscript.trim());
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        isRecording = false;
        setRecordingUI(false);

        let message = 'Speech recognition error: ';
        switch (event.error) {
            case 'not-allowed':
            case 'permission-denied':
                message = 'Microphone access denied. Click the lock icon in your browser URL bar and allow microphone access.';
                break;
            case 'no-speech':
                message = 'No speech detected. Please try again.';
                break;
            case 'network':
                message = 'Network error. Please check your connection.';
                break;
            case 'aborted':
                return; // User stopped, don't show error
            default:
                message += event.error;
        }
        alert(message);
    };

    recognition.onend = () => {
        isRecording = false;
        setRecordingUI(false);
    };

    micBtn.addEventListener('click', toggleRecording);
}

async function toggleRecording() {
    if (isRecording) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch (err) {
            console.error('Failed to start recognition:', err);
            alert('Failed to start speech recognition. Please try again.');
        }
    }
}

function setRecordingUI(active, statusText = '') {
    const btn    = $('mic-btn');
    const status = $('recording-status');
    const text   = $('rec-status-text');
    
    if (active) {
        btn?.classList.add('recording');
        if (status) status.style.display = 'flex';
        if (text && statusText) text.textContent = statusText;
    } else {
        btn?.classList.remove('recording');
        if (status) status.style.display = 'none';
    }
}

async function handleTranscript(transcript) {
    if (!transcript) return;

    setRecordingUI(true, 'Extracting information...');

    try {
        const res = await fetch('/api/extract-intake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript })
        });
        const data = await res.json();

        if (data.error) {
            alert('Extraction failed: ' + (data.messages || []).join(' '));
            return;
        }

        const extracted = data.extracted || {};
        
        // Auto-populate form fields where values exist
        const fieldMap = {
            'patient_name': extracted.name,
            'age_group': extracted.age,
            'chief_complaint': extracted.chief_complaint,
            'symptoms_description': extracted.symptoms_description,
            'procedure': extracted.procedure_type,
            'current_medications': Array.isArray(extracted.current_medications) 
                ? extracted.current_medications.join(', ') 
                : extracted.current_medications,
            'allergies': Array.isArray(extracted.allergies) 
                ? extracted.allergies.join(', ') 
                : extracted.allergies,
            'prior_conditions': Array.isArray(extracted.prior_conditions) 
                ? extracted.prior_conditions.join(', ') 
                : extracted.prior_conditions
        };

        // Populate fields and highlight missing ones
        Object.keys(fieldMap).forEach(fieldId => {
            const el = $(fieldId);
            if (!el) return;

            const value = fieldMap[fieldId];
            if (value && value !== null && value !== '') {
                el.value = value;
                el.style.border = '2px solid #10b981'; // Green border for filled
                setTimeout(() => el.style.border = '', 2000);
            } else {
                el.style.border = '2px solid #fbbf24'; // Yellow border for missing
            }
        });

        // Also store raw transcript in conversational_query
        const convQuery = $('conversational_query');
        if (convQuery) {
            convQuery.value = transcript;
        }

        // Show message about highlighted fields
        const missingCount = Object.values(fieldMap).filter(v => !v || v === '').length;
        if (missingCount > 0) {
            alert(`Information extracted! Please fill in the ${missingCount} highlighted field(s).`);
        }

    } catch (err) {
        console.error('Extraction network error:', err);
        alert('Failed to extract information. Please try again.');
    } finally {
        setRecordingUI(false);
    }
}

