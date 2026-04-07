/**
 * SSS-Goldsprint Admin Controller v1.4
 * Manages race lifecycle, configuration, monitoring, and statistics.
 */

const UI = {
    statusBar: document.getElementById('status-bar'),
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    resetBtn: document.getElementById('resetBtn'),
    ackWinnerBtn: document.getElementById('ackWinnerBtn'),
    ackChampBtn: document.getElementById('ackChampBtn'),
    applyConfigBtn: document.getElementById('applyConfigBtn'),
    inputs: {
        dist: document.getElementById('inputDist'),
        circ: document.getElementById('inputCirc'),
        fs: document.getElementById('inputFS')
    },
    monitors: {
        p1NameInput: document.getElementById('p1NameInput'),
        p2NameInput: document.getElementById('p2NameInput'),
        p1Rpm: document.getElementById('p1Rpm'),
        p1Dist: document.getElementById('p1Dist'),
        p2Rpm: document.getElementById('p2Rpm'),
        p2Dist: document.getElementById('p2Dist')
    },
    bracket: {
        toggle: document.getElementById('showBracketToggle'),
        addParticipantBtn: document.getElementById('addParticipantBtn'),
        newParticipantName: document.getElementById('newParticipantName'),
        participantList: document.getElementById('participantList'),
        randomizeBtn: document.getElementById('randomizeBtn'),
        container: document.getElementById('bracketContainer'),
        nameSuggestions: document.getElementById('name-suggestions')
    }
};

