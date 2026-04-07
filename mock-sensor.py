import socket
import time
import random

HOST = '127.0.0.1'
PORT = 5000

def run_mock_sensor():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Mock sensor server listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                p1_rpm = 0
                p2_rpm = 0
                
                while True:
                    try:
                        # Simulate some realistic RPM fluctuation
                        p1_rpm = max(0, min(200, p1_rpm + random.randint(-10, 15)))
                        p2_rpm = max(0, min(200, p2_rpm + random.randint(-10, 15)))
                        
                        data = f"P1:{p1_rpm}\nP2:{p2_rpm}\n"
                        conn.sendall(data.encode())
                        
                        time.sleep(0.1) # 10Hz update rate
                    except (ConnectionResetError, BrokenPipeError):
                        print("Connection lost. Waiting for new connection...")
                        break

if __name__ == "__main__":
    run_mock_sensor()
