import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Mobile CSS Block
old_css_pattern = r'@media\s*\(max-width:\s*640px\)\s*\{.*?\.fc-theme-standard\s*\.fc-scrollgrid\s*\{\s*border:\s*none\s*!important;\s*\}\s*\}'
new_css = """@media (max-width: 640px) {
        /* Mobile Calendar Header - 2 Rows */
        .fc .fc-toolbar.fc-header-toolbar {
            display: grid !important;
            grid-template-areas: 
                "title title"
                "left right";
            grid-template-columns: 1fr 1fr;
            row-gap: 12px;
            align-items: center;
            margin-top: 20px !important;
            margin-bottom: 15px !important;
        }
        .fc .fc-toolbar-chunk:nth-child(1) { grid-area: left; justify-self: start; display: flex; gap: 4px; }
        .fc .fc-toolbar-chunk:nth-child(2) { grid-area: title; justify-self: center; }
        .fc .fc-toolbar-chunk:nth-child(3) { grid-area: right; justify-self: end; display: flex; gap: 4px; }
        
        .fc .fc-toolbar-title { font-size: 1.15rem !important; margin: 0 !important; white-space: nowrap !important; }
        .fc .fc-button { padding: 4px 8px !important; font-size: 0.75rem !important; height: auto !important; }
        .fc .fc-button .fc-icon { font-size: 1.1em !important; }

        /* Mobile Calendar Body - Portrait Dates */
        .fc .fc-daygrid-day-frame { min-height: 80px !important; } /* Taller rectangles */
        .fc-scroller { overflow-y: auto !important; } /* Allow native scroll down */
        
        /* Mobile Event Tags */
        .fc .fc-event { padding: 4px 0 !important; margin: 2px !important; border-radius: 4px !important; }
        .fc .fc-event-org { display: none !important; } /* Hide the org text on mobile */
        .fc .fc-event-time { font-size: 0.7rem !important; text-align: center; width: 100%; display: block; }
        .fc-theme-standard .fc-scrollgrid { border: none !important; }
    }"""
content = re.sub(old_css_pattern, new_css, content, flags=re.DOTALL)

# 2. Add eventContent hook in FullCalendar initialization
# Find where events: is defined
event_click_pattern = r'eventClick:\s*function\(info\)\s*\{'
event_content_injection = """eventContent: function(arg) {
                                let timeStr = arg.event.extendedProps.time || arg.event.extendedProps.start_time || '';
                                let orgStr = (arg.event.extendedProps.org || '').toUpperCase();
                                return {
                                    html: `<div class="fc-event-main-inner flex flex-col items-center justify-center w-full w-100" style="width:100%;">
                                        <div class="fc-event-time font-bold w-full text-center" style="font-size:inherit;">${timeStr}</div>
                                        <div class="fc-event-org font-bold w-full text-center sm:block" style="font-size:inherit;">${orgStr}</div>
                                    </div>`
                                };
                            },
                            eventClick: function(info) {"""
content = content.replace('eventClick: function(info) {', event_content_injection)

# Write it back
with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied mobile refinements.")
