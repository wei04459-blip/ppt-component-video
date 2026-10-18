"""Local release checks; neither rendering success nor this report means published."""
from pathlib import Path
import re


def check_notes(out_root, notes, registry, semantic_review_required=True):
    results = []
    for note in notes:
        template_id = str(note["template_id"]).zfill(2)
        folder = Path(out_root) / str(note.get("id", template_id))
        # Count delivered images, not source slides or slots within a collage.
        images = sorted(p for p in folder.glob("*.png")
                        if re.fullmatch(r"\d{2}-(封面|内容页)\.png", p.name))
        expected = 1 + len(note["content_groups"])
        issues = []
        exception = note.get("publication_image_exception", "")
        if len(images) != expected:
            issues.append("实际输出图数与规划不一致，检查缺失文件或旧文件残留")
        if len(images) < 5 and not (isinstance(exception, str) and exception.strip()):
            issues.append("少于5张发布图片；保留历史渲染，发布例外须记录用户确认依据")
        title = note.get("title", "")
        if not title.strip() or len(title) > 20:
            issues.append("标题须非空且不超过20字符")
        topics = note.get("topics", [])
        normalized_topics = [str(t).strip().lstrip("#") for t in topics]
        if (not 8 <= len(normalized_topics) <= 10 or
                len(set(normalized_topics)) != len(normalized_topics) or
                any(not t for t in normalized_topics)):
            issues.append("须提供8–10个非空且不重复的相关话题，相关性仍需人工核对")
        if registry[template_id].get("approval_status") == "pending_user_review":
            issues.append("模板仍待用户验收")
        results.append({"id": note.get("id", template_id),
                        "actual_image_count": len(images), "planned_image_count": expected,
                        "image_exception_evidence": exception, "issues": issues,
                        "checks_passed": not issues})
    return {"checks_passed": bool(results) and all(r["checks_passed"] for r in results),
            "semantic_visual_review_required": semantic_review_required,
            "published": False, "notes": results}
