"""xhs_engine: PPT → 小红书笔记图 出图引擎。

核心 KPI：让「相同内容」在机审眼里变成「不同笔记」（图差异化 + 文差异化）。
本包只负责「图」这一半：真实渲染 PPT + 换场景 + 透视 + 拼图 + 相似度自检 + 隐形去重。
"""

from .collage import make_collage
from .cover import cover_big_title, cover_collage, cover_scene_single
from .perspective import perspective_compose
from .ppt2img import pdf_to_pngs, ppt_to_images, ppt_to_pdf
from .similarity import find_too_similar, is_distinct, pairwise_phash
from .stealth import lsb_embed, pixel_jitter, reencode_jpeg

__all__ = [
    # PPT 转图
    "ppt_to_images",
    "ppt_to_pdf",
    "pdf_to_pngs",
    # 透视合成
    "perspective_compose",
    # 拼图
    "make_collage",
    # 封面
    "cover_scene_single",
    "cover_collage",
    "cover_big_title",
    # 相似度自检
    "pairwise_phash",
    "find_too_similar",
    "is_distinct",
    # 隐形去重
    "pixel_jitter",
    "lsb_embed",
    "reencode_jpeg",
]
