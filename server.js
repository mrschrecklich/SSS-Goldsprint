/**
 * SSS-Goldsprint Server
 * Authoritative source of truth for race logic and state synchronization.
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const net = require('net');
const path = require('path');

// --- Configuration ---
const PORT = process.env.PORT || 3000;
const SENSOR_CONFIG = {
    HOST: '127.0.0.1',
    PORT: 5000
};

// --- Game Engine Class ---
class GoldsprintEngine {
    constructor() {
        this.reset();
        this.targetDist = 500;
        this.circumference = 2.1;
        this.falseStartThreshold = 20;
    }

    /**
     * Resets the current race session data.
     */
    reset() {
        this.isRacing = false;
        this.countdown = null;
        this.winner = null;
        this.raceStartTime = null;
        this.p1 = { rpm: 0, speed: 0, dist: 0, finishTime: null };
        this.p2 = { rpm: 0, speed: 0, dist: 0, finishTime: null };
        this.countdownInterval = null;
    }

    /**
     * Handles the 3-second countdown logic.
     */
    startCountdown(broadcastCallback) {
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        
        this.reset();
        this.countdown = 3;
        broadcastCallback();

        this.countdownInterval = setInterval(() => {
            this.countdown--;
            
            if (this.countdown === 0) {
                // Official race start
                this.isRacing = true;
                this.raceStartTime = Date.now();
            } else if (this.countdown < 0) {
                // Clear countdown overlay after GOLDSPRINT! animation
                clearInterval(this.countdownInterval);
                this.countdown = null;
            }
            
            broadcastCallback();
        }, 1000);
    }

    /**
     * Aborts the race immediately (for stops or false starts).
     */
    abort(reason = null) {
        if (this.countdownInterval) clearInterval(this.countdownInterval);
        this.isRacing = false;
        this.countdown = null;
        if (reason) this.winner = reason;
    }

    /**
     * Updates player progress based on latest sensor data.
     */
    updateTick(p1Rpm, p2Rpm, dt) {
        // Handle False Start Check
        if (this.countdown !== null && this.countdown > 0) {
            if (p1Rpm > this.falseStartThreshold) return 'FALSE START: PLAYER 1';
            if (p2Rpm > this.falseStartThreshold) return 'FALSE START: PLAYER 2';
        }

        this.p1.rpm = p1Rpm;
        this.p2.rpm = p2Rpm;

        // Calculate m/s speed: (RPM / 60) * Circumference
        const p1MS = (p1Rpm / 60) * this.circumference;
        const p2MS = (p2Rpm / 60) * this.circumference;

        this.p1.speed = p1MS * 3.6; // km/h
        this.p2.speed = p2MS * 3.6; // km/h

        if (this.isRacing) {
            this.processPlayerProgress('p1', p1MS, dt);
            this.processPlayerProgress('p2', p2MS, dt);

            // Check if both players finished to stop the loop
            if (this.p1.finishTime && this.p2.finishTime) {
                this.isRacing = false;
            }
        }
        return null;
    }

    processPlayerProgress(playerKey, speedMS, dt) {
        const player = this[playerKey];
        if (!player.finishTime) {
            player.dist += speedMS * dt;
            if (player.dist >= this.targetDist) {
                player.dist = this.targetDist;
                player.finishTime = (Date.now() - this.raceStartTime) / 1000;
                if (!this.winner) this.winner = playerKey === 'p1' ? 'Player 1' : 'Player 2';
            }
        }
    }

    getState() {
        return {
            isRacing: this.isRacing,
            countdown: this.countdown,
            targetDist: this.targetDist,
            circumference: this.circumference,
            falseStartThreshold: this.falseStartThreshold,
            winner: this.winner,
            p1: this.p1,
            p2: this.p2
        };
    }
}

// --- Server Setup ---
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
const engine = new GoldsprintEngine();

app.use(express.static(path.join(__dirname, 'public')));

// Broadcast state to all connected UI clients
const broadcast = () => {
    const data = JSON.stringify(engine.getState());
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) client.send(data);
    });
};

// --- WebSocket Message Routing ---
wss.on('connection', (ws) => {
    ws.send(JSON.stringify(engine.getState()));

    ws.on('message', (message) => {
        try {
            const cmd = JSON.parse(message);
            switch (cmd.type) {
                case 'START': engine.startCountdown(broadcast); break;
                case 'STOP': engine.abort(); break;
                case 'RESET': engine.reset(); break;
                case 'CONFIG':
                    if (cmd.dist !== undefined) engine.targetDist = parseFloat(cmd.dist) || 0;
                    if (cmd.circ !== undefined) engine.circumference = parseFloat(cmd.circ) || 0;
                    if (cmd.fsThreshold !== undefined) engine.falseStartThreshold = parseFloat(cmd.fsThreshold) || 0;
                    break;
            }
            broadcast();
        } catch (e) {
            console.error('WS Error:', e);
        }
    });
});

// --- Sensor TCP Ingestion ---
let lastTickTime = Date.now();

const connectSensor = () => {
    const socket = new net.Socket();
    
    socket.connect(SENSOR_CONFIG.PORT, SENSOR_CONFIG.HOST, () => {
        console.log(`Connected to sensor: ${SENSOR_CONFIG.HOST}:${SENSOR_CONFIG.PORT}`);
        lastTickTime = Date.now();
    });

    socket.on('data', (data) => {
        const lines = data.toString().split('\n');
        let rpm1 = engine.p1.rpm, rpm2 = engine.p2.rpm;

        lines.forEach(l => {
            if (l.startsWith('P1:')) rpm1 = parseInt(l.split(':')[1]) || 0;
            if (l.startsWith('P2:')) rpm2 = parseInt(l.split(':')[1]) || 0;
        });

        const now = Date.now();
        const dt = (now - lastTickTime) / 1000;
        lastTickTime = now;

        const error = engine.updateTick(rpm1, rpm2, dt);
        if (error) engine.abort(error);

        broadcast();
    });

    socket.on('close', () => setTimeout(connectSensor, 2000));
    socket.on('error', () => {}); // Silent reconnect
};

server.listen(PORT, () => {
    console.log(`Goldsprint Web Server: http://localhost:${PORT}`);
    connectSensor();
});
