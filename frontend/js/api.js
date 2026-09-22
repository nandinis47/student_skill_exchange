// ============================================
// API Helper - All backend calls go here
// ============================================

const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000/api`;

// Current logged-in student (stored in sessionStorage)
function getCurrentStudent() {
    const data = sessionStorage.getItem('student');
    return data ? JSON.parse(data) : null;
}

function setCurrentStudent(student) {
    localStorage.removeItem('skillx_logged_out');
    sessionStorage.setItem('student', JSON.stringify(student));
}

function clearCurrentStudent() {
    sessionStorage.removeItem('student');
}

// Redirect to login if not authenticated (also blocks bfcache restore after logout)
function requireAuth() {
    const enforce = () => {
        if (!getCurrentStudent() || localStorage.getItem('skillx_logged_out') === '1') {
            clearCurrentStudent();
            window.location.replace('index.html');
            return false;
        }
        return true;
    };

    enforce();

    // When browser Back/Swipe-Back restores a protected page from bfcache,
    // re-check auth and bounce to login without leaving the page in history.
    if (!window.__skillxAuthPageshowBound) {
        window.__skillxAuthPageshowBound = true;
        window.addEventListener('pageshow', (event) => {
            if (event.persisted || localStorage.getItem('skillx_logged_out') === '1') {
                enforce();
            }
        });
    }
}

// Generic fetch wrapper
async function apiFetch(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            ...options
        });
        const data = await res.json();
        return { ok: res.ok, status: res.status, data };
    } catch (err) {
        return { ok: false, status: 0, data: { error: 'Network error. Is the backend running?' } };
    }
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function ensureFirebaseSignedOut() {
    // 1. If Firebase auth SDK is already initialized on current page
    if (typeof firebase !== 'undefined' && firebase.apps && firebase.apps.length > 0 && firebase.auth) {
        try {
            await firebase.auth().signOut();
        } catch (e) {
            console.warn('Firebase signOut error:', e);
        }
        return;
    }

    // 2. Otherwise, dynamically load Firebase compat SDK, initialize with window.firebaseConfig, and sign out
    const cfg = window.firebaseConfig || (typeof firebaseConfig !== 'undefined' ? firebaseConfig : null);
    if (!cfg || !cfg.apiKey || cfg.apiKey.startsWith('YOUR_')) return;

    try {
        if (typeof firebase === 'undefined') {
            await loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
            await loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js');
        }
        if (typeof firebase !== 'undefined' && firebase.auth) {
            if (!firebase.apps || firebase.apps.length === 0) {
                firebase.initializeApp(cfg);
            }
            await firebase.auth().signOut();
        }
    } catch (err) {
        console.warn('Dynamic Firebase signOut error:', err);
    }
}

// ============================================
// AUTH
// ============================================
const Auth = {
    async login(email, password) {
        return apiFetch('/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },
    async register(payload) {
        return apiFetch('/register', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },
    async logout() {
        // 1. Mark explicit logout flag in localStorage (persists reliably across reloads)
        localStorage.setItem('skillx_logged_out', '1');

        // 2. Clear current student from sessionStorage
        clearCurrentStudent();

        // 3. Clear Flask backend server session
        try { await apiFetch('/logout', { method: 'POST' }); } catch (_) {}

        // 4. Ensure Firebase signOut completes fully before navigating away
        try { await ensureFirebaseSignedOut(); } catch (_) {}

        // 5. Replace current history entry so Back cannot return to this
        //    authenticated page (dashboard/settings/etc.) after logout.
        window.location.replace('index.html');
    }
};

// ============================================
// STUDENTS
// ============================================
const Students = {
    async getAll() {
        return apiFetch('/students');
    },
    async getById(id) {
        return apiFetch(`/students/${id}`);
    },
    async update(id, payload) {
        return apiFetch(`/students/${id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
    }
};

// ============================================
// SKILLS
// ============================================
const Skills = {
    async getAll() {
        return apiFetch('/skills');
    },
    async addSkill(skill_name) {
        return apiFetch('/skills', {
            method: 'POST',
            body: JSON.stringify({ skill_name })
        });
    },
    async addStudentSkill(student_id, skill_id, type) {
        return apiFetch('/student-skills', {
            method: 'POST',
            body: JSON.stringify({ student_id, skill_id, type })
        });
    },
    async removeStudentSkill(id) {
        return apiFetch(`/student-skills/${id}`, { method: 'DELETE' });
    },
    async search(skill, type = 'teach') {
        return apiFetch(`/search?skill=${encodeURIComponent(skill)}&type=${type}`);
    }
};

