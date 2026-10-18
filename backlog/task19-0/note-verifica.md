# Note di verifica — task19-0

Quello che si impara solo provando, e che altrimenti si ripaga due volte.
Scritto durante le Fasi 0-2; va letto prima di verificare qualunque fase.

## L'ambiente

- **Virtualenv: `.venv/` nella root.** Nel repo ce ne sono due (`.venv/` e
  `pyspendless/.venv/`), entrambi con Flask e SQLAlchemy. Si usa il primo.
- **La shell dell'agente È sul Mac e raggiunge `http://localhost:5000`**
  (verificato: `HTTP 200` in ~2 ms). Il RUNBOOK §1.2 afferma il contrario:
  è sbagliato. Non serve passare da Chrome per verificare l'app.
- **Non serve fare login.** `tools/ps_session_cookie.py` firma un cookie di
  sessione Flask con `SECRET_KEY` per il primo utente del DB — lo stesso
  meccanismo che `test_task19_0.py` usa con `session_transaction()`, espresso
  come cookie iniettabile in un browser vero. Nessuna credenziale, nessun OAuth.
- Playwright + Chromium sono installati nel `.venv`.

## Gli strumenti

| Strumento | A cosa serve |
|---|---|
| `tools/build-css.sh` | compila Tailwind; fallisce se l'output è < 5 KB o se git ignora il CSS |
| `tools/ui-measure.py [rotta]` | peso e numero di richieste, per origine. Misura il guadagno a fine lavoro |
| `tools/ui-shots.py` | matrice pagine × viewport + stati interattivi (`--out docs/ui-after` per il confronto) |
| `tools/ui-preview.py <template>` | rende un template **non instradato** e lo serve da localhost |
| `tools/ui_preview_helper.py` | `rendi_html(template, user_id="admin"\|"utente")` — con i context processor attivi |
| `tools/check-conversion-table.py` | A1.4: ogni classe dei template ha una destinazione in tabella |
| `tools/check-nav-parity.py` | A2.3: destinazioni della nav vecchia vs nuova, posizione per posizione |

## Quattro trappole che hanno già prodotto falsi allarmi

**1. `set_content` falsa il test del tema.** Una pagina consegnata con
`page.set_content()` vive su `about:blank`, dove `localStorage` è inaccessibile.
Lo script anti-FOUC finisce nel suo `try/catch` e la pagina resta **sempre in
light**: il tema sembra rotto quando è il banco di prova a esserlo. Servire
sempre dall'origine vera (`tools/ui-preview.py`).

