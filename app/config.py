import os
import sqlalchemy
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') 
        or 'mysql+pymysql://root:root@localhost/hospital_complaints?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 280}
    
    # Use absolute path for uploads to prevent path resolution errors
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))

    # --- Session security ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    SESSION_REFRESH_EACH_REQUEST = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_DURATION = timedelta(days=1)
    WTF_CSRF_TIME_LIMIT = 8 * 3600

    # --- Login throttling ---
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    LOGIN_ATTEMPT_WINDOW_MINUTES = 30

    # --- Security headers ---
    ENABLE_SECURITY_HEADERS = True
    ENABLE_HSTS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    ENABLE_HSTS = True

    @classmethod
    def validate(cls):
        if not os.environ.get('SECRET_KEY') or cls.SECRET_KEY == 'dev-secret-key-change-me':
            raise RuntimeError('SECRET_KEY must be set to a strong value in production.')
        if not os.environ.get('DATABASE_URL'):
            raise RuntimeError('DATABASE_URL must be set in production.')


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    # Use 'sqlite://' with StaticPool to ensure the in-memory database 
    # is shared across all threads/connections during pytest execution.
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": sqlalchemy.pool.StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    ENABLE_HSTS = False
    MAX_FAILED_LOGIN_ATTEMPTS = 5


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}