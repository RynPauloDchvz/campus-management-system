import re

with open('templates/admin_dashboard/event_records.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Vue import
content = content.replace("const { createApp, ref, computed, onMounted } = Vue;", "const { createApp, ref, computed, onMounted, nextTick } = Vue;")

# Replace the open/close button
content = content.replace('@click="isCalendarOpen = true"', '@click="openCalendarModal"')

# Replace the Calendar Logic
pattern_logic = r'// Calendar Logic\s+const currentMonth = ref.*?const nextMonth = \(\) => \{.*?\};'
replacement_logic = '''// Calendar Logic (FullCalendar)
            let calendarInstance = null;
            
            const openCalendarModal = (e) => {
                isCalendarOpen.value = true;
                document.body.style.overflow = 'hidden';
                
                nextTick(() => {
                    if (!calendarInstance) {
                        const calEl = document.getElementById('admin-calendar');
                        calendarInstance = new FullCalendar.Calendar(calEl, {
                            initialView: 'dayGridMonth',
                            headerToolbar: {
                                left: 'prev,next today',
                                center: 'title',
                                right: 'dayGridMonth,timeGridWeek'
                            },
                            themeSystem: 'standard',
                            events: historyEvents.value.filter(e => e.status !== 'REJECTED').map(evt => {
                                let bgColor = 'rgba(107, 114, 128, 0.1)';
                                let textColor = '#6b7280';
                                
                                const orgUpper = (evt.org || '').toUpperCase();
                                if (orgUpper === 'ITO') { bgColor = '#800000'; textColor = '#ffffff'; }
                                else if (orgUpper === 'BEED') { bgColor = '#2563eb'; textColor = '#ffffff'; }
                                else if (orgUpper === 'YEO') { bgColor = '#eab308'; textColor = '#000000'; }
                                else if (orgUpper === 'ITS') { bgColor = '#000000'; textColor = '#ffffff'; }
                                else if (orgUpper === 'BPA') { bgColor = '#dc2626'; textColor = '#ffffff'; }
                                else if (orgUpper === 'FTO') { bgColor = '#2563eb'; textColor = '#ffffff'; }
                                else { bgColor = '#6b7280'; textColor = '#ffffff'; }
                                
                                let displayTime = evt.time || evt.start_time || '';
                                const displayTitle = `${displayTime} ${orgUpper}`.trim().toUpperCase();
                                
                                let formattedDate = evt.date;
                                try {
                                    const d = new Date(evt.date);
                                    if(!isNaN(d)) {
                                        formattedDate = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
                                    }
                                } catch(e) {}
                                
                                return {
                                    id: evt.id,
                                    title: displayTitle,
                                    start: formattedDate,
                                    allDay: true,
                                    display: 'block',
                                    backgroundColor: bgColor,
                                    borderColor: bgColor,
                                    textColor: textColor,
                                    extendedProps: evt
                                };
                            }),
                            eventClick: function(info) {
                                selectedCalendarEvent.value = info.event.extendedProps;
                            },
                            height: '100%'
                        });
                    }
                    calendarInstance.render();
                    setTimeout(() => {
                        if (calendarInstance) calendarInstance.updateSize();
                    }, 400);
                });
            };

            const closeCalendarModal = () => {
                isCalendarOpen.value = false;
                document.body.style.overflow = '';
            };'''
content = re.sub(pattern_logic, replacement_logic, content, flags=re.DOTALL)

# Replace the returned variables
content = content.replace("currentMonth, currentYear, monthNames, calendarDays, prevMonth, nextMonth, isCalendarOpen, selectedCalendarEvent,", "isCalendarOpen, selectedCalendarEvent, openCalendarModal, closeCalendarModal,")

with open('templates/admin_dashboard/event_records.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done replacing Vue script.")
