"""CLI国际化支持."""

import os
from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'zh-CN': {
        'convert.success': '转换完成: {path}',
        'convert.error': '转换失败: {error}',
        'convert.analyzing': '分析中...',
        'convert.recommending': '推荐预设: {preset} (置信度 {confidence}%)',
        'batch.progress': '[{current}/{total}] {filename} ... {status}',
        'batch.summary': '完成 {total} 张图片转换',
        'batch.failures': '失败 {failures}/{total}',
        'cache.cleared': '缓存已清空',
        'cache.status': '缓存状态: 内存 {memory_items} 项, 磁盘 {disk_items} 项',
        'deprecated.trace': '警告: `trace` 命令已弃用，请使用 `vector-studio convert <file>`',
        'deprecated.batch': '警告: `batch` 命令已弃用，请使用 `vector-studio convert batch <input> <output>`',
        'no_images': '未找到支持的图片。',
    },
    'en-US': {
        'convert.success': 'Conversion complete: {path}',
        'convert.error': 'Conversion failed: {error}',
        'convert.analyzing': 'Analyzing...',
        'convert.recommending': 'Recommended preset: {preset} (confidence {confidence}%)',
        'batch.progress': '[{current}/{total}] {filename} ... {status}',
        'batch.summary': 'Completed {total} image conversions',
        'batch.failures': 'Failed {failures}/{total}',
        'cache.cleared': 'Cache cleared',
        'cache.status': 'Cache status: memory {memory_items} items, disk {disk_items} items',
        'deprecated.trace': 'Warning: `trace` is deprecated, use `vector-studio convert <file>`',
        'deprecated.batch': 'Warning: `batch` is deprecated, use `vector-studio convert batch <input> <output>`',
        'no_images': 'No supported images found.',
    },
}

def get_locale() -> str:
    """获取当前语言环境."""
    return os.environ.get('BVS_LANG', 'zh-CN')

def t(key: str, **kwargs) -> str:
    """翻译."""
    locale = get_locale()
    text = TRANSLATIONS.get(locale, TRANSLATIONS['zh-CN']).get(key, key)
    return text.format(**kwargs)
