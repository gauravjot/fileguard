# file_manager/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse, FileResponse
from django.conf import settings
from django.core.files.storage import default_storage
import os
import uuid  # For unique temporary filenames

from .forms import EncryptFileForm, DecryptFileForm, CreateDirectoryForm
from .models import EncryptedFile, get_home_contents, Directory
from .tasks import perform_encryption_task, perform_decryption_task  # Import our Celery tasks
from celery.result import AsyncResult  # To check task status


def index(request):
    return render(request, 'dashboard.html')


def upload_file_form(request):
    if request.method == 'POST':
        form = EncryptFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            password = form.cleaned_data['password']
            parent_directory = form.cleaned_data['parent_directory']

            # 1. Save the uploaded file temporarily to disk
            # Generate a unique temp filename to avoid clashes
            temp_file_uuid = uuid.uuid4().hex
            temp_upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
            os.makedirs(temp_upload_dir, exist_ok=True)

            temp_file_name_on_disk = default_storage.save(
                os.path.join('temp_uploads', f"{temp_file_uuid}_{uploaded_file.name}"),
                uploaded_file
            )
            temp_file_path_absolute = default_storage.path(temp_file_name_on_disk)

            # 2. Create a pending EncryptedFile entry (optional, but good for tracking)
            # This allows you to track the file even before encryption completes.
            pending_file_entry = EncryptedFile.objects.create(
                original_filename=uploaded_file.name,
                status='PENDING',
                # These fields will be updated by the Celery task
                encrypted_file='',  # Placeholder
                file_size=0,       # Placeholder
                salt=b'',          # Placeholder
                nonce=b'',         # Placeholder
                directory=Directory.objects.get(pk=parent_directory) if parent_directory else None,
            )

            # 3. Enqueue the encryption task to Celery
            task = perform_encryption_task.delay(temp_file_path_absolute, pending_file_entry.pk, password)

            return redirect('dashboard:list_encrypted_files', directory=parent_directory if parent_directory else '')
    return JsonResponse({'success': False, 'message': 'Invalid form submission.'}, status=400)


def create_directory_form(request):
    if request.method == 'POST':
        form = CreateDirectoryForm(request.POST)
        if form.is_valid():
            directory_name = form.cleaned_data['directory_name']
            parent_directory = form.cleaned_data['parent_directory']

            parent_directory_obj = Directory.objects.get(
                pk=parent_directory) if parent_directory else None

            # Create the directory using the manager method
            try:
                Directory.objects.create(name=directory_name, parent=parent_directory_obj)
                # Redirect to the file list view
                return redirect('dashboard:list_encrypted_files', directory=parent_directory)
            except ValueError as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid form submission.'}, status=400)


def list_encrypted_files(request, directory=None):
    try:
        create_directory_form = CreateDirectoryForm()
        upload_file_form = EncryptFileForm()
        if directory:
            create_directory_form.fields['parent_directory'].initial = directory
            upload_file_form.fields['parent_directory'].initial = directory
        return render(
            request,
            'file_manager/list_files.html',
            {
                'create_directory_form': create_directory_form,
                'upload_file_form': upload_file_form,
                'breadcrumbs': Directory.objects.get(pk=directory).get_breadcrumbs() if directory and int(directory) > 0 else [Directory(name='/', parent=None)],
                **get_home_contents(directory=directory if directory is not None else '', sort='name')
            })
    except Directory.DoesNotExist:
        raise Http404("Directory not found.")


