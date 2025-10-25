# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import enum

Base = declarative_base()

class RoleEnum(enum.Enum):
    admin = "admin"
    organization = "organization"
    voter = "voter"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)
    description = Column(Text)
    candidates = relationship("Candidate", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # hashed
    role = Column(Enum(RoleEnum), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    public_key = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    description = Column(Text, nullable=True)
    organization = relationship("Organization", back_populates="candidates")

class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    voting_active = Column(Boolean, default=False, nullable=False)
    results_declared = Column(Boolean, default=False, nullable=False)

class ResultRecord(Base):
    __tablename__ = "result_records"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    results_data = Column(JSON)  # stores {candidate_name: votes}
    total_votes = Column(Integer)
    winner = Column(String)
