// ============================================================
//  Real-Time Chat + Shared Content
// ============================================================
requireAuth();
renderNavUser();
setActiveNav('messages');

const student      = getCurrentStudent();
let currentChatId  = null;
let currentChatName= '';
let allStudents    = [];
let conversations  = {};
let pollTimer      = null;
let typingTimer    = null;
let activeContentTab = 'media';
let shareModalType = 'media';
let lastMsgCount   = 0;

// ── Init ─────────────────────────────────────────────────────
async function init() {
    // Mark student online
    await apiFetch(`/online/${student.id}`, { method:'POST', body: JSON.stringify({online:true}) });

    // Load student list for new-chat dropdown
    const studRes = await Students.getAll();
    if (studRes.ok) {
        allStudents = studRes.data.filter(s => s.id !== student.id);
        const sel = document.getElementById('new-chat-select');
        sel.innerHTML = '<option value="">Start new chat...</option>' +
            allStudents.map(s =>
                `<option value="${s.id}" data-name="${s.name}">${s.name} (${s.department || ''})</option>`
            ).join('');
    }

    await loadConversations();

    // Auto-open from URL params (?to=ID&name=NAME)
    const p = new URLSearchParams(window.location.search);
    if (p.get('to')) openChat(parseInt(p.get('to')), decodeURIComponent(p.get('name') || ''));

    // Poll for new messages every 3 seconds
    pollTimer = setInterval(poll, 3000);

    // Mark offline on page leave
    window.addEventListener('beforeunload', () => {
        apiFetch(`/online/${student.id}`, { method:'POST', body: JSON.stringify({online:false}) });
        clearInterval(pollTimer);
    });
}

// ── Polling ──────────────────────────────────────────────────
async function poll() {
    await loadConversations(true);       // silent refresh sidebar
    if (currentChatId) {
        await loadMessages(true);        // silent refresh chat
        await checkTyping();
    }
    await loadUnreadTotal();
}

async function loadUnreadTotal() {
    const res = await apiFetch(`/messages/${student.id}/unread-count`);
    if (!res.ok) return;
    const total = res.data.reduce((s, r) => s + r.cnt, 0);
    const el = document.getElementById('unread-total');
    if (total > 0) { el.textContent = total; el.style.display = 'inline-block'; }
    else            { el.style.display = 'none'; }
}

// ── Conversations Sidebar ─────────────────────────────────────
async function loadConversations(silent = false) {
    const [msgRes, unreadRes] = await Promise.all([
        Messages.getAll(student.id),
        apiFetch(`/messages/${student.id}/unread-count`)
    ]);
    if (!msgRes.ok) return;

    // Build map keyed by partner id
    const prev = conversations;
    conversations = {};
    msgRes.data.forEach(m => {
        const otherId   = m.sender_id === student.id ? m.receiver_id : m.sender_id;
        const otherName = m.sender_id === student.id ? m.receiver_name : m.sender_name;
        if (!conversations[otherId]) {
            conversations[otherId] = {
                id: otherId, name: otherName,
                lastMsg: m.message || '📎 Attachment',
                time: m.timestamp,
                unread: 0
            };
        }
    });

    if (unreadRes.ok) {
        unreadRes.data.forEach(r => {
            if (conversations[r.sender_id]) conversations[r.sender_id].unread = r.cnt;
        });
    }

    renderSidebar();
}

