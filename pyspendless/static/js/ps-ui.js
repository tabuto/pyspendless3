/*
 * pyspendless/static/js/ps-ui.js
 * ============================================================================
 * Task 19-0 (Fase 1) — Sostituto vanilla del JS imperativo di Bootstrap.
 *
 * Implementa modal (su <dialog> nativo), collapse, tab e alert-dismiss, più
 * un drawer off-canvas generico per la sidebar mobile (usato dalla shell
 * Tailwind a partire dalla Fase 2).
 *
 * ──────────────────────────────────────────────────────────────────────────
 * PERCHÉ ESISTE window.bootstrap.Modal — E PERCHÉ È TEMPORANEO
 * ──────────────────────────────────────────────────────────────────────────
 * Il JS di pagina (ps-setting-categories.html, ps-setting-wallet.html,
 * ps-setting-admin.html, ps-setting-group.html, ps-recurrent-mov.html) NON
 * viene riscritto in questo task: chiama l'API imperativa di Bootstrap in
 * 12 punti (`new bootstrap.Modal(el).show()`, `bootstrap.Modal.getInstance(el)
 * .hide()`, `getOrCreateInstance`) e ascolta 5 eventi `*.bs.modal` /
 * `*.bs.collapse`. Elenco completo:
 * backlog/task19-0/analisi-decisioni-D4-D5.md, "Rilevazione 1".
 *
 * Questo shim esiste SOLO per restare compatibile con quel codice esistente
 * senza toccarlo. Non è "il vero" Bootstrap: è un adattatore sopra PsModal.
 * Debito tecnico esplicito (vedi backlog): una volta che i test di
 * contratto sono stabili, i 12 call site vanno migrati a `psUI.modal(...)`
 * e questo shim va rimosso.
 *
 * ──────────────────────────────────────────────────────────────────────────
 * I DUE PUNTI DI TIMING CRITICI (vedi .claude/agents/ps-component.md)
 * ──────────────────────────────────────────────────────────────────────────
 * 1. `show.bs.modal` su #deleteAccountModal (ps-setting-group.html:264)
 *    scatena checkAccountSharing(), una chiamata API che decide cosa
 *    l'utente legge in #deletionDetails PRIMA di cancellare l'account.
 *    L'evento va emesso PRIMA che il modal diventi visibile (vedi show()).
 *
 * 2. `shown.bs.collapse` su #filters-collapse (ps-show-mov.html:403) fa
 *    partire l'init differita di Tom Select. Va emesso a TRANSIZIONE
 *    CONCLUSA (vedi _finishShow() in PsCollapse): inizializzare Tom Select
 *    mentre il contenitore è display:none produce larghezze e dropdown
 *    sbagliati (commento a ps-show-mov.html:377-379).
 * ============================================================================
 */

