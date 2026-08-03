#!/bin/bash
# Render corpus/source/*.md into the messy binary formats the real corpus uses.
#
# The pipeline only ever reads corpus/rendered/. Holding the markdown back is
# what makes parsing accuracy measurable (spec section 6.1): extracted text can
# be diffed against the source that produced it.
#
#   bash scripts/render_corpus.sh            # render everything
#   bash scripts/render_corpus.sh D06        # render one doc_id
#   bash scripts/render_corpus.sh --check    # report tool availability and exit
#
# Target format comes from the `render:` front-matter field:
#   markdown | pdf | pdf-2col | pdf-scanned | docx | xlsx | png
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/corpus/source"
OUT="$ROOT/corpus/rendered"

# --- dependencies ------------------------------------------------------------
# pandoc          markdown -> docx, pdf, html
# libreoffice     docx -> pdf (better layout fidelity than pandoc for our case)
# pdftoppm        pdf -> raster (poppler-utils), for the scanned path
# img2pdf         raster -> pdf, completing the scan simulation
# convert         raster manipulation (ImageMagick): skew, noise, grayscale
declare -A TOOLS=(
  [pandoc]="pandoc"
  [libreoffice]="libreoffice"
  [pdftoppm]="poppler-utils"
  [img2pdf]="img2pdf"
  [convert]="imagemagick"
)

check_tools() {
  local missing=0
  echo "Tool availability:"
  for t in "${!TOOLS[@]}"; do
    if command -v "$t" >/dev/null 2>&1; then
      printf "  %-14s ok\n" "$t"
    else
      printf "  %-14s MISSING  (apt install %s)\n" "$t" "${TOOLS[$t]}"
      missing=1
    fi
  done
  return $missing
}

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: '$1' not found — apt install ${TOOLS[$1]}" >&2
    exit 1
  }
}

