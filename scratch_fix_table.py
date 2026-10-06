import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add the fix for the global table min-width
fix = "\n    /* Fix global table min-width affecting FullCalendar */\n    .fc table { min-width: 0 !important; }\n"
content = content.replace('/* Event tags */', fix + '\n    /* Event tags */')

# Make sure the mobile CSS is still intact and matches requirements
# The user wants "portrait rectangle"
# But they said "RECTANGLE NA AKO NG RECTANGLE SHAPE TAPOS PORTRAIT YUNG RECTANGLE PERO BOX PA DIN"
# If the table was 700px wide (100px per column), and min-height was 90px... it was 100x90, which looks like a box!
# Now that we remove the 700px min-width, on a 375px screen it will be ~50px wide. 
# 50px width x 90px height = definitely a portrait rectangle!

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied table min-width override.")
