from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://studyportal:studyportal_pass@localhost:5432/studyportal"
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    RUSTFS_ENDPOINT: str = "http://localhost:9000"
    # Browser-facing URL for presigned download links.
    # In Docker: internal endpoint is rustfs:9000, but the browser reaches it via localhost:9000.
    RUSTFS_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    RUSTFS_ACCESS_KEY: str = "studyportal"
    RUSTFS_SECRET_KEY: str = "studyportal_pass"
    RUSTFS_BUCKET: str = "study-portal"

    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_SUBMISSION_TOPIC: str = "homework.submitted"
    KAFKA_GRADED_TOPIC: str = "homework.graded"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
