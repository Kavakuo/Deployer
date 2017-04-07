# Readme

Cloning is done with:  
`git clone -b [branch] git@github.com:Kavakuo/[repoName].git .`

Pulling is done with:
```
git clean -d -f     # cleans all files and directories except paths in ignore file
git reset --hard
git checkout BRANCH
git fetch
git reset --hard origin/BRANCH

git checkout TAG    # optional
```

## Features
* Support for `reload` and `setup` script
    * `setup` is launched after cloning (only on first deployment)
    * `reload` is launched after pulling (for any other deployment)
    * Both scripts take two arguments the current BranchName and the Host field from the HTTP request header
* Option to auto deploy only releases.
* Select which branches should auto deploy.
    * `config.py` file
    * Put a `disabled[-branchName]` file into your repo to disable auto deploy.
* Support for GitHub Push and Release Webhooks
    * `/github` API Endpoint
* API to deploy manually
    * `/deploy/repoName[/branch[/tag]]`
    * `tag` could be `latest` to deploy the latest release


## config.py
Rename `config_sample.py` to `config.py` after cloning!

```
{
    "REPO_NAME": {
        "whitelistedBranches":["master", "develop"],
        "blacklistedBranches":["feature"],
        "releasesOnly": {
            "master":True
        }
    },
    "mailLogger": logging.handlers.SMTPHandler(),
    "deployPath": "/home/kavakuo/GitProjects/",
    "gitBaseUrl": "git@github.com:Kavakuo/",
    "hmacSecret": b"secret"
}
```

* `REPO_NAME: Dictionary`
    * `whitelistedBranches: list[str]`  
    Only auto deploy on new pushs/releases on branches in this list. \*
    * `blacklistedBranches: list[str]`  
    Do not auto deploy on new pushs/releases on branches in this list. \*
    * `releasesOnly: Bool or Dictionary`  
    Auto deploy only on new releases. Use a bool to specify this behaviour for all branches. Or a dict with branchnames as keys. Default is false!
* `mailLogger: logging.handlers.SMTPHandler()`  
[SMTPHandler()](https://docs.python.org/3.6/library/logging.handlers.html#logging.handlers.SMTPHandler) logging handler, to send you mails on certain events.
* `deployPath: String`  
Use this to specifiy the parent folder for the deployment. Repos are located at `[deployPath]/[REPO_NAME]-[BRANCH]`.
* `gitBaseUrl: String`  
Just change your Username. Uses `ssh` protocol by default to access the repos.
* `hmacSecret: bytes`  
The secret key to verify the itegrity and authentication of the GitHub Messages.

\* Every entry in this list is handled as regex. It is matched with `re.compile(entry).match(branch)`. [\[Documentation\]](https://docs.python.org/3.6/library/re.html#re.match)

