import pygame
import sys
import requests
import time
import threading

SERVER_URL = "http://127.0.0.1:8000"
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 600
BG_COLOR = (200, 200, 200)
ROAD_COLOR = (60, 60, 60)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 200, 0)
RED = (180, 0, 0) 
MOVING_CAR_COLOR = (220, 30, 30)

CAR_WIDTH = 70
CAR_HEIGHT = 110
CAR_SIZE = (CAR_WIDTH, CAR_HEIGHT)
CAR_SPEED = 5

SPOTS_CONFIG = [
    {'id': 'A1', 'pos': (350, 100), 'status': 'FREE'},
    {'id': 'A2', 'pos': (450, 100), 'status': 'OCCUPIED'},
    {'id': 'A3', 'pos': (550, 100), 'status': 'FREE'},
    {'id': 'A4', 'pos': (650, 100), 'status': 'OCCUPIED'},
    {'id': 'A5', 'pos': (750, 100), 'status': 'OCCUPIED'},
    {'id': 'B1', 'pos': (350, 400), 'status': 'FREE'},
    {'id': 'B2', 'pos': (450, 400), 'status': 'OCCUPIED'},
    {'id': 'B3', 'pos': (550, 400), 'status': 'OCCUPIED'},
    {'id': 'B4', 'pos': (650, 400), 'status': 'OCCUPIED'},
    {'id': 'B5', 'pos': (750, 400), 'status': 'FREE'},
]

# ----- Global State -----
gate_open = False
car_state = "APPROACHING" 
log_messages = ["> System Ready."]

# Simulation Variables
simulation_car_x = -150 
simulation_car_y = 245
simulation_car_angle = -90 
target_spot = None 

# --- Networking Function ---
def initialize_sensors():
    add_log("--- Initializing Network ---")
    try:
        # Register Entry Sensor
        requests.post(f"{SERVER_URL}/register", json={"id": "Entry_Sensor", "type": "sensor", "location": "Gate"})
        
        # Register Spots & Send Initial Status
        for spot in SPOTS_CONFIG:
            requests.post(f"{SERVER_URL}/register", json={"id": spot['id'], "type": "parking_spot", "location": "Zone_A"})
            requests.post(f"{SERVER_URL}/data", json={"device_id": spot['id'], "value": spot['status']})
            time.sleep(0.01)
            
        add_log("--- All Sensors Synced ---")
    except:
        add_log("Error: Server Offline.")

