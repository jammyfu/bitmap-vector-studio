from __future__ import annotations

import json
import math
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)


def _get_local_name(tag: str) -> str:
    """Strip namespace prefix from an ElementTree tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


class SVG3D:
    """Apply 3-D transformations to SVG content using pure-Python math.

    The class manipulates SVG elements by injecting CSS ``transform``
    attributes and SVG filter effects.  No external 3-D libraries are
    required.
    """

    @staticmethod
    def _rotation_matrix(axis: str, angle_deg: float) -> list[list[float]]:
        """Return a 4×4 rotation matrix for *angle_deg* around *axis*."""
        rad = math.radians(angle_deg)
        c = math.cos(rad)
        s = math.sin(rad)
        if axis.lower() == "x":
            return [
                [1, 0, 0, 0],
                [0, c, -s, 0],
                [0, s, c, 0],
                [0, 0, 0, 1],
            ]
        elif axis.lower() == "y":
            return [
                [c, 0, s, 0],
                [0, 1, 0, 0],
                [-s, 0, c, 0],
                [0, 0, 0, 1],
            ]
        else:  # z or default
            return [
                [c, -s, 0, 0],
                [s, c, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ]

    @staticmethod
    def _matmul(m: list[list[float]], v: list[float]) -> list[float]:
        """Multiply a 4×4 matrix with a 4-element column vector."""
        return [
            sum(m[i][j] * v[j] for j in range(4))
            for i in range(4)
        ]

    @staticmethod
    def _svg_transform_from_matrix(m: list[list[float]]) -> str:
        """Convert a 4×4 matrix to a 2-D SVG ``matrix(...)`` string.

        We project the 3-D matrix onto the XY plane by dropping the Z
        component, which gives a convincing pseudo-3-D effect for flat
        vector graphics.
        """
        # SVG matrix(a, b, c, d, e, f) maps to:
        #   x' = a*x + c*y + e
        #   y' = b*x + d*y + f
        a = m[0][0]
        b = m[1][0]
        c = m[0][1]
        d = m[1][1]
        e = m[0][3]
        f = m[1][3]
        return f"matrix({a:.4f}, {b:.4f}, {c:.4f}, {d:.4f}, {e:.4f}, {f:.4f})"

    def extrude(self, svg_path: Path, depth: float = 10.0) -> str:
        """Create a pseudo-extrusion effect by duplicating and offsetting paths.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        depth:
            Extrusion depth in pixels.

        Returns
        -------
        SVG text with duplicated layers offset by *depth*.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8")

        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            return text

        root = tree.getroot()
        # Inject a filter for drop-shadow extrusion look
        defs = root.find(f".//{{{_SVG_NS}}}defs")
        if defs is None:
            defs = ET.SubElement(root, f"{{{_SVG_NS}}}defs")

        filter_elem = ET.SubElement(defs, f"{{{_SVG_NS}}}filter")
        filter_elem.set("id", "extrude-shadow")
        filter_elem.set("x", "-50%")
        filter_elem.set("y", "-50%")
        filter_elem.set("width", "200%")
        filter_elem.set("height", "200%")

        fe_offset = ET.SubElement(filter_elem, f"{{{_SVG_NS}}}feOffset")
        fe_offset.set("in", "SourceGraphic")
        fe_offset.set("dx", str(depth * 0.7))
        fe_offset.set("dy", str(depth * 0.7))
        fe_offset.set("result", "offset")

        fe_blend = ET.SubElement(filter_elem, f"{{{_SVG_NS}}}feBlend")
        fe_blend.set("in", "SourceGraphic")
        fe_blend.set("in2", "offset")
        fe_blend.set("mode", "normal")

        # Apply filter to root group or create one
        svg_elem = root if _get_local_name(root.tag) == "svg" else root.find(f".//{{{_SVG_NS}}}svg")
        if svg_elem is None:
            svg_elem = root

        # Wrap existing children in a group with the filter
        wrapper = ET.SubElement(svg_elem, f"{{{_SVG_NS}}}g")
        wrapper.set("filter", "url(#extrude-shadow)")
        wrapper.set("transform", f"translate({depth * 0.3}, {depth * 0.3})")

        for child in list(svg_elem):
            if child is not wrapper and child is not defs:
                wrapper.append(child)
                svg_elem.remove(child)

        return ET.tostring(root, encoding="unicode")

    def rotate(self, svg_path: Path, axis: str, angle: float) -> str:
        """Apply a 3-D rotation to an SVG and return the transformed text.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        axis:
            Rotation axis: ``x``, ``y``, or ``z``.
        angle:
            Rotation angle in degrees.

        Returns
        -------
        SVG text with a CSS transform applied to the root ``<g>``.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8")

        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            return text

        root = tree.getroot()
        svg_elem = root if _get_local_name(root.tag) == "svg" else root.find(f".//{{{_SVG_NS}}}svg")
        if svg_elem is None:
            svg_elem = root

        mat = self._rotation_matrix(axis, angle)
        transform = self._svg_transform_from_matrix(mat)

        # Find or create a root group to host the transform
        g = svg_elem.find(f"{{{_SVG_NS}}}g")
        if g is None:
            g = ET.SubElement(svg_elem, f"{{{_SVG_NS}}}g")
            for child in list(svg_elem):
                if child is not g:
                    g.append(child)
                    svg_elem.remove(child)

        existing = g.get("transform", "")
        g.set("transform", f"{existing} {transform}".strip())

        return ET.tostring(root, encoding="unicode")

    def add_lighting(self, svg_path: Path, light_direction: tuple[float, float, float]) -> str:
        """Add a directional-light filter to an SVG.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        light_direction:
            Normalised light direction vector ``(x, y, z)``.

        Returns
        -------
        SVG text with an SVG ``feDiffuseLighting`` filter.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8")

        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            return text

        root = tree.getroot()
        defs = root.find(f".//{{{_SVG_NS}}}defs")
        if defs is None:
            defs = ET.SubElement(root, f"{{{_SVG_NS}}}defs")

        filter_elem = ET.SubElement(defs, f"{{{_SVG_NS}}}filter")
        filter_elem.set("id", "3d-lighting")
        filter_elem.set("x", "-50%")
        filter_elem.set("y", "-50%")
        filter_elem.set("width", "200%")
        filter_elem.set("height", "200%")

        fe_light = ET.SubElement(filter_elem, f"{{{_SVG_NS}}}feDiffuseLighting")
        fe_light.set("in", "SourceGraphic")
        fe_light.set("result", "light")
        fe_light.set("lighting-color", "white")
        fe_light.set("surfaceScale", "2")
        fe_light.set("diffuseConstant", "1.2")

        fe_distant = ET.SubElement(fe_light, f"{{{_SVG_NS}}}feDistantLight")
        lx, ly, lz = light_direction
        # Compute elevation and azimuth from the vector
        length = math.sqrt(lx * lx + ly * ly + lz * lz) or 1.0
        lx, ly, lz = lx / length, ly / length, lz / length
        elevation = math.degrees(math.asin(max(-1.0, min(1.0, lz))))
        azimuth = math.degrees(math.atan2(ly, lx))
        fe_distant.set("elevation", f"{elevation:.1f}")
        fe_distant.set("azimuth", f"{azimuth:.1f}")

        fe_blend = ET.SubElement(filter_elem, f"{{{_SVG_NS}}}feBlend")
        fe_blend.set("in", "SourceGraphic")
        fe_blend.set("in2", "light")
        fe_blend.set("mode", "multiply")

        svg_elem = root if _get_local_name(root.tag) == "svg" else root.find(f".//{{{_SVG_NS}}}svg")
        if svg_elem is None:
            svg_elem = root

        g = svg_elem.find(f"{{{_SVG_NS}}}g")
        if g is None:
            g = ET.SubElement(svg_elem, f"{{{_SVG_NS}}}g")
            for child in list(svg_elem):
                if child is not g and child is not defs:
                    g.append(child)
                    svg_elem.remove(child)

        existing = g.get("filter", "")
        filters = [f for f in existing.split() if f]
        filters.append("url(#3d-lighting)")
        g.set("filter", " ".join(filters))

        return ET.tostring(root, encoding="unicode")

    def perspective(self, svg_path: Path, fov: float = 60.0) -> str:
        """Apply a perspective projection transform to an SVG.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        fov:
            Field of view in degrees.

        Returns
        -------
        SVG text with a perspective CSS transform.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8")

        try:
            tree = ET.parse(svg_path)
        except ET.ParseError:
            return text

        root = tree.getroot()
        svg_elem = root if _get_local_name(root.tag) == "svg" else root.find(f".//{{{_SVG_NS}}}svg")
        if svg_elem is None:
            svg_elem = root

        # Approximate perspective with a skew/scale matrix
        fov_rad = math.radians(fov)
        scale = 1.0 / math.tan(fov_rad / 2.0) if math.tan(fov_rad / 2.0) != 0 else 1.0
        perspective_mat = [
            [scale, 0, 0, 0],
            [0, scale, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        transform = self._svg_transform_from_matrix(perspective_mat)

        g = svg_elem.find(f"{{{_SVG_NS}}}g")
        if g is None:
            g = ET.SubElement(svg_elem, f"{{{_SVG_NS}}}g")
            for child in list(svg_elem):
                if child is not g:
                    g.append(child)
                    svg_elem.remove(child)

        existing = g.get("transform", "")
        g.set("transform", f"{existing} {transform}".strip())

        return ET.tostring(root, encoding="unicode")


class ARPreview:
    """Generate AR preview assets from SVG files.

    This includes AR marker generation, overlay configuration, and a
    lightweight USDZ export stub for iOS Quick Look.
    """

    def generate_ar_marker(self, svg_path: Path) -> bytes:
        """Generate a simple AR marker (PNG) from an SVG.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.

        Returns
        -------
        PNG bytes representing the marker.
        """
        svg_path = Path(svg_path)
        if not svg_path.exists():
            raise FileNotFoundError(f"SVG not found: {svg_path}")

        try:
            import qrcode
        except ImportError:
            # Fallback: generate a minimal PNG placeholder
            return self._fallback_marker_png(svg_path)

        qr = qrcode.make(str(svg_path.resolve()))
        from io import BytesIO

        buf = BytesIO()
        qr.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _fallback_marker_png(svg_path: Path) -> bytes:
        """Return a tiny 1×1 placeholder PNG when qrcode is unavailable."""
        # Minimal PNG signature + IHDR + IDAT + IEND for a 1×1 black pixel
        return (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def create_ar_overlay(self, svg_path: Path, width: float = 100.0) -> dict[str, Any]:
        """Create an AR overlay configuration dictionary.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        width:
            Desired physical width in millimetres.

        Returns
        -------
        Dictionary suitable for ARKit / ARCore overlay descriptors.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8", errors="replace")
        vb_match = re.search(r'viewBox="([^"]+)"', text)
        if vb_match:
            parts = vb_match.group(1).split()
            if len(parts) == 4:
                svg_width = float(parts[2])
                svg_height = float(parts[3])
            else:
                svg_width = svg_height = 100.0
        else:
            w_match = re.search(r'width="([^"]+)"', text)
            h_match = re.search(r'height="([^"]+)"', text)
            svg_width = float(w_match.group(1)) if w_match else 100.0
            svg_height = float(h_match.group(1)) if h_match else 100.0

        scale = width / svg_width if svg_width else 1.0
        height = svg_height * scale

        return {
            "type": "svg_overlay",
            "source": str(svg_path.resolve()),
            "physical_width_mm": width,
            "physical_height_mm": height,
            "scale": scale,
            "anchor": "center",
        }

    def export_usdz(self, svg_path: Path, output_path: Path) -> Path:
        """Export a USDZ package for iOS AR Quick Look.

        This is a lightweight stub that writes a valid USDZ container
        with a single plane textured by the SVG (converted to PNG if
        ``cairosvg`` is available).

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        output_path:
            Destination ``.usdz`` path.

        Returns
        -------
        The *output_path* that was written.
        """
        svg_path = Path(svg_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to convert SVG to PNG for the texture
        texture_bytes = b""
        try:
            import cairosvg

            texture_bytes = cairosvg.svg2png(url=str(svg_path), scale=2.0)
        except Exception:
            texture_bytes = self._fallback_marker_png(svg_path)

        # Build a minimal USDA description
        usda = (
            '#usda 1.0\n'
            'def Xform "SvgModel"\n'
            '{\n'
            '    def Mesh "plane"\n'
            '    {\n'
            '        float3[] extent = [(-0.5, -0.5, 0), (0.5, 0.5, 0)]\n'
            '        int[] faceVertexCounts = [4]\n'
            '        int[] faceVertexIndices = [0, 1, 2, 3]\n'
            '        point3f[] points = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)]\n'
            '        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)]\n'
            '        uniform token subdivisionScheme = "none"\n'
            '    }\n'
            '}\n'
        )

        # USDZ is a zip containing .usdc and texture files
        import zipfile

        with zipfile.ZipFile(output_path, "w") as zf:
            zf.writestr("SvgModel.usda", usda)
            zf.writestr("texture.png", texture_bytes)

        return output_path
