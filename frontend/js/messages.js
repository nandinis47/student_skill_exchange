// ============================================================
//  Messages v4 — WhatsApp-style full chat system
// ============================================================
requireAuth(); renderNavUser(); setActiveNav('messages');

const student = getCurrentStudent();
let currentChatId   = null, currentChatName = '';
let currentGroupId  = null, currentGroupName = '';
let allStudents = [], conversations = {};
let pollTimer = null, typingTimer = null;
let lastMsgCount = 0, lastGrpMsgCount = 0;
let replyTo = null;
let sidebarTab = 'chats';
let espOpen = false, currentEspTab = 'emoji';
let recentEmojis = JSON.parse(localStorage.getItem('recentEmojis') || '[]');
let currentStickerPack = 0;
let ctxMenuEl = null;

// ── EMOJI DATA ────────────────────────────────────────────────
const EMOJI_CATS = [
    {icon:'😊',label:'Smileys', emojis:['😀','😁','😂','🤣','😃','😄','😅','😆','😇','😉','😊','😋','😎','😍','🥰','😘','🙂','🤗','🤩','🤔','😐','🙄','😏','😣','😥','😮','😪','😴','😌','😛','😜','😝','🤤','😒','😓','😔','😕','🙃','🤑','😲','☹️','😖','😞','😟','😤','😢','😭','😦','😧','😨','😩','🤯','😬','😰','😱','🥵','🥶','😳','🤪','😵','🥴','😷','🤒','🤕','🤢','🤮','🤧','🥳']},
    {icon:'👋',label:'People',  emojis:['👋','🤚','🖐','✋','🖖','👌','✌️','🤞','👈','👉','👆','👇','👍','👎','✊','👊','🤛','🤜','👏','🙌','🙏','💪','🤝','🫶','💅','🫰','🤟','🤘','🤙']},
    {icon:'🐶',label:'Animals', emojis:['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🐔','🐧','🐦','🦆','🦅','🦉','🦇','🐝','🦋','🐌','🐞','🐜','🐢','🐍','🦎','🐙','🦑','🦐','🐡','🐟','🐬','🐳','🦈','🐊','🐆','🦓','🐘','🦒','🐄','🐎','🐖','🐑','🦄']},
    {icon:'🍕',label:'Food',    emojis:['🍕','🍔','🍟','🌭','🌮','🌯','🥪','🍿','🧆','🍳','🍜','🍝','🍛','🍣','🍱','🥟','🍤','🍙','🍚','🍰','🎂','🍮','🍭','🍬','🍫','🍩','🍪','🧁','☕','🍵','🧃','🥤','🧋','🍺','🍻','🥂','🍷','🥃']},
    {icon:'⚽',label:'Sports',  emojis:['⚽','🏀','🏈','⚾','🥎','🎾','🏐','🏉','🎱','🏓','🏸','🥍','🎿','🛷','🏋️','🤸','🏊','🚴','🏆','🥇','🥈','🥉','🏅','🎯','🎳','🎮','🎲','♟','🎨','🎭','🎬','🎤','🎧','🎼','🎹','🎸']},
    {icon:'🚀',label:'Travel',  emojis:['🚗','🚕','🚙','🚌','🏎','🚑','🚒','🛻','🛵','🏍','🚲','🛴','✈️','🚀','🛸','⛵','🚢','🚂','🚄','🚇','🌍','🌎','🌏','🗺','🏔','🌋','🏕','🏖','🏜','🏝','🏙','🌆','🌃','🌉','🌌']},
    {icon:'💡',label:'Objects', emojis:['💡','🔦','💰','💎','⚖️','🔧','🔨','⚙️','🔑','🗝','🔐','🔒','🔓','🖥','💻','📱','📷','📸','🔭','🔬','💊','🩺','📚','✏️','📝','📎','📌','📋','🗒','🗓','📅','⏰','⏱','🎁','🎈','🎉','🎊']},
    {icon:'❤️',label:'Symbols', emojis:['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔','❣️','💕','💞','💓','💗','💖','💘','💝','✨','⭐','🌟','💫','🔥','💥','❄️','🌈','☀️','🌙','⚡','🌊','💧','🌿','🍀','🌸','🌺','🌻','🌹']},
];
const STICKER_PACKS = [
    {name:'Celebrate',stickers:['🎉','🎊','🥳','🎈','🎁','🎀','🎆','🎇','✨','🌟','⭐','💫','🏆','🥇','🎖','🏅','🎗','🎟']},
    {name:'Love',     stickers:['❤️','💕','💖','💗','💓','💞','💘','💝','💌','💟','🌹','💐','🌸','🌺','😍','🥰','😘','💏','💑','👫']},
    {name:'Study',    stickers:['📚','✏️','📝','📖','🎓','🏫','💡','🔬','🔭','📐','📏','🖊️','📓','📒','📔','📕','📗','📘','📙','🗒️']},
    {name:'Reactions',stickers:['👍','👎','👌','🤙','✌️','🤞','🙌','👏','🤝','💪','🙏','🤦','🤷','🙇','💁','🤔','😤','🤩','🥹','💯']},
];

