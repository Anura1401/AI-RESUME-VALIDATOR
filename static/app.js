// Global App State
let allResults = [];
let defaultData = null;

// DOM Elements
const form = document.getElementById('ranking-form');
const jobTitleInput = document.getElementById('job_title');
const jobDescInput = document.getElementById('job_description');
const qualificationsInput = document.getElementById('qualifications');
const runBtn = document.getElementById('run-btn');

const sourceRadios = document.querySelectorAll('input[name="candidate_source"]');
const jsonUploadGroup = document.getElementById('json-upload-group');
const resumesUploadGroup = document.getElementById('resumes-upload-group');

const jsonDropzone = document.getElementById('json-dropzone');
const jsonFileField = document.getElementById('candidates_file');
const jsonFileNameDisplay = document.getElementById('json-file-name');

const resumesDropzone = document.getElementById('resumes-dropzone');
const resumesFileField = document.getElementById('resumes');
const resumesCountDisplay = document.getElementById('resumes-files-count');

const logSection = document.getElementById('log-section');
const logBox = document.getElementById('log-box');
const logPulse = document.getElementById('log-pulse');

const resultsPanel = document.getElementById('results-panel');
const candidatesContainer = document.getElementById('candidates-container');
const searchInput = document.getElementById('candidate-search');
const scoreRange = document.getElementById('score-range');
const scoreVal = document.getElementById('score-val');

const statTotal = document.getElementById('stat-total');
const statTop = document.getElementById('stat-top');
const statAvg = document.getElementById('stat-avg');

const exportExcelBtn = document.getElementById('export-excel-btn');
const exportCsvBtn = document.getElementById('export-csv-btn');
const exportJsonBtn = document.getElementById('export-json-btn');

// Detailed Modal Elements
const detailModal = document.getElementById('detail-modal');
const modalCandidateId = document.getElementById('modal-candidate-id');
const modalTitle = document.getElementById('modal-title');
const modalScore = document.getElementById('modal-score');
const modalReasoningDesc = document.getElementById('modal-reasoning-desc');
const modalResumeContent = document.getElementById('modal-resume-content');
const closeModalBtn = document.getElementById('close-modal-btn');

// Initialize App
window.addEventListener('DOMContentLoaded', () => {
    fetchDefaults();
    setupEventListeners();
});

// Event Listeners Setup
function setupEventListeners() {
    // Toggle Candidate Source UI
    sourceRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'defaults') {
                jsonUploadGroup.classList.add('hidden');
                resumesUploadGroup.classList.add('hidden');
            } else if (val === 'custom_json') {
                jsonUploadGroup.classList.remove('hidden');
                resumesUploadGroup.classList.add('hidden');
            } else if (val === 'resumes') {
                jsonUploadGroup.classList.add('hidden');
                resumesUploadGroup.classList.remove('hidden');
            }
        });
    });

    // File Input Display Changes
    jsonFileField.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            jsonFileNameDisplay.textContent = `Selected: ${e.target.files[0].name}`;
        } else {
            jsonFileNameDisplay.textContent = '';
        }
    });

    resumesFileField.addEventListener('change', (e) => {
        const count = e.target.files.length;
        if (count > 0) {
            resumesCountDisplay.textContent = `Selected: ${count} resume file(s)`;
        } else {
            resumesCountDisplay.textContent = '';
        }
    });

    // Drag and Drop Effects
    [jsonDropzone, resumesDropzone].forEach(dropzone => {
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                if (dropzone === jsonDropzone) {
                    // Limit to exactly 1 file for JSON/JSONL candidates database
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(files[0]);
                    jsonFileField.files = dataTransfer.files;
                    // Trigger change event to update label
                    jsonFileField.dispatchEvent(new Event('change'));
                } else if (dropzone === resumesDropzone) {
                    // Raw resumes can accept multiple files
                    resumesFileField.files = files;
                    resumesFileField.dispatchEvent(new Event('change'));
                }
            }
        });
    });

    // Search and Filter Listeners
    searchInput.addEventListener('input', filterAndRender);
    scoreRange.addEventListener('input', (e) => {
        scoreVal.textContent = `${e.target.value}%`;
        filterAndRender();
    });

    // Modal Close Trigger
    closeModalBtn.addEventListener('click', () => {
        detailModal.classList.add('hidden');
    });
    detailModal.addEventListener('click', (e) => {
        if (e.target === detailModal) {
            detailModal.classList.add('hidden');
        }
    });

    // Form Submit Rank
    form.addEventListener('submit', runRankingPipeline);

    // Export Triggers
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', exportExcel);
    }
    exportCsvBtn.addEventListener('click', exportCSV);
    exportJsonBtn.addEventListener('click', exportJSON);
}

