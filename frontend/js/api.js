// ============================================
// API Helper - All backend calls go here
// ============================================

const API_BASE = 'http://localhost:5000/api';

// Current logged-in student (stored in sessionStorage)
function getCurrentStudent() {
    const data = sessionStorage.getItem('student');
    return data ? JSON.parse(data) : null;
}

function setCurrentStudent(student) {
    sessionStorage.setItem('student', JSON.stringify(student));
}

function clearCurrentStudent() {
    sessionStorage.removeItem('student');
}

// Redirect to login if not authenticated
function requireAuth() {
    if (!getCurrentStudent()) {
        window.location.href = 'index.html';
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
        clearCurrentStudent();
        await apiFetch('/logout', { method: 'POST' });
        window.location.href = 'index.html';
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
    async send(sender_id, receiver_id, skill_id) {
        return apiFetch('/requests', {
            method: 'POST',
            body: JSON.stringify({ sender_id, receiver_id, skill_id })
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
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    container.innerHTML = `
        <div class="alert alert-${type}">
            <span>${icons[type]}</span> ${message}
        </div>`;
    setTimeout(() => { container.innerHTML = ''; }, 4000);
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

// Set active nav link
function setActiveNav(page) {
    document.querySelectorAll('.navbar-nav a').forEach(a => {
        a.classList.toggle('active', a.dataset.page === page);
    });
}

// Render navbar user info
function renderNavUser() {
    const student = getCurrentStudent();
    if (!student) return;
    const el = document.getElementById('nav-user-name');
    const av = document.getElementById('nav-avatar');
    if (el) el.textContent = student.name.split(' ')[0];
    if (av) av.textContent = getInitials(student.name);
}
