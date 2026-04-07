/**
 * SSS-Goldsprint Audience Controller v1.4
 * Handles high-performance animations, auto-cycling brackets, and auto-centering.
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
        wrapper: document.querySelector('.bracket-wrapper'),
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
let displayedCategory = null;
let categoryCycleInterval = null;
let latestBracketState = null;

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onmessage = (e) => renderState(JSON.parse(e.data));
    ws.onclose = () => setTimeout(connect, 2000);
}

let lastBracketHash = null;

function renderState(state) {
    // 1. High-frequency updates
    if (UI.targetDist) UI.targetDist.textContent = state.targetDist;
    updatePlayer(0, state.p1, state.targetDist);
    updatePlayer(1, state.p2, state.targetDist);
    handleCountdown(state.countdown);
    
    const p1Name = state.bracketState?.active_match?.p1 || 'PLAYER 1';
    const p2Name = state.bracketState?.active_match?.p2 || 'PLAYER 2';
    UI.lanes[0].name.textContent = p1Name;
    UI.lanes[1].name.textContent = p2Name;
    
    handleResults(state, p1Name, p2Name);

    // 2. Bracket State Handling
    if (state.bracketState) {
        latestBracketState = state.bracketState;
        const activeMatchCat = state.bracketState.active_match?.category;
        const isRacing = state.isRacing || state.countdown !== null;

        // Smart Cycling Logic
        if (isRacing && activeMatchCat) {
            displayedCategory = activeMatchCat;
            if (categoryCycleInterval) { clearInterval(categoryCycleInterval); categoryCycleInterval = null; }
        } else if (!displayedCategory) {
            displayedCategory = state.bracketState.active_category || "OPEN";
            startCategoryCycling();
        } else if (!isRacing && !categoryCycleInterval) {
            startCategoryCycling();
        }

        const currentBracketHash = JSON.stringify({
            displayedCat: displayedCategory,
            show: state.bracketState.show_bracket,
            activeMatch: state.bracketState.active_match?.id,
            champs: state.bracketState.champions,
            data: state.bracketState.categories[displayedCategory]?.bracket
        });

        if (currentBracketHash !== lastBracketHash) {
            lastBracketHash = currentBracketHash;
            handleBracket(state.bracketState);
        }
    }
}

function startCategoryCycling() {
    if (categoryCycleInterval) clearInterval(categoryCycleInterval);
    if (!latestBracketState) return;
    
    const categories = Object.keys(latestBracketState.categories).filter(cat => 
        latestBracketState.categories[cat].bracket && latestBracketState.categories[cat].bracket.length > 0
    );
    if (categories.length <= 1) return;

    categoryCycleInterval = setInterval(() => {
        const currentIndex = categories.indexOf(displayedCategory);
        displayedCategory = categories[(currentIndex + 1) % categories.length];
        
        // Force a re-render with the new category
        if (latestBracketState) {
            lastBracketHash = null; // Force hash mismatch
            handleBracket(latestBracketState);
        }
    }, 15000); 
}

function handleResults(state, p1Name, p2Name) {
    const isFinished = state.winner || (state.p1.finishTime && state.p2.finishTime);
    if (isFinished) {
        if (state.winner && state.winner.startsWith('FALSE START')) {
            UI.win.title.textContent = state.winner;
            UI.win.p1.name.textContent = 'RACE ABORTED';
            UI.win.p2.name.textContent = 'FALSE START';
        } else if (state.winner === 'TIE') {
            UI.win.title.textContent = "IT'S A TIE!";
            UI.win.p1.name.textContent = p1Name;
            UI.win.p2.name.textContent = p2Name;
        } else {
            const displayWinner = state.winner === 'Player 1' ? p1Name : p2Name;
            UI.win.title.textContent = `${displayWinner.toUpperCase()} WINS!`;
            UI.win.p1.name.textContent = p1Name;
            UI.win.p2.name.textContent = p2Name;
        }
        UI.win.p1.time.textContent = state.p1.finishTime ? `${state.p1.finishTime.toFixed(2)}S` : 'DNF';
        UI.win.p2.time.textContent = state.p2.finishTime ? `${state.p2.finishTime.toFixed(2)}S` : 'DNF';
        UI.win.overlay.classList.remove('hidden');
    } else {
        UI.win.overlay.classList.add('hidden');
    }
}

function handleCountdown(value) {
    if (value !== null) {
        UI.countdown.text.textContent = value > 0 ? value : 'GOLDSPRINT!';
        UI.countdown.text.classList.toggle('goldsprint-text', value <= 0);
        UI.countdown.overlay.classList.remove('hidden');
    } else {
        UI.countdown.overlay.classList.add('hidden');
    }
}

function updatePlayer(index, player, target) {
    const ui = UI.lanes[index];
    ui.rpm.textContent = player.rpm;
    ui.speed.textContent = player.speed.toFixed(1);
    ui.distLabel.textContent = `${Math.floor(player.dist)}M`;
    const pct = target > 0 ? Math.min(100, (player.dist / target) * 100) : 0;
    ui.progress.style.width = `${pct}%`;
    const classes = ['shake-sluggish', 'shake-light', 'shake-medium', 'shake-heavy', 'shake-vibrant', 'shake-extreme', 'shake-max'];
    ui.lane.classList.remove(...classes);
    if (player.rpm >= 200) ui.lane.classList.add('shake-max');
    else if (player.rpm >= 150) ui.lane.classList.add('shake-heavy');
    else if (player.rpm >= 100) ui.lane.classList.add('shake-light');
}

function handleBracket(bracketState) {
    const catsWithBrackets = Object.values(bracketState.categories).filter(c => c.bracket && c.bracket.length > 0);
    const allFinished = catsWithBrackets.length > 0 && catsWithBrackets.every(c => bracketState.champions[c.name]);
    
    if (allFinished) {
        UI.bracket.overlay.classList.add('hidden');
        UI.champion.overlay.classList.remove('hidden');
        const mainChamp = bracketState.champions[displayedCategory];
        if (mainChamp) {
            UI.champion.name.textContent = mainChamp.name;
            UI.champion.leaderboard.innerHTML = '';
            (bracketState.categories[displayedCategory].top_times || []).forEach((entry, idx) => {
                const row = document.createElement('div');
                row.className = 'leader-row';
                row.innerHTML = `<span class="rank">#${idx+1}</span><span class="name">${entry.name}</span><span class="time">${entry.time.toFixed(2)}s</span>`;
                UI.champion.leaderboard.appendChild(row);
            });
        }
        return;
    } else if (bracketState.show_bracket) {
        UI.bracket.overlay.classList.remove('hidden');
        UI.champion.overlay.classList.add('hidden');
    } else {
        UI.bracket.overlay.classList.add('hidden');
        UI.champion.overlay.classList.add('hidden');
        return;
    }

    const catData = bracketState.categories[displayedCategory];
    if (!catData) return;

    UI.bracket.title.textContent = `${catData.name} BRACKET`;

    if (lastBracketData && lastBracketData[catData.name]) {
        checkForAdvancement(lastBracketData[catData.name], catData, bracketState);
    }
    
    lastBracketData = {};
    catsWithBrackets.forEach(c => lastBracketData[c.name] = JSON.parse(JSON.stringify(c)));

    if (UI.bracket.statsBody) {
        UI.bracket.statsBody.innerHTML = '';
        const uniqueParticipants = [...new Set(catData.participants || [])];
        uniqueParticipants.forEach(name => {
            const bests = (bracketState.participants_bests || {})[name];
            if (!bests || !bests.tournament) return;
            const row = document.createElement('div');
            row.className = 'stats-row';
            row.innerHTML = `<div class="stats-name">${name}</div><div class="stats-times"><span>TOURNAMENT: ${parseFloat(bests.tournament).toFixed(2)}s</span></div>`;
            UI.bracket.statsBody.appendChild(row);
        });
    }

    if (!isAnimating) renderBracketTree(catData, bracketState);
}

function renderBracketTree(catData, bracketState) {
    UI.bracket.container.innerHTML = '';
    UI.bracket.svg.innerHTML = '';
    if (!catData.bracket) return;

    catData.bracket.forEach((round, rIdx) => {
        const roundDiv = document.createElement('div');
        roundDiv.className = 'aud-bracket-round';
        round.forEach(match => {
            const matchDiv = document.createElement('div');
            matchDiv.className = 'aud-bracket-match' + (bracketState.active_match?.id === match.id ? ' active-match' : '');
            matchDiv.id = `match-${match.id}`;
            const p1W = match.winner === match.p1 && match.p1 ? 'winner' : (match.winner ? 'loser' : '');
            const p2W = match.winner === match.p2 && match.p2 ? 'winner' : (match.winner ? 'loser' : '');
            matchDiv.innerHTML = `<div class="aud-bracket-slot ${p1W}">${match.p1 || '---'}</div><div class="aud-bracket-slot ${p2W}">${match.p2 || '---'}</div>`;
            roundDiv.appendChild(matchDiv);
        });
        UI.bracket.container.appendChild(roundDiv);
    });

    setTimeout(() => {
        drawBracketLines(catData);
        if (bracketState.active_match?.category === catData.name) {
            const el = document.getElementById(`match-${bracketState.active_match.id}`);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
        }
    }, 100);
}

function drawBracketLines(catData) {
    const svg = UI.bracket.svg;
    svg.innerHTML = '';
    const containerRect = UI.bracket.container.getBoundingClientRect();
    
    catData.bracket.forEach((round, rIdx) => {
        round.forEach(match => {
            if (!match.next_match_id) return;
            const mEl = document.getElementById(`match-${match.id}`);
            const nmEl = document.getElementById(`match-${match.next_match_id}`);
            if (!mEl || !nmEl) return;

            const mRect = mEl.getBoundingClientRect();
            const nmRect = nmEl.getBoundingClientRect();

            const x1 = mRect.right - containerRect.left;
            const y1 = mRect.top + mRect.height / 2 - containerRect.top;
            const x2 = nmRect.left - containerRect.left;
            
            const isUpper = round.indexOf(match) % 2 === 0;
            const y2 = nmRect.top + (isUpper ? nmRect.height * 0.25 : nmRect.height * 0.75) - containerRect.top;
            
            const midX = x1 + (x2 - x1) / 2;
            const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
            path.setAttribute("d", `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`);
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
                triggerRideAnimation(match, rIdx, rIdx === newCatData.bracket.length - 1, bracketState);
            }
        });
    });
}

function triggerRideAnimation(match, rIdx, isFinal, bracketState) {
    const el = document.getElementById(`match-${match.id}`);
    if (!el) return;
    isAnimating = true;
    const tag = document.createElement('div');
    tag.className = 'floating-tag';
    tag.textContent = match.winner;
    document.body.appendChild(tag);
    const rect = el.getBoundingClientRect();
    tag.style.left = `${rect.left + rect.width / 2}px`;
    tag.style.top = `${rect.top + rect.height / 2}px`;
    setTimeout(() => {
        let ex = window.innerWidth / 2, ey = window.innerHeight / 2;
        if (!isFinal) {
            const nel = document.getElementById(`match-${match.next_match_id}`);
            if (nel) {
                const nr = nel.getBoundingClientRect();
                ex = nr.left + nr.width / 2;
                const isUpper = lastBracketData[displayedCategory].bracket[rIdx].findIndex(m => m.id === match.id) % 2 === 0;
                ey = nr.top + (isUpper ? nr.height * 0.25 : nr.height * 0.75);
            }
        }
        tag.style.transition = "all 1.5s cubic-bezier(0.45, 0, 0.55, 1)";
        tag.style.left = `${ex}px`; tag.style.top = `${ey}px`;
        if (isFinal) tag.style.transform = "translate(-50%, -50%) scale(3)";
        setTimeout(() => { tag.remove(); isAnimating = false; renderBracketTree(bracketState.categories[displayedCategory], bracketState); }, 1600);
    }, 50);
}

connect();
