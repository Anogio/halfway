from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageFilter


BASE = 1024
PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"


COLORS = {
    "navy": (25, 51, 78),
    "navy_deep": (18, 39, 61),
    "teal": (31, 145, 130),
    "teal_bright": (51, 181, 164),
    "cream": (255, 247, 231),
    "paper": (243, 239, 229),
    "gold": (245, 191, 74),
    "amber": (236, 170, 56),
    "coral": (209, 79, 42),
    "pin_shadow": (18, 39, 61, 115),
    "tile_shadow": (12, 24, 36, 72),
    "route_shadow": (17, 34, 52, 86),
}


ROUTES = (
    {
        "start": (286, 332),
        "control": (392, 372),
        "end": (512, 420),
        "node_fill": (31, 145, 130),
    },
    {
        "start": (746, 298),
        "control": (640, 356),
        "end": (512, 420),
        "node_fill": (209, 79, 42),
    },
    {
        "start": (282, 636),
        "control": (382, 534),
        "end": (512, 420),
        "node_fill": (245, 191, 74),
    },
)


PIN_PATH = [
    ("M", (512, 838)),
    ("C", (404, 694), (334, 586), (334, 438)),
    ("C", (334, 302), (414, 220), (512, 220)),
    ("C", (610, 220), (690, 302), (690, 438)),
    ("C", (690, 586), (620, 694), (512, 838)),
]


def scale_point(point: tuple[float, float], size: int) -> tuple[float, float]:
    factor = size / BASE
    return (point[0] * factor, point[1] * factor)


def scale_value(value: float, size: int) -> float:
    return value * size / BASE


def quadratic_points(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    *,
    steps: int = 120,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps + 1):
        t = index / steps
        inv = 1.0 - t
        x = inv * inv * start[0] + 2 * inv * t * control[0] + t * t * end[0]
        y = inv * inv * start[1] + 2 * inv * t * control[1] + t * t * end[1]
        points.append((x, y))
    return points


def cubic_points(
    start: tuple[float, float],
    control1: tuple[float, float],
    control2: tuple[float, float],
    end: tuple[float, float],
    *,
    steps: int = 180,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps + 1):
        t = index / steps
        inv = 1.0 - t
        x = (
            inv**3 * start[0]
            + 3 * inv * inv * t * control1[0]
            + 3 * inv * t * t * control2[0]
            + t**3 * end[0]
        )
        y = (
            inv**3 * start[1]
            + 3 * inv * inv * t * control1[1]
            + 3 * inv * t * t * control2[1]
            + t**3 * end[1]
        )
        points.append((x, y))
    return points


def build_pin_polygon(size: int) -> list[tuple[float, float]]:
    polygon: list[tuple[float, float]] = []
    current = scale_point(PIN_PATH[0][1], size)
    polygon.append(current)
    for command, *points in PIN_PATH[1:]:
        if command != "C":
            continue
        control1 = scale_point(points[0], size)
        control2 = scale_point(points[1], size)
        end = scale_point(points[2], size)
        segment = cubic_points(current, control1, control2, end)[1:]
        polygon.extend(segment)
        current = end
    return polygon


def build_pin_path_d() -> str:
    parts = [f"M {PIN_PATH[0][1][0]} {PIN_PATH[0][1][1]}"]
    for command, *points in PIN_PATH[1:]:
        if command != "C":
            continue
        c1, c2, end = points
        parts.append(f"C {c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]}")
    parts.append("Z")
    return " ".join(parts)


def create_linear_gradient(size: int, start: tuple[int, int, int], end: tuple[int, int, int], *, angle: int) -> Image.Image:
    mask = Image.linear_gradient("L").rotate(angle, expand=True).resize((size, size))
    return Image.composite(Image.new("RGBA", (size, size), end + (255,)), Image.new("RGBA", (size, size), start + (255,)), mask)


