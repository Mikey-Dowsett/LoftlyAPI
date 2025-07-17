import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from io import StringIO

def load_encrypted_env(encrypted_file_path: str, key: str):
    fernet = Fernet(key.encode())
    with open(encrypted_file_path, 'rb') as file:
        decrypted = fernet.decrypt(file.read())
    env_stream = StringIO(decrypted.decode())
    load_dotenv(stream=env_stream)
