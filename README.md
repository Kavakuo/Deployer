# Readme

Cloning is done by:  
`git clone -b [branch] git@github.com:Kavakuo/[repoName].git .`

Pulling is done by:  
`git clean -d -f && git reset --hard && git checkout "+ branch +" && git pull --rebase`

* Support for „reload“ and „setup“ script
  * setup is launched after cloning (only on first deployment)
  * reload is launched after pulling (for any other deployment)
* Select which branches should auto deploy
	* config.py file
	* put a disabled[-branchName] file into your repo
* Support for GitHub Push Events 
	* `/github` API Endpoint
* API to deploy manually
	* `/deploy/repoName[/branch[/tag]]` 