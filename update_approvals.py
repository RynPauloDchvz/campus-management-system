import sys

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove History Log Section
history_start = content.find('<!-- 🎯 HISTORY LOG SECTION 🎯 -->')
modal_start = content.find('<!-- 🏛️ MAIN APPROVAL/RECORD MODAL 🏛️ -->')
if history_start != -1 and modal_start != -1:
    content = content[:history_start] + content[modal_start:]

# 2. Add Vue setup reactive variable
setup_idx = content.find('setup() {')
if setup_idx != -1 and 'isSearchActive' not in content:
    content = content[:setup_idx+9] + '\n                const isSearchActive = ref(false);' + content[setup_idx+9:]
    
return_idx = content.find('return {')
if return_idx != -1 and 'isSearchActive' not in content[return_idx:return_idx+100]:
    content = content[:return_idx+8] + '\n                    isSearchActive,' + content[return_idx+8:]

# 3. Replace pending-header-controls HTML
# Let's find exactly the pending header controls div.
header_start = content.find('<div class="pending-header-controls"')
# Find the closing </div> of this block. It's before <!-- 🎯 PENDING APPROVALS LIST 🎯 --> or something, but actually we can just look for the first </button> or </div>...
# Wait, let's use exact string matching for safety.
old_html = '''<div class="pending-header-controls" style="display: flex; align-items: center; gap: 15px; flex-wrap: nowrap; flex-grow: 1; justify-content: flex-end;">
                            <div class="search-box" style="flex-grow: 1; max-width: none;">
                                <i class="ph-bold ph-magnifying-glass" style="color: var(--text-muted);"></i>
                                <input type="text" v-model="searchPending" class="search-input" placeholder="Search pending event org org name e.g FTO Assembly">
                            </div>
                            
                            <!-- View Calendar Button -->
                            <button @click="isCalendarOpen = true" class="calendar-btn pending-calendar-btn" style="flex-shrink: 0;">
                                <i class="ph-bold ph-calendar"></i> <span class="hide-on-mobile">VIEW EVENT CALENDAR</span>
                            </button>
                        </div>'''

new_html = '''<div class="pending-header-controls mobile-search-controls" style="display: flex; align-items: center; gap: 15px; flex-wrap: nowrap; flex-grow: 1; justify-content: flex-end;">
                            <!-- SEARCH COMPONENT -->
                            <div class="search-box-wrapper" :class="{'is-active': isSearchActive}">
                                <button class="mobile-search-trigger action-btn theme-action-btn" @click.stop="isSearchActive = true; $nextTick(() => $refs.mobileSearchInput.focus())">
                                    <i class="ph-bold ph-magnifying-glass"></i>
                                </button>
                                
                                <div class="search-box desktop-search-box">
                                    <i class="ph-bold ph-magnifying-glass search-icon"></i>
                                    <input type="text" ref="mobileSearchInput" v-model="searchPending" class="search-input" placeholder="Search pending event org org name e.g FTO Assembly" @blur="isSearchActive = false">
                                </div>
                            </div>

                            <!-- RIGHT ICONS -->
                            <div class="right-action-icons">
                                <button @click="isCalendarOpen = true" class="calendar-btn pending-calendar-btn toggle-icon">
                                    <i class="ph-bold ph-calendar"></i> <span class="hide-on-mobile">VIEW EVENT CALENDAR</span>
                                </button>
                                <a href="{% url 'event_records' %}" class="action-btn theme-action-btn toggle-icon" style="text-decoration: none;">
                                    <i class="ph-bold ph-clock-counter-clockwise"></i> <span class="hide-on-mobile">EVENT RECORDS</span>
                                </a>
                            </div>
                        </div>'''

if old_html in content:
    content = content.replace(old_html, new_html)
else:
    # Try finding it dynamically if spacing differs
    end_btn = content.find('VIEW EVENT CALENDAR</span>\n                            </button>\n                        </div>')
    if header_start != -1 and end_btn != -1:
        end_idx = end_btn + len('VIEW EVENT CALENDAR</span>\n                            </button>\n                        </div>')
        content = content[:header_start] + new_html + content[end_idx:]

# 4. Insert custom CSS at the end of the <style> block
custom_css = '''
/* Base input padding to fix desktop overlap */
.search-input {
    padding-left: 45px !important;
}

/* Desktop defaults */
.search-box-wrapper {
    flex-grow: 1;
    display: flex;
    align-items: center;
}
.mobile-search-trigger {
    display: none !important;
}
.desktop-search-box {
    flex-grow: 1;
    display: flex;
    align-items: center;
    position: relative;
    max-width: none;
    background: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0 15px;
}
.search-icon {
    position: absolute; left: 15px; top: 50%; transform: translateY(-50%); z-index: 10; color: var(--text-muted);
}
.right-action-icons {
    display: flex;
    gap: 15px;
    align-items: center;
    flex-shrink: 0;
}

@media (max-width: 768px) {
    .pending-header-controls {
        gap: 8px !important;
    }
    
    .right-action-icons {
        gap: 8px !important;
    }
    
    .search-box-wrapper {
        justify-content: flex-start;
    }
    
    /* Make all 3 icons identical squares */
    .mobile-search-trigger,
    .right-action-icons .action-btn, 
    .right-action-icons .calendar-btn {
        display: flex !important;
        width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        flex-shrink: 0;
    }
    
    .mobile-search-trigger i,
    .right-action-icons .action-btn i, 
    .right-action-icons .calendar-btn i {
        margin: 0 !important;
        font-size: 1.1rem;
    }
    
    .search-box-wrapper.is-active .mobile-search-trigger {
        display: none !important;
    }
    
    /* Pop-up search bar animation */
    .desktop-search-box {
        display: flex !important;
        max-width: 0;
        opacity: 0;
        overflow: hidden;
        white-space: nowrap;
        transition: max-width 0.4s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
        margin: 0 !important;
        padding: 0 !important;
        border-width: 0 !important;
        background: transparent !important;
    }
    
    .search-box-wrapper.is-active .desktop-search-box {
        max-width: 100%;
        opacity: 1;
        padding: 0 15px !important;
        border-width: 1px !important;
        background: var(--input-bg) !important;
    }
    
    .desktop-search-box .search-input {
        width: 100%;
        min-width: 100px;
        background: transparent !important;
        color: var(--text-main) !important;
    }
    
    .hide-on-mobile { display: none !important; }
}
'''
style_end = content.find('</style>')
if style_end != -1 and 'mobile-search-trigger' not in content:
    content = content[:style_end] + custom_css + content[style_end:]

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Restore complete.')
