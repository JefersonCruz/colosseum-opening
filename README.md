# Colosseum Opening

**[Make yours →](https://jefersoncruz.github.io/colosseum-opening/)**

Drop your logo. It finds your tile among the ~3,000 in the Crypto World's Fair mosaic, rings it, and replaces it with your logo — sharp, never a pixelated 46px square — then settles into an end card you can put your own text on.

Nothing is uploaded. The search runs in your browser.

Interface in **English, 中文 and 日本語** — picked from your browser language, switchable at the top. The end-card text stays whatever you type.

---

## The part that is actually hard

Animating a zoom is easy. **Finding your tile in a grid of ~3,000 is not** — and without it nothing works, because every number in the animation depends on where your cell is.

So the page does that: it detects the grid, scores all 3,025 cells against your logo, and shows you the best candidates as thumbnails. You click yours.

It ranks, you confirm. That split is deliberate — see *How reliable is the search*.

---

## Use it

**In the browser** — [open the page](https://jefersoncruz.github.io/colosseum-opening/), drop your logo, pick your tile, press `F`, record.

**Two mosaics are available**, and you choose which to search: Colosseum's official one (55×55) and a second one published by @solana_sailor (55×53). Not every project is in both — if you cannot find yourself in one, switch and search the other. The second is only downloaded if you pick it.

Use the same logo file you submitted, at the best resolution you have: it is both what gets matched and what ends up on screen.

**From the command line**, if you prefer it or want to batch. Note it renders the plain version — the colour, pace and ending options live only in the browser tool:

```bash
pip install pillow numpy

# 1. save Colosseum's mosaic next to the scripts as mosaico.jpg
# 2. find your tile - writes candidatas.png for you to confirm
python localizar.py --logo my-logo.png --mosaico mosaico.jpg

# 3. render it
python gerar.py --linha 51 --coluna 39 --logo my-logo.png --mosaico mosaico.jpg   --colunas 55 --linhas 55 \
  --titulo "WHAT YOU DO, IN FIVE WORDS" \
  --frase "One sentence that earns the click." \
  --rodape "Your track &nbsp;·&nbsp; yoursite.com"
```

---

## Recording it

The stage is square. On a 16:9 monitor, fullscreen leaves black bars at the sides — so **record the square area, not the whole screen**. OBS or ScreenToGif will do it; the Windows Game Bar will not, it captures the whole window.

Runs about 18 seconds. X autoplays muted and loops, and the clip opens and closes on black, so it loops cleanly.

There is no download button, on purpose. Exporting video from the browser would mean rebuilding the animation on canvas, and `MediaRecorder` only emits WebM — which X frequently rejects and Safari handles badly. A screen recording is less work and a better file.

---

## How reliable is the search

Measured, not asserted — and it depends almost entirely on one thing: **whether your logo file is framed the way the mosaic frames it.**

Method: take 100 real tiles, turn each into a plausible logo file (upscaled, JPEG re-encoded, exposure shifted), then crop its edges by a given amount to simulate different framing, and search all 3,025 cells for it. Run against the 3072px mosaic this page actually ships.

| Your file vs the tile | Ranked #1 | Among the 12 shown |
|---|---|---|
| Same framing | **99%** | **100%** |
| 6% tighter | 75% | 81% |
| 10% tighter | 73% | 80% |
| 18% tighter | 53% | 66% |
| 25% tighter | 20% | 39% |

Read it honestly: if you have the file you submitted, it is close to certain. If your file is cropped noticeably tighter than the mosaic version (or the reverse), **it can fail** — and at the extreme it fails more often than it works.

That is why **you pick from thumbnails and there is a manual row/column box**. At 25% framing difference, six in ten people need that box. It is not an edge case.

Resolution matters more than it looks. The same test on a 2048px mosaic scored 63% at 10% framing difference and 45% at 18%; at 3072px those are 73% and 53%.

Three notes on the numbers:

- They are *optimistic*, because the query is derived from the mosaic itself. They measure loss from compression and framing, not the gap between your original artwork and whatever rendering the organisers used. If you submitted a wordmark and the mosaic shows your icon, no amount of this helps.
- The one fully independent data point is the VILIGION tile, searched with its original PNG which never passed through the mosaic: **rank 1, score 0.880 against 0.742** for the runner-up. Run inside Chrome instead of Python the same search gives 0.824 against 0.724 — canvas downsampling is not PIL's, but the ranking agrees.
- Searching the second mosaic for that same logo tops out at 0.638 with the candidates bunched together, which is what "not in this one" looks like.

---

## How it works

Your row and column give the centre of your cell as a fraction of the mosaic, `(fx, fy)`. Everything follows:

- **The camera push.** With `transform-origin: 0 0`, holding that point in the centre of the frame while scaling by `k` needs `tx = (0.5 - fx·k)·100%` and `ty = (0.5 - fy·k)·100%` — but the pan is then **clamped to the mosaic's edges**, so `u = -tx` is held inside `[0, k-1]`. Without the clamp, a cell near an edge makes the camera look past the image and the frame fills with black: measured on a cell four rows from the bottom, the void covered a third of the frame through the first two thirds of the push, and most of ~3,000 projects sit near some edge.
  Because of the clamp the cell is *not* always centred — it enters from a corner and slides to the middle as the zoom closes in. So the ring, the sharp logo and the darkening all follow the cell's real on-screen position rather than assuming the centre.
- **The sharp logo.** A cell is `100/n %` of the frame per unit of scale, so the logo's width at each step is that times `k`. Because width is linear in `k`, and because the width keyframes sit at the *same* percentages as the zoom keyframes with the same easing, the logo stays locked to the cell instead of sliding against it. Measured worst-case drift: **0.1%**.

That second point is the whole trick: it is why your logo appears the moment it is found, legible, instead of waiting out the zoom and cross-fading from a blurry square.

Two things worth knowing if you change the code:

- CSS applies an animation's timing function **inside each keyframe segment**. Keyframes at 25%/33% against 28%/64% diverge mid-segment even when the endpoints match. The marks have to line up. This was a real bug here, not a hypothetical.
- Grid detection by autocorrelation answered **54 for a 55×55 grid**, and one column off does not fail gracefully: the misalignment accumulates until crops straddle two tiles, and then nothing matches anything. Both implementations instead test which grid puts the gutters on the darkest pixels, which separated the right answer by 3× and yields a confidence number the page shows you.
- Columns and rows are detected **separately**. Assuming a square grid was a real bug: a 4096×3948 mosaic turned out to be 55 columns by 53 rows with square cells, and a single number aligned one axis while drifting off the other.

### Running it locally

`python -m http.server` in this folder, then open `localhost:8000`. Opening `index.html` straight from disk will not work: browsers refuse to let a `file://` page read the pixels of a local image, and without reading pixels there is no search. The page tells you if that happens.

---

## Translations

The UI strings live in one `IDIOMAS` object near the top of the script, three languages deep. Adding a fourth is adding a key to that object — every piece of visible text already goes through `T()` or a `data-t` attribute, so nothing is hardcoded.

The Chinese and Japanese were translated without a native speaker reviewing them. If something reads wrong, it is my error and worth fixing before you promote the page.

---

## Customizing

Title, line and footer are fields on the page, and `--titulo / --frase / --rodape / --chapeu` on the CLI. Leave one empty and it is dropped rather than leaving a gap.

Whether your logo is treated as dark-background art (blended, so the glow passes behind it) or light-background art (given its own white card) is decided from its average brightness, weighted by alpha. On the CLI, `--fundo` overrides the guess.

All timings live in one labelled block. Want it tighter for X? Scale them down — about 12s is a reasonable target.

---

## About the images

The MIT licence covers **the code**. It does not cover the images — see [NOTICE](NOTICE).

`assets/mosaico.jpg` is Colosseum's participants image, carrying the marks of roughly three thousand projects. It is here so the tool can work, and it is explicitly outside the MIT grant. Shipped at 3072px / quality 74 (1.9 MB): measured against the 4096px original, the smaller file matches just as reliably (0.880 against 0.880) and the two are visually indistinguishable at the sizes this page shows.

Posting about being a participant is ordinary use. Redistributing three thousand companies' marks as a packaged asset is not, and the licence on this code does not give you the right to.

---

## Who made this

Built by [VILIGION](https://github.com/JefersonCruz/VILIGION) while preparing our own submission — on-chain treasury monitoring with phone-call alerting, Tempo track. We are [@Viligion](https://x.com/Viligion) on X.

Use it, change it, strip the credit line if you want: it is MIT. If it saved you an afternoon and you feel like returning the favour, the VILIGION repo has a published contract for adding blockchain support and a conformance suite that makes a new network adapter about a weekend's work.
