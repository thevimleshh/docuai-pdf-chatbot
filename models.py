
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


# ==========================================
# USER MODEL
# ==========================================

class User(Base):

    __tablename__ = "users"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    name = Column(
        String(100),
        nullable=False
    )


    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )


    password = Column(
        String(255),
        nullable=False
    )


    # User ke documents
    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# ==========================================
# DOCUMENT MODEL
# ==========================================

class Document(Base):

    __tablename__ = "documents"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )


    document_name = Column(
        String(255),
        nullable=False
    )


    file_path = Column(
        String(500),
        nullable=False
    )


    document_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )


    # Document ka user
    user = relationship(
        "User",
        back_populates="documents"
    )

