// static/js/organizer.js

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // 1. VUE.JS APPLICATION (CENTRALIZED)
    // ==========================================
    const { createApp } = Vue;

    const app = createApp({
        delimiters: ['[[', ']]'],
        data() {
            return {
                isDark: false,
                isLoading: true,
                showProfileBubble: false,
                isLogoutModalOpen: false,
                // --- ?? Notification System ?? ---
                unreadNotifCount: 0,
                allNotifs: [],
                readNotifs: JSON.parse(localStorage.getItem('organizer_read_notifs') || '[]'),
                popupBanners: [],
                shownBannerIds: JSON.parse(sessionStorage.getItem('organizer_shown_banners') || '[]'),
                isMsgModalOpen: false,
                currentMsg: {},

                // --- ?? State ?? ---
                isEventModalOpen: false,
                selectedEvent: {}, 
                latestNews: window.VUE_APP_DATA?.latestNews || [],
                managedEvents: window.VUE_APP_DATA?.managedEvents || [],
                calendarEvents: window.VUE_APP_DATA?.calendarEvents || [],
                filteredCalendarEvents: [],
                actionRequired: window.VUE_APP_DATA?.actionRequired || null
            }
        },
        created() {
            const urlToIndex = {
                'organizer_homepage': 0,
                'organizer_school_events': 1,
                'organizer_create_events': 2,
                'organizer_manage_students': 3,
                'organizer_manage_attendance': 4,
                'organizer_analytics': 5
            };
            this.activeIndex = urlToIndex[this.currentUrl] !== undefined ? urlToIndex[this.currentUrl] : -1;
            
            // Initialize filteredCalendarEvents for current month
            const now = new Date();
            this.filteredCalendarEvents = this.calendarEvents.filter(e => {
                const d = new Date(e.date);
                return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
            });
        },
        mounted() {
            // Safety: Ensure loading always clears
            setTimeout(() => { 
                this.isLoading = false; 
            }, 800);

            const savedTheme = localStorage.getItem('theme') || 'light';
            this.isDark = (savedTheme === 'dark');
            document.documentElement.classList.toggle('dark', this.isDark);

            this.fetchNotifications();
            setInterval(this.fetchNotifications, 10000);

            this.initIndicator();
            window.addEventListener('resize', () => {
                if (this.activeIndex !== -1) this.calculatePosition(this.activeIndex);
            });

            // Global logic to handle search redirection from banner
            if (this.currentUrl === 'organizer_school_events') {
                const searchQuery = sessionStorage.getItem('eventSearchQuery');
                if (searchQuery) {
                    setTimeout(() => {
                        const searchInput = document.getElementById('eventSearch');
                        if (searchInput) {
                            searchInput.value = searchQuery;
                            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        sessionStorage.removeItem('eventSearchQuery');
                    }, 500);
                }
            }
        },
        methods: {
            async fetchNotifications() {
                try {
                    const response = await fetch('/organizer/api/notifications/');
                    const data = await response.json();
                    if (data.status === 'success') {
                        this.allNotifs = data.notifications;
                        
                        // Kung nasa message history page, i-mark lahat bilang read automatic
                        if (this.currentUrl === 'organizer_message_history') {
                            this.markAllAsRead();
                        }
                        
                        this.updateNotificationState();
                    }
                } catch (error) {
                    console.error('Error fetching notifications:', error);
                }
            },
            updateNotificationState() {
                const unread = this.allNotifs.filter(n => !this.readNotifs.includes(n.id));
                this.unreadNotifCount = unread.length;

                // New unread that haven't been shown as banners
                const newNotifs = unread.filter(n => !this.shownBannerIds.includes(n.id));
                
                if (newNotifs.length > 0) {
                    this.popupBanners = [...newNotifs, ...this.popupBanners].slice(0, 5);
                    newNotifs.forEach(n => this.shownBannerIds.push(n.id));
                    sessionStorage.setItem('organizer_shown_banners', JSON.stringify(this.shownBannerIds));

                    newNotifs.forEach(n => {
                        setTimeout(() => { this.closeBanner(n.id); }, 8000);
                    });
                }
            },
            markAllAsRead() {
                const allIds = this.allNotifs.map(n => n.id);
                // Merge current readNotifs with allIds to ensure everything is marked
                this.readNotifs = [...new Set([...this.readNotifs, ...allIds])];
                localStorage.setItem('organizer_read_notifs', JSON.stringify(this.readNotifs));
                this.unreadNotifCount = 0;
            },
            closeBanner(id) {
                this.popupBanners = this.popupBanners.filter(b => b.id !== id);
            },
            handleBannerClick(banner) {
                if (!this.readNotifs.includes(banner.id)) {
                    this.readNotifs.push(banner.id);
                    localStorage.setItem('organizer_read_notifs', JSON.stringify(this.readNotifs));
                }
                this.unreadNotifCount = this.allNotifs.filter(n => !this.readNotifs.includes(n.id)).length;
                
                // Logic based on title for redirection
                const title = banner.title.toLowerCase();
                const msg = banner.message.toLowerCase();
                
                if (title.includes('attendance') || msg.includes('attendance')) {
                    let eventName = '';
                    const match = banner.message.match(/for "(.*?)"/);
                    if (match) eventName = match[1];
                    if (eventName) sessionStorage.setItem('eventSearchQuery', eventName);
                    window.location.href = window.VUE_APP_DATA?.urls?.school_events || '/organizer/school-events/';
                } else if (title.includes('student') || msg.includes('student')) {
                    window.location.href = window.VUE_APP_DATA?.urls?.manage_students || '/organizer/manage-students/';
                } else if (title.includes('event') || msg.includes('event')) {
                    window.location.href = window.VUE_APP_DATA?.urls?.school_events || '/organizer/school-events/';
                } else {
                    window.location.href = window.VUE_APP_DATA?.urls?.messages || '/organizer/messages/';
                }
                
                this.closeBanner(banner.id);
            },
            openNotifications() {
                this.markAllAsRead();
                window.location.href = window.VUE_APP_DATA?.urls?.messages || '/organizer/messages/';
            },
            getNotifBorderClass(type, status) {
                if (status === 'Approved') return 'border-l-green-500';
                if (status === 'Rejected' || type === 'alert') return 'border-l-red-500';
                return 'border-l-blue-500';
            },
            getIconClass(type) {
                if (type === 'event') return 'ph-calendar-star';
                if (type === 'alert') return 'ph-warning-circle';
                return 'ph-megaphone';
            },
            getIconBgClass(type) {
                if (type === 'event') return 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400 border-green-200 dark:border-green-800';
                if (type === 'alert') return 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400 border-red-200 dark:border-red-800';
                return 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 border-blue-200 dark:border-blue-800';
            },
            handleHeaderProfileClick() {
                if (window.innerWidth >= 1024) {
                    window.location.href = window.VUE_APP_DATA?.urls?.profile || '#';
                } else {
                    this.showProfileBubble = !this.showProfileBubble;
                }
            },
            toggleTheme() {
                this.isDark = !this.isDark;
                document.documentElement.classList.toggle('dark', this.isDark);
                localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
            },
            toggleMobileMenu() {
                this.isMobileMenuOpen = !this.isMobileMenuOpen;
            },
            setNavRef(index, el) {
                if (el) this.navRefs[index] = el;
            },
            initIndicator() {
                this.$nextTick(() => {
                    if (this.activeIndex === -1) return;
                    setTimeout(() => this.calculatePosition(this.activeIndex), 250);
                    setTimeout(() => this.calculatePosition(this.activeIndex), 600);
                });
            },
            calculatePosition(index) {
                if (index === -1 || index >= this.navItems.length - 1) {
                    this.indicatorWidth = 0;
                    return;
                }
                const el = this.navRefs[index];
                if (el) {
                    // Because the indicator is now inside the flex container,
                    // we use offsetLeft relative to the parent, ignoring scroll.
                    this.indicatorWidth = el.offsetWidth - 10;
                    this.indicatorOffset = el.offsetLeft + 5;
                }
            },
            handleNavClick(item, index) {
                if (item.name === 'Theme') {
                    this.toggleTheme();
                } else {
                    this.activeIndex = index;
                    this.calculatePosition(index);
                    if (item.url) {
                        setTimeout(() => { window.location.href = item.url; }, 250);
                    }
                }
            },
            handleNavScroll(e) {
                const el = e.target;
                this.showLeftArrow = el.scrollLeft > 10;
                this.showRightArrow = el.scrollLeft < (el.scrollWidth - el.clientWidth - 10);
            },
            triggerLogout() {
                this.showProfileBubble = false;
                this.isLogoutModalOpen = true;
            },
            getStaticImageUrl(filename) {
                if (!filename) return window.DEFAULT_LOGO;
                if (filename.startsWith('/') || filename.startsWith('http')) return filename;
                return window.STATIC_IMAGES_BASE + filename;
            },
            handleImageError(event) {
                event.target.src = window.DEFAULT_LOGO;
            },
            openEventModal(eventData) {
                this.selectedEvent = eventData;
                this.isEventModalOpen = true;
                document.body.style.overflow = 'hidden'; 
            },
            handleCalendarEventClick(evt) {
                // Call the global function defined in homepage.html
                if (window.handleCalendarEventClick) {
                    window.handleCalendarEventClick(evt);
                }
            },
            getMonth(dateStr) {
                const date = new Date(dateStr);
                return date.toLocaleString('en-US', { month: 'short' });
            },
            getDay(dateStr) {
                const date = new Date(dateStr);
                return date.getDate();
            },
            closeModal() {
                this.isEventModalOpen = false;
                document.body.style.overflow = ''; 
            }
        }
    });

    app.mount('#app');

});
