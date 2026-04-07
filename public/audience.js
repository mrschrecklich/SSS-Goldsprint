/**
 * SSS-Goldsprint Audience Controller v1.3
 * Handles high-performance animations, bracket logic with riding winners,
 * and champion visualizations.
 */

const UI = {
    targetDist: document.getElementById('targetDistValue'),
    countdown: {
        overlay: document.getElementById('countdownOverlay'),
        text: document.getElementById('countdownText')
    },
    win: {
        overlay: document.getElementById('winOverlay'),
        title: document.getElementById('winnerText'),
        p1: { name: document.getElementById('winnerName'), time: document.getElementById('winnerTime') },
        p2: { name: document.getElementById('secondName'), time: document.getElementById('secondTime') }
    },
    lanes: [
        {
            lane: document.getElementById('lane1'),
            name: document.querySelector('#lane1 .player-name'),
            rpm: document.getElementById('p1Rpm'),
            speed: document.getElementById('p1Speed'),
            progress: document.getElementById('p1Progress'),
            distLabel: document.getElementById('p1DistLabel')
        },
        {
            lane: document.getElementById('lane2'),
            name: document.querySelector('#lane2 .player-name'),
            rpm: document.getElementById('p2Rpm'),
            speed: document.getElementById('p2Speed'),
            progress: document.getElementById('p2Progress'),
            distLabel: document.getElementById('p2DistLabel')
        }
    ],
    bracket: {
        overlay: document.getElementById('bracketOverlay'),
        title: document.getElementById('bracketCategoryTitle'),
        container: document.getElementById('audienceBracketContainer'),
        svg: document.getElementById('bracketSvg'),
        statsBody: document.getElementById('audienceStatsBody')
    },
    champion: {
        overlay: document.getElementById('championOverlay'),
        name: document.getElementById('championName'),
        leaderboard: document.getElementById('leaderboardList')
    }
};

let ws;
let lastBracketData = null;
let isAnimating = false;

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onmessage = (e) => renderState(JSON.parse(e.data));
    ws.onclose = () => setTimeout(connect, 2000);
}

let lastFullStateStr = null;

function renderState(state) {
    // Quick optimization: only re-render if something changed
    const currentStateStr = JSON.stringify(state);
    if (currentStateStr === lastFullStateStr) return;
    lastFullStateStr = currentStateStr;

    UI.targetDist.textContent = Math.round(state.targetDist);

    const p1Name = state.bracketState?.active_match?.p1 || 'PLAYER 1';
    const p2Name = state.bracketState?.active_match?.p2 || 'PLAYER 2';
    
    UI.lanes[0].name.textContent = p1Name;
    UI.lanes[1].name.textContent = p2Name;

    handleCountdown(state.countdown);
    handleResults(state, p1Name, p2Name);

    updatePlayer(0, state.p1, state.targetDist);
    updatePlayer(1, state.p2, state.targetDist);

    if (state.bracketState) {
        handleBracket(state.bracketState);
    }
}

function handleCountdown(value) {
    if (value !== null) {
        if (value > 0) {
            UI.countdown.text.textContent = value;
            UI.countdown.text.classList.remove('goldsprint-text');
        } else {
            UI.countdown.text.textContent = 'GOLDSPRINT!';
            UI.countdown.text.classList.add('goldsprint-text');
        }
        UI.countdown.overlay.classList.remove('hidden');
    } else {
        UI.countdown.overlay.classList.add('hidden');
    }
}

function handleResults(state, p1Name, p2Name) {
    const isFinished = state.winner || (state.p1.finishTime && state.p2.finishTime);
    if (isFinished) {
        if (state.winner && state.winner.startsWith('FALSE START')) {
            UI.win.title.textContent = state.winner;
            UI.win.p1.name.textContent = 'RACE ABORTED';
            UI.win.p1.time.textContent = '';
            UI.win.p2.name.textContent = 'FALSE START';
            UI.win.p2.time.textContent = '';
        } else {
            const displayWinner = state.winner === 'Player 1' ? p1Name : p2Name;
            UI.win.title.textContent = `${displayWinner.toUpperCase()} WINS!`;
            const results = [
                { name: p1Name, time: state.p1.finishTime || 999.99 },
                { name: p2Name, time: state.p2.finishTime || 999.99 }
            ].sort((a, b) => a.time - b.time);
            UI.win.p1.name.textContent = results[0].name;
            UI.win.p1.time.textContent = results[0].time < 999 ? `${results[0].time.toFixed(2)}S` : 'DNF';
            UI.win.p2.name.textContent = results[1].name;
            UI.win.p2.time.textContent = results[1].time < 999 ? `${results[1].time.toFixed(2)}S` : 'DNF';
        }
        UI.win.overlay.classList.remove('hidden');
    } else {
        UI.win.overlay.classList.remove('hidden'); // Ensure hidden class is removed if active
        UI.win.overlay.classList.add('hidden');
    }
}

