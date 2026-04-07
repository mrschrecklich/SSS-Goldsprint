/**
 * SSS-Goldsprint Audience Controller
 * Optimized for 10-foot UI on projectors. Handles high-performance 
 * animations and synchronized race visualization.
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
            rpm: document.getElementById('p1Rpm'),
            speed: document.getElementById('p1Speed'),
            progress: document.getElementById('p1Progress'),
            distLabel: document.getElementById('p1DistLabel')
        },
        {
            lane: document.getElementById('lane2'),
            rpm: document.getElementById('p2Rpm'),
            speed: document.getElementById('p2Speed'),
            progress: document.getElementById('p2Progress'),
            distLabel: document.getElementById('p2DistLabel')
        }
    ]
};

let ws;

/**
 * WebSocket Connection Management
 */
function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onmessage = (e) => renderState(JSON.parse(e.data));
    ws.onclose = () => setTimeout(connect, 2000);
}

/**
 * Main Render Loop
 */
function renderState(state) {
    // 1. Sync Race Distance
    UI.targetDist.textContent = Math.round(state.targetDist);

    // 2. Handle Overlays (Countdown & Results)
    handleCountdown(state.countdown);
    handleResults(state);

    // 3. Update Player Visualization
    updatePlayer(0, state.p1, state.targetDist);
    updatePlayer(1, state.p2, state.targetDist);
}

/**
 * Handles the "3-2-1-GOLDSPRINT!" countdown display
 */
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

/**
 * Renders the High-Contrast Winner Screen
 */
function handleResults(state) {
    const isFinished = state.winner || (state.p1.finishTime && state.p2.finishTime);
    
    if (isFinished) {
        // Handle False Starts differently
        if (state.winner && state.winner.startsWith('FALSE START')) {
            UI.win.title.textContent = state.winner;
            UI.win.p1.name.textContent = 'RACE ABORTED';
            UI.win.p1.time.textContent = '';
            UI.win.p2.name.textContent = 'FALSE START';
            UI.win.p2.time.textContent = '';
        } else {
            UI.win.title.textContent = `${state.winner.toUpperCase()} WINS!`;
            
            // Sort results
            const results = [
                { name: 'PLAYER 1', time: state.p1.finishTime || 999.99 },
                { name: 'PLAYER 2', time: state.p2.finishTime || 999.99 }
            ].sort((a, b) => a.time - b.time);

            UI.win.p1.name.textContent = results[0].name;
            UI.win.p1.time.textContent = results[0].time < 999 ? `${results[0].time.toFixed(2)}S` : 'DNF';
            UI.win.p2.name.textContent = results[1].name;
            UI.win.p2.time.textContent = results[1].time < 999 ? `${results[1].time.toFixed(2)}S` : 'DNF';
        }
        UI.win.overlay.classList.remove('hidden');
    } else {
        UI.win.overlay.classList.add('hidden');
    }
}

/**
 * Updates individual player progress and visual effects
 */
function updatePlayer(index, player, target) {
    const ui = UI.lanes[index];
    
    // Core Stats
    ui.rpm.textContent = player.rpm;
    ui.speed.textContent = player.speed.toFixed(1);
    ui.distLabel.textContent = `${Math.floor(player.dist)}M`;

    // Progress Bar
    const pct = target > 0 ? Math.min(100, (player.dist / target) * 100) : 0;
    ui.progress.style.width = `${pct}%`;

    // Dynamic Shaking & Glow (based on RPM)
    applyRpmEffects(ui, player.rpm);
}

function applyRpmEffects(ui, rpm) {
    // Threshold Classes for Shaking
    const classes = ['shake-sluggish', 'shake-light', 'shake-medium', 'shake-heavy', 'shake-vibrant', 'shake-extreme', 'shake-max'];
    ui.lane.classList.remove(...classes);

    if (rpm >= 200) ui.lane.classList.add('shake-max');
    else if (rpm >= 180) ui.lane.classList.add('shake-extreme');
    else if (rpm >= 160) ui.lane.classList.add('shake-vibrant');
    else if (rpm >= 150) ui.lane.classList.add('shake-heavy');
    else if (rpm >= 120) ui.lane.classList.add('shake-medium');
    else if (rpm >= 100) ui.lane.classList.add('shake-light');
    else if (rpm >= 80) ui.lane.classList.add('shake-sluggish');

    // Intense Glow (>150 RPM)
    if (rpm >= 150) ui.progress.classList.add('intense-glow');
    else ui.progress.classList.remove('intense-glow');
}

// Initialization
connect();
