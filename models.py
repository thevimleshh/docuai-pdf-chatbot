
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


# ==============================
# USER MODEL
# ==============================

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

    is_verified = Column(
        Boolean,
        default=False
    )

    verification_code = Column(
        String(6),
        nullable=True
    )

    # User ke documents
    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# ==============================
# DOCUMENT MODEL
# ==============================

class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # Document kis user ka hai
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Original PDF ka naam
    document_name = Column(
        String(255),
        nullable=False
    )

    # Server par PDF ka path
    file_path = Column(
        String(500),
        nullable=False
    )

    # ChromaDB ka unique document ID
    document_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    # User relationship
    user = relationship(
        "User",
        back_populates="documents"
    )

