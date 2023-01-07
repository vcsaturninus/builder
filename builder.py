#!/usr/bin/python3

"""
Copyright (c) 2022, vcsaturninus -- vcsaturninus@protonmail.com
"""

import argparse
import os
import sys
import shutil

import utils
import containers
import sdk
import settings

def clean_up_paths(paths):
    for path in paths:
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)

def load_known_targets(tgroot):
    """
    List targets that are currently supported i.e. can be built.
    """
    return {x : True for x in os.listdir(tgroot) if os.path.isdir(tgroot + "/" + x) and x != "common"}

def print_known_targets(tgroot):
    targets = load_known_targets(tgroot).keys()
    if not len(targets):
        print("No support for any targets")
    else:
        print("Supported targets:")
        for tg in targets:
            print(f"\t ** {tg}")

def is_known_target(target):
    return bool(load_known_targets(tgroot).get(target))

def validate_json_files(ignore_missing_specs):
    paths = { "steps" : steps_dir, "common" : tgroot + "common/specs/" }
    for key,path in paths.items():
        print(f"Validating {key} specs ...")
        for file in os.listdir(path):
            subject = path + file
            utils.validate_json_against_schema(subject, schemas_dir)
            print(f" # {subject} : valid.")

    print("Validating target specs ...")
    for directory in os.listdir(tgroot):
        if directory != "common":
            tgspec = f"{directory}_spec.json"
            subject = tgroot + directory + "/" + tgspec
            if not os.path.isfile(subject):
                print(f"Target {directory} missing '{tgspec}'")
                if not ignore_missing_specs:
                    raise FileNotFoundError
            else:
                utils.validate_json_against_schema(subject, schemas_dir)
                print(f" # {subject} : valid.")

    if developer_config:
        print(f"Validating {developer_config} ...")
        subject = developer_config
        utils.validate_json_against_schema(subject, schemas_dir)
        print(f" # {subject} : valid.")

def dispatch_tasks(tasks, context):
    for task in tasks:
        task,ctx = task.popitem()
        if ctx == context:
            utils.log(f" > Step: {task} [{context}]")
            sdk.execute_task(task)

def load_env_defaults():
    j = utils.load_json_from_file(env_defaults_file)
    return j["variables"]

def load_env_overrides():
    env = {}
    if not developer_config:
        return env
    j = utils.load_json_from_file(developer_config)
    env = j["environment"]["variables"]
    return env

def load_mount_overrides():
    mounts = []
    if not developer_config:
        return mounts
    j = utils.load_json_from_file(developer_config)
    # convert to list of three-tuples as expected by sdk class
    # all target mounts are relative to the container home dir
    # unless the first character is a '/'
    prefix = paths.get('container', 'home')
    for label, spec in j["mounts"].items():
        target_path = spec['target']
        if not os.path.isabs(target_path):
            target_path = prefix + target_path
        mounts.append( (spec['source'], target_path, spec['type']) )
    return mounts

def load_mount_defaults():
    """ Currently unused """
    return []

def sanitize_cli(argv):
    unsane = False
    if argv.verbose and argv.quiet:
        print("Nonsensical argument combination of '--verbose' and '--quiet'")
        unsane=True
    if unsane:
        raise ValueError("Invalid command line")

parser = argparse.ArgumentParser(description='Build SDK automaton')
parser.add_argument('-d',
                     '--devbuild-with-host-mounts',
                     action='store_true',
                     dest='devbuild',
                     help="Perform build in directory mounted from host and store artifcats there. \
                             Useful for 'dev' containers"
                     )

parser.add_argument('-t',
                     '--target',
                     metavar='PLATFORM',
                     dest='target',
                     help='Target platform to build for'
                     )

parser.add_argument('-q',
                    '--quiet',
                     action='store_true',
                     dest='quiet',
                     help='Do not print verbose/diagnostic messages'
                     )

parser.add_argument('-v',
                    '--verbose',
                     action='store_true',
                     dest='verbose',
                     help="Print verbose/diagnostic messages when they've been silenced"
                     )

parser.add_argument('--clean',
                     action='store_true',
                     dest='clean',
                     help='Start clean'
                     )

parser.add_argument('--validate',
                     action='store_true',
                     dest='validate_jsons',
                     help='Validate all json files against their schemas'
                     )

parser.add_argument('--list-targets',
                     action='store_true',
                     dest='list_targets',
                     help='List currently supported targets'
                     )

parser.add_argument("--cores",
                    action='store',
                    dest='num_build_cores',
                    help='Number of processor cores to use for the build (default=1)'
                    )

parser.add_argument("--build-firmware",
                    action='store_true',
                    dest='only_firmware',
                    help='Build full firmware using prebuilt sdk infrastructure'
                    )

parser.add_argument("--build-package",
                    action='store',
                    dest='only_packages',
                    nargs='*',
                    metavar='PACKAGE',
                    help='Build only specified package(s) and retrieve artifact(s). \
                            Assumes firmware has already been built'
                    )

