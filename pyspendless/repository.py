"""
Repository per PySpendless
Funzioni CRUD e logica di accesso ai dati
"""

import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any

from models import (
    Account, User, Wallet, Category, CategoryTemplate, 
    EmailWhitelist, Movement, UserGroup, GroupMembership, Token
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
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Recupera un utente tramite ID"""
        return self.db.query(User).filter_by(id=user_id).first()
    
    def get_users_by_account(self, account_id: int) -> List[User]:
        """Recupera tutti gli utenti associati a un account"""
        return self.db.query(User).filter_by(account_id=account_id).all()
    
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
    
    def get_wallets_for_account(self, account_id: int) -> List[Wallet]:
        """Recupera tutti i wallet di un account"""
        return self.db.query(Wallet).filter_by(account_id=account_id).all()
    
    def get_wallet(self, wallet_id: int) -> Optional[Wallet]:
        """Recupera un wallet tramite ID"""
        return self.db.query(Wallet).filter_by(id=wallet_id).first()
    
    def create_wallet(self, code: str, name: str, account_id: int, currency: str = 'EUR') -> Wallet:
        """Crea un nuovo wallet"""
        wallet = Wallet(
            code=code,
            name=name,
            currency=currency,
            account_id=account_id,
            created_at=datetime.utcnow()
        )
        self.db.add(wallet)
        self.db.commit()
        return wallet
    
    def update_wallet(self, wallet_id: int, data: Dict[str, Any]) -> Optional[Wallet]:
        """Aggiorna un wallet"""
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            return None
        
        for key, value in data.items():
            if hasattr(wallet, key):
                setattr(wallet, key, value)
        
        self.db.commit()
        return wallet
    
    def delete_wallet(self, wallet_id: int) -> bool:
        """Elimina un wallet"""
        wallet = self.get_wallet(wallet_id)
        if not wallet:
            return False
        
        self.db.delete(wallet)
        self.db.commit()
        return True


class CategoryRepository:
    """Repository per gestione categorie"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_categories_for_account(self, account_id: int) -> List[Category]:
        """Recupera tutte le categorie di un account"""
        return self.db.query(Category).filter_by(account_id=account_id).all()
    
    def get_category(self, category_id: int) -> Optional[Category]:
        """Recupera una categoria tramite ID"""
        return self.db.query(Category).filter_by(id=category_id).first()
    
    def create_category(self, name: str, account_id: int, type: str, template_id: Optional[int] = None) -> Category:
        """Crea una nuova categoria"""
        category = Category(
            name=name,
            type=type,
            account_id=account_id,
            template_id=template_id
        )
        self.db.add(category)
        self.db.commit()
        return category
    
    def update_category(self, category_id: int, data: Dict[str, Any]) -> Optional[Category]:
        """Aggiorna una categoria"""
        category = self.get_category(category_id)
        if not category:
            return None
        
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        self.db.commit()
        return category
    
    def delete_category(self, category_id: int) -> bool:
        """Elimina una categoria"""
        category = self.get_category(category_id)
        if not category:
            return False
        
        self.db.delete(category)
        self.db.commit()
        return True


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
        category_id: Optional[int] = None,
        category_type: Optional[str] = None
    ) -> List[Movement]:
        """
        Recupera i movimenti di un account con filtri opzionali
        """
        query = self.db.query(Movement).filter_by(account_id=account_id)
        
        if wallet_id:
            query = query.filter_by(wallet_id=wallet_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if year:
            query = query.filter_by(move_year=year)
        if month:
            query = query.filter_by(move_month=month)
        if category_id:
            query = query.filter_by(category_id=category_id)
        
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
    
    def delete_movement(self, movement_id: str) -> bool:
        """Elimina un movimento"""
        movement = self.get_movement(movement_id)
        if not movement:
            return False
        
        self.db.delete(movement)
        self.db.commit()
        return True
    
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
        category_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcola statistiche aggregate sui movimenti
        Returns:
            Dict con: total_income, total_expense, balance, expenses_by_category
        """
        from sqlalchemy import func
        
        # Recupera i movimenti filtrati
        movements = self.get_movements_for_account(
            account_id=account_id,
            wallet_id=wallet_id,
            user_id=user_id,
            year=year,
            month=month,
            category_id=category_id,
            category_type=category_type
        )
        
        # Calcola totali
        total_income = sum(float(m.income) if m.income else 0 for m in movements)
        total_expense = sum(float(m.expense) if m.expense else 0 for m in movements)
        balance = total_income - total_expense
        
        # Raggruppa spese per categoria
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
        if category_id:
            query = query.filter(Movement.category_id == category_id)
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
        from sqlalchemy import func
        
        # Query base per il mese specifico
        base_query = self.db.query(Movement)\
            .filter(Movement.account_id == account_id)\
            .filter(Movement.move_year == year)\
            .filter(Movement.move_month == month)
        
        # Totale entrate vs uscite
        income_total = base_query.with_entities(func.sum(Movement.income)).scalar() or 0
        expense_total = base_query.with_entities(func.sum(Movement.expense)).scalar() or 0
        
        # Spese per wallet
        expense_by_wallet_query = self.db.query(
            Movement.wallet,
            func.sum(Movement.expense).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.move_month == month)\
         .filter(Movement.expense > 0)\
         .group_by(Movement.wallet)\
         .all()
        
        expense_by_wallet = {row.wallet: float(row.total) for row in expense_by_wallet_query}
        
        # Entrate per wallet
        income_by_wallet_query = self.db.query(
            Movement.wallet,
            func.sum(Movement.income).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.move_month == month)\
         .filter(Movement.income > 0)\
         .group_by(Movement.wallet)\
         .all()
        
        income_by_wallet = {row.wallet: float(row.total) for row in income_by_wallet_query}
        
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
        from sqlalchemy import func
        
        # Query base per l'anno specifico
        base_query = self.db.query(Movement)\
            .filter(Movement.account_id == account_id)\
            .filter(Movement.move_year == year)
        
        # Totale entrate vs uscite
        income_total = base_query.with_entities(func.sum(Movement.income)).scalar() or 0
        expense_total = base_query.with_entities(func.sum(Movement.expense)).scalar() or 0
        
        # Spese per wallet
        expense_by_wallet_query = self.db.query(
            Movement.wallet,
            func.sum(Movement.expense).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.expense > 0)\
         .group_by(Movement.wallet)\
         .all()
        
        expense_by_wallet = {row.wallet: float(row.total) for row in expense_by_wallet_query}
        
        # Entrate per wallet
        income_by_wallet_query = self.db.query(
            Movement.wallet,
            func.sum(Movement.income).label('total')
        ).filter(Movement.account_id == account_id)\
         .filter(Movement.move_year == year)\
         .filter(Movement.income > 0)\
         .group_by(Movement.wallet)\
         .all()
        
        income_by_wallet = {row.wallet: float(row.total) for row in income_by_wallet_query}
        
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
