"""
Finds your project's tile inside the Colosseum participants mosaic.

    python localizar.py --logo my-logo.png --mosaico mosaico.jpg

Prints the cell and, more usefully, writes `candidatas.png`: a contact sheet
of the best guesses, enlarged, so you can confirm with your own eyes before
rendering a video around the wrong tile.

Why a contact sheet instead of just an answer: the mosaic tiles are ~46px and
JPEG-compressed, and a logo that is mostly a dark field (ours is) matches
weakly. The first version of this matcher confidently returned eight wrong
cells. Ranked guesses you verify beat one guess you trust.
"""

import argparse
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Missing dependencies. Run:  pip install pillow numpy")


def detectar_grade(img, minimo=20, maximo=140):
    """
    Descobre a grade testando qual divisao poe as calhas nos pixels mais
    escuros. Colunas e linhas SEPARADAS: um mosaico de 4096x3948 visto em
    24/10/2026 tinha 55 colunas por 53 linhas, e assumir grade quadrada
    alinhava um eixo e desalinhava o outro progressivamente.

    Autocorrelacao era o caminho obvio e respondeu 54 para uma grade de 55 -
    e uma coluna a menos nao falha com elegancia: o desalinhamento acumula
    ate os recortes pegarem duas celulas, e ai nada casa com nada.
    """
    g = np.asarray(img.convert("L"), dtype=np.float64)
    W, H = img.size
    col, lin = g.mean(axis=0), g.mean(axis=1)

    def varrer(perfil, tam):
        pontos = []
        for n in range(minimo, maximo + 1):
            i = np.round(np.arange(1, n) * tam / n).astype(int)
            i = i[(i > 0) & (i < tam)]
            if len(i) == 0:
                continue
            pontos.append((float(np.mean([perfil[i].mean(), perfil[i - 1].mean()])), n))
        pontos.sort()
        return pontos[0][1], (pontos[1][0] / pontos[0][0] if pontos[0][0] > 0 else 0.0)

    nc, conf_c = varrer(col, W)
    nl, conf_l = varrer(lin, H)
    return nc, nl, min(conf_c, conf_l)


def normalizar(a):
    a = a.astype(np.float64).ravel()
    return (a - a.mean()) / (a.std() + 1e-9)


# escala do logotipo dentro da celula -> peso. Varre os DOIS sentidos: arte
# estourando a celula (>1) e arte com folga (<1). A primeira versao so
# recortava para dentro, o que cobria metade dos casos - e a metade menos
# comum. Medido em 60 logotipos com 18% de diferenca de enquadramento, o
# acerto em 1o lugar subiu de 13% para 45%.
# O peso faz a escala natural ganhar o empate: sem ele, mais variantes davam
# mais chance de uma celula errada ter sorte, e o caso facil caia de 100%
# para 97%.
ESCALAS = [(1.18, 0.985), (1.0, 1.0), (0.85, 0.99), (0.72, 0.975), (0.60, 0.96)]


def procurar(mosaico, logo, nc, nl, topo=12):
    px = mosaico.size[0] / nc
    py = mosaico.size[1] / nl

    gabaritos = []
    for fundo in ((0, 0, 0), (255, 255, 255)):
        for s, peso in ESCALAS:
            base = Image.new("RGB", (128, 128), fundo)
            lado = int(round(128 * s))
            o = (128 - lado) // 2
            base.paste(logo.resize((lado, lado), Image.LANCZOS), (o, o))
            gabaritos.append((
                normalizar(np.asarray(base.convert("L").resize((32, 32), Image.LANCZOS))),
                normalizar(np.asarray(base.resize((16, 16), Image.LANCZOS))),
                peso,
            ))

    achados = []
    for lin in range(nl):
        for col in range(nc):
            x0, y0 = int(round(col * px)), int(round(lin * py))
            cel = mosaico.crop((x0, y0, int(round((col + 1) * px)), int(round((lin + 1) * py))))
            cinza = normalizar(np.asarray(cel.convert("L").resize((32, 32), Image.LANCZOS)))
            cor = normalizar(np.asarray(cel.convert("RGB").resize((16, 16), Image.LANCZOS)))
            melhor = max(((cinza * gc).mean() * 0.5 + (cor * gr).mean() * 0.5) * w
                         for gc, gr, w in gabaritos)
            achados.append((melhor, lin, col))

    achados.sort(reverse=True)
    return achados[:topo], px, py


