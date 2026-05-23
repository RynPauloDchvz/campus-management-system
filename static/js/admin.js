// --- THEME INIT ---
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateIcons(savedTheme);
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateIcons(newTheme);
}

function updateIcons(theme) {
    const icons = document.querySelectorAll('.theme-toggle');
    icons.forEach(icon => {
        if(theme === 'light') icon.classList.replace('ph-moon', 'ph-sun');
        else icon.classList.replace('ph-sun', 'ph-moon');
    });
}

// --- 18 SAMPLE EVENTS DATA ---
let eventsData = [
    { id: 1, org: 'ITO', title: 'World War Summit', date: '2026-03-25', time: '05:20', venue: 'PUP Gymnasium', status: 'Pending Proposal', desc: 'Bridging the Past: The Annual World War Summit.', repName: 'Juan Dela Cruz', repId: '2023-0001-UQ-0' },
    { id: 2, org: 'BPA', title: 'Leadership Summit', date: '2026-03-15', time: '08:00', venue: 'AVR Room', status: 'Cleared', desc: 'Annual leadership summit for Public Administration students.', repName: 'Andres B.', repId: '2021-0102-UQ-0' },
    { id: 3, org: 'FTO', title: 'Teaching Methodologies', date: '2026-04-12', time: '13:00', venue: 'Room 201', status: 'Pending Proposal', desc: 'Workshop for future educators focusing on modern pedagogical methods.', repName: 'Maria Clara', repId: '2022-0050-UQ-0' },
    { id: 4, org: 'ITS', title: 'Code Camp 2026', date: '2026-05-10', time: '09:00', venue: 'Comp Lab 1', status: 'Permit Submitted', desc: 'Intensive programming boot camp for freshmen.', repName: 'Jose Rizal', repId: '2023-0200-UQ-0' },
    { id: 5, org: 'YEO', title: 'Startup Pitch Fest', date: '2026-06-05', time: '14:00', venue: 'Conference Hall', status: 'Rejected', desc: 'Business pitching competition for young entrepreneurs.', repName: 'Gabriela Silang', repId: '2021-0404-UQ-0' },
    { id: 6, org: 'ITO', title: 'Cybersecurity Seminar', date: '2026-07-20', time: '10:00', venue: 'AVR Room', status: 'Cleared', desc: 'Awareness campaign on data privacy and cybersecurity.', repName: 'Emilio Aguinaldo', repId: '2020-0111-UQ-0' },
    { id: 7, org: 'BPA', title: 'Public Governance Forum', date: '2026-08-15', time: '08:30', venue: 'PUP Gymnasium', status: 'Pending Proposal', desc: 'Discussion on transparent governance and public policies.', repName: 'Apolinario Mabini', repId: '2022-0333-UQ-0' },
    { id: 8, org: 'FTO', title: 'Language Arts Festival', date: '2026-09-01', time: '09:00', venue: 'Quadrangle', status: 'Permit Submitted', desc: 'Celebration of languages through poetry and theatrical plays.', repName: 'Melchora Aquino', repId: '2023-0555-UQ-0' },
    { id: 9, org: 'ITS', title: 'Hackathon Beta', date: '2026-09-15', time: '07:00', venue: 'Comp Lab 2', status: 'Cleared', desc: '24-hour coding challenge for IT students.', repName: 'Antonio Luna', repId: '2021-0666-UQ-0' },
    { id: 10, org: 'YEO', title: 'Bazaar Week', date: '2026-10-10', time: '08:00', venue: 'Campus Grounds', status: 'Pending Proposal', desc: 'A week-long bazaar showcasing student-led businesses.', repName: 'Marcelo H. Del Pilar', repId: '2022-0777-UQ-0' },
    { id: 11, org: 'ITO', title: 'AI in Modern World', date: '2026-11-05', time: '13:00', venue: 'AVR Room', status: 'Permit Submitted', desc: 'Exploring the impacts of Artificial Intelligence in society.', repName: 'Gregorio Del Pilar', repId: '2023-0888-UQ-0' },
    { id: 12, org: 'BPA', title: 'Youth Parliament', date: '2026-11-20', time: '09:00', venue: 'Conference Hall', status: 'Cleared', desc: 'Simulation of parliamentary debates and bill drafting.', repName: 'Miguel Malvar', repId: '2020-0999-UQ-0' },
    { id: 13, org: 'FTO', title: 'Child Psychology Talk', date: '2026-12-02', time: '14:30', venue: 'Room 305', status: 'Rejected', desc: 'Understanding the cognitive development of children.', repName: 'Teresa Magbanua', repId: '2021-1122-UQ-0' },
    { id: 14, org: 'ITS', title: 'Web Dev Workshop', date: '2026-12-10', time: '10:00', venue: 'Comp Lab 1', status: 'Pending Proposal', desc: 'Hands-on workshop on React and Django frameworks.', repName: 'Macario Sakay', repId: '2022-2233-UQ-0' },
    { id: 15, org: 'YEO', title: 'Financial Literacy 101', date: '2027-01-15', time: '08:00', venue: 'AVR Room', status: 'Permit Submitted', desc: 'Seminar on investing, saving, and financial management.', repName: 'Diego Silang', repId: '2023-3344-UQ-0' },
    { id: 16, org: 'ITO', title: 'Esports Tournament', date: '2027-02-14', time: '12:00', venue: 'PUP Gymnasium', status: 'Cleared', desc: 'Campus-wide Mobile Legends and Valorant tournament.', repName: 'Lapu-Lapu', repId: '2020-4455-UQ-0' },
    { id: 17, org: 'BPA', title: 'Community Outreach', date: '2027-03-01', time: '07:00', venue: 'Brgy. Unisan', status: 'Pending Proposal', desc: 'Distribution of relief goods and teaching sessions for kids.', repName: 'Sultan Kudarat', repId: '2021-5566-UQ-0' },
    { id: 18, org: 'FTO', title: 'Special Ed Seminar', date: '2027-03-20', time: '09:30', venue: 'AVR Room', status: 'Permit Submitted', desc: 'Handling students with special needs in a modern classroom.', repName: 'Francisco Dagohoy', repId: '2022-6677-UQ-0' }
];