**2. I selettori si leggono, non si indovinano.** Due FAIL in Fase 2 erano
della sonda: il chevron dei treeview è la **seconda** `<i>` del bottone
(`i.nav-arrow`), non la prima (che è l'icona di sezione); l'hamburger si marca
`data-ps-toggle="drawer"`. Una sonda che indovina costa quanto un bug vero.

**3. Jinja analizza anche i commenti HTML.** Scrivere i delimitatori Jinja per
esteso dentro un `<!-- -->` rende il template **non compilabile**. È successo
due volte (`_styleguide.html`, `ps-base-tw.html`). Peggio: un template che non
compila non fa fallire il contratto finché nessuna rotta lo rende, quindi può
restare rotto a lungo in silenzio.

**4. Un overlay va verificato da CHIUSO.** `.ps-modal` applicava `display:flex`
sempre, sovrascrivendo il `display:none` che il browser dà a un `<dialog>`
chiuso: il dialog restava steso sulla viewport, invisibile ma **intercettando
ogni click della pagina**. Non si vede in uno screenshot — si scopre solo
provando a cliccare. Vale per qualunque overlay: modal, drawer, backdrop.

## Il test di contratto, dettagli non ovvi

- `_ids_in` / `_names_in` usano un lookbehind: senza, `\bid=` combacia anche in
  `data-category-id="27"` e l'estrattore cattura il **valore** del data-attribute
  come se fosse un id.
- `DYNAMIC_CLASS_PATTERNS` sorveglia **due** forme del rischio R1: la
  concatenazione JavaScript e l'assemblaggio Jinja (`class="alert-{{ x }}"`).
  I rami completi (`{% if %}ps-a{% else %}ps-b{% endif %}`) sono sicuri e non
  vanno "corretti".
- `whitelist_non_migrati` va **sfoltita** man mano: togliere il file quando lo
  si migra. È l'unica modifica legittima al file di test durante la migrazione.
- `solo_admin` salta la rotta se la sessione finta non è `ADMIN_USER_ID`,
  invece di produrre un rosso fasullo su un altro DB.
- `contains` copre ciò che non è un id: i `data-*` letti dal JS e gli id
  ricomposti dal JS (`row-<n>`).
- **Stati condizionali**: `/movements?category_type=expense` è una voce a sé
  perché `bulk-category` esiste solo con quel filtro attivo. Una `GET` sulla
  rotta nuda non lo vede.

## Cose che il DB locale non mostra

- Gli **inviti pendenti** di `/settings/group` arrivano da `/api/pending-invites`
  e sono renderizzati **dal JS**, non dal server: il contratto non li vede, e lo
  screenshot va preso dopo il fetch.
- `/onboarding` risponde **302** a un utente che ha già un account: non è
  copribile dal contratto senza una fixture dedicata.
- La pagina di **manutenzione** non è raggiungibile dal server in esecuzione
  (`MAINTENANCE_MODE` si legge a ogni richiesta). `tools/ui-shots.py` la rende
  con il test client e la variabile attiva, poi la passa al browser.

## Decisioni prese in corso d'opera

- **D10 (icone Font Awesome): si rimuovono.** FA non è caricato, quelle 23
  occorrenze oggi non mostrano nulla, e la rimozione è la scelta isofunzionale.
  Cancellare l'elemento `<i>` intero, non solo le classi.
- **P6 è inesistente**: Bootstrap JS è caricato una volta sola. Le due righe
  sospette in `ps-show-mov.html` sono gli adattatori DataTables.
- **P7, nuovo**: una navbar Bootstrap residua in `ps-base.html` rendeva una
  scritta "PySpendless" isolata su ogni pagina. La shell nuova non la riproduce.
- **MB-006**: ordinamento per data corretto con `data-order`, separatamente dal
  restyling. La Fase 6 deve conservare quell'attributo.

## Aggiunte dopo la Fase 3

**`isolation: worktree` nel frontmatter NON ha effetto.** Il RUNBOOK §4.1
afferma che, stando nella definizione di `ps-markup`, «vale sempre e
l'orchestratore non se ne deve ricordare». È falso: i quattro subagent della
Fase 3 hanno scritto tutti nel checkout principale (`git worktree list` mostra
solo quello). Nessun danno, perché i quattro file erano disgiunti — ma in Fase 5
ci saranno cinque agenti e la stessa assunzione. **L'isolamento va passato
esplicitamente all'invocazione.**

**Un worktree non vedrebbe comunque il lavoro non committato.** Contiene solo i
file **tracciati**: prima di usarne uno, il lavoro delle fasi precedenti deve
essere committato, o gli agenti trovano `TemplateNotFound` sulle shell `-tw`.

**`/onboarding` non redirige perché l'utente ha già un account** — come si era
supposto in Fase 0. Redirige perché manca `session['oauth_user_info']`
(`app.py:338`), che è l'**unica** chiave che quella rotta legge e che nessun
altro endpoint usa. Iniettandola, la pagina è raggiungibile e testabile: ora è
nel CONTRACT, e `build_cookie(extra=...)` la rende visitabile anche nel browser.

**Il confine di parola morde anche negli strumenti.** `check-page-migration.py`
cercava `\bcard-body\b` e combaciava **dentro** `ps-card-body`, segnalando come
residuo Bootstrap la classe Tailwind che lo sostituisce. Stesso difetto di
`\bid=` nel test. Ogni pattern su nomi di classe con trattini vuole un
lookbehind `(?<![-\w])`.

**Lo strumento non deve rompersi sui commenti.** La regex che rimuove i tag per
confrontare il testo visibile non toglieva i commenti Jinja `{# #}`: un commento
aggiunto durante la conversione faceva fallire il confronto. E un commento che
**cita** l'anti-pattern R1 fa scattare la sonda del contratto, che legge il
testo grezzo. Regola: nei commenti non si scrive l'anti-pattern per esteso.

**Alcuni file migrati compaiono fra quelli "con Bootstrap"** perché chiamano
`new bootstrap.Modal(...)`: è lo **shim** di `ps-ui.js`, non il framework. Al
2026-10-17 sono `_styleguide.html` (lo prova apposta) e `ps-recurrent-mov.html`
(il modal di conferma). Il controllo `PS_FASE9=1` cerca la stringa `bootstrap`
nel testo grezzo e li segnalerebbe come residui: in Fase 9 va distinto il
**riferimento al framework** (CSS, CDN, classi) dalla **chiamata all'API
shimmata**. `tools/check-page-migration.py` lo fa già, con un lookahead che
esclude `bootstrap.Modal` / `.Tab` / `.Collapse`: conviene allineare il test.

## Aggiunte dopo la Fase 4

**Le scritture si verificano senza scrivere.** `/create` e le ricorrenti
salvano via `fetch`. Intercettando la chiamata con `page.route(...)` e
rispondendo un 200 finto si esercita **tutto** il percorso client — alert,
reset del form, redirect a 1s — senza toccare il DB. Il conteggio dei movimenti
prima e dopo la prova è parte della verifica: 8210 → 8210.

**`showAlert()` è il punto in cui "non toccare il JS" si rompe.** Il JS di
pagina genera classi del vecchio framework (`alert alert-${type}`,
`btn-close`): dopo la conversione del CSS quelle classi non hanno più stile, e
l'alert di esito comparirebbe **senza sfondo né bordo**. L'istruzione "il
blocco `<script>` non si tocca" va quindi letta come "non si tocca la LOGICA":
le stringhe di classe dentro il JS sono markup travestito e vanno convertite.
`ps-component` l'ha segnalato invece di decidere da solo — comportamento
corretto.

**Il dismiss dei modal passa da `data-bs-dismiss`, non da `dialog.close()`.**
Chiamare `close()` direttamente funziona ma scavalca `ps-ui.js`: niente
`hidden.bs.modal` e niente ritorno del focus al trigger, che la Fase 1 aveva
verificato. Lo shim resta in sincrono solo se la chiusura passa da lui.

**A4.15 dipende da MB-004.** `applyLastUsedWallet()` esce subito se l'utente ha
un wallet preferito: la scelta esplicita batte l'euristica dell'ultimo usato.
Tutti gli utenti del DB di sviluppo ne hanno uno, quindi il ramo con
`localStorage` si prova solo spegnendo `hasPreferredWallet` nell'HTML reso.
Un test che lo ignora produce un falso fallimento.

**Due difetti miei negli strumenti, trovati usandoli.** Il corpo degli
`<script>` contava come "testo visibile", quindi ogni stringa di classe
cambiata nel JS faceva fallire il confronto; e nel codice del diff avevo
chiamato `a` sia il namespace di argparse sia una lista, facendo esplodere il
controllo successivo. Gli strumenti di verifica vanno verificati.

## Correzione importante (Fase 5)

**P6 era vero, e l'avevo dichiarato falso.** In Fase 1 avevo misurato gli asset
di `/movements`, trovato un solo Bootstrap, e concluso che il difetto "caricato
due volte" non esisteva. Sbagliato: **sei pagine di impostazioni** caricano in
fondo un secondo bundle (`bootstrap@5.3.0`) sopra quello della shell
(`bootstrap@5.3.2`), e a runtime **vince il secondo**, il più vecchio.

Una misura su una pagina sola non dimostra niente su diciassette. Quando si
smentisce un difetto, va smentito **sull'insieme dei file**, non su un campione
scelto perché comodo.

## Aggiunte dopo la Fase 5

**La finzione deve imitare il CONTRATTO, non dire solo "ok".** Intercettando le
scritture, `deleteCategory()` sembrava rotta: il modal di eliminazione non si
apriva. Non era un bug — quella funzione manda **prima** una `DELETE`, e il
modal si apre solo se il server risponde `requires_target: true` con nome,
tipo e conteggio movimenti. La risposta finta diceva "successo", quindi il
codice prendeva giustamente l'altro ramo. Quando il **ramo** dipende dalla
forma della risposta, la risposta finta va modellata su quella vera.

**Guidare l'interfaccia come la guida un utente.** Il bottone "Salva" del
wallet è `onclick="addWallet()"`, non un submit del form: il mio
`requestSubmit()` faceva navigare la pagina, e sembrava che l'alert non
comparisse. Terzo errore di sonda della sessione dello stesso tipo — **cliccare
il bottone vero**, non sintetizzare l'evento che si suppone ci sia dietro.

**Un modal senza X può essere voluto.** `#showTokenModal` non ha il bottone di
chiusura e ha `data-bs-backdrop="static"`: mostra il token MCP appena creato,
visibile una volta sola, e l'unica uscita è il bottone che chiama anche
`clearTokenValue()`. Era così anche prima. La sonda che assume "ogni modal ha
una X" segnala un difetto che non c'è.

**`data-bs-backdrop="static"` ora è supportato dallo shim.** Non lo era: un
subagent aveva rimosso l'attributo ritenendolo superfluo con `<dialog>`, e il
click accidentale fuori dal riquadro avrebbe fatto perdere il token. Aggiunto a
`ps-ui.js` con la semantica di Bootstrap — lo sfondo non chiude, Esc sì — più
il "sobbalzo" del pannello come feedback.

**Due overflow a 375px erano preesistenti, e vanno comunque chiusi.**
`/settings/admin` (tabelle senza contenitore scorrevole: 688px su 375) e
`/settings/import-export` (il tracciato CSV in un `<code>` non spezzabile).
Nessuno dei due è una regressione — l'originale non aveva `table-responsive` —
ma il task chiede esplicitamente "nessun overflow a 375px", quindi il
restyling ha il mandato di risolverli.

**Tre agenti su sei hanno modificato il file di test nonostante il divieto.**
Uno ha riscritto un blocco togliendo dalla whitelist anche due file di altri
agenti ancora in corso. Niente si è corrotto, ma su un file condiviso da sei
processi paralleli il rischio è reale: il divieto va ripetuto **citando il
precedente**, non solo enunciato.
