# coding=utf-8

from test_data.testBase import DeployerTestCase, verifyTEST_SEQUENCE
from unittest.mock import patch
from classes import TEST_SEQs
from context import CONTEXT
import test_data.config_test as config_test
import main
import os


class GitHubTestCase(DeployerTestCase):
    @staticmethod
    def setupHeaders(event):
        return {
            "User-Agent": "GitHub-Hookshot/a837270",
            "X-GitHub-Delivery": "0aa67100-1b16-11e7-8bbf-ee052e733e39",
            "X-GitHub-Event": event
        }
    
    @staticmethod
    def getJson(event, repoName, branch="master", **kwargs):
        if event == "push":
            return {
                "repository": {
                    "name":repoName
                },
                "ref":"refs/heads/"+branch,
                **kwargs
            }
        elif event == "release":
            return {
                "repository": {
                    "name": repoName
                },
                "release": {
                    "tag_name": kwargs["tag_name"]
                }
            }
        elif event == "create":
            return {
                "repository": {
                    "name": repoName
                },
                "ref_type":"tag",
                "ref":kwargs["tag_name"]
            }
        

    def setupRequestMock(self, requestMock, event="push", repo="TestRepo", branch="master", **kwargs):
        requestMock.headers = self.setupHeaders(event)
        requestMock.get_data.return_value = ""
        requestMock.args = self.setupArgs()
        requestMock.get_json.return_value = self.getJson(event, repo, branch=branch, **kwargs)
    
    @patch("main.request")
    def test_push_master(self, requestMock):
        self.setupRequestMock(requestMock)
        
        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_develop(self, requestMock):
        self.setupRequestMock(requestMock, branch="develop")
    
        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-develop")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-develop"), self.latestPush_at_develop)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_noWhitelist(self, requestMock):
        self.setupRequestMock(requestMock, branch="noWhitelist")
    
        main.github()
        self.assertTrue((not os.path.exists(self.pathRelativeToDeployPath("TestRepo-noWhitelist"))))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_autoDeployConfigDisabled))

    @patch("main.request")
    def test_push_overwrite(self, requestMock):
        self.setupRequestMock(requestMock, branch="noWhitelist")
        requestMock.args = self.setupArgs(force=True)
        
        # overwriting not allowed with webhook
        main.github()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-noWhitelist")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_whQueryNotAllowed))

    @patch("main.request")
    def test_push_releaseOnly(self, requestMock):
        self.setupRequestMock(requestMock, branch=".Releases")
    
        main.github()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_releaseOnlyNoRelease))

    @patch("main.request")
    def test_push_tagOnly(self, requestMock):
        self.setupRequestMock(requestMock, branch=".Tags")
    
        main.github()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_tagRequiredNoTag))





    # releases
    @patch("main.request")
    def test_release_newest(self, requestMock):
        self.setupRequestMock(requestMock, event="release", branch="master", tag_name=self.latestReleaseTag.replace(".txt", ""))
        
        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), self.latestReleaseTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_release_notNewest(self, requestMock):
        self.setupRequestMock(requestMock, event="release", branch="master", tag_name="dev18")
    
        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Releases"), self.latestReleaseTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_releaseOnlyNotLatestRelRelKnown))


    @patch("main.request")
    def test_release_releaseUnknown(self, requestMock):
        self.setupRequestMock(requestMock, event="release", branch="master", tag_name="dev18")
        
        config_test.CONFIG["github"]["username"] = "Kavakuosss"
        CONTEXT.CONFIG = config_test.CONFIG
        
        main.github()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.release_invalidCredentials, TEST_SEQs.dl_releaseOnlyRelUnknown))



    # create
    @patch("main.request")
    def test_create_latestTag(self, requestMock):
        self.setupRequestMock(requestMock, event="create", branch="master", tag_name=self.latestTag.replace(".txt", ""))

        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_create_notLatestTag(self, requestMock):
        self.setupRequestMock(requestMock, event="create", branch="master", tag_name="dev18")

        main.github()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_notNewestTag))