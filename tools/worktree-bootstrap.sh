#!/usr/bin/env bash
#
# Task 19-0 — bootstrap di un git worktree.
#
# Un `git worktree` contiene solo i file TRACCIATI. Restano fuori tutti quelli
# ignorati, fra cui i due che servono per far girare l'applicazione e i test:
#
#   .venv/              -> l'interprete con Flask, SQLAlchemy, ecc.
#   pyspendless/.env    -> DATABASE_URL, SECRET_KEY, credenziali OAuth
#
# Senza, `import pyspendless.app` fallisce e il test di contratto — che e' il
# criterio di rilascio dei subagent — non parte nemmeno.
#
# Questo script e' VERSIONATO, quindi esiste gia' dentro ogni worktree appena
# creato: non serve copiarcelo. Va solo eseguito come primo passo.
#
#   ./tools/worktree-bootstrap.sh          # prepara e basta
#   ./tools/worktree-bootstrap.sh --test   # prepara ed esegue il contratto
#
# Nel checkout principale e' un no-op: non crea symlink e usa il proprio venv.
# Eseguirlo due volte non fa danni.

set -euo pipefail

# --- dove sta il checkout principale ---------------------------------------
# `--git-common-dir` punta sempre al .git del worktree principale, anche da
# dentro un worktree secondario. Nel principale restituisce ".git", e il
# dirname e' "." -> MAIN_ROOT coincide con la cwd, e tutto diventa no-op.
MAIN_GIT="$(git rev-parse --git-common-dir)"
MAIN_ROOT="$(cd "$(dirname "$MAIN_GIT")" && pwd)"
HERE="$(git rev-parse --show-toplevel)"

echo "checkout principale : $MAIN_ROOT"
echo "worktree corrente   : $HERE"

if [ "$MAIN_ROOT" = "$HERE" ]; then
  echo "-> sei nel checkout principale, niente da collegare."
else
  # --- .env ----------------------------------------------------------------
  if [ -e "$HERE/pyspendless/.env" ]; then
    echo "-> pyspendless/.env gia' presente."
  elif [ -e "$MAIN_ROOT/pyspendless/.env" ]; then
    ln -s "$MAIN_ROOT/pyspendless/.env" "$HERE/pyspendless/.env"
    echo "-> collegato pyspendless/.env"
  else
    echo "!! $MAIN_ROOT/pyspendless/.env non esiste: l'app non partira'." >&2
    exit 1
  fi
fi

# --- interprete -------------------------------------------------------------
# Nel repo ci sono due virtualenv. Si usa quello che ha Flask installato.
PY=""
for cand in "$MAIN_ROOT/.venv/bin/python" "$MAIN_ROOT/pyspendless/.venv/bin/python"; do
  if [ -x "$cand" ] && "$cand" -c "import flask" >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "!! Nessun virtualenv con Flask fra:" >&2
  echo "   $MAIN_ROOT/.venv/bin/python" >&2
  echo "   $MAIN_ROOT/pyspendless/.venv/bin/python" >&2
  exit 1
fi
echo "-> interprete: $PY"

# --- DATABASE_URL relativo? -------------------------------------------------
# Da un worktree un percorso relativo punterebbe a un file inesistente.
# Il controllo e' testuale: non stampa valori, solo un avviso.
if [ "$MAIN_ROOT" != "$HERE" ] && [ -e "$HERE/pyspendless/.env" ]; then
  if grep -qE '^\s*DATABASE_URL\s*=\s*sqlite:///[^/]' "$HERE/pyspendless/.env" 2>/dev/null; then
    echo "!! DATABASE_URL sembra RELATIVO: da un worktree non trovera' il DB." >&2
    echo "   Rendilo assoluto in pyspendless/.env (file locale, non versionato)." >&2
  fi
fi

# --- il comando da usare ----------------------------------------------------
# L'interprete viene dal checkout principale, il codice dal worktree: Python
# mette la cwd in sys.path, quindi `pyspendless.*` risolve ai file locali.
echo
echo "Comando per il test di contratto (da eseguire con cwd = $HERE):"
echo "  $PY -m pyspendless.test.test_task19_0"

if [ "${1:-}" = "--test" ]; then
  echo
  cd "$HERE"
  exec "$PY" -m pyspendless.test.test_task19_0
fi
