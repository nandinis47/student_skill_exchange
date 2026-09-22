"""Replace 'Skills Exchange' → 'SkillX' across all frontend HTML files"""
import os, re

frontend = r'C:\Users\likhi\OneDrive\Desktop\student_skill_exchange\frontend'
changed = []

replacements = [
    # exact brand text variants (order matters — longest first)
    ('Student Skills Exchange',  'SkillX'),
    ('Skills Exchange',          'SkillX'),
    ('Skill Exchange',           'SkillX'),
    # page titles
    ('Skills Exchange -',        'SkillX -'),
    ('- Skills Exchange',        '- SkillX'),
]

for fname in os.listdir(frontend):
    if not fname.endswith('.html'):
        continue
    path = os.path.join(frontend, fname)
    with open(path, encoding='utf-8') as f:
        original = f.read()

    updated = original
    for old, new in replacements:
        updated = updated.replace(old, new)

    if updated != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated)
        changed.append(fname)
        print(f'  Updated: {fname}')

print(f'\nDone. {len(changed)} file(s) updated.')