// ── Init ─────────────────────────────────────────────────────
async function init() {
    await apiFetch(`/online/${student.id}`,{method:'POST',body:JSON.stringify({online:true})});
    document.getElementById('sf-av').textContent   = getInitials(student.name);
    document.getElementById('sf-name').textContent = student.name;

    const res = await Students.getAll();
    if (res.ok) {
        allStudents = res.data.filter(s => s.id !== student.id);
        const sel = document.getElementById('new-chat-select');
        sel.innerHTML = '<option value="">Choose…</option>' +
            allStudents.map(s=>`<option value="${s.id}" data-name="${s.name}">${s.name} (${s.department||''})</option>`).join('');
        // Build group member checkboxes
        renderMemberCheckboxes();
    }

    await loadConversations();
    const p = new URLSearchParams(window.location.search);
    if (p.get('to')) openChat(parseInt(p.get('to')), decodeURIComponent(p.get('name')||''));

    pollTimer = setInterval(poll, 3000);
    window.addEventListener('beforeunload', ()=>{
        apiFetch(`/online/${student.id}`,{method:'POST',body:JSON.stringify({online:false})});
        clearInterval(pollTimer);
    });

    buildEmojiUI(); buildStickerUI();
    document.addEventListener('click', handleOutsideClick);
}

async function poll() {
    await loadConversations(true);
    if (currentChatId)  { await loadMessages(true); await checkTyping(); }
    if (currentGroupId) await loadGroupMessages(true);
    await loadUnreadTotal();
}

async function loadUnreadTotal() {
    const res = await apiFetch(`/messages/${student.id}/unread-count`);
    if (!res.ok) return;
    const total = res.data.reduce((s,r)=>s+r.cnt,0);
    const b = document.getElementById('unread-banner');
    if (total > 0) { b.style.display='block'; document.getElementById('unread-text').textContent=`${total} unread`; }
    else b.style.display='none';
}

// ── Sidebar ───────────────────────────────────────────────────
function switchSidebarTab(tab, btn) {
    sidebarTab = tab;
    document.querySelectorAll('.stab').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    if (tab === 'chats')  loadConversations();
    else                  loadGroups();
}

async function loadConversations(silent=false) {
    if (sidebarTab !== 'chats') return;
    const [msgRes, unreadRes] = await Promise.all([
        Messages.getAll(student.id),
        apiFetch(`/messages/${student.id}/unread-count`)
    ]);
    if (!msgRes.ok) return;
    conversations = {};
    msgRes.data.forEach(m=>{
        const otherId   = m.sender_id===student.id ? m.receiver_id : m.sender_id;
        const otherName = m.sender_id===student.id ? m.receiver_name : m.sender_name;
        if (!conversations[otherId])
            conversations[otherId]={id:otherId,name:otherName,lastMsg:m.message||'📎',time:m.timestamp,unread:0};
    });
    if (unreadRes.ok) unreadRes.data.forEach(r=>{
        if (conversations[r.sender_id]) conversations[r.sender_id].unread=r.cnt;
    });
    renderChatSidebar();
}

function renderChatSidebar() {
    const el   = document.getElementById('contacts-list');
    const list = Object.values(conversations).sort((a,b)=>new Date(b.time||0)-new Date(a.time||0));
    if (!list.length){
        el.innerHTML='<div style="padding:24px;text-align:center;color:rgba(255,255,255,0.3);font-size:0.8rem;">No conversations yet</div>';
        return;
    }
    const today=new Date(), yest=new Date(); yest.setDate(today.getDate()-1);
    const groups={Today:[],Yesterday:{},__months:{}};
    list.forEach(c=>{
        const d=c.time?new Date(c.time):null;
        if (!d||isNaN(d.getTime())) { if (!groups.Today) groups.Today=[]; groups.Today.push(c); return; }
        if (d.toDateString()===today.toDateString()) groups.Today.push(c);
        else if (d.toDateString()===yest.toDateString()) { if (!groups.Yesterday[0]) groups.Yesterday={}; if (!Array.isArray(groups.Yesterday)) groups.Yesterday=[]; groups.Yesterday.push?groups.Yesterday.push(c):(groups.Yesterday=[c]); }
        else { const k=d.toLocaleString('en',{month:'long',year:'numeric'}); if (!groups.__months[k]) groups.__months[k]=[]; groups.__months[k].push(c); }
    });
    let html='';
    const rg=(label,items)=>{ if (!Array.isArray(items)||!items.length) return;
        html+=`<div class="chat-group-label">${label}</div>`+items.map(c=>contactHTML(c,false)).join(''); };
    rg('Today',groups.Today);
    if (Array.isArray(groups.Yesterday)) rg('Yesterday',groups.Yesterday);
    Object.entries(groups.__months).sort((a,b)=>new Date(b[0])-new Date(a[0])).forEach(([l,items])=>rg(l,items));
    el.innerHTML=html;
    list.forEach(c=>apiFetch(`/online/${c.id}`).then(r=>{
        if (!r.ok) return;
        const ring=document.getElementById(`ring-${c.id}`);
        if (ring) ring.className=`online-ring ${r.data.is_online?'online':'offline'}`;
    }));
}

