// ============================================================
//  Messages v3 — Grouped sidebar, Emoji/GIF/Sticker, Date seps
// ============================================================
requireAuth();
renderNavUser();
setActiveNav('messages');

const student = getCurrentStudent();
let currentChatId   = null;
let currentChatName = '';
let allStudents     = [];
let conversations   = {};
let pollTimer       = null;
let typingTimer     = null;
let activeContentTab  = 'media';
let shareModalType    = 'media';
let lastMsgCount      = 0;
let espOpen           = false;
let currentEspTab     = 'emoji';
let recentEmojis      = JSON.parse(localStorage.getItem('recentEmojis') || '[]');
let currentStickerPack= 0;

// ── EMOJI DATA ──────────────────────────────────────────────
const EMOJI_CATS = [
    { icon:'😊', label:'Smileys',  emojis:['😀','😁','😂','🤣','😃','😄','😅','😆','😇','😉','😊','😋','😎','😍','🥰','😘','😗','😙','😚','🙂','🤗','🤩','🤔','🤨','😐','😑','😶','🙄','😏','😣','😥','😮','🤐','😯','😪','😫','🥱','😴','😌','😛','😜','😝','🤤','😒','😓','😔','😕','🙃','🤑','😲','☹️','🙁','😖','😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯','😬','😰','😱','🥵','🥶','😳','🤪','😵','🥴','😷','🤒','🤕','🤢','🤮','🤧','🥳'] },
    { icon:'👋', label:'People',   emojis:['👋','🤚','🖐','✋','🖖','👌','🤌','🤏','✌️','🤞','🤟','🤘','🤙','👈','👉','👆','🖕','👇','☝️','👍','👎','✊','👊','🤛','🤜','👏','🙌','👐','🤲','🤝','🙏','✍️','💅','🤳','💪','🦾','🦿','🦵','🦶','👂','🦻','👃','👀','👁','👅','👄','💋'] },
    { icon:'🐶', label:'Animals',  emojis:['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🐔','🐧','🐦','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄','🐝','🐛','🦋','🐌','🐞','🐜','🦟','🦗','🕷','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑','🦐','🦞','🦀','🐡','🐟','🐠','🐬','🐳','🐋','🦈','🐊','🐅','🐆','🦓','🦍','🦧','🦣','🐘','🦛','🦏','🐪','🐫','🦒','🦘','🦬','🐃','🐂','🐄','🐎','🐖','🐏','🐑','🦙','🐐','🦌'] },
    { icon:'🍕', label:'Food',     emojis:['🍕','🍔','🍟','🌭','🌮','🌯','🥪','🥗','🍿','🧆','🥚','🍳','🥘','🍲','🍜','🍝','🍛','🍣','🍱','🥟','🦪','🍤','🍙','🍚','🍘','🍥','🥮','🍢','🧁','🍰','🎂','🍮','🍭','🍬','🍫','🍿','🍩','🍪','🌰','🥜','🍯','🍼','🥛','☕','🍵','🧃','🥤','🧋','🍶','🍺','🍻','🥂','🍷','🥃','🍸','🍹','🧉','🍾','🧊'] },
    { icon:'⚽', label:'Sports',   emojis:['⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🥏','🎱','🏓','🏸','🏒','🥍','🏑','🏏','🎿','🛷','🥌','⛷','🏂','🪂','🏋️','🤼','🤸','🏊','🤽','🚣','🧘','🚴','🏇','⛺','🏆','🥇','🥈','🥉','🏅','🎖','🎗','🎫','🎟','🎪','🎭','🎨','🎬','🎤','🎧','🎼','🎹','🥁','🎷','🎺','🎸','🎻','🎲','♟','🎯','🎳','🎮','🎰','🧩'] },
    { icon:'🚀', label:'Travel',   emojis:['🚗','🚕','🚙','🚌','🚎','🏎','🚓','🚑','🚒','🚐','🛻','🚚','🚛','🚜','🛵','🏍','🚲','🛴','🛹','🛼','🛺','🚁','🛸','✈️','🚀','🛶','⛵','🚤','🛥','🛳','⛴','🚢','🚂','🚃','🚄','🚅','🚆','🚇','🚈','🚉','🚊','🚝','🚞','🚋','🚌','🚍','🚎','🏁','🚏','🛣','🏔','⛰','🌋','🗺','🏕','🏖','🏜','🏝','🏞','🏟','🏛','🏗'] },
    { icon:'💡', label:'Objects',  emojis:['💡','🔦','🕯','🪔','💰','💴','💵','💶','💷','💸','💳','🪙','💎','⚖️','🔧','🔨','⚙️','🗜','🔩','🧲','🔑','🗝','🔐','🔒','🔓','🚪','🪑','🛋','🛏','🛁','🚿','🧹','🧺','🧻','🪣','🧼','🧽','🧴','🪒','🧻','🪟','🖥','💻','📱','📲','☎️','📞','📟','📠','📺','📷','📸','🔭','🔬','🩺','🩻','💊','🩹','🩺'] },
    { icon:'❤️', label:'Symbols',  emojis:['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔','❣️','💕','💞','💓','💗','💖','💘','💝','💟','☮️','✝️','☪️','🕉','☸️','✡️','🔯','🕎','☯️','☦️','🛐','⛎','♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓','🆔','⚛️','🉑','☢️','☣️','📴','📳','🈶','🈚','🈸','🈺','🈷','✴️','🆚','💮','🉐','㊙️','㊗️','🈴','🈵','🈹','🈲','🅰️','🅱️','🆎','🆑','🅾️','🆘'] },
];

