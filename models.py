import uuid
import datetime
from sqlalchemy import Column, String, Text, Boolean, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Issue(Base):
    __tablename__ = "issues"

    issue_id = Column(String(36), primary_key=True, default=generate_uuid)
    repo_url = Column(Text, nullable=False)
    issue_title = Column(Text, nullable=False)
    issue_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    states = relationship("FSMStateLedger", back_populates="issue", cascade="all, delete-orphan", order_by="FSMStateLedger.updated_at")
    patches = relationship("Patch", back_populates="issue", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="issue", cascade="all, delete-orphan")


class FSMStateLedger(Base):
    __tablename__ = "fsm_states"

    state_id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False, index=True)
    state_name = Column(String(50), nullable=False)
    retry_count = Column(Integer, default=0)
    payload = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    issue = relationship("Issue", back_populates="states")


class Patch(Base):
    __tablename__ = "patches"

    patch_id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False, index=True)
    patch_diff = Column(Text, nullable=False)
    is_compiled = Column(Boolean, default=False)
    passes_lint = Column(Boolean, default=False)
    passes_tests = Column(Boolean, default=False)
    mutation_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    issue = relationship("Issue", back_populates="patches")
    reviews = relationship("HumanReview", back_populates="patch")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    review_id = Column(String(36), primary_key=True, default=generate_uuid)
    issue_id = Column(String(36), ForeignKey("issues.issue_id", ondelete="CASCADE"), nullable=False, index=True)
    patch_id = Column(String(36), ForeignKey("patches.patch_id", ondelete="CASCADE"), nullable=True)
    reviewer_name = Column(String(100), nullable=True)
    decision = Column(String(20), nullable=False)  # APPROVED / REJECTED
    comments = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.datetime.utcnow)

    issue = relationship("Issue", back_populates="reviews")
    patch = relationship("Patch", back_populates="reviews")
