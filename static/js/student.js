// static/js/student_home.js

document.addEventListener('DOMContentLoaded', () => {
    // Kung may specific na Vanilla JS ka para sa dashboard (tulad ng pag-fetch ng data), dito ilalagay.
    console.log("Student Dashboard Loaded Successfully.");

    // Simple function para sa pag-navigate ng mga Quick Action cards
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            if(url) {
                window.location.href = url;
            }
        });
    });
});

// static/js/student.js

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // PROFILE LOGIC
    // ==========================================
    let isEditing = false;
    
    window.toggleEditMode = function() {
        isEditing = !isEditing;
        
        const btn = document.getElementById('editBtn');
        const yearDisplay = document.getElementById('yearDisplay');
        const yearEditContainer = document.getElementById('yearEditContainer');
        const yearSelect = document.getElementById('yearSelect');
        
        const avatarWrapper = document.getElementById('avatarWrapper');
        const coverWrapper = document.getElementById('coverPhotoWrapper');

        if (isEditing) {
            // Change button to SAVE
            btn.innerHTML = 'Save Profile';
            btn.classList.replace('bg-[#800000]', 'bg-green-600');
            
            // Enable Image Edit Overlays
            avatarWrapper.classList.add('editable-mode');
            coverWrapper.classList.add('editable-mode');
            
            // Show Dropdown for Year Level
            yearDisplay.classList.add('hidden');
            yearEditContainer.classList.remove('hidden');
        } else {
            // Revert button to EDIT
            btn.innerHTML = 'Edit Profile';
            btn.classList.replace('bg-green-600', 'bg-[#800000]');
            
            // Disable Image Edit Overlays
            avatarWrapper.classList.remove('editable-mode');
            coverWrapper.classList.remove('editable-mode');
            
            // Save Dropdown Value to Text
            yearDisplay.innerText = yearSelect.value;
            yearDisplay.classList.remove('hidden');
            yearEditContainer.classList.add('hidden');
        }
    };

    // Trigger File Inputs
    window.triggerImageUpload = function() {
        if (isEditing) document.getElementById('profileFileInput').click();
    };

    window.triggerCoverUpload = function() {
        if (isEditing) document.getElementById('coverFileInput').click();
    };

    // Preview Uploaded Images
    window.previewImage = function(event, targetId) {
        const reader = new FileReader();
        reader.onload = function() { 
            document.getElementById(targetId).src = reader.result; 
        };
        if(event.target.files[0]) reader.readAsDataURL(event.target.files[0]);
    };

    // ==========================================
    // LOGOUT MODAL LOGIC
    // ==========================================
    window.openLogoutModal = function() {
        document.getElementById('logoutModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeLogoutModal = function() {
        document.getElementById('logoutModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    window.performLogout = function() {
        window.location.href = '/'; 
    };

});

