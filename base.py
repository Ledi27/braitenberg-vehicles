import pygame
import math

pygame.init()

# Setup Pygame window
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vehicles")

# Setup clock for controlling frame rate
clock = pygame.time.Clock()
fps = 60

# Setup font for debug info
font = pygame.font.SysFont("consolas", 16)


# Vehicle Two
class VehicleTwo:
    def __init__(self, x, y, radius=20, heading=0):
        # Vehicle state
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading

        # Sensor configuration
        self.sensor_offset_angle = math.radians(30)
        self.sensor_dist = self.radius

    # Calculate sensor positions based on vehicle position and heading
    def _sensor_positions(self):
        angle = self.sensor_offset_angle
        distance = self.sensor_dist

        # Calculate x and y relative to vehicle center
        left_local_x = math.cos(+angle) * distance
        left_local_y = math.sin(+angle) * distance
        right_local_x = math.cos(-angle) * distance
        right_local_y = math.sin(-angle) * distance

        # Calculate x and y relative to world coordinates (of vehicle)
        cos_heading = math.cos(self.heading)
        sin_heading = math.sin(self.heading)

        left_world_x = self.x + cos_heading * left_local_x - sin_heading * left_local_y
        left_world_y = self.y + sin_heading * left_local_x + cos_heading * left_local_y
        right_world_x = (
            self.x + cos_heading * right_local_x - sin_heading * right_local_y
        )
        right_world_y = (
            self.y + sin_heading * right_local_x + cos_heading * right_local_y
        )

        # Return sensor positions
        left_sensor_position = (left_world_x, left_world_y)
        right_sensor_position = (right_world_x, right_world_y)
        return left_sensor_position, right_sensor_position

    # Calculate intensity value of a particular source at a given point
    def _intensity_at(self, point_x, point_y, light_x, light_y):
        # EDIT this to change how intensity is calculated such as using inverse-square law
        # When using multiple sources, consider adding a new function to
        # aggregate intensities and if needed normalize them
        return 1.0

    # Update sensor intensities based on light position(s)
    def update(self, light_pos):
        # Get sensor positions
        left_sensor, right_sensor = self._sensor_positions()

        # Calculate intensities at each sensor
        # Update this section to handle multiple light sources if needed
        self.intensity_left = self._intensity_at(
            left_sensor[0], left_sensor[1], light_pos[0], light_pos[1]
        )
        self.intensity_right = self._intensity_at(
            right_sensor[0], right_sensor[1], light_pos[0], light_pos[1]
        )
        left_motor_speed = (
            1  # EDIT this value to set left motor speed based on intensity
        )
        right_motor_speed = (
            1  # EDIT this value to set right motor speed based on intensity
        )

        forward_speed = (
            left_motor_speed * right_motor_speed
        )  # EDIT this value to set forward speed based on motor speeds
        turning_rate = 0  # EDIT this value to set turning rate based on motor speeds

        # Update vehicle position and heading based on calculated speed and turning rate
        self.heading += turning_rate
        self.x += forward_speed * math.cos(self.heading)
        self.y += forward_speed * math.sin(self.heading)

        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surface):
        pygame.draw.circle(
            surface, (0, 0, 255), (int(self.x), int(self.y)), self.radius
        )
        pygame.draw.circle(
            surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2
        )

        left_sensor, right_sensor = self._sensor_positions()
        pygame.draw.circle(
            surface, (255, 0, 0), (int(left_sensor[0]), int(left_sensor[1])), 5
        )
        pygame.draw.circle(
            surface, (255, 0, 0), (int(right_sensor[0]), int(right_sensor[1])), 5
        )

        # Optionally draw debug info
        if font:
            surface.blit(
                font.render(
                    "Speed=xxx Turning=xxx",
                    True,
                    (0, 0, 0),
                ),
                (10, 10),
            )
            surface.blit(
                font.render(
                    "Left=xxx Right=xxx",
                    True,
                    (0, 0, 0),
                ),
                (10, 30),
            )


# Light source
# COPY OR EXTEND this to support multiple source types if needed
class Light:
    def __init__(self, x, y, radius=10):
        self.x, self.y = x, y
        self.radius = radius

    def move_light(self, new_position):
        self.x, self.y = new_position

    def pos(self):
        return (self.x, self.y)

    def draw(self, surface):
        pygame.draw.circle(
            surface, (255, 255, 0), (int(self.x), int(self.y)), self.radius
        )
        pygame.draw.circle(
            surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2
        )


# CREATE instances of vehicles and light sources
# ADJUST as needed to create multiple vehicles or lights
light = Light(WIDTH // 2, HEIGHT // 2, radius=20)
vehicle = VehicleTwo(WIDTH // 2 - 100, HEIGHT // 2, radius=20)

running = True
while running:
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # OPTIONAL functionality to move light with mouse
        # If needed, extend this to handle multiple lights
        if event.type == pygame.MOUSEBUTTONDOWN:
            light.move_light(event.pos)

    # Draw light source(s)
    light.draw(screen)

    # Update and draw vehicle(s)
    # EDIT the update method to pass multiple light positions if needed
    vehicle.update(light.pos())
    vehicle.draw(screen)

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()