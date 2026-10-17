/*
 * pyspendless/static/js/ps-theme.js
 * ============================================================================
 * Task 19-0 (Fase 1, attività 1.5) — Toggle del tema light/dark/system.
 *
 * Tre stati: 'light' | 'dark' | 'system' (default 'system', rispetta
 * prefers-color-scheme). Persistenza in localStorage['ps_theme'].
 * Emette 'ps:themechange' su document (dettaglio: { theme, dark }), che
 * serve a Chart.js in Fase 8 per rileggere i colori dai token CSS.
 *
 * ──────────────────────────────────────────────────────────────────────────
 * IMPORTANTE — lo script anti-FOUC NON è in questo file.
 * ──────────────────────────────────────────────────────────────────────────
 * Deve girare PRIMA del primo paint, quindi inline nel <head>, prima del
 * <link> al CSS, e non può essere né `async` né `defer` (altrimenti il primo
 * paint avviene in light e poi salta a dark: è esattamente il flash che deve
 * evitare). Questo file viene caricato più avanti (anche defer va bene) e si
 * occupa solo del toggle e della sincronizzazione dopo il primo paint.
 *
 * Lo snippet da incollare nel <head> della nuova shell (ps-base-tw.html,
 * Fase 2), SUBITO prima del <link rel="stylesheet" href=".../ps-tailwind.css">,
 * è il valore della costante PS_FOUC_SNIPPET poco più sotto (unica fonte di
 * verità, per evitare che un commento e il codice reale divergano nel tempo
 * senza che nessuno se ne accorga). In forma leggibile corrisponde a:
 *
 *   (function () {
 *     try {
 *       var t = localStorage.getItem('ps_theme') || 'system';
 *       var dark = t === 'dark' ||
 *                  (t === 'system' &&
 *                   window.matchMedia('(prefers-color-scheme: dark)').matches);
 *       document.documentElement.classList.toggle('dark', dark);
 *       document.documentElement.dataset.psTheme = t;
 *     } catch (e) {
 *       // localStorage negato (modalità privata, policy aziendale, ecc.):
 *       // resta light, è il fallback più prudente e non lancia mai un
 *       // errore visibile.
 *     }
 *   })();
 *
 * Va incollato COSÌ COM'È dentro un tag <script> inline, non async né defer,
 * non caricato da questo file (che arriva troppo tardi per evitare il flash).
 * ============================================================================
 */

// Fonte di verità unica per lo snippet anti-FOUC: Fase 2 lo copia inline nel
// <head> di ps-base-tw.html. Esposto qui solo come stringa di riferimento,
// per evitare che le due versioni (questo commento e il file reale) divergano
// nel tempo senza che nessuno se ne accorga.
var PS_FOUC_SNIPPET =
  "(function(){try{var t=localStorage.getItem('ps_theme')||'system';" +
  "var dark=t==='dark'||(t==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);" +
  "document.documentElement.classList.toggle('dark',dark);" +
  "document.documentElement.dataset.psTheme=t;}catch(e){}})();";

(function () {
  "use strict";

  var STORAGE_KEY = "ps_theme";
  var media = window.matchMedia("(prefers-color-scheme: dark)");

  function systemPrefersDark() {
    return media.matches;
  }

  function resolveDark(mode) {
    return mode === "dark" || (mode === "system" && systemPrefersDark());
  }

  function currentMode() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "system";
    } catch (e) {
      return "system";
    }
  }

  var psTheme = {
    /** 'light' | 'dark' | 'system' */
    get: currentMode,

    /** Applica senza persistere (usato anche dal listener di sistema). */
    apply: function (mode) {
      var dark = resolveDark(mode);
      document.documentElement.classList.toggle("dark", dark);
      document.documentElement.dataset.psTheme = mode;

      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) {
        meta.setAttribute("content", dark ? "#0b1120" : "#4f46e5");
      }

      document.dispatchEvent(
        new CustomEvent("ps:themechange", { detail: { theme: mode, dark: dark } })
      );
      return dark;
    },

    /** Persiste in localStorage['ps_theme'] e applica. */
    set: function (mode) {
      if (mode !== "light" && mode !== "dark" && mode !== "system") {
        throw new Error("psTheme.set: modalità non valida: " + mode);
      }
      try {
        localStorage.setItem(STORAGE_KEY, mode);
      } catch (e) {
        // localStorage negato: il tema si applica comunque per la sessione
        // corrente, semplicemente non persiste al reload.
      }
      return this.apply(mode);
    },
  };

  window.psTheme = psTheme;

  // Sincronizza lo stato (dataset.psTheme, meta theme-color, evento) con
  // quanto già deciso dallo script anti-FOUC inline, senza toccare la classe
  // 'dark' se non necessario (eviterebbe un flash inverso).
  psTheme.apply(currentMode());

  // Se l'utente è in modalità 'system' e il SO cambia tema mentre la pagina
  // è aperta, segue senza bisogno di reload (piano §4.3).
  media.addEventListener("change", function () {
    if (currentMode() === "system") {
      psTheme.apply("system");
    }
  });
})();
