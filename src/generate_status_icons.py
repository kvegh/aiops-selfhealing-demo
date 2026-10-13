"""Generate the native Zabbix map status icons using only Python's stdlib."""

from pathlib import Path
import struct
import zlib


ASSETS = Path(__file__).resolve().parents[1] / "assets" / "zabbix"
SIZE = 256
STATES = {
    "healthy": ((34, 153, 84), [(64, 132, 110, 178), (110, 178, 195, 80)]),
    "problem": ((204, 0, 0), [(80, 80, 176, 176), (176, 80, 80, 176)]),
    "disabled": ((112, 119, 126), [(101, 80, 101, 176), (155, 80, 155, 176)]),
}


def distance_squared(x, y, segment):
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    position = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return (x - x1 - position * dx) ** 2 + (y - y1 - position * dy) ** 2


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def render(color, segments):
    rows = bytearray()
    for y in range(SIZE):
        rows.append(0)  # PNG filter: none.
        for x in range(SIZE):
            rgba = [0, 0, 0, 0]
            for dx, dy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
                px, py = x + dx, y + dy
                if (px - 128) ** 2 + (py - 128) ** 2 > 120 ** 2:
                    continue
                pixel = (255, 255, 255) if any(
                    distance_squared(px, py, line) <= 10 ** 2 for line in segments
                ) else color
                for channel, value in enumerate((*pixel, 255)):
                    rgba[channel] += value
            # Convert supersampled premultiplied RGB back to straight alpha.
            alpha = rgba[3]
            rows.extend([round(v * 255 / alpha) if alpha else 0 for v in rgba[:3]])
            rows.append(round(alpha / 4))
    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, (color, segments) in STATES.items():
        (ASSETS / f"website-{name}.png").write_bytes(render(color, segments))
        paths = "\n".join(
            f'<path d="M{x1} {y1} L{x2} {y2}"/>' for x1, y1, x2, y2 in segments
        )
        fill = "#{:02x}{:02x}{:02x}".format(*color)
        (ASSETS / f"website-{name}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}">\n'
            f'<circle cx="128" cy="128" r="120" fill="{fill}"/>\n'
            f'<g fill="none" stroke="white" stroke-width="20" stroke-linecap="round">\n'
            f'{paths}\n</g>\n</svg>\n'
        )
        print(f"Generated website-{name}.png and .svg")


if __name__ == "__main__":
    main()
