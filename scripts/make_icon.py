#!/usr/bin/env python3
"""Install the app icon from the approved artwork.

Reads the artwork as delivered, kept unmodified in docs/branding/:

    NogaiKeyboard_AppIcon_1024.png    if present (a 1024 px original), otherwise
    NogaiKeyboard_AppIcon_1254.webp   the copy the artwork arrived as (1254 × 1254)

and writes into Assets.xcassets:

    AppIcon.appiconset/AppIcon-1024.png   1024 × 1024, opaque RGB, square
    AppLogo.imageset/AppLogo.png          512 × 512, the logo on the app's screen

Needs Pillow:

    python3 scripts/make_icon.py

The artwork is not redrawn: no pixel is repainted and nothing is cropped. A
1024 px source is only re-encoded as PNG; the 1254 px WebP is scaled down to
1024 px (Lanczos), the one size iOS takes. The script checks what iOS
requires of an app icon and stops if a check fails: a square source, no
transparency, and a full-bleed square. Full bleed here means that each
corner carries the colour of the field 24 px inside it (no pre-rounded
corners) and that the outer 8 px hold no pixel of another colour than the
field (no margin, outline or shadow).
"""
import os
import sys

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDING = os.path.join(REPO, "docs", "branding")
SOURCES = ["NogaiKeyboard_AppIcon_1024.png", "NogaiKeyboard_AppIcon_1254.webp"]
ASSETS = os.path.join(REPO, "NogaiKeyboard", "NogaiKeyboard", "Assets.xcassets")
SIZE = 1024
BORDER = 8        # px from each edge that are checked
REFERENCE = 24    # px inward from a corner where the field colour is sampled
TOLERANCE = 40    # summed RGB difference that counts as another colour


def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def main():
    path = next((p for p in (os.path.join(BRANDING, n) for n in SOURCES) if os.path.exists(p)), None)
    if path is None:
        sys.exit("error: no artwork in docs/branding/ (expected " + " or ".join(SOURCES) + ")")
    source = Image.open(path)
    if source.size[0] != source.size[1] or source.size[0] < SIZE:
        sys.exit(f"error: the source is {source.size}, expected a square of {SIZE} px or more")
    if "A" in source.getbands() and source.getchannel("A").getextrema()[0] < 255:
        sys.exit("error: the source has transparent pixels; an app icon must be opaque")
    img = source.convert("RGB")
    scaled = img.size != (SIZE, SIZE)
    if scaled:
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
    px = img.load()

    last = SIZE - 1
    field = px[REFERENCE, REFERENCE]
    for (x, y), (ix, iy) in {(0, 0): (REFERENCE, REFERENCE), (last, 0): (last - REFERENCE, REFERENCE),
                             (0, last): (REFERENCE, last - REFERENCE),
                             (last, last): (last - REFERENCE, last - REFERENCE)}.items():
        if distance(px[x, y], px[ix, iy]) > TOLERANCE:
            sys.exit(f"error: the corner at ({x}, {y}) is not the colour of its field "
                     "(pre-rounded corners?); the artwork must be a full-bleed square")
    other = sum(1 for y in range(SIZE) for x in range(SIZE)
                if min(x, y, last - x, last - y) < BORDER and distance(px[x, y], field) > TOLERANCE)
    if other:
        sys.exit(f"error: {other} pixels in the outer {BORDER} px are not the colour of the field "
                 "(a margin, an outline or a shadow?); the artwork must be full bleed")

    img.save(os.path.join(ASSETS, "AppIcon.appiconset", "AppIcon-1024.png"), "PNG", optimize=True)
    img.resize((512, 512), Image.LANCZOS).save(os.path.join(ASSETS, "AppLogo.imageset", "AppLogo.png"),
                                               "PNG", optimize=True)
    corners = " ".join("#%02X%02X%02X" % px[x, y] for x, y in ((0, 0), (last, 0), (0, last), (last, last)))
    print(f"icon installed from {os.path.basename(path)} ({source.size[0]} × {source.size[1]}"
          f"{', scaled to 1024' if scaled else ''}): {SIZE} × {SIZE} RGB PNG, no alpha, full bleed, "
          f"field #%02X%02X%02X, corner colours {corners}" % field)


if __name__ == "__main__":
    main()
