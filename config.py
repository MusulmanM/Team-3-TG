from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding='utf-8',
        extra='ignore'
    )

    BOT_TOKEN: str
    ADMINS: str
    ADMIN_CHAT_LINK: str

    @property
    def admin_list(self) -> list[int]:
        return [int(x.strip()) for x in self.ADMINS.split(",") if x.strip()]

settings = Settings()
