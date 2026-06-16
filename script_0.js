
    const eventsText = document.getElementById('events-data').textContent;
    const EVENTS_DATA = eventsText ? JSON.parse(eventsText) : [];
    
    const organizerText = document.getElementById('organizer-data').textContent;
    const ORGANIZER_DATA = organizerText ? JSON.parse(organizerText) : { face_encoding: null };
    
    const DEFAULT_IMG = "{% static 'images/PUPLogo.png' %}";
    const CAMPUS_COORDS = [13.84615, 121.96955];

    function initSchoolEventsLogic() {
        const eventsGrid = document.getElementById('eventsGrid');
        const noResults = document.getElementById('noResults');
        const searchInput = document.getElementById('eventSearch');
        const modalOverlay = document.getElementById('modalOverlay');
        const questionModal = document.getElementById('questionModal');
        const registrationModal = document.getElementById('registrationModal');
        const participationModal = document.getElementById('participationModal');
        const btnParticipate = document.getElementById('btnParticipate');
        
        let currentEvent = null;
        let videoStream = null;
        let scanInterval = null;
        let faceMatcher = null;
        let isFaceVerified = false;
        let isLocationVerified = false;
        let userLat = null;
        let userLng = null;
        let modelsLoaded = false;

        let qualityStatus = { tooDark: false, tooBright: false, obstructed: false, noFaceDetail: false, isReady: false };
        let qualityScore = 0;
        let validationInterval = null;

        function renderEvents(query = '') {
            if (!eventsGrid) return;
            eventsGrid.innerHTML = '';
            const filtered = EVENTS_DATA.filter(e => e.title.toLowerCase().includes(query.toLowerCase()));
            if (filtered.length === 0) { if(noResults) noResults.style.display = 'block'; return; }
            if(noResults) noResults.style.display = 'none';

            filtered.forEach(e => {
                const card = document.createElement('div');
                card.className = "bg-white dark:bg-pup-darkcard rounded-2xl sm:rounded-[2rem] overflow-hidden border border-gray-100 dark:border-gray-800 flex flex-row sm:flex-col cursor-pointer group shadow-sm hover:shadow-2xl transition-all duration-700 h-full";
                card.innerHTML = `
                    <div class="w-24 h-24 sm:h-40 sm:w-full shrink-0 relative overflow-hidden bg-gray-100 dark:bg-gray-800 flex items-center justify-center border-r sm:border-r-0 sm:border-b border-gray-100 dark:border-gray-800">
                        <img src="${e.image}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000" onerror="this.src=DEFAULT_IMG; this.classList.remove('object-cover'); this.classList.add('object-contain', 'p-6 sm:p-8');">
                        <div class="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent hidden sm:block"></div>
                        <div class="absolute top-2 right-2 sm:top-4 sm:right-4">
                            <span class="text-white text-[6px] sm:text-[8px] px-1.5 py-0.5 sm:px-2.5 sm:py-1 rounded-full font-black uppercase tracking-widest shadow-2xl countdown-small flex items-center gap-1 sm:gap-1.5" data-event-id="${e.id}">
                                <i class="ph-bold ph-clock"></i> --:--:--
                            </span>
                        </div>
                    </div>
                    <div class="p-3 sm:p-5 flex flex-col flex-grow min-w-0">
                        <div class="text-[7px] sm:text-[8px] font-black text-pup-maroon dark:text-pup-gold mb-0.5 sm:mb-1 uppercase tracking-[0.2em]">${e.date_display}</div>
                        <h3 class="font-black text-xs sm:text-base text-gray-900 dark:text-white leading-tight mb-1 sm:mb-3 uppercase tracking-tighter truncate">${e.title}</h3>
                        <div class="flex items-center justify-between pt-2 sm:pt-4 border-t border-gray-50 dark:border-gray-800 mt-auto">
                             <div class="flex items-center gap-1 sm:gap-1.5 text-gray-400 font-bold text-[7px] sm:text-[8px] uppercase tracking-widest truncate">
                                <i class="ph-fill ph-map-pin text-pup-maroon dark:text-pup-gold"></i> <span class="truncate">${e.venue}</span>
                             </div>
                             <i class="ph-bold ph-arrow-right text-gray-200 group-hover:text-pup-maroon dark:group-hover:text-pup-gold transition-all group-hover:translate-x-1 text-xs sm:text-base"></i>
                        </div>
                    </div>
                `;
                card.addEventListener('click', () => openModal(e));
                eventsGrid.appendChild(card);
            });
            updateAllCountdowns();
        }

        function updateAllCountdowns() {
            const now = new Date();
            document.querySelectorAll('.countdown-small').forEach(el => {
                const e = EVENTS_DATA.find(evt => evt && evt.id == el.dataset.eventId);
                if (!e) return;
                const start = new Date(`${e.date}T${e.start_time_iso}`);
                const end = e.end_time_iso ? new Date(`${e.date}T${e.end_time_iso}`) : null;
                const expiry = end ? new Date(end.getTime() + (60 * 60 * 1000)) : new Date(start.getTime() + (4 * 60 * 60 * 1000));
                const diffStart = start - now;
                const diffExpiry = expiry - now;
                if (diffStart > 0) {
                    el.innerHTML = `<i class="ph-bold ph-hourglass"></i> ${formatTimeDiff(diffStart)}`;
                    el.className = "text-white text-[9px] px-3 py-1.5 rounded-full font-black uppercase tracking-widest shadow-2xl countdown-small status-upcoming";
                } else if (diffExpiry > 0) {
                    el.innerHTML = `<i class="ph-bold ph-activity"></i> LIVE`;
                    el.className = "text-white text-[9px] px-3 py-1.5 rounded-full font-black uppercase tracking-widest shadow-2xl countdown-small status-ongoing animate-pulse";
                } else {
                    el.innerHTML = `<i class="ph-bold ph-clock-counter-clockwise"></i> ENDED`;
                    el.className = "text-white text-[9px] px-3 py-1.5 rounded-full font-black uppercase tracking-widest shadow-2xl countdown-small status-ended";
                }
            });
        }

        function formatTimeDiff(ms) {
            const s = Math.floor(ms / 1000);
            const h = Math.floor(s / 3600);
            const m = Math.floor((s % 3600) / 60);
            const sec = s % 60;
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
        }

        function openModal(e) {
            currentEvent = e;
            document.getElementById('modalImg').src = e.image;
            document.getElementById('modalTitle').innerText = e.title;
            document.getElementById('modalDate').innerText = e.date_display;
            document.getElementById('modalVenue').innerText = e.venue;
            document.getElementById('modalTime').innerText = `${e.date_display} @ ${e.time}`;
            document.getElementById('modalDesc').innerText = e.description || "No description provided.";
            
            const now = new Date();
            const start = new Date(`${e.date}T${e.start_time_iso}`);
            const end = e.end_time_iso ? new Date(`${e.date}T${e.end_time_iso}`) : null;
            const expiry = end ? new Date(end.getTime() + (60 * 60 * 1000)) : new Date(start.getTime() + (4 * 60 * 60 * 1000));
            
            const diffStart = start - now;
            const diffExpiry = expiry - now;

            if (diffStart <= 0 && diffExpiry > 0) {
                document.getElementById('countdownContainer').classList.remove('hidden');
                document.getElementById('endedStatus').classList.add('hidden');
                document.getElementById('btnParticipateWrapper').classList.remove('hidden');
                updateModalCountdown(diffExpiry);
            } else if (diffExpiry <= 0) {
                document.getElementById('countdownContainer').classList.add('hidden');
                document.getElementById('endedStatus').classList.remove('hidden');
                document.getElementById('btnParticipateWrapper').classList.add('hidden');
            } else {
                document.getElementById('countdownContainer').classList.add('hidden');
                document.getElementById('endedStatus').classList.add('hidden');
                document.getElementById('btnParticipateWrapper').classList.add('hidden');
            }
            modalOverlay.style.display = 'flex';
        }

        function updateModalCountdown(diff) {
            const el = document.getElementById('modalCountdown');
            const timer = setInterval(() => {
                if (!currentEvent) { clearInterval(timer); return; }
                const now = new Date();
                const end = currentEvent.end_time_iso ? new Date(`${currentEvent.date}T${currentEvent.end_time_iso}`) : null;
                const expiry = end ? new Date(end.getTime() + (60 * 60 * 1000)) : null;
                if (!expiry) { clearInterval(timer); return; }
                const currentDiff = expiry - now;
                if (currentDiff <= 0) { clearInterval(timer); closeModal(); return; }
                el.innerText = formatTimeDiff(currentDiff);
            }, 1000);
        }

        function closeEventDetailsModal() { modalOverlay.style.display = 'none'; }
        function resetCurrentEvent() { currentEvent = null; }

        if (btnParticipate) btnParticipate.addEventListener('click', () => { closeEventDetailsModal(); questionModal.style.display = 'flex'; });
        document.getElementById('btnCancelQuestion').addEventListener('click', () => { questionModal.style.display = 'none'; resetCurrentEvent(); });
        document.getElementById('btnCancelReg').addEventListener('click', () => { registrationModal.style.display = 'none'; stopScanner(); resetCurrentEvent(); });
        document.getElementById('btnCancelScan').addEventListener('click', () => { participationModal.style.display = 'none'; stopScanner(); resetCurrentEvent(); });
        document.getElementById('modalClose').addEventListener('click', () => { closeEventDetailsModal(); resetCurrentEvent(); });

        document.getElementById('btnAlreadyRegistered').addEventListener('click', () => {
            questionModal.style.display = 'none';
            if (!ORGANIZER_DATA.face_encoding) { alert("Please register first."); questionModal.style.display = 'flex'; return; }
            startParticipationScanner();
        });

        document.getElementById('btnNeedRegister').addEventListener('click', () => { questionModal.style.display = 'none'; startRegistrationScanner(); });
        document.getElementById('btnUpdateFace').addEventListener('click', () => { questionModal.style.display = 'none'; startRegistrationScanner(); });

        async function loadModels() {
            // Models are no longer loaded on frontend, backend handles verification
            modelsLoaded = true;
        }

        loadModels().then(() => {
            if (ORGANIZER_DATA.face_encoding) console.log("Organizer Biometrics loaded.");
        });

        async function startRegistrationScanner() {
            registrationModal.style.display = 'flex';
            const status = document.getElementById('regScanStatus');
            status.innerText = "INITIALIZING SENSORS...";
            if (!modelsLoaded) await loadModels();
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } } });
                const v = document.getElementById('regVideo');
                v.srcObject = videoStream;
                v.onloadedmetadata = () => {
                    document.getElementById('regLoader').style.display = 'none';
                    v.play();
                    startQualityValidation(v, 'reg');
                    let capturedEncoding = null;
                    const btn = document.getElementById('btnConfirmReg');
                    
                    const scanUpdateLoop = async () => {
                        if (!videoStream) return;
                        if (!qualityStatus.isReady) { 
                            btn.disabled = true; 
                            status.innerText = "OPTIMIZING SENSORS..."; 
                        } else {
                            btn.disabled = false;
                            status.innerText = "SENSOR READY! CLICK REGISTER";
                            status.className = "absolute top-4 left-4 right-4 bg-green-600/90 backdrop-blur-2xl px-3 py-2 rounded-full text-white text-[8px] font-black uppercase tracking-[0.2em] text-center shadow-2xl";
                        }
                        scanInterval = setTimeout(scanUpdateLoop, 300);
                    };
                    scanUpdateLoop();
                    
                    btn.onclick = async () => {
                        btn.disabled = true; btn.innerText = "REGISTERING...";
                        
                        const canvas = document.createElement('canvas');
                        canvas.width = v.videoWidth; canvas.height = v.videoHeight;
                        canvas.getContext('2d').drawImage(v, 0, 0);
                        const capturedImage = canvas.toDataURL('image/jpeg', 0.9);

                        const fd = new FormData(); 
                        fd.append('face_encoding', capturedImage);
                        
                        const csrf = document.cookie.split('; ').find(r => r.startsWith('csrftoken=')).split('=')[1];
                        try {
                            const res = await fetch('/organizer/register-face/', { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd });
                            const data = await res.json();
                            if (data.status === 'success') {
                                ORGANIZER_DATA.face_encoding = capturedImage;
                                alert("Success!"); registrationModal.style.display = 'none'; stopScanner(); startParticipationScanner();
                            } else { alert(data.message); btn.disabled = false; btn.innerText = "Register Identity"; }
                        } catch (e) { alert("Registration failed: " + e.message); btn.disabled = false; }
                    };
                };
            } catch (e) { alert("Camera Error (Registration): " + e.message); registrationModal.style.display = 'none'; }
        }

        async function startParticipationScanner() {
            participationModal.style.display = 'flex';
            const status = document.getElementById('scanStatus');
            status.innerText = "AUTHENTICATING SENSORS...";
            isFaceVerified = false; 
            isLocationVerified = false;
            updateSubmitButton();

            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } } });
                const v = document.getElementById('video');
                v.srcObject = videoStream;
                v.onloadedmetadata = () => {
                    document.getElementById('scannerLoader').style.display = 'none';
                    v.play();
                    startQualityValidation(v);
                    startGeofenceWatch();
                    const partScanLoop = async () => {
                        if (!videoStream) return;
                        const faceStatus = document.querySelector('#faceStatus .status-label');
                        if (!qualityStatus.isReady) { 
                            status.innerText = "OPTIMIZING SENSOR QUALITY..."; 
                            status.className = "absolute top-6 left-6 right-6 bg-amber-600/90 backdrop-blur-2xl px-4 py-3 rounded-full text-white text-[9px] font-black uppercase tracking-[0.25em] text-center shadow-2xl animate-pulse";
                        } else {
                            status.innerText = "SENSOR READY! ALIGN FACE TO CENTER";
                            status.className = "absolute top-6 left-6 right-6 bg-green-600/90 backdrop-blur-2xl px-4 py-3 rounded-full text-white text-[9px] font-black uppercase tracking-[0.25em] text-center shadow-2xl";
                        }
                        updateSubmitButton();
                        if (videoStream) scanInterval = setTimeout(partScanLoop, 300);
                    };
                    partScanLoop();
                };
            } catch (e) { alert("Camera Error (Participation): " + e.message); participationModal.style.display = 'none'; }
        }

        function startGeofenceWatch() {
            const locLabel = document.querySelector('#locStatus .status-label');
            navigator.geolocation.watchPosition((pos) => {
                userLat = pos.coords.latitude; userLng = pos.coords.longitude;
                const titleLower = currentEvent && currentEvent.title ? currentEvent.title.toLowerCase() : '';
                const isFlagRaising = currentEvent && (currentEvent.is_flag_raising || titleLower.includes('flag') || titleLower.includes('ceremony'));
                
                if (isFlagRaising) {
                    isLocationVerified = true; locLabel.innerText = "GLOBAL ACCESS VERIFIED"; locLabel.className = "status-label text-[10px] font-black text-green-500 uppercase tracking-widest";
                } else {
                    const targetLat = currentEvent ? currentEvent.target_lat : CAMPUS_COORDS[0];
                    const targetLng = currentEvent ? currentEvent.target_lng : CAMPUS_COORDS[1];
                    const dist = calculateDistance(userLat, userLng, targetLat, targetLng);
                    if (dist <= 300) {
                        isLocationVerified = true; locLabel.innerText = "GEOFENCE VERIFIED"; locLabel.className = "status-label text-[10px] font-black text-green-500 uppercase tracking-widest";
                    } else {
                        isLocationVerified = false; locLabel.innerText = `OUTSIDE (${Math.round(dist)}m)`; locLabel.className = "status-label text-[10px] font-black text-red-500 uppercase tracking-widest";
                    }
                }
                updateSubmitButton();
            }, null, { enableHighAccuracy: true });
        }

        function calculateDistance(lat1, lon1, lat2, lon2) {
            const R = 6371e3;
            const φ1 = lat1 * Math.PI/180; const φ2 = lat2 * Math.PI/180;
            const Δφ = (lat2-lat1) * Math.PI/180; const Δλ = (lon2-lon1) * Math.PI/180;
            const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ/2) * Math.sin(Δλ/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }

        function updateSubmitButton() {
            const btn = document.getElementById('btnSubmitScan');
            if (btn) btn.disabled = !(qualityStatus.isReady && isLocationVerified);
        }

        const btnSubmitScan = document.getElementById('btnSubmitScan');
        if (btnSubmitScan) {
            btnSubmitScan.addEventListener('click', async () => {
                const btn = document.getElementById('btnSubmitScan');
                btn.disabled = true; btn.innerText = "COMMITTING...";
                try {
                    const v = document.getElementById('video');
                    const canvas = document.createElement('canvas');
                    canvas.width = v.videoWidth; canvas.height = v.videoHeight;
                    canvas.getContext('2d').drawImage(v, 0, 0);
                    const faceImage = canvas.toDataURL('image/jpeg', 0.8);

                    const fd = new FormData();
                    fd.append('event_id', currentEvent.id);
                    fd.append('face_image', faceImage);
                    fd.append('face_matched', isFaceVerified);
                    fd.append('is_valid_location', isLocationVerified);
                    fd.append('latitude', userLat);
                    fd.append('longitude', userLng);
                    let csrf = '';
                    const csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
                    if (csrfMatch) csrf = csrfMatch[1];
                    else {
                        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
                        if (csrfInput) csrf = csrfInput.value;
                    }

                    const res = await fetch('/record-attendance/', { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: fd });
                    if (!res.ok) throw new Error("Server returned " + res.status);
                    const data = await res.json();
                    if (data.status === 'success' || data.status === 'issue') {
                        alert(data.message || "Attendance Recorded Successfully!"); location.reload();
                    } else { alert(data.message || "Error"); btn.disabled = false; btn.innerText = "Submit Entry"; }
                } catch (e) { alert("Error: " + e.message); console.error(e); btn.disabled = false; btn.innerText = "Submit Entry"; }
            });
        }

        function stopScanner() {
            if (videoStream) { videoStream.getTracks().forEach(track => track.stop()); videoStream = null; }
            if (scanInterval) { clearInterval(scanInterval); scanInterval = null; }
            if (validationInterval) { clearInterval(validationInterval); validationInterval = null; }
            document.getElementById('qualityMeter').classList.add('hidden');
            document.getElementById('regQualityMeter').classList.add('hidden');
        }

        function startQualityValidation(video, prefix = '') {
            if (validationInterval) clearInterval(validationInterval);
            const canvas = document.createElement('canvas'); const ctx = canvas.getContext('2d');
            const meter = document.getElementById(prefix ? prefix + 'QualityMeter' : 'qualityMeter');
            if (meter) meter.classList.remove('hidden');
            validationInterval = setInterval(() => {
                if (!videoStream || !video || video.videoWidth === 0) return;
                canvas.width = 64; canvas.height = 64; ctx.drawImage(video, 0, 0, 64, 64);
                const data = ctx.getImageData(0, 0, 64, 64).data;
                let brightness = 0;
                for (let i = 0; i < data.length; i += 4) brightness += (data[i] + data[i+1] + data[i+2]) / 3;
                const avg = brightness / (64 * 64);
                qualityStatus.isReady = avg > 40 && avg < 230;
                const bar = document.getElementById(prefix ? prefix + 'QualityBar' : 'qualityBar');
                const text = document.getElementById(prefix ? prefix + 'QualityText' : 'qualityText');
                if (bar && text) {
                    if (qualityStatus.isReady) {
                        bar.style.width = '100%'; bar.className = "h-full bg-green-500 transition-all";
                        text.innerText = "OPTIMIZED"; text.className = "text-[10px] font-bold text-green-500 uppercase";
                    } else {
                        bar.style.width = '30%'; bar.className = "h-full bg-amber-500 transition-all";
                        text.innerText = "ADJUSTING..."; text.className = "text-[10px] font-bold text-amber-500 uppercase";
                    }
                }
            }, 200);
        }

        if(searchInput) searchInput.addEventListener('input', () => renderEvents(searchInput.value));
        const overlay = document.getElementById('modalOverlay');
        if(overlay) overlay.addEventListener('click', () => { closeEventDetailsModal(); resetCurrentEvent(); });
        const closeBtn = document.getElementById('btnClose');
        if(closeBtn) closeBtn.addEventListener('click', () => { closeEventDetailsModal(); resetCurrentEvent(); });

        renderEvents();
        setInterval(updateAllCountdowns, 1000);
    }

    document.addEventListener('DOMContentLoaded', () => { setTimeout(initSchoolEventsLogic, 100); });