function renderSidebar() {
    const el   = document.getElementById('contacts-list');
    const list = Object.values(conversations);

    if (!list.length) {
        el.innerHTML = `<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.8rem;">
            No conversations yet.<br>Start a new chat below.</div>`;
        return;
    }

    // Check online status for listed contacts
    el.innerHTML = list.map(c => `
        <div class="contact-item ${currentChatId === c.id ? 'active' : ''}"
             id="contact-${c.id}"
             onclick="openChat(${c.id}, '${c.name.replace(/'/g,"\\'")}')">
            <div class="contact-av">
                ${getInitials(c.name)}
                <div class="online-ring offline" id="ring-${c.id}"></div>
            </div>
            <div class="contact-body">
                <div class="contact-name">${c.name}</div>
                <div class="contact-preview">${c.lastMsg}</div>
            </div>
            <div class="contact-meta">
                <span class="contact-time">${c.time ? formatTime(c.time) : ''}</span>
                ${c.unread > 0 ? `<span class="unread-badge">${c.unread}</span>` : ''}
            </div>
        </div>`).join('');

    // Load online status for each contact asynchronously
    list.forEach(c => {
        apiFetch(`/online/${c.id}`).then(res => {
            if (res.ok) {
                const ring = document.getElementById(`ring-${c.id}`);
                if (ring) {
                    ring.className = `online-ring ${res.data.is_online ? 'online' : 'offline'}`;
                }
                // Update header if this is active chat
                if (currentChatId === c.id) updateOnlineHeader(res.data);
            }
        });
    });
}

function filterContacts() {
    const q = document.getElementById('contact-search').value.toLowerCase();
    document.querySelectorAll('.contact-item').forEach(el => {
        const name = el.querySelector('.contact-name').textContent.toLowerCase();
        el.style.display = name.includes(q) ? '' : 'none';
    });
}

// ── Open Chat ─────────────────────────────────────────────────
async function openChat(otherId, otherName) {
    currentChatId   = otherId;
    currentChatName = otherName;

    document.getElementById('no-chat').style.display    = 'none';
    document.getElementById('chat-wrapper').style.display = 'flex';

    document.getElementById('ch-avatar').textContent = getInitials(otherName);
    document.getElementById('ch-name').textContent   = otherName;

    const other = allStudents.find(s => s.id === otherId);
    document.getElementById('ch-status').title = other
        ? `${other.department || ''} • Year ${other.year || ''}` : '';

    showTab('chat');
    renderSidebar();
    await loadMessages();

    // Mark messages as read
    await apiFetch(`/messages/${student.id}/mark-read`, {
        method:'PUT', body: JSON.stringify({ other_id: otherId })
    });

    // Get online status
    const onRes = await apiFetch(`/online/${otherId}`);
    if (onRes.ok) updateOnlineHeader(onRes.data);

    document.getElementById('msg-input').focus();
}

function updateOnlineHeader(data) {
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (data.is_online) {
        dot.className  = 'status-dot online';
        text.textContent = 'Online';
    } else {
        dot.className  = 'status-dot offline';
        const ago = data.last_seen
            ? 'Last seen ' + formatTime(data.last_seen)
            : 'Offline';
        text.textContent = ago;
    }
}

