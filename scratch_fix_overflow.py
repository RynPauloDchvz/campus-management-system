import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix horizontal scrolling and ensure grid fits 100% width
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
            width: 100% !important;
        }
        .fc .fc-toolbar-chunk:nth-child(1) { grid-area: left; justify-self: start; display: flex; gap: 4px; }
        .fc .fc-toolbar-chunk:nth-child(2) { grid-area: title; justify-self: center; }
        .fc .fc-toolbar-chunk:nth-child(3) { grid-area: right; justify-self: end; display: flex; gap: 4px; }
        
        .fc .fc-toolbar-title { font-size: 1.15rem !important; margin: 0 !important; white-space: nowrap !important; }
        .fc .fc-button { padding: 4px 8px !important; font-size: 0.75rem !important; height: auto !important; }
        .fc .fc-button .fc-icon { font-size: 1.1em !important; }

        /* Mobile Calendar Body - Portrait Dates */
        .fc .fc-daygrid-day-frame { min-height: 80px !important; } /* Taller rectangles */
        .fc-scroller { overflow-y: auto !important; overflow-x: hidden !important; } /* Force vertical scroll, prevent horizontal */
        .fc-scrollgrid { width: 100% !important; table-layout: fixed !important; }
        .fc-view-harness { width: 100% !important; max-width: 100vw !important; overflow-x: hidden !important; }
        
        /* Mobile Event Tags */
        .fc .fc-event { padding: 4px 0 !important; margin: 2px 1px !important; border-radius: 4px !important; }
        .fc .fc-event-org { display: none !important; } /* Hide the org text on mobile */
        .fc .fc-event-time { font-size: 0.6rem !important; text-align: center; width: 100%; display: block; overflow: hidden; white-space: nowrap; text-overflow: clip; }
        .fc-theme-standard .fc-scrollgrid { border: none !important; }
    }"""

old_css_pattern = r'@media\s*\(max-width:\s*640px\)\s*\{.*?\.fc-theme-standard\s*\.fc-scrollgrid\s*\{\s*border:\s*none\s*!important;\s*\}\s*\}'
content = re.sub(old_css_pattern, new_css, content, flags=re.DOTALL)

# Also fix the padding on the calendar body to give it maximum width on mobile
# Replace class="pt-16 p-4 sm:p-8 sm:pt-20 overflow-hidden flex-grow bg-white dark:bg-pup-darkcard flex flex-col"
content = content.replace(
    'class="pt-16 p-4 sm:p-8 sm:pt-20 overflow-hidden flex-grow bg-white dark:bg-pup-darkcard flex flex-col"',
    'class="pt-16 p-1 sm:p-8 sm:pt-20 overflow-hidden flex-grow bg-white dark:bg-pup-darkcard flex flex-col"'
)

# And fix the close button positioning since padding is reduced
content = content.replace(
    '<button @click="closeCalendarModal" class="absolute top-4 right-4 sm:top-6 sm:right-6',
    '<button @click="closeCalendarModal" class="absolute top-4 right-2 sm:top-6 sm:right-6'
)
content = content.replace(
    '<div class="absolute top-4 left-4 sm:top-6 sm:left-6 z-40">',
    '<div class="absolute top-4 left-2 sm:top-6 sm:left-6 z-40">'
)

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied fix for horizontal clipping.")
