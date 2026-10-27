"""Local-only OCR bridge. Recognition is evidence, not verified source transcription."""
from __future__ import annotations
import argparse
import json
import os
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


def recognize(image_path: str | Path, *, language_correction: bool = False, backend: str = "apple_vision", rapidocr_python: str | None = None) -> dict:
    """Return Apple Vision lines, raw confidence and top-left normalized boxes."""
    if backend == "rapidocr":
        return recognize_rapid(image_path, python_path=rapidocr_python)
    if backend != "apple_vision":
        return {"available": False, "backend": backend, "lines": [], "issues": ["Unknown local OCR backend"]}
    base = {"available": False, "backend": "apple_vision", "lines": [], "issues": []}
    if sys.platform != "darwin":
        return {**base, "issues": ["Apple Vision OCR requires macOS; no external fallback was used"]}
    swift = shutil.which("swift")
    script = Path(__file__).with_name("local_ocr.swift")
    if not swift or not script.is_file():
        return {**base, "issues": ["Local Swift runtime or bundled Vision bridge is missing"]}
    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        return {**base, "issues": [f"Local image is missing: {path}"]}
    try:
        command = [swift, str(script), str(path)] + (["--language-correction"] if language_correction else [])
        result = subprocess.run(command, text=True, capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {**base, "issues": [f"Local OCR execution failed: {exc}"]}
    try:
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
            raise ValueError("Invalid OCR response")
        for line in data["lines"]:
            if not isinstance(line.get("text"), str) or len(line.get("box", [])) != 4:
                raise ValueError("Invalid OCR line")
            if not 0 <= float(line.get("confidence", -1)) <= 1:
                raise ValueError("Invalid OCR confidence")
        if result.returncode and not data.get("issues"):
            data.setdefault("issues", []).append(f"Vision bridge exited with code {result.returncode}")
        return data
    except (ValueError, TypeError, KeyError) as exc:
        return {**base, "issues": [f"Local OCR returned no usable JSON: {exc}", result.stderr.strip()[:1000]]}


_RAPID_PROGRAM = r"""
import sys,json,time
from pathlib import Path
try:
    import rapidocr
    from rapidocr import RapidOCR
    from PIL import Image
    folder=Path(rapidocr.__file__).parent/'models'
    files={'Det.model_path':folder/'PP-OCRv6_det_small.onnx','Cls.model_path':folder/'ch_ppocr_mobile_v2.0_cls_mobile.onnx','Rec.model_path':folder/'PP-OCRv6_rec_small.onnx'}
    missing=[str(p) for p in files.values() if not p.is_file()]
    if missing:
        print(json.dumps({'available':False,'backend':'rapidocr_onnxruntime','lines':[],'issues':['Bundled local model missing; no download attempted']+missing}));sys.exit(1)
    engine=RapidOCR(params={k:str(v) for k,v in files.items()})
    width,height=Image.open(sys.argv[1]).size
    start=time.monotonic();result=engine(sys.argv[1]);elapsed=time.monotonic()-start
    rows=[]
    if result.txts is not None:
        for text,score,polygon in zip(result.txts,result.scores,result.boxes):
            points=polygon.tolist();xs=[p[0] for p in points];ys=[p[1] for p in points]
            left=max(0.,min(xs)/width);top=max(0.,min(ys)/height);right=min(1.,max(xs)/width);bottom=min(1.,max(ys)/height)
            rows.append({'text':text,'confidence':float(score),'box':[left,top,max(0.,right-left),max(0.,bottom-top)],'polygon':[[x/width,y/height] for x,y in points]})
    print(json.dumps({'available':True,'backend':'rapidocr_onnxruntime','lines':rows,'issues':[] if rows else ['No text recognized'],'elapsed':elapsed,'coordinate_origin':'top-left','models':'PP-OCRv6 small / bundled local only'},ensure_ascii=False))
except Exception as exc:
    print(json.dumps({'available':False,'backend':'rapidocr_onnxruntime','lines':[],'issues':['Local RapidOCR failed: '+str(exc)]}))
"""


def recognize_rapid(image_path: str | Path, *, python_path: str | None = None) -> dict:
    """Optional isolated local RapidOCR backend; never installs or downloads models."""
    base = {"available": False, "backend": "rapidocr_onnxruntime", "lines": [], "issues": []}
    runtime = python_path or os.environ.get("CREATOR_RAPIDOCR_PYTHON")
    if not runtime and importlib.util.find_spec("rapidocr") is not None:
        runtime = sys.executable
    if not runtime or not Path(runtime).is_file():
        return {**base, "issues": ["Local RapidOCR Python runtime is unavailable; configure CREATOR_RAPIDOCR_PYTHON"]}
    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        return {**base, "issues": ["Local image is missing"]}
    try:
        result = subprocess.run([str(runtime), "-c", _RAPID_PROGRAM, str(path)], text=True, capture_output=True, timeout=120, check=False)
        data = json.loads(result.stdout.strip().splitlines()[-1])
        if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
            raise ValueError("Invalid RapidOCR response")
        return data
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        return {**base, "issues": [f"Local RapidOCR execution failed: {exc}"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local Apple Vision OCR; no network fallback")
    parser.add_argument("image")
    parser.add_argument("--out")
    parser.add_argument("--backend", choices=["apple_vision", "rapidocr"], default="apple_vision")
    parser.add_argument("--rapidocr-python")
    parser.add_argument("--language-correction", action="store_true")
    args = parser.parse_args()
    data = recognize(args.image, backend=args.backend, rapidocr_python=args.rapidocr_python, language_correction=args.language_correction)
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        print(output)
    sys.exit(0 if data.get("available") and data.get("lines") else 1)
