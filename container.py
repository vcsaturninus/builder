"""
Abstraction layer for interacting with varying container/jail OS technologies.
"""

from abc import ABC, abstractmethod
import os

import docker

import utils

class Container(ABC):
    @abstractmethod
    def set_mount_configs(self, mounts):
        """
        Make the container object aware of any directories or files that must be mounted.
        :param mounts    a list of tuples, where each tuple if of the form:
                         (<host path>, <container path>, <mount type>). The type parameter 
                         (and whether it's required) depends on the container technology.
        """

    @abstractmethod
    def run(self, cmd, interactive=False, ephemeral=False):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def wait(self):
        pass

    @abstractmethod
    def id(self):
        pass

    @abstractmethod
    def destroy(self):
        pass

    @abstractmethod
    def logs(self):
        pass

class Docker(Container):
    def __init__(self, img, env=None, interactive=False, ephemeral=False):
        self.client     = docker.client.from_env()
        self.container  = None
        self.image      = img
        self.mounts     = []
        self.mount_tuples = []
        self.env        = env or {}
        self.interactive = interactive
        self.ephemeral  = ephemeral
        self.exited    = False
        self.exitcode  = 0

    def set_mounts(self, mounts):
        for host_path, container_path, mount_type in mounts:
            mount = docker.types.Mount(
                    source=host_path,
                    target=container_path,
                    type=mount_type
                    )
            self.mounts.append(mount)
        self.mount_tuples=mounts
        return mounts
    
    def interact(self, cmd):
        """
        There's no simple way to get a cli-interactive container instance via the python API.
        As such,  we'll need to call the docker cli client instead in a subprocesss.
        """
        cli = f"docker run {'--rm' if self.ephemeral else ''} --net=host"
        for k,v in self.env.items():
            cli += f" -e '{k}={v}'"
        for host_path,container_path,mount_type in self.mount_tuples:
            cli += f" --mount type='{mount_type}',source='{host_path}',target='{container_path}'"
        cli += f" -it {self.image} {cmd}"

        rc = utils.interact(cli)
        self.exited=True
        self.exitcode = rc

    def run(self, cmd):
        if self.interactive:
            return self.interact(cmd)
        client = self.client
        mounts = self.mounts
        container = client.containers.run(
                image=self.image,
                command=cmd,
                environment=self.env,
                mounts = mounts,
                detach=True,
                network_mode='host'
                )
        self.container = container
    
    def logs(self):
        if self.interactive:
            raise RuntimeError("Interactive containers do not return logs")
        logs = self.container.logs(stream=True)
        for log in logs:
            yield log.decode('utf8').rstrip()
    
    def wait(self):
        if self.exited:
            return self.exitcode
        status = self.container.wait()
        return (status['StatusCode'])

    def id(self):
        return self.container.id

    def destroy(self):
        pass

    def stop(self):
        pass
    
    def start(self):
        pass

    def set_mount_configs(self):
        pass


def get(container_tech):
    known_tech = {"docker": Docker}
    interface  = known_tech.get(container_tech)
    if not interface:
        raise NotImplementedError(f"No interface for '{container_tech}'")
    return interface
