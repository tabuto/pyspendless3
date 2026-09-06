# Task 18-0: Deploy su PythonAnywhere via GitHub Actions (`deploy.yml`)

## Obiettivo

Automatizzare il deploy dell'istanza PythonAnywhere `tabuto.pythonanywhere.com`
tramite un **workflow GitHub Actions** che, usando l'**API token** di PA:

1. esegue una `git pull` nella working copy del progetto sul server PA
   (`git pull` in `$PA_REPO_PATH`), da una console bash aperta via API;
2. **riavvia la web app** (reload del dominio via API).

> **Cambio di approccio.** La prima stesura prevedeva uno script locale
> `deploy-pyspendless.sh` con i segreti in `pyspendless/.env`. Si è invece
> optato per **GitHub Actions**: il workflow è versionato, i segreti stanno nei
> **GitHub repository secrets** (mai nel repo), e il deploy parte da GitHub
> senza bisogno che nessuno lanci lo script da locale. Lo script `.sh` e le
> chiavi `PA_*` in `.env` **non fanno più parte di questo task**.

## Stato attuale

Esiste già una bozza del workflow, **non ancora committata**:
`pyspendless/.github/workflows/deploy.yml` (visibile in `git status` come
`?? pyspendless/.github/`).

### ⚠️ Blocco n.1 — posizione del file

GitHub Actions individua i workflow **solo** in
`<root-del-repo>/.github/workflows/`. La root del repo git è
`/Users/fradidio/Sviluppo/pyspendless3` (`git rev-parse --show-toplevel`),
quindi il file in `pyspendless/.github/workflows/deploy.yml` **non verrà mai
eseguito**.

**Azione**: spostarlo in `/.github/workflows/deploy.yml` (root del repo).

```bash
mkdir -p .github/workflows
git mv pyspendless/.github/workflows/deploy.yml .github/workflows/deploy.yml   # se già tracciato
# oppure, non essendo ancora tracciato:
mkdir -p .github/workflows && mv pyspendless/.github/workflows/deploy.yml .github/workflows/ && rmdir -p pyspendless/.github/workflows 2>/dev/null || true
```

## Contenuto attuale di `deploy.yml`

```yaml
name: Deploy to PythonAnywhere
on:
  push:
    tags:
      - 'v*'            # solo sui tag vX.Y.Z
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via PythonAnywhere API
        env:
          PA_USER:      ${{ secrets.PA_USER }}
          PA_TOKEN:     ${{ secrets.PA_TOKEN }}
          PA_DOMAIN:    ${{ secrets.PA_DOMAIN }}
          PA_REPO_PATH: ${{ secrets.PA_REPO_PATH }}
        run: |
          API="https://www.pythonanywhere.com/api/v0/user/$PA_USER"
          CONSOLE_ID=$(curl -s -H "Authorization: Token $PA_TOKEN" \
            -X POST "$API/consoles/" -d "executable=bash" \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
          curl -s -H "Authorization: Token $PA_TOKEN" \
            -X POST "$API/consoles/$CONSOLE_ID/send_input/" \
            --data-urlencode "input=cd $PA_REPO_PATH && git pull && exit
          "
          sleep 8
          curl -s -H "Authorization: Token $PA_TOKEN" \
            "$API/consoles/$CONSOLE_ID/get_latest_output/"
          curl -s -H "Authorization: Token $PA_TOKEN" \
            -X POST "$API/webapps/$PA_DOMAIN/reload/"
          echo "Deploy completato: pull + reload eseguiti."
```

## Trigger

`on: push: tags: ['v*']` → il deploy parte **solo** quando si pusha un tag
`vX.Y.Z`, non a ogni push su `master`. Scelta deliberata (deploy = release
esplicita). Flusso operativo:

```bash
git push                       # lavoro normale, nessun deploy
git tag v1.4.0 && git push --tags   # <-- questo fa partire il deploy
```

Se invece si vuole il deploy a ogni push su un branch, cambiare in
`on: push: branches: [master]` (ma allora valutare un tag/commit di release
per tracciabilità).

## GitHub repository secrets da configurare

In *Settings → Secrets and variables → Actions → New repository secret* del repo
`tabuto/pyspendless3`:

