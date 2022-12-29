#!/bin/bash

# This script will build one or more packages and copy the resulting ipk(s)
# to the predefined output directory.

out_dir="${PACKAGE_OUTDIR:?}"
pkgs="${PACKAGES_TO_BUILD:?}"
sdk_topdir="${SDK_TOPDIR:?}"
artifacts_dir="$sdk_topdir/bin"
ncores="${NUM_BUILD_CORES:-1}"

fail(){
    printf "%s\n" "$1"
    exit 1
}

cd "$sdk_topdir" || fail "Couldn't cd to $sdk_topdir"
mkdir -p "$out_dir"
echo "Packages to build: $pkgs"
for pkg in $pkgs; do
    build_cmd=(make package/"$pkg"/{clean,compile} V=sc -j"$ncores")
    echo "Building $pkg ('${build_cmd[@]}')"
    "${build_cmd[@]}" || fail "Error building $pkg"

    find_cmd=(find "$artifacts_dir" -iname "*$pkg*.ipk" -exec cp {} "$out_dir" \;)
    echo "Looking for $pkg artifact ('${find_cmd[@]}')"
    "${find_cmd[@]}"
done
