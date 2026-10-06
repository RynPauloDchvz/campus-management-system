import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the Mobile CSS
new_css = """@media (max-width: 640px) {
        .fc .fc-toolbar.fc-header-toolbar {
            flex-wrap: wrap;
            gap: 10px;
            justify-content: space-between;
            margin-top: 15px !important;
        }
        .fc .fc-toolbar-chunk:nth-child(2) {
            order: -1;
            width: 100%;
            text-align: center;
        }
        .fc .fc-toolbar-title {
            font-size: 1.2rem !important;
        }
        .fc .fc-button {
            padding: 6px 10px !important;
            font-size: 0.75rem !important;
        }
        
        /* Make calendar cells portrait */
        .fc .fc-daygrid-day-frame { min-height: 90px !important; } 
    }"""
old_css_pattern = r'@media\s*\(max-width:\s*640px\)\s*\{.*?\.fc-theme-standard\s*\.fc-scrollgrid\s*\{\s*border:\s*none\s*!important;\s*\}\s*\}'
content = re.sub(old_css_pattern, new_css, content, flags=re.DOTALL)

# 2. Fix the eventContent hook
# Find the current eventContent block
old_event_content = r'eventContent: function\(arg\) \{.*?\},'
new_event_content = """eventContent: function(arg) {
                                let timeStr = arg.event.extendedProps.time || arg.event.extendedProps.start_time || '';
                                let orgStr = (arg.event.extendedProps.org || '').toUpperCase();
                                return {
                                    html: `<div class="truncate" style="width: 100%;">
                                        <span class="font-bold">${timeStr}</span><span class="font-bold hidden sm:inline"> ${orgStr}</span>
                                    </div>`
                                };
                            },"""
content = re.sub(old_event_content, new_event_content, content, flags=re.DOTALL)

# Write it back
with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied final mobile fixes.")