| Secret | Valore | Fonte |
|---|---|---|
| `PA_USER` | `tabuto` | username PythonAnywhere |
| `PA_TOKEN` | *(API token)* | PA → *Account → API token* |
| `PA_DOMAIN` | `tabuto.pythonanywhere.com` | `pyspendless/.env_pa` → `BASE_URL` |
| `PA_REPO_PATH` | `/home/tabuto/pyspendless3` | `pyspendless/.env_pa` → `DATABASE_URL` |

Nessun segreto finisce nel repo: nel YAML compaiono solo i riferimenti
`${{ secrets.* }}`. La regione è US → host API `www.pythonanywhere.com`
(il `BASE_URL` non è `*.eu.*`).

## API PythonAnywhere usate

Base: `https://www.pythonanywhere.com/api/v0/user/tabuto/` — header su ogni
chiamata: `Authorization: Token <PA_TOKEN>`.

| Scopo | Metodo + endpoint |
|---|---|
| Crea console bash | `POST /consoles/` body `executable=bash` |
| (meglio) elenca console | `GET  /consoles/` → riusa una bash esistente |
| Invia comando | `POST /consoles/<id>/send_input/` body `input=<cmd>\n` (l'`\n` finale è obbligatorio) |
| Leggi output | `GET  /consoles/<id>/get_latest_output/` → `{"output": "..."}` |
| Reload web app | `POST /webapps/tabuto.pythonanywhere.com/reload/` → `{"status": "OK"}` |

## Criticità della bozza da correggere

1. **Posizione file** (Blocco n.1) — spostare in `/.github/workflows/`.

2. **Console nuova a ogni run** — `POST /consoles/` crea una console *ogni volta*
   e il comando termina con `exit`, che la chiude: si accumulano console morte e
   si rischia di sbattere contro il limite di console del piano PA. Inoltre **una
   console creata via API non accetta `send_input` finché non viene aperta almeno
   una volta dal browser** (gotcha noto di PA): con la creazione al volo il primo
   `send_input` può cadere nel vuoto e il `git pull` non parte affatto.
   → Preferire: `GET /consoles/`, riusare la prima con `"executable":"bash"`;
   crearne una solo se non esiste e, in quel caso, **fallire** il job con un
   messaggio che dice di aprirla una volta dal browser. In alternativa, fissare
   l'id di una console dedicata in un secret `PA_CONSOLE_ID`.

3. **`curl -s` senza `-f`** — ogni chiamata fallita (401 token errato, 500, …) è
   silenziosa e il job resta **verde**. → usare `curl -sS -f
   --connect-timeout 10 --max-time 30` e `set -euo pipefail` in testa allo
   script `run:`.

4. **Nessuna verifica del `git pull`** — `sleep 8` fisso, poi si legge l'output
   ma non lo si controlla, e il **reload parte comunque**. → aggiungere un
   marcatore univoco al comando
   (`... && git pull --ff-only 2>&1 && echo __PULL_DONE_$GITHUB_RUN_ID`), poi
   **polling** su `get_latest_output/` (ogni 2s, max ~30s) finché compare il
   marcatore; se compare `CONFLICT` / `error:` o scade il timeout → job **fallito
   e reload NON eseguito**.

5. **`git pull` senza `--ff-only`** — su divergenza col server apre un merge
   interattivo che blocca la console. → `git pull --ff-only`.

6. **Deploy da tag ma `git pull` prende il tip del branch** — con trigger sui
   tag ci si aspetta che il server vada esattamente sul commit taggato. `git
   pull` porta invece l'ultimo commit del branch tracciato (che potrebbe essere
   più avanti del tag). → valutare
   `git fetch --tags --prune && git checkout --force $GITHUB_REF_NAME` al posto
   del `pull`, così il server si allinea al tag. Se si resta su `git pull`,
   documentare che "deploy = ultimo commit del branch", non il tag.

7. **`python3 -c` per il parsing JSON** — funziona su `ubuntu-latest` ma `jq` è
   preinstallato ed è più leggibile: `jq -r '.id'`, `jq -r '.output'`.

8. **Nessuna concurrency guard** — due tag pushati a distanza ravvicinata
   lanciano due deploy paralleli sulla stessa console. → aggiungere:
   ```yaml
   concurrency:
     group: deploy-pythonanywhere
     cancel-in-progress: false
   ```

