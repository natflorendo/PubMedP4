from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

"""
models.py

Pydantic request/response schemas for PubMedFlo user auth.
Defines both user input (signup, login, and partial updates) and output (returned to client) models.
Also includes some JWT token models.
"""


# A base user model that another model inherits from.
class UserBase(BaseModel):
    # ... = no default. User must provide.
    name: str = Field(..., max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    # Default role is end_user and lambda: ["end_user"] ensures a new list is created each time an instance is made
    # (not one shared list).
    # default_factory means when this field has no value provided, call this function to create a fresh default value.
    roles: List[str] = Field(default_factory=lambda: ["end_user"])


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# All fields are optional so you can PATCH just part of a user.
class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8)
    roles: Optional[List[str]] = None


# Used when returning user to the client.
class UserOut(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    roles: List[str]
    created_at: datetime


# JWT token.
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Internal helper to read/validate a token.
class TokenPayload(BaseModel):
    # Usually user's ID or email.
    sub: str
    # Expiration time as a Unix timestamp (seconds since epoch).
    exp: Optional[int] = None
    # Roles encoded into the token for authorization checks (e.g., ["admin"]).
    roles: Optional[List[str]] = None


# After login/signup. Combines token with user to give to the frontend.
class AuthResponse(Token):
    user: UserOut


class QueryRequest(BaseModel):
    # Field(...) = no default. User must provide.
    # Must be a non-empty string
    query: str = Field(..., min_length=1) 
    # Optional Field with a default of 5.
    # `ge` = greater than or equal to; `le` = less than or equal to.
    k: int = Field(5, ge=1, le=20)
    # If true, the backend will call the LLM and generate a natural language 
    # answer based on the retrieved chunks. Otherwise, the API will only return the
    # retrieved chunks and citations.
    include_answer: bool = True
    # Allows client to used a different model instead of the default.
    answer_model: Optional[str] = None


# Article level citation in the response.
class Citation(BaseModel):
    # Pubmed ID for the article.
    pmid: int
    # Title of the article.
    title: str
    # Internal database ID from the `documents` table.
    doc_id: Optional[int] 


# Retrieved text chunk from the similarity search.
class ChunkResult(BaseModel):
    # Internal ID from the `text_chunks` table
    chunk_id: int
    # PubMed ID of the article the chunk came from
    pmid: int
    # Internal database ID from the `documents` table.
    doc_id: Optional[int]
    # Title of the article.
    title: str
    # Retrieval score from FAISS
    score: float
    # Actual text of a chunk.
    chunk_text: str


class QueryResponse(BaseModel):
    # Internal ID from the `query_logs` table.
    query_id: Optional[int]
    # The LLM-generated natural language answer.
    answer: Optional[str]
    # List of unique article-level citations used to support the answer [PMID XXXXXXXX].
    citations: List[Citation]
    # The chunks that were retrieved by FAISS and passed to the LLM.
    retrieved_chunks: List[ChunkResult]
