"""
Input validation utilities
Validates files, parameters, and configuration
"""

import magic
import os
from errors import ValidationError, FileProcessingError
import logging

logger = logging.getLogger(__name__)

# MIME types for allowed files
ALLOWED_MIMETYPES = {
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

# File extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}


def validate_file_extension(filename):
    """Validate file has allowed extension"""
    if not filename:
        raise ValidationError("Filename is required")
    
    ext = os.path.splitext(filename)[1].lstrip('.').lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Invalid file extension: .{ext}",
            details={'allowed': list(ALLOWED_EXTENSIONS)}
        )
    
    return ext


def validate_file_size(file_stream, max_size_mb=50):
    """Validate file size (non-destructive, stores position)"""
    # Get current position
    current_pos = file_stream.tell()
    
    # Seek to end to get size
    file_stream.seek(0, 2)
    size = file_stream.tell()
    
    # Seek back to original position
    file_stream.seek(current_pos)
    
    max_bytes = max_size_mb * 1024 * 1024
    
    if size > max_bytes:
        raise ValidationError(
            f"File size {size / (1024*1024):.1f}MB exceeds limit of {max_size_mb}MB",
            details={'size_mb': size / (1024*1024), 'max_mb': max_size_mb}
        )
    
    if size == 0:
        raise ValidationError("File is empty")
    
    return True


def validate_file_mimetype(file_stream, filename):
    """Validate file MIME type (checks magic bytes)"""
    try:
        # Python-magic library
        mime = magic.from_buffer(file_stream.read(1024), mime=True)
        file_stream.seek(0)  # Reset for reading
        
        if mime not in ALLOWED_MIMETYPES:
            raise ValidationError(
                f"Invalid file type: {mime}",
                details={'type': mime, 'allowed': list(ALLOWED_MIMETYPES)}
            )
        
        return True
    except Exception as e:
        logger.warning(f"MIME type detection failed: {str(e)}, falling back to extension check")
        # Fallback to extension if magic fails
        return validate_file_extension(filename)


def validate_csv_encoding(file_path, encodings=None):
    """Detect and validate CSV file encoding"""
    if encodings is None:
        encodings = ['utf-8', 'iso-8859-1', 'cp1252', 'utf-16']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, LookupError):
            continue
    
    raise FileProcessingError(
        "Unable to detect file encoding. Please ensure file is valid UTF-8 or ISO-8859-1"
    )


def validate_file_upload(file, config):
    """Comprehensive file validation"""
    # Check filename exists
    if not file.filename:
        raise ValidationError("Filename is required")
    
    # Validate extension
    ext = validate_file_extension(file.filename)
    
    # Validate file size
    validate_file_size(file.stream, config.get('max_size_mb', 50))
    
    # Validate MIME type
    # Note: Only use if python-magic is installed
    try:
        validate_file_mimetype(file.stream, file.filename)
    except ImportError:
        logger.warning("python-magic not installed, skipping MIME type check")
    
    # Reset stream to beginning for actual reading
    file.stream.seek(0)
    
    return True


def validate_operation_config(operations):
    """Validate cleaning operation configuration"""
    if not isinstance(operations, dict):
        raise ValidationError("Operations must be an object")
    
    valid_ops = {
        'smart_type_conversion', 'handle_missing', 'remove_duplicates',
        'feature_engineering', 'clean_text', 'handle_outliers',
        'remove_high_missing', 'redact_phi', 'validate_clinical',
        'standardize_codes', 'validate_ranges', 'normalize_clinical_text'
    }
    
    for op_id, op_config in operations.items():
        if op_id not in valid_ops:
            raise ValidationError(
                f"Unknown operation: {op_id}",
                details={'operation': op_id, 'valid': list(valid_ops)}
            )
        
        if not isinstance(op_config, dict):
            raise ValidationError(f"Operation {op_id} must be an object")
        
        # Validate structure
        if 'checked' in op_config and not isinstance(op_config['checked'], bool):
            raise ValidationError(f"Operation {op_id}: 'checked' must be boolean")
        
        if 'method' in op_config and not isinstance(op_config['method'], str):
            raise ValidationError(f"Operation {op_id}: 'method' must be string")
    
    return True


def validate_session_id(session_id):
    """Validate session ID format"""
    if not session_id or not isinstance(session_id, str):
        raise ValidationError("Invalid session ID")
    
    # UUID4 format check (basic)
    if len(session_id) != 36 or session_id.count('-') != 4:
        raise ValidationError("Session ID format invalid")
    
    return True