def create_diagonal_gradient(size: int, start: tuple[int, int, int], end: tuple[int, int, int]) -> Image.Image:
    mask = Image.new("L", (size, size))
    pixels = bytearray(size * size)
    denominator = max(1, 2 * (size - 1))
    index = 0
    for y in range(size):
        inverted_y = size - 1 - y
        for x in range(size):
            pixels[index] = int(255 * (x + inverted_y) / denominator)
            index += 1
    mask.frombytes(bytes(pixels))
    return Image.composite(Image.new("RGBA", (size, size), end + (255,)), Image.new("RGBA", (size, size), start + (255,)), mask)


def create_radial_highlight(size: int, color: tuple[int, int, int], *, diameter: float, center: tuple[float, float], opacity: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), color + (0,))
    patch = Image.new("RGBA", (size, size), color + (0,))
    draw = ImageDraw.Draw(patch)
    box = (
        center[0] - diameter / 2,
        center[1] - diameter / 2,
        center[0] + diameter / 2,
        center[1] + diameter / 2,
    )
    draw.ellipse(box, fill=color + (opacity,))
    return patch.filter(ImageFilter.GaussianBlur(radius=max(1.0, diameter / 5.5)))


def rounded_rect_mask(size: int, *, inset: float, radius: float) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    box = (
        int(scale_value(inset, size)),
        int(scale_value(inset, size)),
        int(size - scale_value(inset, size)),
        int(size - scale_value(inset, size)),
    )
    draw.rounded_rectangle(box, radius=int(scale_value(radius, size)), fill=255)
    return mask


