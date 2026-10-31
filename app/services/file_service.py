import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'log'}

# Map of file extensions to expected MIME types
MIME_TYPE_MAP = {
    'txt': ['text/plain'],
    'pdf': ['application/pdf'],
    'png': ['image/png'],
    'jpg': ['image/jpeg'],
    'jpeg': ['image/jpeg'],
    'gif': ['image/gif'],
    'doc': ['application/msword'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'xls': ['application/vnd.ms-excel'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    'zip': ['application/zip', 'application/x-zip-compressed'],
    'log': ['text/plain', 'application/octet-stream']
}

MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

# Magic bytes for file type detection
MAGIC_BYTES = {
    'pdf': b'%PDF',
    'png': b'\x89PNG',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
    'gif': b'GIF8',
    'zip': b'PK\x03\x04',
    'docx': b'PK\x03\x04',
    'xlsx': b'PK\x03\x04',
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_file_signature(file, extension):
    """Verify file content matches expected type using magic bytes."""
    file.seek(0)
    header = file.read(8)
    file.seek(0)
    
    if extension in MAGIC_BYTES:
        expected = MAGIC_BYTES[extension]
        return header.startswith(expected)
    
    # For text-based files, check if content is mostly printable
    if extension in ['txt', 'log']:
        try:
            header.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False
    
    return True  # Can't verify, allow it


def save_upload(file):
    """
    Securely saves an uploaded file and returns metadata.
    Returns: (stored_filename, storage_path, file_size, mime_type, error_message)
    """
    if not file or file.filename == '':
        return None, None, None, None, 'No file selected'
    
    if not allowed_file(file.filename):
        return None, None, None, None, 'File type not allowed'
    
    # Get extension
    extension = file.filename.rsplit('.', 1)[1].lower()
    
    # Verify file signature (magic bytes)
    if not verify_file_signature(file, extension):
        return None, None, None, None, 'File content does not match extension (possible spoofing)'
    
    # Read file content to check size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return None, None, None, None, f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB'
    
    if file_size == 0:
        return None, None, None, None, 'File is empty'
    
    # Generate secure filename
    original_filename = secure_filename(file.filename)
    if not original_filename:
        original_filename = 'uploaded_file'
    
    # Create unique stored filename
    file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    stored_filename = f"{uuid.uuid4().hex}.{file_ext}" if file_ext else uuid.uuid4().hex
    
    # Create storage path
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    storage_path = os.path.join(upload_folder, stored_filename)
    
    # Save file
    file.save(storage_path)
    
    # Verify saved file size matches
    if os.path.getsize(storage_path) != file_size:
        os.remove(storage_path)
        return None, None, None, None, 'File upload corrupted'
    
    # Get MIME type
    mime_type = file.content_type or 'application/octet-stream'
    
    return stored_filename, storage_path, file_size, mime_type, None