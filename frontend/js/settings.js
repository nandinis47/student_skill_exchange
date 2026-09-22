// ============================================
// Settings Page Logic - SkillX
// ============================================

let currentStudent = null;
let userSettings = null;

document.addEventListener('DOMContentLoaded', async () => {
    requireAuth();
    renderNavUser();

    currentStudent = getCurrentStudent();
    if (!currentStudent) return;

    setupTabs();
    await loadUserSettings();
});

// Setup tab navigation
function setupTabs() {
    const tabBtns = document.querySelectorAll('.settings-tab-btn');
    const sections = document.querySelectorAll('.settings-section');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;

            tabBtns.forEach(b => b.classList.toggle('active', b === btn));
            sections.forEach(s => s.classList.toggle('active', s.id === `tab-${targetTab}`));
        });
    });
}

// Fetch user settings from backend
async function loadUserSettings() {
    const alertBox = document.getElementById('settings-alert');
    const res = await Settings.get(currentStudent.id);

    if (res.ok && res.data) {
        userSettings = res.data;
        populateAccountTab();
        populateNotificationsTab();
        populatePrivacyTab();
        populateSessionTab();
        populateAppearanceTab();
    } else {
        if (alertBox) showAlert(alertBox, res.data.error || 'Failed to load settings', 'error');
    }
}

// ── ACCOUNT TAB ─────────────────────────────────────────────
function populateAccountTab() {
    const emailInput = document.getElementById('account-email');
    if (emailInput) emailInput.value = userSettings.email || currentStudent.email || '';

    const googleNotice = document.getElementById('google-password-notice');
    const pwForm = document.getElementById('password-change-form');

    if (userSettings.is_google_user) {
        if (googleNotice) googleNotice.style.display = 'block';
        if (pwForm) pwForm.style.display = 'none';
    } else {
        if (googleNotice) googleNotice.style.display = 'none';
        if (pwForm) pwForm.style.display = 'block';
    }
}

async function handleUpdateEmail(e) {
    e.preventDefault();
    const email = document.getElementById('account-email').value.trim();
    const alertBox = document.getElementById('account-alert');

    if (!email) {
        showAlert(alertBox, 'Please enter a valid email', 'error');
        return;
    }

    const res = await Settings.updateEmail(currentStudent.id, email);
    if (res.ok && res.data) {
        showAlert(alertBox, 'Email updated successfully!', 'success');
        if (res.data.student) {
            currentStudent.email = res.data.student.email;
            setCurrentStudent(currentStudent);
        }
    } else {
        showAlert(alertBox, res.data.error || 'Failed to update email', 'error');
    }
}

async function handleChangePassword(e) {
    e.preventDefault();
    const currentPw = document.getElementById('current-password').value;
    const newPw = document.getElementById('new-password').value;
    const confirmPw = document.getElementById('confirm-password').value;
    const alertBox = document.getElementById('account-alert');

    if (!currentPw || !newPw || !confirmPw) {
        showAlert(alertBox, 'All password fields are required', 'error');
        return;
    }

    if (newPw !== confirmPw) {
        showAlert(alertBox, 'New passwords do not match', 'error');
        return;
    }

    if (newPw.length < 6) {
        showAlert(alertBox, 'Password must be at least 6 characters long', 'error');
        return;
    }

    const res = await Settings.updatePassword(currentStudent.id, currentPw, newPw);
    if (res.ok) {
        showAlert(alertBox, 'Password changed successfully!', 'success');
        document.getElementById('password-change-form').reset();
    } else {
        showAlert(alertBox, res.data.error || 'Failed to change password', 'error');
    }
}

// ── DELETE ACCOUNT ──────────────────────────────────────────
function openDeleteAccountModal() {
    const modal = document.getElementById('delete-modal');
    if (modal) modal.classList.add('show');
}

function closeDeleteAccountModal() {
    const modal = document.getElementById('delete-modal');
    if (modal) modal.classList.remove('show');
    const input = document.getElementById('delete-confirm-input');
    if (input) input.value = '';
}

async function confirmDeleteAccount() {
    const confirmInput = document.getElementById('delete-confirm-input');
    const modalAlert = document.getElementById('delete-modal-alert');
    if (!confirmInput || confirmInput.value.trim() !== 'DELETE') {
        if (modalAlert) showAlert(modalAlert, 'Please type DELETE to confirm account deletion', 'error');
        return;
    }

    const res = await Settings.deleteAccount(currentStudent.id);
    if (res.ok) {
        localStorage.setItem('skillx_logged_out', '1');
        clearCurrentStudent();
        window.location.replace('index.html');
    } else {
        if (modalAlert) showAlert(modalAlert, res.data.error || 'Failed to delete account', 'error');
    }
}

