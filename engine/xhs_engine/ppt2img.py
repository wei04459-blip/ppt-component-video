"""6.1 PPT 转图引擎：.pptx → 逐页 PNG（真实渲染，逐字准确）。

技术路线：LibreOffice headless 转 PDF → pymupdf 渲染 PNG。
图片型 PPT（文字不可提取）也能像素级原样保留，不会乱码/失真。
"""

import subprocess
from pathlib import Path

import pymupdf

SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"


def ppt_to_pdf(ppt_path: str, out_dir: str) -> str:
    """LibreOffice headless 把 pptx 转成 PDF，返回 PDF 路径。"""
    ppt = Path(ppt_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(out), str(ppt)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice 转换失败: {result.stderr[-500:]}")

    pdf = out / (ppt.stem + ".pdf")
    if not pdf.exists():
        raise FileNotFoundError(f"PDF 未生成: {pdf}")
    return str(pdf)


def pdf_to_pngs(pdf_path: str, out_dir: str, dpi: int = 150) -> list:
    """pymupdf 把 PDF 逐页渲染成 PNG，返回 PNG 路径列表。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    paths = []
    try:
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(dpi=dpi)
            p = out / f"page_{i + 1:02d}.png"
            pix.save(str(p))
            paths.append(str(p))
    finally:
        doc.close()
    return paths


def ppt_to_images(ppt_path: str, out_dir: str, dpi: int = 150) -> list:
    """一步到位：pptx → 逐页 PNG。返回 PNG 路径列表。"""
    pdf = ppt_to_pdf(ppt_path, out_dir)
    return pdf_to_pngs(pdf, out_dir, dpi)
