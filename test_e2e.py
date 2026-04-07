import asyncio
import websockets
import json
import subprocess
import time

async def run_e2e_test():
    # Start the mock sensor
    print("Starting mock sensor...")
    sensor_proc = subprocess.Popen(["python3", "mock-sensor.py"])
    
    await asyncio.sleep(1)  # Give sensor time to start and server to connect

    async with websockets.connect("ws://127.0.0.1:3000/") as ws:
        # 1. Add participants and generate bracket
        print("Setting up bracket...")
        await ws.send(json.dumps({"type": "ADD_PARTICIPANT", "category": "OPEN", "name": "Alice"}))
        await ws.send(json.dumps({"type": "ADD_PARTICIPANT", "category": "OPEN", "name": "Bob"}))
        await ws.send(json.dumps({"type": "GENERATE_BRACKET", "category": "OPEN"}))
        
        # Give some time for messages to process
        await asyncio.sleep(0.5)

        # 2. Wait for mock sensor to do its 5s sync delay (it waits 5s before sending data)
        # We want to send START right as it starts sending data, or slightly before.
        print("Sending START command...")
        await ws.send(json.dumps({"type": "START"}))

        # 3. Listen to broadcasts until race is over
        race_finished = False
        p1_time = None
        p2_time = None
        
        print("Listening for state updates...")
        while not race_finished:
            try:
                state_str = await asyncio.wait_for(ws.recv(), timeout=10.0)
                state = json.loads(state_str)
                print(f"Received state update! P1 dist: {state['p1']['dist']:.1f}, P2 dist: {state['p2']['dist']:.1f}")
                
                # Check engine state
                if state["p1"]["finishTime"] and state["p2"]["finishTime"]:
                    p1_time = state["p1"]["finishTime"]
                    p2_time = state["p2"]["finishTime"]
                    race_finished = True
                    print(f"Race finished! P1: {p1_time:.2f}s, P2: {p2_time:.2f}s")
            except asyncio.TimeoutError:
                print("Timeout waiting for state update. Race might not be progressing.")
                break
            except Exception as e:
                print(f"Error reading state: {e}")
                break

        # 4. Advance winner
        if p1_time and p2_time:
            winner = "Alice" if p1_time < p2_time else "Bob"
            winner_time = min(p1_time, p2_time)
            
            # Need match ID
            bracket_state = state["bracketState"]
            active_match = bracket_state["active_match"]
            match_id = active_match["id"] if active_match else None
            
            if match_id:
                print(f"Advancing winner {winner} for match {match_id}...")
                await ws.send(json.dumps({
                    "type": "ADVANCE_WINNER",
                    "category": "OPEN",
                    "match_id": match_id,
                    "winner": winner,
                    "time": winner_time
                }))
                
                await asyncio.sleep(1)
                
                # Verify DB
                import urllib.request
                req = urllib.request.Request("http://127.0.0.1:3000/api/highscores")
                with urllib.request.urlopen(req) as res:
                    data = json.loads(res.read())
                    print("Highscores from DB:")
                    print(data)
                    if len(data) > 0:
                        print("DB Validation SUCCESS.")
                    else:
                        print("DB Validation FAILED - no highscores found.")
            else:
                print("Failed to get active match ID.")

    # Cleanup
    sensor_proc.terminate()
    sensor_proc.wait()

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
