from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Common SVG namespaces
_SVG_NS = "http://www.w3.org/2000/svg"

ET.register_namespace("", _SVG_NS)


class FigmaPlugin:
    """Integration plugin for Figma design tool.

    Provides import/export and design-token synchronization with Figma files
    via the Figma REST API.  A personal access token must be set in the
    environment variable ``FIGMA_TOKEN`` or passed to the constructor.
    """

    _API_BASE = "https://api.figma.com/v1"

    def __init__(self, token: str | None = None) -> None:
        """Initialise the plugin with an optional API token.

        Parameters
        ----------
        token:
            Figma personal access token.  If *None*, the token is read from
            the ``FIGMA_TOKEN`` environment variable.
        """
        import os

        self.token = token or os.environ.get("FIGMA_TOKEN", "")

    def _request(self, endpoint: str) -> dict[str, Any]:
        """Execute an authenticated GET request against the Figma API."""
        url = f"{self._API_BASE}{endpoint}"
        req = urllib.request.Request(
            url,
            headers={
                "X-Figma-Token": self.token,
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post_file(self, endpoint: str, data: bytes, content_type: str = "application/json") -> dict[str, Any]:
        """Execute an authenticated POST request with raw bytes."""
        url = f"{self._API_BASE}{endpoint}"
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "X-Figma-Token": self.token,
                "Content-Type": content_type,
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def export_to_figma(self, svg_path: Path, file_key: str, node_id: str) -> bool:
        """Export an SVG file into a Figma document.

        Because the Figma REST API does not support direct SVG upload to an
        existing file, this method uploads the SVG as an image asset and
        returns the resulting URL.  The caller can then reference the asset
        when creating or updating nodes.

        Parameters
        ----------
        svg_path:
            Path to the local SVG file.
        file_key:
            Figma file key (the long identifier from the file URL).
        node_id:
            Target node id within the file.

        Returns
        -------
        ``True`` if the upload succeeded, otherwise ``False``.
        """
        svg_path = Path(svg_path)
        if not svg_path.exists():
            return False
        svg_bytes = svg_path.read_bytes()
        try:
            # Figma image upload endpoint (simplified)
            endpoint = f"/files/{file_key}/images"
            self._post_file(endpoint, svg_bytes, content_type="image/svg+xml")
            return True
        except urllib.error.HTTPError:
            return False
        except Exception:
            return False

    def import_from_figma(self, file_key: str, node_id: str) -> Path:
        """Download an SVG representation of a Figma node.

        Parameters
        ----------
        file_key:
            Figma file key.
        node_id:
            Node id to export.

        Returns
        -------
        Path to the downloaded SVG file (written to a temporary location).
        """
        try:
            # Request SVG export
            endpoint = f"/images/{file_key}?ids={node_id}&format=svg"
            data = self._request(endpoint)
            image_url = data.get("images", {}).get(node_id)
            if not image_url:
                raise RuntimeError("Figma did not return an image URL.")

            # Download the rendered SVG
            req = urllib.request.Request(image_url, headers={"Accept": "image/svg+xml"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                svg_data = resp.read()

            out_path = Path(f"figma_{file_key}_{node_id}.svg")
            out_path.write_bytes(svg_data)
            return out_path
        except Exception as exc:
            raise RuntimeError(f"Failed to import from Figma: {exc}") from exc

    def sync_tokens(self, file_key: str) -> dict[str, Any]:
        """Synchronise design tokens (styles, variables) from a Figma file.

        Parameters
        ----------
        file_key:
            Figma file key.

        Returns
        -------
        Dictionary with ``colors``, ``typography``, and ``spacing`` keys.
        """
        try:
            endpoint = f"/files/{file_key}/styles"
            data = self._request(endpoint)
            tokens: dict[str, Any] = {"colors": [], "typography": [], "spacing": []}
            for style in data.get("meta", {}).get("styles", []):
                style_type = style.get("style_type", "")
                if style_type == "FILL":
                    tokens["colors"].append({
                        "name": style.get("name", "unnamed"),
                        "key": style.get("node_id", ""),
                    })
                elif style_type == "TEXT":
                    tokens["typography"].append({
                        "name": style.get("name", "unnamed"),
                        "key": style.get("node_id", ""),
                    })
            return tokens
        except Exception as exc:
            raise RuntimeError(f"Failed to sync tokens from Figma: {exc}") from exc


class SketchPlugin:
    """Integration plugin for Sketch (macOS) documents.

    Sketch files are ZIP archives containing JSON metadata and bitmap
    previews.  This plugin reads and writes the JSON layer descriptors
    so that SVG data can be exchanged with Sketch documents.
    """

    def export_to_sketch(self, svg_path: Path, document_path: Path) -> bool:
        """Embed an SVG into a Sketch document as a new layer.

        Parameters
        ----------
        svg_path:
            Path to the SVG file to embed.
        document_path:
            Path to the ``.sketch`` document (will be created if it does
            not exist).

        Returns
        -------
        ``True`` on success.
        """
        svg_path = Path(svg_path)
        document_path = Path(document_path)
        if not svg_path.exists():
            return False

        svg_text = svg_path.read_text(encoding="utf-8")
        layer = {
            "_class": "shapeGroup",
            "name": svg_path.stem,
            "svg": svg_text,
            "frame": {"x": 0, "y": 0, "width": 100, "height": 100},
        }

        if document_path.exists():
            try:
                import zipfile

                with zipfile.ZipFile(document_path, "a") as zf:
                    layer_json = json.dumps(layer, ensure_ascii=False)
                    zf.writestr(f"svg_layers/{svg_path.stem}.json", layer_json)
                return True
            except Exception:
                return False
        else:
            # Create a minimal Sketch document structure
            try:
                import zipfile

                document_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(document_path, "w") as zf:
                    meta = {"commit": "main", "pagesAndArtboards": {}}
                    zf.writestr("meta.json", json.dumps(meta, indent=2))
                    layer_json = json.dumps(layer, ensure_ascii=False)
                    zf.writestr(f"svg_layers/{svg_path.stem}.json", layer_json)
                return True
            except Exception:
                return False

    def import_from_sketch(self, document_path: Path, layer_name: str) -> Path:
        """Extract an SVG layer from a Sketch document.

        Parameters
        ----------
        document_path:
            Path to the ``.sketch`` file.
        layer_name:
            Name of the layer to extract.

        Returns
        -------
        Path to the extracted SVG file.
        """
        document_path = Path(document_path)
        if not document_path.exists():
            raise FileNotFoundError(f"Sketch document not found: {document_path}")

        try:
            import zipfile

            with zipfile.ZipFile(document_path, "r") as zf:
                name = f"svg_layers/{layer_name}.json"
                if name not in zf.namelist():
                    raise ValueError(f"Layer '{layer_name}' not found in Sketch document.")
                data = json.loads(zf.read(name).decode("utf-8"))
                svg_text = data.get("svg", "")
                if not svg_text:
                    raise ValueError(f"Layer '{layer_name}' contains no SVG data.")
                out_path = Path(f"{layer_name}.svg")
                out_path.write_text(svg_text, encoding="utf-8")
                return out_path
        except Exception as exc:
            raise RuntimeError(f"Failed to import from Sketch: {exc}") from exc


class DesignTokenSync:
    """Extract, apply, and export design tokens from SVG files.

    Tokens include colours, font families, and spacing values derived from
    SVG attributes and inline styles.
    """

    _COLOR_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
    _COLOR_RGB_RE = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
    _FONT_RE = re.compile(r"font-family\s*:\s*([^;]+)", re.IGNORECASE)
    _SIZE_RE = re.compile(r"(width|height|x|y|cx|cy|r|rx|ry)\s*=\s*\"([^\"]+)\"")

    @staticmethod
    def _parse_color(value: str) -> str | None:
        """Normalise a raw colour string to ``#rrggbb``."""
        if not value:
            return None
        value = value.strip().lower()
        if value in ("none", "currentcolor", "transparent", "inherit"):
            return None
        hex_match = DesignTokenSync._COLOR_HEX_RE.match(value)
        if hex_match:
            hex_val = hex_match.group(1)
            if len(hex_val) == 3:
                hex_val = "".join(c * 2 for c in hex_val)
            elif len(hex_val) == 4:
                hex_val = "".join(c * 2 for c in hex_val[:3])
            elif len(hex_val) == 8:
                hex_val = hex_val[:6]
            return f"#{hex_val.lower()}"
        rgb_match = DesignTokenSync._COLOR_RGB_RE.match(value)
        if rgb_match:
            r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
            return f"#{r:02x}{g:02x}{b:02x}"
        return None

    def extract_tokens(self, svg_path: Path) -> dict[str, Any]:
        """Extract design tokens from an SVG file.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.

        Returns
        -------
        Dictionary with ``colors``, ``fonts``, and ``spacing`` keys.
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8", errors="replace")

        colors: set[str] = set()
        for m in self._COLOR_HEX_RE.finditer(text):
            hex_val = m.group(1)
            if len(hex_val) == 3:
                hex_val = "".join(c * 2 for c in hex_val)
            elif len(hex_val) == 4:
                hex_val = "".join(c * 2 for c in hex_val[:3])
            elif len(hex_val) == 8:
                hex_val = hex_val[:6]
            colors.add(f"#{hex_val.lower()}")

        for m in self._COLOR_RGB_RE.finditer(text):
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            colors.add(f"#{r:02x}{g:02x}{b:02x}")

        fonts: set[str] = set()
        for m in self._FONT_RE.finditer(text):
            fonts.add(m.group(1).strip().strip('"\''))

        spacing: set[str] = set()
        for m in self._SIZE_RE.finditer(text):
            spacing.add(f"{m.group(1)}={m.group(2)}")

        return {
            "colors": sorted(colors),
            "fonts": sorted(fonts),
            "spacing": sorted(spacing),
        }

    def apply_tokens(self, svg_path: Path, tokens: dict[str, Any]) -> Path:
        """Apply design tokens to an SVG file.

        The method performs a simple token substitution: every colour in the
        SVG that matches a key in ``tokens["color_map"]`` is replaced with
        the mapped value.  Font families are replaced via
        ``tokens["font_map"]``.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        tokens:
            Token dictionary (usually produced by :meth:`extract_tokens`).

        Returns
        -------
        Path to the modified SVG file (overwrites the input).
        """
        svg_path = Path(svg_path)
        text = svg_path.read_text(encoding="utf-8")

        color_map = tokens.get("color_map", {})
        font_map = tokens.get("font_map", {})

        for old, new in color_map.items():
            text = text.replace(old, new)

        for old, new in font_map.items():
            text = text.replace(old, new)

        svg_path.write_text(text, encoding="utf-8")
        return svg_path

    def export_tokens_json(self, tokens: dict[str, Any], output_path: Path) -> Path:
        """Export a token dictionary to a JSON file.

        Parameters
        ----------
        tokens:
            Token dictionary.
        output_path:
            Destination path.

        Returns
        -------
        The *output_path* that was written.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(tokens, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path
