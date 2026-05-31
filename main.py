#!/usr/bin/env python3
"""
8-Bit Hearts of Iron 4 Style Strategy Game
Main entry point - launches the game.
"""

import sys
import pygame
from src.game import Game
from src.renderer import Renderer


def main():
    """Main entry point for the 8-bit strategy game."""
    pygame.init()
    pygame.display.set_caption("8-Bit Grand Strategy")

    # Screen dimensions (256x224 - NES resolution scaled up)
    SCALE = 3
    NATIVE_W, NATIVE_H = 256, 224
    SCREEN_W, SCREEN_H = NATIVE_W * SCALE, NATIVE_H * SCALE

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    native_surface = pygame.Surface((NATIVE_W, NATIVE_H))

    clock = pygame.time.Clock()
    FPS = 60

    renderer = Renderer(native_surface)
    game = Game()
    game.new_game()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # delta time in seconds

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    game.handle_keydown(event.key, event.mod)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Scale mouse coords to native resolution
                mx = event.pos[0] // SCALE
                my = event.pos[1] // SCALE
                game.handle_click(mx, my, event.button)

        # Update game state
        game.update(dt)

        # Render
        renderer.render(game)

        # Scale to screen
        scaled = pygame.transform.scale(native_surface, (SCREEN_W, SCREEN_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
