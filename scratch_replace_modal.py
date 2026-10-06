import re

with open('templates/admin_dashboard/event_approvals.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the double scrollbar
content = content.replace(
    'class="pt-16 p-4 sm:p-8 sm:pt-20 overflow-y-auto flex-grow bg-white dark:bg-pup-darkcard flex flex-col"',
    'class="pt-16 p-4 sm:p-8 sm:pt-20 overflow-hidden flex-grow bg-white dark:bg-pup-darkcard flex flex-col"'
)

# 2. Replace the Calendar Event Details Modal
pattern = r'<!-- Calendar Event Details Modal -->.*?</div>\s*</div>\s*</div>'

replacement = """<!-- Calendar Event Details Modal -->
                <div v-if="selectedCalendarEvent" v-cloak class="absolute inset-0 bg-black/80 z-[7000] flex items-center justify-center p-0 sm:p-6 backdrop-blur-md animate-fade-in" @click.self="selectedCalendarEvent = null" style="position: absolute; inset: 0; background: rgba(0,0,0,0.8); z-index: 7000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(12px);">
                    <div class="bg-white dark:bg-[#151515] w-full h-full sm:max-w-2xl sm:max-h-[90vh] sm:rounded-3xl shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-800 flex flex-col relative transform transition-all" style="background: var(--card-bg);">
                        <!-- Close Button -->
                        <button @click="selectedCalendarEvent = null" class="absolute top-4 right-4 w-10 h-10 rounded-full bg-black/50 hover:bg-red-600 text-white flex items-center justify-center transition-colors z-10 backdrop-blur-sm border border-white/20">
                            <i class="ph-bold ph-x text-lg"></i>
                        </button>
                        
                        <div class="flex-grow overflow-y-auto hide-scrollbar custom-scrollbar">
                            <!-- Cover Photo Header -->
                            <div class="h-64 sm:h-72 w-full relative bg-gray-900 flex-shrink-0">
                                <img v-if="selectedCalendarEvent.event_cover_photo" 
                                     :src="selectedCalendarEvent.event_cover_photo" 
                                     class="w-full h-full object-cover opacity-90">
                                <div v-else class="w-full h-full flex items-center justify-center bg-gray-800">
                                    <i class="ph-fill ph-image text-4xl text-gray-600"></i>
                                </div>
                                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
                                <div class="absolute bottom-6 left-6 right-6">
                                    <div class="bg-pup-maroon text-white dark:bg-pup-gold dark:text-black inline-block font-black text-[0.65rem] px-3 py-1 rounded-full uppercase mb-2 shadow-sm border border-pup-maroon/30 dark:border-pup-gold/30">
                                        [[ selectedCalendarEvent.org ]]
                                    </div>
                                    <h2 class="text-3xl sm:text-4xl font-black text-white leading-tight">[[ selectedCalendarEvent.title ]]</h2>
                                </div>
                            </div>

                            <!-- Details Content -->
                            <div class="p-6 sm:p-8">
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8 bg-gray-50 dark:bg-black/30 p-5 rounded-2xl border border-gray-100 dark:border-gray-800">
                                    <div>
                                        <div class="text-xs font-bold uppercase text-gray-400 mb-1">Date & Time</div>
                                        <div class="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                            <i class="ph-fill ph-calendar text-pup-maroon dark:text-pup-gold text-lg"></i> 
                                            [[ selectedCalendarEvent.date ]]
                                            [[ selectedCalendarEvent.time ? ' • ' + selectedCalendarEvent.time : '' ]]
                                        </div>
                                    </div>
                                    <div>
                                        <div class="text-xs font-bold uppercase text-gray-400 mb-1">Venue</div>
                                        <div class="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                            <i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold text-lg"></i> 
                                            [[ selectedCalendarEvent.venue || 'TBA' ]]
                                        </div>
                                    </div>
                                </div>
                                
                                <h3 class="font-black text-[9px] text-gray-400 uppercase tracking-[0.4em] mb-4 border-b border-gray-100 dark:border-gray-800 pb-3">Activity Description</h3>
                                <p class="text-gray-500 dark:text-gray-400 text-xs leading-relaxed text-justify mb-10 font-medium whitespace-pre-wrap">[[ selectedCalendarEvent.description || 'No description provided.' ]]</p>
                            </div>
                        </div>
                    </div>
                </div>"""

# Ensure we only replace the target section. Wait, there's `<!-- MODAL FOOTERS -->` after the modal block in event_approvals.html. 
# We need to make sure we don't accidentally swallow it if the regex matches too far.
# Let's see event_approvals.html exactly.

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('templates/admin_dashboard/event_approvals.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Modal replaced successfully")
