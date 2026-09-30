"""Neon Pac-Man — entry point."""

import pygame


def main() -> None:
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("PAC-MAN")

    from pacman.app import App
    from pacman.config import ASSETS
    from pacman.scenes.menu import MenuScene

    pygame.display.set_icon(pygame.image.load(str(ASSETS / "images" / "ico.png")))
    app = App()
    app.push(MenuScene(app))
    app.run()


if __name__ == "__main__":
    main()
