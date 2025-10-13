import pygame
import sys
import pyaudio
import numpy as np
import math
import os
from collections import deque
from moviepy.editor import VideoFileClip
import threading
import random
from PIL import Image

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

class VideoBackground:
    def __init__(self, path, size):
        self.lock = threading.Lock()
        self.path = path  # Guardar la ruta del video
        self.size = size  # Guardar el tamaño
        self.initialize_video()
        print(f"✔ Video cargado: {os.path.basename(path)}")

    def initialize_video(self):
        try:
            # Cargar video sin redimensionar inicialmente
            self.clip = VideoFileClip(self.path)
            
            # Redimensionar
            self.clip = self.clip.resize(newsize=(
                int(self.size[0] * (self.size[1] / self.clip.size[1])),
                self.size[1]
            ))
            
            # Configurar generador de frames
            self.reset_frame_generator()
            self.surface = None
            self.playing = False
            self.audio_thread = None
        except Exception as e:
            print(f"✖ Error crítico: {str(e)}")
            raise

    def reset_frame_generator(self):
        self.frame_gen = self.clip.iter_frames(fps=self.clip.fps, dtype='uint8')

    def _play_audio(self):
        try:
            if hasattr(self.clip, 'audio') and self.clip.audio is not None:
                self.clip.audio.preview()
        except Exception as e:
            print(f"Error al reproducir audio: {e}")

    def start(self):
        with self.lock:
            if not self.playing:
                self.playing = True
                if hasattr(self.clip, 'audio') and self.clip.audio is not None:
                    if self.audio_thread and self.audio_thread.is_alive():
                        self.stop_audio()
                    self.audio_thread = threading.Thread(target=self._play_audio, daemon=True)
                    self.audio_thread.start()

    def stop(self):
        with self.lock:
            self.playing = False
            self.stop_audio()

    def stop_audio(self):
        # No hay forma directa de detener el audio de moviepy, pero podemos cerrar el clip
        if hasattr(self, 'clip') and hasattr(self.clip, 'audio') and self.clip.audio:
            self.clip.audio.close()

    def restart(self):
        self.stop()
        self.close()
        self.initialize_video()
        self.start()

    def update(self):
        if self.playing:
            try:
                frame = next(self.frame_gen)
                frame_surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
                self.surface = pygame.transform.scale(frame_surface, (self.size[0], self.size[1]))
            except StopIteration:
                # Reiniciar el video cuando termina
                self.restart()

    def draw(self, screen):
        if self.surface and self.playing:
            screen.blit(self.surface, (0, 0))

    def close(self):
        self.stop()
        if hasattr(self, 'clip'):
            self.clip.close()

class VideoManager:
    def __init__(self, video_folder="videos"):
        # Asegurar ruta absoluta y compatible con multiplataforma
        self.video_folder = os.path.abspath(video_folder)
        self.current_video = None
        self.available_videos = self._discover_videos()
        self._print_video_status()
        
    def _discover_videos(self):
        try:
            if not os.path.exists(self.video_folder):
                print(f"Creando directorio de videos: {self.video_folder}")
                os.makedirs(self.video_folder, exist_ok=True)
                return []
                
            videos = []
            valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
            
            for file in os.listdir(self.video_folder):
                full_path = os.path.join(self.video_folder, file)
                if file.lower().endswith(valid_extensions):
                    videos.append(full_path)
            
            return videos
        except Exception as e:
            print(f"Error al buscar videos: {e}")
            return []

    def _print_video_status(self):
        print("\n=== Estado de Videos ===")
        print(f"Directorio: {self.video_folder}")
        print(f"Videos encontrados ({len(self.available_videos)}):")
        for i, video in enumerate(self.available_videos, 1):
            print(f"{i}. {os.path.basename(video)}")
        print("=======================\n")
    
    def get_random_video(self):
        if not self.available_videos:
            return None
        return random.choice(self.available_videos)
    
    def play_random_video(self, size):
        if self.current_video:
            self.current_video.close()
            
        video_path = self.get_random_video()
        if video_path:
            try:
                print(f"Intentando cargar video: {os.path.basename(video_path)}")
                self.current_video = VideoBackground(video_path, size)
                self.current_video.start()
                return True
            except Exception as e:
                print(f"Error al cargar video {os.path.basename(video_path)}: {e}")
                return False
        else:
            print("No hay videos disponibles en la carpeta")
            return False
    
    def stop_current_video(self):
        if self.current_video:
            self.current_video.stop()
    
    def update(self):
        if self.current_video:
            self.current_video.update()
    
    def draw(self, screen):
        if self.current_video:
            self.current_video.draw(screen)
    
    def close(self):
        if self.current_video:
            self.current_video.close()

    def restart_current_video(self):
        if self.current_video:
            self.current_video.restart()
            return True
        return False

