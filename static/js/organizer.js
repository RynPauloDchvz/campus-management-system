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
                hasNotification: true, 
                isMobileMenuOpen: false,
                currentUrl: window.VUE_APP_DATA?.currentUrl || '',
                
                // --- 📱 Bottom Nav Configuration 📱 ---
                navItems: [
                    { name: 'Home', label: 'Home', icon: 'ph ph-house', iconActive: 'ph-fill ph-house', url: window.VUE_APP_DATA?.urls?.homepage },
                    { name: 'Events', label: 'Events', icon: 'ph ph-ticket', iconActive: 'ph-fill ph-ticket', url: window.VUE_APP_DATA?.urls?.school_events },
                    { name: 'Create', label: 'Create', icon: 'ph ph-plus-circle', iconActive: 'ph-fill ph-plus-circle', url: window.VUE_APP_DATA?.urls?.create_events },
                    { name: 'Messages', label: 'Messages', icon: 'ph ph-bell', iconActive: 'ph-fill ph-bell', url: window.VUE_APP_DATA?.urls?.messages },
                    { name: 'Students', label: 'Students', icon: 'ph ph-users', iconActive: 'ph-fill ph-users', url: window.VUE_APP_DATA?.urls?.manage_students },
                    { name: 'Attendance', label: 'Attendance', icon: 'ph ph-fingerprint', iconActive: 'ph-fill ph-fingerprint', url: window.VUE_APP_DATA?.urls?.manage_attendance },
                    { name: 'Analytics', label: 'Analytics', icon: 'ph ph-chart-bar', iconActive: 'ph-fill ph-chart-bar', url: window.VUE_APP_DATA?.urls?.analytics },
                    { name: 'Theme', label: 'Mode', icon: 'ph ph-moon', iconActive: 'ph-fill ph-sun', url: null }
                ],
                
                // --- 📱 Bottom Nav State 📱 ---
                navRefs: [],
                indicatorOffset: 0,
                indicatorWidth: 0,
                activeIndex: -1,
                showLeftArrow: false,
                showRightArrow: true,

                // --- 📊 State 📊 ---
                isEventModalOpen: false,
                selectedEvent: {}, 
                latestNews: window.VUE_APP_DATA?.latestNews || []
            }
        },
        created() {
            const urlToIndex = {
                'organizer_homepage': 0,
                'organizer_school_events': 1,
                'organizer_create_events': 2,
                'organizer_message_history': 3,
                'organizer_manage_students': 4,
                'organizer_manage_attendance': 5,
                'organizer_analytics': 6
            };
            this.activeIndex = urlToIndex[this.currentUrl] !== undefined ? urlToIndex[this.currentUrl] : -1;
        },
        mounted() {
            // Safety: Ensure loading always clears
            setTimeout(() => { 
                this.isLoading = false; 
            }, 800);

            const savedTheme = localStorage.getItem('theme') || 'light';
            this.isDark = (savedTheme === 'dark');
            document.documentElement.classList.toggle('dark', this.isDark);

            this.initIndicator();
            window.addEventListener('resize', () => {
                if (this.activeIndex !== -1) this.calculatePosition(this.activeIndex);
            });
        },
        methods: {
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
                });
            },
            calculatePosition(index) {
                if (index === -1 || index >= this.navItems.length - 1) {
                    this.indicatorWidth = 0;
                    return;
                }
                const el = this.navRefs[index];
                if (el) {
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
                this.calculatePosition(this.activeIndex);
            },
            triggerLogout() {
                this.showProfileBubble = false;
                this.isLogoutModalOpen = true;
            },
            getStaticImageUrl(filename) {
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
            closeModal() {
                this.isEventModalOpen = false;
                document.body.style.overflow = ''; 
            }
        }
    });

    app.mount('#app');

});
