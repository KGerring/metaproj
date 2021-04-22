class Error(Exception):
    """Base exception for rope"""


class ResourceNotFoundError(Error):
    """Resource not found exception"""


class RefactoringError(Error):
    """Errors for performing a refactoring"""


class InterruptedTaskError(Error):
    """The task has been interrupted"""


class HistoryError(Error):
    """Errors for history undo/redo operations"""


class ModuleNotFoundError(Error):
    """Module not found exception"""


class AttributeNotFoundError(Error):
    """Attribute not found exception"""


class NameNotFoundError(Error):
    """Name not found exception"""


class BadIdentifierError(Error):
    """The name cannot be resolved"""


class ModuleSyntaxError(Error):
    """Module has syntax errors

    The `filename` and `lineno` fields indicate where the error has
    occurred.

    """

    def __init__(self, filename, lineno, message):
        self.filename = filename
        self.lineno = lineno
        self.message_ = message
        super().__init__(f'Syntax error in file <{filename}> line <{lineno}>: {message}')


class ModuleDecodeError(Error):
    """Cannot decode module"""

    def __init__(self, filename, message):
        self.filename = filename
        self.message_ = message
        super().__init__(f'Cannot decode file <{filename}>: {message}')
