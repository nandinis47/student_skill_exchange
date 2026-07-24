// ============================================================
//  Dashboard JS — all features
// ============================================================
requireAuth();
renderNavUser();
setActiveNav('dashboard');

const student = getCurrentStudent();

// ── Init ────────────────────────────────────────────────────
async function initDashboard() {
    document.getElementById('welcome-name').textContent = student.name.split(' ')[0];
    document.getElementById('welcome-dept').textContent = `${student.department} • Year ${student.year}`;
    document.getElementById('wb-avatar').textContent = getInitials(student.name);

    // Load global stats and full dashboard data in parallel
    const [statsRes, dashRes, reqRes] = await Promise.all([
        Stats.get(),
        Dashboard.get(student.id),
        Requests.getForStudent(student.id)
    ]);

    if (statsRes.ok) renderStats(statsRes.data);
    if (dashRes.ok)  renderAll(dashRes.data);
    if (reqRes.ok)   renderRecentRequests(reqRes.data);
}

// ── Stats Cards ─────────────────────────────────────────────
function renderStats(data) {
    document.getElementById('stat-students').textContent = data.total_students;
    document.getElementById('stat-skills').textContent   = data.total_skills;
}

// ── Master render ────────────────────────────────────────────
function renderAll(d) {
    renderWelcomeBanner(d.student);
    renderTodaysFocus(d.student);
    renderJourney(d.analytics);
    renderStatCards(d.analytics);
    renderSkillProgress(d.skill_progress);
    renderSmartMatches(d.smart_matches);
    renderSkillOfDay(d.skill_of_day);
    renderRecommended(d.recommended);
    renderExchangeMap(d.smart_matches);
    renderSessions(d.sessions);
    renderWeeklyActivity(d.weekly_activity, d.analytics);
    renderBadges(d.badges);
    renderLeaderboard(d.leaderboard);
}

// ── Welcome Banner ───────────────────────────────────────────
function renderWelcomeBanner(s) {
    const maxXP = 200;
    const pct   = Math.min(100, Math.round((s.xp_points / maxXP) * 100));
    document.getElementById('xp-fill').style.width = pct + '%';
    document.getElementById('xp-label').textContent = s.xp_points + ' XP';
    document.getElementById('streak-num').textContent = s.learning_streak || 0;
}

// ── Today's Focus ────────────────────────────────────────────
function renderTodaysFocus(s) {
    const goal = s.daily_goal || 'Set a learning goal for today!';
    document.getElementById('focus-goal').textContent = '🎯 ' + goal;

    // Check streak freshness
    const lastDate = s.last_activity_date ? new Date(s.last_activity_date) : null;
    const today    = new Date();
    const isToday  = lastDate &&
        lastDate.toDateString() === today.toDateString();

    document.getElementById('focus-meta').textContent = isToday
        ? '✅ You\'ve been active today! Keep it up.'
        : '⏰ You haven\'t logged activity today yet. Complete your goal!';
}

// ── Analytics Stat Cards ─────────────────────────────────────
function renderStatCards(a) {
    document.getElementById('stat-exchanges').textContent = a.exchanges_done;
    document.getElementById('stat-hours').textContent = a.total_hours.toFixed(1) + 'h';
}

// ── Skill Journey ────────────────────────────────────────────
function renderJourney(a) {
    // Unlock steps based on activity
    if (a.total_hours > 1)       document.getElementById('js-practicing').classList.add('active');
    if (a.skills_teaching > 0)   document.getElementById('js-teaching').classList.add('active');
    if (a.exchanges_done > 0)    document.getElementById('js-exchanging').classList.add('active');
    if (a.exchanges_done >= 3 && a.skills_teaching >= 2)
                                 document.getElementById('js-mastery').classList.add('active');
}

