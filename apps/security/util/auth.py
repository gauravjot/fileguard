from core.settings import BASE_DIR
from Crypto.Cipher import AES
import pyotp
import random
import string
import hashlib
import os


KEY_PATH = BASE_DIR / 'config' / 'encryption_key.key'
PASS_FILE_PATH = BASE_DIR / 'config' / 'passfile.key'


def is_pass_file_present():
    """
    Check if the pass file exists.
    """
    return os.path.exists(PASS_FILE_PATH)


def config_auth(password: str, otp_secret: str, otp_code: str) -> list[str]:
    # Save encryped password + otp into pass file

    # if any of the parameters are empty, raise an error
    if not password or not otp_secret or not otp_code:
        raise ValueError("Password, OTP secret, and OTP code must not be empty")

    # Validate OTP code
    totp = pyotp.TOTP(otp_secret)
    if not totp.verify(otp_code, valid_window=1):
        raise ValueError("Invalid OTP code")

    # Get the key
    if not os.path.exists(KEY_PATH):
        raise FileNotFoundError("Encryption key file does not exist. Please generate it first.")
    with open(KEY_PATH, 'rb') as f:
        key = f.read()

    cipher = AES.new(key, AES.MODE_EAX)
    # Generate four random 6-digit alphanumeric codes
    backup_codes = []
    for _ in range(4):
        backup_code = ''.join(random.choices(
            string.ascii_lowercase + string.digits, k=6))
        backup_code = hash_this(backup_code)
        backup_codes.append(backup_code)
    # Encrypt
    ciphertext, tag = cipher.encrypt_and_digest(
        hash_this(password).encode() + otp_secret.encode() + ''.join(backup_codes).encode())
    encrypted = [x for x in (cipher.nonce, tag, ciphertext)]

    # Save to pass file
    with open(PASS_FILE_PATH, 'wb') as f:
        for item in encrypted:
            f.write(item)
    return backup_codes


def verify_auth(password: str, otp_code: str):
    # Read the pass file
    with open(PASS_FILE_PATH, 'rb') as f:
        data = f.read()

    nonce = data[:16]
    tag = data[16:32]
    ciphertext = data[32:]

    # Get the key
    with open(KEY_PATH, 'rb') as f:
        key = f.read()

    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)

    try:
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag).decode()
        # format: [hashed password] + [16 length otp secret] + [32 length * 4 backup codes]
        hashed_password = decrypted_data[:(-1 * (16 + 32 * 4))]
        otp_secret = decrypted_data[(-1 * (16 + 32 * 4)):(-1 * (32 * 4))]
        backup_codes = decrypted_data[(-1 * (32 * 4)):]
        backup_codes = [backup_codes[i:i+32] for i in range(0, len(backup_codes), 32)]

        if hashed_password != hash_this(password):
            return False

        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_code):
            # Check backup codes
            if otp_code not in backup_codes:
                return False

        return True
    except (ValueError, KeyError):
        return False


def generate_otp_secret():
    """
    Generates a random 16-character alphanumeric string for OTP secret.
    """
    return pyotp.random_base32()


def hash_this(string):
    return hashlib.sha256(str(string).encode('utf-8')).hexdigest()
