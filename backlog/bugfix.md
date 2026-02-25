# Bugfix Log

| ID | Descrizione | Stato | Note |
|:---:|---|:---:|---|
| 1 | Elenco inviti pendenti non visibili e possibilità di eliminare gli inviti pendenti | Chiuso | Aggiunti API endpoints e UI per visualizzare ed eliminare inviti |
| 2 | Rinomina nel menu dei Setting da "Gruppi" ad "Account" | Chiuso | Modificato ps-nav.html |
| 3 | Dopo aver aggiunto un Wallet rimane il Block-ui | Chiuso | Fix modal backdrop cleanup in ps-setting-wallet.html |
| 4 | Nella fase di onboarding appare il messaggio "logout effettuato con successo" | Chiuso | Rimosso flash message dal logout route |
| 5 | Nella gestione Wallet viene visualizzato il codice a front end con visualizzazione errata. Non visualizzare il codice ma solo il nome Wallet | Chiuso | Rimosso badge wallet code da ps-setting-wallet.html |
| 6 | Nelle dashboard viene visualizzato il code del Wallet, visualizzare solo il name | Chiuso | Modificati stats repository per usare wallet.name via JOIN |
| 7 | Gestione Membership: visualizzare l'elenco degli utenti di un account | Chiuso | Implementata chiamata API /api/accounts/{id}/users in ps-setting-group.html |
| 8 | Aumento durata sessione a 7gg | Chiuso | Modificato PERMANENT_SESSION_LIFETIME da 3600 a 604800 in app.py |
| 9 | Visualizzare il valore nei grafici delle dashboard | Chiuso | Aggiunto plugin chartjs-plugin-datalabels in dashboard yearly e monthly |
| 10 | Cambia i metatag per visualizzare le informazioni di pyspendless e non quelle di adminLTE | Chiuso | Modificati metatag in ps-base.html |
| 11 | Nella home, nelle card titolo e sottotitolo risultano attaccati: "Nuovo MovimentoInserisci una nuova spesa o entrata" | Chiuso | Aggiunta classe mb-2 ai card-title in ps-home.html |
