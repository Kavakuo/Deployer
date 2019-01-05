# coding=utf-8
import unittest, shutil, os, logging
from context import CONTEXT, reload
import test_data.config_test as config_test

def verifyTEST_SEQUENCE(*args):
    sequence = CONTEXT.TEST_SEQUENCE
    noError = True
    
    for a in args:
        try:
            sequence.remove(a)
        except KeyError:
            noError = False
            CONTEXT.LOGGER.warning("CONTEXT.TEST_SEQUENCE missing key: " + a)
    
    if len(sequence) > 0:
        CONTEXT.LOGGER.warning("Additional keys in CONTEXT.TEST_SEQUENCE: %s" % ', '.join(sequence))
        return False
    
    return noError


class DeployerTestCase(unittest.TestCase):
    def __init__(self, methodname='runTest'):
        self.latestPush_at_master = "dev24.txt"
        self.latestPush_at_develop = "dev30.txt"
        self.latestPush_at_noWhitelist = "dev6.txt"
        self.latestReleaseTag = "dev22.txt"
        self.latestTag = "dev23.txt"
        
        CONTEXT.TESTING = True
        CONTEXT.reloadCONFIG = lambda: None
    
        for handler in CONTEXT.LOGGER.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.INFO)
        
        super(DeployerTestCase, self).__init__(methodName=methodname)
    
    def setUp(self):
        shutil.rmtree(os.path.realpath(config_test.CONFIG["github"]["deployPath"]), True)
        CONTEXT.TEST_SEQUENCE = set()
        
        # reload config_test file to undo testing manipulations
        reload(config_test)
        CONTEXT.CONFIG = config_test.CONFIG
        CONTEXT._loadProtection()
        pass
    
    def tearDown(self):
        pass
    
    @staticmethod
    def setupArgs(force=False, ignoreRelease=False, ignoreTagDate=False, ignoreTag=False):
        return {
            "force": force,
            "ignoreRelease": ignoreRelease,
            "ignoreTagDate": ignoreTagDate,
            "ignoreTag":ignoreTag
        }
    
    @staticmethod
    def pathRelativeToDeployPath(path):
        ret = os.path.join(os.path.realpath(config_test.CONFIG["github"]["deployPath"]), path)
        return ret