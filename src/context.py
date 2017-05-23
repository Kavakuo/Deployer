# coding=utf-8


from utils import logger
import sys, os
projectFolder = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, projectFolder)
import config, hashlib
from copy import copy
import validateConfig


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

class _CustomWatchedFileHandler(logger.WatchedFileHandler):
    def emit(self, record):
        os.makedirs(os.path.join(projectFolder, "Logs"), exist_ok=True)
        super().emit(record)

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
        self.MAIL_HANDLER = None
        
        self.CONFIG = config.CONFIG
        self.PROJECT_FOLDER = projectFolder
        
        self.PROTECTION = None
        self.PROTECTION_COOKIE = None
        
        self.configPath = os.path.join(self.PROJECT_FOLDER, "config.py")
        self.configHash = self._calcConfigHash()
        
        # validate CONFIG
        if "github" not in self.CONFIG and "gitlab" not in self.CONFIG and "bitbucket" not in self.CONFIG:
            print("Invalid config.py, check sample!")
            sys.exit(1)

        if os.path.exists("/Users/Philipp/"):
            self.DEBUG = True
            
        self._configureLogger()
        self._validateConfigFile()
        self._loadProtection()
        


    def _configureLogger(self):
        logPath = os.path.join(self.PROJECT_FOLDER, "Logs", "log.log")
        os.makedirs(os.path.join(self.PROJECT_FOLDER, "Logs"), exist_ok=True)
        
        while len(self.LOGGER.handlers) > 0:
            self.LOGGER.handlers.remove(self.LOGGER.handlers[0])
        
        STREAM_HANDLER = logger.StreamHandler(sys.stdout)
        self.LOGGER.addHandler(logger.configureHandler(_CustomWatchedFileHandler(logPath, encoding="utf-8"), _CustomFormatter()))
        self.LOGGER.addHandler(logger.configureHandler(STREAM_HANDLER, logger.logging.Formatter()))
        self.LOGGER.setLevel(logger.logging.DEBUG)
        
        if not self.DEBUG and "mailLogger" in self.CONFIG and not self.TESTING:
            self.MAIL_HANDLER = logger.configureHandler(self.CONFIG["mailLogger"], logger.PNMailLogFormatter(), logLevel=logger.logging.CRITICAL)
            self.LOGGER.addHandler(self.MAIL_HANDLER)


    def _loadProtection(self):
        protection = self.CONFIG.get("protection")
        
        if protection:
            username = protection.get("username")
            password = protection.get("password")
            cookie = protection.get("cookie")
            if not username or not password:
                # invalid configuration
                if not cookie:
                    self.LOGGER.critical("Invalid 'protection' dictonary, username or password is missing.")
                else:
                    self.LOGGER.warning("Invalid 'protection' dictonary, username or password is missing.")
                self.PROTECTION = None
            else:
                self.PROTECTION = protection
                
            if cookie:
                cookieVal = cookie.get("value")
                cookieName = cookie.get("name")
                
                if not cookieVal or not cookieName:
                    # invalid cookie configuration
                    if not self.PROTECTION:
                        self.LOGGER.critical("Invalid 'protection' cookie dictionary, name or value is missing.")
                    else:
                        self.LOGGER.warning("Invalid 'protection' cookie dictionary, name or value is missing.")
                        
                    self.PROTECTION_COOKIE = None
                else:
                    self.PROTECTION_COOKIE = cookie
                    
            if self.PROTECTION and not self.PROTECTION_COOKIE:
                self.LOGGER.info("Authentication for manual deployment only possible with username/password")
            elif self.PROTECTION_COOKIE and not self.PROTECTION:
                self.LOGGER.info("Authentication for manual deployment only possible with cookie")
        
    
    def _calcConfigHash(self):
        with open(self.configPath, "rb") as a:
            content = a.read()
            return hashlib.sha1(content).hexdigest()
            
            
    def _configNeedsReload(self):
        return self.configHash != self._calcConfigHash()
        
    def _validateConfigFile(self):
        validateConfig.LOGGER = self.LOGGER
        self.LOGGER.info("Validating config file...")
        try:
            validateConfig.main()
        except Exception as e:
            self.LOGGER.critical("Deployer terminates, because config file validation failed with reason: %s" % (str(e)))
            raise e

    def addTestSeq(self, seq):
        assert seq != 1
        
        if self.TESTING:
            self.TEST_SEQUENCE.add(seq)

    def reloadCONFIG(self):
        if self._configNeedsReload():
            self.configHash = self._calcConfigHash()
            
            self.LOGGER.debug("reload config")
            reload(config)
            self.CONFIG = config.CONFIG
            self._validateConfigFile()
            
            self._loadProtection()
            self._configureLogger()


CONTEXT = __Context()