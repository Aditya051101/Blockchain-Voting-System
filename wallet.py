# wallet.py
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
from ecdsa.util import sigdecode_string
import hashlib

def generate_keypair():
    """
    Returns (private_hex, public_hex_uncompressed)
    public_hex has leading '04' + X(32) + Y(32) (hex) which is compatible with elliptic.js uncompressed keys.
    """
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    priv_hex = sk.to_string().hex()
    # vk.to_string() returns X||Y (64 bytes) -> prefix with '04' for uncompressed format
    pub_hex = "04" + vk.to_string().hex()
    return priv_hex, pub_hex

def sign_message_hex(private_key_hex: str, message: str) -> str:
    """
    Sign the plaintext message (server-side helper).
    This function hashes the message (sha256) and returns DER signature hex.
    If you are signing on the client, client produces a raw r||s hex (elliptic.js) — server accepts that format too.
    """
    sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    msg_hash = hashlib.sha256(message.encode()).digest()
    signature = sk.sign_digest(msg_hash)   # returns DER by default
    return signature.hex()

def verify_signature_hex(public_key_hex: str, message_hash_hex: str, signature_hex: str) -> bool:
    """
    Verify a signature where:
      - public_key_hex: either '04'+X+Y hex (uncompressed) or X+Y (no prefix)
      - message_hash_hex: sha256 digest hex (the client computed the digest and sent it)
      - signature_hex: either raw r||s hex (128 chars) produced by elliptic.js or a DER hex signature.
    Returns True if valid, False otherwise.
    """
    try:
        # convert public key hex to bytes usable by ecdsa.VerifyingKey
        vk_bytes = bytes.fromhex(public_key_hex)
        # handle uncompressed prefix 0x04
        if len(vk_bytes) == 65 and vk_bytes[0] == 4:
            vk_bytes = vk_bytes[1:]  # remove prefix, leaving 64 bytes X||Y

        # create verifying key
        vk = VerifyingKey.from_string(vk_bytes, curve=SECP256k1)

        # digest bytes (client already sent SHA256 hex)
        msg_hash_bytes = bytes.fromhex(message_hash_hex)

        sig_bytes = bytes.fromhex(signature_hex)

        # If signature is raw r||s (64 bytes), use sigdecode_string with verify_digest
        if len(sig_bytes) == 64:
            # verify_digest expects signature (r||s) and the digest
            return vk.verify_digest(sig_bytes, msg_hash_bytes, sigdecode=sigdecode_string)

        # otherwise assume DER-encoded signature (common on Python side)
        # use verify_digest with default sigdecode; verify_digest accepts DER too
        return vk.verify_digest(sig_bytes, msg_hash_bytes)
    except BadSignatureError:
        # invalid signature
        return False
    except Exception as e:
        # other errors (bad key format, hex decode, etc.)
        print("Signature verification error:", e)
        return False
