"""Bitmap Vector Studio 报告生成器.

支持生成转换报告、批量报告、统计图表.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ConversionReport:
    """单次转换报告."""

    input_file: str
    output_file: str
    input_size_bytes: int
    output_size_bytes: int
    compression_ratio: float
    preset_used: str
    parameters: dict[str, Any]
    quality_score: float | None
    path_count: int | None
    color_count: int | None
    duration_seconds: float
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        return f"""# 转换报告

| 项目 | 值 |
|---|---|
| 输入文件 | `{self.input_file}` |
| 输出文件 | `{self.output_file}` |
| 输入大小 | {self.input_size_bytes / 1024:.1f} KB |
| 输出大小 | {self.output_size_bytes:.1f} KB |
| 压缩比 | {self.compression_ratio:.1f}x |
| 使用预设 | {self.preset_used} |
| 质量评分 | {self.quality_score or 'N/A'} |
| 路径数 | {self.path_count or 'N/A'} |
| 颜色数 | {self.color_count or 'N/A'} |
| 耗时 | {self.duration_seconds:.2f}s |
| 时间 | {self.timestamp} |
"""


@dataclass
class BatchReport:
    """批量转换报告."""

    total_files: int
    successful: int
    failed: int
    total_input_size: int
    total_output_size: int
    average_duration: float
    preset_used: str
    items: list[ConversionReport]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_files": self.total_files,
                "successful": self.successful,
                "failed": self.failed,
                "total_input_size_kb": self.total_input_size / 1024,
                "total_output_size_kb": self.total_output_size / 1024,
                "average_duration": self.average_duration,
                "preset_used": self.preset_used,
                "timestamp": self.timestamp,
            },
            "items": [item.to_dict() for item in self.items],
        }

    def to_markdown(self) -> str:
        lines = [
            "# 批量转换报告",
            "",
            f"- **总文件数**: {self.total_files}",
            f"- **成功**: {self.successful}",
            f"- **失败**: {self.failed}",
            f"- **总输入大小**: {self.total_input_size / 1024:.1f} KB",
            f"- **总输出大小**: {self.total_output_size:.1f} KB",
            f"- **平均耗时**: {self.average_duration:.2f}s",
            f"- **使用预设**: {self.preset_used}",
            f"- **生成时间**: {self.timestamp}",
            "",
            "| # | 文件 | 状态 | 输入 | 输出 | 耗时 |",
            "|---|---|---|---|---|---|",
        ]
        for i, item in enumerate(self.items, 1):
            status = "✅" if item.output_file else "❌"
            lines.append(
                f"| {i} | {Path(item.input_file).name} | {status} | "
                f"{item.input_size_bytes / 1024:.1f}KB | "
                f"{item.output_size_bytes:.1f}KB | {item.duration_seconds:.2f}s |"
            )
        return "\n".join(lines)


class ReportGenerator:
    """报告生成器."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path.home() / ".bitmap_vector_studio" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_report(
        self, report: ConversionReport | BatchReport, format: str = "json"
    ) -> Path:
        """保存报告."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(report, ConversionReport):
            base_name = f"convert_{Path(report.input_file).stem}_{timestamp}"
        else:
            base_name = f"batch_{timestamp}"

        if format == "json":
            path = self.output_dir / f"{base_name}.json"
            path.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        elif format == "md":
            path = self.output_dir / f"{base_name}.md"
            path.write_text(report.to_markdown(), encoding="utf-8")
        elif format == "csv":
            path = self.output_dir / f"{base_name}.csv"
            path.write_text(self._to_csv(report), encoding="utf-8")
        else:
            raise ValueError(f"不支持的格式: {format}")

        return path

    def _to_csv(self, report: ConversionReport | BatchReport) -> str:
        """转换为CSV."""
        if isinstance(report, ConversionReport):
            return (
                "input,output,preset,quality,duration\n"
                f"{report.input_file},{report.output_file},"
                f"{report.preset_used},{report.quality_score or ''},"
                f"{report.duration_seconds}"
            )
        else:
            lines = ["input,output,preset,quality,duration,status"]
            for item in report.items:
                status = "success" if item.output_file else "failed"
                lines.append(
                    f"{item.input_file},{item.output_file},"
                    f"{item.preset_used},{item.quality_score or ''},"
                    f"{item.duration_seconds},{status}"
                )
            return "\n".join(lines)

    def list_reports(self) -> list[Path]:
        """列出所有报告."""
        reports: list[Path] = []
        for ext in ("json", "md", "csv"):
            reports.extend(self.output_dir.glob(f"*.{ext}"))
        return sorted(reports, key=lambda p: p.stat().st_mtime, reverse=True)
