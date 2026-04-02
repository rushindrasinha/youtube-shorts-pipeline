#!/usr/bin/env python3
"""Generate cinematic .cube LUT files for video post-processing."""

import sys
from pathlib import Path

LUT_SIZE = 17  # 17³ = 4913 entries — good balance of quality vs file size


def clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def write_lut(path: Path, title: str, transform):
    """Write a .cube LUT file with the given color transform function."""
    with open(path, "w") as f:
        f.write(f"TITLE \"{title}\"\n")
        f.write(f"LUT_SIZE {LUT_SIZE}\n")
        f.write(f"DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write(f"DOMAIN_MAX 1.0 1.0 1.0\n\n")
        for bi in range(LUT_SIZE):
            for gi in range(LUT_SIZE):
                for ri in range(LUT_SIZE):
                    r = ri / (LUT_SIZE - 1)
                    g = gi / (LUT_SIZE - 1)
                    b = bi / (LUT_SIZE - 1)
                    nr, ng, nb = transform(r, g, b)
                    f.write(f"{clamp(nr):.6f} {clamp(ng):.6f} {clamp(nb):.6f}\n")
    print(f"  Generated: {path.name}")


def warm_cinematic(r, g, b):
    """Warm cinematic look — orange midtones, slightly crushed blacks."""
    # Lift shadows slightly, add warmth
    r = r * 1.05 + 0.01
    g = g * 1.00
    b = b * 0.92
    # Slight S-curve for contrast (clamp before pow to avoid complex)
    r = max(0.0, r) ** 0.95
    g = max(0.0, g) ** 0.98
    b = max(0.0, b) ** 1.05
    return r, g, b


def cool_tech(r, g, b):
    """Cool tech look — teal highlights, blue shadows."""
    r = r * 0.92
    g = g * 1.02 + 0.01
    b = b * 1.08 + 0.02
    # Slight desaturation
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    r = r * 0.85 + luma * 0.15
    g = g * 0.85 + luma * 0.15
    b = b * 0.85 + luma * 0.15
    return r, g, b


def dark_moody(r, g, b):
    """Dark moody look — crushed blacks, desaturated, slight teal."""
    # Crush blacks
    r = max(0, r - 0.03) * 0.95
    g = max(0, g - 0.03) * 0.95
    b = max(0, b - 0.02) * 0.98
    # Desaturate
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    r = r * 0.7 + luma * 0.3
    g = g * 0.7 + luma * 0.3
    b = b * 0.7 + luma * 0.3
    # Slight teal in shadows
    if luma < 0.3:
        g += 0.02
        b += 0.03
    return r, g, b


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    write_lut(out_dir / "warm_cinematic.cube", "Warm Cinematic", warm_cinematic)
    write_lut(out_dir / "cool_tech.cube", "Cool Tech", cool_tech)
    write_lut(out_dir / "dark_moody.cube", "Dark Moody", dark_moody)
    print("  Done!")