(function () {
  "use strict";

  // ==========================================================================
  // Utilità
  // ==========================================================================

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function emit(el, name, detail, cancelable) {
    var ev = new CustomEvent(name, {
      bubbles: true,
      cancelable: !!cancelable,
      detail: detail || {},
    });
    el.dispatchEvent(ev);
    return ev;
  }

  // Durata delle transizioni CSS dei componenti (deve combaciare con quanto
  // scritto in ps-tailwind.src.css: .ps-modal-panel usa duration-150,
  // .ps-alert usa duration-150). Serve da fallback quando 'transitionend'
  // non scatta (elemento con `display:none` improvviso, utente che naviga
  // via, ecc.) — Bootstrap ha lo stesso fallback con TRANSITION_END.
  var MODAL_TRANSITION_MS = 150;
  var ALERT_TRANSITION_MS = 150;
  var COLLAPSE_TRANSITION_MS = 250;

  function onTransitionEnd(el, fallbackMs, cb) {
    var done = false;
    function finish() {
      if (done) return;
      done = true;
      el.removeEventListener("transitionend", onEnd);
      cb();
    }
    function onEnd(e) {
      if (e.target !== el) return;
      finish();
    }
    el.addEventListener("transitionend", onEnd);
    setTimeout(finish, fallbackMs + 50);
  }

  // ==========================================================================
  // PsModal — modal su <dialog> nativo
  // ==========================================================================
  // Backdrop, focus trap, chiusura con Esc e aria-modal arrivano dal browser
  // via dialog.showModal(). Qui si gestisce solo: apertura/chiusura animata,
  // eventi compatibili con Bootstrap, click sul backdrop, e il ritorno del
  // focus al trigger che ha aperto il modal.

  var modalRegistry = new WeakMap();

  function PsModal(el) {
    if (modalRegistry.has(el)) {
      return modalRegistry.get(el);
    }
    this.el = el;
    this._triggerEl = null;
    this._onCancel = this._onCancel.bind(this);
    this._onBackdropClick = this._onBackdropClick.bind(this);
    el.addEventListener("cancel", this._onCancel); // Esc nativo di <dialog>
    el.addEventListener("click", this._onBackdropClick);
    modalRegistry.set(el, this);
  }

  PsModal.prototype._onCancel = function (e) {
    // Il comportamento nativo di <dialog> alla pressione di Esc è chiudere
    // IMMEDIATAMENTE (evento 'cancel' poi 'close'), senza passare dal nostro
    // show/hide. Lo blocchiamo e richiamiamo hide() per ottenere la stessa
    // sequenza di eventi ed animazione di una chiusura programmatica — è
    // così che oggi si chiude un modal Bootstrap con Esc.
    e.preventDefault();
    this.hide();
  };

  PsModal.prototype._onBackdropClick = function (e) {
    // Clic sul "retro": l'elemento <dialog> (.ps-modal) occupa l'intera
    // viewport, il riquadro visibile è .ps-modal-panel dentro di esso.
    // target === this.el significa che il clic non ha toccato nessun
    // discendente, cioè è caduto sull'area di sfondo del dialog stesso.
    if (e.target !== this.el) return;

    // `data-bs-backdrop="static"` (semantica Bootstrap): il clic sullo sfondo
    // NON chiude. Serve dove la chiusura accidentale perde qualcosa di
    // irrecuperabile -- per esempio #showTokenModal, che mostra il token MCP
    // appena creato una volta sola. Esc continua a chiudere, come in Bootstrap.
    if (this.el.getAttribute("data-bs-backdrop") === "static") {
      // piccolo feedback, come fa Bootstrap: il pannello "sobbalza"
      var panel = qs(".ps-modal-panel", this.el);
      if (panel) {
        panel.classList.add("ps-modal-static");
        setTimeout(function () {
          panel.classList.remove("ps-modal-static");
        }, 200);
      }
      return;
    }

    this.hide();
  };

  PsModal.prototype.show = function (triggerEl) {
    if (this.el.open) return;
    this._triggerEl = triggerEl || document.activeElement;

    // Punto critico 1: l'evento precede la visibilità. Un listener su
    // show.bs.modal (es. checkAccountSharing()) deve poter popolare il DOM
    // PRIMA che l'utente veda il modal.
    var ev = emit(this.el, "show.bs.modal", { relatedTarget: this._triggerEl }, true);
    if (ev.defaultPrevented) return;

    this.el.showModal();
    document.body.classList.add("ps-modal-open");

    var self = this;
    var panel = qs(".ps-modal-panel", this.el);
    // Forza un reflow prima di aggiungere lo stato "aperto": altrimenti la
    // transizione opacity/scale non parte (l'elemento era già nel DOM con
    // [open], solo non visibile un frame prima).
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        self.el.classList.add("ps-modal-showing");
        var toWatch = panel || self.el;
        onTransitionEnd(toWatch, MODAL_TRANSITION_MS, function () {
          emit(self.el, "shown.bs.modal", { relatedTarget: self._triggerEl });
        });
      });
    });

    // Focus: <dialog>.showModal() porta già il focus dentro il modal
    // (sul primo elemento con [autofocus], altrimenti sul dialog stesso).
    // Replica il comportamento di default di Bootstrap, che fa lo stesso.
  };

  PsModal.prototype.hide = function () {
    if (!this.el.open) return;

    var ev = emit(this.el, "hide.bs.modal", {}, true);
    if (ev.defaultPrevented) return;

    var self = this;
    var panel = qs(".ps-modal-panel", this.el);
    this.el.classList.remove("ps-modal-showing");
    var toWatch = panel || this.el;
    onTransitionEnd(toWatch, MODAL_TRANSITION_MS, function () {
      self.el.close();
      document.body.classList.remove("ps-modal-open");
      emit(self.el, "hidden.bs.modal", {});
      // Il focus torna al trigger che ha aperto il modal (A1.8).
      if (self._triggerEl && typeof self._triggerEl.focus === "function") {
        self._triggerEl.focus();
      }
      self._triggerEl = null;
    });
  };

  PsModal.prototype.toggle = function (triggerEl) {
    if (this.el.open) this.hide();
    else this.show(triggerEl);
  };

  PsModal.prototype.dispose = function () {
    this.el.removeEventListener("cancel", this._onCancel);
    this.el.removeEventListener("click", this._onBackdropClick);
    modalRegistry.delete(this.el);
  };

  // ── Shim di compatibilità window.bootstrap.Modal ─────────────────────────
  window.bootstrap = window.bootstrap || {};
  window.bootstrap.Modal = (function () {
    function Modal(el) {
      var node = typeof el === "string" ? qs(el) : el;
      var instance = new PsModal(node);
      // Ritorna sempre la STESSA istanza per lo stesso elemento (come fa
      // Bootstrap): new bootstrap.Modal(el) due volte non duplica lo stato.
      this._impl = instance;
    }
    Modal.prototype.show = function () {
      this._impl.show();
    };
    Modal.prototype.hide = function () {
      this._impl.hide();
    };
    Modal.prototype.toggle = function () {
      this._impl.toggle();
    };
    Modal.prototype.dispose = function () {
      this._impl.dispose();
    };
    Modal.getInstance = function (el) {
      var node = typeof el === "string" ? qs(el) : el;
      if (!node) return null;
      var impl = modalRegistry.get(node);
      if (!impl) return null;
      // Una sola istanza-wrapper per elemento, cache sull'impl sottostante:
      // chi chiama getInstance() due volte deve ricevere oggetti coerenti.
      if (!impl.__bsWrapper) {
        var w = Object.create(Modal.prototype);
        w._impl = impl;
        impl.__bsWrapper = w;
      }
      return impl.__bsWrapper;
    };
    Modal.getOrCreateInstance = function (el) {
      return Modal.getInstance(el) || new Modal(el);
    };
    return Modal;
  })();

  // ── Delega dichiarativa: data-bs-toggle="modal" / data-bs-dismiss="modal" ─
  document.addEventListener("click", function (e) {
    var toggle = e.target.closest('[data-bs-toggle="modal"]');
    if (toggle) {
      var targetSel = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
      var targetEl = targetSel ? qs(targetSel) : null;
      if (targetEl) {
        e.preventDefault();
        var instance = modalRegistry.get(targetEl) || new PsModal(targetEl);
        instance.show(toggle);
      }
      return;
    }

    var dismiss = e.target.closest('[data-bs-dismiss="modal"]');
    if (dismiss) {
      var dialogEl = dismiss.closest("dialog.ps-modal");
      if (dialogEl) {
        e.preventDefault();
        var inst = modalRegistry.get(dialogEl);
        if (inst) inst.hide();
      }
    }
  });

  // ==========================================================================
  // PsCollapse — collapse (pannello filtri, ecc.)
  // ==========================================================================

  var collapseRegistry = new WeakMap();

  function PsCollapse(el) {
    if (collapseRegistry.has(el)) return collapseRegistry.get(el);
    this.el = el;
    collapseRegistry.set(el, this);
  }

  PsCollapse.prototype._triggers = function () {
    var id = this.el.id;
    var sel = '[data-bs-toggle="collapse"][data-bs-target="#' + id + '"],' +
      '[data-bs-toggle="collapse"][aria-controls="' + id + '"]';
    return document.querySelectorAll(sel);
  };

  PsCollapse.prototype._setExpanded = function (expanded) {
    var triggers = this._triggers();
    for (var i = 0; i < triggers.length; i++) {
      triggers[i].setAttribute("aria-expanded", expanded ? "true" : "false");
    }
  };

  PsCollapse.prototype.show = function () {
    var el = this.el;
    if (el.classList.contains("show") || el.classList.contains("collapsing")) return;

    var ev = emit(el, "show.bs.collapse", {}, true);
    if (ev.defaultPrevented) return;

    // "collapse" / "show" / "collapsing" sono nomi letterali: il JS di
    // pagina non viene riscritto e in ps-show-mov.html:514 legge
    // classList.contains('show') per decidere se il pannello è già aperto.
    el.classList.add("collapsing");
    el.style.height = "0px";
    this._setExpanded(true);

    var target = el.scrollHeight;
    requestAnimationFrame(function () {
      el.style.height = target + "px";
    });

    onTransitionEnd(el, COLLAPSE_TRANSITION_MS, function () {
      el.classList.remove("collapsing");
      el.classList.add("show");
      el.style.height = "";
      // Punto critico 2: l'evento scatta SOLO a transizione conclusa, non
      // all'inizio dell'espansione — altrimenti Tom Select si inizializza
      // mentre il pannello è ancora display:none/altezza 0.
      emit(el, "shown.bs.collapse", {});
    });
  };

  PsCollapse.prototype.hide = function () {
    var el = this.el;
    if (!el.classList.contains("show")) return;

    var ev = emit(el, "hide.bs.collapse", {}, true);
    if (ev.defaultPrevented) return;

    el.style.height = el.scrollHeight + "px"; // da 'auto' a un valore esplicito
    el.classList.remove("show");
    el.classList.add("collapsing");
    this._setExpanded(false);

    requestAnimationFrame(function () {
      el.style.height = "0px";
    });

    onTransitionEnd(el, COLLAPSE_TRANSITION_MS, function () {
      el.classList.remove("collapsing");
      el.style.height = "";
      // Senza .show, .collapse:not(.show) torna a display:none (CSS).
      emit(el, "hidden.bs.collapse", {});
    });
  };

  PsCollapse.prototype.toggle = function () {
    if (this.el.classList.contains("show")) this.hide();
    else this.show();
  };

  document.addEventListener("click", function (e) {
    var toggle = e.target.closest('[data-bs-toggle="collapse"]');
    if (!toggle) return;
    var targetSel = toggle.getAttribute("data-bs-target") || toggle.getAttribute("href");
    var targetEl = targetSel ? qs(targetSel) : null;
    if (!targetEl) return;
    e.preventDefault();
    var instance = collapseRegistry.get(targetEl) || new PsCollapse(targetEl);
    instance.toggle();
  });

  // ==========================================================================
  // PsTab — nav-tabs / tab-content (uscite / entrate)
  // ==========================================================================
  // Nessun listener della pagina ascolta eventi .bs.tab oggi: si replica solo
  // il comportamento visibile (switch di pannello + stato a11y).

  function activateTab(tabBtn) {
    var targetSel = tabBtn.getAttribute("data-bs-target") || tabBtn.getAttribute("href");
    var targetEl = targetSel ? qs(targetSel) : null;
    if (!targetEl) return;

    var tablist = tabBtn.closest('[role="tablist"]') || tabBtn.parentElement.parentElement;
    var siblingBtns = tablist ? tablist.querySelectorAll('[data-bs-toggle="tab"]') : [tabBtn];

    var prevActiveBtn = null;
    for (var i = 0; i < siblingBtns.length; i++) {
      if (siblingBtns[i].classList.contains("active")) prevActiveBtn = siblingBtns[i];
    }
    if (prevActiveBtn === tabBtn) return;

    emit(tabBtn, "show.bs.tab", { relatedTarget: prevActiveBtn });

    for (var j = 0; j < siblingBtns.length; j++) {
      var b = siblingBtns[j];
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    }
    tabBtn.classList.add("active");
    tabBtn.setAttribute("aria-selected", "true");

    var panelsContainer = targetEl.parentElement;
    var panels = panelsContainer ? panelsContainer.querySelectorAll(".ps-tabpanel, .tab-pane") : [targetEl];
    for (var k = 0; k < panels.length; k++) {
      panels[k].classList.remove("active", "show");
    }
    targetEl.classList.add("active", "show");

    emit(tabBtn, "shown.bs.tab", { relatedTarget: prevActiveBtn });
  }

  document.addEventListener("click", function (e) {
    var tabBtn = e.target.closest('[data-bs-toggle="tab"]');
    if (!tabBtn) return;
    e.preventDefault();
    activateTab(tabBtn);
  });

  // ==========================================================================
  // Alert dismiss — data-bs-dismiss="alert"
  // ==========================================================================
  // NOTA: l'auto-hide a 5s e la sospensione sul focus (ps-add-mov.html:316-333)
  // restano implementate NELLE PAGINE (showAlert() locali), non qui: qui si
  // replica solo il comportamento del bottone di chiusura, che è l'unica
  // parte davvero delegata a Bootstrap oggi.

  document.addEventListener("click", function (e) {
    var closeBtn = e.target.closest('[data-bs-dismiss="alert"]');
    if (!closeBtn) return;
    var alertEl = closeBtn.closest(".ps-alert, .alert");
    if (!alertEl) return;
    e.preventDefault();

    var ev = emit(alertEl, "close.bs.alert", {}, true);
    if (ev.defaultPrevented) return;

    // .fade / .show sono nomi letterali (vedi ps-tailwind.src.css): rimuovere
    // .show avvia il fade-out via CSS, esattamente come su un .alert.fade.show
    // di Bootstrap.
    alertEl.classList.remove("show");
    onTransitionEnd(alertEl, ALERT_TRANSITION_MS, function () {
      emit(alertEl, "closed.bs.alert", {});
      if (alertEl.parentNode) alertEl.parentNode.removeChild(alertEl);
    });
  });

  // ==========================================================================
  // PsDrawer — sidebar off-canvas (usato dalla shell Tailwind in Fase 2)
  // ==========================================================================
  // Non collegato a nessuna pagina esistente in questa fase: nuova UI,
  // dimostrata in _styleguide.html. API: data-ps-toggle="drawer"
  // data-ps-target="#id" per aprire/chiudere, data-ps-dismiss="drawer"
  // data-ps-target="#id" per i bottoni di chiusura E per il backdrop (stesso
  // attributo, stesso selettore: un backdrop è un "dismiss" per quel drawer).

  var drawerRegistry = new WeakMap();

  function PsDrawer(el) {
    if (drawerRegistry.has(el)) return drawerRegistry.get(el);
    this.el = el;
    drawerRegistry.set(el, this);
  }

  PsDrawer.prototype._backdrops = function () {
    return document.querySelectorAll(
      '.ps-drawer-backdrop[data-ps-target="#' + this.el.id + '"]'
    );
  };

  PsDrawer.prototype.open = function () {
    this.el.classList.add("ps-drawer-open");
    this._backdrops().forEach(function (b) { b.classList.add("ps-drawer-open"); });
    document.body.classList.add("ps-drawer-locked");
    this.el.setAttribute("aria-hidden", "false");
    document.addEventListener("keydown", this._escHandler || (this._escHandler = this._onKeydown.bind(this)));
  };

  PsDrawer.prototype.close = function () {
    this.el.classList.remove("ps-drawer-open");
    this._backdrops().forEach(function (b) { b.classList.remove("ps-drawer-open"); });
    document.body.classList.remove("ps-drawer-locked");
    this.el.setAttribute("aria-hidden", "true");
    if (this._escHandler) document.removeEventListener("keydown", this._escHandler);
  };

  PsDrawer.prototype.toggle = function () {
    if (this.el.classList.contains("ps-drawer-open")) this.close();
    else this.open();
  };

  PsDrawer.prototype._onKeydown = function (e) {
    if (e.key === "Escape") this.close();
  };

  document.addEventListener("click", function (e) {
    var toggle = e.target.closest('[data-ps-toggle="drawer"]');
    if (toggle) {
      var sel = toggle.getAttribute("data-ps-target");
      var el = sel ? qs(sel) : null;
      if (el) {
        e.preventDefault();
        var inst = drawerRegistry.get(el) || new PsDrawer(el);
        inst.toggle();
      }
      return;
    }
    var dismiss = e.target.closest('[data-ps-dismiss="drawer"]');
    if (dismiss) {
      // Il backdrop stesso porta data-ps-dismiss="drawer" data-ps-target="#id"
      // (vedi _styleguide.html): non serve un ramo a parte per il click sullo
      // sfondo, è lo stesso pattern dei bottoni di chiusura.
      var drawerEl = dismiss.closest(".ps-drawer") ||
        qs(dismiss.getAttribute("data-ps-target") || "");
      if (drawerEl) {
        var inst2 = drawerRegistry.get(drawerEl);
        if (inst2) inst2.close();
      }
    }
  });

  // ==========================================================================
  // API pubblica (non-Bootstrap): preparazione alla migrazione futura dei
  // 12 call site fuori dallo shim (debito tecnico dichiarato).
  // ==========================================================================
  window.psUI = {
    Modal: PsModal,
    Collapse: PsCollapse,
    Drawer: PsDrawer,
    modal: function (el) {
      var node = typeof el === "string" ? qs(el) : el;
      return modalRegistry.get(node) || new PsModal(node);
    },
    collapse: function (el) {
      var node = typeof el === "string" ? qs(el) : el;
      return collapseRegistry.get(node) || new PsCollapse(node);
    },
    drawer: function (el) {
      var node = typeof el === "string" ? qs(el) : el;
      return drawerRegistry.get(node) || new PsDrawer(node);
    },
  };
})();
