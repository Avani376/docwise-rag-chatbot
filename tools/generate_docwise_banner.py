"""Render the animated and static Docwise GitHub banner.

The banner uses only Pillow so the visual story and its technical labels remain
crisp, reproducible, and faithful to the actual Docwise RAG workflow.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 1280, 480
FRAME_COUNT = 40
FRAME_DURATION_MS = 360  # 14.4 seconds per loop
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

NAVY = (8, 13, 24)
SURFACE = (17, 24, 39)
CYAN = (56, 217, 249)
VIOLET = (155, 140, 255)
TEXT = (244, 247, 252)
MUTED = (148, 163, 184)
AMBER = (251, 191, 36)
ROSE = (251, 113, 133)

NODES = (
    (105, 252, 2.1), (172, 352, 1.7), (244, 226, 2.7), (314, 324, 1.8),
    (404, 245, 2.3), (472, 355, 1.6), (556, 225, 2.3), (631, 329, 1.9),
    (696, 188, 2.5), (796, 265, 1.8), (876, 350, 2.2), (961, 214, 2.1),
    (1056, 311, 1.7), (1160, 226, 2.4), (1218, 361, 1.5), (1182, 100, 1.7),
    (934, 88, 1.5), (760, 85, 2.0), (561, 100, 1.4), (395, 66, 1.5),
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/seguisb.ttf", "DejaVuSans-Bold.ttf")
        if bold
        else ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/DejaVuSans.ttf", "DejaVuSans.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = _font(54, bold=True)
FONT_TAGLINE = _font(25)
FONT_LABEL = _font(13, bold=True)
FONT_CARD_TITLE = _font(19, bold=True)
FONT_BODY = _font(16)
FONT_SMALL = _font(13)
FONT_TINY = _font(11, bold=True)


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _rgba(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, int(max(0, min(255, alpha * 255))))


def _rounded_panel(
    image: Image.Image,
    box: tuple[float, float, float, float],
    alpha: float,
    accent: tuple[int, int, int] = CYAN,
    radius: int = 18,
) -> None:
    if alpha <= 0:
        return
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=radius, fill=_rgba(SURFACE, 0.84 * alpha), outline=_rgba(accent, 0.62 * alpha), width=2)
    image.alpha_composite(layer)


def _glow_line(
    image: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    alpha: float,
    width: int = 2,
) -> None:
    if alpha <= 0:
        return
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.line(points, fill=_rgba(color, 0.45 * alpha), width=width * 4, joint="curve")
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)))
    top = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(top).line(points, fill=_rgba(color, alpha), width=width, joint="curve")
    image.alpha_composite(top)


def _glow_dot(
    image: Image.Image,
    point: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    alpha: float = 1.0,
) -> None:
    if alpha <= 0:
        return
    x, y = point
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((x - radius * 3, y - radius * 3, x + radius * 3, y + radius * 3), fill=_rgba(color, 0.36 * alpha))
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius * 2)))
    dot = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse((x - radius, y - radius, x + radius, y + radius), fill=_rgba(color, alpha))
    image.alpha_composite(dot)


def _text(image: Image.Image, position: tuple[float, float], value: str, font: ImageFont.ImageFont, color: tuple[int, int, int], alpha: float = 1.0, **kwargs: object) -> None:
    if alpha <= 0:
        return
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(position, value, font=font, fill=_rgba(color, alpha), **kwargs)
    image.alpha_composite(layer)


def _background() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (*NAVY, 255))
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            radial = max(0.0, 1.0 - math.hypot((x - 680) / 900, (y - 265) / 480))
            horizon = max(0.0, 1.0 - abs(y - 340) / 430)
            pixels[x, y] = (
                int(_lerp(7, 13, radial)),
                int(_lerp(12, 22, radial + 0.35 * horizon)),
                int(_lerp(23, 44, radial + 0.18 * horizon)),
                255,
            )

    grid = Image.new("RGBA", image.size, (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    for x in range(-120, WIDTH + 160, 70):
        grid_draw.line((x, 330, x + 110, HEIGHT), fill=(56, 217, 249, 13), width=1)
    for y in range(344, HEIGHT + 1, 30):
        grid_draw.line((0, y, WIDTH, y), fill=(155, 140, 255, 12), width=1)
    image.alpha_composite(grid)
    return image


BACKGROUND = _background()


def _stage_weight(progress: float, stage: int) -> float:
    phase = progress * 5.0
    distance = abs(phase - stage)
    distance = min(distance, 5.0 - distance)
    return _ease(1.0 - min(1.0, distance / 0.9))


def _draw_brand(image: Image.Image, progress: float) -> None:
    pulse = 0.72 + 0.28 * math.sin(progress * math.tau)
    _text(image, (56, 38), "DOCWISE", FONT_TITLE, TEXT)
    _text(image, (60, 99), "RETRIEVAL-AUGMENTED GENERATION", FONT_LABEL, CYAN, 0.9)
    _text(image, (60, 124), "Ask your PDFs. Get answers with evidence.", FONT_TAGLINE, TEXT, 0.94)
    _rounded_panel(image, (1014, 40, 1218, 75), 0.82, VIOLET, radius=16)
    _glow_dot(image, (1038, 58), 4 + pulse * 1.4, CYAN, 0.95)
    _text(image, (1052, 51), "EVIDENCE-FIRST RAG", FONT_TINY, TEXT, 0.9)


def _draw_particles(image: Image.Image, progress: float) -> None:
    for index, (x, y, radius) in enumerate(NODES):
        drift_x = math.sin(progress * math.tau + index * 1.9) * (7 + index % 3)
        drift_y = math.cos(progress * math.tau * 0.8 + index * 1.1) * (4 + index % 4)
        palette = (CYAN, VIOLET, AMBER)[index % 3]
        _glow_dot(image, (x + drift_x, y + drift_y), radius, palette, 0.32 + 0.22 * math.sin(progress * math.tau + index))


def _document_card(image: Image.Image, x: float, y: float, alpha: float, highlight: bool = False, scale: float = 1.0) -> None:
    width, height = 150 * scale, 190 * scale
    accent = CYAN if highlight else VIOLET
    _rounded_panel(image, (x, y, x + width, y + height), alpha, accent, radius=15)
    if alpha <= 0:
        return
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((x + 18 * scale, y + 19 * scale, x + 58 * scale, y + 68 * scale), radius=5, outline=_rgba(accent, alpha), width=2)
    draw.polygon(((x + 47 * scale, y + 19 * scale), (x + 58 * scale, y + 30 * scale), (x + 47 * scale, y + 30 * scale)), fill=_rgba(accent, 0.7 * alpha))
    for row, line_width in enumerate((75, 91, 67, 82, 58)):
        yy = y + (91 + row * 15) * scale
        draw.rounded_rectangle((x + 18 * scale, yy, x + (18 + line_width) * scale, yy + 5 * scale), radius=3, fill=_rgba(TEXT, 0.48 * alpha))
    image.alpha_composite(layer)


def _scene_document(image: Image.Image, progress: float, alpha: float) -> None:
    offset = _ease((progress * 5) % 1)
    _document_card(image, 78, 225, alpha * 0.38, scale=0.78)
    _document_card(image, 167, 203, alpha * 0.54, scale=0.88)
    x = _lerp(278, 470, offset)
    _document_card(image, x, _lerp(184, 166, offset), alpha, highlight=True, scale=1.02)
    _text(image, (x + 4, 379), "PDF DOCUMENT", FONT_LABEL, CYAN, alpha)
    _text(image, (x + 4, 401), "Northstar policy.pdf", FONT_SMALL, TEXT, alpha)
    _glow_line(image, [(x + 142, 274), (650, 274)], CYAN, alpha * 0.58, width=2)
    _glow_dot(image, (650, 274), 5, CYAN, alpha)


def _chunk_card(image: Image.Image, x: float, y: float, label: str, alpha: float, accent: tuple[int, int, int]) -> None:
    _rounded_panel(image, (x, y, x + 168, y + 58), alpha, accent, radius=13)
    _text(image, (x + 16, y + 12), label, FONT_TINY, accent, alpha)
    for line, width in enumerate((106, 126)):
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((x + 16, y + 31 + line * 10, x + 16 + width, y + 36 + line * 10), radius=2, fill=_rgba(TEXT, 0.46 * alpha))
        image.alpha_composite(layer)


def _scene_processing(image: Image.Image, progress: float, alpha: float) -> None:
    _document_card(image, 100, 213, alpha * 0.74, highlight=True, scale=0.78)
    labels = ("TEXT EXTRACTION", "CHUNKING", "EMBEDDING")
    cards = ((383, 202, CYAN), (538, 278, VIOLET), (685, 203, CYAN))
    for index, ((x, y, color), label) in enumerate(zip(cards, labels)):
        pulse = 0.72 + 0.28 * math.sin(progress * math.tau * 5 + index)
        _chunk_card(image, x, y, label, alpha * pulse, color)
        if index == 0:
            _glow_line(image, [(250, 287), (x - 18, y + 29)], CYAN, alpha * 0.68)
        else:
            prev_x, prev_y, _ = cards[index - 1]
            _glow_line(image, [(prev_x + 168, prev_y + 29), (x - 18, y + 29)], VIOLET if index == 1 else CYAN, alpha * 0.68)
    _text(image, (382, 179), "PDF → PAGE TEXT → PASSAGES → VECTORS", FONT_LABEL, MUTED, alpha)


def _scene_retrieval(image: Image.Image, progress: float, alpha: float) -> None:
    network = ((355, 275), (430, 215), (502, 304), (550, 225), (610, 293), (672, 217), (725, 278))
    links = ((0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 6), (5, 6))
    for start, end in links:
        _glow_line(image, [network[start], network[end]], CYAN if end in (3, 5) else VIOLET, alpha * 0.58)
    for index, point in enumerate(network):
        selected = index in (1, 3, 5)
        _glow_dot(image, point, 8 if selected else 5, CYAN if selected else VIOLET, alpha * (1 if selected else 0.56))
    _rounded_panel(image, (80, 212, 304, 324), alpha, VIOLET, radius=16)
    _text(image, (101, 230), "QUESTION", FONT_TINY, VIOLET, alpha)
    _text(image, (101, 256), "When does fall semester", FONT_BODY, TEXT, alpha)
    _text(image, (101, 278), "begin?", FONT_BODY, TEXT, alpha)
    _text(image, (750, 194), "SEMANTIC SEARCH", FONT_LABEL, CYAN, alpha)
    _text(image, (750, 222), "TOP-K RETRIEVAL", FONT_CARD_TITLE, TEXT, alpha)
    _text(image, (750, 251), "Relevant evidence illuminates.", FONT_SMALL, MUTED, alpha)
    for row, score in enumerate(("0.55", "0.47", "0.40")):
        y = 280 + row * 35
        _rounded_panel(image, (750, y, 1120, y + 27), alpha * (1 - row * 0.13), CYAN if row == 0 else VIOLET, radius=9)
        _text(image, (766, y + 6), f"northstar_student_policy.pdf · p. {1 if row < 2 else 2}", FONT_TINY, TEXT, alpha)
        _text(image, (1081, y + 6), score, FONT_TINY, CYAN, alpha)


def _scene_answer(image: Image.Image, progress: float, alpha: float) -> None:
    _chunk_card(image, 110, 230, "EVIDENCE · PAGE 1", alpha * 0.88, CYAN)
    _chunk_card(image, 276, 287, "RETRIEVED PASSAGE", alpha * 0.62, VIOLET)
    _glow_line(image, [(444, 259), (720, 250)], CYAN, alpha * 0.78, width=3)
    _glow_dot(image, (720, 250), 6, CYAN, alpha)
    _rounded_panel(image, (738, 166, 1200, 365), alpha, CYAN, radius=20)
    _text(image, (766, 188), "GROUNDED ANSWER", FONT_LABEL, CYAN, alpha)
    _text(image, (766, 219), "When does fall semester begin?", FONT_SMALL, MUTED, alpha)
    _text(image, (766, 251), "The fall semester begins", FONT_CARD_TITLE, TEXT, alpha)
    _text(image, (766, 279), "September 3. [1]", FONT_CARD_TITLE, TEXT, alpha)
    _rounded_panel(image, (766, 315, 1169, 347), alpha * 0.9, VIOLET, radius=10)
    _text(image, (781, 323), "SOURCE  northstar_student_policy.pdf  ·  PAGE 01  ·  [1]", FONT_TINY, TEXT, alpha)


def _scene_abstention(image: Image.Image, progress: float, alpha: float) -> None:
    _rounded_panel(image, (118, 210, 620, 348), alpha * 0.72, VIOLET, radius=18)
    _text(image, (145, 232), "QUESTION", FONT_LABEL, VIOLET, alpha)
    _text(image, (145, 261), "What are the campus gym's", FONT_CARD_TITLE, TEXT, alpha)
    _text(image, (145, 287), "weekend opening times?", FONT_CARD_TITLE, TEXT, alpha)
    _glow_line(image, [(630, 280), (742, 280)], VIOLET, alpha * 0.46)
    _rounded_panel(image, (758, 194, 1175, 351), alpha, ROSE, radius=20)
    _glow_dot(image, (792, 229), 7, AMBER, alpha)
    _text(image, (817, 218), "NO SUPPORTED ANSWER", FONT_CARD_TITLE, TEXT, alpha)
    _text(image, (786, 264), "Insufficient evidence found", FONT_BODY, MUTED, alpha)
    _text(image, (786, 289), "in the indexed document.", FONT_BODY, MUTED, alpha)
    _text(image, (786, 321), "Responsible AI over confident guesses.", FONT_SMALL, VIOLET, alpha)


def render_frame(progress: float) -> Image.Image:
    image = BACKGROUND.copy()
    _draw_particles(image, progress)
    _draw_brand(image, progress)
    _scene_document(image, progress, _stage_weight(progress, 0))
    _scene_processing(image, progress, _stage_weight(progress, 1))
    _scene_retrieval(image, progress, _stage_weight(progress, 2))
    _scene_answer(image, progress, _stage_weight(progress, 3))
    _scene_abstention(image, progress, _stage_weight(progress, 4))
    return image


def _quantize(frames: list[Image.Image]) -> list[Image.Image]:
    palette = frames[0].convert("RGB").quantize(colors=112, method=Image.Quantize.MEDIANCUT)
    return [frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    frames = [render_frame(index / FRAME_COUNT) for index in range(FRAME_COUNT)]
    static = render_frame(0.67).convert("RGB")
    static.save(ASSETS / "docwise-banner.png", optimize=True, quality=92)
    quantized = _quantize(frames)
    quantized[0].save(
        ASSETS / "docwise-banner.gif",
        save_all=True,
        append_images=quantized[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        disposal=2,
        optimize=True,
    )


if __name__ == "__main__":
    main()