// ── Load Messages ─────────────────────────────────────────────
async function loadMessages(silent = false) {
    const res = await Messages.getConversation(student.id, currentChatId);
    const el  = document.getElementById('chat-msgs');

    if (!res.ok || !res.data.length) {
        if (!silent) {
            el.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px 0;">
                <div style="font-size:2.5rem;opacity:0.3;">👋</div>
                <p>Say hello to ${currentChatName}!</p>
            </div>`;
        }
        return;
    }

    // Only re-render if count changed (avoid flicker during polling)
    if (silent && res.data.length === lastMsgCount) return;
    lastMsgCount = res.data.length;

    // Group messages by date
    const groups = {};
    res.data.forEach(m => {
        const day = m.timestamp ? m.timestamp.split('T')[0] : 'Today';
        if (!groups[day]) groups[day] = [];
        groups[day].push(m);
    });

    el.innerHTML = Object.entries(groups).map(([day, msgs]) => `
        <div class="date-sep">${formatDateSep(day)}</div>
        ${msgs.map(m => renderMessage(m)).join('')}
    `).join('');

    el.scrollTop = el.scrollHeight;
}

function renderMessage(m) {
    const isSent = m.sender_id === student.id;
    const side   = isSent ? 'sent' : 'received';
    const time   = m.timestamp ? formatTime(m.timestamp) : '';
    const seen   = isSent
        ? `<span class="seen-tick ${m.is_read ? 'seen' : ''}">✓✓</span>` : '';

    let content = '';
    const type = m.message_type || 'text';

    if (type === 'text') {
        // Auto-detect URLs in text
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const escaped  = (m.message || '').replace(/</g,'&lt;');
        content = escaped.replace(urlRegex,
            url => `<a href="${url}" target="_blank" rel="noopener" style="color:${isSent?'#fff':'var(--primary)'};text-decoration:underline;">${url}</a>`
        );
    } else if (type === 'link') {
        content = `${m.message || ''}
            <div class="msg-link-preview">
                🔗 <a href="${m.file_url}" target="_blank" rel="noopener">${m.file_url}</a>
            </div>`;
    } else if (type === 'image') {
        content = `${m.message || ''}
            <div class="msg-media"><img src="${m.file_url}" alt="${m.file_name||'image'}" onerror="this.style.display='none'"></div>`;
    } else if (['video','audio','document','pdf'].includes(type)) {
        const icons = {video:'🎬',audio:'🎵',document:'📄',pdf:'📋'};
        content = `${m.message || ''}
            <div class="msg-file-bubble">
                <span class="file-icon">${icons[type]||'📎'}</span>
                <div class="file-info"><b>${m.file_name || 'File'}</b>
                ${m.file_url ? `<a href="${m.file_url}" target="_blank" style="color:${isSent?'#fff':'var(--primary)'};">Open →</a>` : ''}
                </div>
            </div>`;
    } else {
        content = m.message || '';
    }

    return `
    <div class="msg-row ${side}">
        <div class="msg-group">
            <div class="msg-bubble">${content}</div>
            <div class="msg-meta">
                <span>${time}</span>${seen}
            </div>
        </div>
    </div>`;
}

function formatDateSep(dateStr) {
    const d     = new Date(dateStr);
    const today = new Date();
    const yest  = new Date(); yest.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return 'Today';
    if (d.toDateString() === yest.toDateString())  return 'Yesterday';
    return d.toLocaleDateString('en-IN', {day:'numeric',month:'short',year:'numeric'});
}

// ── Send Message ──────────────────────────────────────────────
async function sendMsg() {
    const input = document.getElementById('msg-input');
    const text  = input.value.trim();
    if (!text || !currentChatId) return;
    input.value = '';

    // Detect if it's a URL-only message
    const isUrl = /^https?:\/\/\S+$/.test(text);
    const res = await Messages.send(
        student.id, currentChatId, text,
        isUrl ? 'link' : 'text',
        isUrl ? text : null
    );
    if (res.ok) {
        // Stop typing indicator
        clearTyping();
        await loadMessages();
        await loadConversations(true);
    }
}

// ── Typing Indicator ──────────────────────────────────────────
async function onTyping() {
    if (!currentChatId) return;
    // Send typing start
    await apiFetch('/typing', { method:'POST', body: JSON.stringify({
        student_id: student.id, typing_to: currentChatId, is_typing: true
    })});
    // Auto-stop after 3s of inactivity
    clearTimeout(typingTimer);
    typingTimer = setTimeout(clearTyping, 3000);
}

async function clearTyping() {
    if (!currentChatId) return;
    await apiFetch('/typing', { method:'POST', body: JSON.stringify({
        student_id: student.id, typing_to: currentChatId, is_typing: false
    })});
}

async function checkTyping() {
    if (!currentChatId) return;
    const res = await apiFetch(`/typing/${student.id}/${currentChatId}`);
    const el  = document.getElementById('typing-ind');
    if (res.ok && res.data.is_typing) {
        document.getElementById('typing-name').textContent = currentChatName;
        el.style.display = 'flex';
    } else {
        el.style.display = 'none';
    }
}

// ── Tab switching ─────────────────────────────────────────────
function showTab(tab) {
    document.getElementById('tab-chat').style.display    = tab === 'chat'    ? 'flex' : 'none';
    document.getElementById('tab-content').style.display = tab === 'content' ? 'flex' : 'none';
    document.getElementById('tab-chat-btn').classList.toggle('active', tab === 'chat');
    document.getElementById('tab-content-btn').classList.toggle('active', tab === 'content');

    if (tab === 'content') loadSharedContent(activeContentTab);
}

function switchContentTab(type, btn) {
    activeContentTab = type;
    document.querySelectorAll('.ctab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadSharedContent(type);
}

// ── Shared Content ────────────────────────────────────────────
async function loadSharedContent(type) {
    const el  = document.getElementById('content-list');
    el.innerHTML = '<div class="loading-overlay"><div class="spinner"></div></div>';

    const url = `/shared-content/${student.id}?with=${currentChatId}&type=${type}`;
    const res = await apiFetch(url);
    if (!res.ok || !res.data.length) {
        const labels = {media:'videos, audio or images',document:'PDFs, notes or slides',link:'YouTube links, courses or websites'};
        el.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted);">
            <div style="font-size:2.5rem;opacity:0.3;">${type==='media'?'🎬':type==='document'?'📄':'🔗'}</div>
            <p>No shared ${labels[type]} yet.<br>Use the 📎 button to share content.</p>
        </div>`;
        return;
    }

    const icons = {
        video:'🎬',audio:'🎵',image:'🖼️',pdf:'📋',notes:'📝',
        word:'📝',presentation:'📊',youtube:'▶️',course:'🎓',
        website:'🌐',resource:'🔖'
    };

    el.innerHTML = res.data.map(item => `
        <div class="content-item">
            <div class="content-icon ci-${item.content_type}">
                ${icons[item.media_type] || (item.content_type==='media'?'🎬':item.content_type==='document'?'📄':'🔗')}
            </div>
            <div class="content-body">
                <div class="content-title">${item.title}</div>
                <div class="content-meta">
                    Shared by <strong>${item.sender_name}</strong> &nbsp;·&nbsp;
                    ${formatDate(item.shared_at)}
                    ${item.file_size ? ` &nbsp;·&nbsp; ${item.file_size}` : ''}
                </div>
                ${item.description ? `<div class="content-desc">${item.description}</div>` : ''}
                <div class="content-actions">
                    ${item.file_url
                        ? `<a href="${item.file_url}" target="_blank" class="btn btn-primary btn-sm">
                               ${item.content_type==='link' ? '🔗 Open Link' : '⬇️ Open / Download'}
                           </a>`
                        : `<span class="btn btn-secondary btn-sm" style="cursor:default;">📎 File shared in class</span>`
                    }
                    ${item.sender_id === student.id
                        ? `<button class="btn btn-danger btn-sm" onclick="deleteContent(${item.content_id})">🗑️</button>`
                        : ''}
                </div>
            </div>
        </div>`).join('');
}

async function deleteContent(id) {
    if (!confirm('Remove this shared content?')) return;
    const res = await apiFetch(`/shared-content/${id}`, { method:'DELETE' });
    if (res.ok) loadSharedContent(activeContentTab);
}

// ── Share Modal ───────────────────────────────────────────────
const MEDIA_SUBTYPES = {
    media:    [{v:'video','l':'🎬 Video'},{v:'audio','l':'🎵 Audio'},{v:'image','l':'🖼️ Image'}],
    document: [{v:'pdf','l':'📋 PDF'},{v:'notes','l':'📝 Notes'},{v:'word','l':'📝 Word Doc'},{v:'presentation','l':'📊 Presentation'}],
    link:     [{v:'youtube','l':'▶️ YouTube'},{v:'course','l':'🎓 Course'},{v:'website','l':'🌐 Website'},{v:'resource','l':'🔖 Resource'}],
};

function openShareModal(type) {
    shareModalType = type;
    toggleAttachMenu();
    const titles = {media:'🎬 Share Media', document:'📄 Share Document', link:'🔗 Share Link'};
    document.getElementById('share-modal-title').textContent = titles[type];
    document.getElementById('share-alert').innerHTML = '';

    const subtypes = MEDIA_SUBTYPES[type];
    const isLink   = type === 'link';

    document.getElementById('share-fields').innerHTML = `
        <div class="form-group">
            <label>Title</label>
            <input type="text" class="form-control" id="sh-title" placeholder="Give it a clear title...">
        </div>
        <div class="form-group">
            <label>Type</label>
            <select class="form-control" id="sh-subtype">
                ${subtypes.map(s => `<option value="${s.v}">${s.l}</option>`).join('')}
            </select>
        </div>
        ${isLink ? `
        <div class="form-group">
            <label>URL / Link</label>
            <input type="url" class="form-control" id="sh-url" placeholder="https://...">
        </div>` : `
        <div class="form-group">
            <label>File URL (paste Google Drive / OneDrive link)</label>
            <input type="url" class="form-control" id="sh-url" placeholder="https://drive.google.com/...">
        </div>
        <div class="form-group">
            <label>File Name</label>
            <input type="text" class="form-control" id="sh-fname" placeholder="e.g. lecture_notes.pdf">
        </div>
        <div class="form-group">
            <label>File Size (optional)</label>
            <input type="text" class="form-control" id="sh-fsize" placeholder="e.g. 2.4 MB">
        </div>`}
        <div class="form-group">
            <label>Description (optional)</label>
            <textarea class="form-control" id="sh-desc" rows="2" placeholder="Add a note..."></textarea>
        </div>`;

    document.getElementById('share-modal').classList.add('active');
}

function closeShareModal() {
    document.getElementById('share-modal').classList.remove('active');
}

async function submitShare() {
    const title   = document.getElementById('sh-title')?.value.trim();
    const subtype = document.getElementById('sh-subtype')?.value;
    const url     = document.getElementById('sh-url')?.value.trim();
    const fname   = document.getElementById('sh-fname')?.value.trim();
    const fsize   = document.getElementById('sh-fsize')?.value.trim();
    const desc    = document.getElementById('sh-desc')?.value.trim();
    const alertEl = document.getElementById('share-alert');

    if (!title) { showAlert(alertEl,'Please enter a title','error'); return; }

    const payload = {
        sender_id: student.id, receiver_id: currentChatId,
        title, content_type: shareModalType, media_type: subtype,
        file_url: url || null, file_name: fname || null,
        file_size: fsize || null, description: desc || ''
    };

    const res = await apiFetch('/shared-content', { method:'POST', body: JSON.stringify(payload) });
    if (res.ok) {
        // Also send a chat notification
        await Messages.send(student.id, currentChatId,
            `📎 Shared: ${title}`, 'text', null);
        showAlert(alertEl,'Content shared successfully!','success');
        setTimeout(() => {
            closeShareModal();
            showTab('content');
            switchContentTab(shareModalType, document.querySelector(`.ctab:nth-child(${shareModalType==='media'?1:shareModalType==='document'?2:3})`));
        }, 1000);
    } else {
        showAlert(alertEl, res.data.error || 'Failed to share','error');
    }
}

function toggleAttachMenu() {
    const m = document.getElementById('attach-menu');
    m.style.display = m.style.display === 'none' ? 'block' : 'none';
}

// Close attach menu on outside click
document.addEventListener('click', e => {
    if (!e.target.closest('.attach-btn') && !e.target.closest('.attach-menu')) {
        const m = document.getElementById('attach-menu');
        if (m) m.style.display = 'none';
    }
});

function startNewChat() {
    const sel  = document.getElementById('new-chat-select');
    const id   = parseInt(sel.value);
    const name = sel.options[sel.selectedIndex]?.dataset?.name;
    if (!id || !name) return;
    sel.value = '';
    openChat(id, name);
}

// Extend Messages API to support message_type + file_url
const _origSend = Messages.send.bind(Messages);
Messages.send = async (sender_id, receiver_id, message, message_type='text', file_url=null, file_name=null) => {
    return apiFetch('/messages', {
        method: 'POST',
        body: JSON.stringify({ sender_id, receiver_id, message, message_type, file_url, file_name })
    });
};

init();
