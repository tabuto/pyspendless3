"""
SQLAlchemy Models per PySpendless
Definizione delle entità: Account, User, Wallet, Category, CategoryTemplate, 
EmailWhitelist, Movement, UserGroup, GroupMembership
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Numeric, Date, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Account(Base):
    """Rappresenta un account che può avere più utenti e wallet"""
    __tablename__ = 'Account'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    users = relationship('User', back_populates='account')
    wallets = relationship('Wallet', back_populates='account')
    categories = relationship('Category', back_populates='account')
    groups = relationship('UserGroup', back_populates='account')


class User(Base):
    """Rappresenta un utente registrato tramite Google OAuth"""
    __tablename__ = 'User'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    public_uid = Column(Text, unique=True, nullable=False)
    google_id = Column(Text, unique=True, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    role = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    account = relationship('Account', back_populates='users')
    movements = relationship('Movement', back_populates='user_obj', foreign_keys='Movement.user_id')


class Wallet(Base):
    """Rappresenta un wallet (portafoglio) per tracciare le spese"""
    __tablename__ = 'Wallet'
    
    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    currency = Column(Text, nullable=False, default='EUR')
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    account = relationship('Account', back_populates='wallets')
    movements = relationship('Movement', back_populates='wallet_obj', foreign_keys='Movement.wallet_id')


class CategoryTemplate(Base):
    """Template di categorie di default da copiare per ogni nuovo account"""
    __tablename__ = 'CategoryTemplate'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    config = Column(Text, nullable=True)
    
    __table_args__ = (
        CheckConstraint("type IN ('expense','income','transfer')", name='check_type'),
    )
    
    # Relationships
    categories = relationship('Category', back_populates='template')


class Category(Base):
    """Categoria di spesa/entrata specifica per ogni account"""
    __tablename__ = 'Category'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    type = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey('CategoryTemplate.id'), nullable=True)
    
    __table_args__ = (
        CheckConstraint("type IN ('expense','income','transfer')", name='check_category_type'),
    )
    
    # Relationships
    account = relationship('Account', back_populates='categories')
    template = relationship('CategoryTemplate', back_populates='categories')
    movements = relationship('Movement', back_populates='category_obj', foreign_keys='Movement.category_id')


class EmailWhitelist(Base):
    """Whitelist delle email autorizzate alla registrazione"""
    __tablename__ = 'emailWhitelist'
    
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    added_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    note = Column(Text, nullable=True)


class Movement(Base):
    """
    Movimento (spesa/entrata) - Retrocompatibile con schema esistente
    Include sia i campi legacy (stringhe) che i nuovi FK (nullable per compatibilità)
    """
    __tablename__ = 'Movement'
    
    id = Column(Text, primary_key=True)
    move_date = Column(Date, nullable=False)
    move_year = Column(Integer, nullable=False)
    move_month = Column(Integer, nullable=False)
    category = Column(Text, nullable=False)  # Legacy: category name/id as string
    wallet = Column(Text, nullable=False)    # Legacy: wallet code/id as string
    income = Column(Numeric(10, 2), nullable=True)
    expense = Column(Numeric(10, 2), nullable=True)
    note = Column(Text, nullable=True)
    user = Column(Text, nullable=False)       # Legacy: user email/id as string
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    
    # Nuovi campi FK per integrità referenziale (nullable per retrocompatibilità)
    user_id = Column(Text, ForeignKey('User.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('Category.id'), nullable=True)
    wallet_id = Column(Integer, ForeignKey('Wallet.id'), nullable=True)
    
    # Relationships
    user_obj = relationship('User', back_populates='movements', foreign_keys=[user_id])
    category_obj = relationship('Category', back_populates='movements', foreign_keys=[category_id])
    wallet_obj = relationship('Wallet', back_populates='movements', foreign_keys=[wallet_id])


class UserGroup(Base):
    """Gruppo di utenti per condivisione account"""
    __tablename__ = 'USER_GROUP'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    account_id = Column(Integer, ForeignKey('Account.id'), nullable=False)
    owner_user_id = Column(Text, ForeignKey('User.id'), nullable=False)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    
    # Relationships
    account = relationship('Account', back_populates='groups')
    owner = relationship('User', foreign_keys=[owner_user_id])
    memberships = relationship('GroupMembership', back_populates='group')


class GroupMembership(Base):
    """Appartenenza di un utente a un gruppo (o invito)"""
    __tablename__ = 'GroupMembership'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('USER_GROUP.id'), nullable=False)
    user_id = Column(Text, ForeignKey('User.id'), nullable=True)  # Null se invito in pending
    invite_email = Column(Text, nullable=False)
    invited_by_user_id = Column(Text, ForeignKey('User.id'), nullable=False)
    status = Column(Text, nullable=False, default='pending')  # pending, accepted, declined
    token = Column(Text, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("status IN ('pending','accepted','declined')", name='check_membership_status'),
    )
    
    # Relationships
    group = relationship('UserGroup', back_populates='memberships')
    user = relationship('User', foreign_keys=[user_id])
    invited_by = relationship('User', foreign_keys=[invited_by_user_id])
