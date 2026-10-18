"""编排层：消费 Codex 的差异化清单 JSON，批量出 N 条笔记图。

数据契约（Codex 产出，本层消费）：
{
  "ppt": "xxx.pptx",
  "notes": [
    {
      "id": "01",
      "title": "...",
      "body": "...",
      "scene": "会议室",
      "cover_style": "scene_single",   # scene_single / collage / big_title
      "cover_page": 2,                 # 1-indexed 首图页
      "content_pages": [3, 6, 9],      # 1-indexed 内容页
      "topics": ["护理PPT", "..."],
    }
  ]
}
"""

import json
from pathlib import Path

import yaml

from .collage import make_collage
from .cover import cover_big_title, cover_collage, cover_scene_single
from .perspective import perspective_compose
from .ppt2img import ppt_to_images
from .similarity import find_too_similar
from .stealth import lsb_embed


def load_scene_library(yaml_path: str) -> dict:
    """加载场景库：scene 名 → {background, corners}。"""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("scenes", data)


def _write_copy(note: dict, out_dir: Path):
    """写文案 md：标题 + 正文 + 话题。"""
    lines = [f"# {note['title']}", ""]
    if note.get("body"):
        lines.append(note["body"])
        lines.append("")
    lines.append(" ".join("#" + t for t in note.get("topics", [])))
    (out_dir / "文案.md").write_text("\n".join(lines), encoding="utf-8")


def generate_note(note: dict, pages: list, scene_lib: dict, out_dir: str) -> list:
    """生成单条笔记的图（首图 + 内容图），返回图路径列表。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    scene = scene_lib[note["scene"]]
    bg = scene["background"]
    corners = scene["corners"]
    cover_style = note.get("cover_style", "scene_single")
    cover_page = note["cover_page"] - 1  # 转 0-indexed
    produced = []

    # 首图
    cover_path = out / "01-封面.png"
    if cover_style == "scene_single":
        cover_scene_single(bg, pages[cover_page], corners, str(cover_path))
    elif cover_style == "collage":
        collage_pages = [pages[cover_page]] + [pages[i - 1] for i in note["content_pages"][:1]]
        cover_collage(collage_pages, str(cover_path), header_text=note["title"])
    elif cover_style == "big_title":
        cover_big_title(pages[cover_page], str(cover_path), title=note["title"])
    else:
        cover_scene_single(bg, pages[cover_page], corners, str(cover_path))
    produced.append(str(cover_path))

    # 内容图（每条笔记内部统一用本条的 scene，但 PPT 页不同）
    for i, page_num in enumerate(note["content_pages"], start=2):
        p = out / f"{i:02d}-内容页.png"
        perspective_compose(bg, pages[page_num - 1], corners, str(p))
        produced.append(str(p))

    # 文案
    _write_copy(note, out)
    return produced


def run_pipeline(ppt_path: str, manifest_path: str, scene_lib_path: str, out_root: str,
                 dedup_threshold: int = 10, stealth: bool = True) -> dict:
    """主入口：PPT + 差异化清单 + 场景库 → 批量出 N 条笔记。

    返回 {"out": 输出目录, "too_similar": [(i,j,d), ...]} 供上层决策。
    """
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    scene_lib = load_scene_library(scene_lib_path)
    out_dir = Path(out_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 转图（一次转完所有页）
    pages = ppt_to_images(ppt_path, str(out_dir / "_pages"))

    # 2. 逐条生成
    for note in manifest["notes"]:
        note_dir = out_dir / note["id"]
        generate_note(note, pages, scene_lib, str(note_dir))

    # 3. 隐形去重：对每张图做 LSB 隐写（保证 MD5 不同）
    all_imgs = sorted(str(p) for p in out_dir.glob("*/0*-*.png"))
    if stealth:
        for i, p in enumerate(all_imgs):
            lsb_embed(p, p, seed=i)

    # 4. 相似度自检：首图之间两两 pHash，报告过于相似的
    covers = sorted(str(out_dir / n["id"] / "01-封面.png") for n in manifest["notes"])
    too_similar = find_too_similar(covers, dedup_threshold)

    return {"out": str(out_dir), "too_similar": too_similar}
