from pydantic_settings import BaseSettings


class ConfigB(BaseSettings):
    config_b: str = "hello from config b"