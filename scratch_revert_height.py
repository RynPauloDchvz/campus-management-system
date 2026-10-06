import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("height: window.innerWidth < 640 ? 'auto' : '100%',\n                            contentHeight: window.innerWidth < 640 ? 'auto' : undefined,", "height: '100%',")

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Reverted to 100% height")
