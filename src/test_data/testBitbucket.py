# coding=utf-8
from test_data.testBase import DeployerTestCase, verifyTEST_SEQUENCE
from unittest.mock import patch
from classes import TEST_SEQs
from context import CONTEXT
import test_data.config_test as config_test
import main
import os


class BitbucketTestCase(DeployerTestCase):
    @staticmethod
    def setupHeaders(event):
        return {
            "X-Event-Key": event,
            "X-Request-UUID":"",
            "X-Hook-UUID":""
        }
    
    @staticmethod
    def getJson(type, repoName, name="master"):
        return {
            "repository": {
                "name": repoName
            },
            "new": {
                "type":type,
                "name":name
            }
        }
        
    def setupRequestMock(self, requestMock, type="branch", repo="TestRepo-Bitbucket", name="master"):
        requestMock.headers = self.setupHeaders("repo:push")
        requestMock.get_data.return_value = ""
        requestMock.args = self.setupArgs()
        requestMock.get_json.return_value = self.getJson(type, repo, name=name)

    @patch("main.request")
    def test_push_master(self, requestMock):
        self.setupRequestMock(requestMock)
    
        main.bitbucket()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Bitbucket"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_develop(self, requestMock):
        self.setupRequestMock(requestMock, name="develop")
    
        main.bitbucket()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-develop")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Bitbucket-develop"), self.latestPush_at_develop)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_noWhitelist(self, requestMock):
        self.setupRequestMock(requestMock, name="noWhitelist")
    
        main.bitbucket()
        self.assertTrue((not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-noWhitelist"))))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_autoDeployConfigDisabled))


    # release
    @patch("main.request")
    def test_push_releaseOnly(self, requestMock):
        self.setupRequestMock(requestMock, name=".Releases")
    
        main.bitbucket()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_releaseNotSupported))


    # tags
    @patch("main.request")
    def test_push_tagOnly(self, requestMock):
        self.setupRequestMock(requestMock, name=".Tags")
    
        main.bitbucket()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Tags")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_tagRequiredNoTag))

    @patch("main.request")
    def test_create_latestTag(self, requestMock):
        self.setupRequestMock(requestMock, type="tag", name=self.latestTag.replace(".txt", ""))
    
        main.bitbucket()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_create_notLatestTag(self, requestMock):
        self.setupRequestMock(requestMock, type="tag", name="dev18")
    
        main.bitbucket()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Bitbucket-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_notNewestTag))


    @patch("main.request")
    def test_manualWrongApi(self, requestMock):
        # repo not found, using github default API
        main.deploy("TestRepo-Bitbucket")
        
        self.assertTrue(verifyTEST_SEQUENCE())

    @patch("main.request")
    def test_manualNoApi(self, requestMock):
        config_test.CONFIG.pop("defaultApi", None)
        CONTEXT.CONFIG = config_test.CONFIG
        
        main.deploy("TestRepo-Bitbucket")
    
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.deploy_repoConfigNoApi))