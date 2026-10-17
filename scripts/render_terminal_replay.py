"""Render a captured CLI transcript as a GIF, with condensed playback timing.

Requires Pillow only for rendering; it is not a MiniAgent runtime dependency.
This reads existing output. It never calls a model or recreates tool results.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render(transcript, output, font_path):
    lines = transcript.read_text(encoding="utf-8").rstrip().splitlines()
    if not lines:
        raise ValueError("The transcript is empty")
    font = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 14)
    width = max(840, int(max(font.getlength(line) for line in lines)) + 48)
    height = len(lines) * 23 + 112
    # Reveal the original prompt, then each tool start, result and final answer.
    stops = {i for i, line in enumerate(lines) if "usage:" in line}
    stops.update(i + 1 for i, line in enumerate(lines)
                 if line.startswith(("  • ", "  done ", "  failed ")))
    stops.add(len(lines))
    frames = []
    for stop in sorted(stops - {0}):
        frame = Image.new("RGB", (width, height), "#111015")
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=14,
                               outline="#40363b", width=2)
        draw.text((24, 16), "MiniAgent / CLI transcript replay", font=small, fill="#ffae42")
        draw.line((24, 44, width - 24, 44), fill="#40363b")
        for index, line in enumerate(lines[:stop]):
            color = "#e8e1dc"
            if "usage:" in line or line.startswith(("┌", "│", "└")):
                color = "#aaa0a5"
            if line.startswith("  • "):
                color = "#8dd8e5"
            elif line.startswith("  done "):
                color = "#b8d78b"
            elif line.startswith("  failed "):
                color = "#ff815c"
            draw.text((24, 58 + index * 23), line, font=font, fill=color)
        draw.line((24, height - 40, width - 24, height - 40), fill="#40363b")
        draw.text((24, height - 29), "Recorded output / timing condensed", font=small, fill="#aaa0a5")
        frames.append(frame)
    durations = [650] * len(frames)
    durations[0], durations[-1] = 1800, 4500
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=1)
    print(f"Rendered {len(frames)} frames; {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", required=True, help="Path or name of a local monospace TTF")
    args = parser.parse_args()
    render(args.transcript, args.output, args.font)