// Fetch Default data on page load
function fetchDefaults() {
    appendLog('System initialized. Fetching default settings...', 'system');
    fetch('/api/defaults')
        .then(res => res.json())
        .then(data => {
            defaultData = data;
            jobTitleInput.value = data.job_title || '';
            jobDescInput.value = data.job_description || '';
            qualificationsInput.value = data.qualifications || '';
            
            appendLog(`Loaded Default Job Title: "${data.job_title}"`, 'success');
            appendLog(`Default candidates database contains ${data.default_candidates_count} records. Ready to rank.`, 'success');
        })
        .catch(err => {
            appendLog(`Failed to fetch default settings: ${err.message}`, 'error');
        });
}

// Logger helpers
function clearLogs() {
    logBox.innerHTML = '';
}

function appendLog(message, type = 'system') {
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    // Timestamp
    const time = new Date().toLocaleTimeString();
    line.innerHTML = `[${time}] ${message}`;
    logBox.appendChild(line);
    logBox.scrollTop = logBox.scrollHeight;
}

// Main Runner
async function runRankingPipeline(e) {
    e.preventDefault();
    
    // UI Loading state
    runBtn.disabled = true;
    runBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Pipeline...';
    logPulse.classList.remove('hidden');
    clearLogs();
    appendLog("Initiating Job Validator ranking sequence...", "system");

    const source = document.querySelector('input[name="candidate_source"]:checked').value;
    const formData = new FormData();
    formData.append('job_title', jobTitleInput.value);
    formData.append('job_description', jobDescInput.value);
    formData.append('qualifications', qualificationsInput.value);

    // Construct Payload
    if (source === 'defaults') {
        formData.append('use_defaults', 'true');
        appendLog("Source set to use default mock candidates database (650 profiles).", "system");
    } else if (source === 'custom_json') {
        formData.append('use_defaults', 'false');
        if (jsonFileField.files.length === 0) {
            appendLog("Error: No JSON/JSONL database file uploaded.", "error");
            resetRunButton();
            return;
        }
        formData.append('candidates_file', jsonFileField.files[0]);
        appendLog(`Source set to custom database: ${jsonFileField.files[0].name}`, "system");
    } else if (source === 'resumes') {
        formData.append('use_defaults', 'false');
        if (resumesFileField.files.length === 0) {
            appendLog("Error: No resume files uploaded.", "error");
            resetRunButton();
            return;
        }
        const files = resumesFileField.files;
        for (let i = 0; i < files.length; i++) {
            formData.append('resumes', files[i]);
        }
        appendLog(`Source set to ${files.length} uploaded raw resume(s).`, "system");
    }

    // Set up simulated console logs for smooth UI feedback while pipeline runs in background
    let logIntervals = [];
    const simulateLog = (text, type, delay) => {
        const id = setTimeout(() => appendLog(text, type), delay);
        logIntervals.push(id);
    };

    simulateLog("Stage 1/3: Reading inputs & initializing candidate search engine...", "running", 800);
    simulateLog("Loading deep semantic mapping models...", "running", 2500);
    simulateLog("Analyzing profile structures and mapping candidate context...", "running", 5000);
    simulateLog("Analyzing keyword distributions across resumes...", "running", 10000);
    
    if (source === 'defaults') {
        simulateLog("Synthesizing career profiles...", "running", 12000);
        simulateLog("Blending semantic alignment with keyword match indexes...", "running", 16000);
        simulateLog("Stage 2/3: Activating high-precision semantic validator...", "running", 20000);
        simulateLog("Running validation scoring to rank candidates...", "running", 24000);
    } else {
        simulateLog("Blending semantic alignment with keyword match indexes...", "running", 11000);
        simulateLog("Stage 2/3: Activating high-precision semantic validator...", "running", 14000);
        simulateLog("Running validation scoring...", "running", 17000);
    }
    
    simulateLog("Stage 3/3: Performing final scoring calibration and calculations...", "running", 30000);

    try {
        const response = await fetch('/api/rank', {
            method: 'POST',
            body: formData
        });
        
        // Cancel logs simulation since actual response returned
        logIntervals.forEach(clearTimeout);

        const data = await response.json();
        
        if (data.success) {
            allResults = data.results;
            appendLog(`Success! Ranked ${allResults.length} candidates in total.`, "success");
            
            // Calculate stats
            renderStats(allResults);
            
            // Show Panel
            resultsPanel.classList.remove('hidden');
            
            // Render Cards
            filterAndRender();
        } else {
            appendLog(`Engine Error: ${data.error}`, "error");
        }
    } catch (err) {
        logIntervals.forEach(clearTimeout);
        appendLog(`Network or execution failure: ${err.message}`, "error");
    } finally {
        resetRunButton();
    }
}

