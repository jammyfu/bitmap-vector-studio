from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from vector_studio.batch_rules import Rule, RuleEngine


class TestRuleEngine:
    def test_add_rule_and_list_rules(self):
        """add_rule must append rules and list_rules must return them."""
        engine = RuleEngine()
        rule = Rule(name="png-to-svg", condition="suffix == '.png'", action="copy", action_params={"dest": "/tmp"})
        engine.add_rule(rule)
        rules = engine.list_rules()
        assert len(rules) == 1
        assert rules[0].name == "png-to-svg"

    def test_remove_rule(self):
        """remove_rule must delete a rule by name and return True if found."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="r1", condition="suffix == '.png'", action="copy", action_params={"dest": "/tmp"}))
        assert engine.remove_rule("r1") is True
        assert engine.list_rules() == []
        assert engine.remove_rule("r1") is False

    def test_priority_ordering(self):
        """Rules must be evaluated in descending priority order."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="low", condition="suffix == '.png'", action="copy", action_params={"dest": "/tmp"}, priority=1))
        engine.add_rule(Rule(name="high", condition="suffix == '.png'", action="move", action_params={"dest": "/tmp"}, priority=10))
        rules = engine.list_rules()
        assert rules[0].name == "high"
        assert rules[1].name == "low"

    def test_disabled_rule_is_skipped(self, tmp_path: Path):
        """Disabled rules must not be evaluated."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="disabled", condition="suffix == '.png'", action="copy", action_params={"dest": str(tmp_path)}, enabled=False))
        file = tmp_path / "test.png"
        file.write_text("x")
        results = engine.evaluate(file)
        assert results == []

    def test_evaluate_suffix_equality(self, tmp_path: Path):
        """evaluate must match suffix == '.png' correctly."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="match-png", condition="suffix == '.png'", action="copy", action_params={"dest": str(tmp_path / "out")}))
        file = tmp_path / "test.png"
        file.write_text("x")
        results = engine.evaluate(file)
        assert len(results) == 1
        assert results[0][0] == "match-png"
        assert results[0][1] is True

    def test_evaluate_size_greater_than(self, tmp_path: Path):
        """evaluate must match size > N correctly."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="big-files", condition="size > 5", action="copy", action_params={"dest": str(tmp_path / "out")}))
        small = tmp_path / "small.txt"
        small.write_text("hi")
        big = tmp_path / "big.txt"
        big.write_text("this is more than five bytes")
        assert engine.evaluate(small) == []
        results = engine.evaluate(big)
        assert len(results) == 1
        assert results[0][0] == "big-files"

    def test_evaluate_name_contains(self, tmp_path: Path):
        """evaluate must match name contains 'logo' correctly."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="logo-rule", condition="name contains 'logo'", action="copy", action_params={"dest": str(tmp_path / "out")}))
        logo = tmp_path / "my_logo.png"
        logo.write_text("x")
        other = tmp_path / "other.png"
        other.write_text("x")
        assert len(engine.evaluate(logo)) == 1
        assert engine.evaluate(other) == []

    def test_evaluate_suffix_in_list(self, tmp_path: Path):
        """evaluate must match suffix in ['.png', '.jpg'] correctly."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="images", condition="suffix in ['.png', '.jpg']", action="copy", action_params={"dest": str(tmp_path / "out")}))
        png = tmp_path / "img.png"
        png.write_text("x")
        gif = tmp_path / "anim.gif"
        gif.write_text("x")
        assert len(engine.evaluate(png)) == 1
        assert engine.evaluate(gif) == []

    def test_evaluate_unknown_action(self, tmp_path: Path):
        """evaluate must report failure for unknown actions."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="bad", condition="suffix == '.png'", action="fly", action_params={}))
        file = tmp_path / "test.png"
        file.write_text("x")
        results = engine.evaluate(file)
        assert len(results) == 1
        assert results[0][1] is False
        assert "未知动作" in results[0][2]

    def test_action_copy(self, tmp_path: Path):
        """copy action must duplicate the file to the destination."""
        engine = RuleEngine()
        dest = tmp_path / "dest"
        dest.mkdir()
        engine.add_rule(Rule(name="copy-rule", condition="suffix == '.txt'", action="copy", action_params={"dest": str(dest)}))
        source = tmp_path / "source.txt"
        source.write_text("copy me")
        engine.evaluate(source)
        assert (dest / "source.txt").exists()
        assert (dest / "source.txt").read_text() == "copy me"

    def test_action_move(self, tmp_path: Path):
        """move action must relocate the file to the destination."""
        engine = RuleEngine()
        dest = tmp_path / "dest"
        dest.mkdir()
        engine.add_rule(Rule(name="move-rule", condition="suffix == '.txt'", action="move", action_params={"dest": str(dest)}))
        source = tmp_path / "source.txt"
        source.write_text("move me")
        engine.evaluate(source)
        assert (dest / "source.txt").exists()
        assert not source.exists()

    def test_action_rename(self, tmp_path: Path):
        """rename action must rename the file according to the pattern."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="rename-rule", condition="suffix == '.txt'", action="rename", action_params={"pattern": "{stem}_renamed{suffix}"}))
        source = tmp_path / "source.txt"
        source.write_text("rename me")
        engine.evaluate(source)
        assert (tmp_path / "source_renamed.txt").exists()
        assert not source.exists()

    def test_action_delete(self, tmp_path: Path):
        """delete action must remove the file."""
        engine = RuleEngine()
        engine.add_rule(Rule(name="delete-rule", condition="suffix == '.tmp'", action="delete", action_params={}))
        source = tmp_path / "junk.tmp"
        source.write_text("delete me")
        engine.evaluate(source)
        assert not source.exists()

    def test_action_convert_calls_trace_image(self, tmp_path: Path):
        """convert action must invoke trace_image with correct arguments."""
        engine = RuleEngine()
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        engine.add_rule(
            Rule(
                name="convert-rule",
                condition="suffix == '.png'",
                action="convert",
                action_params={"output_dir": str(out_dir), "preset": "logo"},
            )
        )
        source = tmp_path / "image.png"
        source.write_text("fake png")
        with patch("vector_studio.tracer.trace_image") as mock_trace:
            engine.evaluate(source)
            mock_trace.assert_called_once()
            args = mock_trace.call_args
            assert args[0][0] == source
            assert args[0][1] == out_dir / "image.svg"
            assert args[1]["options"].colormode == "color"

    def test_action_tag_calls_tag_manager(self, tmp_path: Path):
        """tag action must invoke TagManager.add_tag for each tag."""
        engine = RuleEngine()
        engine.add_rule(
            Rule(
                name="tag-rule",
                condition="suffix == '.png'",
                action="tag",
                action_params={"tags": ["photo", "asset"]},
            )
        )
        source = tmp_path / "image.png"
        source.write_text("fake png")
        with patch("vector_studio.tag_manager.TagManager") as MockTM:
            instance = MockTM.return_value
            engine.evaluate(source)
            assert instance.add_tag.call_count == 2
            instance.add_tag.assert_any_call(str(source), "photo")
            instance.add_tag.assert_any_call(str(source), "asset")
