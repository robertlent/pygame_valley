import pygame
from sys import exit
from settings import *
from level import Level


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pygame Valley")
        self.clock = pygame.time.Clock()
        self.level = Level()

        self.background_music = pygame.mixer.Sound('audio/music.mp3')
        self.background_music.set_volume(.04)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

            dt = self.clock.tick() / 1000
            self.level.run(dt)

            self.background_music.play(loops=-1)

            pygame.display.update()


if __name__ == '__main__':
    game = Game()
    game.run()
