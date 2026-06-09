"""批量模板应用系统.

将模板批量应用到多个图片，支持进度跟踪和结果收集.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from .template_market import TemplateMarket, Template


class BatchTemplateApplier:
    """批量模板应用器."""

    def __init__(self, market: TemplateMarket | None = None, max_workers: int = 4):
        self.market = market or TemplateMarket()
        self.max_workers = max_workers

    def apply_to_directory(
        self,
        template_id: str,
        input_dir: Path,
        output_dir: Path,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> list[Path]:
        """将模板应用到目录中的所有图片.

        Args:
            template_id: 模板ID
            input_dir: 输入图片目录
            output_dir: 输出目录
            on_progress: 进度回调(current, total, filename)

        Returns:
            成功转换的输出文件路径列表
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 获取模板
        template = self._get_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        # 收集输入文件
        input_files = [
            f for f in input_dir.iterdir()
            if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
        ]

        results: list[Path] = []
        total = len(input_files)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._apply_single, template, f, output_dir): f
                for f in input_files
            }

            completed = 0
            for future in as_completed(futures):
                input_file = futures[future]
                completed += 1
                try:
                    output_path = future.result()
                    if output_path:
                        results.append(output_path)
                except Exception as e:
                    print(f"[BatchTemplate] 失败: {input_file.name} - {e}")

                if on_progress:
                    on_progress(completed, total, input_file.name)

        return results

    def _get_template(self, template_id: str) -> Template | None:
        templates = self.market.discover_templates()
        for t in templates:
            if t.template_id == template_id:
                return t
        return None

    def _apply_single(self, template: Template, input_file: Path, output_dir: Path) -> Path | None:
        try:
            output_path = output_dir / f"{input_file.stem}.svg"
            self.market.apply_template(template.template_id, input_file, output_path)
            return output_path
        except Exception:
            return None
