// static/js/organizer.js

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================
    // 1. VUE.JS APPLICATION
    // ==========================================
    const { createApp } = Vue;

    createApp({
        delimiters: ['[[', ']]'],
        data() {
            return {
                isDark: false,
                isMobileMenuOpen: false,
                hasNotification: true, 
                orgList: ['BPA', 'FTO', 'ITO', 'ITS', 'YEO', 'CAO', 'Newsette', 'SSC', 'PRIDE', 'ROTC'],
                
                isEventModalOpen: false,
                selectedEvent: {}, 
                
                latestNews: [
                    {
                        id: 101,
                        title: 'Research Colloquium 2025',
                        date: 'DEC 12, 2025',
                        location: 'PUP Unisan Quezon',
                        image: 'research.jpg',
                        description: 'Isang pagtitipon para sa pagpapakita at pagtalakay ng mga pinakabagong pananaliksik at pag-aaral ng mga iskolar ng bayan.'
                    },
                    {
                        id: 102,
                        title: 'Navigating the World of IT-Tech-Talk 1.0',
                        date: 'NOV 21, 2025',
                        location: 'Computer Laboratory',
                        image: 'tech_talk.jpg',
                        description: 'Seminar na nakatuon sa mga makabagong teknolohiya, programming trends, at mga oportunidad sa larangan ng Information Technology.'
                    }
                ],
                upcomingEvents: [
                    {
                        id: 1,
                        title: 'PUP General Assembly',
                        date: 'FEB 14, 2026',
                        location: 'PUP Main Campus Gym',
                        image: 'background.jpg', 
                        description: 'Ang taunang pagtitipon ng lahat ng Iskolar ng Bayan para sa mga anunsyo at pagpapakilala ng mga bagong proyekto ng unibersidad.'
                    },
                    {
                        id: 2,
                        title: 'Tech Summit 2026',
                        date: 'MAR 05, 2026',
                        location: 'Computer Lab 1 & 2',
                        image: 'tech_talk.jpg',
                        description: 'Isang summit na nakatuon sa pinakabagong teknolohiya, inobasyon, at mga workshop mula sa mga eksperto sa industriya.'
                    }
                ]
            }
        },
        mounted() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                this.isDark = true;
                document.documentElement.classList.add('dark');
            }

            window.addEventListener('scroll', () => {
                if (this.isMobileMenuOpen) {
                    this.isMobileMenuOpen = false;
                }
            }, { passive: true });
        },
        methods: {
            toggleTheme() {
                this.isDark = !this.isDark;
                document.documentElement.classList.toggle('dark');
                localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
            },
            toggleMobileMenu() {
                this.isMobileMenuOpen = !this.isMobileMenuOpen;
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
    }).mount('#app');

    // ==========================================
    // 2. VANILLA JS MODALS (Global Scope)
    // ==========================================

    window.openManagedEventModal = function() {
        const modal = document.getElementById('managedEventModal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    };

    window.closeManagedEventModal = function() {
        const modal = document.getElementById('managedEventModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    };

    window.openLogModal = function(type) {
        const modal = document.getElementById('recentLogModal');
        if (!modal) return;

        const iconDiv = document.getElementById('logModalIcon');
        const title = document.getElementById('logModalTitle');
        const date = document.getElementById('logModalDate');
        const desc = document.getElementById('logModalDesc');

        if(type === 'eval') {
            iconDiv.className = "w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-4 mt-2 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-4xl";
            iconDiv.innerHTML = '<i class="ph-fill ph-clipboard-text"></i>';
            title.innerText = "Evaluation Form Drafted";
            date.innerText = "Dec 10, 2025 • 02:30 PM";
            desc.innerText = "You have successfully drafted the evaluation template for the 'Research Colloquium 2025'. It is currently saved and ready to be published.";
        } else if(type === 'proposal') {
            iconDiv.className = "w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-4 mt-2 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-4xl";
            iconDiv.innerHTML = '<i class="ph-fill ph-plus-circle"></i>';
            title.innerText = "New Event Proposal";
            date.innerText = "Nov 28, 2025 • 09:15 AM";
            desc.innerText = "You have submitted the 'Tech Summit 2026' proposal. The Administration Office has been notified and it is currently under review.";
        }

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeLogModal = function() {
        const modal = document.getElementById('recentLogModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    };
});


// ==========================================
// MANAGE STUDENTS LOGIC
// ==========================================
document.addEventListener('DOMContentLoaded', () => {

    const studentsData = [
        { id: 1, name: 'Juan Dela Cruz', stdNum: '2023-00123-UQ-0', year: '3rd Year', birth: 'Oct 25, 2003', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 2, name: 'Maria Santos', stdNum: '2024-00456-UQ-0', year: '2nd Year', birth: 'Feb 14, 2004', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 3, name: 'Jose Rizal', stdNum: '2022-00789-UQ-0', year: '4th Year', birth: 'Jun 19, 2002', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 4, name: 'Andres Bonifacio', stdNum: '2025-00111-UQ-0', year: '1st Year', birth: 'Nov 30, 2005', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 5, name: 'Emilio Aguinaldo', stdNum: '2023-00222-UQ-0', year: '3rd Year', birth: 'Mar 22, 2003', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 6, name: 'Apolinario Mabini', stdNum: '2024-00333-UQ-0', year: '2nd Year', birth: 'Jul 23, 2004', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 7, name: 'Gabriela Silang', stdNum: '2022-00444-UQ-0', year: '4th Year', birth: 'Mar 19, 2002', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 8, name: 'Melchora Aquino', stdNum: '2025-00555-UQ-0', year: '1st Year', birth: 'Jan 06, 2005', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 9, name: 'Gregorio Del Pilar', stdNum: '2023-00666-UQ-0', year: '3rd Year', birth: 'Nov 14, 2003', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 10, name: 'Antonio Luna', stdNum: '2024-00777-UQ-0', year: '2nd Year', birth: 'Oct 29, 2004', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 11, name: 'Juan Luna', stdNum: '2022-00888-UQ-0', year: '4th Year', birth: 'Oct 23, 2002', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 12, name: 'Marcelo H. Del Pilar', stdNum: '2025-00999-UQ-0', year: '1st Year', birth: 'Aug 30, 2005', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 13, name: 'Graciano Lopez Jaena', stdNum: '2023-00101-UQ-0', year: '3rd Year', birth: 'Dec 18, 2003', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 14, name: 'Emilio Jacinto', stdNum: '2024-00202-UQ-0', year: '2nd Year', birth: 'Dec 15, 2004', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 15, name: 'Mariano Ponce', stdNum: '2022-00303-UQ-0', year: '4th Year', birth: 'Mar 23, 2002', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 16, name: 'Jose Burgos', stdNum: '2025-00404-UQ-0', year: '1st Year', birth: 'Feb 09, 2005', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 17, name: 'Teresa Magbanua', stdNum: '2023-00505-UQ-0', year: '3rd Year', birth: 'Oct 13, 2003', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 18, name: 'Diego Silang', stdNum: '2024-00606-UQ-0', year: '2nd Year', birth: 'Dec 16, 2004', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 19, name: 'Lapu-Lapu', stdNum: '2022-00707-UQ-0', year: '4th Year', birth: 'Apr 27, 2002', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 20, name: 'Rajah Sulayman', stdNum: '2025-00808-UQ-0', year: '1st Year', birth: 'Jan 01, 2005', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 21, name: 'Francisco Dagohoy', stdNum: '2023-00909-UQ-0', year: '3rd Year', birth: 'Feb 10, 2003', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 22, name: 'Miguel Malvar', stdNum: '2024-01010-UQ-0', year: '2nd Year', birth: 'Sep 27, 2004', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 23, name: 'Artemio Ricarte', stdNum: '2022-01111-UQ-0', year: '4th Year', birth: 'Oct 20, 2002', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 24, name: 'Vicente Lim', stdNum: '2025-01212-UQ-0', year: '1st Year', birth: 'Apr 05, 2005', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 25, name: 'Macario Sakay', stdNum: '2023-01313-UQ-0', year: '3rd Year', birth: 'Mar 01, 2003', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 26, name: 'Julio Nakpil', stdNum: '2024-01414-UQ-0', year: '2nd Year', birth: 'May 22, 2004', avatar: 'PUPLogo.png', cover: 'PUP1.jpg' },
        { id: 27, name: 'Simeon Ola', stdNum: '2022-01515-UQ-0', year: '4th Year', birth: 'Sep 02, 2002', avatar: 'student.jpg', cover: 'background.jpg' },
        { id: 28, name: 'Tamblot', stdNum: '2025-01616-UQ-0', year: '1st Year', birth: 'Nov 01, 2005', avatar: 'student.jpg', cover: 'PUP1.jpg' },
        { id: 29, name: 'Magat Salamat', stdNum: '2023-01717-UQ-0', year: '3rd Year', birth: 'Dec 05, 2003', avatar: 'PUPLogo.png', cover: 'background.jpg' },
        { id: 30, name: 'Lakan Dula', stdNum: '2024-01818-UQ-0', year: '2nd Year', birth: 'Aug 14, 2004', avatar: 'student.jpg', cover: 'PUP1.jpg' }
    ];

    let currentSelectedStudent = null;

    const listContainer = document.getElementById('studentListContainer');
    const searchInput = document.getElementById('searchInput');
    const yearFilter = document.getElementById('yearFilter');
    const noResults = document.getElementById('noResultsState');

    function renderStudents(data) {
        if(!listContainer) return;

        listContainer.innerHTML = '';
        
        if (data.length === 0) {
            if(noResults) noResults.classList.remove('hidden');
            return;
        }
        if(noResults) noResults.classList.add('hidden');

        data.forEach(student => {
            const avatarUrl = window.STATIC_IMAGES_BASE + student.avatar;
            
            const html = `
                <div class="student-row flex flex-col sm:grid sm:grid-cols-12 gap-4 p-4 sm:p-5 items-center cursor-pointer" onclick="openStudentProfile(${student.id})">
                    
                    <div class="col-span-5 flex items-center gap-4 w-full sm:w-auto">
                        <img src="${avatarUrl}" class="w-12 h-12 rounded-full object-cover border border-gray-200 dark:border-gray-700 shrink-0" onerror="this.src=window.DEFAULT_LOGO">
                        <div class="flex-grow min-w-0">
                            <h4 class="font-bold text-gray-900 dark:text-white text-base truncate">${student.name}</h4>
                            <p class="text-xs text-gray-500 sm:hidden">${student.stdNum} • ${student.year}</p>
                        </div>
                    </div>

                    <div class="hidden sm:flex col-span-3 items-center">
                        <span class="text-sm font-bold text-gray-600 dark:text-gray-400">${student.stdNum}</span>
                    </div>

                    <div class="hidden sm:flex col-span-2 items-center justify-center">
                        <span class="text-xs font-bold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700">${student.year}</span>
                    </div>

                    <div class="col-span-2 w-full sm:w-auto flex justify-center sm:justify-end mt-2 sm:mt-0">
                        <button class="w-full sm:w-auto px-4 py-2 rounded-lg bg-[#800000]/10 dark:bg-[#D4AF37]/10 text-[#800000] dark:text-[#D4AF37] font-bold text-xs hover:bg-[#800000] hover:text-white dark:hover:bg-[#D4AF37] dark:hover:text-black transition-colors flex items-center justify-center gap-2">
                            <i class="ph-bold ph-eye"></i> View Profile
                        </button>
                    </div>
                </div>
            `;
            listContainer.insertAdjacentHTML('beforeend', html);
        });
    }

    function filterData() {
        if(!searchInput || !yearFilter) return;

        const query = searchInput.value.toLowerCase();
        const year = yearFilter.value;

        const filtered = studentsData.filter(item => {
            const matchSearch = item.name.toLowerCase().includes(query) || item.stdNum.toLowerCase().includes(query);
            const matchYear = year === 'All' || item.year === year;
            return matchSearch && matchYear;
        });

        renderStudents(filtered);
    }

    if (searchInput) searchInput.addEventListener('input', filterData);
    if (yearFilter) yearFilter.addEventListener('change', filterData);

    if(listContainer) renderStudents(studentsData);

    window.openStudentProfile = function(id) {
        currentSelectedStudent = studentsData.find(s => s.id === id);
        if(!currentSelectedStudent) return;

        document.getElementById('modName').innerText = currentSelectedStudent.name;
        document.getElementById('modStdNum').innerText = currentSelectedStudent.stdNum;
        document.getElementById('modYear').innerText = currentSelectedStudent.year;
        document.getElementById('modBirth').innerText = currentSelectedStudent.birth;
        document.getElementById('modAvatar').src = window.STATIC_IMAGES_BASE + currentSelectedStudent.avatar;
        document.getElementById('modCover').src = window.STATIC_IMAGES_BASE + currentSelectedStudent.cover;

        document.getElementById('studentProfileModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeStudentModal = function() {
        document.getElementById('studentProfileModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    window.promptApprove = function() {
        document.getElementById('approveNameText').innerText = currentSelectedStudent.name;
        document.getElementById('approveModal').classList.remove('hidden');
    };

    window.closeApproveModal = function() {
        document.getElementById('approveModal').classList.add('hidden');
    };

    window.promptReject = function() {
        document.getElementById('rejectNameText').innerText = currentSelectedStudent.name;
        document.getElementById('rejectModal').classList.remove('hidden');
    };

    window.closeRejectModal = function() {
        document.getElementById('rejectModal').classList.add('hidden');
    };

    window.confirmAction = function(type) {
        if(type === 'approve') closeApproveModal();
        if(type === 'reject') closeRejectModal();
        closeStudentModal();

        const index = studentsData.findIndex(s => s.id === currentSelectedStudent.id);
        if(index > -1) {
            studentsData.splice(index, 1);
            filterData(); 
        }
    };
});

// ==========================================
// MANAGE ATTENDANCE LOGIC
// ==========================================
document.addEventListener('DOMContentLoaded', () => {

    let map;
    let marker;

    window.initMap = function(lat, lng) {
        if (map) {
            map.setView([lat, lng], 16);
            if(marker) map.removeLayer(marker);
            
            marker = L.marker([lat, lng]).addTo(map)
                .bindPopup('<div style="text-align:center; font-family:sans-serif; color:black;"><b>VERIFIED LOCATION</b><br>PUP Unisan Campus</div>')
                .openPopup();
        } else {
            const mapContainer = document.getElementById('realMap');
            if(!mapContainer) return;

            map = L.map('realMap').setView([lat, lng], 16);
            
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: ''
            }).addTo(map);

            marker = L.marker([lat, lng]).addTo(map)
                .bindPopup('<div style="text-align:center; font-family:sans-serif; color:black;"><b>VERIFIED LOCATION</b><br>PUP Unisan Campus</div>')
                .openPopup();
        }
        
        setTimeout(() => { map.invalidateSize(); }, 300);
    };

    // 🟢 HAHATAKIN ANG NAKA-LOGIN NA ORG MULA SA HTML 🟢
    const hiddenOrgInput = document.getElementById('currentOrgAcronym');
    let currentOrg = hiddenOrgInput ? hiddenOrgInput.value : 'ITO';
    let currentYear = '1';
    let currentProgramFilter = 'all';

    const orgDetails = {
        'ITO': { name: 'ITO', programs: ['BS Information Technology'] },
        'BPA': { name: 'BPA', programs: ['Bachelor of Public Administration'] },
        'ITS': { name: 'ITS', programs: ['Diploma in Information Technology', 'Diploma in Office Management Technology'] },
        'FTO': { name: 'FTO', programs: ['Bachelor of Elementary Education'] },
        'YEO': { name: 'YEO', programs: ['BS Entrepreneurship'] },
        'PUSO': { name: 'PUSO', programs: ['Sports Science', 'Physical Education'] },
        'SSC': { name: 'SSC', programs: ['General Student Body'] },
        'PAS': { name: 'PAS', programs: ['Public Administration'] },
        'CAO': { name: 'CAO', programs: ['Culture and Arts'] },
        'PRIDEVerse': { name: 'PRIDEVerse', programs: ['General'] },
        'ROTC': { name: 'ROTC', programs: ['Military Science'] },
        'NEWSETTE': { name: 'NEWSETTE', programs: ['Journalism', 'Broadcasting'] }
    };

    if (!orgDetails[currentOrg]) {
        orgDetails[currentOrg] = { name: currentOrg, programs: ['General Program'] };
    }

    const animeCharacters = [
        { name: "Naruto Uzumaki", seed: "naruto" }, { name: "Sasuke Uchiha", seed: "sasuke" }, { name: "Sakura Haruno", seed: "sakura" },
        { name: "Goku Son", seed: "goku" }, { name: "Vegeta Prince", seed: "vegeta" }, { name: "Luffy Monkey D.", seed: "luffy" },
        { name: "Zoro Roronoa", seed: "zoro" }, { name: "Nami Swan", seed: "nami" }, { name: "Edward Elric", seed: "edward" },
        { name: "Light Yagami", seed: "light" }, { name: "Levi Ackerman", seed: "levi" }, { name: "Tanjiro Kamado", seed: "tanjiro" }
    ];

    const generateStudents = (org, year, count) => {
        const students = [];
        const programs = orgDetails[org].programs;
        const yearPrefix = { 1: '2025', 2: '2024', 3: '2023', 4: '2022' };

        for(let i=1; i<=count; i++) {
            const status = Math.random() > 0.8 ? 'Late' : (Math.random() > 0.9 ? 'Absent' : 'Present');
            const prog = programs[Math.floor(Math.random() * programs.length)];
            const charIndex = Math.floor(Math.random() * animeCharacters.length);
            const character = animeCharacters[charIndex];

            const faceImg = `https://api.dicebear.com/7.x/adventurer/svg?seed=${character.seed}&flip=true`;
            const randNum = Math.floor(Math.random() * 10000).toString().padStart(5, '0');
            const studentId = `${yearPrefix[year]}-${randNum}-UQ-0`;

            const lat = 13.8392 + (Math.random() * 0.001 - 0.0005);
            const lng = 121.9861 + (Math.random() * 0.001 - 0.0005);

            students.push({
                name: character.name,
                id: studentId,
                course: prog,
                time: status === 'Absent' ? '--:--' : '07:45 AM',
                status: status,
                lat: lat, 
                lng: lng,
                face: faceImg 
            });
        }
        return students;
    };

    const db = {};
    db[currentOrg] = {
        '1': generateStudents(currentOrg, 1, 15),
        '2': generateStudents(currentOrg, 2, 12),
        '3': generateStudents(currentOrg, 3, 10),
        '4': generateStudents(currentOrg, 4, 8)
    };

    const opt4 = document.getElementById('opt4th');
    const progFilter = document.getElementById('programFilterGroup');
    const programSelect = document.getElementById('programSelect');
    
    if(currentOrg === 'ITS') {
        if(opt4) opt4.style.display = 'none';
        if(currentYear === '4') { currentYear = '1'; document.getElementById('yearSelect').value = '1'; }
        if(progFilter) {
            progFilter.classList.remove('hidden');
            progFilter.classList.add('flex');
        }
        if(programSelect) programSelect.value = 'all';
    } else {
        if(opt4) opt4.style.display = 'block';
        if(progFilter) {
            progFilter.classList.remove('flex');
            progFilter.classList.add('hidden');
        }
    }

    window.filterData = function() {
        const yearSelect = document.getElementById('yearSelect');
        if(yearSelect) currentYear = yearSelect.value;

        const programSelect = document.getElementById('programSelect');
        if(currentOrg === 'ITS' && programSelect) { currentProgramFilter = programSelect.value; }
        
        renderTable();
    };

    function renderTable() {
        const tbody = document.getElementById('tableBody');
        if(!tbody) return;

        tbody.innerHTML = '';
        let data = db[currentOrg][currentYear] || [];

        if(currentOrg === 'ITS' && currentProgramFilter !== 'all') {
            const keyword = currentProgramFilter === 'DIT' ? 'Information Technology' : 'Office Management';
            data = data.filter(s => s.course.includes(keyword));
        }

        const studentCount = document.getElementById('studentCount');
        if(studentCount) studentCount.innerText = data.length;

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="p-8 text-center text-gray-500 font-bold">No records found.</td></tr>';
            return;
        }

        data.forEach(s => {
            let badgeClass = s.status.toLowerCase();
            const row = `
                <tr onclick="openProofModal('${s.name}', '${s.id}', '${s.course}', '${s.status}', ${s.lat}, ${s.lng}, '${s.time}', '${s.face}')">
                    <td class="p-4 pl-6 font-bold text-pup-maroon dark:text-pup-gold">${s.name}</td>
                    <td class="p-4 text-sm font-bold">${s.id}</td>
                    <td class="p-4 text-sm">${s.course}</td>
                    <td class="p-4 text-sm font-bold">${s.time}</td>
                    <td class="p-4 pr-6"><span class="status-badge ${badgeClass}">${s.status}</span></td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    }

    window.searchStudent = function() {
        const searchInput = document.getElementById('searchInput');
        if(!searchInput) return;

        const input = searchInput.value.toLowerCase();
        const tbody = document.getElementById('tableBody');
        if(!tbody) return;

        const rows = tbody.getElementsByTagName('tr');
        for (let i = 0; i < rows.length; i++) {
            const nameCell = rows[i].getElementsByTagName('td')[0];
            if (nameCell) {
                const txtValue = nameCell.textContent || nameCell.innerText;
                if (txtValue.toLowerCase().indexOf(input) > -1) {
                    rows[i].style.display = "";
                } else {
                    rows[i].style.display = "none";
                }
            }
        }
    };

    window.openProofModal = function(name, id, course, status, lat, lng, time, faceUrl) {
        
        document.getElementById('modalEventTitle').innerText = `${currentOrg} General Assembly`; 
        
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        const dateStr = new Date().toLocaleDateString('en-US', options).toUpperCase();
        document.getElementById('modalDateInfo').innerText = `${dateStr} • 08:00 AM`;
        
        document.getElementById('modalName').innerText = name;
        document.getElementById('modalId').innerText = id;
        document.getElementById('proofFaceImg').src = faceUrl;
        
        const timeDisplay = status === 'Absent' ? 'N/A' : `${dateStr} at ${time}`;
        document.getElementById('geoTime').innerText = timeDisplay;
        
        const badge = document.getElementById('modalStatusBadge');
        badge.innerText = status;
        if(status === 'Present') {
            badge.className = "mt-2 text-xs font-bold px-3 py-1 rounded-full inline-block border border-green-200 text-green-600 bg-green-50 dark:border-green-800/50 dark:text-green-400 dark:bg-green-900/20";
        } else if(status === 'Late') {
            badge.className = "mt-2 text-xs font-bold px-3 py-1 rounded-full inline-block border border-yellow-200 text-yellow-600 bg-yellow-50 dark:border-yellow-800/50 dark:text-yellow-400 dark:bg-yellow-900/20";
        } else {
            badge.className = "mt-2 text-xs font-bold px-3 py-1 rounded-full inline-block border border-red-200 text-red-600 bg-red-50 dark:border-red-800/50 dark:text-red-400 dark:bg-red-900/20";
        }

        document.getElementById('proofModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        setTimeout(() => {
            initMap(lat, lng);
        }, 100);
    };

    window.closeProofModal = function() {
        document.getElementById('proofModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    renderTable();
});

// ==========================================
// ORGANIZER ANALYTICS LOGIC
// ==========================================
document.addEventListener('DOMContentLoaded', () => {

    const orgSelect = document.getElementById('orgSelect');
    if(!orgSelect) return;

    const db = {
        'ITO': {
            program: 'BS Information Technology',
            totalEvals: 1250,
            avgRating: 4.6,
            topYear: '3rd Year',
            posSentiment: '82%',
            starsOverall: [50, 100, 200, 400, 500], 
            starsByYear: [4.1, 4.3, 4.8, 4.6], 
            sentOverall: [82, 12, 6], 
            sentByYearPos: [70, 80, 90, 85],
            sentByYearNeu: [20, 15, 5, 10],
            sentByYearNeg: [10, 5, 5, 5]
        },
        'BPA': {
            program: 'Bachelor of Public Administration',
            totalEvals: 890,
            avgRating: 4.2,
            topYear: '2nd Year',
            posSentiment: '65%',
            starsOverall: [80, 120, 250, 300, 140], 
            starsByYear: [3.9, 4.5, 4.0, 4.1], 
            sentOverall: [65, 25, 10], 
            sentByYearPos: [60, 75, 60, 65],
            sentByYearNeu: [25, 20, 30, 25],
            sentByYearNeg: [15, 5, 10, 10]
        },
        'ITS': {
            program: 'Institute of Technology Society',
            totalEvals: 1540,
            avgRating: 4.8,
            topYear: '1st Year',
            posSentiment: '88%',
            starsOverall: [20, 30, 100, 500, 890], 
            starsByYear: [4.9, 4.7, 4.8, 0], 
            sentOverall: [88, 10, 2], 
            sentByYearPos: [92, 85, 87, 0],
            sentByYearNeu: [6, 12, 10, 0],
            sentByYearNeg: [2, 3, 3, 0]
        },
        'FTO': {
            program: 'Future Teachers Organization',
            totalEvals: 760,
            avgRating: 4.4,
            topYear: '4th Year',
            posSentiment: '75%',
            starsOverall: [40, 60, 150, 300, 210], 
            starsByYear: [4.0, 4.2, 4.5, 4.9], 
            sentOverall: [75, 20, 5], 
            sentByYearPos: [65, 70, 75, 90],
            sentByYearNeu: [25, 25, 20, 10],
            sentByYearNeg: [10, 5, 5, 0]
        },
        'YEO': {
            program: 'Young Entrepreneurs Organization',
            totalEvals: 920,
            avgRating: 4.1,
            topYear: '3rd Year',
            posSentiment: '60%',
            starsOverall: [90, 150, 200, 280, 200], 
            starsByYear: [3.8, 4.0, 4.6, 4.0], 
            sentOverall: [60, 25, 15], 
            sentByYearPos: [50, 55, 75, 60],
            sentByYearNeu: [30, 30, 15, 25],
            sentByYearNeg: [20, 15, 10, 15]
        }
    };

    let starsOverallChart, starsYearChart, sentOverallChart, sentYearChart;

    function getThemeColors() {
        const isDark = document.documentElement.classList.contains('dark');
        return {
            text: isDark ? '#ffffff' : '#333333',
            grid: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
        };
    }

    window.loadDashboardData = function() {
        const org = document.getElementById('orgSelect').value;
        const data = db[org];
        const theme = getThemeColors();

        document.getElementById('displayOrgName').innerText = org;
        document.getElementById('displayOrgProgram').innerText = data.program;
        
        document.getElementById('statTotalEval').innerText = data.totalEvals;
        document.getElementById('statAvgStar').innerText = data.avgRating;
        document.getElementById('statPosSentiment').innerText = data.posSentiment;
        document.getElementById('statTopYear').innerText = data.topYear;

        if(starsOverallChart) starsOverallChart.destroy();
        if(starsYearChart) starsYearChart.destroy();
        if(sentOverallChart) sentOverallChart.destroy();
        if(sentYearChart) sentYearChart.destroy();

        const ctx1 = document.getElementById('starsOverallChart').getContext('2d');
        starsOverallChart = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars'],
                datasets: [{
                    data: data.starsOverall,
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#20c997', '#28a745'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: theme.text, font: { family: 'Inter' } } }
                }
            }
        });

        const ctx2 = document.getElementById('starsYearChart').getContext('2d');
        starsYearChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: ['1st Year', '2nd Year', '3rd Year', '4th Year'],
                datasets: [{
                    label: 'Average Star Rating',
                    data: data.starsByYear,
                    backgroundColor: '#D4AF37', 
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 5, ticks: { color: theme.text }, grid: { color: theme.grid } },
                    x: { ticks: { color: theme.text }, grid: { display: false } }
                },
                plugins: {
                    legend: { display: false } 
                }
            }
        });

        const ctx3 = document.getElementById('sentimentOverallChart').getContext('2d');
        sentOverallChart = new Chart(ctx3, {
            type: 'pie',
            data: {
                labels: ['Positive', 'Neutral', 'Negative'],
                datasets: [{
                    data: data.sentOverall,
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { color: theme.text, font: { family: 'Inter' } } }
                }
            }
        });

        const ctx4 = document.getElementById('sentimentYearChart').getContext('2d');
        sentYearChart = new Chart(ctx4, {
            type: 'radar',
            data: {
                labels: ['1st Year', '2nd Year', '3rd Year', '4th Year'],
                datasets: [
                    {
                        label: 'Positive',
                        data: data.sentByYearPos,
                        backgroundColor: 'rgba(40, 167, 69, 0.2)',
                        borderColor: '#28a745',
                        pointBackgroundColor: '#28a745'
                    },
                    {
                        label: 'Neutral',
                        data: data.sentByYearNeu,
                        backgroundColor: 'rgba(255, 193, 7, 0.2)',
                        borderColor: '#ffc107',
                        pointBackgroundColor: '#ffc107'
                    },
                    {
                        label: 'Negative',
                        data: data.sentByYearNeg,
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        borderColor: '#dc3545',
                        pointBackgroundColor: '#dc3545'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    r: {
                        angleLines: { color: theme.grid },
                        grid: { color: theme.grid },
                        pointLabels: { color: theme.text, font: { family: 'Inter', weight: 'bold' } },
                        ticks: { display: false, max: 100, min: 0 }
                    }
                },
                plugins: {
                    legend: { position: 'top', labels: { color: theme.text, font: { family: 'Inter' } } }
                }
            }
        });
    };

    const observer = new MutationObserver(() => { loadDashboardData(); });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

    loadDashboardData();
});

// =======================================================
// PARTICIPATION HUB (EVENT SCANNER & MODALS LOGIC)
// =======================================================
const participatedEvents = {}; 

document.addEventListener('DOMContentLoaded', () => {
    let stream = null;
    let map = null;
    let userLat = null;
    let userLng = null;
    let currentEventTitle = ""; 
    let currentEventVenue = ""; 
    let currentEventDateTime = ""; 
    let detectedAddress = "";
    let scanAttempts = 0; 

    const searchInput = document.getElementById('eventSearch');
    const filterBtns = document.querySelectorAll('.js-category-btn');
    const eventCards = document.querySelectorAll('.js-event-card');
    const noResults = document.getElementById('noResults');
    const participationModal = document.getElementById('participationModal');

    function filterEvents() {
        if (!searchInput || !noResults) return;
        const query = searchInput.value.toLowerCase().trim();
        const activeBtn = document.querySelector('.js-category-btn.active');
        const activeFilter = activeBtn ? activeBtn.dataset.category : 'All';
        
        let visibleCount = 0;
        eventCards.forEach(card => {
            const title = card.dataset.title ? card.dataset.title.toLowerCase() : "";
            const category = card.dataset.category;
            const matchesSearch = title.includes(query);
            const matchesCategory = activeFilter === 'All' || category === activeFilter;

            if (matchesSearch && matchesCategory) {
                card.style.display = "flex"; 
                visibleCount++;
            } else {
                card.style.display = "none";
            }
        });
        noResults.style.display = visibleCount > 0 ? 'none' : 'block';
    }

    if (searchInput) searchInput.addEventListener('input', filterEvents);
    
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => {
                b.classList.remove('active', 'bg-pup-maroon', 'text-white', 'dark:bg-pup-gold', 'dark:text-black', 'border-pup-maroon', 'dark:border-pup-gold');
                b.classList.add('bg-white', 'dark:bg-pup-darkcard', 'text-gray-600', 'dark:text-gray-300');
            });
            const target = e.target;
            target.classList.remove('bg-white', 'dark:bg-pup-darkcard', 'text-gray-600', 'dark:text-gray-300');
            target.classList.add('active', 'bg-pup-maroon', 'text-white', 'dark:bg-pup-gold', 'dark:text-black', 'border-pup-maroon', 'dark:border-pup-gold');
            filterEvents();
        });
    });

    function switchView(viewId) {
        ['viewDetails', 'viewPermissions', 'viewScanner', 'viewSuccess', 'viewProof'].forEach(v => {
            const el = document.getElementById(v);
            if (el) el.style.display = 'none';
        });
        
        const targetView = document.getElementById(viewId);
        if (targetView) targetView.style.display = 'flex';
        
        if(viewId !== 'viewScanner') {
            scanAttempts = 0;
            const locStatus = document.getElementById('locStatus');
            if (locStatus) locStatus.innerHTML = '<i class="ph-bold ph-spinner animate-spin text-lg"></i> Waiting for GPS signal...';
            
            const btnSubmit = document.getElementById('btnSubmitScan');
            if (btnSubmit) {
                btnSubmit.innerHTML = '<i class="ph-bold ph-bounding-box text-xl"></i> Scan & Submit Attendance';
                btnSubmit.disabled = false;
            }
        }
    }

    function openParticipationModal() {
        if (participationModal) {
            participationModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }

    function closeParticipationModal() {
        if (participationModal) participationModal.style.display = 'none';
        document.body.style.overflow = '';
        if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    }

    eventCards.forEach(card => {
        card.addEventListener('click', () => {
            currentEventTitle = card.dataset.title;
            currentEventVenue = card.dataset.venue;
            currentEventDateTime = `${card.dataset.date} • ${card.dataset.time}`;

            if (participatedEvents[currentEventTitle]) {
                const proofData = participatedEvents[currentEventTitle];
                
                document.getElementById('proofModalTitle').innerText = currentEventTitle;
                document.getElementById('proofModalDateTime').innerText = currentEventDateTime;
                document.getElementById('proofModalVenue').innerText = currentEventVenue;
                
                document.getElementById('proofFaceImg').src = proofData.image;
                document.getElementById('proofTime').innerText = proofData.time;
                document.getElementById('proofAddress').innerText = proofData.address; 
                document.getElementById('proofLocation').innerText = `${proofData.lat}, ${proofData.lng}`;
                
                openParticipationModal();
                switchView('viewProof');
            } else {
                const imgElem = card.querySelector('img');
                if (imgElem) document.getElementById('modalImg').src = imgElem.src;
                
                document.getElementById('modalCategory').innerText = card.dataset.category;
                document.getElementById('modalTitle').innerText = currentEventTitle;
                document.getElementById('modalDateTime').innerHTML = `<i class="ph-fill ph-calendar text-pup-maroon dark:text-pup-gold text-lg"></i> ${currentEventDateTime}`;
                document.getElementById('modalVenue').innerHTML = `<i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold text-lg"></i> ${currentEventVenue}`;
                document.getElementById('modalDesc').innerText = card.dataset.desc;

                openParticipationModal();
                switchView('viewDetails');
            }
        });
    });

    const closeBtns = ['btnTopClose', 'bgOverlayClose', 'btnCancelPermission', 'btnSuccessClose', 'btnProofClose'];
    closeBtns.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener('click', closeParticipationModal);
    });

    const btnParticipate = document.getElementById('btnParticipateNow');
    if (btnParticipate) {
        btnParticipate.addEventListener('click', () => {
            switchView('viewPermissions');
        });
    }

    function fetchHumanAddress(lat, lng) {
        return fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`)
            .then(response => response.json())
            .then(data => {
                detectedAddress = data.display_name;
                return detectedAddress;
            })
            .catch(error => {
                detectedAddress = "Location Identified via OpenStreetMap";
                return detectedAddress;
            });
    }

    const btnGrant = document.getElementById('btnGrantPermission');
    if (btnGrant) {
        btnGrant.addEventListener('click', function() {
            this.innerHTML = '<i class="ph-bold ph-spinner animate-spin"></i> Ina-access...';
            userLat = null; userLng = null; detectedAddress = "";

            setTimeout(() => {
                switchView('viewScanner');
                this.innerHTML = 'I Understand, Allow Access'; 
                
                if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } })
                        .then(s => { 
                            stream = s; 
                            document.getElementById('videoFeed').srcObject = stream; 
                        })
                        .catch(err => {
                            document.getElementById('cameraContainer').innerHTML = `<div class="absolute inset-0 flex items-center justify-center bg-gray-900"><p class="text-white font-bold">Camera Blocked</p></div>`;
                        });
                }

                setTimeout(() => {
                    if (!map) {
                        map = L.map('locationMap', {zoomControl: false}).setView([13.8392, 121.9861], 15);
                        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
                    }
                    map.invalidateSize(); 

                    if (navigator.geolocation) {
                        const locStatus = document.getElementById('locStatus');
                        locStatus.innerHTML = '<i class="ph-bold ph-spinner animate-spin text-lg"></i> Locating...';
                        
                        navigator.geolocation.getCurrentPosition(pos => {
                            userLat = pos.coords.latitude;
                            userLng = pos.coords.longitude;
                            map.setView([userLat, userLng], 17);
                            L.marker([userLat, userLng]).addTo(map).bindPopup('Current Location').openPopup();
                            
                            fetchHumanAddress(userLat, userLng).then(() => {
                                locStatus.innerHTML = `<span class="text-green-600 dark:text-green-400 flex items-center gap-2"><i class="ph-fill ph-check-circle text-xl"></i> GPS Coordinates Locked! Address detected.</span>`;
                            });
                        }, () => {
                            locStatus.innerHTML = `<span class="text-red-500"><i class="ph-fill ph-warning-circle text-xl"></i> Location Blocked!</span>`;
                            document.getElementById('btnSubmitScan').disabled = true;
                        });
                    }
                }, 400);
            }, 800);
        });
    }

    const btnSubmitScan = document.getElementById('btnSubmitScan');
    if (btnSubmitScan) {
        btnSubmitScan.addEventListener('click', function() {
            if (!stream) { alert("Camera is required!"); return; }
            if (!userLat || !userLng) { alert("Wait for GPS lock!"); return; }

            const btn = this;
            btn.innerHTML = '<i class="ph-bold ph-spinner animate-spin text-xl"></i> Processing...';
            btn.disabled = true;

            const video = document.getElementById('videoFeed');
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const faceImageData = canvas.toDataURL('image/jpeg');

            setTimeout(() => {
                btn.innerHTML = '<i class="ph-bold ph-check text-xl"></i> Verification Success';
                
                setTimeout(() => {
                    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
                    
                    participatedEvents[currentEventTitle] = {
                        image: faceImageData,
                        lat: userLat.toFixed(6),
                        lng: userLng.toFixed(6),
                        address: detectedAddress || "Verified inside PUP Campus Perimeter.",
                        time: new Date().toLocaleString('en-US', { dateStyle: 'long', timeStyle: 'medium' })
                    };
                    
                    switchView('viewSuccess');
                }, 1200);
            }, 2000);
        });
    }
});

document.addEventListener('DOMContentLoaded', () => {
    
    const historyGridContainer = document.getElementById('historyGrid');
    if (!historyGridContainer) return;

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

    historyData.sort(() => Math.random() - 0.5);

    const searchInput = document.getElementById('historySearch');
    const noResults = document.getElementById('noResults');

    function renderCards(data) {
        historyGridContainer.innerHTML = '';
        if (data.length === 0) {
            noResults.classList.remove('hidden');
            return;
        }
        noResults.classList.add('hidden');

        data.forEach(item => {
            const badgeColor = 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
            const icon = 'ph-user-focus';

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

    function filterData() {
        const query = searchInput.value.toLowerCase();

        const filtered = historyData.filter(item => {
            return item.title.toLowerCase().includes(query) || item.venue.toLowerCase().includes(query);
        });

        renderCards(filtered);
    }

    if (searchInput) searchInput.addEventListener('input', filterData);

    renderCards(historyData);

    window.openHistoryModal = function(id) {
        const item = historyData.find(i => i.id === id);
        if(!item) return;

        document.getElementById('modalTitle').innerText = item.title;
        document.getElementById('modalType').innerText = item.type + " Record";
        document.getElementById('modalDateTime').innerHTML = `<i class="ph-fill ph-calendar text-pup-maroon dark:text-pup-gold text-lg"></i> ${item.date} • ${item.time}`;
        document.getElementById('modalVenue').innerHTML = `<i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold text-lg"></i> ${item.venue}`;

        document.getElementById('proofTime').innerText = item.date + " at " + item.time;
        document.getElementById('viewAttendanceProof').classList.remove('hidden');

        const evalView = document.getElementById('viewEvaluationProof');
        if (evalView) evalView.classList.add('hidden');

        document.getElementById('historyModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    window.closeHistoryModal = function() {
        document.getElementById('historyModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

});

// =======================================================
// 🟢 DOCUMENT TRACKING LOGIC (THE BULLETPROOF FIX) 🟢
// =======================================================
document.addEventListener('DOMContentLoaded', () => {
    const trackingGrid = document.getElementById('trackingGrid');
    if (!trackingGrid) return; // Para tumakbo lang ito sa Document Tracking Page

    let documentsData = [];
    let docMapInstance = null;

    // Kunin ang data galing sa hidden textarea
    setTimeout(() => {
        try {
            const raw = document.getElementById('django-docs-data').value;
            if (raw && raw.trim() !== '') {
                documentsData = JSON.parse(raw.trim());
            }
        } catch(e) { console.error("Parse Error:", e); }
        
        window.renderTrackingGrid(documentsData);
    }, 100);

    window.renderTrackingGrid = function(dataList) {
        const grid = document.getElementById('trackingGrid');
        const noRes = document.getElementById('noResults');
        if (!grid || !noRes) return;
        
        if (dataList.length === 0) {
            grid.innerHTML = '';
            noRes.classList.remove('hidden');
            return;
        }

        noRes.classList.add('hidden');
        let html = '';

        dataList.forEach((doc) => {
            let statusColor = 'text-yellow-600 bg-yellow-50 border-yellow-200 dark:text-yellow-400 dark:bg-yellow-900/20 dark:border-yellow-900/50';
            let icon = 'ph-clock';
            
            // 🟢 TUGMA SA MGA BAGONG STATUSES NATIN 🟢
            if(doc.status === 'Approved') {
                statusColor = 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-900/20 dark:border-green-900/50';
                icon = 'ph-check-circle';
            } else if (doc.status === 'Admin Approved') {
                statusColor = 'text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-900/20 dark:border-blue-900/50';
                icon = 'ph-file-signature';
            } else if (doc.status === 'Rejected') {
                statusColor = 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-900/20 dark:border-red-900/50';
                icon = 'ph-x-circle';
            }

            const docJson = encodeURIComponent(JSON.stringify(doc));

            html += `
                <div onclick="openTrackingModal('${docJson}')" class="doc-card bg-white dark:bg-[#151515] rounded-2xl p-5 border border-gray-200 dark:border-gray-800 shadow-sm cursor-pointer flex flex-col justify-between h-full relative overflow-hidden group">
                    <div class="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-gray-100 to-transparent dark:from-gray-800 opacity-50 rounded-bl-3xl z-0 transition-transform group-hover:scale-110"></div>
                    
                    <div class="relative z-10">
                        <div class="flex justify-between items-start mb-3">
                            <span class="text-[10px] font-extrabold uppercase tracking-widest text-gray-400 bg-gray-100 dark:bg-[#111] dark:text-gray-500 px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-800">
                                ${doc.orgName}
                            </span>
                            <span class="text-[10px] font-extrabold uppercase tracking-widest px-2.5 py-1 rounded-md border flex items-center gap-1 ${statusColor}">
                                <i class="ph-fill ${icon}"></i> ${doc.status}
                            </span>
                        </div>
                        
                        <h3 class="font-black text-gray-900 dark:text-white text-lg leading-tight mb-1 line-clamp-2">${doc.eventName}</h3>
                        <p class="text-xs font-bold text-pup-maroon dark:text-pup-gold"><i class="ph-bold ph-calendar"></i> Submitted: ${doc.date}</p>
                    </div>

                    <div class="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800 relative z-10 flex items-center justify-between">
                        <div class="flex items-center gap-1.5 text-xs font-bold text-gray-500 dark:text-gray-400 truncate pr-2">
                            <i class="ph-fill ph-map-pin text-gray-400 shrink-0"></i> <span class="truncate">${doc.currentLoc}</span>
                        </div>
                        <i class="ph-bold ph-arrow-right text-gray-300 group-hover:text-pup-maroon dark:group-hover:text-pup-gold transition-colors shrink-0"></i>
                    </div>
                </div>
            `;
        });
        
        grid.innerHTML = html;
    };

    window.filterTrackingDocs = function() {
        const query = document.getElementById('trackSearch').value.toLowerCase().trim();
        const stat = document.getElementById('trackStatusFilter').value;

        const filtered = documentsData.filter(doc => {
            const titleMatch = doc.eventName ? doc.eventName.toLowerCase().includes(query) : false;
            const orgMatch = doc.orgName ? doc.orgName.toLowerCase().includes(query) : false;
            
            const matchSearch = titleMatch || orgMatch;
            
            let matchStat = false;
            if(stat === 'All') matchStat = true;
            else if (stat === 'Pending') matchStat = doc.status.includes('Pending') || doc.status.includes('Verification') || doc.status.includes('Review');
            else matchStat = doc.status === stat;

            return matchSearch && matchStat;
        });

        window.renderTrackingGrid(filtered);
    };

    window.openTrackingModal = function(docStr) {
        const doc = JSON.parse(decodeURIComponent(docStr));
        
        document.getElementById('modalOrgName').innerText = doc.orgName;
        document.getElementById('modalEventTitle').innerText = doc.eventName;
        document.getElementById('modalCurrentLoc').innerText = doc.currentLoc;

        const badge = document.getElementById('modalStatusBadge');
        if(doc.status === 'Approved') {
            badge.className = "font-bold text-[0.65rem] px-3 py-1 rounded-full uppercase tracking-widest border border-green-200 dark:border-green-900/50 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-500";
            badge.innerHTML = `<i class="ph-fill ph-check-circle"></i> Approved`;
        } else if (doc.status === 'Rejected') {
            badge.className = "font-bold text-[0.65rem] px-3 py-1 rounded-full uppercase tracking-widest border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-500";
            badge.innerHTML = `<i class="ph-fill ph-x-circle"></i> Rejected`;
        } else if (doc.status === 'Admin Approved') {
            badge.className = "font-bold text-[0.65rem] px-3 py-1 rounded-full uppercase tracking-widest border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-500";
            badge.innerHTML = `<i class="ph-fill ph-file-signature"></i> Initial Approval`;
        } else {
            badge.className = "font-bold text-[0.65rem] px-3 py-1 rounded-full uppercase tracking-widest border border-yellow-200 dark:border-yellow-900/50 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-500";
            badge.innerHTML = `<i class="ph-fill ph-clock"></i> ${doc.status}`;
        }

        const timeline = document.getElementById('timelineContainer');
        let tHtml = '';

        if (doc.progress === -1) {
            // Rejected State
            tHtml += `
                <div class="relative pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 bg-red-500 w-3.5 h-3.5 rounded-full ring-4 ring-red-500/30 animate-pulse"></div>
                    <p class="text-xs font-bold text-red-600 dark:text-red-500 mb-0.5">Document Rejected</p>
                    <p class="text-[10px] text-red-500/80 leading-relaxed">Returned to Org. Reason: ${doc.rejectReason}</p>
                </div>
            `;
        } else {
            // 🟢 BAGONG 6-STEP TIMELINE LOGIC 🟢
            
            // Step 1: Proposal Submitted
            tHtml += `
                <div class="relative pb-6 border-l-[3px] ${doc.progress > 1 ? 'border-green-500' : 'border-gray-200 dark:border-gray-700'} pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 bg-green-500 w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">1. Proposal Submitted</p>
                    <p class="text-[10px] text-gray-500">Document generated by ${doc.orgName}</p>
                </div>
            `;

            // Step 2: Adviser Initial Review
            let advBorder = doc.progress > 2 ? 'border-green-500' : 'border-gray-200 dark:border-gray-700';
            let advDot = doc.progress >= 2 ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-700';
            let advPulse = doc.progress === 1 ? 'ring-4 ring-green-500/30 animate-pulse' : '';
            tHtml += `
                <div class="relative pb-6 border-l-[3px] ${advBorder} pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 ${advDot} ${advPulse} w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">2. Adviser Review</p>
                    <p class="text-[10px] text-gray-500">${doc.progress > 1 ? 'Approved by Adviser' : 'Currently at Office of the Adviser'}</p>
                </div>
            `;

            // Step 3: Admin Initial Clearance
            let admBorder = doc.progress > 3 ? 'border-green-500' : 'border-gray-200 dark:border-gray-700';
            let admDot = doc.progress >= 3 ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-700';
            let admPulse = doc.progress === 2 ? 'ring-4 ring-green-500/30 animate-pulse' : '';
            tHtml += `
                <div class="relative pb-6 border-l-[3px] ${admBorder} pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 ${admDot} ${admPulse} w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">3. Initial Clearance</p>
                    <p class="text-[10px] text-gray-500">${doc.progress > 2 ? 'Initial approval granted' : 'Currently at Student Services / Admin'}</p>
                </div>
            `;

            // Step 4: Vault Upload (Org Signatures)
            let uploadBorder = doc.progress > 4 ? 'border-green-500' : 'border-gray-200 dark:border-gray-700';
            let uploadDot = doc.progress > 3 ? 'bg-green-500' : (doc.progress === 3 ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-700');
            let uploadPulse = doc.progress === 3 ? 'ring-4 ring-blue-500/30 animate-pulse bg-blue-500' : '';
            tHtml += `
                <div class="relative pb-6 border-l-[3px] ${uploadBorder} pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 ${uploadPulse || uploadDot} w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">4. Document Vault</p>
                    <p class="text-[10px] text-gray-500">${doc.progress === 3 ? '<b class="text-blue-500">ACTION REQUIRED:</b> Upload signed permits.' : (doc.progress > 3 ? 'Documents uploaded by Org.' : 'Awaiting admin clearance.')}</p>
                </div>
            `;

            // Step 5: Adviser Signature Verification
            let verBorder = doc.progress > 5 ? 'border-green-500' : 'border-gray-200 dark:border-gray-700';
            let verDot = doc.progress >= 5 ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-700';
            let verPulse = doc.progress === 4 ? 'ring-4 ring-green-500/30 animate-pulse' : '';
            tHtml += `
                <div class="relative pb-6 border-l-[3px] ${verBorder} pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 ${verDot} ${verPulse} w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">5. Signature Verification</p>
                    <p class="text-[10px] text-gray-500">${doc.progress > 4 ? 'Signatures verified.' : (doc.progress === 4 ? 'Adviser verifying attached signatures.' : 'Awaiting document upload.')}</p>
                </div>
            `;

            // Step 6: Final Publication
            let finDot = doc.progress >= 6 ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-700';
            let finPulse = doc.progress === 5 ? 'ring-4 ring-green-500/30 animate-pulse' : (doc.progress === 6 ? 'ring-4 ring-green-500/30 animate-pulse' : '');
            tHtml += `
                <div class="relative pl-4 ml-2">
                    <div class="absolute -left-[8px] top-0 ${finDot} ${finPulse} w-3.5 h-3.5 rounded-full"></div>
                    <p class="text-xs font-bold text-gray-900 dark:text-white mb-0.5">6. Final Publication</p>
                    <p class="text-[10px] text-gray-500">${doc.progress === 6 ? 'Event is now cleared and published!' : (doc.progress === 5 ? 'Admin final check for publication.' : 'Awaiting signature verification.')}</p>
                </div>
            `;
        }

        timeline.innerHTML = tHtml;

        document.getElementById('trackingModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Initialize Map
        window.initTrackingMap(doc.coords, doc.currentLoc);
    };

    window.closeTrackingModal = function() {
        document.getElementById('trackingModal').classList.add('hidden');
        document.body.style.overflow = '';
    };

    // 🟢 ANG MACHINE-GUN RESIZE HACK PARA LUMABAS ANG MAPA SA MODAL 🟢
    window.initTrackingMap = function(coords, locName) {
        if (docMapInstance !== null) {
            docMapInstance.remove();
            docMapInstance = null;
        }

        const mapContainer = document.getElementById('docMap');
        if (!mapContainer) return;

        docMapInstance = L.map('docMap', {zoomControl: false}).setView(coords, 17);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(docMapInstance);
        
        const markerIcon = L.divIcon({
            className: 'custom-div-icon',
            html: "<div style='background-color:#800000; width:16px; height:16px; border-radius:50%; border:3px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);'></div>",
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
        
        L.marker(coords, {icon: markerIcon}).addTo(docMapInstance)
            .bindPopup(`<b style="color:#800000; font-size:12px;">Current Location</b><br><span style="font-size:11px; line-height:1.2; display:block; margin-top:3px;">${locName}</span>`)
            .openPopup();
        
        // Pilitin ang Leaflet na i-recalculate ang size habang bumababa ang CSS animation ng Modal (15 times in ~450ms)
        let resizeCount = 0;
        let resizeInterval = setInterval(() => {
            docMapInstance.invalidateSize();
            resizeCount++;
            if (resizeCount > 15) clearInterval(resizeInterval); 
        }, 30);
    };
});