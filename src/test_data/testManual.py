# coding=utf-8

from test_data.testBase import DeployerTestCase, verifyTEST_SEQUENCE
from unittest.mock import patch
from classes import TEST_SEQs
from context import CONTEXT
import test_data.config_test as config_test
import main
import os


class ManualTestCase(DeployerTestCase):
    @staticmethod
    def deployWrap(repo="TestRepo", branch="master", tag=None):
        main.deploy(repo, branch, tag)
    
    
    # standard cases
    @patch("main.request")
    def test_master(self, requestMock):
        # pull latest push@master
        requestMock.args = self.setupArgs()
        
        self.deployWrap()

        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_develop(self, requestMock):
        # pull latest push@develop
        requestMock.args = self.setupArgs()
        
        self.deployWrap(branch="develop")

        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-develop")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-develop"), self.latestPush_at_develop)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_noWhitelist(self, requestMock):
        # not on whitelist
        requestMock.args = self.setupArgs()
        
        self.deployWrap(branch="noWhitelist")

        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-noWhitelist")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_autoDeployConfigDisabled))
        
        
    @patch("main.request")
    def test_ignoreWhitelist(self, requestMock):
        # pulls latest push@noWhitelist
        requestMock.args = self.setupArgs(force=True)

        self.deployWrap(branch="noWhitelist")
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-noWhitelist")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-noWhitelist"), self.latestPush_at_noWhitelist)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_autoDeployConfigDisabledOW))




    # Release Only
    @patch("main.request")
    def test_releaseOnly(self, requestMock):
        # abort because of release only branch
        requestMock.args = self.setupArgs()
        
        self.deployWrap(branch=".Releases")

        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_tagRequiredNoTag))
        
    
    @patch("main.request")
    def test_releaseOnlyOW(self, requestMock):
        # pull latest push@master
        requestMock.args = self.setupArgs(ignoreRelease=True)
    
        self.deployWrap(branch=".Releases")
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_tagRequiredNoTagOW))

    @patch("main.request")
    def test_releaseOnlyNotNewestRelease(self, requestMock):
        # pull latest release
        requestMock.args = self.setupArgs()
    
        self.deployWrap(branch=".Releases", tag="dev18")
        
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), self.latestReleaseTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnown))
        
    @patch("main.request")
    def test_releaseOnlyNotNewestReleaseOW(self, requestMock):
        # pull specified tag
        requestMock.args = self.setupArgs(ignoreRelease=True)
    
        self.deployWrap(branch=".Releases", tag="dev18")
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), "dev18.txt")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnownOW))

    @patch("main.request")
    def test_releaseOnlyReleaseUnknown(self, requestMock):
        # abort latest release unknown on releaseOnly branch
        requestMock.args = self.setupArgs()
        
        config_test.CONFIG["github"]["username"] = "Kavakuosss"
        CONTEXT.CONFIG = config_test.CONFIG
    
        self.deployWrap(branch=".Releases", tag="dev18")
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.release_invalidCredentials, TEST_SEQs.dl_releaseOnlyRelUnknown))

    @patch("main.request")
    def test_releaseOnlyReleaseUnknownOW(self, requestMock):
        # pulls spevified tag
        requestMock.args = self.setupArgs(ignoreRelease=True)

        config_test.CONFIG["github"]["username"] = "Kavakuosss"
        CONTEXT.CONFIG = config_test.CONFIG
    
        self.deployWrap(branch=".Releases", tag="dev18")
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), "dev18.txt")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.release_invalidCredentials, TEST_SEQs.dl_releaseOnlyRelUnknownOW))




    # Tags Only
    @patch("main.request")
    def test_tagOnly(self, requestMock):
        # abort tagOnly Branch
        requestMock.args = self.setupArgs()
        
        self.deployWrap(branch=".Tags")
        
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_tagRequiredNoTag))

    @patch("main.request")
    def test_tagOnlyOW(self, requestMock):
        # pull latest push@master
        requestMock.args = self.setupArgs(ignoreTag=True)

        self.deployWrap(branch=".Tags")

        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_tagRequiredNoTagOW))
    
    @patch("main.request")
    def test_tagOnlyNotNewestTag(self, requestMock):
        # pull latest tag
        requestMock.args = self.setupArgs()
    
        self.deployWrap(branch=".Tags", tag="dev18")
        
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_notNewestTag))

    @patch("main.request")
    def test_tagOnlyNotNewestTagOW(self, requestMock):
        # pull specified tag
        requestMock.args = self.setupArgs(ignoreTagDate=True)
    
        self.deployWrap(branch=".Tags", tag="dev18")
        
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), "dev18.txt")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_notNewestTagOW))


    @patch("main.request")
    def test_latest(self, requestMock):
        # pull latest tag
        requestMock.args = self.setupArgs()
    
        self.deployWrap(branch=".Tags", tag="latest")
    
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_nwhTagLatest))


    @patch("main.request")
    def test_latestRelease(self, requestMock):
        # pull latest release
        requestMock.args = self.setupArgs()
    
        self.deployWrap(branch=".Tags", tag="latestRelease")
    
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestReleaseTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_nwhTagLatestRelease))