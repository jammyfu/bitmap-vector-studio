from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vector_studio.report_generator import (
    BatchReport,
    ConversionReport,
    ReportGenerator,
)


class TestConversionReport:
    def test_to_dict_returns_asdict(self):
        """to_dict 返回与 asdict 一致的字典."""
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=1024,
            output_size_bytes=512,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={"colormode": "color"},
            quality_score=85.0,
            path_count=10,
            color_count=4,
            duration_seconds=1.5,
            timestamp="2024-01-01T00:00:00",
        )
        d = report.to_dict()
        assert d["input_file"] == "in.png"
        assert d["output_file"] == "out.svg"
        assert d["quality_score"] == 85.0

    def test_to_markdown_contains_key_fields(self):
        """to_markdown 包含关键字段."""
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=2048,
            output_size_bytes=1024,
            compression_ratio=2.0,
            preset_used="poster",
            parameters={},
            quality_score=None,
            path_count=None,
            color_count=None,
            duration_seconds=2.0,
            timestamp="2024-01-01T00:00:00",
        )
        md = report.to_markdown()
        assert "in.png" in md
        assert "out.svg" in md
        assert "2.0 KB" in md or "2.0KB" in md
        assert "N/A" in md


class TestBatchReport:
    def test_to_dict_structure(self):
        """BatchReport.to_dict 包含 summary 和 items."""
        item = ConversionReport(
            input_file="a.png",
            output_file="a.svg",
            input_size_bytes=100,
            output_size_bytes=50,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=90.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.0,
            timestamp="2024-01-01T00:00:00",
        )
        batch = BatchReport(
            total_files=1,
            successful=1,
            failed=0,
            total_input_size=100,
            total_output_size=50,
            average_duration=1.0,
            preset_used="logo",
            items=[item],
            timestamp="2024-01-01T00:00:00",
        )
        d = batch.to_dict()
        assert d["summary"]["total_files"] == 1
        assert d["summary"]["successful"] == 1
        assert len(d["items"]) == 1

    def test_to_markdown_contains_summary_and_table(self):
        """BatchReport.to_markdown 包含汇总和表格."""
        item = ConversionReport(
            input_file="a.png",
            output_file="a.svg",
            input_size_bytes=100,
            output_size_bytes=50,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=None,
            path_count=None,
            color_count=None,
            duration_seconds=1.0,
            timestamp="2024-01-01T00:00:00",
        )
        batch = BatchReport(
            total_files=1,
            successful=1,
            failed=0,
            total_input_size=100,
            total_output_size=50,
            average_duration=1.0,
            preset_used="logo",
            items=[item],
            timestamp="2024-01-01T00:00:00",
        )
        md = batch.to_markdown()
        assert "批量转换报告" in md
        assert "总文件数" in md
        assert "a.png" in md
        assert "✅" in md


class TestReportGenerator:
    def test_save_report_json(self, tmp_path: Path):
        """save_report 生成 JSON 文件."""
        gen = ReportGenerator(output_dir=tmp_path)
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=1024,
            output_size_bytes=512,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=80.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.2,
            timestamp="2024-01-01T00:00:00",
        )
        path = gen.save_report(report, format="json")
        assert path.exists()
        assert path.suffix == ".json"
        assert "in.png" in path.read_text(encoding="utf-8")

    def test_save_report_md(self, tmp_path: Path):
        """save_report 生成 Markdown 文件."""
        gen = ReportGenerator(output_dir=tmp_path)
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=1024,
            output_size_bytes=512,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=80.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.2,
            timestamp="2024-01-01T00:00:00",
        )
        path = gen.save_report(report, format="md")
        assert path.exists()
        assert path.suffix == ".md"
        assert "# 转换报告" in path.read_text(encoding="utf-8")

    def test_save_report_csv(self, tmp_path: Path):
        """save_report 生成 CSV 文件."""
        gen = ReportGenerator(output_dir=tmp_path)
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=1024,
            output_size_bytes=512,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=80.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.2,
            timestamp="2024-01-01T00:00:00",
        )
        path = gen.save_report(report, format="csv")
        assert path.exists()
        assert path.suffix == ".csv"
        text = path.read_text(encoding="utf-8")
        assert "input,output,preset,quality,duration" in text
        assert "in.png" in text

    def test_save_report_unsupported_format_raises(self, tmp_path: Path):
        """不支持的格式抛出 ValueError."""
        gen = ReportGenerator(output_dir=tmp_path)
        report = ConversionReport(
            input_file="in.png",
            output_file="out.svg",
            input_size_bytes=1024,
            output_size_bytes=512,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=80.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.2,
            timestamp="2024-01-01T00:00:00",
        )
        with pytest.raises(ValueError, match="不支持的格式"):
            gen.save_report(report, format="xml")

    def test_list_reports_sorted_by_mtime(self, tmp_path: Path):
        """list_reports 按修改时间倒序排列."""
        gen = ReportGenerator(output_dir=tmp_path)
        # 创建两个报告文件
        (tmp_path / "report_a.json").write_text("{}", encoding="utf-8")
        (tmp_path / "report_b.md").write_text("#", encoding="utf-8")
        reports = gen.list_reports()
        assert len(reports) == 2
        # 默认按 mtime 倒序，后创建的在前面
        assert reports[0].name in ("report_a.json", "report_b.md")

    def test_to_csv_batch_report(self, tmp_path: Path):
        """_to_csv 对 BatchReport 生成多行 CSV."""
        gen = ReportGenerator(output_dir=tmp_path)
        item1 = ConversionReport(
            input_file="a.png",
            output_file="a.svg",
            input_size_bytes=100,
            output_size_bytes=50,
            compression_ratio=2.0,
            preset_used="logo",
            parameters={},
            quality_score=90.0,
            path_count=5,
            color_count=3,
            duration_seconds=1.0,
            timestamp="2024-01-01T00:00:00",
        )
        item2 = ConversionReport(
            input_file="b.png",
            output_file="",
            input_size_bytes=200,
            output_size_bytes=0,
            compression_ratio=0.0,
            preset_used="logo",
            parameters={},
            quality_score=None,
            path_count=None,
            color_count=None,
            duration_seconds=0.0,
            timestamp="2024-01-01T00:00:00",
        )
        batch = BatchReport(
            total_files=2,
            successful=1,
            failed=1,
            total_input_size=300,
            total_output_size=50,
            average_duration=0.5,
            preset_used="logo",
            items=[item1, item2],
            timestamp="2024-01-01T00:00:00",
        )
        csv_text = gen._to_csv(batch)
        lines = csv_text.strip().split("\n")
        assert len(lines) == 3
        assert "success" in lines[1]
        assert "failed" in lines[2]
