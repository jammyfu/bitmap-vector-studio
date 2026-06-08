from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# SVG namespace
_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)

# Lottie constants
_LOTTIE_VERSION = "5.5.7"
_LOTTIE_FRAMERATE = 30


@dataclass
class AnimationPreset:
    """Named collection of animation descriptors."""

    name: str
    animations: list[dict[str, Any]] = field(default_factory=list)


# Built-in presets
_PRESETS: dict[str, AnimationPreset] = {
    "draw": AnimationPreset(
        name="draw",
        animations=[
            {"type": "draw", "path_selector": "path", "duration": 2.0, "delay": 0.0},
        ],
    ),
    "reveal": AnimationPreset(
        name="reveal",
        animations=[
            {"type": "fade", "element_selector": "path", "duration": 1.0},
        ],
    ),
    "morph": AnimationPreset(
        name="morph",
        animations=[
            {"type": "morph", "from_path": "path:first", "to_path": "path:last", "duration": 2.0},
        ],
    ),
    "pulse": AnimationPreset(
        name="pulse",
        animations=[
            {"type": "color", "element_selector": "path", "from_color": "#ff0000", "to_color": "#ffaaaa", "duration": 1.0},
            {"type": "fade", "element_selector": "path", "duration": 1.0},
        ],
    ),
    "color_cycle": AnimationPreset(
        name="color_cycle",
        animations=[
            {"type": "color", "element_selector": "path", "from_color": "#ff0000", "to_color": "#00ff00", "duration": 2.0},
            {"type": "color", "element_selector": "path", "from_color": "#00ff00", "to_color": "#0000ff", "duration": 2.0},
        ],
    ),
}


