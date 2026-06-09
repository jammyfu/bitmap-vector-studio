from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector_studio.search_engine import HistorySearch, SearchEngine, SearchResult


class TestSearchEngine:
    def test_search_exact_match(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "poster", "desc": "A poster preset"})
        results = engine.search("poster")
        assert len(results) == 1
        assert results[0].item == "item1"
        # exact match in name (10) + word match in desc (3) = 13
        assert results[0].score == 13.0
        assert "name" in results[0].matched_fields

    def test_search_prefix_match(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "posterize", "desc": "Posterize effect"})
        results = engine.search("post")
        assert len(results) == 1
        # prefix match in name (5) + prefix match in desc (5) = 10
        assert results[0].score == 10.0

    def test_search_contains_match(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "my_poster_file", "desc": "A file"})
        results = engine.search("poster")
        assert len(results) == 1
        assert results[0].score == 2.0

    def test_search_word_match(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "best poster ever", "desc": "A file"})
        results = engine.search("poster")
        assert len(results) == 1
        # word match in name (3) + contains match in desc (2) = 5
        assert results[0].score >= 3.0

    def test_search_with_filters(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "logo", "status": "completed"})
        engine.add("item2", {"name": "logo", "status": "failed"})
        results = engine.search("logo", filters={"status": "completed"})
        assert len(results) == 1
        assert results[0].item == "item1"

    def test_search_no_query_no_filters(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "logo"})
        results = engine.search("")
        assert results == []

    def test_search_limit(self):
        engine = SearchEngine()
        for i in range(30):
            engine.add(f"item{i}", {"name": f"test{i}"})
        results = engine.search("test", limit=10)
        assert len(results) == 10

    def test_fuzzy_search(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "poster", "desc": "A poster preset"})
        results = engine.fuzzy_search("postr")  # typo
        assert len(results) >= 1
        assert results[0].item == "item1"

    def test_clear(self):
        engine = SearchEngine()
        engine.add("item1", {"name": "logo"})
        engine.clear()
        results = engine.search("logo")
        assert results == []


class TestHistorySearch:
    def test_build_index_from_history(self, tmp_path: Path):
        history_file = tmp_path / "history.jsonl"
        record = {
            "task_id": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "input_path": "/home/user/image.png",
            "output_path": "/home/user/image.svg",
            "preset_name": "poster",
            "engine": "vtracer",
        }
        history_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

        search = HistorySearch(history_dir=tmp_path)
        results = search.search("image")
        assert len(results) == 1
        assert results[0].item["task_id"] == "abc"

    def test_search_with_status_filter(self, tmp_path: Path):
        history_file = tmp_path / "history.jsonl"
        record1 = {
            "task_id": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "input_path": "/home/user/image.png",
            "output_path": "/home/user/image.svg",
            "preset_name": "poster",
        }
        record2 = {
            "task_id": "def",
            "timestamp": "2024-01-02T00:00:00",
            "input_path": "/home/user/fail.png",
            "output_path": None,
            "preset_name": "logo",
        }
        history_file.write_text(
            json.dumps(record1) + "\n" + json.dumps(record2) + "\n",
            encoding="utf-8",
        )

        search = HistorySearch(history_dir=tmp_path)
        results = search.search("", status="completed")
        assert len(results) == 1
        assert results[0].item["task_id"] == "abc"

    def test_search_with_preset_filter(self, tmp_path: Path):
        history_file = tmp_path / "history.jsonl"
        record1 = {
            "task_id": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "input_path": "/home/user/image.png",
            "output_path": "/home/user/image.svg",
            "preset_name": "poster",
        }
        record2 = {
            "task_id": "def",
            "timestamp": "2024-01-02T00:00:00",
            "input_path": "/home/user/logo.png",
            "output_path": "/home/user/logo.svg",
            "preset_name": "logo",
        }
        history_file.write_text(
            json.dumps(record1) + "\n" + json.dumps(record2) + "\n",
            encoding="utf-8",
        )

        search = HistorySearch(history_dir=tmp_path)
        results = search.search("", preset="logo")
        assert len(results) == 1
        assert results[0].item["task_id"] == "def"

    def test_refresh(self, tmp_path: Path):
        history_file = tmp_path / "history.jsonl"
        record = {
            "task_id": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "input_path": "/home/user/image.png",
            "output_path": "/home/user/image.svg",
            "preset_name": "poster",
        }
        history_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

        search = HistorySearch(history_dir=tmp_path)
        assert len(search.search("image")) == 1

        # Add a new record and refresh
        record2 = {
            "task_id": "def",
            "timestamp": "2024-01-02T00:00:00",
            "input_path": "/home/user/new.png",
            "output_path": "/home/user/new.svg",
            "preset_name": "logo",
        }
        with history_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record2) + "\n")

        search.refresh()
        results = search.search("new")
        assert len(results) == 1
        assert results[0].item["task_id"] == "def"

    def test_empty_history(self, tmp_path: Path):
        search = HistorySearch(history_dir=tmp_path)
        results = search.search("anything")
        assert results == []

    def test_history_search_query(self, tmp_path: Path):
        history_file = tmp_path / "history.jsonl"
        record = {
            "task_id": "abc",
            "timestamp": "2024-01-01T00:00:00",
            "input_path": "/home/user/landscape.png",
            "output_path": "/home/user/landscape.svg",
            "preset_name": "photo",
        }
        history_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

        search = HistorySearch(history_dir=tmp_path)
        results = search.search("landscape")
        assert len(results) == 1
        assert results[0].score > 0
