import os
import stat
import logging
from distutils.dir_util import copy_tree
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class in_container(Builder):
    def __init__(this, name="Run in Docker Container"):
        super().__init__(name)

        this.clearBuildPath = False

        this.requiredKWArgs.append("image")
        this.requiredKWArgs.append("next")

        this.optionalKWArgs["cpus"] = 1
        this.optionalKWArgs["copy_env"] = []

        this.supportedProjectTypes = []

    # Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        return True  # TODO: how would we even know?

    # Required Builder method. See that class for details.
    def Build(this):
        # Now, we should put us in this.buildPath.
        pass

    # Override of Builder method. See that class for details.
    def BuildNext(this):
        if (not hasattr(this, "next")):
            logging.warn("No \"next\" to run in container. Build process complete!")
            return

        logging.info("Setting up environment for containerized building.")
        envFile = this.CreateFile("host.env")
        for var in this.copy_env:
            envFile.write(f"{var}=\"{os.getenv(var)}\"\n")
        envFile.close()
        regDest = os.path.join(this.buildPath, os.path.basename(this.executor.defaultRepoDirectory))
        logging.debug(f"Copying {this.executor.defaultRepoDirectory} to {regDest}")
        copy_tree(this.executor.defaultRepoDirectory, regDest)
        for dir in this.executor.registerDirectories:
            if (not os.path.isdir(dir)):
                continue
            regDest = os.path.join(this.buildPath, os.path.basename(dir))
            logging.debug(f"Copying {dir} to {regDest}")
            copy_tree(dir, regDest)

        for nxt in this.next:
            nxtPath = this.PrepareNext(nxt)
            os.chdir(nxtPath)
            logging.debug(f"Preparing to run ({nxt['build']}) in {nxtPath} within docker image {this.image}")
            runEBBSFileName = "run-ebbs.sh"
            runEBBS = this.CreateFile(runEBBSFileName)
            runEBBS.write(f"#!/bin/bash\n")
            # TODO: Support windows & bash-less linux.
            runEBBS.write(f"pip install eons\n")
            runEBBS.write(f"pip install ebbs\n")
            runEBBS.write(f"pip install eot\n")
            nxtBuildFolder = ""
            if ("build_in" in nxt):
                nxtBuildFolder = nxt['build_in']
            events = this.events
            events.add("containerized")
            eventStr = ""
            for e in events:
                eventStr += f" --event {e}"
            runEBBS.write(f"ebbs -v . -b {nxt['build']} --name {this.projectName} --type {this.projectType} {eventStr} \n")
            # runEBBS.write(f"pwd; echo ''; ls; echo ''; ls {nxtPath}")
            runEBBS.close()
            os.chmod(runEBBSFileName, os.stat(runEBBSFileName).st_mode | stat.S_IEXEC)
            this.RunCommand(f'''docker run \
--rm \
--mount type=bind,src={this.buildPath},dst=/mnt/env \
--mount type=bind,src={nxtPath},dst=/mnt/run \
--mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
-w /mnt/run \
--cpus {this.cpus} \
--entrypoint /mnt/run/run-ebbs.sh \
--env-file {this.buildPath}/host.env \
{this.image}
''')