// ── Skill Progress Bars ──────────────────────────────────────
function renderSkillProgress(items) {
    const el = document.getElementById('skill-progress-list');
    if (!items || !items.length) {
        el.innerHTML = `<div class="empty-state" style="padding:20px 0;">
            <div class="empty-icon">📈</div>
            <p>Add skills you want to learn to track progress</p>
            <a href="skills.html" class="btn btn-primary btn-sm" style="margin-top:8px;">Add Skills</a>
        </div>`;
        return;
    }
    el.innerHTML = items.slice(0, 5).map(item => {
        const pct   = item.progress_percent;
        const cls   = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low';
        return `
        <div class="progress-item">
            <div class="progress-header">
                <span class="progress-name">📚 ${item.skill_name}</span>
                <span class="progress-pct">${pct}%</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill ${cls}" style="width:0%" data-target="${pct}"></div>
            </div>
            <div class="progress-hours">⏱ ${item.hours_spent}h spent · Last: ${item.last_practiced || 'N/A'}</div>
        </div>`;
    }).join('');

    // Animate bars after render
    setTimeout(() => {
        document.querySelectorAll('.progress-fill').forEach(bar => {
            bar.style.width = bar.dataset.target + '%';
        });
    }, 100);
}

// ── Smart Matches ────────────────────────────────────────────
function renderSmartMatches(matches) {
    const el = document.getElementById('smart-matches-list');
    if (!matches || !matches.length) {
        el.innerHTML = `<div class="empty-state" style="padding:20px 0;">
            <div class="empty-icon">🤝</div>
            <p>Add skills you want to learn to see matches</p>
        </div>`;
        return;
    }
    el.innerHTML = matches.map(m => `
        <div class="match-card" onclick="location.href='search.html'">
            <div class="match-left">
                <div class="student-avatar" style="width:40px;height:40px;font-size:0.85rem;">
                    ${getInitials(m.name)}
                </div>
                <div class="match-info">
                    <h4>👤 ${m.name}</h4>
                    <p>🎓 Can teach: ${m.skill_name} · ${m.department}</p>
                    <p>🎯 Wants to learn what you know</p>
                </div>
            </div>
            <div class="match-pct">${m.match_percent}% match</div>
        </div>
    `).join('');
}

// ── Skill of the Day ─────────────────────────────────────────
function renderSkillOfDay(s) {
    if (!s) return;
    document.getElementById('sod-skill').textContent = s.skill_name;
    document.getElementById('sod-meta').textContent =
        `${s.learner_count} student${s.learner_count !== 1 ? 's' : ''} are currently offering this skill`;
    document.getElementById('sod-btn').href =
        `search.html?skill=${encodeURIComponent(s.skill_name)}`;
}

// ── Recommended ──────────────────────────────────────────────
const REC_ICONS = ['💻','⚡','🗄️','🎨','🤖','📱','☁️','🔒'];
function renderRecommended(items) {
    const el = document.getElementById('recommended-list');
    if (!items || !items.length) {
        el.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">Add skills to get recommendations</p>';
        return;
    }
    el.innerHTML = `<p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:10px;">
        Based on what other learners are exploring:</p>` +
        items.map((item, i) => `
        <div class="rec-item" onclick="location.href='search.html'">
            <div class="rec-left">
                <div class="rec-icon">${REC_ICONS[i % REC_ICONS.length]}</div>
                <div>
                    <div class="rec-name">${item.skill_name}</div>
                    <div class="rec-count">${item.popularity} learners exploring this</div>
                </div>
            </div>
            <button class="btn btn-outline btn-sm">Explore</button>
        </div>
    `).join('');
}

// ── Exchange Map ─────────────────────────────────────────────
function renderExchangeMap(matches) {
    const el = document.getElementById('exchange-map');
    if (!matches || !matches.length) {
        el.innerHTML = `<div class="empty-state" style="padding:20px 0;">
            <div class="empty-icon">🗺️</div>
            <p>Your exchange network will appear here once you connect with students</p>
        </div>`;
        return;
    }

    const colors = ['#34a853','#ea4335','#fbbc04','#9c27b0','#00bcd4'];
    let html = `
        <div class="map-node">
            <div class="map-node-circle you">${getInitials(student.name)}</div>
            <div class="map-node-label">You</div>
        </div>`;

    matches.slice(0, 4).forEach((m, i) => {
        html += `
        <div class="map-connector">
            <div class="map-conn-skill">📚 ${m.skill_name}</div>
            <div class="map-arrow">⇄</div>
        </div>
        <div class="map-node" onclick="location.href='search.html'">
            <div class="map-node-circle" style="background:linear-gradient(135deg,${colors[i]},${colors[(i+1)%colors.length]});">
                ${getInitials(m.name)}
            </div>
            <div class="map-node-label">${m.name.split(' ')[0]}</div>
        </div>`;
    });

    el.innerHTML = html;
}

