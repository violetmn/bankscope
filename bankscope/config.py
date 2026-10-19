"""Load private project settings without overriding explicitly exported variables."""
from pathlib import Path
from dotenv import load_dotenv


def load_private_env(path=".env"):
    return load_dotenv(dotenv_path=Path(path), override=False, interpolate=False)