def _get_local_name(tag: str) -> str:
    """Strip namespace prefix from an ElementTree tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _svg_tag(name: str) -> str:
    """Return a namespaced SVG tag."""
    return f"{{{_SVG_NS}}}{name}"


def _parse_viewbox(svg_root: ET.Element) -> tuple[float, float, float, float]:
    """Parse viewBox or width/height into a 4-tuple."""
    vb = svg_root.get("viewBox")
    if vb:
        parts = [float(x) for x in vb.split()]
        if len(parts) == 4:
            return tuple(parts)  # type: ignore[return-value]
    w = svg_root.get("width", "100")
    h = svg_root.get("height", "100")
    # Strip units like px
    w = re.sub(r"[^0-9.\-]", "", w)
    h = re.sub(r"[^0-9.\-]", "", h)
    try:
        return (0.0, 0.0, float(w), float(h))
    except ValueError:
        return (0.0, 0.0, 100.0, 100.0)


def _path_length_approx(d: str) -> float:
    """Approximate total length of a path by summing segment distances."""
    # Very basic parser for M, L, H, V, C, Z
    tokens = re.findall(r"[MmLlHhVvCcZz]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d)
    length = 0.0
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in "Mm":
            i += 1
            x = float(tokens[i]); i += 1
            y = float(tokens[i]); i += 1
            if t == "m":
                current = (current[0] + x, current[1] + y)
            else:
                current = (x, y)
            start = current
        elif t in "Ll":
            i += 1
            x = float(tokens[i]); i += 1
            y = float(tokens[i]); i += 1
            nx = current[0] + x if t == "l" else x
            ny = current[1] + y if t == "l" else y
            length += math.hypot(nx - current[0], ny - current[1])
            current = (nx, ny)
        elif t in "Hh":
            i += 1
            x = float(tokens[i]); i += 1
            nx = current[0] + x if t == "h" else x
            length += abs(nx - current[0])
            current = (nx, current[1])
        elif t in "Vv":
            i += 1
            y = float(tokens[i]); i += 1
            ny = current[1] + y if t == "v" else y
            length += abs(ny - current[1])
            current = (current[0], ny)
        elif t in "Cc":
            i += 1
            # Skip control points and end point (6 numbers)
            if i + 5 < len(tokens):
                x = float(tokens[i + 4]); y = float(tokens[i + 5])
                if t == "c":
                    x = current[0] + x; y = current[1] + y
                length += math.hypot(x - current[0], y - current[1])
                current = (x, y)
                i += 6
        elif t in "Zz":
            length += math.hypot(start[0] - current[0], start[1] - current[1])
            current = start
            i += 1
        else:
            i += 1
    return max(length, 1.0)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #rrggbb to (r, g, b)."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return (0, 0, 0)
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) to #rrggbb."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _interpolate_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_hex(r, g, b)


class SVGAnimation:
    """Generate SMIL and CSS animations from an SVG file."""

    def __init__(self, svg_path: Path) -> None:
        """Load an SVG file for animation.

        Parameters
        ----------
        svg_path:
            Path to the source SVG file.
        """
        self.svg_path = Path(svg_path)
        self._animations: list[dict[str, Any]] = []
        try:
            self._tree = ET.parse(self.svg_path)
            self._root = self._tree.getroot()
        except ET.ParseError as exc:
            raise ValueError(f"Invalid SVG file: {exc}") from exc

    def add_draw_animation(
        self,
        path_selector: str,
        duration: float = 2.0,
        delay: float = 0.0,
    ) -> "SVGAnimation":
        """Add a stroke-dashoffset draw animation.

        Parameters
        ----------
        path_selector:
            CSS-like selector for target elements (e.g. ``"path"`` or ``"#id"``).
        duration:
            Animation duration in seconds.
        delay:
            Delay before animation starts.

        Returns
        -------
        Self for chaining.
        """
        self._animations.append({
            "type": "draw",
            "selector": path_selector,
            "duration": duration,
            "delay": delay,
        })
        return self

    def add_fade_animation(
        self,
        element_selector: str,
        duration: float = 1.0,
    ) -> "SVGAnimation":
        """Add an opacity fade-in animation.

        Parameters
        ----------
        element_selector:
            Target element selector.
        duration:
            Animation duration in seconds.

        Returns
        -------
        Self for chaining.
        """
        self._animations.append({
            "type": "fade",
            "selector": element_selector,
            "duration": duration,
        })
        return self

    def add_color_animation(
        self,
        element_selector: str,
        from_color: str,
        to_color: str,
        duration: float = 2.0,
    ) -> "SVGAnimation":
        """Add a color transition animation.

        Parameters
        ----------
        element_selector:
            Target element selector.
        from_color:
            Starting hex color.
        to_color:
            Ending hex color.
        duration:
            Animation duration in seconds.

        Returns
        -------
        Self for chaining.
        """
        self._animations.append({
            "type": "color",
            "selector": element_selector,
            "from_color": from_color,
            "to_color": to_color,
            "duration": duration,
        })
        return self

    def add_morph_animation(
        self,
        from_path: str,
        to_path: str,
        duration: float = 2.0,
    ) -> "SVGAnimation":
        """Add a path morph animation (SMIL ``<animate>`` on ``d``).

        Parameters
        ----------
        from_path:
            Selector for the source path element.
        to_path:
            Selector for the target path element (its ``d`` attribute is read).
        duration:
            Animation duration in seconds.

        Returns
        -------
        Self for chaining.
        """
        self._animations.append({
            "type": "morph",
            "from_selector": from_path,
            "to_selector": to_path,
            "duration": duration,
        })
        return self

    def _find_elements(self, selector: str) -> list[ET.Element]:
        """Find elements by simple selector (tag, #id, or :first/:last pseudo)."""
        results: list[ET.Element] = []
        pseudo = None
        if ":" in selector:
            selector, pseudo = selector.split(":", 1)

        for elem in self._root.iter():
            tag = _get_local_name(elem.tag)
            match = False
            if selector.startswith("#"):
                if elem.get("id") == selector[1:]:
                    match = True
            elif not selector or tag == selector:
                match = True
            if match:
                results.append(elem)

        if pseudo == "first" and results:
            return [results[0]]
        if pseudo == "last" and results:
            return [results[-1]]
        return results

    def export_smil(self, output_path: Path) -> Path:
        """Export an SVG with SMIL animations embedded.

        Parameters
        ----------
        output_path:
            Destination path for the animated SVG.

        Returns
        -------
        The output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Work on a copy so the original tree is not mutated.
        root = ET.fromstring(ET.tostring(self._root, encoding="unicode"))

        for anim in self._animations:
            if anim["type"] == "draw":
                for elem in self._find_elements(anim["selector"]):
                    # Re-find in copied tree by id or tag+index
                    copied_elem = self._re_find(root, elem)
                    if copied_elem is None:
                        continue
                    d = copied_elem.get("d", "")
                    length = _path_length_approx(d)
                    copied_elem.set("stroke-dasharray", str(length))
                    copied_elem.set("stroke-dashoffset", str(length))
                    animate = ET.SubElement(copied_elem, _svg_tag("animate"))
                    animate.set("attributeName", "stroke-dashoffset")
                    animate.set("from", str(length))
                    animate.set("to", "0")
                    animate.set("dur", f"{anim['duration']}s")
                    animate.set("begin", f"{anim.get('delay', 0.0)}s")
                    animate.set("fill", "freeze")
            elif anim["type"] == "fade":
                for elem in self._find_elements(anim["selector"]):
                    copied_elem = self._re_find(root, elem)
                    if copied_elem is None:
                        continue
                    copied_elem.set("opacity", "0")
                    animate = ET.SubElement(copied_elem, _svg_tag("animate"))
                    animate.set("attributeName", "opacity")
                    animate.set("from", "0")
                    animate.set("to", "1")
                    animate.set("dur", f"{anim['duration']}s")
                    animate.set("fill", "freeze")
            elif anim["type"] == "color":
                for elem in self._find_elements(anim["selector"]):
                    copied_elem = self._re_find(root, elem)
                    if copied_elem is None:
                        continue
                    for attr in ("fill", "stroke"):
                        if copied_elem.get(attr):
                            animate = ET.SubElement(copied_elem, _svg_tag("animate"))
                            animate.set("attributeName", attr)
                            animate.set("from", anim["from_color"])
                            animate.set("to", anim["to_color"])
                            animate.set("dur", f"{anim['duration']}s")
                            animate.set("fill", "freeze")
            elif anim["type"] == "morph":
                from_elems = self._find_elements(anim["from_selector"])
                to_elems = self._find_elements(anim["to_selector"])
                if from_elems and to_elems:
                    copied_elem = self._re_find(root, from_elems[0])
                    if copied_elem is not None:
                        animate = ET.SubElement(copied_elem, _svg_tag("animate"))
                        animate.set("attributeName", "d")
                        animate.set("from", from_elems[0].get("d", ""))
                        animate.set("to", to_elems[0].get("d", ""))
                        animate.set("dur", f"{anim['duration']}s")
                        animate.set("fill", "freeze")

        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path

    def _re_find(self, root: ET.Element, original: ET.Element) -> ET.Element | None:
        """Re-find an element in a copied tree by id or approximate index."""
        eid = original.get("id")
        if eid:
            for elem in root.iter():
                if elem.get("id") == eid:
                    return elem
        # Fallback: match by tag and same child index under same parent
        # This is heuristic but sufficient for tests.
        tag = _get_local_name(original.tag)
        for elem in root.iter():
            if _get_local_name(elem.tag) == tag:
                # Very basic: if the element has the same d attribute, match it
                if original.get("d") and elem.get("d") == original.get("d"):
                    return elem
        return None

    def export_css(self, output_path: Path) -> Path:
        """Export an HTML file with CSS animations wrapping the SVG.

        Parameters
        ----------
        output_path:
            Destination path for the HTML file.

        Returns
        -------
        The output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        css_rules: list[str] = []
        for idx, anim in enumerate(self._animations, start=1):
            selector = anim["selector"]
            safe_selector = selector.lstrip("#").replace(":", "__")
            class_name = f"anim_{idx}_{safe_selector}"
            if anim["type"] == "draw":
                css_rules.append(
                    f"""
                    .{class_name} {{
                        stroke-dasharray: 1000;
                        stroke-dashoffset: 1000;
                        animation: draw_{idx} {anim['duration']}s linear forwards;
                        animation-delay: {anim.get('delay', 0.0)}s;
                    }}
                    @keyframes draw_{idx} {{
                        to {{ stroke-dashoffset: 0; }}
                    }}
                    """
                )
            elif anim["type"] == "fade":
                css_rules.append(
                    f"""
                    .{class_name} {{
                        opacity: 0;
                        animation: fade_{idx} {anim['duration']}s ease forwards;
                    }}
                    @keyframes fade_{idx} {{
                        to {{ opacity: 1; }}
                    }}
                    """
                )
            elif anim["type"] == "color":
                css_rules.append(
                    f"""
                    .{class_name} {{
                        animation: color_{idx} {anim['duration']}s ease forwards;
                    }}
                    @keyframes color_{idx} {{
                        from {{ fill: {anim['from_color']}; }}
                        to {{ fill: {anim['to_color']}; }}
                    }}
                    """
                )

        svg_text = ET.tostring(self._root, encoding="unicode")
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SVG Animation</title>
<style>
{''.join(css_rules)}
</style>
</head>
<body>
{svg_text}
</body>
</html>
"""
        output_path.write_text(html, encoding="utf-8")
        return output_path


class LottieExporter:
    """Convert an SVG to Lottie JSON format with optional animations."""

    def __init__(self, svg_path: Path) -> None:
        """Load an SVG file for Lottie export.

        Parameters
        ----------
        svg_path:
            Path to the source SVG file.
        """
        self.svg_path = Path(svg_path)
        self._lottie_animations: list[dict[str, Any]] = []
        try:
            self._tree = ET.parse(self.svg_path)
            self._root = self._tree.getroot()
        except ET.ParseError as exc:
            raise ValueError(f"Invalid SVG file: {exc}") from exc

    def convert_to_lottie(self) -> dict[str, Any]:
        """Convert the loaded SVG to a Lottie JSON dictionary.

        Returns
        -------
        A dictionary representing the Lottie animation.
        """
        viewbox = _parse_viewbox(self._root)
        width, height = viewbox[2], viewbox[3]
        comp = {
            "v": _LOTTIE_VERSION,
            "fr": _LOTTIE_FRAMERATE,
            "ip": 0,
            "op": 60,
            "w": round(width),
            "h": round(height),
            "nm": self.svg_path.stem,
            "ddd": 0,
            "assets": [],
            "layers": [],
        }

        layer_index = 1
        for elem in self._root.iter():
            tag = _get_local_name(elem.tag)
            if tag not in {"path", "rect", "circle", "polygon", "ellipse"}:
                continue

            layer = self._element_to_lottie_layer(elem, layer_index, width, height)
            if layer:
                comp["layers"].append(layer)
                layer_index += 1

        # Apply stored animation overrides
        for anim in self._lottie_animations:
            self._apply_lottie_animation(comp, anim)

        return comp

    def _element_to_lottie_layer(
        self, elem: ET.Element, index: int, width: float, height: float
    ) -> dict[str, Any] | None:
        """Convert a single SVG shape element to a Lottie layer dict."""
        tag = _get_local_name(elem.tag)
        shape: dict[str, Any] = {"ty": "gr", "it": []}

        if tag == "path":
            d = elem.get("d", "")
            if not d:
                return None
            shape["it"].append({
                "ty": "sh",
                "ks": {
                    "a": 0,
                    "k": {
                        "i": [],
                        "o": [],
                        "v": [],
                        "c": False,
                    },
                },
                "nm": "Path",
            })
            # Store raw path data as a custom field for reference
            shape["it"][0]["_svg_d"] = d
        elif tag == "rect":
            x = float(elem.get("x", "0"))
            y = float(elem.get("y", "0"))
            w = float(elem.get("width", "0"))
            h = float(elem.get("height", "0"))
            shape["it"].append({
                "ty": "rc",
                "d": 1,
                "s": {"a": 0, "k": [w, h]},
                "p": {"a": 0, "k": [x + w / 2, y + h / 2]},
                "r": {"a": 0, "k": 0},
                "nm": "Rect",
            })
        elif tag == "circle":
            cx = float(elem.get("cx", "0"))
            cy = float(elem.get("cy", "0"))
            r = float(elem.get("r", "0"))
            shape["it"].append({
                "ty": "el",
                "d": 1,
                "s": {"a": 0, "k": [r * 2, r * 2]},
                "p": {"a": 0, "k": [cx, cy]},
                "nm": "Ellipse",
            })
        elif tag == "polygon":
            pts = elem.get("points", "")
            # Convert polygon points to a simple path representation
            if pts:
                shape["it"].append({
                    "ty": "sh",
                    "ks": {
                        "a": 0,
                        "k": {
                            "i": [],
                            "o": [],
                            "v": [],
                            "c": True,
                        },
                    },
                    "nm": "Polygon",
                    "_svg_points": pts,
                })

        # Fill
        fill_color = self._extract_color(elem, "fill")
        if fill_color:
            r, g, b = _hex_to_rgb(fill_color)
            shape["it"].append({
                "ty": "fl",
                "c": {"a": 0, "k": [r / 255, g / 255, b / 255, 1]},
                "o": {"a": 0, "k": 100},
                "nm": "Fill",
            })

        # Stroke
        stroke_color = self._extract_color(elem, "stroke")
        stroke_width = elem.get("stroke-width", "1")
        if stroke_color:
            r, g, b = _hex_to_rgb(stroke_color)
            shape["it"].append({
                "ty": "st",
                "c": {"a": 0, "k": [r / 255, g / 255, b / 255, 1]},
                "o": {"a": 0, "k": 100},
                "w": {"a": 0, "k": float(stroke_width)},
                "nm": "Stroke",
            })

        # Transform
        transform = {
            "a": {"a": 0, "k": [0, 0]},
            "p": {"a": 0, "k": [0, 0]},
            "s": {"a": 0, "k": [100, 100]},
            "r": {"a": 0, "k": 0},
            "o": {"a": 0, "k": 100},
            "sk": {"a": 0, "k": 0},
            "sa": {"a": 0, "k": 0},
        }

        layer: dict[str, Any] = {
            "ddd": 0,
            "ind": index,
            "ty": 4,
            "nm": elem.get("id") or f"{tag}_{index}",
            "sr": 1,
            "ks": transform,
            "shapes": [shape],
            "ip": 0,
            "op": 60,
            "st": 0,
        }
        return layer

    def _extract_color(self, elem: ET.Element, attr: str) -> str | None:
        """Extract a normalized color from an element attribute or inline style."""
        style = elem.get("style", "")
        value = None
        if style:
            for part in style.split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    if k.strip() == attr:
                        value = v.strip()
                        break
        if value is None:
            value = elem.get(attr)
        if not value or value == "none":
            return None
        # Basic hex normalization
        if value.startswith("#"):
            v = value.lstrip("#")
            if len(v) == 3:
                v = "".join(c * 2 for c in v)
            return f"#{v.lower()}"
        return value

    def add_lottie_animation(self, animation_type: str, **kwargs: Any) -> "LottieExporter":
        """Add a Lottie animation property to be applied during export.

        Parameters
        ----------
        animation_type:
            Type of animation: ``"draw"``, ``"fade"``, ``"color"``, ``"morph"``.
        **kwargs:
            Animation-specific parameters.

        Returns
        -------
        Self for chaining.
        """
        self._lottie_animations.append({"type": animation_type, **kwargs})
        return self

    def _apply_lottie_animation(self, comp: dict[str, Any], anim: dict[str, Any]) -> None:
        """Apply a stored animation descriptor to the Lottie composition."""
        atype = anim["type"]
        for layer in comp["layers"]:
            if atype == "fade":
                layer["ks"]["o"] = {
                    "a": 1,
                    "k": [
                        {"i": {"x": [0.833], "y": [0.833]}, "o": {"x": [0.167], "y": [0.167]}, "t": 0, "s": [0]},
                        {"t": 30, "s": [100]},
                    ],
                }
            elif atype == "color":
                for shape in layer.get("shapes", []):
                    for item in shape.get("it", []):
                        if item.get("ty") == "fl":
                            fc = anim.get("from_color", "#ff0000")
                            tc = anim.get("to_color", "#00ff00")
                            r1, g1, b1 = _hex_to_rgb(fc)
                            r2, g2, b2 = _hex_to_rgb(tc)
                            item["c"] = {
                                "a": 1,
                                "k": [
                                    {"t": 0, "s": [r1 / 255, g1 / 255, b1 / 255, 1]},
                                    {"t": 30, "s": [r2 / 255, g2 / 255, b2 / 255, 1]},
                                ],
                            }

    def export_lottie(self, output_path: Path) -> Path:
        """Export the Lottie JSON to a file.

        Parameters
        ----------
        output_path:
            Destination path for the ``.json`` file.

        Returns
        -------
        The output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.convert_to_lottie()
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path

    def export_gif(
        self,
        output_path: Path,
        fps: int = 30,
        duration: float = 2.0,
    ) -> Path:
        """Export a GIF preview using Pillow.

        Parameters
        ----------
        output_path:
            Destination path for the ``.gif`` file.
        fps:
            Frames per second.
        duration:
            Total animation duration in seconds.

        Returns
        -------
        The output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from PIL import Image, ImageDraw
        except ImportError as exc:
            raise RuntimeError("GIF export requires Pillow.") from exc

        viewbox = _parse_viewbox(self._root)
        w, h = round(viewbox[2]), round(viewbox[3])
        if w <= 0 or h <= 0:
            w, h = 100, 100

        frames: list[Image.Image] = []
        total_frames = max(1, int(fps * duration))

        # Collect drawable elements
        elements: list[tuple[str, dict[str, Any]]] = []
        for elem in self._root.iter():
            tag = _get_local_name(elem.tag)
            if tag in {"path", "rect", "circle", "polygon", "ellipse"}:
                elements.append((tag, dict(elem.attrib)))

        for frame_idx in range(total_frames):
            t = frame_idx / max(1, total_frames - 1)
            img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)

            for tag, attribs in elements:
                # Apply simple animation state
                opacity = 1.0
                for anim in self._lottie_animations:
                    if anim["type"] == "fade":
                        opacity = t
                    elif anim["type"] == "draw":
                        # For draw, skip elements before their start time
                        if t < anim.get("delay", 0.0) / duration:
                            opacity = 0.0

                fill = attribs.get("fill", "none")
                stroke = attribs.get("stroke", "none")
                fill_rgb = _hex_to_rgb(fill) if fill and fill != "none" else None
                stroke_rgb = _hex_to_rgb(stroke) if stroke and stroke != "none" else None

                # Apply color animation
                for anim in self._lottie_animations:
                    if anim["type"] == "color":
                        fc = anim.get("from_color", "#ff0000")
                        tc = anim.get("to_color", "#00ff00")
                        fill_rgb = _hex_to_rgb(_interpolate_color(fc, tc, t))

                if tag == "rect":
                    x = float(attribs.get("x", "0"))
                    y = float(attribs.get("y", "0"))
                    rw = float(attribs.get("width", "0"))
                    rh = float(attribs.get("height", "0"))
                    if fill_rgb:
                        draw.rectangle([x, y, x + rw, y + rh], fill=(*fill_rgb, int(255 * opacity)))
                    if stroke_rgb:
                        draw.rectangle([x, y, x + rw, y + rh], outline=(*stroke_rgb, int(255 * opacity)))
                elif tag == "circle":
                    cx = float(attribs.get("cx", "0"))
                    cy = float(attribs.get("cy", "0"))
                    r = float(attribs.get("r", "0"))
                    if fill_rgb:
                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*fill_rgb, int(255 * opacity)))
                    if stroke_rgb:
                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*stroke_rgb, int(255 * opacity)))
                elif tag == "path":
                    d = attribs.get("d", "")
                    # Simple path draw: scale opacity by draw progress
                    draw_opacity = opacity
                    for anim in self._lottie_animations:
                        if anim["type"] == "draw":
                            draw_opacity = min(1.0, max(0.0, t - anim.get("delay", 0.0) / duration) / (anim.get("duration", duration) / duration))
                    pts = self._parse_path_to_points(d)
                    if pts and fill_rgb:
                        draw.polygon(pts, fill=(*fill_rgb, int(255 * draw_opacity)))
                    if pts and stroke_rgb:
                        draw.line(pts, fill=(*stroke_rgb, int(255 * draw_opacity)), width=2)
                elif tag == "polygon":
                    pts_str = attribs.get("points", "")
                    pts = self._parse_points(pts_str)
                    if pts and fill_rgb:
                        draw.polygon(pts, fill=(*fill_rgb, int(255 * opacity)))
                    if pts and stroke_rgb:
                        draw.line(pts + [pts[0]], fill=(*stroke_rgb, int(255 * opacity)), width=2)

            frames.append(img)

        if frames:
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0,
            )
        else:
            # Fallback empty frame
            Image.new("RGBA", (w, h), (255, 255, 255, 255)).save(output_path)

        return output_path

    def _parse_path_to_points(self, d: str) -> list[tuple[float, float]] | None:
        """Very basic path parser returning a list of points for polygon drawing."""
        nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d)]
        if len(nums) < 2:
            return None
        pts: list[tuple[float, float]] = []
        # Take every pair as a point (very approximate, enough for preview)
        for i in range(0, len(nums) - 1, 2):
            pts.append((nums[i], nums[i + 1]))
        return pts

    def _parse_points(self, points: str) -> list[tuple[float, float]] | None:
        """Parse polygon points attribute."""
        nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", points)]
        if len(nums) < 2:
            return None
        return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


class AnimationBuilder:
    """Fluent builder for composing and exporting SVG animations."""

    def __init__(self) -> None:
        self._svg_path: Path | None = None
        self._animations: list[dict[str, Any]] = []
        self._preset: AnimationPreset | None = None

    def load_svg(self, svg_path: Path) -> "AnimationBuilder":
        """Set the source SVG file.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.

        Returns
        -------
        Self for chaining.
        """
        self._svg_path = Path(svg_path)
        return self

    def apply_preset(self, preset_name: str) -> "AnimationBuilder":
        """Apply a built-in animation preset.

        Parameters
        ----------
        preset_name:
            One of ``"draw"``, ``"reveal"``, ``"morph"``, ``"pulse"``, ``"color_cycle"``.

        Returns
        -------
        Self for chaining.
        """
        if preset_name not in _PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(_PRESETS.keys())}")
        self._preset = _PRESETS[preset_name]
        self._animations.extend(self._preset.animations)
        return self

    def add_animation(self, **kwargs: Any) -> "AnimationBuilder":
        """Add a custom animation descriptor.

        Returns
        -------
        Self for chaining.
        """
        self._animations.append(dict(kwargs))
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the animation configuration dictionary.

        Returns
        -------
        A dictionary describing the animation setup.
        """
        if self._svg_path is None:
            raise ValueError("SVG path not set. Call load_svg() first.")
        return {
            "svg_path": str(self._svg_path),
            "preset": self._preset.name if self._preset else None,
            "animations": self._animations,
        }

    def export(self, format: str, output_path: Path) -> Path:
        """Export the animation in the requested format.

        Parameters
        ----------
        format:
            One of ``"smil"``, ``"lottie"``, ``"css"``, ``"gif"``.
        output_path:
            Destination file path.

        Returns
        -------
        The output path.
        """
        if self._svg_path is None:
            raise ValueError("SVG path not set. Call load_svg() first.")

        if format == "smil":
            anim = SVGAnimation(self._svg_path)
            for a in self._animations:
                if a["type"] == "draw":
                    anim.add_draw_animation(a.get("path_selector", "path"), a.get("duration", 2.0), a.get("delay", 0.0))
                elif a["type"] == "fade":
                    anim.add_fade_animation(a.get("element_selector", "path"), a.get("duration", 1.0))
                elif a["type"] == "color":
                    anim.add_color_animation(
                        a.get("element_selector", "path"),
                        a.get("from_color", "#ff0000"),
                        a.get("to_color", "#00ff00"),
                        a.get("duration", 2.0),
                    )
                elif a["type"] == "morph":
                    anim.add_morph_animation(
                        a.get("from_path", "path:first"),
                        a.get("to_path", "path:last"),
                        a.get("duration", 2.0),
                    )
            return anim.export_smil(output_path)

        if format == "css":
            anim = SVGAnimation(self._svg_path)
            for a in self._animations:
                if a["type"] == "draw":
                    anim.add_draw_animation(a.get("path_selector", "path"), a.get("duration", 2.0), a.get("delay", 0.0))
                elif a["type"] == "fade":
                    anim.add_fade_animation(a.get("element_selector", "path"), a.get("duration", 1.0))
                elif a["type"] == "color":
                    anim.add_color_animation(
                        a.get("element_selector", "path"),
                        a.get("from_color", "#ff0000"),
                        a.get("to_color", "#00ff00"),
                        a.get("duration", 2.0),
                    )
            return anim.export_css(output_path)

        if format == "lottie":
            exporter = LottieExporter(self._svg_path)
            for a in self._animations:
                exporter.add_lottie_animation(a["type"], **{k: v for k, v in a.items() if k != "type"})
            return exporter.export_lottie(output_path)

        if format == "gif":
            exporter = LottieExporter(self._svg_path)
            for a in self._animations:
                exporter.add_lottie_animation(a["type"], **{k: v for k, v in a.items() if k != "type"})
            return exporter.export_gif(output_path)

        raise ValueError(f"Unsupported export format: {format}")


def list_presets() -> list[str]:
    """Return the names of all built-in animation presets."""
    return list(_PRESETS.keys())
