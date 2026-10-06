from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login" # type: ignore[assignment]
limiter = Limiter(key_func=get_remote_address)
oauth = OAuth()