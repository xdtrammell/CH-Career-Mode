import struct
from typing import List

from .core import Song

MAGIC = b"\xEA\xEC\x33\x01"


def export_setlist_binary(order: List[Song], out_path: str) -> None:
    md5s: List[str] = []
    for s in order:
        if not s.chart_md5:
            raise RuntimeError(f"Missing chart MD5 for: {s.name}")
        md5s.append(s.chart_md5)

    with open(out_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<I", len(md5s)))
        for h in md5s:
            f.write(b"\x20")
            f.write(h.encode("ascii"))
            f.write(b"\x64\x00")


def read_setlist_md5s(path: str) -> List[str]:
    md5s: List[str] = []
    with open(path, "rb") as f:
        header = f.read(4)
        if header != MAGIC:
            raise RuntimeError("Invalid setlist header")
        (count,) = struct.unpack("<I", f.read(4))
        for _ in range(count):
            if f.read(1) != b"\x20":
                raise RuntimeError("Malformed entry")
            h = f.read(32).decode("ascii")
            if f.read(2) != b"\x64\x00":
                raise RuntimeError("Malformed tail")
            md5s.append(h)
    return md5s
