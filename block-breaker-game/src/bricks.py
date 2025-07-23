class Brick:
    def __init__(self, x, y, width, height):
        self.rect = (x, y, width, height)
        self.is_hit = False

    def draw(self, surface):
        if not self.is_hit:
            import pygame
            pygame.draw.rect(surface, (255, 0, 0), self.rect)

    def hit(self):
        self.is_hit = True