from os import path
from logging import getLogger, INFO, FileHandler, StreamHandler

logger = getLogger(__name__)
logger.setLevel(INFO)

log_file = path.join(
    path.dirname(path.dirname(path.realpath(__file__))),
    'log.log')
file_handler = FileHandler(log_file)
file_handler.setLevel(INFO)

console_handler = StreamHandler()
console_handler.setLevel(INFO)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