// static/js/student.js

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // 1. PROFILE LOGIC
    // ==========================================
    let isEditing = false;
    
    window.toggleEditMode = function() {
        isEditing = !isEditing;
        const btn = document.getElementById('editBtn');
        const yearDisplay = document.getElementById('yearDisplay');
        const yearEditContainer = document.getElementById('yearEditContainer');
        const yearSelect = document.getElementById('yearSelect');
        const avatarWrapper = document.getElementById('avatarWrapper');
        const coverWrapper = document.getElementById('coverPhotoWrapper');

        if (isEditing) {
            btn.innerHTML = '<i class="ph-bold ph-floppy-disk text-lg"></i> <span class="hidden sm:inline">Save Profile</span><span class="sm:hidden">Save</span>';
            btn.classList.replace('bg-[#800000]', 'bg-green-600');
            if (btn.classList.contains('dark:bg-[#D4AF37]')) {
                btn.classList.replace('dark:bg-[#D4AF37]', 'dark:bg-green-500');
                btn.classList.replace('dark:text-black', 'dark:text-white');
            }
            avatarWrapper.classList.add('editable-mode');
            coverWrapper.classList.add('editable-mode');
            yearDisplay.classList.add('hidden');
            yearEditContainer.classList.remove('hidden');
        } else {
            btn.innerHTML = '<i class="ph-bold ph-pencil-simple text-lg"></i> <span class="hidden sm:inline">Edit Profile</span><span class="sm:hidden">Edit</span>';
            btn.classList.replace('bg-green-600', 'bg-[#800000]');
            if (btn.classList.contains('dark:bg-green-500')) {
                btn.classList.replace('dark:bg-green-500', 'dark:bg-[#D4AF37]');
                btn.classList.replace('dark:text-white', 'dark:text-black');
            }
            avatarWrapper.classList.remove('editable-mode');
            coverWrapper.classList.remove('editable-mode');
            yearDisplay.innerText = yearSelect.value;
            yearDisplay.classList.remove('hidden');
            yearEditContainer.classList.add('hidden');
        }
    };

    window.triggerImageUpload = function() { if (isEditing) document.getElementById('profileFileInput').click(); };
    window.triggerCoverUpload = function() { if (isEditing) document.getElementById('coverFileInput').click(); };
    window.previewImage = function(event, targetId) {
        const reader = new FileReader();
        reader.onload = function() { document.getElementById(targetId).src = reader.result; };
        if(event.target.files[0]) reader.readAsDataURL(event.target.files[0]);
    };

    // ==========================================
    // 2. SETTINGS & PASSWORD MODALS
    // ==========================================
    window.openSettingsModal = function() {
        document.getElementById('settingsModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };
    window.closeSettingsModal = function() {
        document.getElementById('settingsModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    window.openPasswordModal = function() {
        document.getElementById('settingsModal').classList.add('hidden');
        document.getElementById('passwordModal').classList.remove('hidden');
    };
    window.closePasswordModal = function() {
        document.getElementById('passwordModal').classList.add('hidden');
        document.getElementById('settingsModal').classList.remove('hidden'); 
    };

    // Password Eye Toggle
    window.togglePassword = function(inputId, iconId) {
        const input = document.getElementById(inputId);
        const icon = document.getElementById(iconId);
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.replace('ph-eye', 'ph-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.replace('ph-eye-slash', 'ph-eye');
        }
    };

    window.submitPasswordChange = function() {
        const btn = document.getElementById('btnSubmitPassword');
        const origText = btn.innerHTML;
        btn.innerHTML = '<i class="ph-bold ph-spinner animate-spin"></i> Updating...';
        btn.disabled = true;
        setTimeout(() => {
            btn.innerHTML = origText;
            btn.disabled = false;
            document.getElementById('passwordModal').classList.add('hidden');
            document.body.style.overflow = '';
        }, 1500);
    };

    // ==========================================
    // 3. MESSAGES & NOTIFICATIONS MODAL
    // ==========================================
    const messagesData = [
        { id: 1, title: 'Welcome to PUPUni-CAMS!', sender: 'System Admin', date: 'Oct 25, 2026 • 08:00 AM', body: 'Mabuhay Iskolar ng Bayan! Welcome sa bagong Campus Activities Management System. Please make sure to complete your profile information and check the Event Calendar regularly for upcoming activities.', read: false },
        { id: 2, title: 'Evaluation Reminder', sender: 'SSC Organization', date: 'Oct 23, 2026 • 05:30 PM', body: 'Do not forget to submit your evaluation for the Mental Health Talk event. Your feedback is required for institutional documentation.', read: true },
        { id: 3, title: 'Attendance Verified', sender: 'System Admin', date: 'Sep 05, 2026 • 10:15 AM', body: 'Your attendance for the E-Sports Tournament has been successfully verified via Face Capture and Location GPS. Thank you for participating!', read: true },
        { id: 4, title: 'New Event: Leadership Seminar', sender: 'CAMS Admin', date: 'Sep 01, 2026 • 09:00 AM', body: 'A new event has been posted! The Leadership Seminar is now open for registration. Limited slots only so register early.', read: true }
    ];

    window.openMessageModal = function(id) {
        const msg = messagesData.find(m => m.id === id);
        if(!msg) return;

        document.getElementById('msgModalTitle').innerText = msg.title;
        document.getElementById('msgModalSender').innerText = msg.sender;
        document.getElementById('msgModalDate').innerText = msg.date;
        document.getElementById('msgModalBody').innerText = msg.body;
        
        const btn = document.getElementById('btnMarkRead');
        if(msg.read) {
            btn.innerHTML = '<i class="ph-bold ph-envelope-simple"></i> Mark as Unread';
            btn.dataset.state = 'read';
        } else {
            btn.innerHTML = '<i class="ph-bold ph-envelope-open"></i> Mark as Read';
            btn.dataset.state = 'unread';
        }

        document.getElementById('messageModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeMessageModal = function() {
        document.getElementById('messageModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    window.toggleMessageReadStatus = function() {
        const btn = document.getElementById('btnMarkRead');
        if(btn.dataset.state === 'read') {
            btn.innerHTML = '<i class="ph-bold ph-envelope-open"></i> Mark as Read';
            btn.dataset.state = 'unread';
        } else {
            btn.innerHTML = '<i class="ph-bold ph-envelope-simple"></i> Mark as Unread';
            btn.dataset.state = 'read';
        }
    };

    // ==========================================
    // 4. LOGOUT MODAL
    // ==========================================
    window.openLogoutModal = function() {
        document.getElementById('logoutModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };
    window.closeLogoutModal = function() {
        document.getElementById('logoutModal').classList.add('hidden');
        document.body.style.overflow = '';
    };
    window.performLogout = function() {
        window.location.href = '/'; 
    };

});

document.addEventListener('DOMContentLoaded', () => {
    
    // Check muna natin kung nasa Event History page tayo bago patakbuhin ito
    // para hindi mag-error sa ibang pages.
    const historyGridContainer = document.getElementById('historyGrid');
    if (!historyGridContainer) return;

    // Ang 18 Master Events natin
    const baseEvents = [
        { title: 'Research Colloquium', date: 'MAY 12, 2026', time: '08:00 AM', venue: 'Audio Visual Room', img: 'research.jpg' },
        { title: 'IT Week Hackathon', date: 'JUN 05, 2026', time: '07:00 AM', venue: 'Computer Lab 1', img: 'tech_talk.jpg' },
        { title: 'Quiz Bee Competition', date: 'JUL 20, 2026', time: '01:00 PM', venue: 'Main Gym', img: 'background.jpg' },
        { title: 'Basketball Intrams', date: 'AUG 15, 2026', time: '08:00 AM', venue: 'University Oval', img: 'student_week.jpg' },
        { title: 'Volleyball Tryouts', date: 'AUG 18, 2026', time: '03:00 PM', venue: 'PUP Gym', img: 'PUP1.jpg' },
        { title: 'E-Sports Tournament', date: 'SEP 05, 2026', time: '09:00 AM', venue: 'ComLab 3', img: 'tech_talk.jpg' },
        { title: 'Buwan ng Wika Celebration', date: 'AUG 28, 2026', time: '08:00 AM', venue: 'PUP Plaza', img: 'background.jpg' },
        { title: 'PUP Got Talent', date: 'OCT 15, 2026', time: '04:00 PM', venue: 'Main Stage', img: 'student_week.jpg' },
        { title: 'Sining Exhibit', date: 'NOV 10, 2026', time: '10:00 AM', venue: 'Library Lobby', img: 'PUP1.jpg' },
        { title: 'SSC General Assembly', date: 'FEB 14, 2026', time: '01:00 PM', venue: 'PUP Gym', img: 'background.jpg' },
        { title: 'ITO Meet and Greet', date: 'MAR 01, 2026', time: '10:00 AM', venue: 'Audio Visual Room', img: 'tech_talk.jpg' },
        { title: 'RCY Orientation', date: 'MAR 20, 2026', time: '09:00 AM', venue: 'Room 201', img: 'community.jpg' },
        { title: 'Leadership Seminar', date: 'DEC 25, 2025', time: '08:00 AM', venue: 'Conference Hall', img: 'leadership.jpg' },
        { title: 'Tech Trends 2026', date: 'MAY 02, 2026', time: '08:00 AM', venue: 'Audio Visual Room', img: 'tech_talk.jpg' },
        { title: 'Mental Health Talk', date: 'OCT 22, 2026', time: '10:00 AM', venue: 'Main Gym', img: 'PUP1.jpg' },
        { title: 'Coastal Clean-up', date: 'NOV 08, 2026', time: '06:00 AM', venue: 'Unisan Beachfront', img: 'community.jpg' },
        { title: 'Blood Donation Drive', date: 'DEC 01, 2026', time: '08:00 AM', venue: 'PUP Clinic', img: 'research.jpg' },
        { title: 'Tree Planting Activity', date: 'JAN 15, 2027', time: '07:00 AM', venue: 'Mt. Unisan Reserve', img: 'background.jpg' }
    ];

    let historyData = [];
    let idCounter = 1;

    // Generate 18 ATTENDANCE Records
    baseEvents.forEach(evt => {
        historyData.push({
            id: idCounter++,
            title: evt.title,
            type: 'Attendance',
            date: evt.date,
            time: evt.time,
            venue: evt.venue,
            img: evt.img
        });
    });

    // Generate 18 EVALUATION Records (Para tig-18 sila = 36 total)
    baseEvents.forEach(evt => {
        historyData.push({
            id: idCounter++,
            title: evt.title,
            type: 'Evaluation',
            date: evt.date,
            time: evt.time,
            venue: evt.venue,
            img: evt.img
        });
    });

    // Randomize display order para maganda tingnan sa grid
    historyData.sort(() => Math.random() - 0.5);

    const searchInput = document.getElementById('historySearch');
    const typeFilter = document.getElementById('historyTypeFilter');
    const noResults = document.getElementById('noResults');

    // ==========================================
    // RENDER CARDS FUNCTION
    // ==========================================
    function renderCards(data) {
        historyGridContainer.innerHTML = '';
        if (data.length === 0) {
            noResults.classList.remove('hidden');
            return;
        }
        noResults.classList.add('hidden');

        data.forEach(item => {
            const isAtt = item.type === 'Attendance';
            // Styling base sa type
            const badgeColor = isAtt ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
            const icon = isAtt ? 'ph-user-focus' : 'ph-star';

            const html = `
                <div class="bg-white dark:bg-pup-darkcard rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800 flex flex-row sm:flex-col cursor-pointer group shadow-sm hover:border-pup-maroon dark:hover:border-pup-gold transition-all" onclick="openHistoryModal(${item.id})">
                    <div class="w-24 sm:w-full h-24 sm:h-32 shrink-0 relative bg-gray-100 dark:bg-[#0a0a0a] border-r sm:border-r-0 sm:border-b border-gray-200 dark:border-gray-800">
                        <img src="${APP_STATIC_URL}${item.img}" class="w-full h-full object-cover group-hover:scale-105 transition-transform" onerror="this.src=DEFAULT_IMG; this.classList.remove('object-cover'); this.classList.add('object-contain', 'p-2');">
                        <div class="absolute top-2 right-2 hidden sm:block">
                            <span class="text-[0.65rem] font-bold px-2 py-1 rounded-md uppercase flex items-center gap-1 shadow-sm ${badgeColor}"><i class="ph-fill ${icon}"></i> ${item.type}</span>
                        </div>
                    </div>
                    <div class="p-3 sm:p-4 flex flex-col justify-center flex-grow min-w-0">
                        <div class="flex justify-between items-start mb-1">
                            <div class="text-[0.65rem] font-bold text-pup-maroon dark:text-pup-gold truncate">${item.date}</div>
                            <span class="sm:hidden text-[0.6rem] font-bold px-1.5 py-0.5 rounded uppercase ${badgeColor}">${item.type}</span>
                        </div>
                        <h3 class="font-bold text-sm sm:text-base text-gray-900 dark:text-white leading-tight mb-1 truncate">${item.title}</h3>
                        <p class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 truncate"><i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold shrink-0"></i> <span class="truncate">${item.venue}</span></p>
                    </div>
                </div>
            `;
            historyGridContainer.insertAdjacentHTML('beforeend', html);
        });
    }

    // ==========================================
    // FILTER & SEARCH LOGIC
    // ==========================================
    function filterData() {
        const query = searchInput.value.toLowerCase();
        const type = typeFilter.value;

        const filtered = historyData.filter(item => {
            const matchSearch = item.title.toLowerCase().includes(query) || item.venue.toLowerCase().includes(query);
            const matchType = type === 'All' || item.type === type;
            return matchSearch && matchType;
        });

        renderCards(filtered);
    }

    if (searchInput) searchInput.addEventListener('input', filterData);
    if (typeFilter) typeFilter.addEventListener('change', filterData);

    // Initial load
    renderCards(historyData);

    // ==========================================
    // MODAL LOGIC (Dynamic views based on type)
    // ==========================================
    window.openHistoryModal = function(id) {
        const item = historyData.find(i => i.id === id);
        if(!item) return;

        // Reset views
        document.getElementById('viewAttendanceProof').classList.add('hidden');
        document.getElementById('viewEvaluationProof').classList.add('hidden');

        // Populate header data
        document.getElementById('modalTitle').innerText = item.title;
        document.getElementById('modalType').innerText = item.type + " Record";
        document.getElementById('modalDateTime').innerHTML = `<i class="ph-fill ph-calendar text-pup-maroon dark:text-pup-gold text-lg"></i> ${item.date} • ${item.time}`;
        document.getElementById('modalVenue').innerHTML = `<i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold text-lg"></i> ${item.venue}`;

        // Switch internal proof view
        if(item.type === 'Attendance') {
            document.getElementById('proofTime').innerText = item.date + " at " + item.time;
            document.getElementById('viewAttendanceProof').classList.remove('hidden');
        } else {
            // Evaluated
            document.getElementById('evalTime').innerText = "Submitted on " + item.date;
            document.getElementById('viewEvaluationProof').classList.remove('hidden');
        }

        // Show Modal
        document.getElementById('historyModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeHistoryModal = function() {
        document.getElementById('historyModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

});