// SSS-Goldsprint Frontend Logic
let ws;
let p1Dist = 0;
let p2Dist = 0;
let isRacing = false;
let lastUpdate = Date.now();

// Config inputs
const inputDist = document.getElementById('inputDist');
const inputCirc = document.getElementById('inputCirc');

// Display elements
const p1RpmEl = document.getElementById('p1-rpm');
const p2RpmEl = document.getElementById('p2-rpm');
const p1SpeedEl = document.getElementById('p1-speed');
const p2SpeedEl = document.getElementById('p2-speed');
const p1DistEl = document.getElementById('p1-dist');
const p2DistEl = document.getElementById('p2-dist');
const p1ProgressEl = document.getElementById('p1-progress');
const p2ProgressEl = document.getElementById('p2-progress');
const statusEl = document.getElementById('status');
const startBtn = document.getElementById('startBtn');

// Modal elements
const winModal = document.getElementById('win-modal');
const winnerText = document.getElementById('winner-text');

function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onopen = () => {
        statusEl.innerText = 'Connected to Race Server';
        statusEl.style.color = '#4CAF50';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const now = Date.now();
        const dt = (now - lastUpdate) / 1000; // time in seconds since last update
        lastUpdate = now;

        if (isRacing) {
            updateRace(data, dt);
        } else {
            // Update RPM even if not racing
            p1RpmEl.innerText = data.p1;
            p2RpmEl.innerText = data.p2;
        }
    };

    ws.onclose = () => {
        statusEl.innerText = 'Disconnected. Retrying...';
        statusEl.style.color = '#f44336';
        setTimeout(connect, 2000);
    };
}

function updateRace(data, dt) {
    const circumference = parseFloat(inputCirc.value) || 2.1;
    const targetDist = parseFloat(inputDist.value) || 500;

    // RPM is Revs Per Minute, so Revs Per Second = RPM / 60
    // Speed in m/s = (RPM / 60) * circumference
    const p1SpeedMS = (data.p1 / 60) * circumference;
    const p2SpeedMS = (data.p2 / 60) * circumference;

    // Convert m/s to km/h: (m/s) * 3.6
    const p1SpeedKMH = p1SpeedMS * 3.6;
    const p2SpeedKMH = p2SpeedMS * 3.6;

    p1Dist += p1SpeedMS * dt;
    p2Dist += p2SpeedMS * dt;

    // UI Updates
    p1RpmEl.innerText = data.p1;
    p2RpmEl.innerText = data.p2;
    p1SpeedEl.innerText = p1SpeedKMH.toFixed(1);
    p2SpeedEl.innerText = p2SpeedKMH.toFixed(1);
    p1DistEl.innerText = p1Dist.toFixed(2);
    p2DistEl.innerText = p2Dist.toFixed(2);

    // Progress Bars (capped at 100%)
    const p1Percent = Math.min(100, (p1Dist / targetDist) * 100);
    const p2Percent = Math.min(100, (p2Dist / targetDist) * 100);
    
    p1ProgressEl.style.width = p1Percent + '%';
    p2ProgressEl.style.width = p2Percent + '%';

    // Check for Winner
    if (p1Dist >= targetDist) {
        endRace('Player 1');
    } else if (p2Dist >= targetDist) {
        endRace('Player 2');
    }
}

function startRace() {
    p1Dist = 0;
    p2Dist = 0;
    p1ProgressEl.style.width = '0%';
    p2ProgressEl.style.width = '0%';
    p1DistEl.innerText = '0.00';
    p2DistEl.innerText = '0.00';
    p1SpeedEl.innerText = '0.0';
    p2SpeedEl.innerText = '0.0';
    
    isRacing = true;
    lastUpdate = Date.now();
    
    startBtn.innerText = 'STOP RACE';
    startBtn.classList.add('racing');
    statusEl.innerText = 'RACING!';
    statusEl.style.color = '#ff9900';
}

function stopRace() {
    isRacing = false;
    startBtn.innerText = 'START RACE';
    startBtn.classList.remove('racing');
    statusEl.innerText = 'Race Stopped';
    statusEl.style.color = '#aaa';
}

function endRace(winner) {
    isRacing = false;
    stopRace();
    winnerText.innerText = winner + ' WINS!';
    winModal.style.display = 'block';
}

window.closeModal = function() {
    winModal.style.display = 'none';
};

startBtn.onclick = () => {
    if (isRacing) {
        stopRace();
    } else {
        startRace();
    }
};

// Start connection
connect();