async function loadGroups() {
    const res = await apiFetch(`/groups/${student.id}`);
    const el  = document.getElementById('contacts-list');
    if (!res.ok||!res.data.length){
        el.innerHTML='<div style="padding:24px;text-align:center;color:rgba(255,255,255,0.3);font-size:0.8rem;">No groups yet.<br>Create one!</div>';
        return;
    }
    el.innerHTML='<div class="chat-group-label">Your Groups</div>'+
        res.data.map(g=>`
        <div class="contact-item ${currentGroupId===g.group_id?'active':''}" onclick="openGroup(${g.group_id},'${g.group_name.replace(/'/g,"\\'")}',${g.member_count})">
            <div class="contact-av" style="background:linear-gradient(135deg,#9c27b0,#673ab7);font-size:1.1rem;">👥</div>
            <div class="contact-body">
                <div class="contact-name">${g.group_name}</div>
                <div class="contact-preview">${g.last_msg||'No messages yet'}</div>
            </div>
            <div class="contact-meta">
                <span class="contact-time">${safeFormatTime(g.created_at)}</span>
                ${g.role==='admin'?'<span style="font-size:0.6rem;color:gold;">★ Admin</span>':''}
            </div>
        </div>`).join('');
}

function contactHTML(c) {
    const unreadBadge = c.unread>0 ? `<span class="unread-badge u-badge">${c.unread}</span>` : '';
    return `<div class="contact-item ${currentChatId===c.id?'active':''}" id="contact-${c.id}"
         onclick="openChat(${c.id},'${c.name.replace(/'/g,"\\'")}')">
        <div class="contact-av">${getInitials(c.name)}<div class="online-ring offline" id="ring-${c.id}"></div></div>
        <div class="contact-body">
            <div class="contact-name">${c.name}</div>
            <div class="contact-preview">${c.lastMsg||''}</div>
        </div>
        <div class="contact-meta"><span class="contact-time">${safeFormatTime(c.time)}</span>${unreadBadge}</div>
    </div>`;
}

function safeFormatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    return isNaN(d.getTime()) ? '' : formatTime(ts);
}
function filterContacts() {
    const q = document.getElementById('contact-search').value.toLowerCase();
    document.querySelectorAll('.contact-item').forEach(el=>{
        const n = el.querySelector('.contact-name')?.textContent.toLowerCase()||'';
        el.style.display = n.includes(q)?'':'none';
    });
}

// ── Open Chat / Group ─────────────────────────────────────────
async function openChat(otherId, otherName) {
    currentChatId=otherId; currentChatName=otherName;
    currentGroupId=null; replyTo=null;
    document.getElementById('no-chat').style.display='none';
    document.getElementById('chat-wrapper').style.display='flex';
    document.getElementById('group-wrapper').style.display='none';
    document.getElementById('ch-av').textContent=getInitials(otherName);
    document.getElementById('ch-name').textContent=otherName;
    document.getElementById('ch-sub').innerHTML='<span class="status-dot offline" id="status-dot"></span><span id="status-text">Loading…</span>';
    showTab('chat'); renderChatSidebar();
    await loadMessages();
    await apiFetch(`/messages/${student.id}/mark-read`,{method:'PUT',body:JSON.stringify({other_id:otherId})});
    const onRes=await apiFetch(`/online/${otherId}`);
    if (onRes.ok) updateOnlineHdr(onRes.data);
    document.getElementById('msg-input').focus();
    closeModal('new-chat-modal');
}

async function openGroup(groupId, groupName, memberCount) {
    currentGroupId=groupId; currentGroupName=groupName;
    currentChatId=null; replyTo=null;
    document.getElementById('no-chat').style.display='none';
    document.getElementById('chat-wrapper').style.display='none';
    document.getElementById('group-wrapper').style.display='flex';
    document.getElementById('grp-av').textContent='👥';
    document.getElementById('grp-name').textContent=groupName;
    document.getElementById('grp-sub').textContent=`${memberCount} members`;
    await loadGroups();
    await loadGroupMessages();
    document.getElementById('grp-input').focus();
}

function updateOnlineHdr(data) {
    const dot=document.getElementById('status-dot'), txt=document.getElementById('status-text');
    if (!dot||!txt) return;
    dot.className=`status-dot ${data.is_online?'online':'offline'}`;
    txt.textContent=data.is_online?'Online':(data.last_seen?'Last seen '+formatTime(data.last_seen):'Offline');
}

// ── Load & Render Messages ────────────────────────────────────
async function loadMessages(silent=false) {
    const res=await Messages.getConversation(student.id,currentChatId);
    const el=document.getElementById('chat-msgs');
    if (!res.ok||!res.data.length){
        if (!silent) el.innerHTML=`<div style="text-align:center;color:var(--text-muted);padding:40px 0;"><div style="font-size:3rem;opacity:.2;">👋</div><p>Say hello to ${currentChatName}!</p></div>`;
        return;
    }
    if (silent&&res.data.length===lastMsgCount) return;
    lastMsgCount=res.data.length;
    const groups={};
    res.data.forEach(m=>{ const d=m.timestamp?(m.timestamp.split('T')[0]||'today'):'today'; if (!groups[d]) groups[d]=[]; groups[d].push(m); });
    el.innerHTML=Object.entries(groups).map(([d,msgs])=>
        `<div class="date-sep"><span>${fmtDateSep(d)}</span></div>${msgs.map(m=>renderMsg(m)).join('')}`).join('');
    el.scrollTop=el.scrollHeight;
}

