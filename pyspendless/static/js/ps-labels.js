/*
 * pyspendless/static/js/ps-labels.js
 * ============================================================================
 * Task 26-0 (Fase 4) — gemello JS di pyspendless/labels.py + campo a chip.
 *
 * Tre parti, in quest'ordine nel file:
 *   1. GRAMMATICA — funzioni pure (isValid, extract, extractNorm, hasLabel,
 *      addLabel, removeLabel, renameLabel, canonicalize, normalizeSpace).
 *      Stesso contratto del lato Python (pyspendless/labels.py), stessi nomi
 *      in camelCase, stessi 112 casi (pyspendless/test/fixtures/labels_cases.json).
 *      NON toccano il DOM: devono poter essere eseguite in un ambiente senza
 *      `document` (tools/check-labels-js.mjs le carica così) ed è lo stesso
 *      vincolo che serve in produzione per degradare quando il CDN di Tom
 *      Select non risponde (vedi punto 3).
 *   2. decorate(root) — resa delle label come chip <a> cliccabili nelle note
 *      già salvate (elenco, ricerca). Nodi DOM e textContent, mai innerHTML
 *      concatenato: la nota è testo utente.
 *   3. initField(el) — il campo a chip (Tom Select) nel form movimento,
 *      sincronizzato nei due versi con la textarea della nota.
 *
 * Senza lookbehind nella regex: Safari lo supporta solo da 16.4 e l'app è
 * mobile-first (backlog/task26-0-labels/task26-spec.md §3).
 *
 * Riferimento: backlog/task26-0-labels/task26-spec.md §3, §5, §6, §9, §11.
 *              backlog/task26-0-labels/fasi/fase-4.md.
 * ============================================================================
 */