9. **Osservabilità** — stampare nel log del job: tag/ref in deploy, output del
   `git pull`, esito del reload (`status`). Nessun `echo` del token (non usare
   `set -x` sull'intero blocco).

## Struttura `deploy.yml` proposta (target)

```yaml
name: Deploy to PythonAnywhere

on:
  push:
    tags: ['v*']

concurrency:
  group: deploy-pythonanywhere
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via PythonAnywhere API
        env:
          PA_USER:      ${{ secrets.PA_USER }}
          PA_TOKEN:     ${{ secrets.PA_TOKEN }}
          PA_DOMAIN:    ${{ secrets.PA_DOMAIN }}
          PA_REPO_PATH: ${{ secrets.PA_REPO_PATH }}
        run: |
          set -euo pipefail
          API="https://www.pythonanywhere.com/api/v0/user/$PA_USER"
          hdr=(-H "Authorization: Token $PA_TOKEN")
          curlf=(curl -sS -f --connect-timeout 10 --max-time 30)

          # 1. riusa una console bash esistente, altrimenti fallisci
          CONSOLE_ID=$("${curlf[@]}" "${hdr[@]}" "$API/consoles/" \
            | jq -r '[.[] | select(.executable=="bash")][0].id // empty')
          if [ -z "$CONSOLE_ID" ]; then
            echo "::error::Nessuna console bash. Creane una e aprila una volta dal browser, poi rilancia."
            exit 1
          fi

          # 2. git pull sul server, con marcatore univoco
          MARK="__PULL_DONE_${GITHUB_RUN_ID}"
          CMD="cd $PA_REPO_PATH && git fetch --tags --prune && git checkout --force ${GITHUB_REF_NAME} 2>&1 && echo $MARK"
          "${curlf[@]}" "${hdr[@]}" -X POST "$API/consoles/$CONSOLE_ID/send_input/" \
            --data-urlencode "input=${CMD}
          "

          # 3. polling dell'output finché compare il marcatore (max ~30s)
          for i in $(seq 1 15); do
            sleep 2
            OUT=$("${curlf[@]}" "${hdr[@]}" "$API/consoles/$CONSOLE_ID/get_latest_output/" | jq -r '.output')
            echo "$OUT" | grep -q "$MARK" && break
            [ "$i" = 15 ] && { echo "::error::timeout git pull"; echo "$OUT"; exit 1; }
          done
          echo "$OUT"
          echo "$OUT" | grep -Eqi 'CONFLICT|^error:|fatal:' && { echo "::error::git pull fallito"; exit 1; }

          # 4. reload web app (solo se il pull è andato a buon fine)
          "${curlf[@]}" "${hdr[@]}" -X POST "$API/webapps/$PA_DOMAIN/reload/" | jq -r '.status'
          echo "Deploy $GITHUB_REF_NAME completato."
```

## File toccati

- `.github/workflows/deploy.yml` — **spostato** da `pyspendless/.github/...` alla
  root del repo e riscritto secondo la struttura target.
- `pyspendless/.github/` — rimossa (cartella vuota dopo lo spostamento).
- `pyspendless/README.md` — sezione "Deploy": i 4 secret da creare su GitHub,
  come si lancia (`git tag vX.Y.Z && git push --tags`), prerequisito della
  console bash aperta una volta dal browser.
- `backlog/features.md` — riga di backlog aggiornata.

Nessuna modifica al codice applicativo, nessuna migrazione DB, **nessun file
`.env` coinvolto**.

## Test

- **File in posizione giusta**: dopo lo spostamento, la tab *Actions* del repo
  GitHub mostra il workflow "Deploy to PythonAnywhere".
- **Happy path**: `git tag v0.0.1-test && git push --tags` → il job passa, il
  log mostra il `git checkout` del tag sul server e `status: OK` del reload; la
  web app risponde aggiornata.
- **Token errato** (`PA_TOKEN` con valore fasullo in un branch di prova) → il
  job **fallisce** alla prima curl (grazie a `-f`), nessun reload.
- **Nessuna console bash** disponibile su PA → job fallito con messaggio
  esplicito, nessun reload.
- **Pull con conflitto** (modifica locale non committata sul server) → output
  con `error:`/`CONFLICT` → job fallito, **reload non eseguito**.
- **Push senza tag** (push normale su `master`) → nessun run del workflow.
- **Doppio tag ravvicinato** → i due run non girano in parallelo sulla console
  (concurrency group).
- **Segretezza**: il log del job non contiene il valore di `PA_TOKEN` in chiaro.
