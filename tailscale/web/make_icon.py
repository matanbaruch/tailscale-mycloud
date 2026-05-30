#!/usr/bin/env python3
"""Generate the app icon (128x128 PNG) using only the Python standard library.

A dark tile with a 3x3 grid of light dots — a simple, non-trademarked nod to a
mesh network. Run: ``python3 make_icon.py [out.png]``.
"""

import struct
import sys
import zlib

WIDTH = HEIGHT = 128
BG = (38, 40, 48)        # dark slate
DOT = (245, 246, 250)    # near-white


def _png_chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def make_png(width, height, pixels):
    """Encode an RGB pixel list (length width*height) as PNG bytes."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None) for this scanline
        for x in range(width):
            raw += bytes(pixels[y * width + x])
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit, color type 2 (RGB)
    idat = zlib.compress(bytes(raw), 9)
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


def render():
    px = [BG] * (WIDTH * HEIGHT)
    centers = (32, 64, 96)
    radius = 14
    r2 = radius * radius
    for cy in centers:
        for cx in centers:
            for y in range(cy - radius, cy + radius + 1):
                for x in range(cx - radius, cx + radius + 1):
                    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                        dx, dy = x - cx, y - cy
                        if dx * dx + dy * dy <= r2:
                            px[y * WIDTH + x] = DOT
    return px


def main(path):
    with open(path, "wb") as fh:
        fh.write(make_png(WIDTH, HEIGHT, render()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tailscale.png")
