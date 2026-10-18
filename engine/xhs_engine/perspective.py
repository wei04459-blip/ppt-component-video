"""6.2 透视合成引擎：把 PPT 页四点透视贴合进背景图（背景换图）。

核心技术：OpenCV getPerspectiveTransform + warpPerspective。
src 四角 = PPT 页四角；dst 四角 = 背景中屏幕区域的四角。
"""

import cv2
import numpy as np
from PIL import Image


def perspective_compose(
    background_path: str,
    page_path: str,
    dst_corners,  # 背景中屏幕四角 [(x,y),(x,y),(x,y),(x,y)]，顺序：左上、右上、右下、左下
    out_path: str,
    feather: int = 3,  # 边缘羽化像素，0 = 不羽化
) -> str:
    """把 PPT 页透视贴合进背景图的屏幕区域，输出合成图。"""
    bg = Image.open(background_path).convert("RGB")
    page = Image.open(page_path).convert("RGB")

    w, h = page.size
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])  # PPT 页四角
    dst = np.float32(dst_corners)

    bg_cv = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
    page_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)

    # 透视变换
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(page_cv, M, (bg_cv.shape[1], bg_cv.shape[0]))

    # 目标四边形 mask（合成区域）
    mask = np.zeros(bg_cv.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask, dst.astype(np.int32), 255)

    # 羽化，让边缘过渡自然（去「贴图感」）
    if feather > 0:
        k = feather * 2 + 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)

    mask3 = mask[:, :, None].astype(np.float32) / 255.0
    result = (bg_cv * (1 - mask3) + warped * mask3).astype(np.uint8)

    Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB)).save(out_path)
    return str(out_path)
