import os
from datetime import datetime

from cryptography.fernet import Fernet
from flask_login import UserMixin
from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

_fernet = Fernet(os.environ["ENCRYPTION_KEY"].encode())


def encrypt_text(plain: str) -> str:
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_text(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()


def encrypt_optional(plain: str | None) -> str | None:
    if plain is None:
        return None
    return encrypt_text(plain)


def decrypt_optional(token: str | None) -> str | None:
    if token is None:
        return None
    return decrypt_text(token)


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # null if Google-only
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __init__(self, email: str, google_id: str | None = None):
        super().__init__()
        self.email = email
        self.google_id = google_id

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class QueryHistory(db.Model):
    """
    One row per question asked - the "message table" for this app, same
    idea as flask-chatgpt-app's chat_message table. Both the request (the
    question) and the response (the generated SQL) are stored encrypted;
    only status/note/created_at are plain, since they carry no user content.
    """
    __tablename__ = "query_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    _nl_question: Mapped[str] = mapped_column("nl_question", Text, nullable=False)
    _generated_sql: Mapped[str | None] = mapped_column("generated_sql", Text, nullable=True)

    # "generated" (safe SQL was produced) | "blocked" (guardrails refused it)
    # | "error" (the AI call itself failed, e.g. all providers down)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __init__(self, user_id: int, nl_question: str, generated_sql: str | None = None):
        super().__init__()
        self.user_id = user_id
        self.nl_question = nl_question       # goes through the setter below -> encrypted
        self.generated_sql = generated_sql   # goes through the setter below -> encrypted

    @property
    def nl_question(self) -> str:
        # return decrypt_text(self._nl_question)     # <-- commented out
        return self._nl_question                     # <-- changed

    @nl_question.setter
    def nl_question(self, value: str) -> None:
        # self._nl_question = encrypt_text(value)    # <-- commented out
        self._nl_question = value                    # <-- changed

    @property
    def generated_sql(self) -> str | None:
        # return decrypt_optional(self._generated_sql)   # <-- commented out
        return self._generated_sql                       # <-- changed

    @generated_sql.setter
    def generated_sql(self, value: str | None) -> None:
        # self._generated_sql = encrypt_optional(value)  # <-- commented out
        self._generated_sql = value                      # <-- changed