def polygon_mask(size: int, points: Iterable[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(list(points), fill=255)
    return mask


def draw_tube(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    *,
    fill: tuple[int, ...],
    width: int,
) -> None:
    radius = width / 2
    for start, end in zip(points, points[1:]):
        draw.line([start, end], fill=fill, width=width)
    for x, y in points[::2]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)
    end_x, end_y = points[-1]
    draw.ellipse((end_x - radius, end_y - radius, end_x + radius, end_y + radius), fill=fill)


def render_logo(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    tile_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile_shadow_draw = ImageDraw.Draw(tile_shadow)
    inset = scale_value(92, size)
    radius = scale_value(212, size)
    shadow_box = (int(inset), int(inset + scale_value(18, size)), int(size - inset), int(size - inset + scale_value(18, size)))
    tile_shadow_draw.rounded_rectangle(shadow_box, radius=int(radius), fill=COLORS["tile_shadow"])
    image.alpha_composite(tile_shadow.filter(ImageFilter.GaussianBlur(radius=scale_value(32, size))))

    background = create_diagonal_gradient(size, COLORS["teal"], COLORS["navy"])
    background.alpha_composite(
        create_radial_highlight(
            size,
            COLORS["gold"],
            diameter=scale_value(620, size),
            center=scale_point((324, 282), size),
            opacity=84,
        )
    )
    background.alpha_composite(
        create_radial_highlight(
            size,
            COLORS["teal_bright"],
            diameter=scale_value(720, size),
            center=scale_point((348, 734), size),
            opacity=78,
        )
    )
    background.putalpha(rounded_rect_mask(size, inset=80, radius=212))
    image.alpha_composite(background)

    routes_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    routes_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    routes_shadow_draw = ImageDraw.Draw(routes_shadow)
    routes_draw = ImageDraw.Draw(routes_layer)
    route_width = int(scale_value(52, size))
    node_radius = scale_value(26, size)
    for route in ROUTES:
        points = [
            scale_point(point, size)
            for point in quadratic_points(route["start"], route["control"], route["end"])
        ]
        draw_tube(
            routes_shadow_draw,
            [(x, y + scale_value(8, size)) for x, y in points],
            fill=COLORS["route_shadow"],
            width=route_width,
        )
        draw_tube(routes_draw, points, fill=COLORS["cream"] + (255,), width=route_width)
        cx, cy = scale_point(route["start"], size)
        routes_draw.ellipse(
            (cx - node_radius, cy - node_radius, cx + node_radius, cy + node_radius),
            fill=route["node_fill"] + (255,),
            outline=COLORS["cream"] + (255,),
            width=max(2, int(scale_value(10, size))),
        )
    image.alpha_composite(routes_shadow.filter(ImageFilter.GaussianBlur(radius=scale_value(10, size))))
    image.alpha_composite(routes_layer)

    pin_polygon = build_pin_polygon(size)
    pin_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pin_shadow_draw = ImageDraw.Draw(pin_shadow)
    pin_shadow_draw.polygon(
        [(x, y + scale_value(14, size)) for x, y in pin_polygon],
        fill=COLORS["pin_shadow"],
    )
    image.alpha_composite(pin_shadow.filter(ImageFilter.GaussianBlur(radius=scale_value(24, size))))

    pin_mask = polygon_mask(size, pin_polygon)

    stroke_width = max(3, int(scale_value(20, size)))
    if stroke_width % 2 == 0:
        stroke_width += 1
    pin_outline_alpha = ImageChops.subtract(pin_mask.filter(ImageFilter.MaxFilter(stroke_width)), pin_mask)
    pin_outline = Image.new("RGBA", (size, size), (178, 74, 34, 255))
    pin_outline.putalpha(pin_outline_alpha)
    image.alpha_composite(pin_outline)

    pin_gradient = create_linear_gradient(size, COLORS["gold"], COLORS["coral"], angle=90)
    pin_gradient.alpha_composite(
        create_radial_highlight(
            size,
            COLORS["cream"],
            diameter=scale_value(380, size),
            center=scale_point((452, 304), size),
            opacity=50,
        )
    )
    pin_gradient.putalpha(pin_mask)
    image.alpha_composite(pin_gradient)

    hub_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hub_draw = ImageDraw.Draw(hub_layer)
    hub_center = scale_point((512, 420), size)
    outer_radius = scale_value(112, size)
    middle_radius = scale_value(82, size)
    core_radius = scale_value(32, size)
    hub_draw.ellipse(
        (
            hub_center[0] - outer_radius,
            hub_center[1] - outer_radius,
            hub_center[0] + outer_radius,
            hub_center[1] + outer_radius,
        ),
        fill=COLORS["cream"] + (255,),
    )
    hub_draw.ellipse(
        (
            hub_center[0] - middle_radius,
            hub_center[1] - middle_radius,
            hub_center[0] + middle_radius,
            hub_center[1] + middle_radius,
        ),
        fill=COLORS["navy_deep"] + (255,),
    )
    hub_draw.ellipse(
        (
            hub_center[0] - core_radius,
            hub_center[1] - core_radius,
            hub_center[0] + core_radius,
            hub_center[1] + core_radius,
        ),
        fill=COLORS["gold"] + (255,),
    )
    image.alpha_composite(hub_layer)

    tile_gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    tile_gloss_draw = ImageDraw.Draw(tile_gloss)
    tile_gloss_draw.rounded_rectangle(
        (
            int(scale_value(80, size)),
            int(scale_value(80, size)),
            int(size - scale_value(80, size)),
            int(size - scale_value(80, size)),
        ),
        radius=int(scale_value(212, size)),
        outline=(255, 255, 255, 54),
        width=max(1, int(scale_value(10, size))),
    )
    image.alpha_composite(tile_gloss)

    return image


def save_png(image: Image.Image, path: Path, size: int) -> None:
    image.resize((size, size), Image.Resampling.LANCZOS).save(path, format="PNG")


def save_favicon(image: Image.Image, path: Path) -> None:
    image.resize((512, 512), Image.Resampling.LANCZOS).save(
        path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )


def write_svg(path: Path) -> None:
    route_paths = "\n".join(
        [
            f'<path d="M {route["start"][0]} {route["start"][1]} Q {route["control"][0]} {route["control"][1]} {route["end"][0]} {route["end"][1]}" />'
            for route in ROUTES
        ]
    )
    route_nodes = "\n".join(
        [
            f'<circle cx="{route["start"][0]}" cy="{route["start"][1]}" r="26" fill="rgb({route["node_fill"][0]} {route["node_fill"][1]} {route["node_fill"][2]})" stroke="rgb(255 247 231)" stroke-width="10" />'
            for route in ROUTES
        ]
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" fill="none">
  <defs>
    <linearGradient id="tileGradient" x1="190" y1="820" x2="834" y2="170" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#1f9182" />
      <stop offset="1" stop-color="#19334e" />
    </linearGradient>
    <radialGradient id="tileWarmGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(324 282) rotate(90) scale(310)">
      <stop offset="0" stop-color="#f5bf4a" stop-opacity=".45" />
      <stop offset="1" stop-color="#f5bf4a" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="tileCoolGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(348 734) rotate(90) scale(360)">
      <stop offset="0" stop-color="#33b5a4" stop-opacity=".42" />
      <stop offset="1" stop-color="#33b5a4" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="pinGradient" x1="512" y1="220" x2="512" y2="838" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#f5bf4a" />
      <stop offset=".62" stop-color="#eca838" />
      <stop offset="1" stop-color="#d14f2a" />
    </linearGradient>
    <radialGradient id="pinHighlight" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(452 304) rotate(90) scale(190)">
      <stop offset="0" stop-color="#fff7e7" stop-opacity=".6" />
      <stop offset="1" stop-color="#fff7e7" stop-opacity="0" />
    </radialGradient>
    <filter id="tileShadow" x="28" y="50" width="968" height="968" color-interpolation-filters="sRGB">
      <feGaussianBlur stdDeviation="18" />
    </filter>
    <filter id="routeShadow" x="180" y="210" width="650" height="500" color-interpolation-filters="sRGB">
      <feOffset dy="8" />
      <feGaussianBlur stdDeviation="7" />
    </filter>
    <filter id="pinShadow" x="250" y="196" width="524" height="712" color-interpolation-filters="sRGB">
      <feOffset dy="14" />
      <feGaussianBlur stdDeviation="14" />
    </filter>
  </defs>
  <rect x="92" y="110" width="840" height="840" rx="212" fill="#0c1824" fill-opacity=".28" filter="url(#tileShadow)" />
  <rect x="80" y="80" width="864" height="864" rx="212" fill="url(#tileGradient)" />
  <rect x="80" y="80" width="864" height="864" rx="212" fill="url(#tileWarmGlow)" />
  <rect x="80" y="80" width="864" height="864" rx="212" fill="url(#tileCoolGlow)" />
  <g filter="url(#routeShadow)">
    <g stroke="#112234" stroke-opacity=".35" stroke-linecap="round" stroke-width="52">
      {route_paths}
    </g>
  </g>
  <g stroke="#fff7e7" stroke-linecap="round" stroke-width="52">
    {route_paths}
  </g>
  {route_nodes}
  <path d="{build_pin_path_d()}" fill="#12273d" fill-opacity=".36" filter="url(#pinShadow)" transform="translate(0 14)" />
  <path d="{build_pin_path_d()}" fill="url(#pinGradient)" stroke="#b24a22" stroke-width="12" />
  <path d="{build_pin_path_d()}" fill="url(#pinHighlight)" />
  <circle cx="512" cy="420" r="112" fill="#fff7e7" />
  <circle cx="512" cy="420" r="82" fill="#12273d" />
  <circle cx="512" cy="420" r="32" fill="#f5bf4a" />
  <rect x="85" y="85" width="854" height="854" rx="207" stroke="white" stroke-opacity=".22" stroke-width="10" />
</svg>
"""
    path.write_text(svg)


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    master = render_logo(2048)
    write_svg(PUBLIC_DIR / "logo-mark.svg")
    save_png(master, PUBLIC_DIR / "logo-1024.png", 1024)
    save_png(master, PUBLIC_DIR / "favicon-512.png", 512)
    save_png(master, PUBLIC_DIR / "icon-192.png", 192)
    save_png(master, PUBLIC_DIR / "apple-touch-icon.png", 180)
    save_favicon(master, PUBLIC_DIR / "favicon.ico")


if __name__ == "__main__":
    main()
