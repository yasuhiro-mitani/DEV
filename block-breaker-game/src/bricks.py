class Brick:
    def __init__(self, x, y, width, height):
        self.rect = (x, y, width, height)
        self.is_hit = False

    def draw(self, surface):
        if not self.is_hit:
            # Draw the brick on the given surface
            # This is a placeholder for the actual drawing code
            pass

    def hit(self):
        self.is_hit = True