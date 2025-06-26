import pygame
from game import Game

def main():
    pygame.init()
    game = Game()
    game.start_game()

    while True:
        game.update()
        game.draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

if __name__ == "__main__":
    main()