def check_parking_access():
    global gate_open, car_state, target_spot
    add_log("Sensor: Car Detected.")
    time.sleep(0.5)
    
    try:
        payload = {"device_id": "Entry_Sensor", "value": "CAR_DETECTED"}
        response = requests.post(f"{SERVER_URL}/data", json=payload, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            server_response = data.get('response')
            add_log(f"Server: {server_response}")
            
            if data.get("action") == "OPEN_GATE":
                # Find the first FREE spot to drive to
                target_spot = next((s for s in SPOTS_CONFIG if s['status'] == 'FREE'), None)
                
                if target_spot:
                    time.sleep(0.5)
                    gate_open = True
                    add_log(f"Assigned to {target_spot['id']}")
                    time.sleep(0.5)
                    car_state = "ENTERING"
                else:
                    # Logic safety: Server said open, but we have no spots? Treat as full.
                    car_state = "LEAVING_FULL" 
            else:
                # Parking Full - Reject
                add_log("Parking Full. Denied.")
                time.sleep(1)
                car_state = "LEAVING_FULL"
        else:
            add_log("Error: Server Error.")

    except Exception as e:
        add_log("Error: Connection Failed.")

def update_spot_status_on_server(spot_id, status):
    try:
        requests.post(f"{SERVER_URL}/data", json={"device_id": spot_id, "value": status})
    except:
        pass

def add_log(msg):
    log_messages.append(f"> {msg}")
    if len(log_messages) > 15:
        log_messages.pop(0)

def spawn_next_car():
    global simulation_car_x, simulation_car_y, simulation_car_angle, car_state, gate_open, target_spot
    time.sleep(1.5) # Delay before next car
    simulation_car_x = -150
    simulation_car_y = 245
    simulation_car_angle = -90
    gate_open = False
    target_spot = None
    car_state = "APPROACHING"
    add_log("--- Next Car Arriving ---")

# --- Pygame Initialization ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Smart Parking Simulation Final")
clock = pygame.time.Clock()
font_log = pygame.font.Font(None, 20)
font_label = pygame.font.Font(None, 28)
font_display = pygame.font.Font(None, 40) # Font for the Gate Display

# Start logic in background
threading.Thread(target=initialize_sensors, daemon=True).start()

# --- Drawing Helpers ---
def draw_car(surface, x, y, color, angle=0):
    w, h = CAR_SIZE
    car_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    r,g,b = color
    # Tires
    pygame.draw.rect(car_surf, (20,20,20), (0, 15, 8, 18), border_radius=3) 
    pygame.draw.rect(car_surf, (20,20,20), (w-8, 15, 8, 18), border_radius=3)
    pygame.draw.rect(car_surf, (20,20,20), (0, h-35, 8, 18), border_radius=3) 
    pygame.draw.rect(car_surf, (20,20,20), (w-8, h-35, 8, 18), border_radius=3)
    # Body
    pygame.draw.rect(car_surf, color, (4, 0, w-8, h), border_radius=15)
    # Roof
    pygame.draw.rect(car_surf, (max(0,r-30),max(0,g-30),max(0,b-30)), (10, 25, w-20, h-45), border_radius=8)
    # Windows
    pygame.draw.rect(car_surf, (50,70,90), (12, 28, w-24, 12), border_radius=4) 
    pygame.draw.rect(car_surf, (50,70,90), (12, h-28, w-24, 10), border_radius=4) 
    
    rotated = pygame.transform.rotate(car_surf, angle)
    rect = rotated.get_rect(center=(x + w//2, y + h//2))
    surface.blit(rotated, rect.topleft)

def draw_scene():
    screen.fill(BG_COLOR)
    # Road
    pygame.draw.rect(screen, ROAD_COLOR, (0, 250, 900, 100))
    pygame.draw.rect(screen, ROAD_COLOR, (0, 0, 150, SCREEN_HEIGHT))
    
    # --- NEW: GATE DISPLAY (Available Spots) ---
    # Calculate free spots
    free_count = sum(1 for s in SPOTS_CONFIG if s['status'] == 'FREE')
    
    # Draw the Pole holding the screen
    pygame.draw.rect(screen, (50,50,50), (220, 150, 10, 100))
    # Draw the Screen Box
    display_rect = pygame.Rect(180, 100, 120, 60)
    pygame.draw.rect(screen, BLACK, display_rect, border_radius=8)
    pygame.draw.rect(screen, (100,100,100), display_rect, 3, border_radius=8)
    
    # Draw Text
    if free_count > 0:
        text_surf = font_display.render(f"FREE: {free_count}", True, GREEN)
    else:
        text_surf = font_display.render("FULL", True, RED)
    
    # Center text in box
    text_rect = text_surf.get_rect(center=display_rect.center)
    screen.blit(text_surf, text_rect)
    # ------------------------------------------

    # Sensor
    pygame.draw.rect(screen, YELLOW, (180, 250, 80, 100), 3)
    
    # Gate Arm
    pygame.draw.rect(screen, (50, 50, 50), (260, 230, 15, 140)) 
    if gate_open:
        pygame.draw.rect(screen, GREEN, (260, 235, 80, 12), border_radius=5) 
    else:
        pygame.draw.rect(screen, RED, (265, 290, 12, 80), border_radius=5) 

    # Spots
    for spot in SPOTS_CONFIG:
        x, y = spot['pos']
        color = GREEN if spot['status'] == 'FREE' else RED
        pygame.draw.rect(screen, color, (x, y, 80, 120), 3, border_radius=5)
        text = font_label.render(spot['id'], True, BLACK)
        screen.blit(text, (x + 25, y + 50))
        if spot['status'] == 'OCCUPIED':
            draw_car(screen, x+5, y+5, RED)

    # Active Car (Only draw if not "DONE")
    if car_state != "DONE":
        draw_car(screen, simulation_car_x, simulation_car_y, MOVING_CAR_COLOR, angle=simulation_car_angle)

    # Log
    pygame.draw.rect(screen, (230, 230, 230), (900, 0, 200, SCREEN_HEIGHT))
    for i, msg in enumerate(log_messages):
        text = font_log.render(msg, True, BLACK)
        screen.blit(text, (910, 20 + i * 25))

# --- Main Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
    # --- Logic ---
    if car_state == "APPROACHING":
        simulation_car_x += CAR_SPEED
        if simulation_car_x >= 110:
            car_state = "WAITING"
            threading.Thread(target=check_parking_access, daemon=True).start()

    elif car_state == "ENTERING":
        simulation_car_x += CAR_SPEED
        target_x = target_spot['pos'][0] + 5 
        if simulation_car_x >= target_x:
            simulation_car_x = target_x
            car_state = "TURNING"

    elif car_state == "TURNING":
        target_y = target_spot['pos'][1]
        if target_y < 250: # Top Row
            if simulation_car_angle < 0: simulation_car_angle += 5
            else: 
                simulation_car_angle = 0
                car_state = "PARKING_MOVE"
        else: # Bottom Row
            if simulation_car_angle > -180: simulation_car_angle -= 5
            else: 
                simulation_car_angle = -180
                car_state = "PARKING_MOVE"

    elif car_state == "PARKING_MOVE":
        target_y = target_spot['pos'][1] + 5
        if simulation_car_angle == 0: # Up
            simulation_car_y -= CAR_SPEED
            if simulation_car_y <= target_y:
                simulation_car_y = target_y
                car_state = "PARKED"
        else: # Down
            simulation_car_y += CAR_SPEED
            if simulation_car_y >= target_y:
                simulation_car_y = target_y
                car_state = "PARKED"

    elif car_state == "PARKED":
        target_spot['status'] = 'OCCUPIED'
        add_log(f"Parked in {target_spot['id']}")
        threading.Thread(target=update_spot_status_on_server, args=(target_spot['id'], 'OCCUPIED'), daemon=True).start()
        car_state = "DONE"
        threading.Thread(target=spawn_next_car, daemon=True).start()

    # --- REJECTION LOGIC (Backing up) ---
    elif car_state == "LEAVING_FULL":
        # Wait a moment, then start turning around
        simulation_car_angle += 5
        # Turn 180 degrees (face Left)
        if simulation_car_angle >= 90:
            simulation_car_angle = 90
            car_state = "LEAVING_DRIVE"
            
    elif car_state == "LEAVING_DRIVE":
        # Drive back out to the left
        simulation_car_x -= CAR_SPEED 
        if simulation_car_x < -150:
            car_state = "DONE" # Remove car
            threading.Thread(target=spawn_next_car, daemon=True).start()

    draw_scene()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()