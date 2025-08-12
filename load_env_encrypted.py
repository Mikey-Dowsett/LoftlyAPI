from io import StringIO

from cryptography.fernet import Fernet
from dotenv import load_dotenv


def load_encrypted_env(encrypted_file_path: str, key: str):
    fernet = Fernet(key.encode())
    with open(encrypted_file_path, 'rb') as file:
        decrypted = fernet.decrypt(file.read())
    env_stream = StringIO(decrypted.decode())
    load_dotenv(stream=env_stream)