# Initialize Pygame with optimizations
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF)
pygame.display.set_caption("Ike-Tuber")

# Initialize video manager with debug info
print("\nInicializando gestor de videos...")
video_manager = VideoManager()
print("Gestor de videos listo\n")

# Color palette
DARK_GREEN = (10, 50, 10)
MEDIUM_GREEN = (30, 120, 30)
LIGHT_GREEN = (50, 255, 50)
DEBUG_COLOR = (200, 255, 200)

# Font system
font = pygame.font.SysFont('Arial', 24, bold=True)
large_font = pygame.font.SysFont('Arial', 48, bold=True)

def load_image_enhanced(path, scale=0.3):
    try:
        image = pygame.image.load(path).convert_alpha()
        if scale != 1.0:
            new_size = (int(image.get_width() * scale), int(image.get_height() * scale))
            return pygame.transform.smoothscale(image, new_size)
        return image
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        surf = pygame.Surface((200, 200), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 0, 0, 128), (100, 100), 100)
        return surf

# Load assets (scaled at 30%)
print("Cargando recursos...")
scale_factor = 0.3
try:
    upper_half = load_image_enhanced('images/upper_half.png', scale_factor)
    lower_half = load_image_enhanced('images/lower_half.png', scale_factor)
    idle_image = load_image_enhanced('images/idle.png', scale_factor)
    middle_finger_img = load_image_enhanced('images/middle_finger.png', scale_factor)  # Un poco más pequeño
    print("Recursos cargados correctamente\n")
except Exception as e:
    print(f"Error crítico al cargar recursos: {e}")
    sys.exit(1)

mouth_center_x = screen_width // 2
mouth_center_y = screen_height // 2

# Variables para el dedo medio
show_middle_finger = False
middle_finger_scale = 0.1
middle_finger_target_scale = 2.0
middle_finger_scale_speed = 3.0
middle_finger_pos = (mouth_center_x + 150, mouth_center_y + 100)  # Posición relativa a la boca

