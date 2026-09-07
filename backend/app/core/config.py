import os
from dotenv import load_dotenv

# Load the .env file from the root directory
load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://verve_gate_user:JoNo48N1H57bWzcTPpD5u7n8GGS5W4mT@dpg-daf6q8on74is738jp1ig-a.oregon-postgres.render.com/verve_gate"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    LIVE_RATES_ENABLED: bool = os.getenv("LIVE_RATES_ENABLED", "true").lower() == "true"
    RATE_PROVIDER_URL: str = os.getenv(
        "RATE_PROVIDER_URL",
        "https://api.coinbase.com/v2/exchange-rates?currency=USD",
    )
    RATE_CACHE_SECONDS: int = int(os.getenv("RATE_CACHE_SECONDS", 60))
    PLATFORM_FEE_PERCENTAGE: float = float(os.getenv("PLATFORM_FEE_PERCENTAGE", 3.0))
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Verve Gate")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    PASSWORD_RESET_TTL_MINUTES: int = int(os.getenv("PASSWORD_RESET_TTL_MINUTES", 30))
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]

settings = Settings()