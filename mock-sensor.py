"""
SSS-Goldsprint Realistic Mock Sensor
Simulates bicycle RPM data with acceleration, maintain, and fatigue phases.
"""

import socket
import time
import random

# === EASY CONFIGURATION ===
# General Race Parameters
TARGET_DIST = 500      # Race distance in meters
CIRCUMFERENCE = 2.1    # Wheel circumference in meters (default 700c tire)

# Player 1 Performance (Pro Rider)
P1_CONFIG = {
    'MAX_RPM': 200,
    'ACCEL': 18,       # RPM increase per 0.1s
    'FATIGUE': 0.75,   # Start tiring at 75% of race
    'DROP': 0.8        # RPM drop-off per 0.1s after fatigue
}

# Player 2 Performance (Challenger)
P2_CONFIG = {
    'MAX_RPM': 185,
    'ACCEL': 12,
    'FATIGUE': 0.60,   # Start tiring at 60% of race
    'DROP': 1.2
}

# Network Configuration
HOST = '127.0.0.1'
PORT = 5000
# ==========================

class PlayerSimulator:
    """Simulates a single rider's physical output during a Goldsprint race."""
    
    def __init__(self, name, config):
        self.name = name
        self.cfg = config
        self.rpm = 0
        self.dist = 0
        self.is_active = False
        self.finished = False

    def reset(self):
        """Resets the player for a new race."""
        self.rpm = 0
        self.dist = 0
        self.is_active = False
        self.finished = False

    def update(self, dt):
        """Calculates RPM and distance for the current tick."""
        if not self.is_active:
            return

        progress = self.dist / TARGET_DIST
        
        if not self.finished:
            # Phase 1: Spin Up & Maintenance
            if progress < self.cfg['FATIGUE']:
                self.rpm = min(self.cfg['MAX_RPM'], 
                              self.rpm + self.cfg['ACCEL'] + random.randint(-2, 2))
            # Phase 2: Fatigue & Power Drop
            else:
                self.rpm = max(80, 
                              self.rpm - self.cfg['DROP'] + random.randint(-3, 2))

            # Physics: Update Distance
            speed_ms = (self.rpm / 60) * CIRCUMFERENCE
            self.dist += speed_ms * dt

            if self.dist >= TARGET_DIST:
                self.dist = TARGET_DIST
                self.finished = True
        else:
            # Phase 3: Post-Finish Slowdown
            self.rpm = max(0, self.rpm - 10)

def run_sensor_server():
    """Main execution loop for the mock sensor TCP server."""
    p1 = PlayerSimulator("P1", P1_CONFIG)
    p2 = PlayerSimulator("P2", P2_CONFIG)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        
        print(f"\n[MOCK SENSOR] Listening on {HOST}:{PORT}")
        print("[MOCK SENSOR] Ready for Web Server connection...")
        
        conn, addr = s.accept()
        with conn:
            print(f"[MOCK SENSOR] Web Server connected from {addr}")
            
            print("\n[SYNC] PREPARE START: Hit 'START RACE' on Web Admin when countdown hits GO!")
            for i in range(5, 0, -1):
                print(f"  {i}...")
                time.sleep(1)
            
            print("  GO! (Simulation active)")
            p1.is_active = True
            p2.is_active = True

            try:
                while True:
                    p1.update(0.1)
                    p2.update(0.1)
                    
                    # Protocol: P1:RPM\nP2:RPM\n
                    data = f"P1:{int(p1.rpm)}\nP2:{int(p2.rpm)}\n"
                    conn.sendall(data.encode())
                    
                    # Auto-stop when both players have halted
                    if p1.finished and p2.finished and p1.rpm == 0 and p2.rpm == 0:
                        print("\n[MOCK SENSOR] Race completed. Simulation ended.")
                        break

                    time.sleep(0.1) # 10Hz Broadcast
            except (ConnectionResetError, BrokenPipeError):
                print("\n[MOCK SENSOR] Connection lost. Simulation aborted.")

if __name__ == "__main__":
    try:
        run_sensor_server()
    except KeyboardInterrupt:
        print("\n[MOCK SENSOR] Server stopped by user.")