function updatePlayer(index, player, target) {
    const ui = UI.lanes[index];
    ui.rpm.textContent = player.rpm;
    ui.speed.textContent = player.speed.toFixed(1);
    ui.distLabel.textContent = `${Math.floor(player.dist)}M`;
    const pct = target > 0 ? Math.min(100, (player.dist / target) * 100) : 0;
    ui.progress.style.width = `${pct}%`;
    applyRpmEffects(ui, player.rpm);
}

function applyRpmEffects(ui, rpm) {
    const classes = ['shake-sluggish', 'shake-light', 'shake-medium', 'shake-heavy', 'shake-vibrant', 'shake-extreme', 'shake-max'];
    ui.lane.classList.remove(...classes);
    if (rpm >= 200) ui.lane.classList.add('shake-max');
    else if (rpm >= 180) ui.lane.classList.add('shake-extreme');
    else if (rpm >= 160) ui.lane.classList.add('shake-vibrant');
    else if (rpm >= 150) ui.lane.classList.add('shake-heavy');
    else if (rpm >= 120) ui.lane.classList.add('shake-medium');
    else if (rpm >= 100) ui.lane.classList.add('shake-light');
    else if (rpm >= 80) ui.lane.classList.add('shake-sluggish');
    if (rpm >= 150) ui.progress.classList.add('intense-glow');
    else ui.progress.classList.remove('intense-glow');
}

/**
 * Bracket Rendering & Animations
 */
function handleBracket(bracketState) {
    // 1. Determine which overlay to show
    const isChamp = bracketState.champion && bracketState.champion.category === bracketState.active_category;
    
    if (isChamp) {
        UI.bracket.overlay.classList.add('hidden');
        UI.champion.overlay.classList.remove('hidden');
    } else if (bracketState.show_bracket) {
        UI.bracket.overlay.classList.remove('hidden');
        UI.champion.overlay.classList.add('hidden');
    } else {
        UI.bracket.overlay.classList.add('hidden');
        UI.champion.overlay.classList.add('hidden');
        return;
    }

    const catData = bracketState.categories[bracketState.active_category];
    if (!catData) return;

    // 2. Handle Champion View Rendering
    if (isChamp) {
        UI.champion.name.textContent = bracketState.champion.name;
        UI.champion.leaderboard.innerHTML = '';
        (catData.top_times || []).forEach((entry, idx) => {
            const row = document.createElement('div');
            row.className = 'leader-row';
            row.innerHTML = `
                <span class="rank">#${idx + 1}</span>
                <span class="name">${entry.name}</span>
                <span class="time">${entry.time.toFixed(2)}s</span>
            `;
            UI.champion.leaderboard.appendChild(row);
        });
        return;
    }

    // 3. Normal Bracket View Rendering
    UI.bracket.title.textContent = `${catData.name} BRACKET`;

    // Check for advancement animations
    if (lastBracketData) {
        checkForAdvancement(lastBracketData, catData, bracketState);
    }
    lastBracketData = JSON.parse(JSON.stringify(catData));

    // Render Live Stats Sidebar
    if (UI.bracket.statsBody) {
        UI.bracket.statsBody.innerHTML = '';
        const participants = catData.participants || [];
        const uniqueParticipants = [...new Set(participants)];
        const bestsMap = bracketState.participants_bests || {};
        
        uniqueParticipants.forEach(name => {
            const bests = bestsMap[name] || { tournament: null, all_time: null };
            
            // Only show row if there is at least a tournament best for this specific distance
            if (!bests.tournament) return;

            const row = document.createElement('div');
            row.className = 'stats-row';
            row.innerHTML = `
                <div class="stats-name">${name}</div>
                <div class="stats-times">
                    <span class="time-label">TOURNAMENT:</span>
                    <span class="time-value">${parseFloat(bests.tournament).toFixed(2)}s</span>
                    <span class="time-label">BEST:</span>
                    <span class="time-value all-time">${bests.all_time ? parseFloat(bests.all_time).toFixed(2) + 's' : '-'}</span>
                </div>
            `;
            UI.bracket.statsBody.appendChild(row);
        });
    }

    if (!isAnimating) {
        renderBracketTree(catData, bracketState);
    }
}