def folha(mosaico, achados, px, py, caminho, por_linha=6):
    lado = int(round(px)) * 4
    linhas = (len(achados) + por_linha - 1) // por_linha
    folha = Image.new("RGB", (por_linha * lado, linhas * (lado + 18)), "black")
    try:
        from PIL import ImageDraw
        d = ImageDraw.Draw(folha)
    except ImportError:
        d = None
    for i, (score, lin, col) in enumerate(achados):
        x0, y0 = int(round(col * px)), int(round(lin * py))
        cel = mosaico.crop((x0, y0, int(round((col + 1) * px)), int(round((lin + 1) * py)))).resize((lado, lado), Image.LANCZOS)
        px, py = (i % por_linha) * lado, (i // por_linha) * (lado + 18)
        folha.paste(cel, (px, py))
        if d:
            d.text((px + 4, py + lado + 3), f"#{i+1}  linha {lin}  col {col}", fill=(140, 190, 230))
    folha.save(caminho)


def main():
    ap = argparse.ArgumentParser(description="Find your tile in the Colosseum mosaic.")
    ap.add_argument("--logo", required=True, help="your logo, ideally the same file you submitted")
    ap.add_argument("--mosaico", required=True, help="the participants mosaic image")
    ap.add_argument("--colunas", type=int, default=0, help="columns in the grid (default: autodetect)")
    ap.add_argument("--linhas", type=int, default=0, help="rows in the grid (default: autodetect)")
    ap.add_argument("--folha", default="candidatas.png", help="contact sheet to write")
    args = ap.parse_args()

    mosaico = Image.open(args.mosaico).convert("RGB")
    logo = Image.open(args.logo).convert("RGB")
    if mosaico.size[0] != mosaico.size[1]:
        print(f"note: mosaic is {mosaico.size[0]}x{mosaico.size[1]}, not square; grid detection assumes square cells")

    nc_auto, nl_auto, confianca = detectar_grade(mosaico)
    nc = args.colunas or nc_auto
    nl = args.linhas or nl_auto
    print(f"mosaic {mosaico.size[0]}x{mosaico.size[1]}, grid {nc}x{nl}, "
          f"cell {mosaico.size[0]/nc:.2f}x{mosaico.size[1]/nl:.2f}px")
    if not (args.colunas and args.linhas):
        print(f"grid confidence: {confianca:.1f}x better than the runner-up"
              + ("" if confianca >= 1.8 else "  <-- LOW. Count them yourself and pass --colunas/--linhas."))

    achados, px, py = procurar(mosaico, logo, nc, nl)
    print("\nbest guesses (confirm them in the contact sheet, do not just trust #1):")
    for i, (score, lin, col) in enumerate(achados, 1):
        cx = (col + 0.5) * px
        cy = (lin + 0.5) * py
        print(f"  #{i:2d}  score {score:.3f}   row {lin:2d} col {col:2d}   "
              f"center {cx/mosaico.size[0]*100:.2f}% {cy/mosaico.size[1]*100:.2f}%")

    folha(mosaico, achados, px, py, args.folha)
    print(f"\nwrote {args.folha} — open it, find yours, note its row and col.")
    print("Then:  python gerar.py --linha <row> --coluna <col> --colunas %d --linhas %d --logo %s --mosaico %s"
          % (nc, nl, args.logo, args.mosaico))


if __name__ == "__main__":
    main()
