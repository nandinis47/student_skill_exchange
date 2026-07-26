import os

base = r'C:\Users\likhi\OneDrive\Desktop\student_skill_exchange'

def read(rel):
    try:
        with open(os.path.join(base, rel), encoding='utf-8', errors='ignore') as f:
            return f.read()
    except: return ''

html = read('frontend/messages.html')
js   = read('frontend/js/messages.js')
css  = read('frontend/css/messages.css')
back = read('backend/app.py')

checks = [
    # One-to-One
    ('Search / start new conversation',          'openNewChatModal'        in js),
    ('Send text messages',                       'sendMsg'                 in js),
    ('Send emojis',                              'sendEmoji'               in js),
    ('Send images',                              "type==='image'"          in js),
    ('Send videos',                              "type==='video'"          in js),
    ('Send documents',                           "includes(type)"          in js),
    ('Voice notes UI button',                    'voice-btn'               in css),
    ('Voice note recording logic',               'voiceNote'               in js or 'MediaRecorder' in js),
    # Display
    ('Online/Offline status',                    '.status-dot.online'      in css or '.online-ring.online' in css),
    ('Typing indicator',                         'typing-ind'              in html),
    ('Last seen',                                'last_seen'               in back),
    ('Message timestamps',                       'safeFormatTime'          in js),
    ('Delivered tick ✓✓',                        '.tick.delivered'         in css),
    ('Read tick blue ✓✓',                        '.tick.read'              in css),
    # User actions
    ('Reply to messages',                        'replyMsg'                in js),
    ('Forward messages',                         'forwardMsg'              in js or 'forward_message' in back),
    ('Copy messages',                            'copyMsg'                 in js),
    ('Edit messages',                            'editMsg'                 in js),
    ('Delete for Me',                            "scope"                   in js),
    ('Delete for Everyone',                      "'everyone'"              in js),
    ('Pin chats / pin messages',                 'pinThisChat'             in js or 'pin_message' in back),
    ('Mute conversations',                       'muteThisChat'            in js or 'is_muted'    in back),
    ('Archive chats',                            'archiveThisChat'         in js or 'is_archived' in back),
    ('Block users',                              'blockThisUser'           in js or 'is_blocked'  in back),
    ('Report users',                             'reportThisUser'          in js or 'report'      in back),
    # Chat menu UI (⋮)
    ('Chat options menu (⋮)',                    'chat-ctx-menu'           in html),
    # Message search
    ('Search messages in chat',                  'searchInChat'            in js or 'msg-search-bar' in html),
]

ok = fail = 0
for label, passed in checks:
    sym = '\u2713' if passed else '\u2717'
    print(f'  {sym}  {label}')
    if passed: ok += 1
    else: fail += 1

print(f'\nResult: {ok}/{ok+fail} — {fail} missing')
