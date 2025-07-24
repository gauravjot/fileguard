import os
from django.conf import settings
from celery import shared_task
from django.db import transaction
import uuid

from .models import EncryptedFile
from .crypto import save_encrypted_file_to_disk, decrypt_file_from_disk


@shared_task(bind=True)
def perform_encryption_task(self, uploaded_file_path, encrypted_file_id: int, password_raw):
    """
    Celery task to encrypt a file.

    Args:
    uploaded_file_path: Absolute path to the temporary uploaded file.
    original_filename: The original name of the file being encrypted.
    password_raw: The raw password used for encryption.
    """
    encrypted_file_instance = EncryptedFile.objects.get(id=encrypted_file_id)
    original_filename = encrypted_file_instance.original_filename
    # Make EncryptedFile object with status='PROCESSING'
    with transaction.atomic():
        encrypted_file_instance.status = 'PROCESSING'
        encrypted_file_instance.celery_task_id = self.request.id
        encrypted_file_instance.save()
    try:
        with transaction.atomic():
            # Create a unique filename for the encrypted output
            encrypted_file_basename = f"{self.request.id}.enc"

            # Get the full path where the encrypted file will be saved
            encrypted_file_full_path = os.path.join(settings.MEDIA_ROOT, 'encrypted_files', encrypted_file_basename)
            # Ensure directory exists
            os.makedirs(os.path.dirname(encrypted_file_full_path), exist_ok=True)

            # Encrypt and save to disk
            with open(uploaded_file_path, 'rb') as temp_infile:
                salt, nonce, encrypted_file_size = save_encrypted_file_to_disk(
                    temp_infile, encrypted_file_full_path, password_raw
                )

            # Clean up the temporary uploaded file
            if os.path.exists(uploaded_file_path):
                os.remove(uploaded_file_path)

            # Save to database
            encrypted_file_instance.original_filename = original_filename
            encrypted_file_instance.encrypted_file = os.path.join('encrypted_files', encrypted_file_basename)
            encrypted_file_instance.file_size = encrypted_file_size
            encrypted_file_instance.salt = salt
            encrypted_file_instance.nonce = nonce
            encrypted_file_instance.status = 'COMPLETED'
            encrypted_file_instance.save()

        print(f"Celery: Encryption task for {original_filename} completed successfully! Task ID: {self.request.id}")
        return {'success': True, 'message': 'File encrypted successfully', 'file': encrypted_file_instance.serialize("json")}

    except Exception as e:
        print(f"Celery: Encryption task for {original_filename} failed: {e}")
        # Update model status to FAILED
        try:
            with transaction.atomic():
                # Attempt to find the entry by task_id and update its status
                if encrypted_file_instance:
                    encrypted_file_instance.status = 'FAILED'
                    encrypted_file_instance.save()
        except Exception as update_e:
            print(f"Celery: Failed to update status for task {self.request.id}: {update_e}")
        return {'success': False, 'message': str(e), 'file': encrypted_file_instance.serialize("json") if encrypted_file_instance else None}


@shared_task(bind=True)
def perform_decryption_task(self, encrypted_file_id, password_raw):
    """
    Celery task to decrypt a file.

    Args:
    encrypted_file_id: ID of the EncryptedFile instance to decrypt.
    password_raw: The raw password used for decryption.
    """
    try:
        with transaction.atomic():
            encrypted_file_instance = EncryptedFile.objects.get(id=encrypted_file_id)
            encrypted_file_instance.status = 'DECRYPTING'
            encrypted_file_instance.celery_task_id = self.request.id
            encrypted_file_instance.save()

        # Create a temporary path for the decrypted file
        temp_decrypted_dir = os.path.join(settings.MEDIA_ROOT, 'decrypted_temp')
        os.makedirs(temp_decrypted_dir, exist_ok=True)

        # Use a unique name for the temporary decrypted file
        original_filename = encrypted_file_instance.original_filename
        temp_decrypted_filename = f"{uuid.uuid4()}_{original_filename}"
        temp_decrypted_file_path = os.path.join(temp_decrypted_dir, temp_decrypted_filename)

        # Perform decryption
        decryption_success = decrypt_file_from_disk(
            encrypted_file_instance.encrypted_file.path,
            temp_decrypted_file_path,
            password_raw,
            encrypted_file_instance.salt,
            encrypted_file_instance.nonce
        )

        with transaction.atomic():
            if decryption_success:
                encrypted_file_instance.status = 'DECRYPTED'  # File is ready for download
                encrypted_file_instance.decrypted_temp_path = temp_decrypted_file_path  # Store path
                encrypted_file_instance.save()
                print(
                    f"Celery: Decryption task for {original_filename} completed successfully. Temp file: {temp_decrypted_file_path}")
                return {
                    'success': True,
                    'message': 'File decrypted successfully and ready for download.',
                    'file': encrypted_file_instance.serialize("json"),
                }
            else:
                encrypted_file_instance.status = 'FAILED'
                encrypted_file_instance.save()
                # Clean up incomplete decrypted file
                if os.path.exists(temp_decrypted_file_path):
                    os.remove(temp_decrypted_file_path)
                print(f"Celery: Decryption task for {original_filename} failed: Decryption process failed.")
                return {'success': False, 'message': 'Decryption process failed.', 'file': encrypted_file_instance.serialize("json") if encrypted_file_instance else None}

    except EncryptedFile.DoesNotExist:
        print(f"Celery: Decryption task failed: EncryptedFile with ID {encrypted_file_id} not found.")
        return {'success': False, 'message': 'File not found.'}
    except Exception as e:
        print(f"Celery: Decryption task for ID {encrypted_file_id} failed: {e}")
        try:
            with transaction.atomic():
                encrypted_file_instance = EncryptedFile.objects.filter(celery_task_id=self.request.id).first()
                if encrypted_file_instance:
                    encrypted_file_instance.status = 'FAILED'
                    # Clear temp path on failure
                    if encrypted_file_instance.decrypted_temp_path and os.path.exists(encrypted_file_instance.decrypted_temp_path):
                        os.remove(encrypted_file_instance.decrypted_temp_path)
                        encrypted_file_instance.decrypted_temp_path = None
                    encrypted_file_instance.save()
        except Exception as update_e:
            print(f"Celery: Failed to update status for task {self.request.id}: {update_e}")
        return {'success': False, 'message': str(e), 'file': None}
