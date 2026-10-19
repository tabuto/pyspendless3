"""
Repository per PySpendless
Funzioni CRUD e logica di accesso ai dati
"""

import uuid
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, text
from typing import Optional, List, Dict, Any

# Support both relative and absolute imports
try:
    from .models import (
        Account, User, Wallet, Category, CategoryTemplate, 
        EmailWhitelist, Movement, UserGroup, GroupMembership, Token,
        RecurrentMovement
    )
except ImportError:
    from models import (
        Account, User, Wallet, Category, CategoryTemplate, 
        EmailWhitelist, Movement, UserGroup, GroupMembership, Token,
        RecurrentMovement
    )


class UnauthorizedError(Exception):
    """Eccezione per accesso non autorizzato"""
    pass


class UserRepository:
    """Repository per gestione utenti e autenticazione"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def is_email_whitelisted(self, email: str) -> bool:
        """Verifica se un'email è in whitelist"""
        whitelist_entry = self.db.query(EmailWhitelist).filter_by(email=email).first()
        return whitelist_entry is not None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Recupera un utente tramite Google ID"""
        return self.db.query(User).filter_by(google_id=google_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Recupera un utente tramite email"""
        return self.db.query(User).filter_by(email=email).first()
    
    def create_user_from_oauth(self, user_info: Dict[str, Any], account_id: Optional[int] = None) -> User:
        """
        Crea un nuovo utente e account dopo autenticazione OAuth Google.
        Se l'utente esiste già, lo ritorna.
        
        Args:
            user_info: Dizionario con i dati dell'utente da Google OAuth
                       Deve contenere: 'sub' (google_id), 'email', 'name'
            account_id: ID dell'account a cui associare l'utente (opzionale).
                       Se fornito, l'utente viene creato in quell'account invece di crearne uno nuovo.
        
        Returns:
            User: L'oggetto User creato o esistente
        
        Raises:
            UnauthorizedError: Se l'email non è in whitelist
            SQLAlchemyError: Per errori di database
        """
        email = user_info.get('email')
        google_id = user_info.get('sub')
        name = user_info.get('name', 'Utente')
        
        # 1. Whitelist Check
        if not self.is_email_whitelisted(email):
            raise UnauthorizedError(f"Email {email} non in whitelist")
        
        # 2. Check User Existence (prima per email, poi per google_id)
        existing_user = self.get_user_by_email(email)
        if existing_user:
            # Utente già esistente con questa email
            # Aggiorna google_id se è cambiato
            if existing_user.google_id != google_id:
                existing_user.google_id = google_id
                self.db.commit()
            return existing_user
        
        # Se non trovato per email, prova con google_id
        existing_user = self.get_user_by_google_id(google_id)
        if existing_user:
            return existing_user
        
        try:
            # 3. Create Account (solo se account_id non è fornito)
            if account_id is None:
                new_account = Account(
                    name=f"Account di {name}",
                    created_at=datetime.utcnow()
                )
                self.db.add(new_account)
                self.db.flush()  # Per ottenere l'ID dell'account
                account_id = new_account.id
                role = 'owner'
                create_categories = True
            else:
                # Se account_id è fornito, l'utente è un membro invitato
                role = 'member'
                create_categories = False
            
            # 4. Create User
            new_user = User(
                public_uid=str(uuid.uuid4()),
                google_id=google_id,
                email=email,
                name=name,
                account_id=account_id,
                role=role,
                created_at=datetime.utcnow()
            )
            self.db.add(new_user)
            
            # 5. Copy Categories from Templates (solo se nuovo account)
            if create_categories:
                self._create_default_categories(account_id)
            
            # Commit della transazione
            self.db.commit()
            
            return new_user
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def _create_default_categories(self, account_id: int) -> None:
        """
        Crea le categorie di default per un nuovo account
        copiando i template dalla tabella CategoryTemplate
        """
        templates = self.db.query(CategoryTemplate).all()
        
        for template in templates:
            new_category = Category(
                name=template.name,
                type=template.type,
                account_id=account_id,
                template_id=template.id
            )
            self.db.add(new_category)
    
    def complete_onboarding(self, user_info: Dict[str, Any], account_name: str, wallet_name: str) -> User:
        """
        Completa il processo di onboarding per un nuovo utente.
        Crea Account, User, Wallet e le categorie di default in una singola transazione.
        
        Args:
            user_info: Dizionario con i dati dell'utente da Google OAuth
                       Deve contenere: 'sub' (google_id), 'email', 'name'
            account_name: Nome dell'account da creare
            wallet_name: Nome del wallet da creare
        
        Returns:
            User: L'oggetto User creato
        
        Raises:
            ValueError: Se i parametri sono mancanti o non validi
            SQLAlchemyError: Per errori di database
        """
        if not account_name or not wallet_name:
            raise ValueError("account_name e wallet_name sono obbligatori")
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        name = user_info.get('name', 'Utente')
        
        if not email or not google_id:
            raise ValueError("user_info deve contenere 'email' e 'sub'")
        
        try:
            # 1. Crea Account
            new_account = Account(
                name=account_name,
                created_at=datetime.utcnow()
            )
            self.db.add(new_account)
            self.db.flush()  # Per ottenere l'ID dell'account
            account_id = new_account.id
            
            # 2. Crea User
            new_user = User(
                public_uid=str(uuid.uuid4()),
                google_id=google_id,
                email=email,
                name=name,
                account_id=account_id,
                role='owner',
                created_at=datetime.utcnow()
            )
            self.db.add(new_user)
            
            # 3. Crea Wallet
            wallet_code = str(uuid.uuid4())
            new_wallet = Wallet(
                code=wallet_code,
                name=wallet_name,
                currency='EUR',  # Default, potrebbe essere parametrizzato in futuro
                account_id=account_id,
                created_at=datetime.utcnow()
            )
            self.db.add(new_wallet)
            
            # 4. Setup Categorie da template
            self._create_default_categories(account_id)
            
            # Commit della transazione
            self.db.commit()
            
            return new_user
            
        except Exception as e:
            self.db.rollback()
            raise
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Recupera un utente tramite ID"""
        return self.db.query(User).filter_by(id=user_id).first()

    def get_users_by_account(self, account_id: int) -> List[User]:
        """Recupera tutti gli utenti associati a un account"""
        return self.db.query(User).filter_by(account_id=account_id).all()

    def get_preferred_wallet(self, user_id: int) -> Optional[Wallet]:
        """
        Ritorna il wallet preferito dell'utente, oppure **None** se non ne ha
        impostato uno (task22-0).

        A differenza della versione precedente (MB-004) il preferito è
        un'impostazione del singolo utente, non dell'account: due utenti dello
        stesso account possono avere preferiti diversi.
        """
        user = self.get_user_by_id(user_id)
        if not user or not user.preferred_wallet_id:
            return None
        return self.db.query(Wallet).filter_by(id=user.preferred_wallet_id).first()

    def set_preferred_wallet(self, user_id: int, wallet_id: int, account_id: int) -> Optional[Wallet]:
        """
        Imposta il wallet preferito dell'utente (task22-0).

        Verifica che l'utente e il wallet appartengano entrambi ad
        `account_id`, per evitare che un utente imposti come preferito un
        wallet di un altro account.

        Returns:
            Il wallet promosso, None se utente o wallet non esistono o non
            appartengono all'account.
        """
        user = self.get_user_by_id(user_id)
        if not user or user.account_id != account_id:
            return None

        wallet = self.db.query(Wallet).filter_by(id=wallet_id, account_id=account_id).first()
        if not wallet:
            return None

        user.preferred_wallet_id = wallet.id
        self.db.commit()
        return wallet

    def unset_preferred_wallet(self, user_id: int, wallet_id: int) -> Optional[Wallet]:
        """
        Toglie la preferenza dell'utente (task22-0): torna a "nessun preferito".

        `wallet_id` deve corrispondere al preferito corrente dell'utente,
        stesso vincolo della versione precedente (evita che una DELETE su un
        wallet non preferito abbia effetto).

        Returns:
            Il wallet che era preferito; None se l'utente non esiste, non
            aveva un preferito impostato, o `wallet_id` non è quello attuale.
        """
        user = self.get_user_by_id(user_id)
        if not user or user.preferred_wallet_id != wallet_id:
            return None

        wallet = self.db.query(Wallet).filter_by(id=user.preferred_wallet_id).first()
        user.preferred_wallet_id = None
        self.db.commit()
        return wallet
    
    def delete_user(self, user_id: int) -> bool:
        """
        Elimina un utente e i suoi dati associati.
        Se l'utente è l'unico nell'account, elimina anche l'account e tutti i dati.
        Altrimenti elimina solo l'utente e i suoi movimenti.
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        account_id = user.account_id
        
        # Conta quanti utenti ci sono nell'account
        users_in_account = self.get_users_by_account(account_id)
        
        try:
            if len(users_in_account) <= 1:
                # Unico utente: elimina tutto l'account
                # Prima elimina tutti i movimenti
                self.db.query(Movement).filter_by(account_id=account_id).delete()
                
                # Elimina tutte le categorie
                self.db.query(Category).filter_by(account_id=account_id).delete()
                
                # Elimina tutti i wallet
                self.db.query(Wallet).filter_by(account_id=account_id).delete()
                
                # Elimina tutti i gruppi e membership
                # Usa una subquery per evitare problemi con colonne mancanti
                group_ids = [g[0] for g in self.db.query(UserGroup.id).filter_by(account_id=account_id).all()]
                for group_id in group_ids:
                    self.db.query(GroupMembership).filter_by(group_id=group_id).delete()
                self.db.query(UserGroup).filter_by(account_id=account_id).delete()
                
                # Elimina l'utente
                self.db.delete(user)
                
                # Elimina l'account
                account = self.db.query(Account).filter_by(id=account_id).first()
                if account:
                    self.db.delete(account)
            else:
                # Più utenti: elimina solo l'utente e i suoi movimenti
                # Elimina i movimenti dell'utente
                self.db.query(Movement).filter_by(user_id=user_id).delete()
                
                # Elimina le membership dell'utente nei gruppi
                self.db.query(GroupMembership).filter_by(user_id=user_id).delete()
                
                # Elimina l'utente
                self.db.delete(user)
            
            self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e


