# coding=utf-8


from utils import logger
import sys, os
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
import config
from copy import copy


version = sys.version_info
if version[0] == 3:
    if version[1] >= 4:
        import importlib
        reload = importlib.reload
    else:
        import imp
        reload = imp.reload


# Formatter for WatchedFileHandler
class _CustomFormatter(logger.logging.Formatter):
    def __init__(self, fmt="%s %s in %s():%s:\n%s" % (logger.LOG_FMT_TIME, logger.LOG_FMT_LEVEL, logger.LOG_FMT_FUNC_NAME, logger.LOG_FMT_LINE, logger.LOG_FMT_MESSEGE), datefmt="%Y-%m-%d %H:%M:%S"):
        super(_CustomFormatter, self).__init__(fmt, datefmt)
    
    def format(self, record):
        record = copy(record)
        res = super().format(record)
        res = res.strip()
        # shift linebreaks of the same log to the right
        res = res.replace("\n", "\n\t")
        return res


_initalized = False

class __Context(object):
    def __init__(self):
        global _initalized
        assert not _initalized
        _initalized = True
        
        # only set global constants and raw config file
        self.TESTING = False
        self.DEBUG = False
        self.TEST_SEQUENCE = set()
        self.LOGGER = logger.loggerWithName("Deployment")
        self.CONFIG = config.CONFIG
        self.PROJECT_FOLDER = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))

        # validate CONFIG
        if "github" not in self.CONFIG:
            print("Invalid config.py, check sample!")
            sys.exit(1)

        if os.path.exists("/Users/Philipp/"):
            self.DEBUG = True
            
        self._configureLogger()
        
    def _configureLogger(self):
        logPath = os.path.join(self.PROJECT_FOLDER, "Logs", "log.log")
        
        STREAM_HANDLER = logger.StreamHandler(sys.stdout)
        self.LOGGER.addHandler(logger.configureHandler(logger.WatchedFileHandler(logPath, encoding="utf-8"), _CustomFormatter()))
        self.LOGGER.addHandler(logger.configureHandler(STREAM_HANDLER, logger.logging.Formatter()))
        self.LOGGER.setLevel(logger.logging.DEBUG)
        
        if not self.DEBUG and "mailLogger" in self.CONFIG and not self.TESTING:
            self.LOGGER.addHandler(logger.configureHandler(self.CONFIG["mailLogger"], logger.PNMailLogFormatter(), logLevel=logger.logging.CRITICAL))

    def addTestSeq(self, seq):
        assert seq != 1
        
        if self.TESTING:
            self.TEST_SEQUENCE.add(seq)

    def reloadCONFIG(self):
        reload(config)
        self.CONFIG = config.CONFIG


CONTEXT = __Context()