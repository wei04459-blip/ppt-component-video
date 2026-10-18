"""6.8 隐形去重：像素级微调兜底（人眼不可感知，哈希必不同）。

定位：锦上添花，不是主力。主力是换场景（显性差异化）。
这里解决「MD5 完全相同」这一层的兜底。
"""

import numpy as np
from PIL import Image


def pixel_jitter(path: str, out_path: str, max_delta: int = 2, seed=None) -> str:
    """随机微调每个像素 ±max_delta 的 RGB 值，人眼不可感知。"""
    rng = np.random.default_rng(seed)
    arr = np.array(Image.open(path).convert("RGB")).astype(np.int16)
    noise = rng.integers(-max_delta, max_delta + 1, size=arr.shape, dtype=np.int16)
    out = np.clip(arr + noise, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(out_path)
    return str(out_path)


def lsb_embed(path: str, out_path: str, seed=None) -> str:
    """LSB 隐写：最低有效位嵌入随机位，观感无损，哈希必变。"""
    rng = np.random.default_rng(seed)
    arr = np.array(Image.open(path).convert("RGB")).astype(np.uint8)
    bits = rng.integers(0, 2, size=arr.shape, dtype=np.uint8)
    arr = (arr & 0xFE) | bits  # 清零最低位，再嵌入随机位
    Image.fromarray(arr).save(out_path)
    return str(out_path)


def reencode_jpeg(path: str, out_path: str, quality: int = 90) -> str:
    """重新 JPEG 压缩，改变哈希。"""
    Image.open(path).convert("RGB").save(out_path, "JPEG", quality=quality)
    return str(out_path)
