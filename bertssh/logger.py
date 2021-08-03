import logging
import logging.handlers
import sys

class Logger:

  def __init__(self, **kwargs):
    self.debug = kwargs.get('debug', False)

  def init_logger(self, name=None, debug=False):
    # Setup Logging
    logger = logging.getLogger(name)
    # TODO Find a better approach to this hacky method
    if '---debug' in ' '.join(sys.argv) or self.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
    )
    logger.addHandler(streamhandler)
    return logger