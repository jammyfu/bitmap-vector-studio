from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.batch_template import BatchTemplateApplier
from vector_studio.template_market import Template, TemplateMarket


class TestBatchTemplateApplier:
    def test_apply_to_directory_success(self, tmp_path, monkeypatch):
        """批量应用模板成功."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="Logo", category="logo", data={"preset": "logo"}),
            "u1",
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")
        (input_dir / "img2.jpg").write_bytes(b"fake")

        applier = BatchTemplateApplier(market=market, max_workers=2)

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img1.svg"

        with patch("vector_studio.template_market.trace_image", return_value=mock_result):
            with patch.object(market, "_persist_index"):
                results = applier.apply_to_directory(tid, input_dir, output_dir)

        assert len(results) == 2
        assert all(isinstance(p, Path) for p in results)

    def test_apply_to_directory_template_not_found(self, tmp_path, monkeypatch):
        """模板不存在时抛出ValueError."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        applier = BatchTemplateApplier(market=market)

        with pytest.raises(ValueError, match="模板不存在"):
            applier.apply_to_directory("missing", tmp_path / "in", tmp_path / "out")

    def test_apply_to_directory_empty_input(self, tmp_path, monkeypatch):
        """空输入目录返回空结果."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="Logo", category="logo", data={"preset": "logo"}),
            "u1",
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        applier = BatchTemplateApplier(market=market)
        results = applier.apply_to_directory(tid, input_dir, output_dir)
        assert results == []

    def test_apply_to_directory_progress_callback(self, tmp_path, monkeypatch):
        """进度回调被正确调用."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="Logo", category="logo", data={"preset": "logo"}),
            "u1",
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")

        applier = BatchTemplateApplier(market=market, max_workers=1)
        progress_calls = []

        def on_progress(current, total, filename):
            progress_calls.append((current, total, filename))

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img1.svg"

        with patch("vector_studio.template_market.trace_image", return_value=mock_result):
            applier.apply_to_directory(tid, input_dir, output_dir, on_progress=on_progress)

        assert len(progress_calls) == 1
        assert progress_calls[0][0] == 1
        assert progress_calls[0][1] == 1
        assert progress_calls[0][2] == "img1.png"

    def test_apply_to_directory_skips_unsupported_files(self, tmp_path, monkeypatch):
        """跳过不支持的文件格式."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="Logo", category="logo", data={"preset": "logo"}),
            "u1",
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")
        (input_dir / "readme.txt").write_text("not an image")
        (input_dir / "script.py").write_text("print(1)")

        applier = BatchTemplateApplier(market=market, max_workers=1)

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img1.svg"

        with patch("vector_studio.template_market.trace_image", return_value=mock_result):
            results = applier.apply_to_directory(tid, input_dir, output_dir)

        assert len(results) == 1

    def test_apply_to_directory_failure_handling(self, tmp_path, monkeypatch):
        """单个文件失败不影响其他文件."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="Logo", category="logo", data={"preset": "logo"}),
            "u1",
        )

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "good.png").write_bytes(b"fake")
        (input_dir / "bad.png").write_bytes(b"fake")

        applier = BatchTemplateApplier(market=market, max_workers=2)

        def side_effect(*args, **kwargs):
            input_path = args[0]
            if "bad" in str(input_path):
                raise RuntimeError("trace failed")
            mock_result = MagicMock()
            mock_result.svg_path = output_dir / f"{input_path.stem}.svg"
            return mock_result

        with patch("vector_studio.template_market.trace_image", side_effect=side_effect):
            results = applier.apply_to_directory(tid, input_dir, output_dir)

        assert len(results) == 1
        assert results[0].name == "good.svg"
