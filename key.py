#key.py
from wallet import generate_keypair
private_key, public_key = generate_keypair()
print("Private Key:", private_key)
print("Public Key :", public_key)