parser.add_argument("--container",
                    action='store_true',
                    dest='container',
                    help='create and attach to an appropriate container. the container is not \
                            removed automatically on exit unless --ephemeral is specified too.'
                    )

parser.add_argument("--ephemeral",
                    action='store_true',
                    dest='ephemeral',
                    help='if --container is specified, make the container emphemeral i.e. the container \
                            will be automatically removed on exit so the user does not have to bother.'
                    )

parser.add_argument("--devconfig",
                    action='store',
                    metavar='<config>.json',
                    dest='devconfig',
                    help='Absolute path to file to use for the developer config rather than the default'
                    )

parser.add_argument("--stage",
                    action='store_true',
                    dest='populate_staging',
                    help='Populate the staging directory and do nothing else.'
                    )

print(f" ** Invocation: {sys.argv}", flush=True)
os.chdir(utils.get_project_root())
args = parser.parse_args()
sanitize_cli(args)

# guards for certain actions and prints
build_mode  = not (args.populate_staging or args.container or args.list_targets or args.validate_jsons)

interactive = args.container
# excessive verbosity is inconvenient by default
verbose    = not args.quiet and (build_mode or args.verbose)
utils.set_logging(tostdout=verbose, tofile=not containers.inside_container())
restricted_build   = args.only_packages or args.only_firmware

paths              = settings.set_paths(args.target)
start_clean        = args.clean
steps_file         = paths.dev_build_steps if args.devbuild else paths.automated_build_steps
sdk_build_type     = "dev" if args.devbuild else "automated"
num_build_cores    = args.num_build_cores or 1
schemas_dir        = paths.schemas
steps_dir          = paths.steps_dir
env_defaults_file  = paths.env_defaults
tgroot             = paths.tgroot
developer_config   = args.devconfig if args.devconfig else paths.get(paths.get_current_context(), 'devconfig', True)
developer_config   = developer_config if os.path.isfile(developer_config) else None
if developer_config and ((build_mode or interactive) and sdk_build_type != 'dev'):
    raise ValueError("Developer configs can only be used for dev containers")

if args.list_targets:
    print_known_targets(paths.tgroot)
elif args.validate_jsons:
    validate_json_files(ignore_missing_specs=False)
else:
    target = args.target.lower() if args.target else None
    if not target:
        print("Mandatory argument not specified: '-t|--target'")
        sys.exit(13)
    elif not is_known_target(target):
        print_known_targets(paths.tgroot)
        raise LookupError(f"Target specified ('{target}') not supported")
    
    paths_to_clean = [paths.tmpdir]
    if not interactive:
        paths_to_clean.append(paths.outdir)
    clean_up_paths(paths_to_clean)
    utils.log(f" > Cleaning up {paths_to_clean}")

    utils.log(f" ** SDK type:   '{sdk_build_type}'")
    utils.log(f" ** SDK target: '{target}'")

    tgspec_file = paths.tgspec
    tgspec_file = paths.tgroot + f"{target}/{target}_spec.json"

    utils.log(f" > Validating {tgspec_file} against schema ...")
    tgspec = utils.validate_json_against_schema(tgspec_file, schemas_dir)

    utils.log(f" > Validating {steps_file} against schema ...")
    steps  = utils.validate_json_against_schema(steps_file, schemas_dir)
    
    if developer_config:
        utils.log(f" > Validating {developer_config} against schema ...")
        utils.validate_json_against_schema(developer_config, schemas_dir)

    confvars = {
            'sdk_build_type'    : sdk_build_type,
            'num_build_cores'   : str(num_build_cores),
            'start_clean'       : start_clean,
            'verbose'           : verbose,
            "build_artifacts_archive_name": tgspec["build_artifacts_archive_name"],
            "build_user"        : settings.build_user,
            "container_tech"    : settings.container_technology,
            "env_defaults"      : load_env_defaults(),
            "env_overrides"     : load_env_overrides(),
            "mount_defaults"    : load_mount_defaults(),
            "mount_overrides"   : load_mount_overrides(),
            "builder_entrypoint": utils.get_last_path_component(__file__)
            }

    sdk = sdk.get_sdk_for(target)(tgspec, paths, confvars)
    utils.log(f" ** steps: {steps['steps']}", cond=(build_mode and not restricted_build))
    utils.log(f" ** environment: {sdk.get_env_vars(inherit=False)}")
    utils.log(f" ** mounts: {sdk.get_mounts(validate=False)}")
    utils.log(f" ** confvars: {confvars}")

    if args.only_packages:
        sdk.build_single_packages(args.only_packages)
        sdk.retrieve_build_artifacts(paths.get('container', 'pkg_outdir'))
    elif args.only_firmware:
        sdk.build_only_firmware()
        sdk.retrieve_build_artifacts(paths.get('container', 'outdir'))
    elif args.container:
        sdk.get_interactive_container(ephemeral=args.ephemeral)
    elif args.populate_staging:
        sdk.populate_staging_dir()
    else: # full sdk build
        tasks=steps["steps"]
        context = paths.get_current_context()
        dispatch_tasks(tasks, context)

