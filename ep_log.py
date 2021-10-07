import logging
from logging.handlers import RotatingFileHandler

# logger = logging.getLogger("ep." + __name__)
logger = logging.getLogger("ep")

FORMAT = "%(asctime)s|%(levelname)-8s|%(filename)s:%(lineno)s-%(funcName)s| %(message)s"
formatter = logging.Formatter(FORMAT)

logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

fh = RotatingFileHandler('log__output.log', maxBytes=1024*1024*10)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


# %%

logger.critical('Logging started')

logger.error('test error')
logger.debug('test debug')
logger.info('test info')
logger.warning('test warning')
