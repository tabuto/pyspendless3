crea un file SPECS.md contenente tutte le specifiche per la realizzazione di una webApp in python3, flask, Alchemy e SQLLite per il salvataggio delle spese.

L'applicazione permette solo agli utenti in una whitelist di registrarsi tramite google login.
L'applicazione permette ad un utente registrato di:
aggiungere 1 gruppo (nomeGruppo)
Invitare qualcuno a condividere il gruppo

Ad ogni account sono legati uno o più utenti
Ad ogni account sono legati uno o più wallet
Ad ogni wallet sono legati i movimenti (le spese)
Ogni movimento è legato ad un utente, una categoria, un wallet
creare, aggiungere e modificare dei wallet 
creare, aggiungere e modificare delle spese
creare, aggiungere e modificare delle categorie

per essere retrocompatibile con un applicazione esistente la tabelle delle spese sarà:

CREATE TABLE MOVEMENTS(id varchar(100) PRIMARY KEY,move_date date, move_year int, move_month int, category varchar(100), wallet varchar(100), income decimal(10,2),expense decimal(10,2),note varchar(255),user varchar(100), account_id int)


Suddividi l'applicazione in
pyspendless/
│
├── app.py                # Entry point e definizioni delle rotte (API)
├── models.py             # Definizione delle tabelle (Classi SQLAlchemy)
├── conf.py               # Configurazione e connessione al DB
├── repository.py         # Funzioni CRUD (Logica di astrazione)
└── .env                  # Variabili d'ambiente (Connection String)

Tutte le configurazioni e le costanti devono risiedere nel gile conf.py
nel file .env andranno i secret e le variabili d'ambiente
Descrivi lo script per l'ambiente virtuale del progetto
Descrivi le entità coinvolte nell'applicazione