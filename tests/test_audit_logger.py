import json
from pathlib import Path

import pytest

from vector_studio.audit_logger import AuditEvent, AuditLevel, AuditLogger


class TestAuditEvent:
    def test_to_dict(self):
        event = AuditEvent(AuditLevel.INFO, "convert", "alice", "image.png", {"preset": "logo"})
        d = event.to_dict()
        assert d["level"] == "info"
        assert d["action"] == "convert"
        assert d["user"] == "alice"
        assert d["resource"] == "image.png"
        assert d["details"] == {"preset": "logo"}
        assert "timestamp" in d


class TestAuditLogger:
    def test_info_log(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.info("convert", "alice", "image.png", {"engine": "vtracer"})
        events = logger.query()
        assert len(events) == 1
        assert events[0]["action"] == "convert"
        assert events[0]["user"] == "alice"
        assert events[0]["level"] == "info"

    def test_security_log(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.security("blocked_path_traversal", "system", "../etc/passwd")
        events = logger.query()
        assert len(events) == 1
        assert events[0]["level"] == "security"
        assert events[0]["action"] == "blocked_path_traversal"

    def test_query_by_user(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.info("convert", "alice", "a.png")
        logger.info("convert", "bob", "b.png")
        logger.info("batch", "alice", "folder")
        alice_events = logger.query(user="alice")
        assert len(alice_events) == 2
        assert all(e["user"] == "alice" for e in alice_events)

    def test_query_by_action(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.info("convert", "alice", "a.png")
        logger.info("batch", "bob", "folder")
        convert_events = logger.query(action="convert")
        assert len(convert_events) == 1
        assert convert_events[0]["action"] == "convert"

    def test_query_limit(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        for i in range(10):
            logger.info("convert", "user", f"img{i}.png")
        events = logger.query(limit=3)
        assert len(events) == 3

    def test_query_time_range(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.info("convert", "alice", "a.png")
        events = logger.query(start_time="2099-01-01T00:00:00")
        assert len(events) == 0
        events = logger.query(end_time="2000-01-01T00:00:00")
        assert len(events) == 0

    def test_multiple_log_files(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        logger.info("convert", "alice", "a.png")
        # Simulate a second day by writing directly
        second_file = tmp_path / "audit-2099-01-01.jsonl"
        second_file.write_text(
            json.dumps({
                "timestamp": "2099-01-01T00:00:00",
                "level": "info",
                "action": "batch",
                "user": "bob",
                "resource": "folder",
                "details": {},
            }) + "\n"
        )
        events = logger.query()
        assert len(events) == 2

    def test_ignores_corrupt_lines(self, tmp_path: Path):
        logger = AuditLogger(log_dir=tmp_path)
        log_file = tmp_path / f"audit-{logger._get_log_file().stem.split('-')[1]}.jsonl"
        log_file.write_text("not json\n", encoding="utf-8")
        events = logger.query()
        assert events == []