function renderMsg(m) {
    if (m.is_deleted) return `<div class="msg-row ${m.sender_id===student.id?'sent':'received'}"><div class="msg-group"><div class="msg-bubble deleted">🚫 This message was deleted</div></div></div>`;
    const isSent=m.sender_id===student.id, side=isSent?'sent':'received';
    const time=safeFormatTime(m.timestamp);
    const tick=isSent?`<span class="tick ${m.is_read?'read':'delivered'}">✓✓</span>`:'';
    const edited=m.edited_at?`<span class="edited-label"> (edited)</span>`:'';
    const type=m.message_type||'text';
    let body='';

    if (m.reply_to_id) {
        body+=`<div class="reply-quote">↩ Reply</div>`;
    }

    if (type==='text') {
        const emojiOnly=/^[\p{Emoji}\s]+$/u.test(m.message||'')&&(m.message||'').trim().length<=8;
        const urlRx=/(https?:\/\/[^\s]+)/g;
        const esc=(m.message||'').replace(/</g,'&lt;');
        const linked=esc.replace(urlRx,url=>`<a href="${url}" target="_blank" rel="noopener" style="color:${isSent?'#fff':'var(--primary)'};text-decoration:underline;">${url}</a>`);
        body+=`<span${emojiOnly?' class="emoji-text"':''}>${linked}</span>`;
        return `<div class="msg-row ${side}" oncontextmenu="showCtxMenu(event,${m.message_id},'${side}')">
            <div class="msg-group"><div class="msg-bubble${emojiOnly?' emoji-only':''}">${body}${edited}</div>
            <div class="msg-meta"><span>${time}</span>${tick}</div></div></div>`;
    }
    if (type==='link') { body=`${m.message||''}<div class="msg-link-card">🔗 <a href="${m.file_url}" target="_blank" rel="noopener">${m.file_url}</a></div>`; }
    else if (type==='image') { body=`<div class="msg-image"><img src="${m.file_url}" alt="img" onclick="openImgViewer('${m.file_url}')" onerror="this.style.display='none'"></div>`; }
    else if (type==='video') { body=`<div class="msg-video"><video src="${m.file_url}" controls style="max-width:220px;border-radius:10px;"></video></div>`; }
    else if (['document','audio'].includes(type)) {
        const ic={document:'📄',audio:'🎵'}[type]||'📎';
        body=`<div class="msg-file"><span class="msg-file-icon">${ic}</span><div class="msg-file-info"><b>${m.file_name||'File'}</b>${m.file_url?`<a href="${m.file_url}" target="_blank" style="color:${isSent?'#fff':'var(--primary)'};">Open →</a>`:''}</div></div>`;
    }
    else if (type==='sticker') { return `<div class="msg-row ${side}"><div class="msg-group"><div style="font-size:2.5rem;padding:4px;">${m.message}</div><div class="msg-meta"><span>${time}</span>${tick}</div></div></div>`; }
    else if (type==='location') { body=`<div class="msg-location" onclick="openLocation(${m.location_lat},${m.location_lng})">📍 Location · Tap to view</div>`; }
    else if (type==='poll') {
        try {
            const pd=JSON.parse(m.poll_data||m.message||'{}');
            body=`<div class="msg-poll"><div class="poll-q">📊 ${pd.question||'Poll'}</div>${(pd.options||[]).map((o,i)=>`<div class="poll-opt-row">◯ ${o}</div>`).join('')}</div>`;
        } catch { body=m.message||''; }
    }
    else { body=m.message||''; }

    return `<div class="msg-row ${side}" oncontextmenu="showCtxMenu(event,${m.message_id},'${side}')">
        <div class="msg-group"><div class="msg-bubble">${body}${edited}</div>
        <div class="msg-meta"><span>${time}</span>${tick}</div></div></div>`;
}

function fmtDateSep(ds) {
    if (!ds||ds==='today') return 'Today';
    const d=new Date(ds); if (isNaN(d.getTime())) return 'Today';
    const t=new Date(), y=new Date(); y.setDate(t.getDate()-1);
    if (d.toDateString()===t.toDateString()) return 'Today';
    if (d.toDateString()===y.toDateString()) return 'Yesterday';
    return d.toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
}

// ── Send Messages ─────────────────────────────────────────────
async function sendMsg() {
    const input=document.getElementById('msg-input');
    const text=input.value.trim(); if (!text||!currentChatId) return;
    input.value='';
    const isUrl=/^https?:\/\/\S+$/.test(text);
    const payload={sender_id:student.id,receiver_id:currentChatId,message:text,
        message_type:isUrl?'link':'text',file_url:isUrl?text:null,
        reply_to_id:replyTo?replyTo.message_id:null};
    await apiFetch('/messages',{method:'POST',body:JSON.stringify(payload)});
    clearReply(); clearTyping();
    await loadMessages(); await loadConversations(true);
}

async function sendEmoji(e) {
    if (!currentChatId) return;
    addRecentEmoji(e);
    await apiFetch('/messages',{method:'POST',body:JSON.stringify({sender_id:student.id,receiver_id:currentChatId,message:e,message_type:'text'})});
    await loadMessages(); await loadConversations(true);
}

async function sendSticker(s) {
    if (!currentChatId) return;
    await apiFetch('/messages',{method:'POST',body:JSON.stringify({sender_id:student.id,receiver_id:currentChatId,message:s,message_type:'sticker'})});
    closeEspPanel(); await loadMessages();
}