// --- Autocomplete logic ---
UI.bracket.newParticipantName.addEventListener('input', async (e) => {
    const query = e.target.value;
    if (query.length < 2) {
        UI.bracket.nameSuggestions.innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`);
        const names = await response.json();
        
        UI.bracket.nameSuggestions.innerHTML = names
            .map(name => `<option value="${name}">`)
            .join('');
    } catch (err) {
        console.error("Failed to fetch suggestions:", err);
    }
});

let ws;
let isFirstLoad = true;
let currentState = null;
let activeCategory = 'OPEN';

window.switchTab = (tabId) => {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    const btn = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
    if (btn) btn.classList.add('active');
    document.getElementById(`${tabId}-tab`).classList.add('active');
};

window.setActiveCategory = (cat) => {
    if (currentState && currentState.bracketState && currentState.bracketState.active_match) {
        const activeMatchCat = currentState.bracketState.active_match.category;
        if (cat !== activeMatchCat) {
            if (!confirm(`Switching to ${cat}? The active race is set for ${activeMatchCat}. This will update the audience view to ${cat}.`)) {
                return;
            }
        }
    }

    activeCategory = cat;
    sendCommand('SET_ACTIVE_CATEGORY', { category: cat });
};

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onopen = () => updateUIStatus('Connected & Ready', 'ready');
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'ERROR') {
            alert(`⚠️ Error: ${msg.message}`);
            return;
        }
        currentState = msg;
        renderState(currentState);
    };
    ws.onclose = () => {
        updateUIStatus('Disconnected. Retrying...', 'warning');
        setTimeout(connect, 2000);
    };
}

function updateUIStatus(text, type) {
    UI.statusBar.textContent = text;
    UI.statusBar.className = `status ${type}`;
}

const sendCommand = (type, payload = {}) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, ...payload }));
    }
};

// --- Render Loop ---
function renderState(state) {
    const isFinished = state.winner || (state.p1.finishTime && state.p2.finishTime);
    const hasChampion = state.bracketState && state.bracketState.champion;
    
    if (isFinished) {
        updateUIStatus(state.winner || 'Finished', 'stop');
        UI.ackWinnerBtn.style.display = hasChampion ? 'none' : 'block';
        UI.ackChampBtn.style.display = hasChampion ? 'block' : 'none';
    } else if (state.countdown !== null) {
        updateUIStatus(`COUNTDOWN: ${state.countdown > 0 ? state.countdown : 'GO!'}`, 'racing');
        UI.ackWinnerBtn.style.display = 'none';
        UI.ackChampBtn.style.display = 'none';
    } else if (state.isRacing) {
        updateUIStatus('RACING', 'racing');
        UI.ackWinnerBtn.style.display = 'none';
        UI.ackChampBtn.style.display = 'none';
    } else {
        if (hasChampion) {
            updateUIStatus('TOURNAMENT CHAMPION!', 'ready');
            UI.ackChampBtn.style.display = 'block';
            UI.ackWinnerBtn.style.display = 'none';
        } else {
            updateUIStatus('Ready to Race', 'ready');
            UI.ackWinnerBtn.style.display = 'none';
            UI.ackChampBtn.style.display = 'none';
        }
    }

    UI.monitors.p1Rpm.textContent = state.p1.rpm;
    UI.monitors.p2Rpm.textContent = state.p2.rpm;
    UI.monitors.p1Dist.textContent = state.p1.dist.toFixed(1);
    UI.monitors.p2Dist.textContent = state.p2.dist.toFixed(1);

    if (isFirstLoad) {
        UI.inputs.dist.value = state.targetDist;
        UI.inputs.circ.value = state.circumference;
        UI.inputs.fs.value = state.falseStartThreshold;
        isFirstLoad = false;
    }
    
    // Sync active match names if any
    if (state.bracketState && state.bracketState.active_match) {
        UI.monitors.p1NameInput.value = state.bracketState.active_match.p1 || 'Player 1';
        UI.monitors.p2NameInput.value = state.bracketState.active_match.p2 || 'Player 2';
    } else if (!state.isRacing && state.countdown === null) {
        // Only clear if not in an active manual race
        UI.monitors.p1NameInput.value = 'Player 1';
        UI.monitors.p2NameInput.value = 'Player 2';
    }

    if (state.bracketState) {
        if (state.bracketState.active_category) {
            activeCategory = state.bracketState.active_category;
            document.querySelectorAll('.cat-btn').forEach(btn => {
                btn.classList.toggle('active', btn.innerText === activeCategory);
            });
        }
        
        renderBracketUI(state.bracketState);
        UI.bracket.toggle.checked = state.bracketState.show_bracket;
        UI.bracket.toggle.disabled = state.isRacing;
    }
}

// --- Bracket UI Logic ---
function renderBracketUI(bracketState) {
    const catData = bracketState.categories[activeCategory];
    if (!catData) return;

    // Render Participant List
    UI.bracket.participantList.innerHTML = '';
    const participants = catData.participants || [];
    participants.forEach(p => {
        const chip = document.createElement('div');
        chip.className = 'participant-chip';
        chip.innerHTML = `<span>${p}</span> <button onclick="removeParticipant('${p}')">&times;</button>`;
        UI.bracket.participantList.appendChild(chip);
    });

    // Render Bracket Tree
    UI.bracket.container.innerHTML = '';
    if (!catData.bracket || catData.bracket.length === 0) {
        UI.bracket.container.innerHTML = '<p style="color:#aaa;">No bracket generated yet.</p>';
        return;
    }

    catData.bracket.forEach((round, rIndex) => {
        const roundDiv = document.createElement('div');
        roundDiv.className = 'bracket-round';
        
        round.forEach(match => {
            const matchDiv = document.createElement('div');
            matchDiv.className = 'bracket-match';
            if (bracketState.active_match && bracketState.active_match.id === match.id) {
                matchDiv.classList.add('active');
            }

            matchDiv.innerHTML = `
                <div style="font-size:0.8rem; color:#888;">Match ${match.id.substring(0,4)}</div>
                <div class="bracket-slot ${match.winner === match.p1 && match.p1 ? 'winner' : ''}" 
                     draggable="${match.p1 && match.p1 !== 'BYE'}" 
                     ondragstart="dragStart(event, '${match.id}', 1, '${match.p1}')"
                     ondragover="allowDrop(event)"
                     ondrop="drop(event, '${match.id}', 1)"
                     ondragleave="dragLeave(event)">
                    ${match.p1 || 'TBD'}
                    ${match.winner === match.p1 && match.p1 ? '<span>★</span>' : ''}
                </div>
                <div class="bracket-slot ${match.winner === match.p2 && match.p2 ? 'winner' : ''}" 
                     draggable="${match.p2 && match.p2 !== 'BYE'}" 
                     ondragstart="dragStart(event, '${match.id}', 2, '${match.p2}')"
                     ondragover="allowDrop(event)"
                     ondrop="drop(event, '${match.id}', 2)"
                     ondragleave="dragLeave(event)">
                    ${match.p2 || 'TBD'}
                    ${match.winner === match.p2 && match.p2 ? '<span>★</span>' : ''}
                </div>
                ${!match.winner && match.p1 && match.p2 && match.p1 !== 'BYE' && match.p2 !== 'BYE' ? 
                    `<button class="set-active-btn" onclick="setActiveMatch('${match.id}', '${match.p1}', '${match.p2}')">Set Active</button>` : ''}
            `;
            roundDiv.appendChild(matchDiv);
        });
        UI.bracket.container.appendChild(roundDiv);
    });
}

// --- Drag and Drop Logic ---
let draggedData = null;

window.dragStart = (e, matchId, pIdx, name) => {
    draggedData = { matchId, pIdx, name };
    e.dataTransfer.effectAllowed = "move";
};

window.allowDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
};

window.dragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over');
};

window.drop = (e, targetMatchId, targetPIdx) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    if (!draggedData) return;

    const catData = currentState.bracketState.categories[activeCategory];
    const bracket = catData.bracket;
    
    let sourceRoundIdx = -1;
    let targetRoundIdx = -1;
    let sourceMatch = null;
    
    bracket.forEach((round, rIdx) => {
        round.forEach(m => {
            if (m.id === draggedData.matchId) { sourceRoundIdx = rIdx; sourceMatch = m; }
            if (m.id === targetMatchId) { targetRoundIdx = rIdx; }
        });
    });

    // 1. ADVANCE Logic: If target match is the direct successor of source match
    if (targetMatchId === sourceMatch.next_match_id) {
        if (confirm(`Manually advance ${draggedData.name} to the next round?`)) {
            sendCommand('MANUAL_ADVANCE', {
                category: activeCategory,
                match_id: draggedData.matchId,
                winner: draggedData.name
            });
        }
    } 
    // 2. CHAMPION Logic: If dragging from the final match (declaring winner)
    else if (sourceRoundIdx === bracket.length - 1 && draggedData.matchId === targetMatchId) {
        if (confirm(`Confirm ${draggedData.name} as the final TOURNAMENT WINNER?`)) {
            sendCommand('MANUAL_ADVANCE', {
                category: activeCategory,
                match_id: draggedData.matchId,
                winner: draggedData.name
            });
        }
    }
    // 3. SWAP Logic: If dropped in the same round (e.g., seeding changes)
    else if (sourceRoundIdx === targetRoundIdx) {
        sendCommand('SWAP_PARTICIPANTS', {
            category: activeCategory,
            match1_id: draggedData.matchId,
            p1_idx: draggedData.pIdx,
            match2_id: targetMatchId,
            p2_idx: targetPIdx
        });
    }
    
    draggedData = null;
};

// --- Bracket Commands ---
UI.bracket.addParticipantBtn.addEventListener('click', () => {
    const name = UI.bracket.newParticipantName.value.trim();
    if (!name) {
        alert("Please enter a name.");
        return;
    }
    
    let exists = false;
    for (const cat in currentState.bracketState.categories) {
        if (currentState.bracketState.categories[cat].participants.includes(name)) {
            alert(`⚠️ Error: '${name}' is already registered in ${cat} category.`);
            exists = true;
            break;
        }
    }
    
    if (!exists) {
        sendCommand('ADD_PARTICIPANT', { category: activeCategory, name });
        UI.bracket.newParticipantName.value = '';
    }
});

window.removeParticipant = (name) => {
    sendCommand('REMOVE_PARTICIPANT', { category: activeCategory, name });
};

UI.bracket.randomizeBtn.addEventListener('click', () => {
    if (confirm('Are you sure? This will overwrite the current bracket for this category.')) {
        sendCommand('GENERATE_BRACKET', { category: activeCategory });
    }
});

UI.bracket.toggle.addEventListener('change', (e) => {
    sendCommand('TOGGLE_BRACKET_VIEW', { show: e.target.checked });
});

window.setActiveMatch = (matchId, p1, p2) => {
    sendCommand('SET_ACTIVE_MATCH', { match: { id: matchId, category: activeCategory, p1, p2 } });
    UI.monitors.p1NameInput.value = p1;
    UI.monitors.p2NameInput.value = p2;
    switchTab('race');
};

// --- Race Commands ---
UI.startBtn.addEventListener('click', () => sendCommand('START'));
UI.stopBtn.addEventListener('click', () => sendCommand('STOP'));
UI.resetBtn.addEventListener('click', () => {
    if (confirm('Full Reset: Clear all distances and stop race?')) sendCommand('RESET');
});

UI.applyConfigBtn.addEventListener('click', () => {
    const dist = parseFloat(UI.inputs.dist.value);
    const circ = parseFloat(UI.inputs.circ.value);
    const fs = parseFloat(UI.inputs.fs.value);

    if (isNaN(dist) || dist <= 0) { alert("Distance must be a positive number."); return; }
    if (isNaN(circ) || circ <= 0) { alert("Circumference must be a positive number."); return; }
    if (isNaN(fs) || fs < 1) { alert("False start threshold must be at least 1 RPM."); return; }

    sendCommand('CONFIG', {
        dist: dist,
        circ: circ,
        fsThreshold: fs
    });
    const originalText = UI.applyConfigBtn.textContent;
    UI.applyConfigBtn.textContent = 'CONFIG APPLIED!';
    UI.applyConfigBtn.style.backgroundColor = '#2196F3';
    setTimeout(() => {
        UI.applyConfigBtn.textContent = originalText;
        UI.applyConfigBtn.style.backgroundColor = '';
    }, 1500);
});

UI.ackWinnerBtn.addEventListener('click', () => {
    if (!currentState || !currentState.bracketState || !currentState.bracketState.active_match) {
        alert("No active match assigned! Cannot advance winner automatically.");
        return;
    }
    
    let winnerName = null;
    let winnerTime = null;
    const match = currentState.bracketState.active_match;
    if (currentState.winner === 'Player 1') {
        winnerName = match.p1;
        winnerTime = currentState.p1.finishTime;
    } else if (currentState.winner === 'Player 2') {
        winnerName = match.p2;
        winnerTime = currentState.p2.finishTime;
    }
    
    if (winnerName) {
        sendCommand('ADVANCE_WINNER', {
            category: match.category,
            match_id: match.id,
            winner: winnerName,
            time: winnerTime
        });
    } else {
        alert("Race ended in false start or error, cannot advance winner.");
    }
});

UI.ackChampBtn.addEventListener('click', () => {
    sendCommand('ACK_CHAMPION');
    switchTab('bracket');
});

connect();