// ── Sessions ─────────────────────────────────────────────────
function renderSessions(sessions) {
    const el = document.getElementById('sessions-list');
    if (!sessions || !sessions.length) {
        el.innerHTML = `<div class="empty-state" style="padding:20px 0;">
            <div class="empty-icon">📅</div>
            <h3>No upcoming sessions</h3>
            <p>Schedule a session with a learning partner</p>
        </div>`;
        return;
    }
    el.innerHTML = sessions.map(s => {
        const d   = new Date(s.session_date);
        const day = d.getDate();
        const mon = d.toLocaleString('en', { month: 'short' }).toUpperCase();
        const tim = d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' });
        return `
        <div class="session-item">
            <div class="session-left">
                <div class="session-date-box">
                    <span class="session-day">${day}</span>
                    <span class="session-month">${mon}</span>
                </div>
                <div class="session-info">
                    <h4>📚 ${s.skill_name}</h4>
                    <p>${s.partner_name ? '👤 with ' + s.partner_name : 'Solo session'} · ${tim} · ${s.duration_minutes}min</p>
                </div>
            </div>
            <button class="btn btn-success btn-sm"
                    onclick="joinSession(${s.session_id})">Join</button>
        </div>`;
    }).join('');
}

// ── Weekly Activity Chart ────────────────────────────────────
function renderWeeklyActivity(activity, analytics) {
    const el    = document.getElementById('weekly-chart');
    const days  = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const today = new Date();
    const week  = [];

    for (let i = 6; i >= 0; i--) {
        const d   = new Date(today);
        d.setDate(today.getDate() - i);
        const key = d.toISOString().split('T')[0];
        const found = activity && activity.find(a => a.day && a.day.startsWith(key));
        week.push({ label: days[d.getDay()], count: found ? found.cnt : 0 });
    }

    const max = Math.max(...week.map(w => w.count), 1);
    el.innerHTML = week.map(w => {
        const h = Math.max(8, Math.round((w.count / max) * 72));
        return `
        <div class="chart-bar-wrap">
            <div class="chart-bar ${w.count > 0 ? 'has-data' : ''}" style="height:${h}px;" title="${w.count} activities"></div>
            <span class="chart-label">${w.label}</span>
        </div>`;
    }).join('');

    document.getElementById('analytics-mini').innerHTML = `
        <div class="anal-box"><h4>${analytics.skills_learning}</h4><p>Skills Learning</p></div>
        <div class="anal-box"><h4>${analytics.skills_teaching}</h4><p>Skills Teaching</p></div>
        <div class="anal-box"><h4>${analytics.exchanges_done}</h4><p>Exchanges Done</p></div>
        <div class="anal-box"><h4>${analytics.total_hours.toFixed(0)}h</h4><p>Hours Learned</p></div>
    `;
}

// ── Badges ───────────────────────────────────────────────────
const BADGE_ICONS = {
    seedling: '🌱', handshake: '🤝', zap: '⚡',
    teacher: '👨‍🏫', fire: '🔥', butterfly: '🦋',
    books: '📚', trophy: '🏆'
};
function renderBadges(badges) {
    const el = document.getElementById('badges-grid');
    if (!badges || !badges.length) {
        el.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No badges yet — start earning XP!</p>';
        return;
    }

    // Show earned badges + locked placeholders
    const allBadges = [
        {badge_name:'Newbie',badge_icon:'seedling'},
        {badge_name:'First Exchange',badge_icon:'handshake'},
        {badge_name:'Quick Learner',badge_icon:'zap'},
        {badge_name:'Master Teacher',badge_icon:'teacher'},
        {badge_name:'Streak Master',badge_icon:'fire'},
        {badge_name:'Social Butterfly',badge_icon:'butterfly'},
        {badge_name:'Knowledge Seeker',badge_icon:'books'},
        {badge_name:'Community Hero',badge_icon:'trophy'},
    ];

    const earnedNames = badges.map(b => b.badge_name);
    el.innerHTML = allBadges.map(b => {
        const earned = earnedNames.includes(b.badge_name);
        return `
        <div class="badge-item ${earned ? '' : 'badge-locked'}" title="${b.badge_name}${earned ? ' (Earned!)' : ' (Locked)'}">
            <span class="bi-icon">${BADGE_ICONS[b.badge_icon] || '🏅'}</span>
            <span class="bi-name">${b.badge_name}</span>
            ${earned ? '<span class="bi-xp" style="color:var(--secondary);">✓ Earned</span>' : '<span class="bi-xp">🔒 Locked</span>'}
        </div>`;
    }).join('');
}

