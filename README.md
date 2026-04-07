# SSS-Goldsprint

A high-performance, web-based Goldsprint racing simulation designed for events and projectors. This project features a centralized "Source of Truth" architecture to ensure perfect synchronization between race controllers and audience displays.

## 🚀 Tech Stack

- **Backend**: Node.js, Express (Web Server), `ws` (WebSockets), `net` (TCP Ingestion).
- **Frontend**: Vanilla JavaScript (ES6+), CSS3 (Animations & Flexbox), HTML5.
- **Sensor Simulation**: Python 3 (Socket programming).
- **Design Philosophy**: "10-foot UI" for projectors, mobile-first for admin controls.

---

## 🏗️ Architecture Overview

The system is split into three core layers:

### 1. The Authoritative Server (`server.js`)
The Node.js server acts as the master controller. Unlike traditional setups where the frontend calculates distance, this server runs a **Goldsprint Engine** that:
- Manages the race state (Ready, Countdown, Racing, Finished).
- Ingests raw RPM data from sensors via a TCP socket (Port 5000).
- Calculates speed (km/h) and distance (meters) at 10Hz.
- Detects **False Starts** if riders pedal too early.
- Broadcasts a single, unified JSON state to all connected WebSockets.

### 2. The Frontend Views (`public/`)
- **Admin View (`admin.html`)**: Optimized for tablets and phones. Features massive "fat-finger" touch targets, traffic-light status indicators, and live configuration for distance, wheel circumference, and false start thresholds.
- **Audience View (`audience.html`)**: A "10-foot UI" designed for high-contrast projection. It features:
    - **Dynamic Shaking**: CSS animations that increase in intensity based on real-time RPM (from "sluggish" at 80 RPM to "exploding" at 200 RPM).
    - **GOLDSPRINT! Countdown**: A high-energy start sequence.
    - **Enhanced Results**: Shows both 1st and 2nd place with precise finish times.
- **Launcher (`index.html`)**: A simple landing page to toggle between the two views.

### 3. The Realistic Mock Sensor (`mock-sensor.py`)
A Python script that emulates professional riders:
- **Phase 1 (Spin Up)**: Rapid acceleration to peak RPM.
- **Phase 2 (Maintain)**: Holding energy until 70% of the race.
- **Phase 3 (Fatigue)**: Realistic RPM drop-off as the rider tires near the finish line.
- **Sync Timer**: Features a 5-second terminal countdown to help you sync your "Start" click with the simulation.

---

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd SSS-Goldsprint
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Ensure Python 3 is installed** (for the mock sensor).

---

## 🏃 Running the Project

To run a full simulation, follow these steps in order:

1. **Start the Web Server**:
   ```bash
   node server.js
   ```
   *The server will start at `http://localhost:3000` and wait for sensor data.*

2. **Start the Mock Sensor**:
   ```bash
   python mock-sensor.py
   ```
   *Wait for the terminal to say `Web Server connected`. A 5-second countdown will begin.*

3. **Open the Interfaces**:
   - Open `http://localhost:3000` in your browser.
   - Launch the **Audience View** in one window (ideally full-screen on a second monitor/projector).
   - Launch the **Admin View** on your control device (phone/tablet/laptop).

4. **Start the Race**:
   - When the Python terminal countdown hits **"GO!"**, click **START RACE** in the Admin View.
   - Watch the Audience View transition from the `3, 2, 1` countdown into a high-energy race.

---

## ⚙️ Configuration

### Adjusting Race Logic (Distance/Wheel Size)
You can adjust these live in the **Admin View** under the "Race Controls" tab. Click **APPLY CONFIG** to sync changes to the server and audience.

### Adjusting Rider Performance
Open `mock-sensor.py` and edit the `=== EASY CONFIGURATION ===` block at the top:
- `TARGET_DIST`: Change the total meters.
- `P1_CONFIG` / `P2_CONFIG`: Tweak `MAX_RPM`, `ACCEL`, and `FATIGUE` to create different race scenarios (e.g., a sprinter vs. an endurance rider).

---

## 🧪 Testing

The project includes unit tests for the core engine logic (distance math, win conditions, config parsing).

```bash
npm test
```
