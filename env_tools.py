import os
from io import StringIO

from cryptography.fernet import Fernet
from dotenv import load_dotenv


def load_env_from_envvar(enc_file: str = ".env.enc"):
    load_dotenv()
    key = os.getenv("ENV_DECRYPT_KEY")
    if not key:
        raise RuntimeError("Missing ENV_DECRYPT_KEY")

    fernet = Fernet(key.encode())

    with open(enc_file, "rb") as f:
        decrypted = fernet.decrypt(f.read())

    load_dotenv(stream=StringIO(decrypted.decode()))
