from __future__ import annotations

from pathlib import Path

from .models import TraceOptions


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError("alpha_background must be a hex color like #ffffff.")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def prepare_input(
    input_path: Path,
    temp_png_path: Path,
    options: TraceOptions,
    *,
    smart_remove_bg: bool = False,
    enhance: str | None = None,
) -> Path:
    """Normalize a raster image to a PNG that VTracer can read consistently.

    This step handles EXIF orientation, transparent backgrounds, optional denoise,
    optional posterization, and optional downscaling for very large photos.
    """
    from PIL import Image, ImageFilter, ImageOps

    options.validate()
    input_path = Path(input_path)
    temp_png_path = Path(temp_png_path)
    temp_png_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)

        if options.max_input_side and max(img.size) > options.max_input_side:
            img.thumbnail((options.max_input_side, options.max_input_side), Image.Resampling.LANCZOS)

        # Smart background removal for logos
        if smart_remove_bg:
            from .smart_background import is_likely_logo, remove_background

            likely_logo, _ = is_likely_logo(img)
            if likely_logo:
                # Remove background and continue with the transparent result.
                bg_removed_path = temp_png_path.with_name(temp_png_path.stem + "_nobg.png")
                remove_background(input_path, bg_removed_path, tolerance=30)
                img = Image.open(bg_removed_path)
                img = ImageOps.exif_transpose(img)

        # Optional enhancement pipeline
        if enhance:
            from .enhance import adaptive_enhance

            img = adaptive_enhance(img, image_type=enhance)

        if img.mode in {"RGBA", "LA"} or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            if options.alpha_background is None:
                img = rgba
            else:
                background = Image.new("RGBA", rgba.size, _hex_to_rgb(options.alpha_background) + (255,))
                background.alpha_composite(rgba)
                img = background.convert("RGB")
        else:
            img = img.convert("RGB")

        if options.denoise:
            img = img.filter(ImageFilter.MedianFilter(size=3))

        if options.posterize is not None:
            img = ImageOps.posterize(img.convert("RGB"), int(options.posterize))

        img.save(temp_png_path, format="PNG", optimize=True)

    return temp_png_path