const STICKER_PACKS = [
    { name:'Celebrate', stickers:['🎉','🎊','🥳','🎈','🎁','🎀','🎆','🎇','✨','🌟','⭐','💫','🌠','🏆','🥇','🎖','🏅'] },
    { name:'Love',      stickers:['❤️','💕','💖','💗','💓','💞','💘','💝','💌','💟','🌹','💐','🌸','🌺','😍','🥰','😘','💏','💑','👫'] },
    { name:'Study',     stickers:['📚','✏️','📝','📖','🎓','🏫','💡','🔬','🔭','📐','📏','🖊️','📓','📒','📔','📕','📗','📘','📙','🗒️'] },
    { name:'Reactions', stickers:['👍','👎','👌','🤙','✌️','🤞','🙌','👏','🤝','💪','🙏','🤦','🤷','🙇','💁','🧏','🤔','😤','🤩','🥹'] },
];


// ── Init ─────────────────────────────────────────────────────
async function init() {
    await apiFetch(`/online/${student.id}`, { method:'POST', body: JSON.stringify({online:true}) });

    // Set sidebar footer user info
    document.getElementById('sf-avatar').textContent = getInitials(student.name);
    document.getElementById('sf-name').textContent   = student.name;

    const studRes = await Students.getAll();
    if (studRes.ok) {
        allStudents = studRes.data.filter(s => s.id !== student.id);
        const sel = document.getElementById('new-chat-select');
        sel.innerHTML = '<option value="">Choose a student…</option>' +
            allStudents.map(s =>
                `<option value="${s.id}" data-name="${s.name}">${s.name} (${s.department||''})</option>`
            ).join('');
    }

    await loadConversations();

    const p = new URLSearchParams(window.location.search);
    if (p.get('to')) openChat(parseInt(p.get('to')), decodeURIComponent(p.get('name')||''));

    pollTimer = setInterval(poll, 3000);
    window.addEventListener('beforeunload', () => {
        apiFetch(`/online/${student.id}`,{method:'POST',body:JSON.stringify({online:false})});
        clearInterval(pollTimer);
    });

    buildEmojiUI();
    buildStickerUI();
}

// ── Poll ─────────────────────────────────────────────────────
async function poll() {
    await loadConversations(true);
    if (currentChatId) { await loadMessages(true); await checkTyping(); }
    await loadUnreadTotal();
}

async function loadUnreadTotal() {
    const res = await apiFetch(`/messages/${student.id}/unread-count`);
    if (!res.ok) return;
    const total = res.data.reduce((s,r) => s+r.cnt, 0);
    const banner = document.getElementById('unread-banner');
    if (total > 0) {
        banner.style.display = 'block';
        document.getElementById('unread-text').textContent = `${total} unread message${total>1?'s':''}`;
    } else { banner.style.display = 'none'; }
}

// ── Conversations ─────────────────────────────────────────────
async function loadConversations(silent=false) {
    const [msgRes, unreadRes] = await Promise.all([
        Messages.getAll(student.id),
        apiFetch(`/messages/${student.id}/unread-count`)
    ]);
    if (!msgRes.ok) return;

    conversations = {};
    msgRes.data.forEach(m => {
        const otherId   = m.sender_id === student.id ? m.receiver_id : m.sender_id;
        const otherName = m.sender_id === student.id ? m.receiver_name : m.sender_name;
        if (!conversations[otherId]) {
            conversations[otherId] = { id:otherId, name:otherName,
                lastMsg: m.message || '📎 Attachment', time:m.timestamp, unread:0 };
        }
    });

    if (unreadRes.ok) unreadRes.data.forEach(r => {
        if (conversations[r.sender_id]) conversations[r.sender_id].unread = r.cnt;
    });

    renderSidebar();
}