class AccountRepository:
    """Repository per gestione account"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_account(self, account_id: int) -> Optional[Account]:
        """Recupera un account tramite ID"""
        return self.db.query(Account).filter_by(id=account_id).first()
    
    def create_account(self, name: str) -> Account:
        """Crea un nuovo account"""
        account = Account(
            name=name,
            created_at=datetime.utcnow()
        )
        self.db.add(account)
        self.db.commit()
        return account
    
    def update_account(self, account_id: int, data: Dict[str, Any]) -> Optional[Account]:
        """Aggiorna un account"""
        account = self.get_account(account_id)
        if not account:
            return None
        
        for key, value in data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        self.db.commit()
        return account


class WalletRepository:
    """Repository per gestione wallet"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # `order_index` è puro ordinamento di visualizzazione (task7-1).
    #
    # Fino al task22-0, `order_index == 0` era anche riservato per convenzione
    # al "wallet preferito dell'account" (MB-004). Da task22-0 la preferenza è
    # per singolo utente (vedi `UserRepository.get/set/unset_preferred_wallet`)
    # e non è più legata in alcun modo a `order_index`: nessun valore è più
    # riservato.
    MIN_ORDER_INDEX = 0

    @classmethod
    def validate_order_index(cls, order_index: Any) -> int:
        """
        Valida un `order_index` fornito dall'utente.

        Raises:
            ValueError: se non è un intero o se è negativo.
        """
        try:
            value = int(order_index)
        except (TypeError, ValueError):
            raise ValueError("L'ordine deve essere un numero intero.")

        if value < cls.MIN_ORDER_INDEX:
            raise ValueError(
                "L'ordine minimo è {}.".format(cls.MIN_ORDER_INDEX)
            )

        return value

    def get_wallets_for_account(self, account_id: int) -> List[Wallet]:
        """Recupera tutti i wallet di un account ordinati per order_index e nome"""
        return self.db.query(Wallet).filter_by(account_id=account_id).order_by(Wallet.order_index.asc(), Wallet.name.asc()).all()

    def get_wallet(self, wallet_id: int) -> Optional[Wallet]:
        """Recupera un wallet tramite ID"""
        return self.db.query(Wallet).filter_by(id=wallet_id).first()

    def create_wallet(self, code: str, name: str, account_id: int, currency: str = 'EUR', order_index: Optional[int] = None) -> Wallet:
        """Crea un nuovo wallet."""
        # Se order_index non è specificato, assegna automaticamente MAX+1
        if order_index is None:
            max_order = self.db.query(func.max(Wallet.order_index)).filter_by(account_id=account_id).scalar()
            order_index = (max_order + 1) if max_order is not None else self.MIN_ORDER_INDEX
        else:
            order_index = self.validate_order_index(order_index)

        order_index = max(order_index, self.MIN_ORDER_INDEX)

        wallet = Wallet(
            code=code,
            name=name,
            currency=currency,
            account_id=account_id,
            created_at=datetime.utcnow(),
            order_index=order_index
        )
        self.db.add(wallet)
        self.db.commit()
        return wallet
    
    def update_wallet(self, wallet_id: int, data: Dict[str, Any]) -> Optional[Wallet]:
        """
        Aggiorna un wallet.

        L'`order_index` passato dall'utente viene validato (intero >= 0).

        Raises:
            ValueError: se `order_index` non è valido.
        """
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            return None

        data = dict(data or {})
        if 'order_index' in data:
            data['order_index'] = self.validate_order_index(data['order_index'])

        for key, value in data.items():
            if hasattr(wallet, key):
                setattr(wallet, key, value)

        self.db.commit()
        return wallet
    
    def delete_wallet(self, wallet_id: int) -> bool:
        """
        Elimina un wallet.

        SQLite non applica qui il vincolo FK (nessun `PRAGMA foreign_keys`):
        libera esplicitamente gli utenti che avessero questo wallet come
        preferito, per non lasciare un `preferred_wallet_id` pendente
        (task22-0).
        """
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            return False

        self.db.query(User).filter_by(preferred_wallet_id=wallet_id).update(
            {User.preferred_wallet_id: None}
        )
        self.db.delete(wallet)
        self.db.commit()
        return True


