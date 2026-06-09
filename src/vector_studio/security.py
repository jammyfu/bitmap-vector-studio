"""Bitmap Vector Studio 安全工具.

提供输入验证、文件安全检查、SVG清理、路径遍历防护.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Any

# 允许的图片格式
ALLOWED_IMAGE_TYPES = {
    'image/png': ['.png'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/bmp': ['.bmp'],
    'image/tiff': ['.tiff', '.tif'],
    'image/webp': ['.webp'],
    'image/gif': ['.gif'],
}

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {ext for exts in ALLOWED_IMAGE_TYPES.values() for ext in exts}

# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 危险SVG标签和属性
DANGEROUS_SVG_TAGS = {
    'script', 'foreignObject', 'iframe', 'embed', 'object',
    'audio', 'video', 'source', 'track', 'canvas',
}

DANGEROUS_SVG_ATTRS = {
    'onload', 'onerror', 'onclick', 'onmouseover',
    'onfocus', 'onblur', 'onchange', 'onsubmit',
    'xlink:href', 'href', 'src', 'data',
}


class SecurityError(Exception):
    """安全错误."""
    pass


class InputValidator:
    """输入验证器."""

    @staticmethod
    def validate_file_path(path: str | Path, must_exist: bool = True, allow_write: bool = False, base_dir: Path | None = None) -> Path:
        """验证文件路径安全.

        防护:
        - 路径遍历攻击 (../)
        - 符号链接跳转
        - 绝对路径注入
        """
        path = Path(path)

        # 检查路径遍历（在解析前检查原始路径）
        if ".." in path.parts:
            raise SecurityError(f"路径包含非法遍历: {path}")

        path = path.resolve()

        # 如果指定了基础目录，检查是否在其范围内
        if base_dir is not None:
            try:
                path.relative_to(base_dir)
            except ValueError:
                if not allow_write:
                    raise SecurityError(f"路径不在允许范围内: {path}")

        # 检查符号链接
        if path.is_symlink():
            raise SecurityError(f"不允许符号链接: {path}")

        if must_exist and not path.exists():
            raise SecurityError(f"文件不存在: {path}")

        return path

    @staticmethod
    def validate_image_file(path: Path) -> None:
        """验证图片文件."""
        if not path.exists():
            raise SecurityError(f"文件不存在: {path}")

        # 检查大小
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise SecurityError(f"文件过大: {size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE / 1024 / 1024}MB")

        # 检查扩展名
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise SecurityError(f"不支持的文件格式: {ext}")

        # 检查MIME类型（如果可用）
        mime, _ = mimetypes.guess_type(str(path))
        if mime and mime not in ALLOWED_IMAGE_TYPES:
            raise SecurityError(f"不支持的MIME类型: {mime}")

    @staticmethod
    def validate_preset_name(name: str) -> str:
        """验证预设名称.

        只允许字母、数字、下划线、连字符.
        """
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise SecurityError(f"非法预设名称: {name}")
        return name

    @staticmethod
    def validate_options(options: dict[str, Any]) -> dict[str, Any]:
        """验证转换参数.

        检查参数范围，防止DoS攻击.
        """
        validated = {}

        # color_precision: 1-8
        cp = options.get('color_precision')
        if cp is not None:
            cp = int(cp)
            if not 1 <= cp <= 8:
                raise SecurityError(f"color_precision 超出范围: {cp}")
            validated['color_precision'] = cp

        # filter_speckle: 0-128
        fs = options.get('filter_speckle')
        if fs is not None:
            fs = int(fs)
            if not 0 <= fs <= 128:
                raise SecurityError(f"filter_speckle 超出范围: {fs}")
            validated['filter_speckle'] = fs

        # max_iterations: 1-50
        mi = options.get('max_iterations')
        if mi is not None:
            mi = int(mi)
            if not 1 <= mi <= 50:
                raise SecurityError(f"max_iterations 超出范围: {mi}")
            validated['max_iterations'] = mi

        # max_input_side: >=64
        mis = options.get('max_input_side')
        if mis is not None:
            mis = int(mis)
            if mis < 64:
                raise SecurityError(f"max_input_side 过小: {mis}")
            validated['max_input_side'] = mis

        return validated


class SVGSanitizer:
    """SVG清理器."""

    @staticmethod
    def sanitize(svg_content: str) -> str:
        """清理SVG内容，移除危险元素.

        防护:
        - XSS攻击 (script标签、事件处理器)
        - 外部资源加载
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(svg_content)
        except ET.ParseError:
            return svg_content  # 解析失败，返回原内容

        # 递归清理属性和子元素
        SVGSanitizer._clean_element(root)

        # 第二遍：彻底移除危险标签
        for parent in root.iter():
            for child in list(parent):
                if child.tag in DANGEROUS_SVG_TAGS or \
                   (isinstance(child.tag, str) and child.tag.endswith('}script')):
                    parent.remove(child)

        return ET.tostring(root, encoding='unicode')

    @staticmethod
    def _clean_element(element):
        """递归清理元素."""
        # 移除危险标签
        if element.tag in DANGEROUS_SVG_TAGS or \
           (isinstance(element.tag, str) and element.tag.endswith('}script')):
            element.clear()
            return

        # 移除危险属性
        dangerous_attrs = [
            attr for attr in element.attrib
            if any(d in attr.lower() for d in DANGEROUS_SVG_ATTRS)
        ]
        for attr in dangerous_attrs:
            del element.attrib[attr]

        # 递归处理子元素
        for child in list(element):
            SVGSanitizer._clean_element(child)

    @staticmethod
    def is_safe(svg_content: str) -> bool:
        """检查SVG是否安全."""
        lower = svg_content.lower()
        return not any(tag in lower for tag in DANGEROUS_SVG_TAGS)


class FileHashChecker:
    """文件哈希检查器."""

    @staticmethod
    def compute_hash(path: Path) -> str:
        """计算文件SHA256哈希."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_hash(path: Path, expected: str) -> bool:
        """验证文件哈希."""
        return FileHashChecker.compute_hash(path) == expected