function resetRunButton() {
    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Resume Ranking Pipeline';
    logPulse.classList.add('hidden');
}

// Compute Statistics on client side
function renderStats(results) {
    statTotal.textContent = results.length;
    if (results.length > 0) {
        const topScore = Math.max(...results.map(r => r.final_score));
        const avgScore = results.reduce((acc, r) => acc + r.final_score, 0) / results.length;
        
        statTop.textContent = `${(topScore * 100).toFixed(1)}%`;
        statAvg.textContent = `${(avgScore * 100).toFixed(1)}%`;
    } else {
        statTop.textContent = '-';
        statAvg.textContent = '-';
    }
}

// Filters & Renders Results
function filterAndRender() {
    const query = searchInput.value.toLowerCase().trim();
    const minScore = parseFloat(scoreRange.value) / 100;
    
    const filtered = allResults.filter(c => {
        // Score filter
        if (c.final_score < minScore) return false;
        
        // Search query match
        if (query) {
            const idMatch = c.candidate_id.toLowerCase().includes(query);
            const titleMatch = c.current_title.toLowerCase().includes(query);
            const reasonMatch = c.reasoning.toLowerCase().includes(query);
            const skillsMatch = c.skills.some(s => s.toLowerCase().includes(query));
            
            // experience timeline check
            const expMatch = c.experience.some(exp => 
                exp.title.toLowerCase().includes(query) || 
                exp.company_name.toLowerCase().includes(query) || 
                exp.description.toLowerCase().includes(query)
            );
            
            const narrativeMatch = c.narrative && c.narrative.toLowerCase().includes(query);
            
            return idMatch || titleMatch || reasonMatch || skillsMatch || expMatch || narrativeMatch;
        }
        
        return true;
    });

    candidatesContainer.innerHTML = '';
    
    if (filtered.length === 0) {
        candidatesContainer.innerHTML = '<div class="no-results">No candidate match criteria. Adjust filters or search keywords.</div>';
        return;
    }

    filtered.forEach((c, idx) => {
        const rank = idx + 1;
        const scorePercentage = (c.final_score * 100).toFixed(1);
        
        // Rank Class
        let rankClass = '';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';

        // Skills tags template
        let skillsHtml = '';
        if (c.skills && c.skills.length > 0) {
            // slice top 6 skills
            skillsHtml = `<div class="skills-tags">` + 
                c.skills.slice(0, 6).map(s => `<span class="skill-tag">${s}</span>`).join('') + 
                (c.skills.length > 6 ? `<span class="skill-tag">+${c.skills.length - 6} more</span>` : '') + 
                `</div>`;
        }

        const card = document.createElement('div');
        card.className = 'candidate-card';
        card.innerHTML = `
            <div class="rank-badge ${rankClass}">${rank}</div>
            <div class="profile-info">
                <h5>${c.candidate_id}</h5>
                <span class="title">${c.current_title || 'Parsed Profile'}</span>
                ${skillsHtml}
            </div>
            <div class="score-container">
                <span class="score-display">${scorePercentage}%</span>
                <div class="score-progress-wrapper">
                    <div class="score-progress-bar" style="width: ${scorePercentage}%"></div>
                </div>
            </div>
            <div class="arrow-icon"><i class="fa-solid fa-chevron-right"></i></div>
        `;
        
        card.addEventListener('click', () => showCandidateModal(c, rank));
        candidatesContainer.appendChild(card);
    });
}

