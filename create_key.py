from cryptography.fernet import Fernet

# Generate a key (do this ONCE, store it securely)
key = Fernet.generate_key()
print("Save this key securely:", key.decode())  # Copy this key

fernet = Fernet(key)

with open('.env', 'rb') as file:
    original = file.read()

encrypted = fernet.encrypt(original)

with open('.env.enc', 'wb') as encrypted_file:
    encrypted_file.write(encrypted)

print("Encrypted .env to .env.enc")