// ============================================
// EXCHANGE REQUESTS
// ============================================
const Requests = {
    async send(sender_id, receiver_id, skill_id, note = null) {
        return apiFetch('/requests', {
            method: 'POST',
            body: JSON.stringify({ sender_id, receiver_id, skill_id, note })
        });
    },
    async getForStudent(student_id) {
        return apiFetch(`/requests/${student_id}`);
    },
    async updateStatus(request_id, status) {
        return apiFetch(`/requests/${request_id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }
};

// ============================================
// MESSAGES
// ============================================
const Messages = {
    async send(sender_id, receiver_id, message, message_type='text', file_url=null, file_name=null) {
        return apiFetch('/messages', {
            method: 'POST',
            body: JSON.stringify({ sender_id, receiver_id, message, message_type, file_url, file_name })
        });
    },
    async getAll(student_id) {
        return apiFetch(`/messages/${student_id}`);
    },
    async getConversation(student_id, other_id) {
        return apiFetch(`/messages/${student_id}?with=${other_id}`);
    },
    async markRead(student_id, other_id) {
        return apiFetch(`/messages/${student_id}/mark-read`, {
            method: 'PUT', body: JSON.stringify({ other_id })
        });
    }
};

// ============================================
// SHARED CONTENT
// ============================================
const SharedContent = {
    async share(payload) {
        return apiFetch('/shared-content', { method:'POST', body: JSON.stringify(payload) });
    },
    async get(student_id, other_id, type) {
        let url = `/shared-content/${student_id}?with=${other_id}`;
        if (type) url += `&type=${type}`;
        return apiFetch(url);
    },
    async delete(content_id) {
        return apiFetch(`/shared-content/${content_id}`, { method:'DELETE' });
    }
};

// ============================================
// STATS
// ============================================
const Stats = {
    async get() {
        return apiFetch('/stats');
    }
};

// ============================================
// GAMIFICATION & DASHBOARD
// ============================================
const Dashboard = {
    async get(student_id) {
        return apiFetch(`/dashboard/${student_id}`);
    }
};

const Sessions = {
    async schedule(payload) {
        return apiFetch('/sessions', { method: 'POST', body: JSON.stringify(payload) });
    },
    async update(session_id, status) {
        return apiFetch(`/sessions/${session_id}`, { method: 'PUT', body: JSON.stringify({ status }) });
    },
    async confirm(session_id, student_id) {
        return apiFetch(`/sessions/${session_id}/confirm`, {
            method: 'POST', body: JSON.stringify({ student_id })
        });
    }
};

const Gamification = {
    async addXP(student_id, xp, type, description) {
        return apiFetch(`/xp/${student_id}`, {
            method: 'POST',
            body: JSON.stringify({ xp, type, description })
        });
    },
    async updateProgress(student_id, skill_id, progress, hours) {
        return apiFetch(`/progress/${student_id}/${skill_id}`, {
            method: 'PUT',
            body: JSON.stringify({ progress, hours })
        });
    },
    async getLeaderboard() {
        return apiFetch('/leaderboard');
    }
};

// ============================================
// UI HELPERS
// ============================================
function showAlert(container, message, type = 'success') {
    const icons = { success: 'âœ“', error: 'âœ•', info: 'â„¹' };
    container.innerHTML = `
        <div class="alert alert-${type}">
            <span>${icons[type]}</span> ${message}
        </div>`;
    // Keep actionable verification alerts visible longer (buttons / links)
    const sticky = /resend-verify-btn|open-verify-link-btn|verification_link|Verify email|Spam|Promotions/i.test(String(message));
    const ms = sticky ? 60000 : 4000;
    setTimeout(() => {
        // Don't wipe if user already replaced the alert with a newer message
        if (container.innerHTML.includes('alert-' + type)) {
            container.innerHTML = '';
        }
    }, ms);
}

function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

// ============================================
// PROFILE PICTURE HELPERS
// ============================================

/**
 * Returns the URL of the student's current profile picture or avatar.
 * Priority: uploaded photo > avatar emoji > initials fallback
 */
function getProfileDisplay(student) {
    if (!student) return null;
    if (student.profile_pic) {
        // Uploaded photo â€” prepend backend base if relative path
        return { type: 'img', src: student.profile_pic.startsWith('/') ? `${window.location.protocol}//${window.location.hostname}:5000${student.profile_pic}` : student.profile_pic };
    }
    if (student.avatar_key) {
        return { type: 'emoji', emoji: student.avatar_key };
    }
    return { type: 'initials', text: getInitials(student.name) };
}

/**
 * Renders the profile display into any element.
 * el â€” the DOM element (div/span) to render into
 */
function renderProfileInto(el, student) {
    if (!el || !student) return;
    const display = getProfileDisplay(student);
    if (display.type === 'img') {
        el.innerHTML = `<img src="${display.src}" alt="Profile" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" onerror="this.parentElement.textContent='${getInitials(student.name)}'">`;
    } else if (display.type === 'emoji') {
        el.innerHTML = `<span style="font-size:1.4rem;line-height:1;">${display.emoji}</span>`;
    } else {
        el.textContent = display.text;
    }
}

// ============================================
// SETTINGS
// ============================================
const Settings = {
    async get(student_id) {
        return apiFetch(`/settings/${student_id}`);
    },
    async update(student_id, payload) {
        return apiFetch(`/settings/${student_id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
    },
    async updateEmail(student_id, email) {
        return apiFetch(`/students/${student_id}/email`, {
            method: 'PUT',
            body: JSON.stringify({ email })
        });
    },
    async updatePassword(student_id, current_password, new_password) {
        return apiFetch(`/students/${student_id}/password`, {
            method: 'PUT',
            body: JSON.stringify({ current_password, new_password })
        });
    },
    async deleteAccount(student_id) {
        return apiFetch(`/students/${student_id}`, {
            method: 'DELETE'
        });
    }
};

// ============================================
// HELP & SUPPORT
// ============================================
const Support = {
    async create(category, description, student_id) {
        return apiFetch('/support-requests', {
            method: 'POST',
            body: JSON.stringify({ category, description, student_id })
        });
    },
    async getByStudent(student_id) {
        return apiFetch(`/support-requests/${student_id}`);
    }
};

// ============================================
// FEEDBACK
// ============================================
const Feedback = {
    async create(rating, category, message, allow_contact, student_id) {
        return apiFetch('/feedback', {
            method: 'POST',
            body: JSON.stringify({ rating, category, message, allow_contact, student_id })
        });
    },
    async getByStudent(student_id) {
        return apiFetch(`/feedback/${student_id}`);
    }
};



// ============================================
// ADMIN API
// ============================================
const Admin = {
    async getOverview() {
        return apiFetch('/admin/overview');
    },
    async getSupportTickets(filters = {}) {
        const queryParams = new URLSearchParams(filters).toString();
        return apiFetch(`/admin/support-tickets?${queryParams}`);
    },
    async updateTicket(request_id, payload) {
        return apiFetch(`/admin/support-tickets/${request_id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
    },
    async updateTicketStatus(request_id, status) {
        return apiFetch(`/admin/support-tickets/${request_id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    },
    async updateFeedbackStatus(feedback_id, status) {
        return apiFetch(`/admin/feedback/${feedback_id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status })
        });
    }
};

function applyGlobalTheme(theme) {
    if (!theme) theme = localStorage.getItem('skillx_theme') || 'light';
    let isDark = false;
    if (theme === 'dark') {
        isDark = true;
    } else if (theme === 'system') {
        isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    document.documentElement.classList.toggle('dark-mode', isDark);
    document.body.classList.toggle('dark-mode', isDark);
}
applyGlobalTheme();

// Set active nav link
function setActiveNav(page) {
    document.querySelectorAll('.navbar-nav a').forEach(a => {
        a.classList.toggle('active', a.dataset.page === page);
    });
}

// Render navbar user info â€” shows pic/avatar/initials and initializes dropdown
function renderNavUser() {
    const student = getCurrentStudent();
    if (!student) return;
    const nameEl   = document.getElementById('nav-user-name');
    const avatarEl = document.getElementById('nav-avatar');
    if (nameEl)   nameEl.textContent = student.name.split(' ')[0];
    if (avatarEl) renderProfileInto(avatarEl, student);

    const trigger = document.getElementById('user-menu-trigger') || document.querySelector('.user-dropdown-btn');
    const dropdownMenu = document.getElementById('user-dropdown-menu');

    if (student.is_admin && dropdownMenu && !document.getElementById('admin-menu-link')) {
        const adminLink = document.createElement('a');
        adminLink.id = 'admin-menu-link';
        adminLink.href = 'admin.html';
        adminLink.innerHTML = '<span class="icon">ðŸ›¡ï¸</span> Admin Overview';
        dropdownMenu.insertBefore(adminLink, dropdownMenu.firstChild);
    }

    if (trigger && dropdownMenu) {
        trigger.onclick = (e) => {
            e.stopPropagation();
            const isVisible = dropdownMenu.classList.contains('show');
            dropdownMenu.classList.toggle('show', !isVisible);
            trigger.setAttribute('aria-expanded', !isVisible);
        };

        document.addEventListener('click', (e) => {
            if (!trigger.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.remove('show');
                trigger.setAttribute('aria-expanded', 'false');
            }
        });
    }
}
