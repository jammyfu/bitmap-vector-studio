from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .models import TraceResult


class Plugin:
    """Base class for all Bitmap Vector Studio plugins.

    Subclasses should override the class attributes and any hook methods
    they wish to implement.  Hooks that are not overridden are no-ops.
    """

    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""

    def preprocess(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:
        """Pre-processing hook called after the input image is prepared.

        Parameters
        ----------
        image:
            The prepared PIL ``Image`` instance.
        options:
            Arbitrary keyword options passed from the conversion pipeline.

        Returns
        -------
        Image.Image
            The (possibly modified) image to send to the tracer.
        """
        return image

    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        """Post-processing hook called after SVG optimization.

        Parameters
        ----------
        svg_path:
            Path to the SVG file produced by the tracer.
        options:
            Arbitrary keyword options passed from the conversion pipeline.

        Returns
        -------
        Path
            The (possibly modified) SVG path.  If the plugin writes a new
            file it should return the new path.
        """
        return svg_path

    def on_convert_complete(self, result: TraceResult, options: dict[str, Any]) -> None:
        """Hook called when the full conversion pipeline has finished.

        Parameters
        ----------
        result:
            The :class:`~vector_studio.models.TraceResult` produced by
            :func:`~vector_studio.tracer.trace_image`.
        options:
            Arbitrary keyword options passed from the conversion pipeline.
        """
        pass
