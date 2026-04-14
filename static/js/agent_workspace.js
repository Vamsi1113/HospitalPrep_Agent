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
// VOICE INTAKE
// ═══════════════════════════════════════════
let audioContext = null;
let processor    = null;
let inputSource  = null;
let isRecording  = false;

function initVoiceIntake() {
    const micBtn = $('mic-btn');
    if (!micBtn) return;

    if (!window.isSecureContext) {
        micBtn.title = 'Microphone requires HTTPS or localhost';
        micBtn.addEventListener('click', () =>
            alert('Microphone access requires http://localhost or HTTPS.'));
        return;
    }

    micBtn.addEventListener('click', toggleRecording);
}

async function toggleRecording() {
    isRecording ? stopRecording() : await startRecording();
}

async function startRecording() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const hasMic  = devices.some(d => d.kind === 'audioinput');
        if (!hasMic) throw new Error('No microphone detected on this system.');

        const stream  = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext  = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        inputSource   = audioContext.createMediaStreamSource(stream);
        processor     = audioContext.createScriptProcessor(4096, 1, 1);

        const leftChannel = [];
        processor.onaudioprocess = e => leftChannel.push(new Float32Array(e.inputBuffer.getChannelData(0)));
        inputSource.connect(processor);
        processor.connect(audioContext.destination);

        isRecording = true;
        setRecordingUI(true);

        window._stopRec = async () => {
            processor.disconnect();
            inputSource.disconnect();
            stream.getTracks().forEach(t => t.stop());
            await sendAudioToBackend(exportWAV(leftChannel, 16000));
        };
    } catch (err) {
        const msg = err.name === 'NotAllowedError'
            ? 'Microphone access denied. Click the lock icon in your browser URL bar and allow microphone access.'
            : 'Could not access microphone: ' + err.message;
        alert(msg);
    }
}

function stopRecording() {
    if (window._stopRec) { window._stopRec(); window._stopRec = null; }
    isRecording = false;
    setRecordingUI(false);
}

function setRecordingUI(active) {
    const btn    = $('mic-btn');
    const status = $('recording-status');
    const text   = $('rec-status-text');
    if (active) {
        btn?.classList.add('recording');
        if (status) status.style.display = 'flex';
        if (text)   text.textContent = 'Listening...';
    } else {
        btn?.classList.remove('recording');
        if (status) status.style.display = 'none';
    }
}

async function sendAudioToBackend(blob) {
    const status = $('recording-status');
    const text   = $('rec-status-text');
    if (status) { status.style.display = 'flex'; }
    if (text)   text.textContent = 'Transcribing...';

    const formData = new FormData();
    formData.append('audio', blob, 'recording.wav');

    try {
        const res  = await fetch('/api/transcribe', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.text) {
            const area = $('conversational_query');
            if (area) {
                area.value = (area.value ? area.value + ' ' : '') + data.text;
            }
        } else if (data.error) {
            alert('Transcription failed: ' + (data.messages || []).join(' '));
        }
    } catch (err) {
        console.error('Transcription network error:', err);
    } finally {
        if (status) status.style.display = 'none';
    }
}

// WAV ENCODER
function exportWAV(chunks, sampleRate) {
    const buffer   = flatten(chunks);
    const dataview = new DataView(new ArrayBuffer(44 + buffer.length * 2));
    writeString(dataview, 0, 'RIFF');
    dataview.setUint32(4, 36 + buffer.length * 2, true);
    writeString(dataview, 8, 'WAVE');
    writeString(dataview, 12, 'fmt ');
    dataview.setUint32(16, 16, true);
    dataview.setUint16(20, 1, true);
    dataview.setUint16(22, 1, true);
    dataview.setUint32(24, sampleRate, true);
    dataview.setUint32(28, sampleRate * 2, true);
    dataview.setUint16(32, 2, true);
    dataview.setUint16(34, 16, true);
    writeString(dataview, 36, 'data');
    dataview.setUint32(40, buffer.length * 2, true);
    let offset = 44;
    for (let i = 0; i < buffer.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, buffer[i]));
        dataview.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return new Blob([dataview], { type: 'audio/wav' });
}

function flatten(chunks) {
    let length = 0;
    chunks.forEach(c => length += c.length);
    const result = new Float32Array(length);
    let offset = 0;
    chunks.forEach(c => { result.set(c, offset); offset += c.length; });
    return result;
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++)
        view.setUint8(offset + i, string.charCodeAt(i));
}
