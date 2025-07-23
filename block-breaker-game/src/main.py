import pygame
from game import Game

def main():
    pygame.init()
    game = Game()
    game.start_game()

    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
        
        game.update()
        game.draw()
    
    pygame.quit()

if __name__ == "__main__":
    main()