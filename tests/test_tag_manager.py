from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector_studio.tag_manager import TagManager


@pytest.fixture(autouse=True)
def _isolated_tag_dir(monkeypatch, tmp_path):
    """Redirect tag storage into a temporary directory for every test."""
    monkeypatch.setattr(
        "vector_studio.tag_manager.Path.home",
        lambda: tmp_path,
    )


@pytest.fixture
def manager(tmp_path) -> TagManager:
    return TagManager(data_dir=tmp_path / ".bitmap_vector_studio")


class TestAddAndGet:
    def test_add_tag(self, manager):
        manager.add_tag("/path/to/file.png", "photo")
        assert manager.get_tags("/path/to/file.png") == ["photo"]

    def test_add_multiple_tags(self, manager):
        manager.add_tag("/path/to/file.png", "photo")
        manager.add_tag("/path/to/file.png", "landscape")
        tags = manager.get_tags("/path/to/file.png")
        assert "photo" in tags
        assert "landscape" in tags

    def test_add_duplicate_ignored(self, manager):
        manager.add_tag("/path/to/file.png", "photo")
        manager.add_tag("/path/to/file.png", "photo")
        assert manager.get_tags("/path/to/file.png") == ["photo"]


class TestRemove:
    def test_remove_tag(self, manager):
        manager.add_tag("/path/to/file.png", "photo")
        manager.remove_tag("/path/to/file.png", "photo")
        assert manager.get_tags("/path/to/file.png") == []

    def test_remove_last_tag_deletes_entry(self, manager, tmp_path):
        manager.add_tag("/path/to/file.png", "photo")
        manager.remove_tag("/path/to/file.png", "photo")
        # Internal dict should no longer hold the key
        assert "/path/to/file.png" not in manager._tags

    def test_remove_nonexistent_no_crash(self, manager):
        manager.remove_tag("/path/to/file.png", "photo")
        assert manager.get_tags("/path/to/file.png") == []


class TestListAndSearch:
    def test_list_all_tags(self, manager):
        manager.add_tag("/a.png", "photo")
        manager.add_tag("/b.svg", "vector")
        manager.add_tag("/c.png", "photo")
        tags = manager.list_all_tags()
        assert tags == ["photo", "vector"]

    def test_search_by_tag(self, manager):
        manager.add_tag("/a.png", "photo")
        manager.add_tag("/b.svg", "vector")
        manager.add_tag("/c.png", "photo")
        results = manager.search_by_tag("photo")
        assert sorted(results) == ["/a.png", "/c.png"]

    def test_search_by_tag_no_match(self, manager):
        assert manager.search_by_tag("nonexistent") == []


class TestSuggest:
    def test_suggest_by_extension_png(self, manager):
        suggestions = manager.suggest_tags("/image.png")
        assert "photo" in suggestions

    def test_suggest_by_extension_jpg(self, manager):
        suggestions = manager.suggest_tags("/image.jpg")
        assert "photo" in suggestions

    def test_suggest_by_extension_svg(self, manager):
        suggestions = manager.suggest_tags("/image.svg")
        assert "vector" in suggestions

    def test_suggest_by_preset_logo(self, manager):
        suggestions = manager.suggest_tags("/logo.png", preset="logo")
        assert "logo" in suggestions
        assert "branding" in suggestions

    def test_suggest_by_preset_poster(self, manager):
        suggestions = manager.suggest_tags("/poster.png", preset="poster")
        assert "poster" in suggestions
        assert "illustration" in suggestions

    def test_suggest_filters_existing(self, manager):
        manager.add_tag("/image.png", "photo")
        suggestions = manager.suggest_tags("/image.png")
        assert "photo" not in suggestions

    def test_suggest_unknown_preset(self, manager):
        suggestions = manager.suggest_tags("/file.png", preset="unknown")
        # Should only return extension-based suggestion
        assert suggestions == ["photo"]


class TestAutoTag:
    def test_auto_tag_png(self, manager):
        added = manager.auto_tag("/image.png")
        assert "photo" in added

    def test_auto_tag_with_preset(self, manager):
        added = manager.auto_tag("/logo.png", preset="logo")
        assert "logo" in added
        assert "branding" in added

    def test_auto_tag_no_duplicates(self, manager):
        manager.add_tag("/image.png", "photo")
        added = manager.auto_tag("/image.png")
        assert "photo" not in added


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        mgr = TagManager(data_dir=tmp_path / ".bitmap_vector_studio")
        mgr.add_tag("/a.png", "photo")
        del mgr

        mgr2 = TagManager(data_dir=tmp_path / ".bitmap_vector_studio")
        assert mgr2.get_tags("/a.png") == ["photo"]

    def test_load_corrupt_file(self, tmp_path):
        tag_file = tmp_path / ".bitmap_vector_studio" / "tags.json"
        tag_file.parent.mkdir(parents=True, exist_ok=True)
        tag_file.write_text("not json", encoding="utf-8")
        mgr = TagManager(data_dir=tmp_path / ".bitmap_vector_studio")
        assert mgr.get_tags("/a.png") == []

    def test_load_valid_file(self, tmp_path):
        tag_file = tmp_path / ".bitmap_vector_studio" / "tags.json"
        tag_file.parent.mkdir(parents=True, exist_ok=True)
        tag_file.write_text(
            json.dumps({"/b.svg": ["vector", "icon"]}),
            encoding="utf-8",
        )
        mgr = TagManager(data_dir=tmp_path / ".bitmap_vector_studio")
        assert mgr.get_tags("/b.svg") == ["vector", "icon"]

    def test_list_all_tags_empty(self, manager):
        assert manager.list_all_tags() == []

    def test_get_tags_missing_file(self, manager):
        assert manager.get_tags("/nonexistent.png") == []
