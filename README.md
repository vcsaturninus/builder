# builder

Generic sdk builder for automatic and 'dev' containizer builds

 * [Problem Statement](#problem-statement)
    * [Automation](#automation)
    * [Development setups](#development-setups)
 * [Overview](#overview)
    * [Main Script and Target Specification](#main-script-and-target-specification)
    * [Automated and Development Setups](#automated-and-development-setups)
    * [Containers and Container Images and Saving Time](#containers-and-container-images-and-saving-time)
    * [Container Image Tags](#container-image-tags)
    * [Build Artifacts](#build-artifacts)
    * [Interactive Containers](#interactive-containers)
 * [Adding New Targets](#adding-a-new-target)
    * [Common and target-specific files and scripts](#common-and-target-specific-files-and-scripts)
    * [Build stages, scripts, and hooks](#build-stages-scripts-and-hooks)
 * [Development SDK setups](#development-sdk-setups)
    * [Full SDK builds and restricted builds](#full-sdk-builds-and-restricted-builds)
    * [Interactive containers and developer.json](#interactive-containers-and-developerjson)
 * [Notes](#notes)

--------------------------------------------------------------------

## Problem Statement

### Automation

The main challenge to automation is improper design through a setup that is not extendible.
Specifically, given two platforms (_targets_) that use the same SDK e.g.
_OpenWrt_ to build their artifacts they might employ **many** specifics. If the
setup is designed and _works_ for the first platform, it will often necessitate
a complete redo to make it work for the second one ([1](#notes)).

Certain platforms have subcomponents that are built using _different_ SDKs.
However, typically there's _main_ sdk that builds the main outputs of interest,
while the others are only needed for building certain components e.g. frontend
files, Linux kernel etc. The other, secondary, SDKs can therefore simply be hooked in at
various stages when building the primary SDK e.g. _OpenWrt_ or _Yocto_.

The solution offered relies on the fact that no matter the sdk, however
many specifics and differences there may be, settings it up typically follows
this rough outline:
 * configure the system (e.g. install dependencies)
 * clone the SDK project
 * configure the SDK (e.g. restore backed-up configuration files)
 * perform preparatory steps for imminent build
 * perform build
 * perform post-build steps e.g. retrieving build artifacts

This is what typical SDKs do. But each part is likely to involve
slightly (or _very_) different actions that vary with the target platform.
With this in mind, to make this as generic as possible, what's provided is a
bare-bones framework described by the aforementioned outline.
The burden of dealing with the complex and variable specifics is shifted
onto particular targets as they are integrated to make use of this framework
(see [Adding a New Target](#Adding-a-New-Target)).

### Development Setups

What's suited to automation is not necessarily suited to development -- it
rarely is. Automation typically involves consuming configuration files for
potentially long-run processes that proceed without user input. Development
needs are often on-the-fly changes and quick build artifacts.

The solution offered provides for _both_ paradigms. See below for a [comparison
of automated and sdk setups](#automated-and-development-setups) and [more
details on development ones](#development-sdk-setups).

-------------------------------------------------------------------

## Overview

### Main Script and Target Specification

`builder.py` is the entrypoint to an sdk builder, which, simply put, will just
try to peform a sequence of steps -- clone sdk sources, build sdk, copy artifacts
in line with the ouline given above.

An SDK, for the purposes of `builder` is built for a _target_.
Different targets could require different SDKs altogether so the target
(a main 'spec' file and a set of files and scripts to carry out the main as well
as any particular target-specific tasks) must be integrated into _builder_.
Once integrated, the target to build for must be specified to `builder.py` e.g.:
```
./builder.py --target rpi4b --cores=$(nproc)
```
Note the list of supported targets can be listed using `--list-targets`.

### Automated and Development Setups

By default, builder will perform an _automated_ build where everything is
**containerized** ([2](#Notes)). The image is entirely self-contained and can be
pushed to a registry and so on.

Alternatively, you can ask it to build a _development_ setup. This will build
only a very minimal container image bundling basic dependencies. The sdk sources
are instead cloned on the _host_ in this case, and are (must be) then mounted
into the container for both the initial and any later builds.

There are pros and cons to each:
 * automated setups are completely self-contained and isolated. Once built, they
   can be pushed to registries, saved as archives etc., and no mounts from the
   host are needed. Conversely, dev SDK setups require mounting various directories
   from the host for anything to be done. Should the files on the host get
   deleted or corrupted, a whole rebuild might be necessary.
 * automated setups result in quite massive container images (typically north
   of 20 GBs). Development SDKs have a similar footprint, of course, on the host,
   but because the container to be loaded and started is very minimal (e.g. internal
   state maintained for it is comparatively negligible), restricted-scope builds
   beyond the initial full setup can actually be significantly _faster_!
 * development SDKs have the artifacts already on the host. The SDK is mounted
   from the host rather than being kept in a container image, meaning once the
   container is done building and gets thrown away, all the files are left on the
   host. Toolchains can be easily copied, the source for the packages is easily
   accessible etc. This avoids the need to shuffle files back and forth between
   host and container.
 * `builder` optionally takes a `.json` developer configuration file
   (see [here](#interactive-containers-and-developerjson)) that lets you specify
   additional or overriding environment variables and mounts configurations.
   See [the relevant section for details](development-setups).

### Containers and Container Images and Saving Time

Note the following points:
 * `builder` will by default (re)build an _entire_ sdk. This is only rarely what
   you want. More commonly you would get it to build the entire SDK only when it
   _needs_ to, in the interests of saving time and space. Instead, with
   the SDK initially built, you can ask `builder` to perform a
   `scope-restricted` build, i.e.:

   - build only selected packages (`./builder.py -t rpi4b --build-package
     <package list>`). For example:
```
./builder.py -t rpi4b --build-package strace
./builder.py -t rpi4b --build-package luaposix luasec luasocket
```
   Obvious time-saver as it will not be building a whole firmware -- or even
   host tools, cross-compilation toolchain etc. You reuse the already-built
   container image and only build the packages inside a _container_ instance
   started from it that gets used just for the occassion and then deleted.

   - build only a firmware or some such artifact. This saves time and space by
     again only building the artifact in question rather than tools and cross
     toolchain. Also, again, it does not build a whole other container image:
     it performs the build in an ephemeral container discarded after the fact.
     Example:
```
./builder.py --target rpi4b --cores=$(nproc) --build-firmware
```
Note in both cases you can also use a _development_ setup instead of an
automated one just as well by specifying the `-d|--devbuild` flag.

### Container Image Tags

`builder` will in the cases above look for an appropriate prebuilt container
image. It tags the image when it builds it with a certain name and that's how it
finds them -- therefore they should not be renamed if they are expected to be found.
Specificaly, each container image built will be tagged as follows:
```
// <sdk name>_<sdk branch>:latest_<sdk build type>_<target>
// e.g.
openwrt_openwrt-22.03   latest_dev_rpi4b
openwrt_openwrt-22.03   latest_automated_rpi4b
```
Development and automated images are separate and can coexist and be used
independently, as shown above, for any given target.

Note `builder` will _not_ delete previously-built images. The user is
responsible for this.

### Build Artifacts

**IF** the target has provided scripts for retrieving build artifacts
(see ![here](spec/targets/rpi4b/scripts/postbuild/401.retrieve_build_artifacts.sh)
for example), then `builder` will make available a tarball (the name of which is
configurable) in the `out` directory of this project. The tarball, besides and
independent of the target-specific artifacts, will contain a `timestamp` file
(which specifies the start and end times for the build process) and a log file.
E.g.
```
└─$ tar tvf artifacts.tar
drwx------ vcsaturninus/vcsaturninus   0 2022-12-28 15:52 ./
drwxr-xr-x vcsaturninus/vcsaturninus   0 2022-12-28 15:52 ./out/
-rw-rw-r-- vcsaturninus/vcsaturninus 687579 2022-12-28 15:52 ./out/build.log
-rw-r--r-- vcsaturninus/vcsaturninus   8258 2022-12-28 15:52 ./out/config.buildinfo
-rw-r--r-- vcsaturninus/vcsaturninus    288 2022-12-28 15:52 ./out/feeds.buildinfo
-rw-r--r-- vcsaturninus/vcsaturninus 49674596 2022-12-28 15:52 ./out/openwrt-22.03-snapshot-r20016-b1722a048a-bcm27xx-bcm2711-rpi-4-ext4-sysupgrade.img.gz
-rw-r--r-- vcsaturninus/vcsaturninus 40791379 2022-12-28 15:52 ./out/openwrt-22.03-snapshot-r20016-b1722a048a-bcm27xx-bcm2711-rpi-4-rootfs.tar.gz
-rw-r--r-- vcsaturninus/vcsaturninus 40344184 2022-12-28 15:52 ./out/openwrt-22.03-snapshot-r20016-b1722a048a-bcm27xx-bcm2711-rpi-4-squashfs-sysupgrade.img.gz
-rw-rw-r-- vcsaturninus/vcsaturninus       64 2022-12-28 15:52 ./out/timestamp
```

### Interactive Containers

Containers are used implicitly to build artifacts such as individual packages
and firmwares, as briefly described earlier. However, containers could be
started _interactively_ instead. Both automated and development `builder` modes
allow this, but the latter is specifically designed for this purpose.
See the section on development setups. The `--ephemeral` flag makes it so
the container is automatically deleted on exit. E.g.
```
# start interactive container from automated container image
./builder.py -t rpi4b --container --ephemeral
# start interactive container from development container image
./builder.py -t rpi4b --container --ephemeral -d
```
-------------------------------------------------------------------

## Adding a New Target

A ![target](spec/targets/rpi4b) has already been added for example purposes.
Any new target should create a similar directory and follow the same structure.

Briefly, the following are necessary:
 * A `<target_name>_spec.json` [target specification file](spec/targets/rpi4b/rpi4b_spec.json)
   is needed that sets various configuration parameters for the sdk build process
   -- source URL, environment variables to make available, etc.

   **NOTE** the fields are not arbitrary. The set of fields that _must_ be
   specified and permissble values are constrained as much as possible via the
   use of json schemas. This applies not only to the `_spec.json` file for the
   target, but to the specification of build `steps` that `builder` will follow
   (for both development and automated MOs), developer config files (see below)
   etc. This is to prevent misconfiguration as much as possible and avoid wasting
   time fixing preventable bugs.

   Files that fail to comply with the schemas in place will raise exceptions.
   A further aid in ensuring configuration files or changes made to them are
   correct is the `--validate` mode `builder.py` can be run in, which makes it
   simply try and validate all relevant json files against their schemas.
   Example:
```
./builder.py --validate
 ** Invocation: ['./builder.py', '--validate']
Validating steps specs ...
 # /home/vcsaturninus/auto/builder/spec/steps/dev_build.json : valid.
 # /home/vcsaturninus/auto/builder/spec/steps/automated_build.json : valid.
Validating common specs ...
 # /home/vcsaturninus/auto/builder/spec/targets/common/specs/environment.json : valid.
 # /home/vcsaturninus/auto/builder/spec/targets/common/specs/example.environment.json : valid.
Validating target specs ...
 # /home/vcsaturninus/auto/builder/spec/targets/rpi4b/rpi4b_spec.json : valid.
```
 * any files (particularly static or other configuration files to install into
   the sdk or the system) should go into `files/{sdk_config,system_config}` as
   apropriate.
 * Almost any number of scripts of arbitrary complexity may be provided
   for accomplishing the required results for the respective target. This is
   arguably in need of most explanation. Details are given in the following section.

The approach adopted by `builder` to try and maximize extendibility and minimize
duplication is twofold:
 * scripts founds in certain expected locations are executed. This makes it easy
   to extend the behavior arbitrarily. The flip side is almost nothing is given
   for free: target or SDK configurations must do the work.
 * files and scripts are installed from the general to the specific to allow
   judicious overriding. This is to be able to reuse as much as possible while
   easily overriding default or general behavior. Note again, `builer` does _not_
   provide defaults such that all new targets would have to do is override them.
   However, it makes it easy for users that have multiple targets to write
   common scripts that can be easily reused and applied to individual targets.

### Common and target-specific files and scripts

Targets are expected to provide configuration files and scripts to get the
desired results. As mentioned, target _files_ should go in the
`files/{sdk_config,system_config}` directory structure of the respective target,
while scripts should go in the `scripts/` directory of the target.

The `scripts` directory is expected to follow the **same directory tree
structure** as that of the _common_ directory.

The [common directory](spec/targets/common) currently looks like this:
```
common/
├── files
│   ├── sdk_config
│   │   ├── common
│   │   └── OpenWrt
│   └── system_config
│       ├── common
│       │   ├── fixuid.yml
│       │   ├── gitconfig
│       │   └── ssh
│       │       ├── id_rsa
│       │       └── id_rsa.pub
│       └── OpenWrt
├── scripts
│   ├── build
│   │   ├── common
│   │   └── OpenWrt
│   │       └── 300.build_sdk.sh
│   ├── hooks
│   │   ├── build_packages
│   │   │   ├── common
│   │   │   └── OpenWrt
│   │   │       └── 100.build_package.sh
│   │   ├── install_configs
│   │   │   ├── common
│   │   │   └── OpenWrt
│   │   │       └── 100.install_configs.sh
│   │   ├── prepare_sdk
│   │   │   ├── common
│   │   │   ├── OpenWrt
│   │   │   └── readme.md
│   │   ├── prepare_system
│   │   │   ├── common
│   │   │   │   └── 0.fixups.sh
│   │   │   ├── OpenWrt
│   │   │   └── readme.md
│   │   └── run_hooks.py
│   ├── postbuild
│   │   ├── common
│   │   └── OpenWrt
│   │       └── 400.post_build.sh
│   └── prebuild
│       ├── common
│       ├── OpenWrt
│       │   ├── 200.update_and_install_feeds
│       │   └── 201.restore_configs.sh
│       └── README.md
└── specs
    ├── environment.json
    └── example.environment.json
```

The example [rpi4b target's directory](spec/targets/rpi4b) layout currently looks as follows:
```
rpi4b/
├── files
│   ├── sdk_config
│   │   ├── feeds.conf
│   │   └── openwrt_config
│   └── system_config
├── rpi4b_spec.json
└── scripts
    ├── build
    ├── misc
    ├── postbuild
    │   └── 401.retrieve_build_artifacts.sh
    └── prebuild
```

To understand the importance of using the same directory tree layout, note
the following, which is what `builder` puts in the container ahead of building the sdk.
```
files/
├── sdk_config
│   ├── feeds.conf
│   └── openwrt_config
└── system_config
    ├── fixuid.yml
    ├── gitconfig
    └── ssh
        ├── id_rsa
        └── id_rsa.pub
scripts/
├── build
│   └── 300.build_sdk.sh
├── hooks
│   ├── build_packages
│   │   └── 100.build_package.sh
│   ├── install_configs
│   │   └── 100.install_configs.sh
│   ├── prepare_sdk
│   ├── prepare_system
│   │   └── 0.fixups.sh
│   └── run_hooks.py
├── postbuild
│   ├── 400.post_build.sh
│   └── 401.retrieve_build_artifacts.sh
└── prebuild
    ├── 200.update_and_install_feeds
    └── 201.restore_configs.sh
```
`builder` creates a `staging directory` of files and scripts which it will then
copy into the container in preparation for the actual sdk build.
Notice each script or _files_ directory under `common` contains another `common`
directory, and another directory with the name of a supported sdk ([4](#notes)).

Builder therefore installs files and scripts into its staging directory in the
following order:
 * common files/scripts. These are common to any SDK or target
 * sdk-specific files/scripts
 * target-specific files/scripts.

Files with the same name will be overwritten and overridden the farther you go down
the list above. Ideally targets should augment rather than override
_common_ files and particularly scripts. This is facilliatated as described
next.

### Build stages, scripts, and hooks

`builder` divides an sdk build process into a few distinct stages:
  * `prebuild` (runs before the build process starts)
  * `build` (the actual build process)
  * `postbuild` (once the build process has finished)

These stages are gone through when you build the entire sdk or a whole firmware
or some such artifact but _not_ when you build individual packages only.

Target configurations (or _sdk_ configurations, or the _common_ layer) are expected
to provide scripts for each of the stages above:
 * `prebuild` should have scripts that always run before any build is actually
   done e.g. update feeds, apply configs etc
 * `build` should have scripts that instruct on how to do the actual build e.g.
   run the top-level `Makefile`.
 * `postbuild` should have scripts that act on the results of the build e.g.
   packaging any build artifacts in any specific way, sending out notifications,
   triggering automated testing etc.

Additionally, `builder` uses a few additional `hooks` which are not disimmilar to the
aforementioend 'stages'. The current hooks are: `prepare_system`, `prepare_sdk`,
`install_configs`, and `build_packages`.

The difference between the `stages` and `hooks` are that, as explained, the
stages are almost always gone through while the hooks are only triggered in
specific scenarios:
 * `prepare_system`: scripts that only run the one time before the initial build
   of the **whole** sdk (as opposed to before every scope-restricted build). The
   scripts are expected to set up the system in some way e.g. apply fixes
   that would prevent any later successful sdk setup.
 * `prepare_sdk` : ditto, but the scripts act on the sdk setup itself rather
   than the system
 * `install_configs`: targets are expected to provide one or more scripts here
   that know how to install into the sdk any config files provided by the target
   in its files directory as explained earlier.
 * `build_packages`: scripts that carry out the building of individual packages
   and the packaging of ensuing artifacts.

**NOTES**:
  * `builder` will do virtually nothing by default. It does _not_ know how to
    _build_ an sdk. It does not know _what_ artifacts to package or where they
    are. It does not know how to build individual packages and it does not know
    how to prepare the system or the sdk or install configs. It would be
    unscalable and not generic if it did. What it _does_ know is that if certain
    scripts are found in certain locations it can call them to accomplish these tasks.
  * _Targets_ added to `builder` should provide scripts for any or all of these
    hooks ([3](#notes)) as appropriate.
  * `builder` will pass various environment variables to these scripts e.g. the
    top directory of the sdk, the `output` directory where artifacts should be
    copied etc. Scripts _should_ use these so as to integrate well. The list of
    environment variables passed is printed out when a build is done e.g.
```
 ** environment: {'VERBOSE': 'Y', 'BUILD_ARTIFACTS_OUTDIR': '/home/dev/out/', 'PACKAGE_OUTDIR': '/home/dev/out/package/', 'NUM_BUILD_CORES': '12', 'PYTHONPATH': ':/home/dev/base/', 'CONFIGS_DIR': '/home/dev/base/files/', 'SDK_TOPDIR': '/home/dev/OpenWrt_openwrt-22.03'}
```
Notably:
 - `SDK_TOPDIR` : the top-level directory of the sdk.
 - `BUILD_ARTIFACTS_OUTDIR` : where full-build e.g. firmware artifacts
   should be copied so `builder` knows where to find them and copy them
   from
 - `PACKAGE_OUTDIR` : where package-restricted builds should copy their
   artifacts e.g. packages, hashes etc.
 - `CONFIGS_DIR` : the directory copied from the _target_ that should
    contain 2 subdirectories: `sdk_config` and `system_config`. Scripts must
    be provided in the `install_configs` hook that retrieve any configs from
    here and apply them to the sdk or the system.

  * Scripts (files) with the same name have the overriding behavior explained above.
  * Scripts _must_ be named in the following way: `<integer>.<script name> ...`.
    `Builder` will perform a numeric sort (note: NOT alphabetical) of the
    scripts' prefixes and then execute each script in the order obtained.
    This allows you to e.g. have 1000 scripts between [1,1000] (or beyond) and allows for
    arbitrary extendibility. Each such directory where `builder` looks for
    scripts to execute is its own namespace such that `100.fix_symlinks.sh` in
    `prebuild` and `100.fix_symlinks.sh` in `build` do _not_ conflict.


## Development SDK setups

The two 'modes' `builder` can be run in is `automated` (default) and
`development`. The former is designed with automated builds e.g. nightly builds,
buildbots etc in mind. The latter, with developers.

### Full SDK builds and restricted builds

Both automated and development sdk setups allow the following
(for the automated mode, simply remove the `--devbuild` flag from the following
examples):
```
# full-sdk build
./builder.py --cores=$(nproc) --target rpi4b --devbuild

# restricted firmware-only build
./builder.py --cores=$(nproc) --target rpi4b --devbuild --build-firmware

# restricted package-only build
./builder.py --cores=$(nproc) --target rpi4b --devbuild --build-package <package1>,<package2>,..,<package n>
```
There must've been a successful full-sdk build and an ensuing container image
for the restricted builds to be possible.

### Interactive Containers and developer.json

By far the most significant part of the development setup as opposed to the
automated one is the ease of mounting host directories with a view to:
 * speeding up the copying of files between host and container (ideally its
   elimination altgether)

   To this end, the user can simply mount a directory with local changes
   anywhere in the sdk, including on top of existing directories, to quickly
   prototype things. This includes for example the build directory of a specific
   package (see example below) where the source code can be modified on the host
   and then simply built in another terminal window. Directories exist at the
   same time on both the host system and in the container.

 * quick and easy obtainment of build artifacts.

   To this end, `build.py` can be called with the `--build-package` argument as
   shown above, in which case it will perform an automated background build in
   a throwaway container and retrieve an archive with build artifacts. However,
   the sdk actually resides on the host so the user _already_ has easy access to
   any build artifacts. More appealing therefore might be not the build artifacts
   (which are typically compiled binaries and such) but the source code,
   binaries with debug symbols left in etc. Again, this can be accomplished by
   judicious use of bind mounts.

Since strategic bind mounts of host paths into the container are expected to be
of particular interest, a `json` configuration file can be provided with dev sdk
setups. See [example](example.developer.json).
By default, `builder` expects a `developer.json` file in the root directory of the
`builder`project but a different file with an arbitrary name can be specified
to allow the user to e.g. maintain separate per-target profiles. E.g.
```
./builder.py -t rpi4b --container --ephemeral -d --devconfig ~/rpi4b-dev.json
```

The contents of such a configuration file are minimal and when found/specified,
the file is checked for compliance with ![the relevant schema](spec/json_schema/developer.schema.json).
The file allows for specification of environment variables and mounts in the
expected format.

Note that specifications here take overriding precendence over
any defaults, `builder`-implicit, or target-specific environment variables or
mounts. This is to allow the user to e.g. instruct the build process to use
different build branches, enable/disable certain behaviors based on environment
variables, or strategically mount directories in places of interest to speed up
the workflow and obtain artifacts of interest.

Taking another look at the basic ![dev config file example](example.developer.json),
one thing of note is the `ubus-source` property of the `mounts` object.
This tells `builder` to mount `/home/dummyuser/code/ubus` into
`/home/dev/OpenWrt_openwrt-22.03/build_dir/target-aarch64_cortex-a72_musl/ubus-2022-06-01-2bebf93c`
when starting a container (whether an interactive one or in the background for a restricted build).
This could e.g. be a directory (mounted from the host) where the developer is working on
a patch.

-----------------------------------------------------------------------------------

## Notes

 * [1] Typical reasons: the sdk is not plain OpenWrt but heavily customized; the
   sdk is OpenWrt but a different (e.g. much older) version, requiring porting
   to a different Linux kernel version, libc, and system libraries;
   3rdParty proprietary SDKs e.g. for a Linux kernel with proprietary drivers might
   be a requirement for the project, which complicates the setup; external toolchains
   and/or out-of-tree kernels with a mismatching OpenWrt version that is not integrated
   with those versions. And the like.

 * [2] The only container technology supported at the moment is `docker` but others
   could be added if required.

 * [3] I mean both 'stages' and 'hooks'. They are, generically, both points in the
   process that can be **hooked into**.

 * [4] Currently the only sdk supported is OpenWrt but another e.g. `yocto` could be added
   by replicating the OpenWrt structure and subclassing the concrete `sdk` class in `sdk.py`.


