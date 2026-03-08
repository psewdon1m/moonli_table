from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image


def _load_source_image(source_image_uri: str | None) -> Image.Image:
    if not source_image_uri:
        return Image.new("RGBA", (512, 512), color=(245, 245, 245, 255))
    parsed = urlparse(source_image_uri)
    if parsed.scheme in {"http", "https"}:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(source_image_uri)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")

    # API can pass data URI path like "/data/runtime_cache/..." while inside containers
    # real files are mounted under "/app/data/...".
    if source_image_uri.startswith("/data/"):
        path = Path("/app") / source_image_uri.lstrip("/")
    elif source_image_uri.startswith("data/"):
        path = Path("/app") / source_image_uri
    else:
        path = Path(source_image_uri)
    if not path.exists():
        raise FileNotFoundError(f"Source image not found: {path}")
    return Image.open(path).convert("RGBA")


def prepare_vector_source(
    session_dir: Path,
    candidate_id: str,
    source_image_uri: str | None,
) -> dict[str, str]:
    source_image = _load_source_image(source_image_uri)
    prepare_dir = session_dir / f"base_{candidate_id}"
    prepare_dir.mkdir(parents=True, exist_ok=True)
    prepared_path = prepare_dir / "prepared_rgba.png"
    source_image.save(prepared_path)
    return {"prepared_image_path": str(prepared_path)}


def _build_run_rects(
    pixels: list[tuple[int, int, int]],
    width: int,
    height: int,
    target_color: tuple[int, int, int],
    alpha_mask: list[bool] | None = None,
) -> list[tuple[int, int, int]]:
    rects: list[tuple[int, int, int]] = []
    for y in range(height):
        row_start = y * width
        x = 0
        while x < width:
            color = pixels[row_start + x]
            if color != target_color or (alpha_mask is not None and not alpha_mask[row_start + x]):
                x += 1
                continue
            start_x = x
            x += 1
            while x < width and pixels[row_start + x] == target_color and (
                alpha_mask is None or alpha_mask[row_start + x]
            ):
                x += 1
            rects.append((start_x, y, x - start_x))
    return rects


def _render_layer_svg(rects: list[tuple[int, int, int]], color: str, width: int, height: int) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    ]
    for x, y, w in rects:
        lines.append(f'  <path d="M{x} {y}h{w}v1h-{w}z" fill="{color}" />')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _render_master_svg(all_layers: list[tuple[str, list[tuple[int, int, int]]]], width: int, height: int) -> str:
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    ]
    for color, rects in all_layers:
        lines.append(f'  <g id="{color[1:].lower()}">')
        for x, y, w in rects:
            lines.append(f'    <path d="M{x} {y}h{w}v1h-{w}z" fill="{color}" />')
        lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def build_vector_assets(
    pack_dir: Path,
    candidate_id: str,
    palette: list[str],
    source_image_uri: str | None = None,
) -> dict:
    _ = candidate_id

    vector_dir = pack_dir / "vector"
    layer_dir = vector_dir / "layers"
    layer_dir.mkdir(parents=True, exist_ok=True)

    if not source_image_uri:
        width, height = 480, 480
        layer_entries: list[tuple[str, list[tuple[int, int, int]]]] = []
        color_layers: list[dict[str, str]] = []
        color_count = max(1, len(palette))
        band_width = max(1, width // color_count)
        for idx, color in enumerate(palette):
            x0 = idx * band_width
            x1 = width if idx == color_count - 1 else min(width, (idx + 1) * band_width)
            rects = [(x0, y, max(1, x1 - x0)) for y in range(height)]
            layer_svg = _render_layer_svg(rects=rects, color=color, width=width, height=height)
            layer_name = f"{color[1:].lower()}.svg"
            (layer_dir / layer_name).write_text(layer_svg, encoding="utf-8")
            layer_entries.append((color, rects))
            color_layers.append({"color": color, "path": f"vector/layers/{layer_name}"})
        master_svg = _render_master_svg(all_layers=layer_entries, width=width, height=height)
        (vector_dir / "master.svg").write_text(master_svg, encoding="utf-8")
        return {
            "master_svg": "vector/master.svg",
            "color_layers": color_layers,
        }

    source_image = _load_source_image(source_image_uri)
    alpha_channel = source_image.getchannel("A")
    alpha_values = list(alpha_channel.getdata())
    alpha_mask = [a > 8 for a in alpha_values]
    rgb_image = source_image.convert("RGB")
    width, height = rgb_image.size
    pixels = list(rgb_image.getdata())

    # Preserve original generated colors (no palette recoloring).
    color_order: list[tuple[int, int, int]] = []
    seen_colors: set[tuple[int, int, int]] = set()
    for idx, color in enumerate(pixels):
        if not alpha_mask[idx]:
            continue
        if color in seen_colors:
            continue
        seen_colors.add(color)
        color_order.append(color)

    layer_entries: list[tuple[str, list[tuple[int, int, int]]]] = []
    color_layers: list[dict[str, str]] = []
    for color_rgb in color_order:
        color = "#{:02X}{:02X}{:02X}".format(*color_rgb)
        rects = _build_run_rects(
            pixels=pixels,
            width=width,
            height=height,
            target_color=color_rgb,
            alpha_mask=alpha_mask,
        )
        if not rects:
            continue
        layer_svg = _render_layer_svg(rects=rects, color=color, width=width, height=height)
        layer_name = f"{color[1:].lower()}.svg"
        (layer_dir / layer_name).write_text(layer_svg, encoding="utf-8")
        layer_entries.append((color, rects))
        color_layers.append({"color": color, "path": f"vector/layers/{layer_name}"})

    master_svg = _render_master_svg(all_layers=layer_entries, width=width, height=height)
    (vector_dir / "master.svg").write_text(master_svg, encoding="utf-8")

    return {
        "master_svg": "vector/master.svg",
        "color_layers": color_layers,
    }
