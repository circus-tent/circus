
class AlreadyExist(Exception):
    """ raised when a show exists """

class MessageError(Exception):
    """ error raised when a message is invalid """

class CallError(Exception):
    pass

class ArgumentError(Exception):
    """ exception raised when one argument or the number of arguments i
    invalid"""