// Show Detailed overlay candidate
function showCandidateModal(c, rank) {
    modalCandidateId.innerHTML = `Rank #${rank}: ${c.candidate_id}`;
    modalTitle.textContent = c.current_title || 'Parsed Candidate Profile';
    modalScore.textContent = `${(c.final_score * 100).toFixed(1)}%`;
    
    // Parse reasoning strings into highlights
    modalReasoningDesc.innerHTML = '';
    const reasons = c.reasoning.split('. ');
    reasons.forEach(r => {
        if (!r.trim()) return;
        
        let icon = '<i class="fa-solid fa-circle-info"></i>';
        let className = 'info';
        
        if (r.includes('Penalty') || r.includes('0.2x') || r.includes('0.1x')) {
            icon = '<i class="fa-solid fa-circle-exclamation"></i>';
            className = 'penalty';
        } else if (r.includes('Bonus') || r.includes('matched') || r.includes('1.2x') || r.includes('1.0x')) {
            icon = '<i class="fa-solid fa-circle-check"></i>';
            className = 'match';
        }
        
        const row = document.createElement('div');
        row.className = `reasoning-item ${className}`;
        row.innerHTML = `${icon} <span>${r}</span>`;
        modalReasoningDesc.appendChild(row);
    });

    // Load experiences or raw resume content
    modalResumeContent.innerHTML = '';
    if (c.experience && c.experience.length > 0) {
        // Structured profile
        c.experience.forEach(exp => {
            const expDiv = document.createElement('div');
            expDiv.style.marginBottom = '16px';
            expDiv.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
            expDiv.style.paddingBottom = '12px';
            expDiv.innerHTML = `
                <div style="font-weight: 600; color: var(--text-main); font-size: 14px;">
                    ${exp.title} at <span style="color: var(--secondary);">${exp.company_name}</span> 
                    ${exp.company_type ? `(${exp.company_type} company)` : ''}
                </div>
                <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 6px; white-space: pre-wrap;">
                    ${exp.description}
                </div>
            `;
            modalResumeContent.appendChild(expDiv);
        });
    } else {
        // Raw resume text
        modalResumeContent.textContent = c.narrative || 'No additional resume text found.';
    }

    detailModal.classList.remove('hidden');
}

// Download exports
function exportExcel() {
    if (allResults.length === 0) return;
    
    // Create an Excel-compatible HTML format with spreadsheet styling schemas
    let html = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <!--[if gte mso 9]>
            <xml>
                <x:ExcelWorkbook>
                    <x:ExcelWorksheets>
                        <x:ExcelWorksheet>
                            <x:Name>Ranked Candidates</x:Name>
                            <x:WorksheetOptions>
                                <x:DisplayGridlines/>
                            </x:WorksheetOptions>
                        </x:ExcelWorksheet>
                    </x:ExcelWorksheets>
                </x:ExcelWorkbook>
            </xml>
            <![endif]-->
            <meta charset="utf-8">
            <style>
                table { border-collapse: collapse; }
                th, td { border: 1px solid #ddd; padding: 8px; font-family: sans-serif; font-size: 10pt; }
                th { background-color: #f2f2f2; font-weight: bold; }
                .score-col { text-align: right; }
                .rank-col { text-align: center; }
            </style>
        </head>
        <body>
            <table>
                <thead>
                    <tr>
                        <th>Candidate ID</th>
                        <th>Rank</th>
                        <th>Score</th>
                        <th>Reasoning</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    allResults.forEach((c, idx) => {
        const rank = idx + 1;
        const score = (c.final_score * 100).toFixed(2) + "%";
        // Escape special XML/HTML entities
        const escapeXml = text => text.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
        const cid = escapeXml(c.candidate_id);
        const reasoning = escapeXml(c.reasoning);
        
        html += `
            <tr>
                <td>${cid}</td>
                <td class="rank-col">${rank}</td>
                <td class="score-col">${score}</td>
                <td>${reasoning}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </body>
        </html>
    `;
    
    const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ranked_candidates.xls");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function exportCSV() {
    if (allResults.length === 0) return;
    
    let csvContent = "candidate_id,rank,score,reasoning\r\n";
    
    allResults.forEach((c, idx) => {
        const rank = idx + 1;
        const score = c.final_score.toFixed(6);
        const reasoningEscaped = `"${c.reasoning.replace(/"/g, '""')}"`;
        const cidEscaped = `"${c.candidate_id.replace(/"/g, '""')}"`;
        
        csvContent += `${cidEscaped},${rank},${score},${reasoningEscaped}\r\n`;
    });
    
    // Prepend UTF-8 BOM (\ufeff) to make it fully readable in Excel
    const blob = new Blob(["\ufeff" + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ranked_candidates.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function exportJSON() {
    if (allResults.length === 0) return;
    
    const jsonString = JSON.stringify(allResults, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "ranked_candidates.json");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}
