import os
import logging

class Logger(object):

    def __init__(self, logdir:str, filename:str, lv='debug', format_str='') -> None:

        if not os.path.isdir(logdir):
            os.makedirs(logdir)

        filepath = os.path.join(logdir, filename)
        
        self.logger = logging.getLogger(__name__)

        self.set_level(lv)

        if not format_str:
            format_str = '%(asctime)s [%(levelname)s] %(message)s'
        formatter = logging.Formatter(format_str)
        file_handler = logging.FileHandler(filepath, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def set_level(self, lv):
        if lv == 'debug':
            level = logging.DEBUG
        elif lv == 'info':
            level = logging.INFO
        elif lv == 'warning':
            level = logging.WARNING
        elif lv == 'error':
            level = logging.DEBUG
        elif lv == 'critical':
            level = logging.CRITICAL
        
        self.logger.setLevel(level)

    def __call__(self, msg:str, cls=None, fn=None, lv:str='info') -> None:
        
        head = []
        if cls:
            head.append(type(cls).__name__)
        if fn:
            head.append(fn.__name__)

        message = '{0} | {1}'.format('.'.join(head), msg)

        if lv == 'debug':
            self.logger.debug(message)
        elif lv == 'info':
            self.logger.info(message)
        elif lv == 'warning':
            self.logger.warning(message)
        elif lv == 'error':
            self.logger.error(message)
        elif lv == 'critical':
            self.logger.critical(message)