import pygame
import sys
import pyaudio
import numpy as np
import math

# Initialize Pygame
pygame.init()

# Screen configuration
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Ike-Tuber")

# Define the green color for the background
background_color = (0, 255, 0)  # RGB for bright green

# Initialize font for debug text
font = pygame.font.Font(None, 36)

# Function to resize and center the image
def resize_and_center(image, max_width, max_height):
    image_rect = image.get_rect()
    scale = min(max_width / image_rect.width, max_height / image_rect.height)
    new_size = (int(image_rect.width * scale), int(image_rect.height * scale))
    resized_image = pygame.transform.scale(image, new_size)
    resized_rect = resized_image.get_rect(center=(screen_width // 2, screen_height // 2))
    return resized_image, resized_rect

# Load VTuber images from the folder
upper_half = pygame.image.load('images/upper_half.png')
lower_half = pygame.image.load('images/lower_half.png')

# Resize and center images to fit the screen
upper_half, upper_half_rect = resize_and_center(upper_half, screen_width * 0.5, screen_height * 0.5)
lower_half, lower_half_rect = resize_and_center(lower_half, screen_width * 0.5, screen_height * 0.5)

# PyAudio configuration
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

def get_audio_level():
    data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
    return np.abs(data).mean()

# Audio detection sensitivity
sensitivity = 0.1  # Adjust according to audio level
min_audio_threshold = 15  # Minimum audio level to trigger movement

# Parameters for angular displacement
angular_offset = 0.5  # Minimum rotation angle

# Update frequency
fps = 30
clock = pygame.time.Clock()

# Lower limit for the lower half position
lower_half_min_y = 300

# Debug information control
show_debug_info = False  # Set to False to hide debug information

# Variables for side switching
opening_side = 1  # 1 for bottom, -1 for top
change_interval = 30  # Interval to change the side that opens (in frames)
frame_count = 0

# Main loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the screen with the green color
    screen.fill(background_color)

    # Get the audio level
    audio_level = get_audio_level()

    # Calculate jaw displacement based on audio level
    jaw_base_offset = min(int(audio_level * sensitivity), screen_height // 16)  # Adjust as needed

    # Update side change interval
    frame_count += 1
    if frame_count > change_interval:
        frame_count = 0
        opening_side *= -1  # Switch the opening side

    # Variables for position and displacement
    upper_half_center_y = screen_height // 2 - jaw_base_offset * 0.5
    lower_half_center_y = screen_height // 2 + jaw_base_offset * 0.5

    if jaw_base_offset > 0 and audio_level > min_audio_threshold:
        if opening_side == 1:  # Bottom side open
            lower_half_rotated = pygame.transform.rotate(lower_half, jaw_base_offset * angular_offset)
            lower_half_rect = lower_half_rotated.get_rect(center=(screen_width // 2, lower_half_center_y))

            # Ensure the lower position does not go below `lower_half_min_y`
            if lower_half_rect.bottom > lower_half_min_y:
                lower_half_rect.bottom = lower_half_min_y

            upper_half_rotated = pygame.transform.rotate(upper_half, -jaw_base_offset * angular_offset * 0.5)
            upper_half_rect = upper_half_rotated.get_rect(center=(screen_width // 2, upper_half_center_y))

            # Ensure halves remain aligned
            upper_half_rect.bottom = screen_height // 2
            lower_half_rect.top = screen_height // 2

            # Draw the upper and lower halves with angular displacement
            screen.blit(upper_half_rotated, (upper_half_rect.left, upper_half_rect.top))
            screen.blit(lower_half_rotated, (lower_half_rect.left, lower_half_rect.top))
        else:  # Top side open
            upper_half_rotated = pygame.transform.rotate(upper_half, jaw_base_offset * angular_offset)
            upper_half_rect = upper_half_rotated.get_rect(center=(screen_width // 2, upper_half_center_y))

            lower_half_rotated = pygame.transform.rotate(lower_half, -jaw_base_offset * angular_offset * 0.5)
            lower_half_rect = lower_half_rotated.get_rect(center=(screen_width // 2, lower_half_center_y))

            # Ensure halves remain aligned
            upper_half_rect.bottom = screen_height // 2
            lower_half_rect.top = screen_height // 2

            # Draw the upper and lower halves with angular displacement
            screen.blit(upper_half_rotated, (upper_half_rect.left, upper_half_rect.top))
            screen.blit(lower_half_rotated, (lower_half_rect.left, lower_half_rect.top))
    else:
        # Draw the halves in the correct position without rotation
        screen.blit(upper_half, (upper_half_rect.left, upper_half_rect.top))
        screen.blit(lower_half, (lower_half_rect.left, lower_half_rect.top))

    # Draw debug information if enabled
    if show_debug_info:
        debug_info = [
            f"Audio Level: {audio_level:.2f}",
            f"Jaw Offset: {jaw_base_offset}",
            f"Upper Half Pos: {upper_half_rect.topleft}",
            f"Lower Half Pos: {lower_half_rect.topleft}",
            f"Opening Side: {'Bottom' if opening_side == 1 else 'Top'}"
        ]

        for i, line in enumerate(debug_info):
            text_surface = font.render(line, True, (255, 255, 255))
            screen.blit(text_surface, (10, 10 + i * 30))

    # Update the screen
    pygame.display.flip()

    # Control the update frequency
    clock.tick(fps)

# Clean up resources
stream.stop_stream()
stream.close()
p.terminate()

pygame.quit()
sys.exit()