def download_encrypted_file(request, file_id):
    encrypted_file_obj = get_object_or_404(EncryptedFile, id=file_id)
    try:
        response = FileResponse(open(encrypted_file_obj.encrypted_file.path, 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{encrypted_file_obj.original_filename}.enc"'
        return response
    except FileNotFoundError:
        raise Http404("Encrypted file not found on disk.")


def decrypt_file(request, file_id):
    encrypted_file_obj = get_object_or_404(EncryptedFile, id=file_id)

    if request.method == 'POST':
        form = DecryptFileForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']

            # Enqueue the decryption task
            task = perform_decryption_task.delay(
                encrypted_file_obj.id,
                password
            )

            # Update the file's Celery task ID and status for tracking
            encrypted_file_obj.celery_task_id = task.id
            encrypted_file_obj.status = 'PENDING_DECRYPTION'  # Or PROCESSING
            encrypted_file_obj.save()

            return render(request, 'file_manager/upload_status.html', {  # Reusing upload_status template
                'message': f"Decryption for '{encrypted_file_obj.original_filename}' has been queued. "
                f"You can track its status.",
                'file_id': encrypted_file_obj.pk,
                'task_id': task.id,
                'is_encryption': False,
            })
    else:
        form = DecryptFileForm()

    return render(request, 'file_manager/decrypt_form.html', {
        'form': form,
        'file_obj': encrypted_file_obj
    })


def check_task_status(request, task_id):
    """
    API endpoint to check the status of a Celery task.
    """
    task = AsyncResult(task_id)
    if task.state == 'SUCCESS':
        # If decryption was successful, you'd handle the data here.
        # For simplicity, we just return status.
        # If the task returned the decrypted data, you'd retrieve it from task.result['data']
        # and potentially serve it or save it to a temporary download location.
        # NOTE: Returning large decrypted data via JSON is not efficient or secure.
        # Best practice is to save to a temp file and provide a URL.
        # This will be the dict {'success': True/False, 'message': ...} or {'success': True, 'data': ...}
        result = task.result
        if result['success']:
            # In a real app, save result['data'] (which is bytes) to a temp file,
            # then return a URL to that temp file.
            # For this example, we just confirm success.
            return JsonResponse({'status': task.state, 'message': result.get('message', 'Error getting message'), 'success': True, 'file_id': task.args[0] if task.args and len(task.args) > 0 else None, 'decrypted_file_id': task.result.get('decrypted_file_id', None)})
        else:
            return JsonResponse({'status': task.state, 'message': result.get('message', 'Task failed'), 'success': False})

    elif task.state == 'FAILURE':
        return JsonResponse({'status': task.state, 'message': str(task.info), 'success': False})
    else:
        # PENDING, STARTED, RETRY, etc.
        return JsonResponse({'status': task.state, 'message': 'Processing...', 'success': None})


def download_decrypted_file(request, file_id):
    encrypted_file_instance = get_object_or_404(EncryptedFile, id=file_id)

    decrypted_file_path = encrypted_file_instance.decrypted_temp_path

    if not decrypted_file_path or not os.path.exists(decrypted_file_path):
        # File not decrypted yet, or already cleaned up, or never existed
        return HttpResponse("File not ready for download or already removed.", status=404)

    # Use FileResponse for efficient serving of large files
    response = FileResponse(open(decrypted_file_path, 'rb'))
    response['Content-Type'] = 'application/octet-stream'  # Or guess based on filename
    response['Content-Disposition'] = f'attachment; filename="{encrypted_file_instance.original_filename}"'

    # Optional: Clean up the temporary decrypted file immediately after serving
    # Be cautious with this if a user might try to download multiple times quickly
    # A better approach for cleanup might be a Celery Beat task.
    # For now, this ensures it's deleted after the first download attempt.
    # (Note: FileResponse might keep the file handle open for a while,
    # so deletion here might fail or happen later. A post-response hook or Celery Beat is more robust)

    # You might want to update the model status here to indicate download started/completed
    # encrypted_file_instance.status = 'DOWNLOADED' # Or some other final status
    # encrypted_file_instance.decrypted_temp_path = None # Clear the path
    # encrypted_file_instance.save()

    # For robust cleanup: Use a callback or a separate task.
    # A simple way for immediate cleanup after the response is sent:
    # This requires `django.core.servers.basehttp.WSGIRequestHandler` to handle `close()`
    # For production, consider `mod_xsendfile` or similar server-level solutions.
    def file_cleanup():
        if os.path.exists(decrypted_file_path):
            os.remove(decrypted_file_path)
            # You might want to update the model status and clear path here too
            # This runs *after* the response is sent and file read
            encrypted_file_instance.decrypted_temp_path = None
            encrypted_file_instance.status = 'COMPLETED'  # Assuming download marks completion
            encrypted_file_instance.save()

    response.streaming = True  # Ensure it's streamed
    response.close = file_cleanup  # Attach cleanup callback

    return response
