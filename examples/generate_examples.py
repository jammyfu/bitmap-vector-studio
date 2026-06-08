"""Generate example images for Bitmap Vector Studio."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EXAMPLES_DIR = Path(__file__).resolve().parent


def create_geometric_shapes() -> Image.Image:
    """Create a 256x256 image with geometric shapes."""
    img = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(img)

    # Red circle
    draw.ellipse([20, 20, 100, 100], fill="red", outline="darkred", width=2)
    # Blue rectangle
    draw.rectangle([140, 30, 230, 120], fill="blue", outline="darkblue", width=2)
    # Green triangle (polygon)
    draw.polygon([(128, 180), (60, 240), (196, 240)], fill="green", outline="darkgreen", width=2)
    # Yellow star-ish shape
    draw.polygon([(30, 150), (50, 190), (90, 190), (60, 220), (70, 260), (30, 240), (-10, 260), (0, 220), (-30, 190), (10, 190)], fill="yellow", outline="orange", width=2)

    return img


def create_text_sample() -> Image.Image:
    """Create a 256x256 image with text."""
    img = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(img)

    # Try to use a default font, fallback to default if not available
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((20, 30), "Vector", fill="black", font=font_large)
    draw.text((20, 80), "Studio", fill="darkblue", font=font_large)
    draw.text((20, 140), "v0.2.0", fill="gray", font=font_small)
    draw.text((20, 180), "Bitmap → SVG", fill="darkgreen", font=font_small)

    # Add a simple border
    draw.rectangle([0, 0, 255, 255], outline="black", width=2)

    return img


def create_gradient_like() -> Image.Image:
    """Create a 256x256 image simulating a gradient with bands."""
    img = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(img)

    # Horizontal color bands to simulate gradient
    colors = [
        (255, 0, 0),    # red
        (255, 128, 0),  # orange
        (255, 255, 0),  # yellow
        (0, 255, 0),    # green
        (0, 255, 255),  # cyan
        (0, 0, 255),    # blue
        (128, 0, 255),  # purple
    ]
    band_height = 256 // len(colors)
    for i, color in enumerate(colors):
        y0 = i * band_height
        y1 = y0 + band_height
        draw.rectangle([0, y0, 255, y1], fill=color)

    # Add some circles on top
    draw.ellipse([60, 60, 196, 196], fill=(255, 255, 255), outline="black", width=3)
    draw.ellipse([90, 90, 166, 166], fill=(200, 200, 200), outline="black", width=2)

    return img


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    images = {
        "geometric_shapes.png": create_geometric_shapes(),
        "text_sample.png": create_text_sample(),
        "gradient_bands.png": create_gradient_like(),
    }

    for filename, img in images.items():
        path = EXAMPLES_DIR / filename
        img.save(path, "PNG")
        print(f"Created {path}")

    print("Example images generated successfully.")


if __name__ == "__main__":
    main()
