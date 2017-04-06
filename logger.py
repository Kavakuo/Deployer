import logging
from logging import StreamHandler
from logging.handlers import WatchedFileHandler, SMTPHandler
from formatter_const import *

def loggerWithName(name):
    """
    :param name: name of the logger
    :type name: str

    :return: A new Logger
    :rtype: logging.Logger
    """

    return logging.getLogger(name)


def addHandlersToLogger(logger, handlers, logLevel=None):
    """
    Adds a list of handlers to a Logger.

    :param logger: Logger instance
    :type logger: logging.Logger

    :param handlers: List of handlers
    :type handlers: list

    :param logLevel: optional logLevel, set to all *handlers*
    :type logLevel: int
    """

    for handler in handlers:
        if logLevel:
            handler.setLevel(logLevel)
        logger.addHandler(handler)



def configureHandler(handler, formatter, logLevel=logging.DEBUG):
    """
    Set formatter and logLevel to handlers.

    :param handler: The Handler to configure.
    :type handler: logging.Handler

    :param formatter: Formatter set to the handler
    :type formatter: logging.Formatter

    :param logLevel: logLevel set to all handlers, DEBUG is default
    :type logLevel: int
    
    :return: handler
    :rtype: logging.Handler
    """

    handler.setFormatter(formatter)
    handler.setLevel(logLevel)
    return handler


class PNLogFormatter(logging.Formatter):
    def __init__(self, fmt="%s %s: %s" %(LOG_FMT_TIME, LOG_FMT_LEVEL, LOG_FMT_MESSEGE), datefmt="%Y-%m-%d %H:%M:%S"):
        super(PNLogFormatter, self).__init__(fmt, datefmt)

class PNMailLogFormatter(logging.Formatter):
    def __init__(self, fmt='%(asctime)s in %(pathname)s:%(lineno)d\n%(levelname)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S"):
        super(PNMailLogFormatter, self).__init__(fmt, datefmt)