// ── Leaderboard ───────────────────────────────────────────────
function renderLeaderboard(leaders) {
    const el = document.getElementById('leaderboard-list');
    if (!leaders || !leaders.length) {
        el.innerHTML = '<p style="color:var(--text-muted);">No data yet</p>';
        return;
    }
    const rankCls = ['gold','silver','bronze'];
    const rankIcon = ['🥇','🥈','🥉'];
    el.innerHTML = leaders.map((l, i) => {
        const isMe = l.id === student.id;
        const rank = i < 3 ? rankCls[i] : '';
        return `
        <div class="lb-item ${isMe ? 'me' : ''}">
            <div class="lb-rank ${rank}">${rankIcon[i] || (i+1)}</div>
            <div class="student-avatar" style="width:32px;height:32px;font-size:0.72rem;flex-shrink:0;">
                ${getInitials(l.name)}
            </div>
            <div class="lb-info">
                <h4>${l.name}${isMe ? ' (You)' : ''}</h4>
                <p>${l.department} · 🔥 ${l.learning_streak}d streak · 🤝 ${l.exchanges} exchanges</p>
            </div>
            <div class="lb-xp">⭐ ${l.xp_points}</div>
        </div>`;
    }).join('');
}

// ── Recent Requests ───────────────────────────────────────────
function renderRecentRequests(data) {
    const el = document.getElementById('recent-requests');
    if (!data || !data.length) {
        el.innerHTML = `<div class="empty-state">
            <div class="empty-icon">📭</div>
            <h3>No requests yet</h3>
            <p>Search for students and send exchange requests</p>
        </div>`;
        return;
    }
    el.innerHTML = `<div style="display:flex;flex-direction:column;gap:8px;">
        ${data.slice(0, 5).map(r => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:var(--bg);border-radius:var(--radius-sm);border:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:10px;">
                <div class="student-avatar" style="width:36px;height:36px;font-size:0.8rem;">
                    ${getInitials(r.sender_id === student.id ? r.receiver_name : r.sender_name)}
                </div>
                <div>
                    <div style="font-size:0.875rem;font-weight:500;">
                        ${r.sender_id === student.id ? 'You → ' + r.receiver_name : r.sender_name + ' → You'}
                    </div>
                    <div style="font-size:0.8rem;color:var(--text-muted);">
                        ${r.skill_name} · ${formatDate(r.created_at)}
                    </div>
                </div>
            </div>
            <span class="badge badge-${r.status}">${r.status}</span>
        </div>`).join('')}
    </div>`;
}

// ── Mark Focus Done (add XP) ──────────────────────────────────
async function markFocusDone() {
    const res = await Gamification.addXP(student.id, 10, 'milestone', 'Completed daily goal');
    if (res.ok) {
        document.getElementById('xp-label').textContent = res.data.xp_points + ' XP';
        document.getElementById('focus-meta').textContent = '🎉 Great job! +10 XP earned today!';
    }
}

// ── Session Join ─────────────────────────────────────────────
async function joinSession(id) {
    await Sessions.update(id, 'completed');
    await Gamification.addXP(student.id, 20, 'exchange_completed', 'Completed a learning session');
    alert('Session marked complete! +20 XP earned 🎉');
    initDashboard();
}

// ── Schedule Session Modal ────────────────────────────────────
async function openScheduleModal() {
    document.getElementById('schedule-modal').classList.add('active');

    // Load skills and partners
    const [skillsRes, studentsRes] = await Promise.all([Skills.getAll(), Students.getAll()]);

    if (skillsRes.ok) {
        document.getElementById('sess-skill').innerHTML =
            '<option value="">Select skill...</option>' +
            skillsRes.data.map(s => `<option value="${s.skill_id}">${s.skill_name}</option>`).join('');
    }
    if (studentsRes.ok) {
        const others = studentsRes.data.filter(s => s.id !== student.id);
        document.getElementById('sess-partner').innerHTML =
            '<option value="">Solo session</option>' +
            others.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    }

    // Set default date to now + 1 hour
    const dt = new Date(Date.now() + 3600000);
    dt.setMinutes(0);
    document.getElementById('sess-datetime').value =
        dt.toISOString().slice(0, 16);
}

function closeScheduleModal() {
    document.getElementById('schedule-modal').classList.remove('active');
}

async function saveSession() {
    const skill_id    = document.getElementById('sess-skill').value;
    const partner_id  = document.getElementById('sess-partner').value || null;
    const session_date= document.getElementById('sess-datetime').value;
    const duration    = document.getElementById('sess-duration').value;
    const alertEl     = document.getElementById('sess-alert');

    if (!skill_id || !session_date) {
        showAlert(alertEl, 'Please fill in skill and date/time', 'error'); return;
    }

    const res = await Sessions.schedule({
        student_id: student.id, partner_id, skill_id, session_date, duration_minutes: duration
    });
    if (res.ok) {
        showAlert(alertEl, 'Session scheduled! +5 XP', 'success');
        await Gamification.addXP(student.id, 5, 'milestone', 'Scheduled a learning session');
        setTimeout(() => { closeScheduleModal(); initDashboard(); }, 1200);
    } else {
        showAlert(alertEl, res.data.error || 'Failed to schedule', 'error');
    }
}

// ── SkillBot ─────────────────────────────────────────────────
function toggleSkillBot() {
    document.getElementById('skillbot-panel').classList.toggle('open');
}

const botResponses = {
    keywords: {
        'python':      '🐍 Python is great for ML & automation! I found 3 students who can teach Python. Go to Search → type "Python".',
        'partner':     '🤝 To find a partner, go to the Search page and filter by skill. You can send Exchange Requests directly!',
        'streak':      '🔥 Your streak grows when you log daily activity. Click "Done for Today" every day to keep it going!',
        'xp':          '⭐ Earn XP by: completing goals (+10), scheduling sessions (+5), finishing exchanges (+20), earning badges (+25)!',
        'badge':       '🏅 Badges are unlocked by reaching milestones — try completing your first exchange to earn "First Exchange"!',
        'help':        '💡 I can help with: finding partners, explaining features, skill tips, or creating a learning plan. Just ask!',
        'learn':       '📚 To add learning skills, go to "My Skills" page and select skills you want to learn.',
        'teach':       '🎓 To add teaching skills, go to "My Skills" page and select skills you can teach.',
        'request':     '📋 You can send exchange requests from the Search page — click any student card to see their skills.',
        'message':     '💬 You can message any student from their profile or after connecting on the Requests page.',
        'plan':        '📅 For a learning plan: 1) Add skills to learn, 2) Find a teacher in Search, 3) Schedule a session, 4) Exchange!',
        'leaderboard': '🏆 Earn more XP to climb the leaderboard! Complete exchanges, log daily activity, and earn badges.',
    },
    default: [
        "🤔 I'm not sure about that! Try asking about: skills, partners, streaks, XP, badges, or learning plans.",
        "💡 Tip: Go to the Search page to find students by skill and send exchange requests!",
        "🎯 Focus on your daily goal today! Every step counts toward your streak.",
        "🤝 The best way to learn is to teach! Add skills you can share with others."
    ]
};

function sendBotMsg() {
    const input  = document.getElementById('bot-input');
    const text   = input.value.trim();
    if (!text) return;

    const msgBox = document.getElementById('bot-messages');
    input.value  = '';

    // Add user message
    msgBox.innerHTML += `<div class="user-msg">${text}</div>`;

    // Find response
    const lower = text.toLowerCase();
    let reply = null;
    for (const [kw, resp] of Object.entries(botResponses.keywords)) {
        if (lower.includes(kw)) { reply = resp; break; }
    }
    if (!reply) {
        reply = botResponses.default[Math.floor(Math.random() * botResponses.default.length)];
    }

    setTimeout(() => {
        msgBox.innerHTML += `<div class="bot-msg">${reply}</div>`;
        msgBox.scrollTop = msgBox.scrollHeight;
    }, 400);

    msgBox.scrollTop = msgBox.scrollHeight;
}

// ── Run ───────────────────────────────────────────────────────
initDashboard();
