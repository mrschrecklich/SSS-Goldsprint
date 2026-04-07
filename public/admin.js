/**
 * SSS-Goldsprint Admin Controller v1.2
 * Manages race lifecycle, configuration, and monitoring.
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
        container: document.getElementById('bracketContainer')
    }
};

let ws;
let isFirstLoad = true;
let currentState = null;
let activeCategory = 'OPEN';

window.switchTab = (tabId) => {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.querySelector(`button[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(`${tabId}-tab`).classList.add('active');
};

window.setActiveCategory = (cat) => {
    // If there's an active match and we are switching to a DIFFERENT category, ask for confirmation
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
    
    // UI update will happen via renderState from the server broadcast
};

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onopen = () => updateUIStatus('Connected & Ready', 'ready');
    ws.onmessage = (event) => {
        currentState = JSON.parse(event.data);
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
    // 1. Handle Status & Race Mode
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
        // Special case: we are in bracket view but champion is shown
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

    // 2. Update Monitors
    UI.monitors.p1Rpm.textContent = state.p1.rpm;
    UI.monitors.p2Rpm.textContent = state.p2.rpm;
    UI.monitors.p1Dist.textContent = state.p1.dist.toFixed(1);
    UI.monitors.p2Dist.textContent = state.p2.dist.toFixed(1);

    // 3. Initial Configuration Sync
    if (isFirstLoad) {
        UI.inputs.dist.value = state.targetDist;
        UI.inputs.circ.value = state.circumference;
        UI.inputs.fs.value = state.falseStartThreshold;
        
        // Sync active match if any
        if (state.bracketState && state.bracketState.active_match) {
            UI.monitors.p1NameInput.value = state.bracketState.active_match.p1 || 'Player 1';
            UI.monitors.p2NameInput.value = state.bracketState.active_match.p2 || 'Player 2';
        }
        
        isFirstLoad = false;
    }

    // 4. Update Bracket UI
    if (state.bracketState) {
        // Sync the admin's activeCategory to the server's authoritative one
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
    catData.participants.forEach(p => {
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
                     draggable="${rIndex === 0 && match.p1 && match.p1 !== 'BYE'}" 
                     ondragstart="dragStart(event, '${match.id}', 1)"
                     ondragover="allowDrop(event)"
                     ondrop="drop(event, '${match.id}', 1)"
                     ondragleave="dragLeave(event)">
                    ${match.p1 || 'TBD'}
                    ${match.winner === match.p1 && match.p1 ? '<span>★</span>' : ''}
                </div>
                <div class="bracket-slot ${match.winner === match.p2 && match.p2 ? 'winner' : ''}" 
                     draggable="${rIndex === 0 && match.p2 && match.p2 !== 'BYE'}" 
                     ondragstart="dragStart(event, '${match.id}', 2)"
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

window.dragStart = (e, matchId, pIdx) => {
    draggedData = { matchId, pIdx };
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
    
    // Send swap command to server
    sendCommand('SWAP_PARTICIPANTS', {
        category: activeCategory,
        match1_id: draggedData.matchId,
        p1_idx: draggedData.pIdx,
        match2_id: targetMatchId,
        p2_idx: targetPIdx
    });
    draggedData = null;
};

// --- Bracket Commands ---
UI.bracket.addParticipantBtn.addEventListener('click', () => {
    const name = UI.bracket.newParticipantName.value;
    if (name) {
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
    sendCommand('CONFIG', {
        dist: parseFloat(UI.inputs.dist.value),
        circ: parseFloat(UI.inputs.circ.value),
        fsThreshold: parseFloat(UI.inputs.fs.value)
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
    
    // Determine winner name and time
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

// Initialization
connect();
