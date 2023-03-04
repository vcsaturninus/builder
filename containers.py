"""
Abstraction layer for interacting with varying container/jail OS technologies.
"""

from abc import ABC, abstractmethod
import os

import docker

import container

class Containers(ABC):
    @abstractmethod
    def image_exists(self, imgid):
        """
        Does the image with the specified id exist?
        An image is a class-like blob that containers can be instantiated from.
        """

    @abstractmethod
    def container_exists(self, contid):
        """
        Does the container with the specified id exist?
        """

    @abstractmethod
    def cp_from_img(self, imgid, src, dst):
        """
        Copy a file out of an image. Typically, files can be copied from containers but not 
        directly from images. Copying a file from an image therefore entails creating a throwaway
        container used just for the copy.
        """
    
    @abstractmethod
    def cp_from_container(self, contid, src, dst, remove_container=False):
        """
        Copy a file out of the specified container.
        """

    @abstractmethod
    def new_container(self):
        pass

    @abstractmethod
    def build_image(self, start_clean, container_config, tag=None, **kwargs):
        pass

class Docker_containers(Containers):
    def __init__(self, container_tech):
        self.api  = docker.client.from_env()
        self.tech = container_tech

    def image_exists(self, imgid):
        """
        True if the docker image with the specified id exists, else False.

        :param imgid    A docker image id or tag

        :return         Boolean indicating whether the image exists or not.
        :rtype          bool
        """
        client = self.api
        try:
            client.images.get(imgid)
        except docker.errors.ImageNotFound:
            return False
        else:
            return True

    def container_exists(self, contid):
        """
        True if the docker container with the specified id exists, else False.

        :param contid   A docker container id or name

        :return         Boolean indicating whether the container exists or not.
        :rtype          bool
        """
        client = self.api
        try:
            client.containers.get(contid)
        except docker.errors.NotFound:
            return False
        else:
            return True

    def cp_from_img(self, imgid, src, dst):
        """
        Create ephemeral container for copying single file/dir out of image.
        """
        if not self.image_exists(imgid):
            raise docker.errors.ImageNotFound

        client = self.api
        container = client.containers.run(command="bash", detach=True, auto_remove=False, image=imgid)
        bytes_, stats = container.get_archive(src)
        with open(dst, "wb") as tar:
            for byte in bytes_:
                tar.write(byte)
        container.stop()
        container.remove(force=True)
        return bytes_, stats

    def cp_from_container(self, contid, src, dst, remove_container=False):
        """
        Copy single file/dir out of existing (running or stopped) container.
        """
        if not self.container_exists(contid):
            raise docker.errors.NotFound
        client = self.api
        container = client.containers.get(contid)
        bytes_, stats = container.get_archive(src)
        with open(dst, "wb") as tar:
            for byte in bytes_:
                tar.write(byte)
        if remove_container:
            container.remove(force=True)
        return bytes_, stats

    def new_container(self, *args, **kwargs):
        return container.get(self.tech)(*args, **kwargs)

    def build_image(self, start_clean, container_config, tag=None, **kwargs):
        uds_uri = 'unix://var/run/docker.sock'
        docker_client = docker.APIClient(base_url=uds_uri)
        nocache = bool(start_clean)
        stream = docker_client.build(
            decode=True, # decode the stream to dictionaries on the fly
            tag = tag,
            path = container_config,
            buildargs = kwargs,
            nocache=nocache,
            network_mode='host',
            rm=True
            )
        for chunk in stream:
            if 'stream' in chunk:
                line=chunk['stream'].rstrip()
                if line:
                    yield line
 

class ImageNotFound(LookupError):
    pass

class ContainerNotFound(LookupError):
    pass


def inside_container():
    """
    True if currently running inside a container, else False.
    """
    return bool(os.getenv("INSIDE_CONTAINER"))

def get_interface_to(container_tech):
    known_tech = {"docker": Docker_containers}
    interface  = known_tech.get(container_tech)
    if not interface:
        raise NotImplementedError(f"No interface for '{container_tech}'")
    return interface(container_tech)

