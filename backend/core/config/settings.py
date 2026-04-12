from pydantic import BaseSettings, validator
from typing import Optional, List
import os

class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    url: str = "sqlite+aiosqlite:///./bybit_trader.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True

    class Config:
        env_prefix = "DATABASE_"

class APISettings(BaseSettings):
    """API configuration settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    workers: int = 1
    debug: bool = False

    @validator('port')
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v

    class Config:
        env_prefix = "API_"

class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Rate limiting
    rate_limit_requests_per_minute: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    class Config:
        env_prefix = "SECURITY_"

class MLSettings(BaseSettings):
    """ML configuration settings"""
    default_model_type: str = "rf"
    universal_model_name: str = "universal_ensemble_model"
    training_timeout_seconds: int = 300  # 5 minutes
    max_training_samples: int = 10000
    validation_split: float = 0.2

    @validator('validation_split')
    def validate_validation_split(cls, v):
        if not (0.1 <= v <= 0.5):
            raise ValueError('Validation split must be between 0.1 and 0.5')
        return v

    class Config:
        env_prefix = "ML_"

class TradingSettings(BaseSettings):
    """Trading configuration settings"""
    default_capital: float = 1000.0
    default_leverage: float = 10.0
    default_stop_loss_pct: float = 0.05
    default_min_hold_candles: int = 6
    max_leverage: float = 100.0
    min_capital: float = 10.0
    max_capital: float = 1000000.0

    @validator('default_capital')
    def validate_default_capital(cls, v):
        if not (cls.min_capital <= v <= cls.max_capital):
            raise ValueError(f'Default capital must be between {cls.min_capital} and {cls.max_capital}')
        return v

    @validator('default_leverage')
    def validate_default_leverage(cls, v):
        if not (1 <= v <= cls.max_leverage):
            raise ValueError(f'Default leverage must be between 1 and {cls.max_leverage}')
        return v

    @validator('default_stop_loss_pct')
    def validate_default_stop_loss_pct(cls, v):
        if not (0 < v <= 1):
            raise ValueError('Default stop loss percentage must be between 0 and 1')
        return v

    class Config:
        env_prefix = "TRADING_"

class LoggingSettings(BaseSettings):
    """Logging configuration settings"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/bybit_trader.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5

    @validator('level')
    def validate_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()

    class Config:
        env_prefix = "LOGGING_"

class BybitSettings(BaseSettings):
    """Bybit API configuration settings"""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: bool = True
    base_url: str = "https://api.bybit.com"
    testnet_url: str = "https://api-testnet.bybit.com"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

    @property
    def actual_base_url(self) -> str:
        return self.testnet_url if self.testnet else self.base_url

    class Config:
        env_prefix = "BYBIT_"

class Settings(BaseSettings):
    """Main application settings"""
    app_name: str = "Bybit AI Swing Trader"
    version: str = "2.0.0"
    description: str = "Enhanced AI-powered swing trading system with database persistence"

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    api: APISettings = APISettings()
    security: SecuritySettings = SecuritySettings()
    ml: MLSettings = MLSettings()
    trading: TradingSettings = TradingSettings()
    logging: LoggingSettings = LoggingSettings()
    bybit: BybitSettings = BybitSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings