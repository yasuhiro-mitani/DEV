def check_collision(rect1, rect2):
    return rect1.colliderect(rect2)

def draw_text(surface, text, position, font, color=(255, 255, 255)):
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, position)

def reset_game_state():
    # Reset any game state variables here
    pass

def load_image(file_path):
    # Load an image from the given file path
    return pygame.image.load(file_path)