(function (window) {
  "use strict";

  var MIN_LABEL_LEN = 2;
  var MAX_LABEL_LEN = 30;

  // Ripiego dei due limiti che vivono in conf.py (MAX_NOTE_LENGTH,
  // MAX_LABELS_PER_MOVEMENT). La fonte di verità resta il server: il template
  // li rende come data-ps-note-max / data-ps-labels-max sul campo, e
  // fieldLimits() li legge da lì. Questi valori valgono solo se il markup non
  // li porta — non si leggono qui al caricamento, perché questo file deve
  // poter essere importato senza DOM (l'harness Node).
  var MAX_NOTE_LENGTH = 500;
  var MAX_LABELS_PER_MOVEMENT = 10;

  // Limiti effettivi del campo: dal markup se c'è, altrimenti il ripiego.
  function fieldLimits(el) {
    function num(attr, fallback) {
      var raw = parseInt(el.getAttribute(attr), 10);
      return (!isNaN(raw) && raw > 0) ? raw : fallback;
    }
    return {
      noteMax: num("data-ps-note-max", MAX_NOTE_LENGTH),
      labelsMax: num("data-ps-labels-max", MAX_LABELS_PER_MOVEMENT)
    };
  }

  // ==========================================================================
  // 1. GRAMMATICA — porting 1:1 di pyspendless/labels.py
  // ==========================================================================
  //
  // La regex trova CANDIDATI; è isValid() a decidere, con la regola che la
  // regex non esprime: la grafia non può iniziare né finire con '-'.
  //
  // Senza lookbehind: il gruppo 1 è il carattere di contesto (consumato),
  // il gruppo 2 è il nome. m.index punta al carattere di contesto, NON al
  // '#': la posizione del '#' è m.index + m[1].length, la fine è quella
  // posizione + 1 (il '#') + il nome. matchLabels() centralizza questo
  // calcolo una volta per tutte: removeLabel/renameLabel/canonicalize
  // ricostruiscono la stringa a pezzi dalle posizioni {start, end, name},
  // mai con una sostituzione testuale ingenua (che mangerebbe il carattere
  // di contesto, condiviso con label adiacenti come "#a #bb").
  var LABEL_RE = /(^|[^\p{L}\p{N}_#-])#([0-9A-Za-z_-]{2,30})(?![\p{L}\p{N}_-])/gu;

  function isValid(name) {
    if (typeof name !== "string") return false;
    if (name.length < MIN_LABEL_LEN || name.length > MAX_LABEL_LEN) return false;
    if (!/^[0-9A-Za-z_-]+$/.test(name)) return false;
    // Primo e ultimo carattere non '-'
    if (name.charAt(0) === "-" || name.charAt(name.length - 1) === "-") return false;
    return true;
  }

  // Lista dei candidati VALIDI come {start, end, name}, start/end riferiti
  // al '#' e alla fine del nome (non al match grezzo della regex, che include
  // il carattere di contesto nel gruppo 1). Unico punto che calcola le
  // posizioni: tutte le funzioni che riscrivono il testo passano da qui.
  function matchLabels(note) {
    var out = [];
    if (!note) return out;
    LABEL_RE.lastIndex = 0; // regex globale con stato: azzerare a ogni chiamata
    var m;
    while ((m = LABEL_RE.exec(note)) !== null) {
      var name = m[2];
      if (!isValid(name)) continue;
      var start = m.index + m[1].length; // posizione del '#'
      var end = start + 1 + name.length; // dopo l'ultimo carattere del nome
      out.push({ start: start, end: end, name: name });
    }
    return out;
  }

  function extract(note) {
    if (!note) return [];
    var seen = Object.create(null);
    var result = [];
    matchLabels(note).forEach(function (mt) {
      var norm = mt.name.toLowerCase();
      if (!seen[norm]) {
        seen[norm] = true;
        result.push(mt.name); // grafia come scritta, vince la prima comparsa
      }
    });
    return result;
  }

  function extractNorm(note) {
    // extract() ha già deduplicato case-insensitive: qui si abbassa solo
    // il case della grafia già unica (porting diretto di labels.py, che fa
    // lo stesso passaggio in più per lo stesso motivo: un solo punto di
    // verità su "cos'è il nome normalizzato").
    return extract(note).map(function (name) { return name.toLowerCase(); });
  }

  function hasLabel(note, name) {
    if (!note || !name) return false;
    if (name.charAt(0) === "#") name = name.slice(1);
    if (!isValid(name)) return false;
    var norm = name.toLowerCase();
    return extract(note).some(function (label) { return label.toLowerCase() === norm; });
  }

  function addLabel(note, name) {
    if (name && name.charAt(0) === "#") name = name.slice(1);
    if (!isValid(name)) return note || "";
    if (!note) return "#" + name;
    if (hasLabel(note, name)) return note; // idempotente
    var trimmed = note.replace(/\s+$/, ""); // rstrip
    return trimmed ? trimmed + " #" + name : "#" + name;
  }

  function removeLabel(note, name) {
    if (!note) return "";
    if (name && name.charAt(0) === "#") name = name.slice(1);
    if (!isValid(name)) return note;
    var norm = name.toLowerCase();

    var result = [];
    var lastEnd = 0;
    matchLabels(note).forEach(function (mt) {
      if (mt.name.toLowerCase() !== norm) return;
      result.push(note.slice(lastEnd, mt.start));
      lastEnd = mt.end;
    });
    result.push(note.slice(lastEnd));
    return normalizeSpace(result.join(""));
  }

  function renameLabel(note, oldName, newName) {
    if (!note) return "";
    if (oldName && oldName.charAt(0) === "#") oldName = oldName.slice(1);
    if (newName && newName.charAt(0) === "#") newName = newName.slice(1);
    if (!isValid(oldName) || !isValid(newName)) return note;

    var oldNorm = oldName.toLowerCase();
    var newNorm = newName.toLowerCase();

    // new era già presente? Se sì, le occorrenze di old si RIMUOVONO (merge)
    // invece di sostituirle, a partire dalla prima trovata.
    var newAlreadyPresent = extract(note).some(function (l) { return l.toLowerCase() === newNorm; });

    var result = [];
    var lastEnd = 0;
    matchLabels(note).forEach(function (mt) {
      if (mt.name.toLowerCase() !== oldNorm) return;
      result.push(note.slice(lastEnd, mt.start));
      if (!newAlreadyPresent) {
        result.push("#" + newName);
        newAlreadyPresent = true; // da ora, le successive occorrenze si fondono
      }
      lastEnd = mt.end;
    });
    result.push(note.slice(lastEnd));
    return normalizeSpace(result.join(""));
  }

  function canonicalize(note, mapping) {
    if (!note) return "";
    mapping = mapping || {};
    var result = [];
    var lastEnd = 0;
    matchLabels(note).forEach(function (mt) {
      var norm = mt.name.toLowerCase();
      if (!Object.prototype.hasOwnProperty.call(mapping, norm)) return;
      result.push(note.slice(lastEnd, mt.start));
      result.push("#" + mapping[norm]);
      lastEnd = mt.end;
    });
    result.push(note.slice(lastEnd));
    return result.join(""); // NESSUN normalizeSpace: canonicalize non normalizza
  }

  function normalizeSpace(text) {
    if (!text) return text;
    var lines = text.split("\n").map(function (line) {
      line = line.replace(/[ \t]+/g, " ");
      line = line.replace(/ ([,;:.!?)])/g, "$1");
      line = line.replace(/\( /g, "(");
      return line.trim();
    });
    return lines.join("\n").trim();
  }

  // ==========================================================================
  // 2. decorate(root) — resa a chip delle label nelle note già salvate
  // ==========================================================================
  // Cerca [data-ps-note], legge il TESTO del nodo (mai l'HTML: la nota è
  // testo utente) e lo sostituisce con una sequenza di nodi: testo normale +
  // <a class="ps-label-chip" href="/movements?label=coop">#coop</a>.
  //
  // Idempotente: se il nodo è già stato decorato non lo si ritocca. Non è
  // richiesto dalla specifica, ma DataTables (draw.dt) e l'infinite scroll
  // possono richiamare decorate() sullo stesso contenitore più volte; sui
  // nodi che DataTables rigenera da zero ad ogni draw questo guard non serve
  // mai, ma costa nulla ed evita un doppio-decoro se un chiamante futuro
  // passa un nodo già decorato.

  function decorateNode(node) {
    if (node.getAttribute("data-ps-decorated") === "1") return;

    var text = node.textContent;
    var matches = matchLabels(text);
    if (!matches.length) return; // niente da fare: lascia il testo com'è

    node.textContent = "";
    var lastEnd = 0;
    matches.forEach(function (mt) {
      if (mt.start > lastEnd) {
        node.appendChild(document.createTextNode(text.slice(lastEnd, mt.start)));
      }
      var a = document.createElement("a");
      a.className = "ps-label-chip";
      // Href in forma canonica (minuscola, D4): il filtro è case-insensitive
      // comunque, ma il testo del link resta coerente con la forma di
      // registro invece che con la grafia digitata dall'utente.
      a.setAttribute("href", "/movements?label=" + encodeURIComponent(mt.name.toLowerCase()));
      a.textContent = "#" + mt.name;
      node.appendChild(a);
      lastEnd = mt.end;
    });
    if (lastEnd < text.length) {
      node.appendChild(document.createTextNode(text.slice(lastEnd)));
    }
    node.setAttribute("data-ps-decorated", "1");
  }

  function decorate(root) {
    root = root || document;
    var nodes = root.querySelectorAll("[data-ps-note]");
    for (var i = 0; i < nodes.length; i++) decorateNode(nodes[i]);
  }

  // ==========================================================================
  // 3. initField(el) — il campo a chip (Tom Select) nel form movimento
  // ==========================================================================
  // el è un <select multiple data-ps-labels data-ps-labels-target="#note">.
  // La textarea puntata da data-ps-labels-target è la fonte di verità (§9):
  // il campo a chip è una VISTA sul suo testo, non un dato a parte.

  function closestHideTarget(el) {
    return el.closest("[data-ps-labels-wrap]") || el;
  }

  function initField(el) {
    // Degrado (§4.4, criterio #15 dei casi limite): se il CDN di Tom Select
    // non risponde, TomSelect non è definito. Nessuna eccezione, nessun
    // blocco del submit: la nota resta la fonte di verità, quindi si nasconde
    // solo il campo a chip e la textarea continua a funzionare com'è oggi.
    if (typeof TomSelect === "undefined") {
      closestHideTarget(el).style.display = "none";
      return;
    }

    var targetSel = el.getAttribute("data-ps-labels-target");
    var textarea = targetSel ? document.querySelector(targetSel) : null;
    if (!textarea) return; // markup incompleto: niente da sincronizzare

    var messageEl = createMessageElement(el);
    var limits = fieldLimits(el);

    // Sospende la sincronizzazione mentre SIAMO NOI a scrivere (sulla
    // textarea dagli eventi item_add/item_remove, o sulle chip dal
    // riallineamento della textarea): senza questa guardia ciascuna delle
    // due direzioni rimette mano all'altra e si innesca un ciclo (il punto
    // delicato della specifica, §4.2).
    var syncing = false;

    function setMessage(text) {
      messageEl.textContent = text;
      messageEl.hidden = false;
    }
    function clearMessage() {
      if (!messageEl.hidden) {
        messageEl.hidden = true;
        messageEl.textContent = "";
      }
    }

    var ts = new TomSelect(el, {
      plugins: ["remove_button"],
      valueField: "name",
      labelField: "name",
      searchField: "name",
      create: true, // una label nuova si crea digitandola
      createFilter: function (input) {
        // Stessa grammatica del server, + i due rifiuti che la regex non
        // esprime (§4.5): undicesima label, nota che supererebbe
        // limits.noteMax. Il terzo rifiuto (CDN giù) non arriva qui: il
        // campo non esiste nemmeno.
        if (!isValid(input)) {
          setMessage("Una label può contenere solo lettere, numeri, \"_\" e \"-\", da 2 a 30 caratteri.");
          return false;
        }
        if (ts.items.length >= limits.labelsMax) {
          setMessage("Massimo " + limits.labelsMax + " label per movimento.");
          return false;
        }
        if (addLabel(textarea.value, input).length > limits.noteMax) {
          setMessage("La nota supererebbe i " + limits.noteMax + " caratteri consentiti.");
          return false;
        }
        clearMessage();
        return true;
      },
      persist: false,
      shouldLoad: function (q) { return q.length >= 1; }, // P4
      maxItems: limits.labelsMax, // P6
      maxOptions: 10, // P4
      load: function (q, callback) {
        fetch("/api/labels?q=" + encodeURIComponent(q))
          .then(function (resp) { return resp.ok ? resp.json() : []; })
          .then(function (rows) { callback(rows); })
          .catch(function () { callback(); }); // load() vuole SEMPRE una callback, anche sull'errore
      },
    });

    // ── Textarea -> chip (quando l'utente scrive #label a mano, o al carico
    //    iniziale per mostrare le label già scritte nella nota — A2) ───────
    function resyncFromTextarea() {
      if (syncing) return;
      syncing = true;

      var wanted = extract(textarea.value); // grafie come scritte, ordine di comparsa
      var wantedNorm = wanted.map(function (n) { return n.toLowerCase(); });

      // Rimuove le chip la cui label non è più nel testo.
      ts.items.slice().forEach(function (name) {
        if (wantedNorm.indexOf(String(name).toLowerCase()) === -1) {
          ts.removeItem(name, true); // silent: non deve far scattare item_remove
        }
      });

      // Aggiunge le chip delle label nuove. Trappola misurata in Fase 0:
      // addItem() su un valore non ancora NOTO al controllo non fa nulla e
      // non solleva. Le label arrivano dal load() remoto, quindi qui serve
      // SEMPRE addOption() prima di addItem().
      var currentNorm = ts.items.map(function (n) { return String(n).toLowerCase(); });
      wanted.forEach(function (name) {
        if (currentNorm.indexOf(name.toLowerCase()) !== -1) return;
        if (!ts.options[name]) ts.addOption({ name: name });
        ts.addItem(name, true); // silent: non deve far scattare item_add
        currentNorm.push(name.toLowerCase());
      });

      syncing = false;
    }

    var debounceTimer = null;
    textarea.addEventListener("input", function () {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(resyncFromTextarea, 150); // P3
    });

    // form.reset() non emette 'input' sulla textarea (è un reset nativo del
    // valore, non una digitazione): senza questo listener le chip resterebbero
    // quelle di prima del reset. Non è nella specifica, è una conseguenza
    // dell'aver scelto la textarea come fonte di verità: se si azzera lei,
    // si azzerano anche le chip. setTimeout(0) perché il valore nativo della
    // textarea sia già stato riscritto quando resyncFromTextarea lo legge.
    var form = el.form || textarea.form;
    if (form) {
      form.addEventListener("reset", function () {
        setTimeout(resyncFromTextarea, 0);
      });
    }

    // ── Chip -> textarea (scelta dal dropdown, creazione, rimozione) ──────
    ts.on("item_add", function (name) {
      if (syncing) return;
      var next = addLabel(textarea.value, name);
      if (next.length > limits.noteMax) {
        // Può succedere anche per una label scelta dal dropdown (non creata:
        // createFilter non viene chiamato in quel caso), quindi il controllo
        // va ripetuto qui, non solo in createFilter.
        syncing = true;
        ts.removeItem(name, true);
        syncing = false;
        setMessage("La nota supererebbe i " + limits.noteMax + " caratteri consentiti.");
        return;
      }
      clearMessage();
      syncing = true;
      textarea.value = next;
      syncing = false;
    });

    ts.on("item_remove", function (name) {
      if (syncing) return;
      clearMessage();
      syncing = true;
      textarea.value = removeLabel(textarea.value, name);
      syncing = false;
    });

    // Stato iniziale: le label già scritte nella nota (riapertura in
    // modifica, A2) diventano chip subito, senza aspettare il primo 'input'.
    resyncFromTextarea();
  }

  function createMessageElement(el) {
    // Convenzione: un elemento [data-ps-labels-message] già nel markup (così
    // il template può posizionarlo e stilarlo) oppure, se assente, se ne crea
    // uno subito dopo il campo. Rifiuti con un messaggio sotto il campo, non
    // un alert() (§4.5).
    var scope = el.closest("[data-ps-labels-wrap]") || el.parentNode;
    var existing = scope ? scope.querySelector("[data-ps-labels-message]") : null;
    if (existing) return existing;

    var div = document.createElement("div");
    div.setAttribute("data-ps-labels-message", "");
    div.className = "ps-labels-message ps-muted text-sm mt-1";
    div.hidden = true;
    el.insertAdjacentElement("afterend", div);
    return div;
  }

  // ==========================================================================
  // Esposizione pubblica + attivazione
  // ==========================================================================

  var PsLabels = {
    isValid: isValid,
    extract: extract,
    extractNorm: extractNorm,
    hasLabel: hasLabel,
    addLabel: addLabel,
    removeLabel: removeLabel,
    renameLabel: renameLabel,
    canonicalize: canonicalize,
    normalizeSpace: normalizeSpace,
    decorate: decorate,
    initField: initField,
  };

  window.PsLabels = PsLabels;

  // Auto-attivazione sui campi [data-ps-labels] presenti nella pagina.
  // Guardia esplicita su `document`: questo file deve poter essere caricato
  // anche in un ambiente senza DOM (tools/check-labels-js.mjs), e `typeof`
  // su un identificatore mai dichiarato non solleva.
  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      var fields = document.querySelectorAll("[data-ps-labels]");
      for (var i = 0; i < fields.length; i++) initField(fields[i]);
    });
  }
})(typeof window !== "undefined" ? window : this);
