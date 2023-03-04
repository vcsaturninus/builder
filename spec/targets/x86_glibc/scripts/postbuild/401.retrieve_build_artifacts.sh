#!/bin/bash

# Copy build artifacts on build completion

sdk_topdir="${SDK_TOPDIR:?}"
outdir="${BUILD_ARTIFACTS_OUTDIR}"
artifacts_dir="$sdk_topdir/bin"

artifacts=()
artifacts+=(openwrt-22.03-*-ext4-sysupgrade.img.gz)
artifacts+=(openwrt-22.03-*-squashfs-sysupgrade.img.gz)
artifacts+=(openwrt-22.03-*-rootfs.tar.gz)
artifacts+=(feeds.buildinfo)
artifacts+=(config.buildinfo)

printf " ~ Copying build artifacts ...\n"
for artifact in "${artifacts[@]}"; do
    cmd=(find "$artifacts_dir" -iname "$artifact" -exec cp {} "$outdir" \;)
    echo "${cmd[@]}"
    "${cmd[@]}"
done