let activeId = null;
let activeEvent = null;

// --- RENDER TABLE ---
function renderTable(data) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    
    data.forEach(item => {
        let badgeClass = '', actionHtml = '';
        
        if(item.status === 'Pending Proposal') {
            badgeClass = 'badge-pending';
            actionHtml = `<button class="btn-action-small btn-primary" onclick="openProposalModal(${item.id})">Review Proposal</button>`;
        } else if(item.status === 'Permit Submitted') {
            badgeClass = 'badge-permit';
            actionHtml = `<button class="btn-action-small" style="background:var(--info); color:white;" onclick="openPermitViewer(${item.id})">Review Permit</button>`;
        } else if(item.status === 'Cleared') {
            badgeClass = 'badge-cleared';
            actionHtml = `<span style="color:var(--text-muted); font-size:0.85rem;"><i class="ph-bold ph-check-circle" style="color:var(--success);"></i> Done</span>`;
        } else {
            badgeClass = 'badge-rejected';
            actionHtml = `<span style="color:var(--text-muted); font-size:0.85rem;">Closed</span>`;
        }

        const row = `
            <tr>
                <td style="font-weight:700; color:var(--accent);">${item.org}</td>
                <td style="font-weight:600;">${item.title}</td>
                <td>${item.date}</td>
                <td><span class="badge ${badgeClass}">${item.status}</span></td>
                <td>${actionHtml}</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function filterTable() {
    const status = document.getElementById('statusFilter').value.toLowerCase();
    const search = document.getElementById('searchInput').value.toLowerCase();
    
    const filtered = eventsData.filter(item => {
        const matchStatus = status === 'all' || item.status.toLowerCase() === status;
        const matchSearch = item.title.toLowerCase().includes(search) || item.org.toLowerCase().includes(search);
        return matchStatus && matchSearch;
    });
    renderTable(filtered);
}

function searchTable() { filterTable(); }

// --- MODAL HELPERS ---
function closeModal(modalId) { 
    document.getElementById(modalId).style.display = 'none'; 
}

function confirmLogout() {
    document.getElementById('logoutModal').style.display = 'flex';
}

// 1. OPEN PROPOSAL (Modify Details)
function openProposalModal(id) {
    activeId = id;
    activeEvent = eventsData.find(e => e.id === id);
    
    document.getElementById('propTitle').innerText = activeEvent.title;
    document.getElementById('propOrg').innerText = activeEvent.org;
    document.getElementById('propDesc').innerText = activeEvent.desc;
    
    document.getElementById('inputDate').value = activeEvent.date;
    document.getElementById('inputTime').value = activeEvent.time;
    document.getElementById('inputVenue').value = activeEvent.venue;
    
    document.getElementById('proposalModal').style.display = 'flex';
}

// SAVE PROPOSAL & APPROVE
function processProposal(action) {
    if(action === 'Approved') {
        activeEvent.date = document.getElementById('inputDate').value;
        activeEvent.time = document.getElementById('inputTime').value;
        activeEvent.venue = document.getElementById('inputVenue').value;
        activeEvent.status = 'Permit Submitted'; 
        alert("Proposal Approved! Organization is now instructed to upload the Signed Permit.");
    } else {
        activeEvent.status = 'Rejected';
        alert("Proposal Rejected.");
    }
    closeModal('proposalModal');
    filterTable();
}

// 2. OPEN DOCUMENT VIEWER
function openDocumentViewer(type) {
    const wrapper = document.getElementById('docContentWrapper');
    const title = document.getElementById('docViewerTitle');
    const footer = document.getElementById('permitFooter');
    
    if(type === 'letter') {
        title.innerText = "Official Request Letter Preview";
        footer.style.display = 'none';
        wrapper.innerHTML = generateLetterHTML();
    } else if (type === 'permit') {
        title.innerText = "Permit to Conduct Activity (Signed Verification)";
        footer.style.display = 'flex';
        wrapper.innerHTML = generatePermitHTML();
    }
    
    document.getElementById('docViewerModal').style.display = 'flex';
}

function openPermitViewer(id) {
    activeId = id;
    activeEvent = eventsData.find(e => e.id === id);
    openDocumentViewer('permit');
}

function confirmPermit() {
    activeEvent.status = 'Cleared';
    alert("Permit Confirmed! Event is now fully Cleared to conduct.");
    closeModal('docViewerModal');
    filterTable();
}

// --- HTML GENERATORS FOR SIMULATED DOCUMENTS ---
// Layout is strictly matched based on User's provided images and requirements

function generateLetterHTML() {
    // Convert 24hr time to 12hr format for the letter
    let timeParts = activeEvent.time.split(':');
    let hours = parseInt(timeParts[0]);
    let ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; 
    let formattedTime = hours + ':' + timeParts[1] + ' ' + ampm;

    // Convert Date to Word Format (e.g. March 25, 2026)
    let dateObj = new Date(activeEvent.date);
    let options = { year: 'numeric', month: 'long', day: 'numeric' };
    let formattedDate = dateObj.toLocaleDateString('en-US', options);

    return `
        <div class="paper-doc">
            <div class="doc-date">${formattedDate}</div>
            
            <div class="doc-sender">
                <strong>${activeEvent.repName}</strong><br>
                ${activeEvent.org} President<br>
                Polytechnic University of the Philippines<br>
                Unisan, Quezon Campus
            </div>
            
            <div class="doc-salutation">Dear <strong>Admin,</strong></div>
            
            <div class="doc-body">
                <p>We, the officers of the <strong>${activeEvent.org}</strong>, are writing to formally propose an event titled <strong>"${activeEvent.title}"</strong>. ${activeEvent.desc}</p>
                
                <p>Join us for an immersive exploration into the subjects that reshape our modern world. Our organization brings together students, educators, and enthusiasts to examine strategic, social, and academic legacies. Through expert-led panels and showcases, we aim to honor our past while uncovering new perspectives on global and local scales.</p>
                
                <p>The said activity is scheduled to take place on <strong>${formattedDate}</strong> at exactly <strong>${formattedTime}</strong>. We humbly request the use of the <strong>${activeEvent.venue}</strong> as our official venue.</p>
                
                <p>Furthermore, to ensure the success of this event, we would like to borrow the following university equipment: <strong>Chairs, Sound System, Projector/TV, Podium, Tables</strong>. Your acceptance and positive response regarding this matter is highly appreciated. Thank you very much and God bless.</p>
                
                <p>Sincerely yours,</p>
            </div>
            
            <div class="doc-signatures">
                <div class="sig-block">
                    <span class="sig-name">${activeEvent.repName.toUpperCase()}</span>
                    <span class="sig-title">${activeEvent.org} President</span>
                </div>
                <div class="sig-block">
                    <span class="sig-name">ORG ADVISER NAME</span>
                    <span class="sig-title">${activeEvent.org} Adviser</span>
                </div>
                <div class="sig-block">
                    <span class="sig-name">ANNABEL S. JANORAS</span>
                    <span class="sig-title">Head, Office of Student Services</span>
                </div>
                <div class="sig-block">
                    <span class="sig-name">PROF. EDWIN G. MALABUYOC</span>
                    <span class="sig-title">Campus Director</span>
                </div>
            </div>
        </div>
    `;
}

function generatePermitHTML() {
    // Permit with NO names, only blank lines as requested. Flows downwards.
    return `
        <div class="paper-doc">
            <div class="permit-header">
                <p class="permit-text-sm">Republic of the Philippines</p>
                <p class="permit-text-md">POLYTECHNIC UNIVERSITY OF THE PHILIPPINES</p>
                <p class="permit-text-sm">Office of the Vice President for Campuses</p>
                <p class="permit-text-md" style="margin-bottom:10px;">Unisan, Quezon</p>
            </div>
            
            <div style="text-align: right; font-size: 0.9rem; margin-bottom: 25px;">Permit #: <strong>26-001-${activeEvent.id}</strong></div>
            <div class="permit-title">PERMIT TO CONDUCT ACTIVITY</div>
            <div class="permit-subtitle"><strong>${activeEvent.title}</strong><br>(Activity to be conducted)</div>

            <table class="permit-table">
                <tr><td>Program Holding the Activity:</td><td style="border-bottom: 1px solid #000;">${activeEvent.org}</td></tr>
                <tr><td>Student Representative Name:</td><td style="border-bottom: 1px solid #000;">${activeEvent.repName}</td></tr>
                <tr><td>Student Representative ID:</td><td style="border-bottom: 1px solid #000;">${activeEvent.repId}</td></tr>
                <tr><td style="padding-top:15px;">Purpose of Permit:</td><td style="padding-top:15px;">Conduct Activity</td></tr>
            </table>

            <div style="border: 1px solid #ccc; padding: 15px; margin-bottom: 35px;">
                <p style="margin:0 0 10px 0; font-size:0.9rem; color:#666;">Permit Duration:</p>
                <table style="width:100%; font-size:0.95rem;">
                    <tr><td style="width:15%;">Date:</td><td><strong>${activeEvent.date}</strong></td></tr>
                    <tr><td>Time:</td><td><strong>${activeEvent.time}</strong></td></tr>
                </table>
            </div>

            <div class="permit-sig-grid">
                <div>
                    <span>Subject Advisor:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                <div>
                    <span>Date:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>

                <div style="margin-top:15px;">
                    <span>Area Chairperson:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                <div style="margin-top:15px;">
                    <span>Date:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>

                <div style="margin-top:15px;">
                    <span>Security Office:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                <div style="margin-top:15px;">
                    <span>Date:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>

                <div style="margin-top:15px;">
                    <span>Property Office:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                <div style="margin-top:15px;">
                    <span>Date:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                
                <div style="margin-top:15px;">
                    <span>Student Signature:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
                <div style="margin-top:15px;">
                    <span>Date:</span> <br>
                    <span class="sig-line" style="margin-top:20px; width: 80%;">_____________________</span>
                </div>
            </div>

            <div style="margin-top: 40px;">
                <p style="margin-bottom:30px;">RECOMMENDING APPROVAL:</p>
                <span class="sig-line" style="width: 50%;">_________________________________</span><br>
                <span style="display:inline-block; padding-top:5px; font-size: 0.9rem;">Head, Student Services</span>
            </div>

            <div style="margin-top: 40px;">
                <p style="margin-bottom:30px;">APPROVED:</p>
                <span class="sig-line" style="width: 50%;">_________________________________</span><br>
                <span style="display:inline-block; padding-top:5px; font-size: 0.9rem;">Director</span>
            </div>
        </div>
    `;
}

// Init
window.onload = () => { 
    initTheme(); 
    renderTable(eventsData); 
};

