"""
Reproduces the hit-rate table in the README.

    python medir-acerto.py                 # 100 samples, the shipped mosaic
    python medir-acerto.py --amostras 300  # tighter numbers, slower
    python medir-acerto.py --mosaico assets/mosaico-2.jpg

Why this file exists: the README states measured accuracy, and a measurement
nobody can repeat is just a claim with a number in it. Run this and you get
the same table, or you find out we were wrong.

METHOD, and its limits

Each sample takes a real tile, turns it into a plausible logo file — upscaled,
JPEG re-encoded, exposure shifted — and optionally crops its edges to simulate
a file framed differently from the mosaic. Then it searches all cells for it
and records where the right one ranked.

This is OPTIMISTIC on purpose, and reading it otherwise would be a mistake:
the query is derived from the mosaic itself, so it measures loss from
compression and framing, not the gap between someone's original artwork and
whatever rendering the organisers used. If a team submitted a wordmark and the
mosaic shows their icon, nothing here predicts that case.

The matching below mirrors index.html exactly: two background fills, five
scales with weights, 32x32 grayscale plus 16x16 colour. If you change one,
change the other, or this file stops being evidence about the shipped tool.
"""

import argparse
import io as _io
import random
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Missing dependencies. Run:  pip install pillow numpy")

# Same as ESCALAS in index.html. The weight makes the natural scale win ties:
# without it, extra variants give a wrong cell more chances to get lucky.
ESCALAS = [(1.18, 0.985), (1.0, 1.0), (0.85, 0.99), (0.72, 0.975), (0.60, 0.96)]

ENQUADRAMENTOS = [(0.0, "same"), (0.06, "6% tighter"), (0.10, "10% tighter"),
                  (0.18, "18% tighter"), (0.25, "25% tighter")]


def normalizar(M):
    M = M.astype(np.float64)
    return (M - M.mean(axis=1, keepdims=True)) / (M.std(axis=1, keepdims=True) + 1e-9)


def blocos(img, n, lado):
    """Every cell of the grid, reduced to `lado` x `lado` and normalised."""
    g = img.resize((n * lado, n * lado), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float64)
    if a.ndim == 2:
        a = a[:, :, None]
    canais = a.shape[2]
    a = a.reshape(n, lado, n, lado, canais).transpose(0, 2, 1, 3, 4)
    return normalizar(a.reshape(n * n, lado * lado * canais))


def gabaritos(logo):
    """The ten template variants the page builds for a dropped logo."""
    saida = []
    for fundo in ((0, 0, 0), (255, 255, 255)):
        for escala, peso in ESCALAS:
            base = Image.new("RGB", (128, 128), fundo)
            lado = int(round(128 * escala))
            o = (128 - lado) // 2
            base.paste(logo.resize((lado, lado), Image.LANCZOS), (o, o))
            cinza = np.asarray(base.convert("L").resize((32, 32), Image.LANCZOS), dtype=np.float64).ravel()
            cor = np.asarray(base.resize((16, 16), Image.LANCZOS), dtype=np.float64).ravel()
            saida.append((normalizar(cinza[None, :])[0], normalizar(cor[None, :])[0], peso))
    return saida


def fabricar_logo(mos, passo, idx, n, corte):
    """A plausible logo file for the project in cell `idx`."""
    lin, col = divmod(idx, n)
    x0, y0 = int(round(col * passo)), int(round(lin * passo))
    p = int(round(passo))
    g = mos.crop((x0, y0, x0 + p, y0 + p)).resize((256, 256), Image.LANCZOS)
    d = int(256 * corte)
    if d:
        g = g.crop((d, d, 256 - d, 256 - d)).resize((256, 256), Image.LANCZOS)
    buf = _io.BytesIO()
    g.save(buf, "JPEG", quality=random.choice([72, 85, 95]))
    buf.seek(0)
    g = Image.open(buf).convert("RGB")
    a = np.asarray(g, dtype=np.float64) * random.uniform(0.92, 1.08)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description="Reproduce the README's hit-rate table.")
    ap.add_argument("--mosaico", default="assets/mosaico.jpg")
    ap.add_argument("--grade", type=int, default=55, help="cells per side")
    ap.add_argument("--amostras", type=int, default=100)
    ap.add_argument("--topo", type=int, default=12, help="how many candidates the page shows")
    ap.add_argument("--semente", type=int, default=11, help="fixed so runs are comparable")
    args = ap.parse_args()

    n = args.grade
    mos = Image.open(args.mosaico).convert("RGB")
    passo = mos.size[0] / n
    print(f"mosaic {mos.size[0]}x{mos.size[1]}, grid {n}x{n}, cell {passo:.1f}px")

    print(f"pre-computing {n * n} cells...")
    C_cinza = blocos(mos.convert("L"), n, 32)
    C_cor = blocos(mos, n, 16)

    brilho = np.asarray(mos.convert("L").resize((n, n), Image.LANCZOS), dtype=np.float64).ravel()
    visiveis = [i for i in range(n * n) if brilho[i] > 12]
    print(f"{len(visiveis)} cells with visible content\n")

    print(f"{'your file vs the tile':>22} {'ranked #1':>12} {'in top ' + str(args.topo):>12} {'median':>8}")
    for corte, rotulo in ENQUADRAMENTOS:
        random.seed(args.semente)
        alvos = random.sample(visiveis, min(args.amostras, len(visiveis)))
        primeiro = dentro = 0
        postos = []
        for idx in alvos:
            logo = fabricar_logo(mos, passo, idx, n, corte)
            melhor = np.full(n * n, -2.0)
            for gc, gr, peso in gabaritos(logo):
                s = ((C_cinza @ gc) / gc.size * 0.5 + (C_cor @ gr) / gr.size * 0.5) * peso
                melhor = np.maximum(melhor, s)
            posto = int(np.where(np.argsort(-melhor) == idx)[0][0]) + 1
            postos.append(posto)
            primeiro += posto == 1
            dentro += posto <= args.topo
        q = len(alvos)
        print(f"{rotulo:>22} {primeiro:5d}/{q} {primeiro / q * 100:3.0f}% "
              f"{dentro:5d}/{q} {dentro / q * 100:3.0f}% {int(np.median(postos)):8d}")

    print("\nOptimistic by construction — see the note at the top of this file.")


if __name__ == "__main__":
    main()
