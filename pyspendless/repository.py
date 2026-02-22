"""
Repository per PySpendless
Funzioni CRUD e logica di accesso ai dati
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any

from models import (
    Account, User, Wallet, Category, CategoryTemplate, 
    EmailWhitelist, Movement, UserGroup, GroupMembership
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
    
    def create_user_from_oauth(self, user_info: Dict[str, Any]) -> User:
        """
        Crea un nuovo utente e account dopo autenticazione OAuth Google.
        Se l'utente esiste già, lo ritorna.
        
        Args:
            user_info: Dizionario con i dati dell'utente da Google OAuth
                       Deve contenere: 'sub' (google_id), 'email', 'name'
        
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
            # 3. Create Account
            new_account = Account(
                name=f"Account di {name}",
                created_at=datetime.utcnow()
            )
            self.db.add(new_account)
            self.db.flush()  # Per ottenere l'ID dell'account
            
            # 4. Create User
            new_user = User(
                public_uid=str(uuid.uuid4()),
                google_id=google_id,
                email=email,
                name=name,
                account_id=new_account.id,
                role='owner',
                created_at=datetime.utcnow()
            )
            self.db.add(new_user)
            
            # 5. Copy Categories from Templates
            self._create_default_categories(new_account.id)
            
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
