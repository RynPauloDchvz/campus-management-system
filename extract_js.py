import re

with open(r'e:\Users\rynwl\Desktop\(V2) PUPUni-CAMS\templates\organizer\school_events.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract script blocks
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(scripts):
    with open(f'script_{i}.js', 'w', encoding='utf-8') as sf:
        sf.write(script)
print(f"Extracted {len(scripts)} scripts.")