# --- front matter ------------------------------------------------------------
# Reads a scalar field from the YAML front matter. Deliberately simple: the
# front matter is authored by us and is flat.
fm() {
  local file="$1" key="$2"
  awk -v k="$key" '
    NR==1 && $0=="---" { inside=1; next }
    inside && $0=="---" { exit }
    inside && $0 ~ "^"k":" {
      sub("^"k":[ \t]*", "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$file"
}

# Strips the front matter so it does not appear in the rendered document.
body() {
  awk 'NR==1 && $0=="---" { inside=1; next } inside && $0=="---" { inside=0; next } !inside' "$1"
}

# --- renderers ---------------------------------------------------------------

render_markdown() {  # keeps the easy case in the corpus as a control group
  local src="$1" stem="$2"
  body "$src" > "$OUT/$stem.md"
}

render_docx() {
  local src="$1" stem="$2"
  require pandoc
  body "$src" | pandoc -f markdown -t docx -o "$OUT/$stem.docx"
}

render_pdf() {
  local src="$1" stem="$2" footer="$3"
  require pandoc
  body "$src" | pandoc -f markdown -o "$OUT/$stem.pdf" \
    -V geometry:margin=2.5cm \
    -V mainfont="DejaVu Sans" \
    ${footer:+-V footer-center="$footer"} \
    --pdf-engine=xelatex 2>/dev/null || {
      # xelatex is often absent; fall back via docx -> libreoffice, which also
      # handles CJK and Vietnamese diacritics without a TeX install.
      require libreoffice
      body "$src" | pandoc -f markdown -t docx -o "$OUT/.$stem.tmp.docx"
      libreoffice --headless --convert-to pdf --outdir "$OUT" \
        "$OUT/.$stem.tmp.docx" >/dev/null 2>&1
      mv "$OUT/.$stem.tmp.pdf" "$OUT/$stem.pdf"
      rm -f "$OUT/.$stem.tmp.docx"
    }
}

render_pdf_2col() {  # two-column: naive extraction interleaves the columns
  local src="$1" stem="$2"
  require pandoc
  body "$src" | pandoc -f markdown -o "$OUT/$stem.pdf" \
    -V geometry:margin=2cm -V classoption=twocolumn \
    -V mainfont="DejaVu Sans" --pdf-engine=xelatex 2>/dev/null || {
      echo "  ! two-column needs xelatex; emitting single-column for $stem" >&2
      render_pdf "$src" "$stem" ""
    }
}

render_pdf_scanned() {
  # The most important renderer in the file. A scanned page extracts to an
  # EMPTY STRING, so the document appears indexed while being unreachable.
  # That is demo block 1, and it cannot be faked with a normal PDF.
  local src="$1" stem="$2"
  require pdftoppm; require convert; require img2pdf
  render_pdf "$src" ".$stem.clean" ""
  pdftoppm -r 150 -png "$OUT/.$stem.clean.pdf" "$OUT/.$stem.page"
  local pages=("$OUT/.$stem.page"*.png)
  for p in "${pages[@]}"; do
    convert "$p" \
      -colorspace Gray \
      -rotate 0.4 \
      -attenuate 0.4 +noise Gaussian \
      -blur 0x0.3 \
      -brightness-contrast -5x10 \
      "$p"
  done
  img2pdf "${pages[@]}" -o "$OUT/$stem.pdf" 2>/dev/null
  rm -f "$OUT/.$stem.clean.pdf" "$OUT/.$stem.page"*.png
}

render_png() {  # screenshots: the answer exists only inside an image
  local src="$1" stem="$2"
  require pandoc; require convert
  body "$src" | pandoc -f markdown -t html -s \
    -V pagetitle="$stem" > "$OUT/.$stem.html"
  if command -v wkhtmltoimage >/dev/null 2>&1; then
    wkhtmltoimage --width 1280 --quality 90 "$OUT/.$stem.html" "$OUT/$stem.png" >/dev/null 2>&1
  else
    render_pdf "$src" ".$stem.img" ""
    pdftoppm -r 130 -png -singlefile "$OUT/.$stem.img.pdf" "$OUT/$stem"
    rm -f "$OUT/.$stem.img.pdf"
  fi
  rm -f "$OUT/.$stem.html"
}

render_xlsx() {
  # Tables become a real workbook. Each markdown table becomes its own sheet,
  # so multi-sheet parsing (only-first-sheet-read) is exercised.
  local src="$1" stem="$2"
  require libreoffice
  local csvdir="$OUT/.$stem.sheets"; mkdir -p "$csvdir"
  body "$src" | awk -v dir="$csvdir" '
    /^\|/ {
      if (!intable) { intable=1; n++; f=sprintf("%s/sheet%02d.csv", dir, n) }
      if ($0 ~ /^\|[ -]*\|/ && $0 ~ /---/) next          # separator row
      line=$0
      gsub(/^\| *| *\|$/, "", line)
      gsub(/ *\| */, ",", line)
      gsub(/\*\*/, "", line)
      print line > f
      next
    }
    { intable=0 }
  '
  if compgen -G "$csvdir/*.csv" >/dev/null; then
    for c in "$csvdir"/*.csv; do
      libreoffice --headless --convert-to xlsx --outdir "$OUT" "$c" >/dev/null 2>&1
    done
    # first sheet keeps the document name; the rest keep their sheet suffix
    local first="$OUT/sheet01.xlsx"
    [[ -f "$first" ]] && mv "$first" "$OUT/$stem.xlsx"
    for x in "$OUT"/sheet*.xlsx; do
      [[ -f "$x" ]] || continue
      mv "$x" "$OUT/$stem.$(basename "$x" .xlsx).xlsx"
    done
  else
    echo "  ! no tables found in $stem; skipping xlsx" >&2
  fi
  rm -rf "$csvdir"
}

# --- main --------------------------------------------------------------------

[[ "${1:-}" == "--check" ]] && { check_tools; exit $?; }

filter="${1:-}"
mkdir -p "$OUT"

shopt -s nullglob
rendered=0 skipped=0
for src in "$SRC"/*.md; do
  base="$(basename "$src" .md)"
  [[ "$base" == "README" ]] && continue
  [[ -n "$filter" && "$base" != "$filter".* ]] && continue

  fmt="$(fm "$src" render)"
  [[ -z "$fmt" ]] && { echo "  ! $base has no render: field; skipping" >&2; ((skipped++)); continue; }
  footer="$(fm "$src" footer)"

  printf "%-14s -> %s\n" "$base" "$fmt"
  case "$fmt" in
    markdown)    render_markdown    "$src" "$base" ;;
    docx)        render_docx        "$src" "$base" ;;
    pdf)         render_pdf         "$src" "$base" "$footer" ;;
    pdf-2col)    render_pdf_2col    "$src" "$base" ;;
    pdf-scanned) render_pdf_scanned "$src" "$base" ;;
    png)         render_png         "$src" "$base" ;;
    xlsx)        render_xlsx        "$src" "$base" ;;
    *) echo "  ! unknown render format '$fmt' for $base" >&2; ((skipped++)); continue ;;
  esac
  ((rendered++))
done

echo
echo "rendered $rendered, skipped $skipped -> corpus/rendered/"
echo
echo "Sanity check — a scanned document must extract to (almost) nothing."
echo "If pdftotext returns real text for a pdf-scanned file, the scan"
echo "simulation failed and demo block 1 will not work:"
echo
for f in "$OUT"/*.pdf; do
  [[ -f "$f" ]] || continue
  stem="$(basename "$f" .pdf)"
  want="$(fm "$SRC/$stem.md" render 2>/dev/null || echo '')"
  [[ "$want" == "pdf-scanned" ]] || continue
  if command -v pdftotext >/dev/null 2>&1; then
    chars=$(pdftotext "$f" - 2>/dev/null | tr -d '[:space:]' | wc -c)
    printf "  %-14s %s chars extracted " "$stem" "$chars"
    (( chars < 50 )) && echo "OK (silently unreachable)" || echo "PROBLEM — still readable"
  fi
done
