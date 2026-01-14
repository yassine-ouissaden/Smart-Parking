import pygame

# --- Captor Style Constants ---
CAPTOR_BOX_COLOR = (40, 40, 50) # Dark Grey casing
BORDER_COLOR = (10, 10, 10)

# Light Colors (Bright vs Dim)
RED_ON = (255, 30, 30)
RED_OFF = (80, 0, 0)     
GREEN_ON = (30, 255, 30)
GREEN_OFF = (0, 80, 0)   

def draw_captor_box(surface, x, y, width, status):
    """
    Draws a sensor box with two lights (Red/Green).
    We position it ABOVE the spot (y - 25) so the car doesn't hide it.
    """
    
    # 1. Calculate Position 
    # Move it UP by 25 pixels (y - 25) so it sits 'above' the parking line
    box_w, box_h = 40, 18
    box_x = x + (width - box_w) // 2
    box_y = y - 25 
    
    # 2. Draw a small "Connector Line" (Visual wire to the ceiling/wall)
    # This makes it look suspended
    center_x = box_x + box_w // 2
    pygame.draw.line(surface, (100, 100, 100), (center_x, box_y + box_h), (center_x, y), 2)

    # 3. Draw the Box Casing
    pygame.draw.rect(surface, CAPTOR_BOX_COLOR, (box_x, box_y, box_w, box_h), border_radius=4)
    pygame.draw.rect(surface, BORDER_COLOR, (box_x, box_y, box_w, box_h), 1, border_radius=4)
    
    # 4. Determine Light Colors based on Status
    if status == 'OCCUPIED':
        light_red = RED_ON
        light_green = GREEN_OFF
        # Add a glow effect for the active light
        pygame.draw.circle(surface, (255, 0, 0, 100), (box_x + 12, box_y + 9), 6)
    else: # FREE
        light_red = RED_OFF
        light_green = GREEN_ON
        # Add a glow effect for the active light
        pygame.draw.circle(surface, (0, 255, 0, 100), (box_x + 28, box_y + 9), 6)

    # 5. Draw the Two LEDs
    # Left Light (Red)
    pygame.draw.circle(surface, light_red, (box_x + 12, box_y + 9), 4)
    # Right Light (Green)
    pygame.draw.circle(surface, light_green, (box_x + 28, box_y + 9), 4)