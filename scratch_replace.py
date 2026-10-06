import re

with open('templates/admin_dashboard/event_records.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Calendar Modal Body
pattern = r'<!-- Calendar Body -->.*?</div>\s*</div>\s*</div>\s*</div>'
replacement = '''<!-- Calendar Body -->
            <div class="pt-16 p-4 sm:p-8 sm:pt-20 overflow-y-auto flex-grow bg-white dark:bg-pup-darkcard flex flex-col" style="background: var(--card-bg);">
                <div id="admin-calendar" class="w-full h-full min-h-[500px] flex-grow"></div>
            </div>'''
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('templates/admin_dashboard/event_records.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done replacing HTML body.")
