document.addEventListener("DOMContentLoaded", () => {
    // --- UI Navigation ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const contentAreas = document.querySelectorAll('.content-area');
    
    // Initial fetch and global interval
    fetchMetrics();
    setInterval(fetchMetrics, 5000); 

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            contentAreas.forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.getElementById(target).style.display = 'flex';
            
            if (target === 'dash-view') {
                fetchMetrics(); // Refresh immediately on view
            }
        });
    });

    const chatHistory = document.querySelector(".chat-history");
    const newChatBtn = document.querySelector(".new-chat-btn");
    const sessionListEl = document.getElementById("session-history-list");
    const chatInput = document.querySelector(".chat-input");
    const sendBtn = document.querySelector(".send-btn");
    
    let isProcessing = false;
    let currentSessionId = localStorage.getItem("rem_session_id") || "session_" + Date.now();
    localStorage.setItem("rem_session_id", currentSessionId);

    // Initialize sidebar
    fetchSessions();
    
    if (newChatBtn) {
        newChatBtn.addEventListener("click", () => {
            currentSessionId = "session_" + Date.now();
            localStorage.setItem("rem_session_id", currentSessionId);
            clearChatUI();
            fetchSessions();
        });
    }

    function clearChatUI() {
        chatHistory.innerHTML = `
            <div class="message ai-message">
                <div class="avatar ai-avatar"><i class="ph-fill ph-brain"></i></div>
                <div class="message-content">
                    <p>New Research Session Initialized. How can I assist you in this new session?</p>
                </div>
            </div>
        `;
    }

    async function fetchSessions() {
        try {
            const res = await fetch('/api/sessions');
            const data = await res.json();
            sessionListEl.innerHTML = '';
            data.sessions.forEach(sid => {
                const li = document.createElement("li");
                li.className = `session-item ${sid === currentSessionId ? 'active' : ''}`;
                li.innerHTML = `<i class="ph ph-chat-text"></i> ${sid.substring(0, 15)}...`;
                li.onclick = () => switchSession(sid);
                sessionListEl.appendChild(li);
            });
        } catch (e) {
            console.error("Failed to fetch sessions", e);
        }
    }

    async function switchSession(sid) {
        currentSessionId = sid;
        localStorage.setItem("rem_session_id", sid);
        document.querySelectorAll(".session-item").forEach(el => el.classList.remove("active"));
        fetchSessions();
        
        chatHistory.innerHTML = '<div class="message ai-message"><div class="message-content"><p><em>Loading research history...</em></p></div></div>';
        try {
            const res = await fetch(`/api/history/${sid}`);
            const data = await res.json();
            chatHistory.innerHTML = '';
            data.history.forEach(item => {
                appendUserMessage(item.input, false);
                appendAIMessage(item, false);
            });
        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    function appendUserMessage(text, scroll = true) {
        const msgHtml = `<div class="message user-message"><div class="avatar user-avatar">U</div><div class="message-content"><p>${text}</p></div></div>`;
        chatHistory.insertAdjacentHTML('beforeend', msgHtml);
        if (scroll) chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function appendAIMessage(data, scroll = true) {
        let toolHtml = '';
        const statusBadge = document.getElementById('ai-status-badge');
        
        if (!data || !data.answer) return;

        // --- 1. Badge & Source Logic ---
        if (data.web_used) {
            statusBadge.style.display = 'inline-flex';
            statusBadge.className = 'badge badge-ollama researcher-active';
            statusBadge.innerHTML = `<i class="ph-fill ph-magnifying-glass"></i> Researcher Active (web)`;
        } else if (data.source.includes("Ensemble")) {
             statusBadge.style.display = 'inline-flex';
             statusBadge.className = 'badge badge-ensemble';
             statusBadge.innerHTML = `<i class="ph-fill ph-brain"></i> Local Ensemble Consensus`;
        } else if (data.source.includes("Ollama")) {
            statusBadge.style.display = 'inline-flex';
            statusBadge.className = 'badge badge-ollama';
            statusBadge.innerHTML = `<i class="ph-fill ph-lightning"></i> ${data.source}`;
        } else if (data.source.includes("Gemini") || data.source.includes("Qwen")) {
            statusBadge.style.display = 'inline-flex';
            statusBadge.style.background = '#F0FFF4';
            statusBadge.style.color = '#2F855A';
            const icon = data.source.includes("Qwen") ? 'ph-sparkle' : 'ph-cloud';
            statusBadge.innerHTML = `<i class="ph-fill ${icon}"></i> ${data.source}`;
        }

        // --- 2. Tool Trace Logic ---
        if (data.math_used) {
            toolHtml = `<div class="tool-call"><i class="ph ph-function"></i><span>Math Engine active... Solved via SymPy</span></div>`;
        } else if (data.source.includes("Ensemble")) {
            toolHtml = `<div class="tool-call" style="border-left-color: #3182CE;"><i class="ph ph-cpu" style="color: #3182CE;"></i><span>Ensemble Consistency Hit... Verified via 768-dim BERT Embeddings</span></div>`;
        }

        // --- 3. Augmented Memory (Summary Parsing) ---
        let summaryCardHtml = '';
        let displayAnswer = data.answer;
        const summaryMatch = data.answer.match(/\[MEM_SUMMARY:\s*(.*?)\]/s);
        
        if (summaryMatch) {
            const summaryText = summaryMatch[1].trim();
            summaryCardHtml = `
                <div class="knowledge-proposal">
                    <div class="proposal-header"><i class="ph-fill ph-lightbulb"></i> Knowledge Proposal</div>
                    <div class="proposal-content">${summaryText}</div>
                </div>`;
            // Clean the main display answer by removing the summary block
            displayAnswer = data.answer.replace(/\[MEM_SUMMARY:.*?\]/s, '').trim();
        }

        const renderedAnswer = marked.parse(displayAnswer);
        const msgId = data.msg_id || `msg_${Date.now()}`;
        let latencyTag = data.latency_ms ? ` • Speed: ${data.latency_ms}ms` : '';
        
        const msgHtml = `
            <div class="message ai-message" data-id="${msgId}">
                <div class="avatar ai-avatar"><i class="ph-fill ph-brain"></i></div>
                <div class="message-content">
                    ${toolHtml}
                    ${summaryCardHtml}
                    <div class="rendered-markdown">${renderedAnswer}</div>
                    
                    <div class="message-actions">
                        <div class="confidence-tag">
                            <i class="ph-fill ph-check-circle"></i> Confidence: ${data.confidence}${latencyTag}
                        </div>
                        <div class="feedback-bar">
                            <button class="action-btn copy-btn" onclick="copyToClipboard('${msgId}')"><i class="ph ph-copy"></i></button>
                            <button class="action-btn feedback-btn up" onclick="sendFeedback('${msgId}', 'up')"><i class="ph ph-thumbs-up"></i></button>
                            <button class="action-btn feedback-btn down" onclick="sendFeedback('${msgId}', 'down')"><i class="ph ph-thumbs-down"></i></button>
                        </div>
                    </div>
                </div>
            </div>`;
        
        chatHistory.insertAdjacentHTML('beforeend', msgHtml);
        if (scroll) chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    window.copyToClipboard = (msgId) => {
        const msgEl = document.querySelector(`.message[data-id="${msgId}"] .rendered-markdown`);
        if (!msgEl) return;
        navigator.clipboard.writeText(msgEl.innerText).then(() => {
            const btn = document.querySelector(`.message[data-id="${msgId}"] .copy-btn`);
            const icon = btn.querySelector('i');
            icon.className = 'ph-fill ph-check';
            setTimeout(() => { icon.className = 'ph ph-copy'; }, 2000);
        });
    };

    window.sendFeedback = async (msgId, type) => {
        const msgEl = document.querySelector(`.message[data-id="${msgId}"]`);
        const btns = msgEl.querySelectorAll('.feedback-btn');
        const proposal = msgEl.querySelector('.knowledge-proposal');
        
        try {
            const res = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: msgId, type: type })
            });
            
            if (res.ok) {
                btns.forEach(b => b.classList.remove('active'));
                const target = msgEl.querySelector(`.feedback-btn.${type}`);
                target.classList.add('active');
                
                const icon = target.querySelector('i');
                icon.className = icon.className.replace('ph ', 'ph-fill ');

                // If it was a proposal confirmation, update the card state
                if (type === 'up' && proposal) {
                    proposal.classList.add('proposal-committed');
                    proposal.querySelector('.proposal-header').innerHTML = `<i class="ph-fill ph-check-square"></i> Committed to Permanent Knowledge`;
                }
            }
        } catch (e) {
            console.error("Feedback failed", e);
        }
    };

    function appendLoading() {
        const id = 'loading-' + Date.now();
        const msgHtml = `<div class="message ai-message" id="${id}"><div class="avatar ai-avatar"><i class="ph-fill ph-brain"></i></div><div class="message-content"><p><em>Resolving through REM Ensemble logic...</em></p></div></div>`;
        chatHistory.insertAdjacentHTML('beforeend', msgHtml);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        chatInput.value = '';
        appendUserMessage(text);
        const loadingId = appendLoading();
        isProcessing = true;
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, session_id: currentSessionId })
            });
            const data = await response.json();
            document.getElementById(loadingId).remove();
            appendAIMessage(data);
            fetchMetrics();
        } catch (error) {
            document.getElementById(loadingId).remove();
            appendAIMessage({ answer: "Connection lost. Please restart the backend server.", source: "System", confidence: "0" });
        }
        isProcessing = false;
    }

    sendBtn.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });

    // --- Metrics & Charts ---
    const primaryColor = '#FF8652';
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Inter' } } } }
    };

    let sourceChartInstance = null;
    let tagChartInstance = null;
    let latencyChartInstance = null;
    let ecgChartInstance = null;

    const ecgDataSize = 100;
    const ecgDataArr = Array(ecgDataSize).fill(0);
    const ecgLabels = Array(ecgDataSize).fill('');

    function initECG() {
        const ctxE = document.getElementById('ecgChart').getContext('2d');
        ecgChartInstance = new Chart(ctxE, {
            type: 'line',
            data: {
                labels: ecgLabels,
                datasets: [{
                    label: 'System Load',
                    data: ecgDataArr,
                    borderColor: '#3182CE', // Changed to blue to match Ensemble
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { min: -10, max: 20, display: false }
                }
            }
        });

        setInterval(() => {
            ecgDataArr.shift();
            let val = 0;
            if (isProcessing) {
                val = (Math.random() * 20) - 5;
            } else {
                if (Math.random() > 0.95) val = 15;
                else val = (Math.random() * 2) - 1;
            }
            ecgDataArr.push(val);
            if (document.getElementById('dash-view').style.display !== 'none') {
                 ecgChartInstance.update();
            }
        }, 100);
    }
    initECG();

    async function fetchMetrics() {
        try {
            const res = await fetch('/api/metrics');
            const data = await res.json();
            
            const totalEl = document.getElementById('stat-total-memory');
            const highFidEl = document.getElementById('stat-factbook-count');
            
            if (totalEl) totalEl.textContent = data.total;
            // Map 'verified-persistent' count to factual stat card
            const verifiedCount = (data.tags && data.tags['verified-persistent']) || 0;
            if (highFidEl) highFidEl.textContent = verifiedCount;
            
            const headerBadge = document.querySelector('#dash-view .badge-math');
            if (headerBadge) {
                headerBadge.innerHTML = `<i class="ph-fill ph-broadcast"></i> Knowledge Bank Synced: ${new Date().toLocaleTimeString()}`;
            }

            const sourceLabels = Object.keys(data.sources);
            const sourceData = Object.values(data.sources);
            
            if (!sourceChartInstance) {
                const ctxS = document.getElementById('sourceChart').getContext('2d');
                sourceChartInstance = new Chart(ctxS, {
                    type: 'doughnut',
                    data: {
                        labels: sourceLabels,
                        datasets: [{ data: sourceData, backgroundColor: ['#3182CE', '#4FD1C5', '#FF8652', '#F6AD55'], borderWidth: 0 }]
                    },
                    options: chartOptions
                });
            } else {
                sourceChartInstance.data.labels = sourceLabels;
                sourceChartInstance.data.datasets[0].data = sourceData;
                sourceChartInstance.update();
            }

            const tagLabels = Object.keys(data.tags);
            const tagData = Object.values(data.tags);
            
            if (!tagChartInstance) {
                const ctxT = document.getElementById('tagChart').getContext('2d');
                tagChartInstance = new Chart(ctxT, {
                    type: 'bar',
                    data: {
                        labels: tagLabels,
                        datasets: [{ label: 'Occurrences', data: tagData, backgroundColor: '#3182CE', borderRadius: 4 }]
                    },
                    options: { ...chartOptions, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
                });
            } else {
                tagChartInstance.data.labels = tagLabels;
                tagChartInstance.data.datasets[0].data = tagData;
                tagChartInstance.update();
            }

            if (data.latencies) {
                const latLabels = data.latencies.map((_, i) => String(i+1));
                if (!latencyChartInstance) {
                    const ctxL = document.getElementById('latencyChart').getContext('2d');
                    latencyChartInstance = new Chart(ctxL, {
                        type: 'line',
                        data: {
                            labels: latLabels,
                            datasets: [{
                                label: 'Latency (ms)',
                                data: data.latencies,
                                borderColor: '#4FD1C5',
                                tension: 0.4,
                                fill: true,
                                backgroundColor: 'rgba(79, 209, 197, 0.1)'
                            }]
                        },
                        options: { ...chartOptions, plugins: { legend: { display: false } } }
                    });
                } else {
                    latencyChartInstance.data.labels = latLabels;
                    latencyChartInstance.data.datasets[0].data = data.latencies;
                    latencyChartInstance.update();
                }
            }
        } catch (error) {
            console.error("Dashboard poll failed", error);
        }
    }
});
