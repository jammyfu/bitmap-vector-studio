from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from vector_studio.plugin_interface import Plugin


class ResizePlugin(Plugin):
    """Resize the SVG viewBox and dimensions after conversion."""

    name = "resize"
    version = "1.0.0"
    description = "Resize SVG viewBox and dimensions after conversion."
    author = "Bitmap Vector Studio"

    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        """Scale the SVG viewBox and width/height attributes.

        The scale factor is read from *options* under the key
        ``resize_scale``.  If absent, no resizing is performed.
        """
        scale = options.get("resize_scale")
        if scale is None:
            return svg_path
        try:
            scale = float(scale)
        except (TypeError, ValueError):
            return svg_path
        if scale <= 0 or scale == 1.0:
            return svg_path

        content = svg_path.read_text(encoding="utf-8")

        # Scale viewBox
        def _scale_viewbox(match: re.Match[str]) -> str:
            parts = match.group(1).split()
            if len(parts) == 4:
                try:
                    x, y, w, h = map(float, parts)
                    return f'viewBox="{x} {y} {w * scale} {h * scale}"'
                except ValueError:
                    pass
            return match.group(0)

        content = re.sub(r'viewBox="([^"]+)"', _scale_viewbox, content)

        # Scale width / height
        def _scale_attr(match: re.Match[str]) -> str:
            name = match.group(1)
            val = match.group(2)
            try:
                num = float(val)
                return f'{name}="{num * scale}"'
            except ValueError:
                return match.group(0)

        content = re.sub(r'(width|height)="([^"]+)"', _scale_attr, content)

        svg_path.write_text(content, encoding="utf-8")
        return svg_path
