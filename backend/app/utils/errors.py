class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"


class SSHConnectionError(AppError):
    status_code = 502
    code = "SSH_CONNECTION_FAILED"


class SSHCommandError(AppError):
    status_code = 502
    code = "SSH_COMMAND_FAILED"


class RemoteFileNotFoundError(AppError):
    status_code = 404
    code = "FILE_NOT_FOUND"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"


class YAMLValidationError(AppError):
    status_code = 400
    code = "YAML_VALIDATION_ERROR"
