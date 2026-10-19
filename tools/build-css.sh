#!/usr/bin/env bash
#
# Compila il CSS Tailwind di PySpendless.
#
# Scarica il binario standalone di Tailwind CLI se manca (decisione D2: nessun
# package.json, nessun Node runtime), poi compila il sorgente nel CSS servito
# dall'app.
#
# Il CSS compilato e' VERSIONATO: il deploy su PythonAnywhere e' un `git pull`,
# sul server non gira nessuna build. Il binario invece NON e' versionato
# (~50 MB), ed e' in .gitignore.
#
# Uso:
#   ./tools/build-css.sh            compila (minificato)
#   ./tools/build-css.sh --watch    ricompila a ogni salvataggio
#
set -euo pipefail

TAILWIND_VERSION="v4.3.3"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/tools/tailwindcss"
SRC="$ROOT/pyspendless/static/css/ps-tailwind.src.css"
OUT="$ROOT/pyspendless/static/css/ps-tailwind.css"

# --- quale binario serve a questa macchina ---------------------------------
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)  ASSET="tailwindcss-macos-arm64" ;;
  Darwin-x86_64) ASSET="tailwindcss-macos-x64" ;;
  Linux-aarch64) ASSET="tailwindcss-linux-arm64" ;;
  Linux-x86_64)  ASSET="tailwindcss-linux-x64" ;;
  *) echo "Piattaforma non gestita: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

# --- scarica il binario se manca -------------------------------------------
if [ ! -x "$BIN" ]; then
  URL="https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/${ASSET}"
  echo "Scarico Tailwind CLI ${TAILWIND_VERSION} (${ASSET})"
  echo "  da ${URL}"
  curl -fsSL --retry 3 -o "$BIN.tmp" "$URL"
  chmod +x "$BIN.tmp"
  mv "$BIN.tmp" "$BIN"
  echo "  installato in tools/tailwindcss"
fi

echo "Tailwind: $("$BIN" --help 2>&1 | head -1)"

if [ ! -f "$SRC" ]; then
  echo "Sorgente mancante: $SRC" >&2
  exit 1
fi

if [ "${1:-}" = "--watch" ]; then
  exec "$BIN" -i "$SRC" -o "$OUT" --watch
fi

"$BIN" -i "$SRC" -o "$OUT" --minify

SIZE=$(wc -c < "$OUT" | tr -d ' ')
echo "Compilato: pyspendless/static/css/ps-tailwind.css  ($((SIZE / 1024)) KB)"

if [ "$SIZE" -lt 5120 ]; then
  echo "ATTENZIONE: output sotto i 5 KB, probabilmente non ha trovato le classi." >&2
  exit 1
fi

if git -C "$ROOT" check-ignore -q "$OUT" 2>/dev/null; then
  echo "ERRORE: ps-tailwind.css risulta IGNORATO da git. Il deploy e' un" >&2
  echo "        git pull: se il CSS non e' versionato, in produzione manca." >&2
  exit 1
fi
