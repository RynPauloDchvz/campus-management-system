import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update HTML description to use parsedCalendarDescription
content = content.replace(
    "[[ selectedCalendarEvent.description || 'No description provided.' ]]",
    "[[ parsedCalendarDescription?.originalDesc || 'No description provided.' ]]"
)

# 2. Inject `parsedCalendarDescription` into the Vue setup
vue_logic = """
            const parsedCalendarDescription = computed(() => {
                if (!selectedCalendarEvent.value) return null;
                let desc = selectedCalendarEvent.value.description || "";
                if (!desc) return null;

                if (desc.includes("[RESCHEDULE]")) {
                    let origDescStr = desc;
                    desc.split('|').forEach(part => {
                        if(part.includes("Desc:")) origDescStr = part.split('Desc:')[1].trim();
                    });
                    return { originalDesc: origDescStr };
                }
                else if (desc.includes("[NEW EVENT]")) {
                    let origDescStr = desc;
                    desc.split('|').forEach(part => {
                        if(part.includes("Desc:")) origDescStr = part.split('Desc:')[1].trim();
                    });
                    return { originalDesc: origDescStr }; 
                }
                else {
                    return { originalDesc: desc };
                }
            });

            // Calendar Logic (FullCalendar)
"""
content = re.sub(r'// Calendar Logic \(FullCalendar\)', vue_logic.strip(), content)

# Export `parsedCalendarDescription`
content = content.replace(
    'isCalendarOpen, selectedCalendarEvent, openCalendarModal, closeCalendarModal,',
    'isCalendarOpen, selectedCalendarEvent, openCalendarModal, closeCalendarModal, parsedCalendarDescription,'
)

# 3. Update FullCalendar height for mobile
content = content.replace(
    "height: '100%'",
    "height: window.innerWidth < 640 ? 'auto' : '100%',\n                            contentHeight: window.innerWidth < 640 ? 'auto' : undefined,"
)

# 4. Inject CSS to optimize mobile layout for FullCalendar
css_injection = """
<style>
/* FullCalendar Mobile Optimizations */
@media (max-width: 640px) {
    /* Force header toolbar to one line */
    .fc .fc-toolbar.fc-header-toolbar {
        display: flex !important;
        flex-wrap: nowrap !important;
        gap: 0.25rem !important;
        padding: 0 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Shrink the month/year title */
    .fc .fc-toolbar-title {
        font-size: 1rem !important;
        line-height: 1.2 !important;
        white-space: nowrap !important;
    }
    
    /* Shrink the buttons (prev/next/today/month/week) */
    .fc .fc-button {
        padding: 0.25rem 0.5rem !important;
        font-size: 0.7rem !important;
        height: auto !important;
        white-space: nowrap !important;
    }

    /* Make calendar cells smaller but ensure they are visible without scrolling */
    .fc .fc-daygrid-day-frame {
        min-height: 40px !important;
    }

    /* Hide horizontal overflow to prevent any side scrolling */
    .fc-scroller {
        overflow: hidden !important;
    }

    /* Shrink event text so it fits */
    .fc .fc-event {
        font-size: 0.6rem !important;
        padding: 1px !important;
        line-height: 1.1 !important;
    }
    
    .fc-theme-standard .fc-scrollgrid {
        border: none !important;
    }
}
</style>
</head>
"""
content = content.replace("</head>", css_injection.strip())

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated event_approvals.html with parsing and mobile layout fixes.")
