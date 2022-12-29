#!/usr/bin/python3

import os
import sys

import utils

def list_known_hooks(hooks_dir):
    return [x for x in os.listdir(hooks_dir) if os.path.isdir(hooks_dir+'/'+x)]


utils.STREAM_LOGGING_ON__ = bool(os.getenv("VERBOSE"))

hook = sys.argv[1] if len(sys.argv)>1 and sys.argv[1] else None

hooks_dir = os.path.dirname(os.path.realpath(__file__)) + '/'
hook_dir  = hooks_dir + hook
utils.log(f" ** Known hooks: {list_known_hooks(hooks_dir)}")

if not hook:
    utils.log("FATAL: Hook not specified")
elif not os.path.isdir(hook_dir):
    utils.log(f"Invalid hook: '{hook}'")
elif not utils.has_scripts(hook_dir):
    utils.log(f"WARNING: no scripts registered with hook '{hook}'")
else:
    utils.log(f" > Running scripts for hook '{hook}'")
    scripts = utils.get_sorted_script_list(hook_dir)
    for script in scripts:
        basename = os.path.basename(script)
        utils.log(f"Runninng {basename} [hook='{hook}']")
        utils.run( f"{script}", capture=not bool(os.getenv("VERBOSE")) )
