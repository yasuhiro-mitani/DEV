class Ball:
    def __init__(self, x, y, radius, color):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.dx = 5  # Horizontal speed
        self.dy = -5  # Vertical speed

    def move(self):
        self.x += self.dx
        self.y += self.dy

    def draw(self, screen):
        import pygame
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

    def reset(self, x, y):
        self.x = x
        self.y = y
        self.dx = 5
        self.dy = -5