function renderBracketTree(catData, bracketState) {
    UI.bracket.container.innerHTML = '';
    UI.bracket.svg.innerHTML = '';
    if (!catData.bracket || catData.bracket.length === 0) return;

    catData.bracket.forEach((round, rIdx) => {
        const roundDiv = document.createElement('div');
        roundDiv.className = 'aud-bracket-round';
        roundDiv.id = `round-${rIdx}`;
        
        round.forEach(match => {
            const matchDiv = document.createElement('div');
            matchDiv.className = 'aud-bracket-match';
            matchDiv.id = `match-${match.id}`;
            if (bracketState.active_match && bracketState.active_match.id === match.id) {
                matchDiv.classList.add('active-match');
            }

            const p1Loser = (match.winner && match.winner !== match.p1) ? 'loser' : '';
            const p2Loser = (match.winner && match.winner !== match.p2) ? 'loser' : '';
            const p1Winner = (match.winner === match.p1 && match.p1) ? 'winner' : '';
            const p2Winner = (match.winner === match.p2 && match.p2) ? 'winner' : '';

            matchDiv.innerHTML = `
                <div class="aud-bracket-slot slot-p1 ${p1Loser} ${p1Winner}">${match.p1 || '---'}</div>
                <div class="aud-bracket-slot slot-p2 ${p2Loser} ${p2Winner}">${match.p2 || '---'}</div>
            `;
            roundDiv.appendChild(matchDiv);
        });
        UI.bracket.container.appendChild(roundDiv);
    });

    // Draw lines after layout
    setTimeout(() => drawBracketLines(catData), 10);
}

function drawBracketLines(catData) {
    const svg = UI.bracket.svg;
    svg.innerHTML = '';
    const containerRect = UI.bracket.container.getBoundingClientRect();

    catData.bracket.forEach((round, rIdx) => {
        round.forEach(match => {
            if (!match.next_match_id) return;

            const matchEl = document.getElementById(`match-${match.id}`);
            const nextMatchEl = document.getElementById(`match-${match.next_match_id}`);
            if (!matchEl || !nextMatchEl) return;

            const mRect = matchEl.getBoundingClientRect();
            const nmRect = nextMatchEl.getBoundingClientRect();

            const x1 = mRect.right - containerRect.left;
            const y1 = mRect.top + mRect.height / 2 - containerRect.top;
            const x2 = nmRect.left - containerRect.left;
            
            // Find which slot in the next match we are feeding into
            const matchIndex = round.indexOf(match);
            const isUpper = matchIndex % 2 === 0;
            const slotOffset = isUpper ? nmRect.height * 0.25 : nmRect.height * 0.75;
            const y2 = nmRect.top + slotOffset - containerRect.top;

            const midX = x1 + (x2 - x1) / 2;

            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            const d = `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`;
            path.setAttribute("d", d);
            path.setAttribute("class", "bracket-line" + (match.winner ? " active" : ""));
            svg.appendChild(path);
        });
    });
}

function checkForAdvancement(oldCatData, newCatData, bracketState) {
    newCatData.bracket.forEach((round, rIdx) => {
        round.forEach((match, mIdx) => {
            const oldMatch = oldCatData.bracket[rIdx][mIdx];
            if (match.winner && match.winner !== 'BYE' && (!oldMatch || oldMatch.winner !== match.winner)) {
                // New winner confirmed!
                const isFinal = (rIdx === newCatData.bracket.length - 1);
                triggerRideAnimation(match, rIdx, isFinal, bracketState);
            }
        });
    });
}

function triggerRideAnimation(match, rIdx, isFinal, bracketState) {
    const startMatchEl = document.getElementById(`match-${match.id}`);
    if (!startMatchEl) return;

    isAnimating = true;
    const winnerName = match.winner;
    
    // Create floating tag
    const tag = document.createElement('div');
    tag.className = 'floating-tag';
    tag.textContent = winnerName;
    document.body.appendChild(tag);

    const startRect = startMatchEl.getBoundingClientRect();
    const startX = startRect.left + startRect.width / 2;
    const startY = startRect.top + startRect.height / 2;

    tag.style.left = `${startX}px`;
    tag.style.top = `${startY}px`;

    setTimeout(() => {
        let endX, endY;

        if (isFinal) {
            // Ride to center of screen for Champion Box
            endX = window.innerWidth / 2;
            endY = window.innerHeight / 2;
        } else {
            // Ride to next match slot
            const nextMatchEl = document.getElementById(`match-${match.next_match_id}`);
            if (nextMatchEl) {
                const nmRect = nextMatchEl.getBoundingClientRect();
                endX = nmRect.left + nmRect.width / 2;
                // Rough estimate of top/bottom slot
                const rData = lastBracketData.bracket[rIdx];
                const mIdxInRound = rData.findIndex(m => m.id === match.id);
                const isUpper = mIdxInRound % 2 === 0;
                endY = nmRect.top + (isUpper ? nmRect.height * 0.25 : nmRect.height * 0.75);
            } else {
                endX = startX; endY = startY;
            }
        }

        tag.style.transition = "all 1.5s cubic-bezier(0.45, 0, 0.55, 1)";
        tag.style.left = `${endX}px`;
        tag.style.top = `${endY}px`;
        if (isFinal) tag.style.transform = "translate(-50%, -50%) scale(3)";

        setTimeout(() => {
            tag.remove();
            isAnimating = false;
            // Full re-render to update the static bracket and show Champion Overlay if needed
            const catData = bracketState.categories[bracketState.active_category];
            renderBracketTree(catData, bracketState);
        }, 1600);
    }, 50);
}

// Initialization
connect();
