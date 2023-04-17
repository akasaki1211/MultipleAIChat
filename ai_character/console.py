import ctypes

ENABLE_PROCESSED_OUTPUT = 0x0001
ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
MODE = ENABLE_PROCESSED_OUTPUT + ENABLE_WRAP_AT_EOL_OUTPUT + ENABLE_VIRTUAL_TERMINAL_PROCESSING

class Console(object):

    def __init__(self, default_color:str='') -> None:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        kernel32.SetConsoleMode(handle, MODE)

        self.default_color = ''
        self.set_default_color(default_color)

    def __call__(self, msg:str, col:str='') -> None:

        if col == 'red':
            s = '\033[31m'
        elif col == 'green':
            s = '\033[32m'
        elif col == 'yellow':
            s = '\033[33m'
        elif col == 'blue':
            s = '\033[34m'
        elif col == 'magenta':
            s = '\033[35m'
        elif col == 'cyan':
            s = '\033[36m'
        else:
            s = self.default_color
        e = '\033[0m'

        print(s + msg + e)
    
    def set_default_color(self, col:str) -> None:
        if col == 'red':
            self.default_color = '\033[31m'
        elif col == 'green':
            self.default_color = '\033[32m'
        elif col == 'yellow':
            self.default_color = '\033[33m'
        elif col == 'blue':
            self.default_color = '\033[34m'
        elif col == 'magenta':
            self.default_color = '\033[35m'
        elif col == 'cyan':
            self.default_color = '\033[36m'
        else:
            self.default_color = ''