class AudioProcessor:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.p = pyaudio.PyAudio()
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            self.audio_active = True
            print("Micrófono inicializado correctamente")
        except Exception as e:
            print(f"No se pudo acceder al micrófono - usando audio simulado: {e}")
            self.audio_active = False
            self.sim_counter = 0
        
        self.history = deque(maxlen=30)
        self.fft_history = deque(maxlen=10)

    def get_audio_level(self):
        if self.audio_active:
            try:
                data = np.frombuffer(
                    self.stream.read(self.CHUNK, exception_on_overflow=False),
                    dtype=np.int16
                )
                level = np.abs(data).mean() / 32768
                fft = np.abs(np.fft.rfft(data)[:self.CHUNK//2])
                self.fft_history.append(fft)
                
                # Cálculos mejorados de frecuencias
                bass = np.mean(fft[:10]) / 100000
                mid = np.mean(fft[10:100]) / 50000
                treble = np.mean(fft[100:300]) / 20000
                
                self.history.append((level, bass, mid, treble))
                return level, bass, mid, treble
            except Exception as e:
                print(f"Error de audio: {e}")
                return 0, 0, 0, 0
        else:
            # Simulación más realista de audio
            self.sim_counter += 0.05
            sim_level = (math.sin(self.sim_counter) + 1) * 0.3 + 0.1
            sim_bass = (math.sin(self.sim_counter * 0.7) + 1) * 0.2 + 0.1
            sim_mid = (math.sin(self.sim_counter * 1.3) + 1) * 0.15 + 0.1
            sim_treble = (math.sin(self.sim_counter * 2.1) + 1) * 0.1 + 0.1
            return sim_level, sim_bass, sim_mid, sim_treble

print("Inicializando procesador de audio...")
audio_processor = AudioProcessor()

class AnimationSystem:
    def __init__(self):
        self.jaw_open = 0
        self.max_open = 100
        self.rotation_factor = 25
        self.head_bob = 0
        self.bob_speed = 2.5
        self.blink_timer = 0
        self.last_blink = 0
        self.blink_duration = 0.15
        self.blink_cooldown = 3.0
        self.current_expression = "neutral"
        self.expression_intensity = 0
        self.side_switch = False
        self.switch_timer = 0

    def update(self, dt, audio_data):
        level, bass, mid, treble = audio_data
        
        # Control de apertura de mandíbula con suavizado
        target_jaw = min(level * 25, 1.0)
        self.jaw_open += (target_jaw - self.jaw_open) * 0.3
        
        # Parpadeo natural
        self.blink_timer += dt
        if self.blink_timer - self.last_blink > self.blink_cooldown:
            self.last_blink = self.blink_timer
        
        # Movimiento de cabeza con el ritmo
        self.head_bob = math.sin(self.blink_timer * self.bob_speed) * 15 * (0.2 + level)
        
        # Cambio de lado periódico
        self.switch_timer += dt
        if self.switch_timer > 0.5:  # Cambia cada medio segundo
            self.side_switch = not self.side_switch
            self.switch_timer = 0
        
        # Expresiones faciales basadas en frecuencias
        if bass > 0.25:
            self.current_expression = "talking"
            self.expression_intensity = bass
        else:
            self.current_expression = "neutral"
            self.expression_intensity = 0

anim_system = AnimationSystem()

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.colors = [
            (255, 255, 200),  # Amarillo claro
            (200, 255, 200),  # Verde claro
            (255, 200, 200),  # Rojo claro
            (200, 200, 255)   # Azul claro
        ]

    def add_particle(self, x, y, audio_data):
        level, bass, _, _ = audio_data
        count = int(level * 10 + bass * 5)
        
        for _ in range(count):
            color = random.choice(self.colors)
            self.particles.append({
                'x': x + np.random.uniform(-30, 30),
                'y': y + np.random.uniform(-20, 20),
                'color': color,
                'size': np.random.uniform(1, 3 + bass * 5),
                'speed': np.random.uniform(0.5, 2 + level * 3),
                'angle': np.random.uniform(0, math.pi * 2),
                'life': np.random.uniform(0.5, 1.5),
                'max_life': 1.5
            })

    def update(self, dt):
        for p in self.particles:
            p['life'] -= dt
            p['x'] += math.cos(p['angle']) * p['speed'] * 10 * dt
            p['y'] += math.sin(p['angle']) * p['speed'] * 10 * dt
            p['y'] -= p['speed'] * 2 * dt  # Gravedad leve
            
        # Eliminar partículas muertas
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, surface):
        for p in sorted(self.particles, key=lambda x: x['y']):  # Ordenar para correcta superposición
            alpha = int(255 * (p['life'] / p['max_life']))
            size = int(p['size'] * (p['life'] / p['max_life'] * 0.5 + 0.5))
            
            if size > 0:
                surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*p['color'][:3], alpha), (size, size), size)
                surface.blit(surf, (int(p['x'] - size), int(p['y'] - size)))

particle_system = ParticleSystem()

