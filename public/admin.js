/**
 * SSS-Goldsprint Admin Controller
 * Manages race lifecycle, configuration, and monitoring.
 */

const UI = {
    statusBar: document.getElementById('status-bar'),
    startBtn: document.getElementById('startBtn'),
    stopBtn: document.getElementById('stopBtn'),
    resetBtn: document.getElementById('resetBtn'),
    applyConfigBtn: document.getElementById('applyConfigBtn'),
    inputs: {
        dist: document.getElementById('inputDist'),
        circ: document.getElementById('inputCirc'),
        fs: document.getElementById('inputFS')
    },
    monitors: {
        p1Rpm: document.getElementById('p1Rpm'),
        p1Dist: document.getElementById('p1Dist'),
        p2Rpm: document.getElementById('p2Rpm'),
        p2Dist: document.getElementById('p2Dist')
    }
};

let ws;
let isFirstLoad = true;

/**
 * Handles Tab Switching
 */
window.switchTab = (tabId) => {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.querySelector(`button[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(`${tabId}-tab`).classList.add('active');
};

/**
 * WebSocket Connection Management
 */
function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}`);

    ws.onopen = () => updateUIStatus('Connected & Ready', 'ready');
    ws.onmessage = (event) => renderState(JSON.parse(event.data));
    ws.onclose = () => {
        updateUIStatus('Disconnected. Retrying...', 'warning');
        setTimeout(connect, 2000);
    };
}

/**
 * Updates the Top Status Bar
 */
function updateUIStatus(text, type) {
    UI.statusBar.textContent = text;
    UI.statusBar.className = `status ${type}`;
}

/**
 * Main Render Loop
 */
function renderState(state) {
    // 1. Handle Status & Race Mode
    if (state.winner) {
        updateUIStatus(state.winner, 'stop');
    } else if (state.countdown !== null) {
        updateUIStatus(`COUNTDOWN: ${state.countdown > 0 ? state.countdown : 'GO!'}`, 'racing');
    } else if (state.isRacing) {
        updateUIStatus('RACING', 'racing');
    } else {
        updateUIStatus('Ready to Race', 'ready');
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
        isFirstLoad = false;
    }
}

/**
 * Command Dispatcher
 */
const sendCommand = (type, payload = {}) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type, ...payload }));
    }
};

// Event Listeners
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
    
    // Success feedback
    const originalText = UI.applyConfigBtn.textContent;
    UI.applyConfigBtn.textContent = 'CONFIG APPLIED!';
    UI.applyConfigBtn.style.backgroundColor = '#2196F3';
    setTimeout(() => {
        UI.applyConfigBtn.textContent = originalText;
        UI.applyConfigBtn.style.backgroundColor = '';
    }, 1500);
});

// Initialization
connect();
