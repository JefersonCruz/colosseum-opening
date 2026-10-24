"""
Renders the opening animation for YOUR tile.

    python gerar.py --linha 51 --coluna 39 --logo my-logo.png --mosaico mosaico.jpg

Writes ./abertura/ with a self-contained page. Open index.html, press F, record.

All the geometry below comes from two numbers — your row and column — so the
camera push always lands on your tile and the sharp logo always matches the
size of the tile it is replacing. Nothing here is hand-tuned per project.
"""

import argparse
import os
import shutil
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Missing dependencies. Run:  pip install pillow numpy")

GABARITO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo.html")


def main():
    ap = argparse.ArgumentParser(description="Render the Colosseum opening for your tile.")
    ap.add_argument("--linha", type=int, required=True, help="your row, from localizar.py")
    ap.add_argument("--coluna", type=int, required=True, help="your column, from localizar.py")
    ap.add_argument("--colunas", type=int, default=55, help="columns in the grid (default 55)")
    ap.add_argument("--linhas", type=int, default=0, help="rows in the grid (default: same as columns)")
    ap.add_argument("--logo", required=True, help="your logo — the highest resolution you have")
    ap.add_argument("--mosaico", required=True, help="the participants mosaic image")
    ap.add_argument("--saida", default="abertura", help="output folder")
    ap.add_argument("--titulo", default="", help="big line under the logo (default: none)")
    ap.add_argument("--frase", default="", help="smaller line under that")
    ap.add_argument("--rodape", default="Crypto World&rsquo;s Fair &nbsp;·&nbsp; Colosseum",
                    help="bottom line")
    ap.add_argument("--chapeu", default="Crypto World&rsquo;s Fair &nbsp;·&nbsp; Colosseum",
                    help="line shown over the full mosaic at the start")
    ap.add_argument("--fundo", choices=["auto", "escuro", "claro"], default="auto",
                    help="is your logo made for a dark background? (default: detect)")
    args = ap.parse_args()

    nc = args.colunas
    nl = args.linhas or nc
    if not (0 <= args.linha < nl and 0 <= args.coluna < nc):
        sys.exit(f"row must be 0-{nl-1} and column 0-{nc-1}.")

    # ---- geometry ----------------------------------------------------------
    # centre of your cell, as a fraction of the mosaic
    fx = (args.coluna + 0.5) / nc
    fy = (args.linha + 0.5) / nl

    # Zoom so your cell ends at 29% of the frame — big enough to read, small
    # enough that the neighbours still show you were one of many.
    kmax = 0.29 * nc
    k2, k3 = kmax * 0.15625, kmax * 0.4375

    # Pan is CLAMPED to the mosaic edges, like a map viewer. Centring a cell
    # near an edge makes the camera look past the image and the frame fills
    # with black - measured on VILIGION's cell, 4th from the bottom, the void
    # covered a third of the frame through the first two thirds of the push.
    # Most of ~3,000 projects sit near some edge.
    #
    # u is how far the image slides left/up, in screens. Centring wants
    # u = f*k - 0.5; the edges allow only 0 <= u <= k-1.
    def camera(k):
        ux = max(0.0, min(fx * k - 0.5, k - 1))
        uy = max(0.0, min(fy * k - 0.5, k - 1))
        # where the cell actually lands on screen, after clamping
        return -ux * 100, -uy * 100, (fx * k - ux) * 100, (fy * k - uy) * 100

    celula = 100.0 / nc         # % of the frame per unit of scale
    larg = [celula * k for k in (1, k2, k3, kmax)]
    anel = [w * 1.18 for w in larg]

    # ---- light or dark logo ------------------------------------------------
    logo = Image.open(args.logo).convert("RGB")
    modo = args.fundo
    if modo == "auto":
        brilho = float(np.asarray(logo.convert("L"), dtype=np.float64).mean())
        modo = "claro" if brilho > 118 else "escuro"
        print(f"logo mean brightness {brilho:.0f} -> treating it as '{modo}'")
    # 'escuro': art already sits on black, so screen blend drops the black and
    # lets the glow pass behind it. 'claro': art needs its own light card, and
    # screen blend would wash the whole frame out.
    if modo == "escuro":
        estilo_logo = "mix-blend-mode:screen;"
    else:
        estilo_logo = "border-radius:4%; background:#fff; padding:1.2%;"

    # ---- write -------------------------------------------------------------
    os.makedirs(args.saida, exist_ok=True)
    shutil.copy(args.mosaico, os.path.join(args.saida, "mosaico.jpg"))
    shutil.copy(args.logo, os.path.join(args.saida, "logo.png"))

    with open(GABARITO, encoding="utf-8") as f:
        html = f.read()

    cam = {i: camera(k) for i, k in enumerate((1, k2, k3, kmax))}
    subs = {
        "{{TX1}}": f"{cam[0][0]:.2f}", "{{TY1}}": f"{cam[0][1]:.2f}",
        "{{TX2}}": f"{cam[1][0]:.2f}", "{{TY2}}": f"{cam[1][1]:.2f}",
        "{{TX3}}": f"{cam[2][0]:.2f}", "{{TY3}}": f"{cam[2][1]:.2f}",
        "{{TX4}}": f"{cam[3][0]:.2f}", "{{TY4}}": f"{cam[3][1]:.2f}",
        "{{SX1}}": f"{cam[0][2]:.2f}", "{{SY1}}": f"{cam[0][3]:.2f}",
        "{{SX2}}": f"{cam[1][2]:.2f}", "{{SY2}}": f"{cam[1][3]:.2f}",
        "{{SX3}}": f"{cam[2][2]:.2f}", "{{SY3}}": f"{cam[2][3]:.2f}",
        "{{SX4}}": f"{cam[3][2]:.2f}", "{{SY4}}": f"{cam[3][3]:.2f}",
        "{{K2}}": f"{k2:.4f}", "{{K3}}": f"{k3:.4f}", "{{K4}}": f"{kmax:.4f}",
        "{{W1}}": f"{larg[0]:.2f}", "{{W2}}": f"{larg[1]:.2f}",
        "{{W3}}": f"{larg[2]:.2f}", "{{W4}}": f"{larg[3]:.2f}",
        "{{A1}}": f"{anel[0]:.2f}", "{{A2}}": f"{anel[1]:.2f}",
        "{{A3}}": f"{anel[2]:.2f}", "{{A4}}": f"{anel[3]:.2f}",
        "{{ESTILO_LOGO}}": estilo_logo,
        "{{CHAPEU}}": args.chapeu,
        "{{TITULO}}": args.titulo,
        "{{FRASE}}": args.frase,
        "{{RODAPE}}": args.rodape,
        "{{LINHA}}": str(args.linha), "{{COLUNA}}": str(args.coluna),
        "{{GRADE}}": f"{nc}x{nl}",
        "{{FX}}": f"{fx*100:.2f}", "{{FY}}": f"{fy*100:.2f}",
    }
    for k, v in subs.items():
        html = html.replace(k, v)
    if "{{" in html:
        resto = html[html.index("{{"): html.index("{{") + 40]
        sys.exit(f"template still has an unreplaced placeholder near: {resto}")

    # lines left empty should not leave a gap where text would have been
    for ident in ("titulo", "frase"):
        if not getattr(args, ident):
            html = html.replace(f'<div class="linha" id="{ident}"></div>', "")

    destino = os.path.join(args.saida, "index.html")
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    print(f"\ncell: row {args.linha}, col {args.coluna} of a {nc}x{nl} grid")
    print(f"centre: {fx*100:.2f}% {fy*100:.2f}%   final zoom: {kmax:.1f}x")
    print(f"wrote {destino}")
    print("\nOpen it, press F for fullscreen, R to replay. Record the square area.")


if __name__ == "__main__":
    main()
