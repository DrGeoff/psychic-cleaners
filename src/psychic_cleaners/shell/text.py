"""Font caching and text drawing helpers."""

import pygame


class TextRenderer:
    """Renders text using the default pygame font, cached per point size."""

    def __init__(self) -> None:
        self._fonts: dict[int, pygame.font.Font] = {}

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            if not pygame.font.get_init():
                pygame.font.init()
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def draw(
        self,
        surface: pygame.Surface,
        message: str,
        pos: tuple[int, int],
        size: int = 16,
        color: tuple[int, int, int] = (230, 230, 230),
    ) -> None:
        rendered = self._font(size).render(message, True, color)
        surface.blit(rendered, pos)
