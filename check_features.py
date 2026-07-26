import os, re

base = r'C:\Users\likhi\OneDrive\Desktop\student_skill_exchange'

def read(rel):
    try:
        with open(os.path.join(base, rel), encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return ''

html  = read('frontend/messages.html')
js    = read('frontend/js/messages.js')
css   = read('frontend/css/messages.css')
back  = read('backend/app.py')

checks = [
    # ── Attachment menu ──────────────────────────────────
    ('✦ Diamond attach button',           'attach-diamond'              in html),
    ('Attach popup with 5 items',         all(x in html for x in ['triggerCamera','triggerGallery','triggerLocation','openDocPicker','openPollModal'])),
    ('Camera (capture=environment)',      'capture="environment"'       in html),
    ('Gallery file input',                'gallery-input'               in html),
    ('Location geolocation',              'getCurrentPosition'          in js),
    ('Document (.pdf .doc .xls .ppt)',   '.pdf,.doc,.docx,.xls'        in html),
    ('Poll modal',                        'poll-modal'                  in html),
    ('Poll send logic',                   'sendPoll'                    in js),
    ('Add poll option',                   'addPollOption'               in js),
    # ── Message types rendered in JS ─────────────────────
    ('Image message rendered',            "type==='image'"              in js),
    ('Video message rendered',            "type==='video'"              in js),
    ('Document/audio rendered',           "includes(type)"              in js),
    ('Link message rendered',             "type==='link'"               in js),
    ('Location message rendered',         "type==='location'"           in js),
    ('Poll message rendered',             "type==='poll'"               in js),
    ('Sticker message rendered',          "type==='sticker'"            in js),
    # ── Message organisation tabs ─────────────────────────
    ('Media tab (tab-media)',              'tab-media'                   in html),
    ('Documents tab (tab-docs)',          'tab-docs'                    in html),
    ('Links tab (tab-links)',              'tab-links'                   in html),
    ('loadMediaTab JS',                   'loadMediaTab'                in js),
    ('loadDocsTab JS',                    'loadDocsTab'                 in js),
    ('loadLinksTab JS',                   'loadLinksTab'                in js),
    # ── Read / unread ─────────────────────────────────────
    ('Blue read tick CSS',                'tick.read'                   in css),
    ('Unread u-badge in JS',              'u-badge'                     in js),
    ('Unread count API polling',          'unread-count'                in js),
    ('Mark-read API call',                'mark-read'                   in js),
    # ── Group features ────────────────────────────────────
    ('Group create modal in HTML',        'group-modal'                 in html),
    ('Member list container',             'member-list'                 in html),
    ('Checkboxes injected by JS',         'grp-member'                  in js),
    ('Group name input',                  'grp-name-input'              in html),
    ('Group description input',           'grp-desc-input'              in html),
    ('Group chat wrapper',                'group-wrapper'               in html),
    ('createGroup JS function',           'createGroup'                 in js),
    ('Group send messages',               'sendGrpMsg'                  in js),
    ('Load group messages',               'loadGroupMessages'           in js),
    # ── Group backend ─────────────────────────────────────
    ('POST /api/groups',                  "route('/api/groups'"         in back),
    ('GET group messages',                'get_group_messages'          in back),
    ('GET group members',                 'get_group_members'           in back),
    ('POST add member',                   'add_group_member'            in back),
    ('DELETE remove member',              'remove_group_member'         in back),
    ('Creator = admin',                   "'admin'"                     in back and 'created_by' in back),
]

ok = fail = 0
for label, passed in checks:
    sym = chr(10003) if passed else chr(10007)
    print(f'  {sym}  {label}')
    if passed: ok += 1
    else: fail += 1

pct = round(ok/(ok+fail)*100)
print(f'\n{"="*50}')
print(f'  Result: {ok}/{ok+fail} ({pct}%) — {fail} gap{"s" if fail!=1 else ""}')
print(f'{"="*50}')
