

class AlreadyExist(Exception):
    """Raised when a watcher exists """
    pass


class MessageError(Exception):
    """ error raised when a message is invalid """
    pass


class CallError(Exception):
    pass


class ArgumentError(Exception):
    """Exception raised when one argument or the number of
    arguments is invalid"""
    pass


class ConflictError(Exception):
    """Exception raised when one exclusive command is already running
    in background"""
    pass