class CategoryRepository:
    """Repository per gestione categorie"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_categories_for_account(self, account_id: int, order_by_index: bool = True) -> List[Category]:
        """
        Recupera tutte le categorie di un account
        
        Args:
            account_id: ID dell'account
            order_by_index: Se True, ordina per order_index, altrimenti per nome
        
        Returns:
            Lista di categorie
        """
        query = self.db.query(Category).filter_by(account_id=account_id)
        
        if order_by_index:
            return query.order_by(Category.order_index, Category.name).all()
        else:
            return query.order_by(Category.name).all()
    
    def get_category(self, category_id: int) -> Optional[Category]:
        """Recupera una categoria tramite ID"""
        return self.db.query(Category).filter_by(id=category_id).first()
    
    def create_category(self, name: str, account_id: int, type: str, template_id: Optional[int] = None, order_index: int = 0) -> Category:
        """Crea una nuova categoria"""
        category = Category(
            name=name,
            type=type,
            account_id=account_id,
            template_id=template_id,
            order_index=order_index
        )
        self.db.add(category)
        self.db.commit()
        return category
    
    def update_category(self, category_id: int, data: Dict[str, Any]) -> Optional[Category]:
        """
        Aggiorna una categoria con gestione automatica di rinomina e merge.
        
        Logica:
        - Se il nuovo nome NON esiste: rinomina semplice + update movements
        - Se il nuovo nome ESISTE già: merge movements + elimina categoria vecchia
        
        Args:
            category_id: ID della categoria da aggiornare
            data: Dizionario con i campi da aggiornare (name, type, order_index)
        
        Returns:
            Categoria aggiornata o None se non trovata
        
        Raises:
            SQLAlchemyError: In caso di errore durante la transazione
        """
        category = self.get_category(category_id)
        if not category:
            return None
        
        account_id = category.account_id
        old_name = category.name
        new_name = data.get('name', old_name)
        
        try:
            # Caso speciale: se il nome viene modificato
            if new_name != old_name:
                # Verifica se esiste già una categoria con il nuovo nome (stesso account e tipo)
                existing_category = self.db.query(Category).filter_by(
                    account_id=account_id,
                    name=new_name,
                    type=category.type
                ).filter(Category.id != category_id).first()
                
                if existing_category:
                    # CASO B: Merge - Il nuovo nome esiste già
                    # 1. Aggiorna tutti i movimenti che puntano alla vecchia categoria
                    self.db.query(Movement).filter_by(
                        account_id=account_id,
                        category=old_name
                    ).update({
                        'category': new_name,
                        'category_id': existing_category.id
                    }, synchronize_session=False)
                    
                    # 2. Aggiorna order_index se specificato
                    if 'order_index' in data:
                        existing_category.order_index = data['order_index']
                    
                    # 3. Elimina la vecchia categoria (ora ridondante)
                    self.db.delete(category)
                    self.db.commit()
                    
                    return existing_category
                else:
                    # CASO A: Rinomina semplice - Il nuovo nome NON esiste
                    # 1. Aggiorna il nome nella tabella category
                    category.name = new_name
                    
                    # 2. Aggiorna retrocompatibilità: campo category in movements
                    self.db.query(Movement).filter_by(
                        account_id=account_id,
                        category=old_name
                    ).update({
                        'category': new_name
                    }, synchronize_session=False)
            
            # Aggiorna altri campi (type, order_index, ecc.)
            for key, value in data.items():
                if key != 'name' and hasattr(category, key):
                    setattr(category, key, value)
            
            self.db.commit()
            return category
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete_category(self, category_id: int, target_category_id: Optional[int] = None) -> bool:
        """
        Elimina una categoria.
        Se ha movimenti associati e viene fornita una categoria target, sposta i movimenti.
        
        Args:
            category_id: ID della categoria da eliminare
            target_category_id: ID della categoria a cui spostare i movimenti (opzionale)
        
        Returns:
            True se eliminata con successo
        
        Raises:
            ValueError: Se la categoria ha movimenti ma non viene fornita una categoria target
            SQLAlchemyError: In caso di errore durante la transazione
        """
        category = self.get_category(category_id)
        if not category:
            return False
        
        try:
            # Se è fornita una categoria target, sposta i movimenti
            if target_category_id:
                target_category = self.get_category(target_category_id)
                if not target_category:
                    raise ValueError("Categoria target non trovata")
                
                # Verifica che siano dello stesso account e tipo
                if target_category.account_id != category.account_id:
                    raise ValueError("La categoria target deve appartenere allo stesso account")
                
                if target_category.type != category.type:
                    raise ValueError("La categoria target deve essere dello stesso tipo")
                
                # Aggiorna i movimenti per puntare alla categoria target
                self.db.query(Movement).filter_by(
                    account_id=category.account_id,
                    category=category.name
                ).update({
                    'category': target_category.name,
                    'category_id': target_category_id
                }, synchronize_session=False)
            
            # Elimina la categoria
            self.db.delete(category)
            self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e


class MovementRepository:
    """Repository per gestione movimenti (spese/entrate)"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_movements_for_account(
        self,
        account_id: int,
        wallet_id: Optional[int] = None,
        user_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        category_id: Optional[int] = None,       # mantenuto per retrocompatibilità
        category_ids: Optional[List[int]] = None, # multi-selezione categorie
        category_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        keywords: Optional[List[str]] = None,    # ricerca LIKE su note
    ) -> List[Movement]:
        """
        Recupera i movimenti di un account con filtri opzionali
        """
        from sqlalchemy import or_

        query = self.db.query(Movement).filter_by(account_id=account_id)

        if wallet_id:
            query = query.filter_by(wallet_id=wallet_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if year:
            query = query.filter_by(move_year=year)
        if month:
            query = query.filter_by(move_month=month)
        # category_ids ha precedenza; category_id è il fallback legacy
        if category_ids:
            query = query.filter(Movement.category_id.in_(category_ids))
        elif category_id:
            query = query.filter_by(category_id=category_id)
        if date_from:
            query = query.filter(Movement.move_date >= date_from)
        if date_to:
            query = query.filter(Movement.move_date <= date_to)
        if keywords:
            kw_filters = [Movement.note.ilike(f'%{kw}%') for kw in keywords]
            query = query.filter(or_(*kw_filters))

        # Filtra per tipo categoria (tramite join)
        if category_type:
            query = query.join(Category, Movement.category_id == Category.id).filter(Category.type == category_type)

        return query.order_by(Movement.move_date.desc()).all()
    
    def get_movement(self, movement_id: str) -> Optional[Movement]:
        """Recupera un movimento tramite ID"""
        return self.db.query(Movement).filter_by(id=movement_id).first()
    
    def get_movement_by_id(self, movement_id: str, account_id: int) -> Optional[Movement]:
        """Recupera un movimento tramite ID verificando l'appartenenza all'account"""
        return self.db.query(Movement).filter_by(id=movement_id, account_id=account_id).first()
    
    def create_movement(self, data: Dict[str, Any]) -> Movement:
        """Crea un nuovo movimento"""
        movement = Movement(**data)
        self.db.add(movement)
        self.db.commit()
        return movement
    
    def update_movement(self, movement_id: str, data: Dict[str, Any]) -> Optional[Movement]:
        """Aggiorna un movimento"""
        movement = self.get_movement(movement_id)
        if not movement:
            return None
        
        for key, value in data.items():
            if hasattr(movement, key):
                setattr(movement, key, value)
        
        self.db.commit()
        return movement
    
    def bulk_update_movements(
        self,
        account_id: int,
        filters: Dict[str, Any],
        category=None,
        category_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> int:
        """
        Applica categoria e/o nota a tutti i movimenti di account_id che
        soddisfano i filtri (stessi filtri di get_movements_for_account),
        in un unico commit. Ritorna il numero di movimenti aggiornati.
        """
        movements = self.get_movements_for_account(account_id=account_id, **filters)

        for m in movements:
            if category_id is not None:
                m.category_id = category_id
                m.category = category
            if note is not None:
                m.note = note

        self.db.commit()
        return len(movements)

    def delete_movement(self, movement_id: str) -> bool:
        """Elimina un movimento"""
        movement = self.get_movement(movement_id)
        if not movement:
            return False

        self.db.delete(movement)
        self.db.commit()
        return True

    def get_last_inserted_for_user(self, user_id: Any, account_id: int) -> Optional[Movement]:
        """
        Recupera l'ULTIMO movimento inserito da un utente (ordine di scrittura, non di data).

        Usato dal server MCP per la verifica anti-duplicazione (task20-0, decisione D7).

        Nota: `Movement` non ha una colonna di data/ora di inserimento (`move_date` è la data
        della spesa e la PK è un UUID testuale, quindi non ordinabile cronologicamente).
        Si usa il `rowid` implicito di SQLite, che è crescente nell'ordine di INSERT.
        È una dipendenza dal motore SQLite, accettata consapevolmente per non modificare lo
        schema: se in futuro si migra a un altro DB, questo metodo va riscritto (oppure si
        aggiunge una colonna `created_at` a Movement).
        """
        base_query = self.db.query(Movement).filter(
            Movement.user_id == str(user_id),
            Movement.account_id == account_id
        )

        try:
            return base_query.order_by(text('rowid DESC')).first()
        except SQLAlchemyError:
            # Motore senza rowid (non SQLite): ripiego sulla data della spesa.
            # Meno preciso, ma non fa fallire l'inserimento.
            self.db.rollback()
            return base_query.order_by(Movement.move_date.desc()).first()

    def search_movements(
        self,
        account_id: int,
        search_text: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Cerca movimenti con ricerca full-text e paginazione
        
        Args:
            account_id: ID dell'account
            search_text: Testo da cercare (opzionale)
            page: Numero pagina (default: 1)
            per_page: Risultati per pagina (default: 20)
        
        Returns:
            Dict con: movements (lista), total (int), pages (int), current_page (int)
        """
        from sqlalchemy import or_, func
        from math import ceil
        
        # Query base con join per category e wallet
        query = self.db.query(Movement).join(
            Category, Movement.category_id == Category.id
        ).join(
            Wallet, Movement.wallet_id == Wallet.id
        ).filter(
            Movement.account_id == account_id
        )
        
        # Ricerca full-text su notes, nome categoria, nome wallet
        if search_text and search_text.strip():
            search_pattern = f"%{search_text.strip()}%"
            query = query.filter(
                or_(
                    Movement.note.ilike(search_pattern),
                    Category.name.ilike(search_pattern),
                    Wallet.name.ilike(search_pattern)
                )
            )
        
        # Conta totale risultati
        total = query.count()
        
        # Calcola numero pagine
        pages = ceil(total / per_page) if total > 0 else 1
        
        # Applica paginazione e ordinamento
        movements = query.order_by(
            Movement.move_date.desc()
        ).limit(per_page).offset((page - 1) * per_page).all()
        
        return {
            'movements': movements,
            'total': total,
            'pages': pages,
            'current_page': page,
            'per_page': per_page
        }
    
    def get_movements_stats(
        self,
        account_id: int,
        wallet_id: Optional[int] = None,
        user_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        category_id: Optional[int] = None,
        category_ids: Optional[List[int]] = None,
        category_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Calcola statistiche aggregate sui movimenti
        Returns:
            Dict con: total_income, total_expense, balance, expenses_by_category
        """
        from sqlalchemy import func, or_

        # Recupera i movimenti filtrati
        movements = self.get_movements_for_account(
            account_id=account_id,
            wallet_id=wallet_id,
            user_id=user_id,
            year=year,
            month=month,
            category_id=category_id,
            category_ids=category_ids,
            category_type=category_type,
            date_from=date_from,
            date_to=date_to,
            keywords=keywords,
        )
        
        # Calcola totali
        total_income = sum(float(m.income) if m.income else 0 for m in movements)
        total_expense = sum(float(m.expense) if m.expense else 0 for m in movements)
        balance = total_income - total_expense
        
        # Raggruppa movimenti per categoria in base al tipo
        # Se filtrato per tipo 'income', raggruppa le entrate; altrimenti le spese
        if category_type == 'income':
            # Raggruppa entrate per categoria
            query = self.db.query(
                Category.name,
                func.sum(Movement.income).label('total')
            ).join(
                Movement, Movement.category_id == Category.id
            ).filter(
                Movement.account_id == account_id,
                Movement.income.isnot(None)
            )
        else:
            # Raggruppa spese per categoria (default)
            query = self.db.query(
                Category.name,
                func.sum(Movement.expense).label('total')
            ).join(
                Movement, Movement.category_id == Category.id
            ).filter(
                Movement.account_id == account_id,
                Movement.expense.isnot(None)
            )
        
        # Applica gli stessi filtri
        if wallet_id:
            query = query.filter(Movement.wallet_id == wallet_id)
        if user_id:
            query = query.filter(Movement.user_id == user_id)
        if year:
            query = query.filter(Movement.move_year == year)
        if month:
            query = query.filter(Movement.move_month == month)
        if category_ids:
            query = query.filter(Movement.category_id.in_(category_ids))
        elif category_id:
            query = query.filter(Movement.category_id == category_id)
        if date_from:
            query = query.filter(Movement.move_date >= date_from)
        if date_to:
            query = query.filter(Movement.move_date <= date_to)
        if keywords:
            kw_filters = [Movement.note.ilike(f'%{kw}%') for kw in keywords]
            query = query.filter(or_(*kw_filters))
        if category_type:
            query = query.filter(Category.type == category_type)
        
        expenses_by_category = query.group_by(Category.name).all()
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': balance,
            'expenses_by_category': [
                {'category': cat, 'total': float(total) if total else 0}
                for cat, total in expenses_by_category
            ]
        }


class GroupRepository:
    """Repository per gestione gruppi e inviti"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_group(self, name: str, account_id: int, owner_user_id: int) -> UserGroup:
        """Crea un nuovo gruppo"""
        group = UserGroup(
            name=name,
            account_id=account_id,
            owner_user_id=owner_user_id,
            created_at=datetime.utcnow()
        )
        self.db.add(group)
        self.db.commit()
        return group
    
    def get_group(self, group_id: int) -> Optional[UserGroup]:
        """Recupera un gruppo tramite ID"""
        return self.db.query(UserGroup).filter_by(id=group_id).first()
    
    def create_invite(
        self, 
        group_id: int, 
        invite_email: str, 
        invited_by_user_id: int
    ) -> GroupMembership:
        """Crea un invito a un gruppo"""
        token = str(uuid.uuid4())
        
        membership = GroupMembership(
            group_id=group_id,
            invite_email=invite_email,
            invited_by_user_id=invited_by_user_id,
            status='pending',
            token=token,
            created_at=datetime.utcnow()
        )
        self.db.add(membership)
        self.db.commit()
        return membership
    
    def get_group_members(self, group_id: int) -> List[GroupMembership]:
        """Recupera tutti i membri di un gruppo"""
        return self.db.query(GroupMembership).filter_by(group_id=group_id).all()
    
    def accept_invite(self, token: str, user_id: int) -> Optional[GroupMembership]:
        """Accetta un invito a un gruppo"""
        membership = self.db.query(GroupMembership).filter_by(token=token).first()
        if not membership or membership.status != 'pending':
            return None
        
        membership.user_id = user_id
        membership.status = 'accepted'
        self.db.commit()
        return membership


class TokenRepository:
    """Repository per gestione token di invito"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_token(
        self, 
        token_type: str, 
        payload: Dict[str, Any], 
        expire_days: int = 7
    ) -> Token:
        """
        Crea un nuovo token
        
        Args:
            token_type: Tipo di token (es. "SHARE")
            payload: Dizionario con i dati del token
            expire_days: Giorni di validità del token
        
        Returns:
            Token creato
        """
        token_uuid = str(uuid.uuid4())
        create_date = datetime.utcnow()
        expire_date = create_date + timedelta(days=expire_days)
        
        token = Token(
            uuid=token_uuid,
            type=token_type,
            create_date=create_date,
            expire_date=expire_date,
            status='PENDING',
            payload=json.dumps(payload)
        )
        
        self.db.add(token)
        self.db.commit()
        return token
    
    def get_token(self, token_uuid: str) -> Optional[Token]:
        """Recupera un token tramite UUID"""
        return self.db.query(Token).filter_by(uuid=token_uuid).first()
    
    def validate_token(self, token_uuid: str) -> Optional[Token]:
        """
        Valida un token verificando che sia:
        - Esistente
        - Status = PENDING
        - Non scaduto
        
        Returns:
            Token se valido, None altrimenti
        """
        token = self.get_token(token_uuid)
        
        if not token:
            return None
        
        if token.status != 'PENDING':
            return None
        
        if datetime.utcnow() > token.expire_date:
            # Token scaduto - aggiorna status
            token.status = 'EXPIRED'
            self.db.commit()
            return None
        
        return token
    
    def get_payload(self, token_uuid: str) -> Optional[Dict[str, Any]]:
        """Recupera il payload di un token come dizionario"""
        token = self.get_token(token_uuid)
        if not token:
            return None
        
        try:
            return json.loads(token.payload)
        except json.JSONDecodeError:
            return None
    
    def mark_as_used(self, token_uuid: str) -> bool:
        """Marca un token come usato"""
        token = self.get_token(token_uuid)
        if not token:
            return False
        
        token.status = 'USED'
        self.db.commit()
        return True
    
    def mark_as_expired(self, token_uuid: str) -> bool:
        """Marca un token come scaduto"""
        token = self.get_token(token_uuid)
        if not token:
            return False
        
        token.status = 'EXPIRED'
        self.db.commit()
        return True
    
    def get_pending_invites_for_account(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Recupera tutti gli inviti pendenti per un account
        
        Args:
            account_id: ID dell'account
            
        Returns:
            Lista di dizionari con i dati degli inviti pendenti
        """
        tokens = self.db.query(Token).filter(
            Token.type == 'SHARE',
            Token.status == 'PENDING',
            Token.expire_date > datetime.utcnow()
        ).all()
        
        # Filtra per account_id nel payload
        invites = []
        for token in tokens:
            try:
                payload = json.loads(token.payload)
                if payload.get('account_id') == account_id:
                    invites.append({
                        'token_uuid': token.uuid,
                        'email': payload.get('email'),
                        'created_at': token.create_date.strftime('%d/%m/%Y %H:%M'),
                        'expires_at': token.expire_date.strftime('%d/%m/%Y %H:%M')
                    })
            except json.JSONDecodeError:
                continue
        
        return invites
    
    def delete_token(self, token_uuid: str) -> bool:
        """Elimina un token"""
        token = self.get_token(token_uuid)
        if not token:
            return False

        self.db.delete(token)
        self.db.commit()
        return True

    # ===== TOKEN PERSONALI PER IL SERVER MCP (task20-0) =====
    #
    # Riusano la stessa tabella Token, senza modifiche allo schema:
    #   type        = 'MCP'
    #   uuid        = SHA-256 del segreto (il segreto in chiaro NON viene mai salvato)
    #   status      = 'PENDING' -> token attivo ; 'USED' -> token revocato
    #   expire_date = creazione + 365 giorni
    #   payload     = {"user_id": ..., "account_id": ..., "label": ..., "prefix": ...}

    MCP_TOKEN_TYPE = 'MCP'
    MCP_TOKEN_EXPIRE_DAYS = 365

    @staticmethod
    def hash_secret(secret: str) -> str:
        """Calcola l'hash SHA-256 (esadecimale) di un segreto."""
        return hashlib.sha256(secret.encode('utf-8')).hexdigest()

    def _create_hashed_secret_token(
        self,
        token_type: str,
        build_payload,
        expire_days: Optional[int] = None,
        expire_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fattorizza la creazione di un token 'a segreto hashato': genera un secret
        casuale, salva in DB solo il suo hash SHA-256 come `uuid` (PK), il segreto
        in chiaro viene restituito una volta sola e non è più recuperabile.

        Usata sia da `create_mcp_token` (type='MCP', task20-0) sia dai nuovi
        metodi OAuth (task23-0): esattamente uno fra `expire_days`/`expire_seconds`
        va passato (i codici/token OAuth hanno TTL in secondi, non in giorni).
        `build_payload(secret, prefix)` costruisce il payload JSON del token: lo
        riceve come callable (non come dict già pronto) perché alcuni payload
        includono il `prefix` del secret, generato solo dentro questo helper.

        Returns:
            dict con 'secret' (in chiaro), 'token_hash', 'prefix', 'create_date',
            'expire_date' (i due oggetti datetime, oltre alle stringhe formattate)
        """
        secret = str(uuid.uuid4())
        token_hash = self.hash_secret(secret)
        prefix = secret[:8]
        payload = build_payload(secret, prefix)

        create_date = datetime.utcnow()
        if expire_seconds is not None:
            expire_date = create_date + timedelta(seconds=expire_seconds)
        else:
            expire_date = create_date + timedelta(days=expire_days or 0)

        token = Token(
            uuid=token_hash,
            type=token_type,
            create_date=create_date,
            expire_date=expire_date,
            status='PENDING',
            payload=json.dumps(payload)
        )

        self.db.add(token)
        self.db.commit()

        return {
            'secret': secret,
            'token_hash': token_hash,
            'prefix': prefix,
            'create_date': create_date,
            'expire_date': expire_date,
            'created_at': create_date.strftime('%d/%m/%Y %H:%M'),
            'expires_at': expire_date.strftime('%d/%m/%Y %H:%M')
        }

    def _validate_hashed_secret_token(self, secret: str, token_type: str) -> Optional[Token]:
        """
        Fattorizza la validazione di un token 'a segreto hashato': hash del
        segreto presentato, `validate_token` (status/scadenza), controllo del
        `type` e confronto a tempo costante sul valore letto dal DB.

        Usata sia da `validate_mcp_secret` (type='MCP') sia dai nuovi metodi
        OAuth (task23-0).
        """
        if not secret:
            return None

        token_hash = self.hash_secret(secret)
        token = self.validate_token(token_hash)

        if not token:
            return None

        if token.type != token_type:
            return None

        # Confronto a tempo costante sul valore effettivamente letto dal DB
        if not hmac.compare_digest(str(token.uuid), token_hash):
            return None

        return token

    def create_mcp_token(
        self,
        user_id: Any,
        account_id: int,
        label: str,
        expire_days: int = MCP_TOKEN_EXPIRE_DAYS
    ) -> Dict[str, Any]:
        """
        Crea un token personale per il server MCP.

        In DB finisce solo l'hash del segreto: il valore in chiaro viene restituito
        qui una volta sola e non è più recuperabile in seguito.

        Returns:
            dict con 'secret' (in chiaro, da mostrare una sola volta), 'token_hash',
            'label', 'created_at', 'expires_at', 'prefix'
        """
        created = self._create_hashed_secret_token(
            self.MCP_TOKEN_TYPE,
            build_payload=lambda secret, prefix: {
                'user_id': str(user_id),
                'account_id': account_id,
                'label': label,
                'prefix': prefix
            },
            expire_days=expire_days
        )

        return {
            'secret': created['secret'],
            'token_hash': created['token_hash'],
            'prefix': created['prefix'],
            'label': label,
            'created_at': created['created_at'],
            'expires_at': created['expires_at']
        }

    def validate_mcp_secret(self, secret: str) -> Optional[Token]:
        """
        Valida il segreto presentato da un client MCP.

        Verifica: hash esistente, type = 'MCP', status = 'PENDING', non scaduto.

        Returns:
            Token se valido, None altrimenti
        """
        return self._validate_hashed_secret_token(secret, self.MCP_TOKEN_TYPE)

    def get_mcp_tokens_for_user(self, user_id: Any) -> List[Dict[str, Any]]:
        """
        Recupera i token MCP attivi di un utente.

        Non restituisce mai il segreto (non è nemmeno salvato): solo il prefisso
        dei primi 8 caratteri, per riconoscere il token nell'elenco.
        """
        tokens = self.db.query(Token).filter(
            Token.type == self.MCP_TOKEN_TYPE,
            Token.status == 'PENDING'
        ).order_by(Token.create_date.desc()).all()

        result = []
        for token in tokens:
            try:
                payload = json.loads(token.payload)
            except (json.JSONDecodeError, TypeError):
                continue

            if str(payload.get('user_id')) != str(user_id):
                continue

            result.append({
                'token_hash': token.uuid,
                'label': payload.get('label') or 'Token',
                'prefix': payload.get('prefix', ''),
                'created_at': token.create_date.strftime('%d/%m/%Y %H:%M'),
                'expires_at': token.expire_date.strftime('%d/%m/%Y %H:%M'),
                'expired': datetime.utcnow() > token.expire_date
            })

        return result

    def get_mcp_token_owner(self, token_hash: str) -> Optional[str]:
        """Ritorna l'user_id proprietario di un token MCP, o None se non esiste."""
        token = self.get_token(token_hash)
        if not token or token.type != self.MCP_TOKEN_TYPE:
            return None

        try:
            payload = json.loads(token.payload)
        except (json.JSONDecodeError, TypeError):
            return None

        owner = payload.get('user_id')
        return str(owner) if owner is not None else None

    # ===== TOKEN OAUTH2 PER /mcp-oauth2 (task23-0) =====
    #
    # Riusano la stessa tabella Token, senza modifiche allo schema, con tre nuovi
    # `type` paralleli a 'MCP':
    #   OAUTH_CODE    = authorization code (PKCE), monouso, TTL 60s
    #   OAUTH_ACCESS  = access token, TTL 3600s (max richiesto da Alexa+)
    #   OAUTH_REFRESH = refresh token (solo per authorization_code, mai per
    #                   client_credentials), monouso con rotazione, TTL 60 giorni
    #
    # payload comune a tutti e tre: user_id (None per client_credentials),
    # account_id, client_id, scope, resource. OAUTH_CODE porta in più
    # redirect_uri e code_challenge, per la verifica in `redeem_oauth_code`.
    #
    # Revoca (manuale o di una connessione): si riusa lo status 'EXPIRED'
    # (mark_as_expired, già generico) invece di introdurre un nuovo status
    # 'REVOKED', che richiederebbe di toccare il CheckConstraint su Token.status
    # in models.py — non necessario per i criteri di accettazione del task.

    OAUTH_CODE_TYPE = 'OAUTH_CODE'
    OAUTH_ACCESS_TYPE = 'OAUTH_ACCESS'
    OAUTH_REFRESH_TYPE = 'OAUTH_REFRESH'

    OAUTH_CODE_TTL_SECONDS = 60
    OAUTH_ACCESS_TTL_SECONDS = 3600
    OAUTH_REFRESH_TTL_DAYS = 60

    @staticmethod
    def _pkce_challenge_from_verifier(code_verifier: str) -> str:
        """code_challenge attesto da un code_verifier, per PKCE S256 (RFC 7636)."""
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

    def create_oauth_code(
        self,
        user_id: Any,
        account_id: Optional[int],
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        resource: str,
        scope: Optional[str] = None
    ) -> str:
        """
        Crea un OAUTH_CODE: monouso, TTL breve (60s). Lega insieme user_id/
        account_id, client_id, redirect_uri, code_challenge (PKCE) e resource,
        così `redeem_oauth_code` può verificarli tutti alla redenzione.

        Returns:
            Il codice in chiaro (da passare nel redirect verso redirect_uri).
        """
        created = self._create_hashed_secret_token(
            self.OAUTH_CODE_TYPE,
            build_payload=lambda secret, prefix: {
                'user_id': str(user_id) if user_id is not None else None,
                'account_id': account_id,
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'code_challenge': code_challenge,
                'resource': resource,
                'scope': scope
            },
            expire_seconds=self.OAUTH_CODE_TTL_SECONDS
        )
        return created['secret']

    def redeem_oauth_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: Optional[str],
        code_verifier: str,
        resource: str
    ) -> Optional[Dict[str, Any]]:
        """
        Riscatta un OAUTH_CODE: valida hash/type/status/scadenza (via
        `_validate_hashed_secret_token`), poi che client_id/redirect_uri/resource
        coincidano con quelli dell'authorize originale e che il PKCE sia corretto.
        `redirect_uri=None` significa "il client non l'ha ripetuto nella richiesta
        di token": il confronto viene saltato (il codice resta legato al client
        autenticato e al PKCE), vedi `_token_authorization_code`.
        Monouso: lo marca USED (mark_as_used, generico) solo alla redenzione
        riuscita.

        Returns:
            Il payload del codice (user_id, account_id, scope, ...) se tutto è
            valido, altrimenti None. Il motivo del fallimento non è nel valore di
            ritorno (anti-enumerazione): resta nel log applicativo del chiamante.
        """
        token = self._validate_hashed_secret_token(code, self.OAUTH_CODE_TYPE)
        if not token:
            return None

        try:
            payload = json.loads(token.payload)
        except (json.JSONDecodeError, TypeError):
            return None

        if payload.get('client_id') != client_id:
            return None
        if redirect_uri is not None and payload.get('redirect_uri') != redirect_uri:
            return None
        if payload.get('resource') != resource:
            return None

        expected_challenge = payload.get('code_challenge')
        if not code_verifier or not expected_challenge:
            return None
        if not hmac.compare_digest(
            self._pkce_challenge_from_verifier(code_verifier), expected_challenge
        ):
            return None

        self.mark_as_used(token.uuid)
        return payload

    def create_oauth_access_token(
        self,
        user_id: Any,
        account_id: Optional[int],
        client_id: str,
        scope: Optional[str],
        resource: str
    ) -> Dict[str, Any]:
        """
        Crea un access token OAuth. `user_id`/`account_id` sono None per i token
        client_credentials (service-level, nessun dato utente — vincolo Alexa+).
        """
        created = self._create_hashed_secret_token(
            self.OAUTH_ACCESS_TYPE,
            build_payload=lambda secret, prefix: {
                'user_id': str(user_id) if user_id is not None else None,
                'account_id': account_id,
                'client_id': client_id,
                'scope': scope,
                'resource': resource
            },
            expire_seconds=self.OAUTH_ACCESS_TTL_SECONDS
        )
        return {
            'access_token': created['secret'],
            'token_hash': created['token_hash'],
            'expires_in': self.OAUTH_ACCESS_TTL_SECONDS,
            'expires_at': created['expires_at']
        }

    def validate_oauth_access_token(self, secret: str) -> Optional[Token]:
        """Valida un access token OAuth. Stesso schema di `validate_mcp_secret`."""
        return self._validate_hashed_secret_token(secret, self.OAUTH_ACCESS_TYPE)

    def create_oauth_refresh_token(
        self,
        user_id: Any,
        account_id: Optional[int],
        client_id: str,
        scope: Optional[str],
        resource: str
    ) -> Dict[str, Any]:
        """
        Crea un refresh token OAuth. SOLO per authorization_code: non va mai
        chiamato per client_credentials (vincolo esplicito Alexa+, verificato dal
        chiamante in oauth_server.py).
        """
        created = self._create_hashed_secret_token(
            self.OAUTH_REFRESH_TYPE,
            build_payload=lambda secret, prefix: {
                'user_id': str(user_id) if user_id is not None else None,
                'account_id': account_id,
                'client_id': client_id,
                'scope': scope,
                'resource': resource
            },
            expire_days=self.OAUTH_REFRESH_TTL_DAYS
        )
        return {
            'refresh_token': created['secret'],
            'token_hash': created['token_hash'],
            'expires_at': created['expires_at']
        }

    def redeem_oauth_refresh_token(self, refresh_secret: str, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Riscatta un refresh token per la rotazione: valida, verifica il
        client_id, lo marca USED (monouso). Il chiamante usa il payload
        restituito per creare la nuova coppia access+refresh.
        """
        token = self._validate_hashed_secret_token(refresh_secret, self.OAUTH_REFRESH_TYPE)
        if not token:
            return None

        try:
            payload = json.loads(token.payload)
        except (json.JSONDecodeError, TypeError):
            return None

        if payload.get('client_id') != client_id:
            return None

        self.mark_as_used(token.uuid)
        return payload

    def get_oauth_connections_for_user(self, user_id: Any) -> List[Dict[str, Any]]:
        """
        Connessioni OAuth attive dell'utente: un elemento per client_id con
        almeno un OAUTH_ACCESS/OAUTH_REFRESH non scaduto e non revocato. Ritorna
        solo `client_id` (la UI lo risolve in un nome leggibile tramite il
        registro client di `oauth_server.OAUTH_CLIENTS`).
        """
        tokens = self.db.query(Token).filter(
            Token.type.in_((self.OAUTH_ACCESS_TYPE, self.OAUTH_REFRESH_TYPE)),
            Token.status == 'PENDING',
            Token.expire_date > datetime.utcnow()
        ).order_by(Token.create_date.desc()).all()

        by_client: Dict[str, Dict[str, Any]] = {}
        for token in tokens:
            try:
                payload = json.loads(token.payload)
            except (json.JSONDecodeError, TypeError):
                continue

            if str(payload.get('user_id')) != str(user_id):
                continue

            client_id = payload.get('client_id')
            if not client_id:
                continue

            entry = by_client.setdefault(client_id, {
                'client_id': client_id,
                'scope': payload.get('scope'),
                'connected_since': token.create_date,
                'expires_at': token.expire_date
            })
            entry['connected_since'] = min(entry['connected_since'], token.create_date)
            entry['expires_at'] = max(entry['expires_at'], token.expire_date)

        return [
            {
                'client_id': entry['client_id'],
                'scope': entry['scope'],
                'connected_since': entry['connected_since'].strftime('%d/%m/%Y %H:%M'),
                'expires_at': entry['expires_at'].strftime('%d/%m/%Y %H:%M')
            }
            for entry in sorted(by_client.values(), key=lambda e: e['client_id'])
        ]

    def revoke_oauth_connection(self, user_id: Any, client_id: str) -> int:
        """
        Revoca (status -> EXPIRED, come `mark_as_expired`) tutti gli OAUTH_ACCESS/
        OAUTH_REFRESH di user_id per client_id. Non tocca i token MCP personali
        (type diverso, stessa tabella Token): le due revoche sono indipendenti.

        Returns:
            Numero di token revocati.
        """
        tokens = self.db.query(Token).filter(
            Token.type.in_((self.OAUTH_ACCESS_TYPE, self.OAUTH_REFRESH_TYPE)),
            Token.status == 'PENDING'
        ).all()

        revoked = 0
        for token in tokens:
            try:
                payload = json.loads(token.payload)
            except (json.JSONDecodeError, TypeError):
                continue

            if payload.get('client_id') != client_id:
                continue
            if str(payload.get('user_id')) != str(user_id):
                continue

            token.status = 'EXPIRED'
            revoked += 1

        if revoked:
            self.db.commit()

        return revoked


class StatsRepository:
    """Repository per statistiche e analisi dati"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_available_years(self, account_id: int) -> List[int]:
        """
        Recupera la lista degli anni disponibili nei movimenti
        
        Args:
            account_id: ID dell'account
        
        Returns:
            Lista di anni ordinati
        """
        from sqlalchemy import func, distinct
        
        years = self.db.query(distinct(Movement.move_year))\
            .filter(Movement.account_id == account_id)\
            .order_by(Movement.move_year.desc())\
            .all()
        
        return [year[0] for year in years if year[0] is not None]
    
    def get_monthly_stats(self, account_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Recupera le statistiche mensili aggregate
        
        Args:
            account_id: ID dell'account
            year: Anno
            month: Mese (1-12)
        
        Returns:
            Dizionario con le statistiche mensili
        """
        from sqlalchemy import func, case
        
        # Query base per il mese specifico
        base_query = self.db.query(Movement)\
            .filter(Movement.account_id == account_id)\
            .filter(Movement.move_year == year)\
            .filter(Movement.move_month == month)
        
        # Totale entrate vs uscite
        income_total = base_query.with_entities(func.sum(Movement.income)).scalar() or 0
        expense_total = base_query.with_entities(func.sum(Movement.expense)).scalar() or 0
        
        # Spese per wallet - usa il nome del wallet dalla tabella Wallet
        expense_by_wallet_query = self.db.query(
            func.coalesce(Wallet.name, Movement.wallet).label('wallet_name'),
            func.sum(Movement.expense).label('total')
        ).outerjoin(Wallet, Movement.wallet_id == Wallet.id)\
         .filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.move_month == month)\
         .filter(Movement.expense > 0)\
         .group_by(func.coalesce(Wallet.name, Movement.wallet))\
         .all()
        
        expense_by_wallet = {row.wallet_name: float(row.total) for row in expense_by_wallet_query}
        
        # Entrate per wallet - usa il nome del wallet dalla tabella Wallet
        income_by_wallet_query = self.db.query(
            func.coalesce(Wallet.name, Movement.wallet).label('wallet_name'),
            func.sum(Movement.income).label('total')
        ).outerjoin(Wallet, Movement.wallet_id == Wallet.id)\
         .filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.move_month == month)\
         .filter(Movement.income > 0)\
         .group_by(func.coalesce(Wallet.name, Movement.wallet))\
         .all()
        
        income_by_wallet = {row.wallet_name: float(row.total) for row in income_by_wallet_query}
        
        # Spese per categoria
        expense_by_category_query = self.db.query(
            Movement.category,
            func.sum(Movement.expense).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.move_month == month)\
         .filter(Movement.expense > 0)\
         .group_by(Movement.category)\
         .all()
        
        expense_by_category = {row.category: float(row.total) for row in expense_by_category_query}
        
        return {
            'income_vs_expense': {
                'income': float(income_total),
                'expense': float(expense_total)
            },
            'expense_by_wallet': expense_by_wallet,
            'income_by_wallet': income_by_wallet,
            'expense_by_category': expense_by_category
        }
    
    def get_yearly_stats(self, account_id: int, year: int) -> Dict[str, Any]:
        """
        Recupera le statistiche annuali aggregate
        
        Args:
            account_id: ID dell'account
            year: Anno
        
        Returns:
            Dizionario con le statistiche annuali
        """
        from sqlalchemy import func, case
        
        # Query base per l'anno specifico
        base_query = self.db.query(Movement)\
            .filter(Movement.account_id == account_id)\
            .filter(Movement.move_year == year)
        
        # Totale entrate vs uscite
        income_total = base_query.with_entities(func.sum(Movement.income)).scalar() or 0
        expense_total = base_query.with_entities(func.sum(Movement.expense)).scalar() or 0
        
        # Spese per wallet - usa il nome del wallet dalla tabella Wallet
        expense_by_wallet_query = self.db.query(
            func.coalesce(Wallet.name, Movement.wallet).label('wallet_name'),
            func.sum(Movement.expense).label('total')
        ).outerjoin(Wallet, Movement.wallet_id == Wallet.id)\
         .filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.expense > 0)\
         .group_by(func.coalesce(Wallet.name, Movement.wallet))\
         .all()
        
        expense_by_wallet = {row.wallet_name: float(row.total) for row in expense_by_wallet_query}
        
        # Entrate per wallet - usa il nome del wallet dalla tabella Wallet
        income_by_wallet_query = self.db.query(
            func.coalesce(Wallet.name, Movement.wallet).label('wallet_name'),
            func.sum(Movement.income).label('total')
        ).outerjoin(Wallet, Movement.wallet_id == Wallet.id)\
         .filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.income > 0)\
         .group_by(func.coalesce(Wallet.name, Movement.wallet))\
         .all()
        
        income_by_wallet = {row.wallet_name: float(row.total) for row in income_by_wallet_query}
        
        # Spese per categoria
        expense_by_category_query = self.db.query(
            Movement.category,
            func.sum(Movement.expense).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.expense > 0)\
         .group_by(Movement.category)\
         .all()
        
        expense_by_category = {row.category: float(row.total) for row in expense_by_category_query}
        
        return {
            'income_vs_expense': {
                'income': float(income_total),
                'expense': float(expense_total)
            },
            'expense_by_wallet': expense_by_wallet,
            'income_by_wallet': income_by_wallet,
            'expense_by_category': expense_by_category
        }
    
    def get_category_monthly_trend(self, account_id: int, year: int, category_name: str) -> Dict[str, Any]:
        """
        Recupera l'andamento mensile di una categoria specifica
        
        Args:
            account_id: ID dell'account
            year: Anno
            category_name: Nome della categoria
        
        Returns:
            Dizionario con labels e data per il grafico
        """
        from sqlalchemy import func
        
        # Query per ottenere le spese mensili per categoria
        monthly_data = []
        labels = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 
                  'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        
        for month in range(1, 13):
            total = self.db.query(func.sum(Movement.expense))\
                .filter(Movement.account_id == account_id)\
                .filter(Movement.move_year == year)\
                .filter(Movement.move_month == month)\
                .filter(Movement.category == category_name)\
                .scalar() or 0
            
            monthly_data.append(float(total))
        
        return {
            'category_name': category_name,
            'year': year,
            'labels': labels,
            'data': monthly_data
        }


class AdminRepository:
    """Repository per operazioni amministrative"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Recupera tutti gli utenti del sistema"""
        users = self.db.query(User).all()
        return [{
            'id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'account_id': u.account_id,
            'created_at': u.created_at.isoformat() if u.created_at else None
        } for u in users]
    
    def delete_user(self, user_id: int) -> bool:
        """Elimina un utente (delega al UserRepository)"""
        user_repo = UserRepository(self.db)
        return user_repo.delete_user(user_id)
    
    def get_all_whitelist(self) -> List[Dict[str, Any]]:
        """Recupera tutte le email in whitelist"""
        entries = self.db.query(EmailWhitelist).all()
        return [{
            'id': e.id,
            'email': e.email,
            'added_at': e.added_at.isoformat() if e.added_at else None,
            'note': e.note
        } for e in entries]
    
    def add_to_whitelist(self, email: str, note: str = None) -> bool:
        """Aggiunge un'email alla whitelist"""
        try:
            # Verifica se esiste già
            existing = self.db.query(EmailWhitelist).filter_by(email=email).first()
            if existing:
                return False
            
            new_entry = EmailWhitelist(
                email=email,
                added_at=datetime.utcnow(),
                note=note
            )
            self.db.add(new_entry)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False
    
    def remove_from_whitelist(self, email: str) -> bool:
        """Rimuove un'email dalla whitelist"""
        try:
            entry = self.db.query(EmailWhitelist).filter_by(email=email).first()
            if not entry:
                return False
            
            self.db.delete(entry)
            self.db.commit()
            return True
        except SQLAlchemyError:
            self.db.rollback()
            return False


class RecurrentMovementRepository:
    """Repository per la gestione delle spese ricorrenti"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_for_account(self, account_id: int) -> List[RecurrentMovement]:
        """Restituisce tutte le spese ricorrenti dell'account con la data dell'ultimo movimento associato."""
        subq = (
            self.db.query(
                Movement.recurrent_movement_id,
                func.max(Movement.move_date).label('last_move_date')
            )
            .filter(Movement.account_id == account_id)
            .group_by(Movement.recurrent_movement_id)
            .subquery()
        )

        rows = (
            self.db.query(RecurrentMovement, subq.c.last_move_date)
            .outerjoin(subq, RecurrentMovement.id == subq.c.recurrent_movement_id)
            .filter(RecurrentMovement.account_id == account_id)
            .order_by(RecurrentMovement.name)
            .all()
        )

        for rm, last_date in rows:
            rm.last_move_date = last_date

        return [rm for rm, _ in rows]

    def get_by_id(self, rm_id: int, account_id: int) -> Optional[RecurrentMovement]:
        """Restituisce una spesa ricorrente per id, verificando l'appartenenza all'account"""
        return (
            self.db.query(RecurrentMovement)
            .filter(
                RecurrentMovement.id == rm_id,
                RecurrentMovement.account_id == account_id
            )
            .first()
        )

    def create(self, account_id: int, name: str, category_id: int, wallet_id: int,
               movement_type: str, amount: float, note: Optional[str] = None) -> RecurrentMovement:
        """Crea una nuova spesa ricorrente"""
        rm = RecurrentMovement(
            name=name,
            category_id=category_id,
            wallet_id=wallet_id,
            income=amount if movement_type == 'income' else None,
            expense=amount if movement_type == 'expense' else None,
            note=note,
            account_id=account_id,
        )
        self.db.add(rm)
        self.db.commit()
        self.db.refresh(rm)
        return rm

    def update(self, rm_id: int, account_id: int, data: Dict[str, Any]) -> Optional[RecurrentMovement]:
        """Aggiorna una spesa ricorrente esistente"""
        rm = self.get_by_id(rm_id, account_id)
        if not rm:
            return None

        if 'name' in data:
            rm.name = data['name']
        if 'category_id' in data:
            rm.category_id = data['category_id']
        if 'wallet_id' in data:
            rm.wallet_id = data['wallet_id']
        if 'note' in data:
            rm.note = data.get('note')

        movement_type = data.get('movement_type')
        amount = data.get('amount')
        if movement_type is not None and amount is not None:
            rm.income = float(amount) if movement_type == 'income' else None
            rm.expense = float(amount) if movement_type == 'expense' else None

        self.db.commit()
        self.db.refresh(rm)
        return rm

    def delete(self, rm_id: int, account_id: int) -> bool:
        """Elimina una spesa ricorrente"""
        rm = self.get_by_id(rm_id, account_id)
        if not rm:
            return False
        self.db.delete(rm)
        self.db.commit()
        return True


class ReportRepository:
    """Repository per la generazione dei dati del report annuale"""

    def __init__(self, db: Session):
        self.db = db

    def get_annual_report_data(self, account_id: int, year: int) -> Dict[str, Any]:
        """
        Raccoglie tutti i dati necessari per il report annuale PDF.

        Returns:
            Dizionario strutturato con tutte le sezioni del report.
        """
        from sqlalchemy import text

        def q(sql, params):
            return self.db.execute(text(sql), params).fetchall()

        # Q1 – Sommario anno
        row = q("""
            SELECT
                COALESCE(SUM(income), 0)  AS tot_income,
                COALESCE(SUM(expense), 0) AS tot_expense,
                COUNT(*)                   AS n_movimenti
            FROM Movement
            WHERE account_id = :account_id AND move_year = :year
        """, {"account_id": account_id, "year": year})[0]
        tot_income = float(row.tot_income)
        tot_expense = float(row.tot_expense)
        summary = {
            "year": year,
            "tot_income": tot_income,
            "tot_expense": tot_expense,
            "saldo": round(tot_income - tot_expense, 2),
            "n_movimenti": int(row.n_movimenti),
        }

        # Q2 – Serie storica anni
        rows = q("""
            SELECT
                move_year,
                ROUND(COALESCE(SUM(income), 0),  2) AS tot_income,
                ROUND(COALESCE(SUM(expense), 0), 2) AS tot_expense,
                COUNT(*) AS n_movimenti
            FROM Movement
            WHERE account_id = :account_id
            GROUP BY move_year
            ORDER BY move_year
        """, {"account_id": account_id})
        yearly_history = []
        for i, r in enumerate(rows):
            prev_exp = float(rows[i - 1].tot_expense) if i > 0 else None
            cur_exp = float(r.tot_expense)
            delta_pct = None
            if prev_exp and prev_exp > 0:
                delta_pct = round((cur_exp - prev_exp) / prev_exp * 100, 1)
            yearly_history.append({
                "year": r.move_year,
                "tot_income": float(r.tot_income),
                "tot_expense": cur_exp,
                "saldo": round(float(r.tot_income) - cur_exp, 2),
                "n_movimenti": int(r.n_movimenti),
                "delta_expense_pct": delta_pct,
            })

        # Q3 – Trend mensile anno selezionato
        rows = q("""
            SELECT
                move_month,
                ROUND(COALESCE(SUM(income), 0),  2) AS tot_income,
                ROUND(COALESCE(SUM(expense), 0), 2) AS tot_expense
            FROM Movement
            WHERE account_id = :account_id AND move_year = :year
            GROUP BY move_month
            ORDER BY move_month
        """, {"account_id": account_id, "year": year})
        month_data = {r.move_month: (float(r.tot_income), float(r.tot_expense)) for r in rows}
        monthly_trend = [
            {"month": m, "income": month_data.get(m, (0, 0))[0], "expense": month_data.get(m, (0, 0))[1]}
            for m in range(1, 13)
        ]

        # Q4 – Top 10 spese singole
        rows = q("""
            SELECT
                m.move_date,
                m.category,
                COALESCE(w.name, m.wallet) AS wallet_name,
                m.note,
                m.expense
            FROM Movement m
            LEFT JOIN Wallet w ON m.wallet_id = w.id
            WHERE m.account_id = :account_id AND m.move_year = :year
              AND m.expense IS NOT NULL
            ORDER BY m.expense DESC
            LIMIT 10
        """, {"account_id": account_id, "year": year})
        top_expenses = [
            {
                "date": str(r.move_date),
                "category": r.category,
                "wallet": r.wallet_name,
                "note": r.note or "",
                "amount": float(r.expense),
            }
            for r in rows
        ]

        # Q5 – Spese per categoria anno corrente
        rows_cur = q("""
            SELECT
                category,
                ROUND(SUM(expense), 2) AS tot_expense,
                COUNT(*)               AS n_movimenti
            FROM Movement
            WHERE account_id = :account_id AND move_year = :year
              AND expense IS NOT NULL
            GROUP BY category
            ORDER BY tot_expense DESC
        """, {"account_id": account_id, "year": year})

        # Q5b – Spese per categoria anno precedente (per confronto)
        rows_prev = q("""
            SELECT category, ROUND(SUM(expense), 2) AS tot_expense
            FROM Movement
            WHERE account_id = :account_id AND move_year = :prev_year
              AND expense IS NOT NULL
            GROUP BY category
        """, {"account_id": account_id, "prev_year": year - 1})
        prev_by_cat = {r.category: float(r.tot_expense) for r in rows_prev}

        expense_by_category = []
        for r in rows_cur:
            cur = float(r.tot_expense)
            prev = prev_by_cat.get(r.category, 0.0)
            pct_budget = round(cur / tot_expense * 100, 1) if tot_expense else 0
            delta = round(((cur - prev) / prev * 100), 1) if prev else None
            expense_by_category.append({
                "category": r.category,
                "tot_expense": cur,
                "n_movimenti": int(r.n_movimenti),
                "pct_budget": pct_budget,
                "prev_year_expense": prev,
                "delta_pct": delta,
            })

        # Q6 – Spese per wallet
        rows = q("""
            SELECT
                COALESCE(w.name, m.wallet) AS wallet_name,
                ROUND(SUM(m.expense), 2)   AS tot_expense,
                COUNT(*)                    AS n_movimenti
            FROM Movement m
            LEFT JOIN Wallet w ON m.wallet_id = w.id
            WHERE m.account_id = :account_id AND m.move_year = :year
              AND m.expense IS NOT NULL
            GROUP BY COALESCE(w.name, m.wallet)
            ORDER BY tot_expense DESC
        """, {"account_id": account_id, "year": year})
        expense_by_wallet = [
            {
                "wallet": r.wallet_name,
                "tot_expense": float(r.tot_expense),
                "pct": round(float(r.tot_expense) / tot_expense * 100, 1) if tot_expense else 0,
                "n_movimenti": int(r.n_movimenti),
            }
            for r in rows
        ]

        # Q7 – Mesi anomali (uscite > media mensile + 20%)
        rows = q("""
            WITH monthly AS (
                SELECT move_month, ROUND(SUM(expense), 2) AS tot
                FROM Movement
                WHERE account_id = :account_id AND move_year = :year AND expense IS NOT NULL
                GROUP BY move_month
            ),
            avg_month AS (SELECT AVG(tot) AS media FROM monthly)
            SELECT m.move_month, m.tot, ROUND(m.tot - a.media, 2) AS delta, a.media
            FROM monthly m, avg_month a
            WHERE m.tot > a.media * 1.2
            ORDER BY m.tot DESC
        """, {"account_id": account_id, "year": year})
        month_names = ["", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                       "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        anomalous_months = [
            {
                "month_num": r.move_month,
                "month_name": month_names[r.move_month],
                "tot_expense": float(r.tot),
                "delta": float(r.delta),
                "media": round(float(r.media), 2),
            }
            for r in rows
        ]

        # Top 5 categorie per incidenza (≥5% budget)
        top5_categories = [c for c in expense_by_category if c["pct_budget"] >= 5][:5]

        return {
            "summary": summary,
            "yearly_history": yearly_history,
            "monthly_trend": monthly_trend,
            "top_expenses": top_expenses,
            "expense_by_category": expense_by_category,
            "top5_categories": top5_categories,
            "expense_by_wallet": expense_by_wallet,
            "anomalous_months": anomalous_months,
        }