// ── Group messages ────────────────────────────────────────────
async function loadGroupMessages(silent=false) {
    const res=await apiFetch(`/groups/${currentGroupId}/messages`);
    const el=document.getElementById('grp-msgs');
    if (!res.ok||!res.data.length){ if (!silent) el.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:40px 0;">No messages yet</div>'; return; }
    if (silent&&res.data.length===lastGrpMsgCount) return;
    lastGrpMsgCount=res.data.length;
    const groups={};
    res.data.forEach(m=>{ const d=m.timestamp?(m.timestamp.split('T')[0]):'today'; if (!groups[d]) groups[d]=[]; groups[d].push(m); });
    el.innerHTML=Object.entries(groups).map(([d,msgs])=>
        `<div class="date-sep"><span>${fmtDateSep(d)}</span></div>${msgs.map(m=>{
            const isSent=m.sender_id===student.id, side=isSent?'sent':'received';
            const time=safeFormatTime(m.timestamp);
            return `<div class="msg-row ${side}">
                ${!isSent?`<div class="sender-av">${getInitials(m.sender_name)}</div>`:''}
                <div class="msg-group">
                    ${!isSent?`<div class="msg-sender-name">${m.sender_name}</div>`:''}
                    <div class="msg-bubble">${m.message||''}</div>
                    <div class="msg-meta"><span>${time}</span></div>
                </div></div>`;
        }).join('')}`).join('');
    el.scrollTop=el.scrollHeight;
}

async function sendGrpMsg() {
    const input=document.getElementById('grp-input');
    const text=input.value.trim(); if (!text||!currentGroupId) return;
    input.value='';
    await apiFetch(`/groups/${currentGroupId}/messages`,{method:'POST',body:JSON.stringify({sender_id:student.id,message:text,message_type:'text'})});
    await loadGroupMessages(); await loadGroups();
}

// ── Tabs ──────────────────────────────────────────────────────
function showTab(tab) {
    ['chat','media','docs','links'].forEach(t=>{
        const el=document.getElementById(`tab-${t}`);
        const btn=document.getElementById(`tbtn-${t}`);
        if (el)  el.style.display=t===tab?'flex':'none';
        if (btn) btn.classList.toggle('active',t===tab);
    });
    if (tab==='media') loadMediaTab();
    if (tab==='docs')  loadDocsTab();
    if (tab==='links') loadLinksTab();
}

async function loadMediaTab() {
    const res=await apiFetch(`/messages/${student.id}?with=${currentChatId}`);
    const el=document.getElementById('media-grid');
    if (!res.ok) return;
    const media=res.data.filter(m=>['image','video'].includes(m.message_type)&&m.file_url);
    if (!media.length){el.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">No media shared yet</div>';return;}
    el.innerHTML=media.map(m=>`<div class="media-thumb">${m.message_type==='image'?`<img src="${m.file_url}" onclick="openImgViewer('${m.file_url}')">`:
        `<video src="${m.file_url}" controls></video>`}</div>`).join('');
}

async function loadDocsTab() {
    const res=await apiFetch(`/shared-content/${student.id}?with=${currentChatId}&type=document`);
    const el=document.getElementById('docs-list');
    if (!res.ok||!res.data.length){el.innerHTML='<div style="text-align:center;padding:40px;color:var(--text-muted);">No documents shared yet</div>';return;}
    const ic={pdf:'📋',notes:'📝',word:'📝',presentation:'📊'};
    el.innerHTML=res.data.map(d=>`<div class="content-row">
        <div class="cr-icon" style="background:#e8f0fe;">${ic[d.media_type]||'📄'}</div>
        <div class="cr-info"><div class="cr-title">${d.title}</div>
        <div class="cr-meta">By ${d.sender_name} · ${formatDate(d.shared_at)}${d.file_size?' · '+d.file_size:''}</div></div>
        ${d.file_url?`<a href="${d.file_url}" target="_blank" class="btn btn-secondary btn-sm">Open</a>`:''}
    </div>`).join('');
}

async function loadLinksTab() {
    const res=await apiFetch(`/shared-content/${student.id}?with=${currentChatId}&type=link`);
    const el=document.getElementById('links-list');
    if (!res.ok||!res.data.length){el.innerHTML='<div style="text-align:center;padding:40px;color:var(--text-muted);">No links shared yet</div>';return;}
    el.innerHTML=res.data.map(l=>`<div class="content-row">
        <div class="cr-icon" style="background:#e6f4ea;">🔗</div>
        <div class="cr-info"><div class="cr-title">${l.title}</div>
        <div class="cr-meta">By ${l.sender_name} · ${formatDate(l.shared_at)}</div>
        ${l.description?`<div class="cr-meta">${l.description}</div>`:''}</div>
        ${l.file_url?`<a href="${l.file_url}" target="_blank" class="btn btn-primary btn-sm">Open →</a>`:''}
    </div>`).join('');
}

// ── Attach menu ───────────────────────────────────────────────
function toggleAttachMenu() {
    const m=document.getElementById('attach-menu');
    m.style.display=m.style.display==='none'?'block':'none';
    closeEspPanel();
}
function toggleGrpAttach() {
    const m=document.getElementById('grp-attach-menu');
    m.style.display=m.style.display==='none'?'block':'none';
}
function triggerCamera()  { document.getElementById('camera-input').click(); toggleAttachMenu(); }
function triggerGallery() { document.getElementById('gallery-input').click(); toggleAttachMenu(); }
function openDocPicker()  { document.getElementById('doc-input').click(); toggleAttachMenu(); }
function triggerGrpGallery() { document.getElementById('grp-gallery-input').click(); toggleGrpAttach(); }
function openGrpDocPicker()  { document.getElementById('grp-doc-input').click(); toggleGrpAttach(); }

function triggerLocation() {
    toggleAttachMenu();
    if (!navigator.geolocation) { alert('Geolocation not supported'); return; }
    navigator.geolocation.getCurrentPosition(async pos=>{
        const {latitude:lat,longitude:lng}=pos.coords;
        await apiFetch('/messages',{method:'POST',body:JSON.stringify({
            sender_id:student.id,receiver_id:currentChatId,
            message:`📍 Location`,message_type:'location',
            location_lat:lat,location_lng:lng
        })});
        await loadMessages();
    }, ()=>alert('Could not get location'));
}

function openLocation(lat, lng) {
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, '_blank');
}

async function handleFileAttach(input, source) {
    const file=input.files[0]; if (!file) return;
    const isImage=file.type.startsWith('image/');
    const isVideo=file.type.startsWith('video/');
    const isDoc  =!isImage&&!isVideo;

    // Read as base64
    const b64=await new Promise(resolve=>{
        const r=new FileReader(); r.onload=e=>resolve(e.target.result); r.readAsDataURL(file);
    });

    // For images/videos: embed as data URL directly (no server storage in this demo)
    const msgType=isImage?'image':isVideo?'video':'document';
    const payload={sender_id:student.id,receiver_id:currentChatId,
        message:file.name,message_type:msgType,
        file_url:isDoc?null:b64,file_name:file.name};

    await apiFetch('/messages',{method:'POST',body:JSON.stringify(payload)});

    // Also add to shared content if document
    if (isDoc) {
        await apiFetch('/shared-content',{method:'POST',body:JSON.stringify({
            sender_id:student.id,receiver_id:currentChatId,
            title:file.name,content_type:'document',media_type:'pdf',
            description:'Uploaded file'
        })});
    }
    await loadMessages(); await loadConversations(true);
    input.value='';
}

async function handleGrpFile(input) {
    const file=input.files[0]; if (!file||!currentGroupId) return;
    const b64=await new Promise(resolve=>{
        const r=new FileReader(); r.onload=e=>resolve(e.target.result); r.readAsDataURL(file);
    });
    const isImg=file.type.startsWith('image/');
    await apiFetch(`/groups/${currentGroupId}/messages`,{method:'POST',body:JSON.stringify({
        sender_id:student.id,message:file.name,
        message_type:isImg?'image':'document',
        file_url:isImg?b64:null,file_name:file.name
    })});
    await loadGroupMessages(); input.value='';
}

// ── Image viewer ──────────────────────────────────────────────
function openImgViewer(url) {
    const ov=document.createElement('div');
    ov.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9999;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
    ov.innerHTML=`<img src="${url}" style="max-width:90vw;max-height:90vh;border-radius:8px;">`;
    ov.onclick=()=>ov.remove();
    document.body.appendChild(ov);
}

// ── Poll ──────────────────────────────────────────────────────
function openPollModal()  { document.getElementById('poll-modal').classList.add('active'); toggleAttachMenu(); }
function openGrpPollModal(){ document.getElementById('poll-modal').classList.add('active'); toggleGrpAttach(); }
function addPollOption() {
    const inp=document.createElement('input');
    inp.type='text'; inp.className='form-control poll-opt'; inp.style.marginBottom='6px';
    inp.placeholder=`Option ${document.querySelectorAll('.poll-opt').length+1}`;
    document.getElementById('poll-options').appendChild(inp);
}
async function sendPoll() {
    const q=document.getElementById('poll-question').value.trim();
    const opts=[...document.querySelectorAll('.poll-opt')].map(i=>i.value.trim()).filter(Boolean);
    if (!q||opts.length<2){alert('Enter a question and at least 2 options');return;}
    const pollData=JSON.stringify({question:q,options:opts,votes:{}});
    const target=currentGroupId?null:currentChatId;
    if (currentGroupId) {
        await apiFetch(`/groups/${currentGroupId}/messages`,{method:'POST',body:JSON.stringify({sender_id:student.id,message:pollData,message_type:'poll'})});
        await loadGroupMessages();
    } else if (target) {
        await apiFetch('/messages',{method:'POST',body:JSON.stringify({sender_id:student.id,receiver_id:target,message:pollData,message_type:'poll'})});
        await loadMessages();
    }
    closeModal('poll-modal');
    document.getElementById('poll-question').value='';
}

// ── Context menu (right click on message) ────────────────────
function showCtxMenu(e, msgId, side) {
    e.preventDefault(); closeCtxMenu();
    const menu=document.createElement('div');
    menu.className='msg-ctx'; menu.id='ctx-menu';
    menu.style.cssText=`position:fixed;top:${e.clientY}px;left:${e.clientX}px;`;
    menu.innerHTML=`
        <button onclick="replyMsg(${msgId})">↩ Reply</button>
        <button onclick="copyMsg(${msgId})">📋 Copy</button>
        ${side==='sent'?`<button onclick="editMsg(${msgId})">✏️ Edit</button><button class="danger" onclick="deleteMsg(${msgId},'everyone')">🗑️ Delete for Everyone</button>`:''}
        <button onclick="deleteMsg(${msgId},'me')">🗑️ Delete for Me</button>`;
    document.body.appendChild(menu);
    ctxMenuEl=menu;
}
function closeCtxMenu() { if (ctxMenuEl) { ctxMenuEl.remove(); ctxMenuEl=null; } }

async function replyMsg(msgId) {
    const res=await Messages.getConversation(student.id,currentChatId);
    const m=res.ok?res.data.find(x=>x.message_id===msgId):null;
    if (m) { replyTo=m; document.getElementById('reply-preview').style.display='flex'; document.getElementById('rp-content').textContent=`↩ ${m.message||'Attachment'}`; }
    closeCtxMenu(); document.getElementById('msg-input').focus();
}
function clearReply() { replyTo=null; document.getElementById('reply-preview').style.display='none'; }

function copyMsg(msgId) {
    closeCtxMenu();
    Messages.getConversation(student.id,currentChatId).then(res=>{
        const m=res.ok?res.data.find(x=>x.message_id===msgId):null;
        if (m&&m.message) navigator.clipboard.writeText(m.message);
    });
}
async function editMsg(msgId) {
    closeCtxMenu();
    const newText=prompt('Edit message:');
    if (!newText) return;
    await apiFetch(`/messages/${msgId}/edit`,{method:'PUT',body:JSON.stringify({message:newText})});
    await loadMessages();
}
async function deleteMsg(msgId, scope) {
    closeCtxMenu();
    if (!confirm(`Delete this message ${scope==='everyone'?'for everyone':'for you'}?`)) return;
    await apiFetch(`/messages/${msgId}/delete`,{method:'PUT',body:JSON.stringify({scope})});
    await loadMessages();
}

// ── Typing ────────────────────────────────────────────────────
async function onTyping() {
    if (!currentChatId) return;
    await apiFetch('/typing',{method:'POST',body:JSON.stringify({student_id:student.id,typing_to:currentChatId,is_typing:true})});
    clearTimeout(typingTimer); typingTimer=setTimeout(clearTyping,3000);
}
async function clearTyping() {
    if (!currentChatId) return;
    await apiFetch('/typing',{method:'POST',body:JSON.stringify({student_id:student.id,typing_to:currentChatId,is_typing:false})});
}
async function checkTyping() {
    if (!currentChatId) return;
    const res=await apiFetch(`/typing/${student.id}/${currentChatId}`);
    const el=document.getElementById('typing-ind');
    if (res.ok&&res.data.is_typing){document.getElementById('typing-name').textContent=currentChatName;el.style.display='flex';}
    else el.style.display='none';
}

// ── Groups modal ──────────────────────────────────────────────
function openGroupModal() { document.getElementById('group-modal').classList.add('active'); }
function renderMemberCheckboxes() {
    document.getElementById('member-list').innerHTML=allStudents.map(s=>`
        <label class="member-check">
            <input type="checkbox" value="${s.id}" name="grp-member">
            <div class="contact-av" style="width:30px;height:30px;font-size:0.7rem;">${getInitials(s.name)}</div>
            <div><div style="font-size:0.85rem;font-weight:600;">${s.name}</div><div style="font-size:0.72rem;color:var(--text-muted);">${s.department||''}</div></div>
        </label>`).join('');
}
async function createGroup() {
    const name=document.getElementById('grp-name-input').value.trim();
    const desc=document.getElementById('grp-desc-input').value.trim();
    const members=[...document.querySelectorAll('input[name="grp-member"]:checked')].map(i=>parseInt(i.value));
    const alertEl=document.getElementById('grp-alert');
    if (!name){showAlert(alertEl,'Enter a group name','error');return;}
    if (members.length<1){showAlert(alertEl,'Add at least 1 member','error');return;}
    const res=await apiFetch('/groups',{method:'POST',body:JSON.stringify({group_name:name,description:desc,created_by:student.id,members})});
    if (res.ok){
        closeModal('group-modal');
        document.getElementById('grp-name-input').value='';
        document.getElementById('grp-desc-input').value='';
        switchSidebarTab('groups',document.querySelector('.stab:nth-child(2)'));
        showAlert(document.getElementById('no-chat'),'Group created!','success');
        setTimeout(()=>loadGroups(),500);
    } else showAlert(alertEl,res.data.error||'Failed','error');
}

async function showGrpInfo() {
    const membersRes=await apiFetch(`/groups/${currentGroupId}/members`);
    document.getElementById('grp-info-title').textContent=currentGroupName;
    const el=document.getElementById('grp-info-body');
    if (!membersRes.ok){el.innerHTML='<p>Failed to load</p>';return;}
    el.innerHTML=`<p style="color:var(--text-muted);font-size:0.8rem;margin-bottom:12px;">${membersRes.data.length} members</p>`+
        membersRes.data.map(m=>`<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);">
            <div class="contact-av" style="width:36px;height:36px;font-size:0.8rem;">${getInitials(m.name)}</div>
            <div><div style="font-size:0.875rem;font-weight:600;">${m.name}</div><div style="font-size:0.75rem;color:var(--text-muted);">${m.department||''}</div></div>
            ${m.role==='admin'?'<span style="margin-left:auto;font-size:0.72rem;background:#fef7e0;color:#b06000;padding:2px 8px;border-radius:10px;">Admin</span>':''}
        </div>`).join('');
    document.getElementById('grp-info-modal').classList.add('active');
}

// ── Emoji/GIF/Sticker Panel ───────────────────────────────────
function toggleEspPanel() { espOpen=!espOpen; document.getElementById('esp-panel').style.display=espOpen?'flex':'none'; if (espOpen) buildEmojiUI(); }
function closeEspPanel()  { espOpen=false; document.getElementById('esp-panel').style.display='none'; }
function switchEspTab(tab,btn) {
    currentEspTab=tab;
    document.querySelectorAll('.esp-tab').forEach(b=>b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('esp-emoji').style.display   =tab==='emoji'  ?'flex':'none';
    document.getElementById('esp-gif').style.display     =tab==='gif'    ?'flex':'none';
    document.getElementById('esp-sticker').style.display =tab==='sticker'?'flex':'none';
    if (tab==='gif') loadTrendingGIFs();
}

function buildEmojiUI() {
    const cats=document.getElementById('emoji-cats');
    cats.innerHTML=EMOJI_CATS.map((c,i)=>`<button class="esp-cat-btn ${i===0?'active':''}" onclick="showEmojiCat(${i},this)" title="${c.label}">${c.icon}</button>`).join('');
    showEmojiCat(0,cats.firstElementChild); renderRecentEmojis();
}
let curEmojiCat=0;
function showEmojiCat(idx,btn) {
    curEmojiCat=idx;
    document.querySelectorAll('.esp-cat-btn').forEach(b=>b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('emoji-grid').innerHTML=EMOJI_CATS[idx].emojis.map(e=>`<div class="emoji-item" onclick="sendEmoji('${e}')">${e}</div>`).join('');
}
function filterEmojis() {
    const q=document.getElementById('emoji-search').value.toLowerCase();
    if (!q){showEmojiCat(curEmojiCat,null);return;}
    document.getElementById('emoji-grid').innerHTML=EMOJI_CATS.flatMap(c=>c.emojis).map(e=>`<div class="emoji-item" onclick="sendEmoji('${e}')">${e}</div>`).join('');
}
function addRecentEmoji(e) { recentEmojis=[e,...recentEmojis.filter(r=>r!==e)].slice(0,16); localStorage.setItem('recentEmojis',JSON.stringify(recentEmojis)); renderRecentEmojis(); }
function renderRecentEmojis() {
    const el=document.getElementById('emoji-recent');
    if (!recentEmojis.length){el.innerHTML='';return;}
    el.innerHTML='<span style="font-size:0.65rem;color:var(--text-muted);padding:4px;">Recent</span>'+recentEmojis.map(e=>`<div class="emoji-item" onclick="sendEmoji('${e}')">${e}</div>`).join('');
}

const DEMO_GIFS=[{t:'Thumbs Up',e:'👍'},{t:'Clapping',e:'👏'},{t:'LOL',e:'😂'},{t:'Fire',e:'🔥'},{t:'Love',e:'❤️'},{t:'Mind Blown',e:'🤯'},{t:'Party',e:'🎉'},{t:'High Five',e:'✋'},{t:'100',e:'💯'},{t:'Ok',e:'👌'},{t:'Thinking',e:'🤔'},{t:'Wow',e:'😮'}];
function loadTrendingGIFs() {
    document.getElementById('gif-grid').innerHTML=DEMO_GIFS.map(g=>`<div class="gif-item" onclick="sendEmoji('${g.e}')" title="${g.t}"><span>${g.e}</span></div>`).join('');
}
function searchGIFs() {
    const q=document.getElementById('gif-search').value.toLowerCase();
    const f=q?DEMO_GIFS.filter(g=>g.t.toLowerCase().includes(q)):DEMO_GIFS;
    document.getElementById('gif-grid').innerHTML=f.length?f.map(g=>`<div class="gif-item" onclick="sendEmoji('${g.e}')"><span>${g.e}</span></div>`).join(''):'<div style="padding:20px;text-align:center;color:var(--text-muted);grid-column:1/-1;">No results</div>';
}
function buildStickerUI() {
    const packs=document.getElementById('sticker-packs');
    packs.innerHTML=STICKER_PACKS.map((p,i)=>`<button class="sticker-pack-btn ${i===0?'active':''}" onclick="showStickerPack(${i},this)">${p.name}</button>`).join('');
    showStickerPack(0,packs.firstElementChild);
}
function showStickerPack(idx,btn) {
    currentStickerPack=idx;
    document.querySelectorAll('.sticker-pack-btn').forEach(b=>b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('sticker-grid').innerHTML=STICKER_PACKS[idx].stickers.map(s=>`<div class="sticker-item" onclick="sendSticker('${s}')">${s}</div>`).join('');
}

// ── New chat & modals ─────────────────────────────────────────
function openNewChatModal() { document.getElementById('new-chat-modal').classList.add('active'); }
function startNewChat() {
    const sel=document.getElementById('new-chat-select');
    const id=parseInt(sel.value),name=sel.options[sel.selectedIndex]?.dataset?.name;
    if (!id||!name) return;
    openChat(id,name);
}
function closeModal(id) { document.getElementById(id).classList.remove('active'); }

// ── Outside click handler ────────────────────────────────────
function handleOutsideClick(e) {
    if (!e.target.closest('.attach-diamond')&&!e.target.closest('.attach-popup')) {
        document.getElementById('attach-menu').style.display='none';
        const gm=document.getElementById('grp-attach-menu'); if (gm) gm.style.display='none';
    }
    if (!e.target.closest('.emoji-open')&&!e.target.closest('.esp-panel')) closeEspPanel();
    if (ctxMenuEl&&!e.target.closest('.msg-ctx')) closeCtxMenu();
}

// Patch Messages.send
Messages.send = async (sender_id,receiver_id,message,message_type='text',file_url=null,file_name=null) =>
    apiFetch('/messages',{method:'POST',body:JSON.stringify({sender_id,receiver_id,message,message_type,file_url,file_name})});

init();
