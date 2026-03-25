from __future__ import annotations

from pathlib import Path
import io

from PIL import Image


def downscale_to_png_bytes(path: Path, max_side: int) -> bytes:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    longest = max(w, h)

    if longest > max_side:
        scale = max_side / float(longest)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
