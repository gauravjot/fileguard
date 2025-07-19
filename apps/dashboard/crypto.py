import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256

# --- Configuration
KEY_LENGTH = 32
SALT_LENGTH = 16
NONCE_LENGTH = 16
ITERATIONS = 100000
CHUNK_SIZE = 64 * 1024 # 64 KB chunks

def derive_key(password, salt, iterations=ITERATIONS, key_len=KEY_LENGTH):
    return PBKDF2(password.encode(), salt, dkLen=key_len, count=iterations, hmac_hash_module=SHA256)


def save_encrypted_file_to_disk(uploaded_file_obj, output_path, password):
    """
    Encrypts an UploadedFile chunk by chunk and saves it to disk.

    Args:
        uploaded_file_obj: File-like object to read the file from.
        output_path: Path where the encrypted file will be saved.
        password: The password used for encryption.

    Returns:
        Tuple: (salt, nonce, file_size_on_disk)
    """
    salt = get_random_bytes(SALT_LENGTH)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_GCM)
    nonce = cipher.nonce

    # We need to write salt, nonce, encrypted_chunks, and tag
    # Salt and nonce go at the beginning of the file, tag at the end
    try:
        with open(output_path, 'wb') as outfile:
            outfile.write(salt)
            outfile.write(nonce)

            while True:
                # Use read(CHUNK_SIZE) instead of .chunks()
                chunk = uploaded_file_obj.read(CHUNK_SIZE)
                if not chunk:
                    break
                encrypted_chunk = cipher.encrypt(chunk)
                outfile.write(encrypted_chunk)

            tag = cipher.digest()
            outfile.write(tag)

        return salt, nonce, os.path.getsize(output_path)
    except Exception as e:
        # Clean up partial file on error
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e


def decrypt_file_from_disk(input_filepath, output_filepath, password, salt, nonce):
    """
    Decrypts an encrypted file from input_filepath and writes the decrypted
    content to output_filepath.

    Args:
        input_filepath (str): Path to the encrypted file.
        output_filepath (str): Path where the decrypted file will be written.
        password (str): The password used for decryption.
        salt (bytes): The salt used during encryption (retrieved from DB).
        nonce (bytes): The nonce used during encryption (retrieved from DB).

    Returns:
        bool: True if decryption was successful, False otherwise.
              (Raises ValueError on tag mismatch/wrong password, which can be caught by caller)
    """
    try:
        key = derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

        with open(input_filepath, 'rb') as infile, open(output_filepath, 'wb') as outfile:
            # Read and discard the salt and nonce (they are passed as arguments)
            # Ensure the file pointer is at the start of the ciphertext
            infile.seek(SALT_LENGTH + NONCE_LENGTH) # Move past salt and nonce

            # Calculate where the tag should be (16 bytes from end)
            file_size = os.path.getsize(input_filepath)
            tag_start_offset = file_size - 16

            if tag_start_offset < (SALT_LENGTH + NONCE_LENGTH): # Ensure file is large enough for header + tag
                raise ValueError("Encrypted file is too small or corrupted.")

            # Read ciphertext in chunks, but be careful not to read the tag
            current_pos = infile.tell()
            while current_pos < tag_start_offset:
                bytes_to_read = min(CHUNK_SIZE, tag_start_offset - current_pos)
                chunk = infile.read(bytes_to_read)
                if not chunk:
                    raise ValueError("Unexpected end of encrypted file before tag.")
                decrypted_chunk = cipher.decrypt(chunk)
                outfile.write(decrypted_chunk)
                current_pos = infile.tell()

            # TODO: Setup Celery task to delete the temporary decrypted file after a certain time (time defined in settings.py)

            # Read the tag from the end of the file
            infile.seek(tag_start_offset)
            tag = infile.read(16)

            if len(tag) != 16:
                raise ValueError("Failed to read complete cipher tag.")
            # Verify the tag
            cipher.verify(tag)

        return True

    except ValueError as e:
        # This typically means wrong password or corrupted file (tag mismatch)
        # Clean up partial decrypted file
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        print(f"Decryption failed for {input_filepath}: {e}")
        return False
    except FileNotFoundError:
        print(f"Decryption failed: Input file '{input_filepath}' not found.")
        return False
    except Exception as e:
        # Clean up partial decrypted file
        if os.path.exists(output_filepath):
            os.remove(output_filepath)
        print(f"An unexpected error occurred during decryption of {input_filepath}: {e}")
        return False


def decrypt_file_from_disk_to_memory(input_path, password, salt, nonce):
    """
    Decrypts a file from disk and returns its content as bytes. Useful to show data within the browser.

    Args:
        input_path (str): Path to the encrypted file.
        password (str): The password used for decryption.
        salt (bytes): The salt used during encryption (retrieved from DB).
        nonce (bytes): The nonce used during encryption (retrieved from DB).

    Returns:
        bytes: The decrypted content of the file.
    """
    try:
        with open(input_path, 'rb') as infile:
            # Skip salt and nonce already passed as arguments
            infile.read(SALT_LENGTH)
            infile.read(NONCE_LENGTH)

            encrypted_content_remaining = infile.read()
            tag = encrypted_content_remaining[-16:]
            ciphertext = encrypted_content_remaining[:-16]

            key = derive_key(password, salt)
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

            decrypted_data = cipher.decrypt(ciphertext)
            cipher.verify(tag)

            return decrypted_data
    except ValueError:
        raise ValueError("Decryption failed: Incorrect password or file corruption.")
    except Exception as e:
        raise Exception(f"Error during decryption: {e}")