// ── Sidebar with date groups ──────────────────────────────────
function renderSidebar() {
    const el   = document.getElementById('contacts-list');
    const list = Object.values(conversations);
    if (!list.length) {
        el.innerHTML = `<div style="padding:24px;text-align:center;color:rgba(255,255,255,0.35);font-size:0.8rem;">
            No conversations yet.<br>Click ✎ to start one.</div>`;
        return;
    }

    // Sort by time descending
    list.sort((a,b) => new Date(b.time||0) - new Date(a.time||0));

    // Group into Today / Yesterday / Month groups
    const today = new Date();
    const yest  = new Date(); yest.setDate(today.getDate()-1);
    const groups = { Today:[], Yesterday:[], __months:{} };

    list.forEach(c => {
        const d = c.time ? new Date(c.time) : null;
        if (!d || isNaN(d.getTime())) { groups.Today.push(c); return; }
        if (d.toDateString() === today.toDateString())  groups.Today.push(c);
        else if (d.toDateString() === yest.toDateString()) groups.Yesterday.push(c);
        else {
            const key = d.toLocaleString('en',{month:'long',year:'numeric'});
            if (!groups.__months[key]) groups.__months[key] = [];
            groups.__months[key].push(c);
        }
    });

    let html = '';
    const renderGroup = (label, items) => {
        if (!items.length) return;
        html += `<div class="chat-group-label">${label}</div>`;
        html += items.map(c => contactHTML(c)).join('');
    };

    renderGroup('Today', groups.Today);
    renderGroup('Yesterday', groups.Yesterday);

    // Month groups sorted newest first
    Object.entries(groups.__months)
        .sort((a,b) => new Date(b[0]) - new Date(a[0]))
        .forEach(([label, items]) => renderGroup(label, items));

    el.innerHTML = html;

    // Load online rings
    list.forEach(c => {
        apiFetch(`/online/${c.id}`).then(res => {
            if (!res.ok) return;
            const ring = document.getElementById(`ring-${c.id}`);
            if (ring) ring.className = `online-ring ${res.data.is_online?'online':'offline'}`;
            if (currentChatId === c.id) updateOnlineHeader(res.data);
        });
    });
}

function contactHTML(c) {
    return `
    <div class="contact-item ${currentChatId===c.id?'active':''}" id="contact-${c.id}"
         onclick="openChat(${c.id},'${c.name.replace(/'/g,"\\'")}')">
        <div class="contact-av">${getInitials(c.name)}
            <div class="online-ring offline" id="ring-${c.id}"></div>
        </div>
        <div class="contact-body">
            <div class="contact-name">${c.name}</div>
            <div class="contact-preview">${c.lastMsg||''}</div>
        </div>
        <div class="contact-meta">
            <span class="contact-time">${safeFormatTime(c.time)}</span>
            ${c.unread>0?`<span class="unread-badge">${c.unread}</span>`:''}
        </div>
    </div>`;
}

function safeFormatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return '';
    return formatTime(ts);
}

