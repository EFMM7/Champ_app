"""Génère les icônes de l'app (192x192 et 512x512) pour le manifest PWA."""

from PIL import Image, ImageDraw, ImageFont

SOIL_DARK = (28, 23, 16)
HEALTHY = (111, 160, 89)
STRESS = (217, 164, 65)
PARCHMENT = (237, 230, 214)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), SOIL_DARK)
    draw = ImageDraw.Draw(img)

    # coins arrondis façon icône d'app
    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)

    # petite grille de 3x3 "zones" colorées, rappel direct du concept de
    # l'app (segmentation du champ), plutôt qu'un pictogramme générique
    pad = size * 0.16
    cell = (size - 2 * pad) / 3
    gap = size * 0.02
    colors = [
        HEALTHY, HEALTHY, STRESS,
        HEALTHY, STRESS, HEALTHY,
        STRESS, HEALTHY, HEALTHY,
    ]
    for i in range(3):
        for j in range(3):
            x0 = pad + j * cell + gap / 2
            y0 = pad + i * cell + gap / 2
            x1 = x0 + cell - gap
            y1 = y0 + cell - gap
            draw.rounded_rectangle([x0, y0, x1, y1], radius=size * 0.03, fill=colors[i * 3 + j])

    out = Image.new("RGBA", (size, size))
    out.paste(img, (0, 0))
    out.putalpha(mask)
    return out


for size in (192, 512):
    icon = make_icon(size)
    icon.save(f"/home/claude/champ_app/static/icon-{size}.png")
    print(f"icon-{size}.png généré")
