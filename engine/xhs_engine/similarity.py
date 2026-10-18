"""6.7 相似度自检引擎：pHash 把关，确保多条笔记图两两不重复（过机审主力）。"""

import imagehash
from PIL import Image


def phash(path: str):
    """计算感知哈希。"""
    return imagehash.phash(Image.open(path))


def pairwise_phash(paths: list) -> dict:
    """计算两两 pHash 汉明距离，返回 {(i, j): distance}。"""
    hashes = [phash(p) for p in paths]
    return {
        (i, j): int(hashes[i] - hashes[j])
        for i in range(len(hashes))
        for j in range(i + 1, len(hashes))
    }


def find_too_similar(paths: list, threshold: int = 10) -> list:
    """返回距离 < threshold 的 (i, j, distance) 列表。"""
    dists = pairwise_phash(paths)
    return [(i, j, d) for (i, j), d in dists.items() if d < threshold]


def is_distinct(paths: list, threshold: int = 10) -> bool:
    """全部两两距离 >= threshold 则返回 True。"""
    return not find_too_similar(paths, threshold)
