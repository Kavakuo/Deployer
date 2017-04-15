# coding=utf-8
from test_data.testBase import DeployerTestCase, verifyTEST_SEQUENCE
from unittest.mock import patch
from classes import TEST_SEQs
from context import CONTEXT
import test_data.config_test as config_test
import main
import os


class GitlabTestCase(DeployerTestCase):
    @staticmethod
    def setupHeaders(event):
        return {
            "X-Gitlab-Event": event
        }
    
    @staticmethod
    def getJson(event, repoName, branch="master", **kwargs):
        if event == "Push Hook":
            return {
                "repository": {
                    "name": repoName
                },
                "ref": "refs/heads/" + branch,
                **kwargs
            }
        elif event == "Tag Push Hook":
            return {
                "repository": {
                    "name": repoName
                },
                "object_kind": "tag_push",
                "ref": "refs/tags/"+kwargs["tag_name"]
            }
        
    def setupRequestMock(self, requestMock, event="Push Hook", repo="TestRepo-Gitlab", branch="master", **kwargs):
        requestMock.headers = self.setupHeaders(event)
        requestMock.get_data.return_value = ""
        requestMock.args = self.setupArgs()
        requestMock.get_json.return_value = self.getJson(event, repo, branch=branch, **kwargs)

    @patch("main.request")
    def test_push_master(self, requestMock):
        self.setupRequestMock(requestMock)
    
        main.gitlab()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Gitlab"), self.latestPush_at_master)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_develop(self, requestMock):
        self.setupRequestMock(requestMock, branch="develop")
    
        main.gitlab()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-develop")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Gitlab-develop"), self.latestPush_at_develop)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_push_noWhitelist(self, requestMock):
        self.setupRequestMock(requestMock, branch="noWhitelist")
    
        main.gitlab()
        self.assertTrue((not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-noWhitelist"))))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_autoDeployConfigDisabled))


    # release
    @patch("main.request")
    def test_push_releaseOnly(self, requestMock):
        self.setupRequestMock(requestMock, branch=".Releases")
    
        main.gitlab()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-Releases")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_releaseNotSupported))


    # tags
    @patch("main.request")
    def test_push_tagOnly(self, requestMock):
        self.setupRequestMock(requestMock, branch=".Tags")
    
        main.gitlab()
        self.assertTrue(not os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-Tags")))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_tagRequiredNoTag))

    @patch("main.request")
    def test_create_latestTag(self, requestMock):
        self.setupRequestMock(requestMock, event="Tag Push Hook", branch="master", tag_name=self.latestTag.replace(".txt", ""))
    
        main.gitlab()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Gitlab-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess))

    @patch("main.request")
    def test_create_notLatestTag(self, requestMock):
        self.setupRequestMock(requestMock, event="Tag Push Hook", branch="master", tag_name="dev18")
    
        main.gitlab()
        self.assertTrue(os.path.exists(self.pathRelativeToDeployPath("TestRepo-Gitlab-Tags")))
        self.assertTrue(os.path.exists(os.path.join(self.pathRelativeToDeployPath("TestRepo-Gitlab-Tags"), self.latestTag)))
        self.assertTrue(verifyTEST_SEQUENCE(TEST_SEQs.dl_deploySuccess, TEST_SEQs.dl_notNewestTag))