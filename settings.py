#!/usr/bin/python3

import os
import sys

import utils
import containers

class Pathmap():
    """
    This project operates, in terms of paths, in three distinct contexts:
    host, container, and a staging directory on the host that represents the base directory of
    a yet-to-be-built container image.

    There's a constant need to refer to the equivalent path in a different context i.e. say, the base
    directory on the host vs the base directory on the container vs the root staging directory.
    This leads to difficult-to-manage proliferation of duplicate variables:
    host_scripts_dir, container_scripts_dir, staging_dir_scripts etc.

    This class seeks to solve that problem: instead of creating new variables for each case, a path is
    added, stored, and retrieved contextually. Specifically, the path is sysrooted and prefixed according
    to the context it was added to and the parent path it was specified as being relative to.
    """
    def __init__(self):
        self.contexts = {}
        self.context = None
     
    def add_context(self, context, basedir, label='basedir'):
        self.contexts[context] = {}
        self.contexts[context]["basedir"] = { "path" : basedir, "parent": None}

    def set_current_context(self, context):
        if not context or context == 'all':
            raise ValueError(f"Invalid value for context: '{context}'")
        self.context = context

    def get_current_context(self):
        if not self.context:
            raise LookupError("No current context: none set yet")
        return self.context

    def check_context(self, context):
        if context != 'all' and not self.contexts.get(context):
            raise LookupError(f"Unknown context: '{context}'")

    def get(self, context, label, nothrows=False):
        self.check_context(context)
        if not self.contexts[context].get(label):
            if nothrows:
                return False
            raise LookupError(f"No such path '{label}' in context '{context}'")
        pathconf = self.contexts[context][label]
        path    = pathconf["path"]
        if not pathconf.get('isfile'):
            path = utils.ensure_dir_semantics(path)
        parent  = pathconf.get('parent')
        if parent:
            path = self.get(context=context, label=parent) + path
        return path

    def set(self, context, label, path, relativeto=None, isfile=False):
        listspec = context.split(';')
        for context in listspec:
            self.check_context(context)
            contexts = self.contexts if context=='all' else {context : self.contexts[context]}
            for paths in contexts.values():
                paths[label] = {"path" : path, "parent": relativeto, "isfile": isfile}
    
    def clone(self, context=None):
        clone = Pathmap()
        clone.context  = context or self.context
        clone.contexts = self.contexts
        return clone

    def __getattr__(self, path):
        return self.get(context=self.context, label=path)

def set_paths(target):
    paths = Pathmap()
    paths.add_context("host", basedir=utils.get_project_root())
    paths.add_context("container", basedir="/home/dev/base")
    paths.add_context("staging", basedir=paths.get("host", "basedir") + '/staging')
    paths.set_current_context('container' if containers.inside_container() else 'host')

    paths.set(context='container', label='home', path='/home/dev', relativeto=None)
    paths.set(context='all', label='tmpdir', path='.tmp', relativeto='basedir')
    paths.set(context='all', label='specs', path='spec', relativeto='basedir')
    paths.set(context='all', label='tgroot', path='targets', relativeto='specs')
    paths.set(context='all', label='target', path=target, relativeto='tgroot')
    paths.set(context='all', label='tgspec', path=f"{target}_spec.json", relativeto='target', isfile=True)
    paths.set(context='all', label='schemas', path='json_schema', relativeto='specs')
    paths.set(context='all', label='steps_dir', path='steps', relativeto='specs')
    paths.set(context='all', label='common', path='common', relativeto='tgroot')
    paths.set(context='host', label='outdir', path='out', relativeto='basedir')
    paths.set(context='container', label='outdir', path='out', relativeto='home')
    paths.set(context='container', label='sdk_path', path=paths.get("container", "home"), relativeto=None)
    paths.set(context='all', label='pkg_outdir', path='package', relativeto='outdir')
    paths.set(context='all', label='pkg_outdir', path='package', relativeto='outdir')
    paths.set(context='host', label='timestamp', path='timestamp', relativeto='tmpdir', isfile=True)
    paths.set(context='all', label='automated_build_steps', path='automated_build.json', relativeto='steps_dir', isfile=True)
    paths.set(context='all', label='dev_build_steps', path='dev_build.json', relativeto='steps_dir', isfile=True)
    paths.set(context='host', label='buildlog', path='build.log', relativeto='tmpdir', isfile=True)
    paths.set(context='all', label='env_defaults', path='specs/environment.json', relativeto='common', isfile=True)
    paths.set(context='host', label='devconfig', path='developer.json', relativeto='basedir', isfile=True)
    paths.set(context='host', label='sdk_path', path='.', relativeto='basedir')
    paths.set(context='host', label='depends', path='depends', relativeto='specs')
    paths.set(context='host', label='common_scripts', path='scripts', relativeto='common')
    paths.set(context='host', label='common_hooks', path='hooks', relativeto='common_scripts')
    paths.set(context='host', label='common_files', path='files', relativeto='common')
    paths.set(context='host', label='target_scripts', path='scripts', relativeto='target')
    paths.set(context='host', label='target_hooks', path='hooks', relativeto='target_scripts')
    paths.set(context='host', label='target_files', path='files', relativeto='target')
    paths.set(context='container', label='filestore', path=paths.get("container", "basedir"), relativeto=None)
    paths.set(context='host', label='filestore', path=paths.get("staging", "basedir"), relativeto=None)
    paths.set(context='host', label='staging', path=paths.get("staging", "basedir"), relativeto=None)
    paths.set(context='all', label='system_configs', path="files/system_configs", relativeto='filestore')
    paths.set(context='all', label='sdk_configs', path="files/sdk_configs", relativeto='filestore')

    paths.set(context='staging;container', label='files', path='files', relativeto='basedir')
    paths.set(context='staging;container', label='scripts', path='scripts', relativeto='basedir')
    paths.set(context='staging;container', label='hooks', path='hooks', relativeto='scripts')
    paths.set(context='staging;container', label='depends', path='depends', relativeto='basedir')
    return paths


# user to build as inside the container
build_user = 'dev'
# container technology used: e.g. docker, lxc, lxd, bsd jails etc
container_technology = 'docker'