function filterContacts() {
    const q = document.getElementById('contact-search').value.toLowerCase();
    document.querySelectorAll('.contact-item').forEach(el => {
        el.style.display = el.querySelector('.contact-name').textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}

// ── Open / Close Chat ─────────────────────────────────────────
async function openChat(otherId, otherName) {
    currentChatId   = otherId;
    currentChatName = otherName;
    lastMsgCount    = 0;

    document.getElementById('no-chat').style.display     = 'none';
    document.getElementById('chat-wrapper').style.display = 'flex';
    document.getElementById('ch-avatar').textContent     = getInitials(otherName);
    document.getElementById('ch-name').textContent       = otherName;

    showTab('chat');
    renderSidebar();
    await loadMessages();
    await apiFetch(`/messages/${student.id}/mark-read`,{method:'PUT',body:JSON.stringify({other_id:otherId})});
    const onRes = await apiFetch(`/online/${otherId}`);
    if (onRes.ok) updateOnlineHeader(onRes.data);
    document.getElementById('msg-input').focus();
    closeEspPanel();
}

function updateOnlineHeader(data) {
    document.getElementById('status-dot').className = `status-dot ${data.is_online?'online':'offline'}`;
    document.getElementById('status-text').textContent = data.is_online
        ? 'Online'
        : (data.last_seen ? 'Last seen '+formatTime(data.last_seen) : 'Offline');
}

// ── Load Messages ─────────────────────────────────────────────
async function loadMessages(silent=false) {
    const res = await Messages.getConversation(student.id, currentChatId);
    const el  = document.getElementById('chat-msgs');
    if (!res.ok || !res.data.length) {
        if (!silent) el.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px 0;">
            <div style="font-size:2.5rem;opacity:0.3;">👋</div><p>Say hello to ${currentChatName}!</p></div>`;
        return;
    }
    if (silent && res.data.length === lastMsgCount) return;
    lastMsgCount = res.data.length;

    // Group by date
    const groups = {};
    res.data.forEach(m => {
        const raw = m.timestamp || '';
        const day = raw ? raw.split('T')[0] : 'today';
        if (!groups[day]) groups[day] = [];
        groups[day].push(m);
    });

    el.innerHTML = Object.entries(groups).map(([day,msgs]) =>
        `<div class="date-sep"><span>${formatDateSep(day)}</span></div>
        ${msgs.map(m => renderMessage(m)).join('')}`
    ).join('');
    el.scrollTop = el.scrollHeight;
}

function renderMessage(m) {
    const isSent = m.sender_id === student.id;
    const side   = isSent ? 'sent' : 'received';
    const time   = safeFormatTime(m.timestamp);
    const seen   = isSent ? `<span class="seen-tick ${m.is_read?'seen':''}">✓✓</span>` : '';
    const type   = m.message_type || 'text';
    let content  = '';

    if (type === 'sticker') {
        content = `<div class="msg-sticker"><span style="font-size:2.5rem;">${m.message}</span></div>`;
        return `<div class="msg-row ${side}"><div class="msg-group">
            <div class="msg-bubble" style="background:transparent;border:none;box-shadow:none;padding:4px 8px;">${content}</div>
            <div class="msg-meta"><span>${time}</span>${seen}</div>
        </div></div>`;
    }

    // Check if text is only emojis
    const emojiOnly = type==='text' && m.message && /^[\p{Emoji}\s]+$/u.test(m.message) && m.message.trim().length <= 8;

    if (type === 'text') {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const escaped  = (m.message||'').replace(/</g,'&lt;');
        content = escaped.replace(urlRegex, url =>
            `<a href="${url}" target="_blank" rel="noopener" style="color:${isSent?'#fff':'var(--primary)'};text-decoration:underline;">${url}</a>`);
    } else if (type === 'link') {
        content = `${m.message||''}<div class="msg-link-preview">🔗 <a href="${m.file_url}" target="_blank" rel="noopener">${m.file_url}</a></div>`;
    } else if (type === 'image') {
        content = `<div class="msg-media"><img src="${m.file_url}" alt="image" onerror="this.style.display='none'"></div>`;
    } else if (['video','audio','document','pdf'].includes(type)) {
        const icons={video:'🎬',audio:'🎵',document:'📄',pdf:'📋'};
        content = `<div class="msg-file-bubble"><span class="file-icon">${icons[type]||'📎'}</span>
            <div class="file-info"><b>${m.file_name||'File'}</b>
            ${m.file_url?`<a href="${m.file_url}" target="_blank" style="color:${isSent?'#fff':'var(--primary)'};">Open →</a>`:''}</div></div>`;
    } else { content = m.message||''; }

    return `<div class="msg-row ${side}"><div class="msg-group">
        <div class="msg-bubble ${emojiOnly?'emoji-only':''}">${content}</div>
        <div class="msg-meta"><span>${time}</span>${seen}</div>
    </div></div>`;
}

function formatDateSep(dateStr) {
    if (!dateStr || dateStr === 'today') return 'Today';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 'Today';
    const today = new Date(), yest = new Date();
    yest.setDate(today.getDate()-1);
    if (d.toDateString()===today.toDateString()) return 'Today';
    if (d.toDateString()===yest.toDateString())  return 'Yesterday';
    return d.toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
}

// ── Send Message ──────────────────────────────────────────────
async function sendMsg() {
    const input = document.getElementById('msg-input');
    const text  = input.value.trim();
    if (!text || !currentChatId) return;
    input.value = '';
    const isUrl = /^https?:\/\/\S+$/.test(text);
    await Messages.send(student.id, currentChatId, text, isUrl?'link':'text', isUrl?text:null);
    clearTyping();
    await loadMessages();
    await loadConversations(true);
}

async function sendEmoji(emoji) {
    if (!currentChatId) return;
    addRecentEmoji(emoji);
    await Messages.send(student.id, currentChatId, emoji, 'text', null);
    await loadMessages();
    await loadConversations(true);
}

async function sendSticker(sticker) {
    if (!currentChatId) return;
    await Messages.send(student.id, currentChatId, sticker, 'sticker', null);
    closeEspPanel();
    await loadMessages();
    await loadConversations(true);
}

