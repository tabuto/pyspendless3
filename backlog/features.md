# Features Backlog

| Task | Descrizione | Stato |
|------|-------------|-------|
| Gestione Categorie | Nuova pagina in Setting per la gestione delle categorie che permetta di rinominare una categoria aggiornando i relativi record | TODO |
| Dashboard Overall | Aggiungere dashboard overall, entrate uscite year by year | TODO |
| Totale Wallet | Aggiunta visualizzazione totale complessivo dei wallet | TODO |
| Gestione Export | gestione export: tutto, anno, anno-mese. filtro Opzionale Categoria; filtro opzionale keyword | TODO |
| Filtri Visualizza Movimenti | in visualizza movimenti, aggiungi la possibilità di non inserire il mese in modo da avere le spese dell'anno; aggiungi un filtro keyword che agisce sulle note | TODO |
| Gestione Categorie Avanzata | Separate sezioni entrata/uscita. Ordinamento custom e alfabetico. Rinominare categoria aggiorna i movimenti. Merge automatico se rinomina coincide con esistente. | TODO |
| Ripeti Movimento | Pulsante "Ripeti" nell'elenco movimenti: apre il form di creazione pre-compilato con tutti i campi dell'originale e la data odierna (task17-0) | DONE |
| Deploy PythonAnywhere | GitHub Actions (`deploy.yml`, trigger sui tag `v*`) che fa `git pull`/checkout sul server PA e reload della web app via API token; segreti nei GitHub repository secrets (task18-0). **SOSPESO**: l'account PA gratuito non consente le API, il workflow fallisce (run del tag `v0.1.7`) — il deploy resta manuale (`git pull` + Reload da console/tab Web) | SOSPESO |
| Server MCP | Endpoint `/mcp` (JSON-RPC stateless) con tool `add_movement` e `list_categories`, autenticati via token personale generato dal profilo utente, per registrare spese parlando a Claude (task20-0) | TODO |
| Rate limiting endpoint MCP | Limite di richieste/401 sull'endpoint `/mcp`, scorporato da task20-0 (decisione D9) | TODO |
| Correzione massiva movimenti | In `/movements`, filtrare i movimenti e cambiare in blocco categoria e/o descrizione su tutti i movimenti risultanti dai filtri (task21-0) | DONE |
| Wallet preferito per singolo utente | Bugfix: il wallet preferito (MB-004/MB-005) era condiviso da tutti gli utenti dello stesso account; diventa un'impostazione per singolo utente (`User.preferred_wallet_id`), con migrazione di backfill (task22-0) | DONE |
| Restyling Tailwind | Rifacimento della presentazione con Tailwind CSS v4: mobile first, tema dark/light persistente, Bootstrap e AdminLTE rimossi dal progetto. Isofunzionale — unica aggiunta voluta il selettore di tema. 18 template convertiti, -33% di peso su `/movements` (task19-0) | DONE |
| Auth assessment | Verifica che ogni API che agisce sui dati dell'utente controlli l'appartenenza all'account e non si fidi dell'input: inventario endpoint e 15 findings (3 Alta confermati: mass assignment su wallet/categorie, accettazione invito da GET, ricorrenti senza verifica id). Solo assessment, nessuna correzione (task24-0) | ASSESSMENT |