// ── NOTIFICATIONS TAB ───────────────────────────────────────
function populateNotificationsTab() {
    document.getElementById('notif-requests').checked = Boolean(userSettings.notif_requests);
    document.getElementById('notif-messages').checked = Boolean(userSettings.notif_messages);
    document.getElementById('notif-sessions').checked = Boolean(userSettings.notif_sessions);
    document.getElementById('notif-smart-matches').checked = Boolean(userSettings.notif_smart_matches);
}

async function handleSaveNotifications(e) {
    e.preventDefault();
    const alertBox = document.getElementById('notifications-alert');

    const payload = {
        ...userSettings,
        notif_requests: document.getElementById('notif-requests').checked,
        notif_messages: document.getElementById('notif-messages').checked,
        notif_sessions: document.getElementById('notif-sessions').checked,
        notif_smart_matches: document.getElementById('notif-smart-matches').checked,
    };

    const res = await Settings.update(currentStudent.id, payload);
    if (res.ok) {
        userSettings = { ...userSettings, ...payload };
        showAlert(alertBox, 'Notification preferences saved!', 'success');
    } else {
        showAlert(alertBox, res.data.error || 'Failed to save notifications', 'error');
    }
}

// ── PRIVACY TAB ─────────────────────────────────────────────
function populatePrivacyTab() {
    const reqPerm = userSettings.request_permissions || 'everyone';
    const profVis = userSettings.profile_visibility || 'public';

    setRadioGroupValue('request_permissions', reqPerm);
    setRadioGroupValue('profile_visibility', profVis);
}

function setRadioGroupValue(name, val) {
    const radios = document.querySelectorAll(`input[name="${name}"]`);
    radios.forEach(r => {
        r.checked = (r.value === val);
        const card = r.closest('.radio-card');
        if (card) card.classList.toggle('active', r.checked);
    });
}

function handleRadioCardClick(input) {
    const name = input.name;
    const radios = document.querySelectorAll(`input[name="${name}"]`);
    radios.forEach(r => {
        const card = r.closest('.radio-card');
        if (card) card.classList.toggle('active', r === input);
    });
}

async function handleSavePrivacy(e) {
    e.preventDefault();
    const alertBox = document.getElementById('privacy-alert');

    const reqPerm = getRadioGroupValue('request_permissions') || 'everyone';
    const profVis = getRadioGroupValue('profile_visibility') || 'public';

    const payload = {
        ...userSettings,
        request_permissions: reqPerm,
        profile_visibility: profVis
    };

    const res = await Settings.update(currentStudent.id, payload);
    if (res.ok) {
        userSettings = { ...userSettings, ...payload };
        showAlert(alertBox, 'Privacy settings saved!', 'success');
    } else {
        showAlert(alertBox, res.data.error || 'Failed to save privacy settings', 'error');
    }
}

function getRadioGroupValue(name) {
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    return selected ? selected.value : null;
}

// ── SESSION PREFERENCES TAB ──────────────────────────────────
function populateSessionTab() {
    const durationSelect = document.getElementById('session-duration');
    const availSelect = document.getElementById('session-availability');

    if (durationSelect) durationSelect.value = userSettings.session_duration || 60;
    if (availSelect) availSelect.value = userSettings.session_availability || 'anytime';
}

async function handleSaveSessionPrefs(e) {
    e.preventDefault();
    const alertBox = document.getElementById('session-alert');

    const duration = parseInt(document.getElementById('session-duration').value, 10);
    const availability = document.getElementById('session-availability').value;

    const payload = {
        ...userSettings,
        session_duration: duration,
        session_availability: availability
    };

    const res = await Settings.update(currentStudent.id, payload);
    if (res.ok) {
        userSettings = { ...userSettings, ...payload };
        showAlert(alertBox, 'Session preferences saved!', 'success');
    } else {
        showAlert(alertBox, res.data.error || 'Failed to save session preferences', 'error');
    }
}

// ── APPEARANCE TAB ──────────────────────────────────────────
function populateAppearanceTab() {
    const theme = userSettings.theme || localStorage.getItem('skillx_theme') || 'light';
    setRadioGroupValue('theme', theme);
    applyGlobalTheme(theme);
}

async function handleSaveAppearance(e) {
    e.preventDefault();
    const alertBox = document.getElementById('appearance-alert');
    const theme = getRadioGroupValue('theme') || 'light';

    const payload = {
        ...userSettings,
        theme: theme
    };

    const res = await Settings.update(currentStudent.id, payload);
    if (res.ok) {
        userSettings = { ...userSettings, ...payload };
        localStorage.setItem('skillx_theme', theme);
        applyGlobalTheme(theme);
        showAlert(alertBox, 'Appearance settings saved!', 'success');
    } else {
        showAlert(alertBox, res.data.error || 'Failed to save theme settings', 'error');
    }
}
