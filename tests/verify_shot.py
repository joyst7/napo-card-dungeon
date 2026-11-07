import os, zlib, struct
import pyxel
OUT = os.environ.get('SHOT_OUT')


def shot(name):
    """環境変数 SHOT_OUT にフォルダを指定したときだけ、画面をPNGで保存する。"""
    if not OUT:
        return
    w, h = pyxel.width, pyxel.height
    cols = [(c >> 16 & 255, c >> 8 & 255, c & 255) for c in list(pyxel.colors)]
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(cols[pyxel.screen.pget(x, y)])

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    open(os.path.join(OUT, name + ".png"), "wb").write(png)