class AudioVisualizer:
    def __init__(self):
        self.width = screen_width - 40
        self.height = 100
        self.x = 20
        self.y = screen_height - self.height - 20
        self.history = deque(maxlen=self.width)
        self.gradient = self._create_gradient()

    def _create_gradient(self):
        gradient = pygame.Surface((self.width, self.height))
        for y in range(self.height):
            # Gradiente vertical de oscuro a claro
            shade = int(10 + (y / self.height) * 40)
            pygame.draw.line(gradient, (shade, shade//2 + 20, shade), (0, y), (self.width, y))
        return gradient

    def update(self, audio_data):
        self.history.append(audio_data)

    def draw(self, surface):
        # Fondo con gradiente
        surface.blit(self.gradient, (self.x, self.y))
        pygame.draw.rect(surface, MEDIUM_GREEN, (self.x, self.y, self.width, self.height), 2)
        
        # Gráfico de onda principal
        if len(self.history) > 1:
            points = [
                (self.x + i * (self.width / len(self.history)),
                self.y + self.height - level * self.height * 0.8
            ) for i, (level, *_ ) in enumerate(self.history)]
            
            if len(points) > 1:
                pygame.draw.lines(surface, LIGHT_GREEN, False, points, 2)
        
        # Indicadores de frecuencia
        if len(self.history) > 0:
            _, bass, mid, treble = self.history[-1]
            
            # Bass (rojo)
            bass_height = bass * self.height
            pygame.draw.line(
                surface, (255, 100, 100), 
                (self.x + 20, self.y + self.height), 
                (self.x + 20, self.y + self.height - bass_height), 
                4
            )
            
            # Mid (verde)
            mid_height = mid * self.height
            pygame.draw.line(
                surface, (100, 255, 100), 
                (self.x + self.width//2, self.y + self.height), 
                (self.x + self.width//2, self.y + self.height - mid_height), 
                4
            )
            
            # Treble (azul)
            treble_height = treble * self.height
            pygame.draw.line(
                surface, (100, 100, 255), 
                (self.x + self.width - 20, self.y + self.height), 
                (self.x + self.width - 20, self.y + self.height - treble_height), 
                4
            )

audio_visualizer = AudioVisualizer()

def update_middle_finger(dt):
    global middle_finger_scale
    if show_middle_finger:
        # Efecto de zoom in
        if middle_finger_scale < middle_finger_target_scale:
            middle_finger_scale += dt * middle_finger_scale_speed
            if middle_finger_scale > middle_finger_target_scale:
                middle_finger_scale = middle_finger_target_scale
    else:
        # Efecto de zoom out al ocultar
        if middle_finger_scale > 0:
            middle_finger_scale -= dt * middle_finger_scale_speed * 2
            if middle_finger_scale < 0:
                middle_finger_scale = 0

# Configuración inicial
clock = pygame.time.Clock()
running = True
last_time = pygame.time.get_ticks() / 1000.0
show_debug = False
show_visualizer = True

# Variables para modo idle
idle_timeout = 5.0  # segundos sin sonido para activar idle
time_without_sound = 0.0
auto_idle_active = False
forced_idle = False

# Bucle principal mejorado
print("\nIniciando bucle principal...")
while running:
    current_time = pygame.time.get_ticks() / 1000.0
    dt = min(current_time - last_time, 0.033)  # Limitar dt para evitar saltos grandes
    last_time = current_time

    # Manejo de eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_d:
                show_debug = not show_debug
            elif event.key == pygame.K_v:
                show_visualizer = not show_visualizer
            elif event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_i:
                forced_idle = not forced_idle
                if forced_idle:
                    auto_idle_active = False
            elif event.key == pygame.K_z:  # Tecla Z para control de video
                if video_manager.current_video:
                    if video_manager.current_video.playing:
                        video_manager.stop_current_video()
                        print("Video detenido")
                    else:
                        # Reiniciar el video actual en lugar de cargar uno nuevo
                        video_manager.current_video.restart()
                        print("Video reiniciado")
                else:
                    # Si no hay video actual, cargar uno nuevo
                    if video_manager.play_random_video((screen_width, screen_height)):
                        print("Video iniciado")
                    else:
                        print("No hay videos disponibles o hubo un error")
            elif event.key == pygame.K_m:  # Tecla M para mostrar/ocultar dedo medio
                show_middle_finger = not show_middle_finger
                if show_middle_finger:
                    middle_finger_scale = 0.1  # Empieza pequeño para el efecto de zoom

    # Procesamiento de audio y actualizaciones
    audio_data = audio_processor.get_audio_level()
    anim_system.update(dt, audio_data)
    particle_system.update(dt)
    audio_visualizer.update(audio_data)
    video_manager.update()
    update_middle_finger(dt)

    # Lógica de idle automático
    audio_level = audio_data[0]
    sound_threshold = 0.05

    if audio_level < sound_threshold and not forced_idle and anim_system.jaw_open < 0.1:
        time_without_sound += dt
    else:
        time_without_sound = 0.0
        auto_idle_active = False

    if time_without_sound >= idle_timeout and not forced_idle:
        auto_idle_active = True

    # Generar partículas cuando hay sonido
    if anim_system.jaw_open > 0.1:
        particle_system.add_particle(
            mouth_center_x,
            mouth_center_y + anim_system.jaw_open * anim_system.max_open * 0.7,
            audio_data
        )

    # Dibujado
    # 1. Fondo (video o gradiente)
    if video_manager.current_video and video_manager.current_video.playing:
        video_manager.draw(screen)
    else:
        # Fondo gradiente alternativo
        for y in range(screen_height):
            factor = y / screen_height
            shade = int(10 + 20 * factor)
            pygame.draw.line(screen, (shade, shade//2 + 20, shade), (0, y), (screen_width, y))

    # 2. Boca/expresión
    jaw_offset = anim_system.jaw_open * anim_system.max_open
    rotation = anim_system.jaw_open * anim_system.rotation_factor

    if auto_idle_active or forced_idle:
        # Modo idle
        idle_rect = idle_image.get_rect(center=(mouth_center_x, mouth_center_y))
        screen.blit(idle_image, idle_rect)
    else:
        # Modo activo con animación
        upper_rotated = pygame.transform.rotate(
            upper_half,
            (-rotation if anim_system.side_switch else rotation) * 0.3
        )
        lower_rotated = pygame.transform.rotate(
            lower_half,
            (rotation if anim_system.side_switch else -rotation) * 0.7
        )

        upper_rect = upper_rotated.get_rect(
            midbottom=(mouth_center_x, mouth_center_y - jaw_offset * 0.3 + anim_system.head_bob)
        )
        lower_rect = lower_rotated.get_rect(
            midtop=(mouth_center_x, mouth_center_y + jaw_offset * 0.5 + anim_system.head_bob)
        )

        screen.blit(upper_rotated, upper_rect)
        screen.blit(lower_rotated, lower_rect)

    # 3. Dibujar dedo medio si está activo
    if middle_finger_scale > 0.01:
        scaled_finger = pygame.transform.smoothscale(
            middle_finger_img,
            (
                int(middle_finger_img.get_width() * middle_finger_scale),
                int(middle_finger_img.get_height() * middle_finger_scale)
            )
        )
        finger_rect = scaled_finger.get_rect(
            center=(middle_finger_pos[0] + math.sin(current_time * 5) * 10,  # Pequeño movimiento
            middle_finger_pos[1]
        ))
        screen.blit(scaled_finger, finger_rect)

    # 4. Partículas
    particle_system.draw(screen)

    # 5. Visualizador de audio
    if show_visualizer:
        audio_visualizer.draw(screen)

    # 6. Información de depuración
    if show_debug:
        debug_info = [
            f"FPS: {clock.get_fps():.1f}",
            f"Audio Level: {audio_data[0]:.2f}",
            f"Bass: {audio_data[1]:.2f} | Mid: {audio_data[2]:.2f} | Treble: {audio_data[3]:.2f}",
            f"Jaw Open: {anim_system.jaw_open*100:.0f}%",
            f"Expression: {anim_system.current_expression}",
            f"Particles: {len(particle_system.particles)}",
            f"Video: {'Playing' if video_manager.current_video and video_manager.current_video.playing else 'Stopped'}",
            f"Video Files: {len(video_manager.available_videos)}",
            f"[D] Toggle Debug | [V] Toggle Visualizer | [I] Toggle Idle | [Z] Toggle Video | [M] Toggle Middle Finger"
        ]
        
        for i, line in enumerate(debug_info):
            text = font.render(line, True, DEBUG_COLOR)
            screen.blit(text, (10, 10 + i * 25))

    pygame.display.flip()
    clock.tick(60)

# Limpieza al salir
print("\nCerrando aplicación...")
if audio_processor.audio_active:
    audio_processor.stream.stop_stream()
    audio_processor.stream.close()
audio_processor.p.terminate()
video_manager.close()
pygame.quit()
sys.exit()