from __future__ import annotations

import json
import logging
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .svg_tools import optimize_svg_file, svg_stats
from .tracer import trace_image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Local market data helpers
# ---------------------------------------------------------------------------


def _template_data_dir() -> Path:
    """Return the directory used for template market data."""
    directory = Path.home() / ".bitmap_vector_studio" / "templates"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _template_index_path() -> Path:
    """Return the path to the local template index file."""
    return _template_data_dir() / "index.json"


def _template_ratings_path() -> Path:
    """Return the path to the local template ratings file."""
    return _template_data_dir() / "ratings.json"


def _load_template_index() -> list[dict[str, Any]]:
    """Load the template index from disk.

    Returns an empty list when the file does not exist or is unreadable.
    """
    path = _template_index_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_template_index(data: list[dict[str, Any]]) -> None:
    """Persist the template index to disk atomically."""
    path = _template_index_path()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    tmp.replace(path)


def _load_template_ratings() -> dict[str, dict[str, Any]]:
    """Load template ratings from disk."""
    path = _template_ratings_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_template_ratings(data: dict[str, dict[str, Any]]) -> None:
    """Persist template ratings to disk atomically."""
    path = _template_ratings_path()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Template data model
# ---------------------------------------------------------------------------


@dataclass
class Template:
    """A reusable vector template in the marketplace."""

    template_id: str
    name: str
    category: str
    tags: list[str] = field(default_factory=list)
    preview_url: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    author: str = ""
    rating: float = 0.0
    downloads: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the template to a dictionary."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "tags": list(self.tags),
            "preview_url": self.preview_url,
            "data": dict(self.data),
            "author": self.author,
            "rating": self.rating,
            "downloads": self.downloads,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Template:
        """Restore a template from a dictionary."""
        return cls(
            template_id=data.get("template_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            tags=list(data.get("tags", [])),
            preview_url=data.get("preview_url", ""),
            data=dict(data.get("data", {})),
            author=data.get("author", ""),
            rating=float(data.get("rating", 0.0)),
            downloads=int(data.get("downloads", 0)),
        )


# ---------------------------------------------------------------------------
# Template market
# ---------------------------------------------------------------------------


class TemplateMarket:
    """Smart template marketplace with discovery, recommendations and publishing."""

    def __init__(self) -> None:
        """Initialize the template market."""
        self._templates: dict[str, Template] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load templates from the local index file."""
        for item in _load_template_index():
            try:
                t = Template.from_dict(item)
                self._templates[t.template_id] = t
            except Exception as exc:
                logger.warning("Skipping invalid template index entry: %s", exc)

    def _persist_index(self) -> None:
        """Save the current template index to disk."""
        data = [t.to_dict() for t in self._templates.values()]
        _save_template_index(data)

    def discover_templates(
        self,
        query: str | None = None,
        category: str | None = None,
    ) -> list[Template]:
        """Discover templates with optional filtering.

        Args:
            query: Free-text search across name and tags.
            category: Filter by template category.

        Returns:
            List of matching templates.
        """
        results = list(self._templates.values())
        if category:
            results = [t for t in results if t.category.lower() == category.lower()]
        if query:
            q = query.lower()
            results = [
                t
                for t in results
                if q in t.name.lower()
                or any(q in tag.lower() for tag in t.tags)
            ]
        # Sort by rating descending, then downloads.
        results.sort(key=lambda t: (t.rating, t.downloads), reverse=True)
        return results

    def get_recommendations(self, user_id: str, context: dict[str, Any]) -> list[Template]:
        """Get AI-powered template recommendations for a user.

        Args:
            user_id: The user identifier.
            context: Context dictionary (e.g. ``{"image_type": "logo"}``).

        Returns:
            List of recommended templates.
        """
        # Simple heuristic recommendation engine based on context matching.
        image_type = context.get("image_type", "").lower()
        category_hint = context.get("category", "").lower()
        scores: dict[str, float] = {}

        for tid, t in self._templates.items():
            score = 0.0
            # Category match
            if category_hint and t.category.lower() == category_hint:
                score += 3.0
            # Tag match against image type
            if image_type:
                for tag in t.tags:
                    if image_type in tag.lower() or tag.lower() in image_type:
                        score += 2.0
            # Rating and popularity boost
            score += t.rating * 0.5
            score += min(t.downloads / 100.0, 2.0)
            scores[tid] = score

        sorted_ids = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [self._templates[tid] for tid in sorted_ids[:10]]

    def apply_template(
        self,
        template_id: str,
        input_path: Path,
        output_path: Path,
    ) -> Path:
        """Apply a template to an input image and produce an output SVG.

        Args:
            template_id: The template to apply.
            input_path: Source bitmap image.
            output_path: Destination SVG path.

        Returns:
            The output path.

        Raises:
            ValueError: If the template does not exist.
        """
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found.")

        template_data = template.data
        preset = template_data.get("preset", "poster")
        optimize = template_data.get("optimize", True)
        optimize_level = template_data.get("optimize_level", "basic")

        from .presets import options_from_preset

        opts = options_from_preset(preset)
        result = trace_image(
            input_path,
            output_path,
            opts,
            optimize=optimize,
            optimize_level=optimize_level,
        )
        template.downloads += 1
        self._persist_index()
        return result.svg_path

    def publish_template(self, template: Template, user_id: str) -> str:
        """Publish a new template to the market.

        Args:
            template: The template to publish.
            user_id: Publisher user identifier.

        Returns:
            The assigned template ID.
        """
        if not template.template_id:
            template.template_id = str(uuid.uuid4())
        template.author = user_id
        template.rating = 0.0
        template.downloads = 0
        self._templates[template.template_id] = template
        self._persist_index()
        logger.info("Published template %s by %s", template.template_id, user_id)
        return template.template_id

    def rate_template(self, template_id: str, user_id: str, rating: int) -> bool:
        """Rate a template.

        Args:
            template_id: The template identifier.
            user_id: The user giving the rating.
            rating: Rating value (1–5).

        Returns:
            ``True`` if the rating was recorded.

        Raises:
            ValueError: If *rating* is outside the 1–5 range.
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        if template_id not in self._templates:
            return False

        ratings = _load_template_ratings()
        tr = ratings.setdefault(template_id, {"ratings": {}, "count": 0, "sum": 0})
        old = tr["ratings"].get(user_id)
        tr["ratings"][user_id] = rating
        if old is not None:
            tr["sum"] = tr["sum"] - old + rating
        else:
            tr["sum"] += rating
            tr["count"] += 1
        tr["average"] = tr["sum"] / tr["count"]
        _save_template_ratings(ratings)

        self._templates[template_id].rating = tr["average"]
        self._persist_index()
        return True

    def get_template(self, template_id: str) -> Template | None:
        """Fetch a single template by ID.

        Args:
            template_id: The template identifier.

        Returns:
            The ``Template`` or ``None`` if not found.
        """
        return self._templates.get(template_id)


# ---------------------------------------------------------------------------
# Template editor
# ---------------------------------------------------------------------------


class TemplateEditor:
    """Editor for creating and modifying vector templates."""

    def load_template(self, template_path: Path) -> dict[str, Any]:
        """Load a template from a JSON file.

        Args:
            template_path: Path to the template JSON file.

        Returns:
            Template dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        with template_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def edit_template(self, template: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
        """Apply changes to a template dictionary.

        Args:
            template: Original template dictionary.
            changes: Dictionary of changes to merge.

        Returns:
            Updated template dictionary.
        """
        updated = dict(template)
        for key, value in changes.items():
            if isinstance(value, dict) and isinstance(updated.get(key), dict):
                updated[key] = {**updated[key], **value}
            elif isinstance(value, list) and isinstance(updated.get(key), list):
                # For lists, replace entirely rather than merge to keep predictable.
                updated[key] = list(value)
            else:
                updated[key] = value
        updated["updated_at"] = datetime.now(timezone.utc).isoformat()
        return updated

    def preview_template(self, template: dict[str, Any], sample_image: Path) -> Path:
        """Generate a preview SVG by applying the template to a sample image.

        Args:
            template: Template dictionary.
            sample_image: Path to a sample bitmap image.

        Returns:
            Path to the generated preview SVG.
        """
        preview_dir = _template_data_dir() / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        out = preview_dir / f"preview_{template.get('template_id', 'unknown')}.svg"

        from .presets import options_from_preset

        preset = template.get("data", {}).get("preset", "poster")
        opts = options_from_preset(preset)
        result = trace_image(sample_image, out, opts, optimize=True)
        return result.svg_path

    def save_template(self, template: dict[str, Any], output_path: Path) -> Path:
        """Save a template dictionary to a JSON file.

        Args:
            template: Template dictionary.
            output_path: Destination file path.

        Returns:
            The output path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(template, fh, indent=2, ensure_ascii=False, sort_keys=False)
            fh.write("\n")
        tmp.replace(output_path)
        return output_path
