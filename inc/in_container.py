import os
import stat
import logging
from distutils.dir_util import copy_tree
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class in_container(Builder):
    def __init__(self, name="Run in Docker Container"):
        super().__init__(name)

        self.clearBuildPath = False

        self.requiredKWArgs.append("image")

        self.optionalKWArgs["cpus"] = 1
        self.optionalKWArgs["copy_env"] = []

        self.supportedProjectTypes = []

    # Required Builder method. See that class for details.
    def DidBuildSucceed(self):
        return True  # TODO: how would we even know?

    # Required Builder method. See that class for details.
    def Build(self):
        # Now, we should put us in self.buildPath.
        pass

    # Override of Builder method. See that class for details.
    def BuildNext(self):
        if (not hasattr(self, "ebbs_next")):
            logging.warn("No \"ebbs_next\" to run in container. Build process complete!")
            return

        logging.info("Setting up environment for containerized building.")
        envFile = self.CreateFile("host.env")
        for var in self.copy_env:
            envFile.write(f"{var}=\"{os.getenv(var)}\"\n")
        envFile.close()
        regDest = os.path.join(self.buildPath, os.path.basename(self.executor.defaultRepoDirectory))
        logging.debug(f"Copying {self.executor.defaultRepoDirectory} to {regDest}")
        copy_tree(self.executor.defaultRepoDirectory, regDest)
        for dir in self.executor.registerDirectories:
            if (not os.path.isdir(dir)):
                continue
            regDest = os.path.join(self.buildPath, os.path.basename(dir))
            logging.debug(f"Copying {dir} to {regDest}")
            copy_tree(dir, regDest)

        for nxt in self.ebbs_next:
            nxtPath = self.PrepareNext(nxt)
            os.chdir(nxtPath)
            logging.debug(f"Preparing to run ({nxt['build']}) in {nxtPath} within docker image {self.image}")
            runEBBSFileName = "run-ebbs.sh"
            runEBBS = self.CreateFile(runEBBSFileName)
            runEBBS.write(f"#!/bin/bash\n")
            # TODO: Support windows & bash-less linux.
            runEBBS.write(f"pip install ebbs\n")
            nxtBuildFolder = ""
            if ("build_in" in nxt):
                nxtBuildFolder = nxt['build_in']
            runEBBS.write(f"ebbs -v -b {nxt['build']} -i {nxtBuildFolder} . --event 'containerized'\n")
            # runEBBS.write(f"pwd; echo ''; ls; echo ''; ls {nxtPath}")
            runEBBS.close()
            os.chmod(runEBBSFileName, os.stat(runEBBSFileName).st_mode | stat.S_IEXEC)
            self.RunCommand(f"docker run                                       \
                --rm                                                           \
                -it                                                            \
                --mount type=bind,src={self.buildPath},dst=/mnt/env            \
                --mount type=bind,src={nxtPath},dst=/mnt/run                   \
                --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock\
                -w /mnt/run                                                    \
                --cpus {self.cpus}                                             \
                --entrypoint /mnt/run/run-ebbs.sh                              \
                --env-file {self.buildPath}/host.env                           \
                {self.image}                                                   \
            ")
            # Removed:
            #     --privileged                                                 \
            #     --user root                                                  \


