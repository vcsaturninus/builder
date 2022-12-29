#!/bin/bash

configs_dir="${CONFIGS_DIR:?}"
sdk_topdir="${SDK_TOPDIR:?}"

# $1 = name of file to install (path should be relative to $configs_dir)
# $2 = path to install to (should be relative to $sdk_topdir)
install_file(){
    local src="$configs_dir/${1:?}"
    local dst="$sdk_topdir/${2:?}"

    if [[ -f $src ]]; then
        mkdir -p "$(dirname "$dst")"
        cp "$src" "$dst"
    else
        echo "WARNING: cannot install '$src' (not found)"
    fi
}

install_file "sdk_config/openwrt_config" ".config"
# used to restore it from here after feeds update and installation;
# needed because openwrt will overwite it initially
install_file "sdk_config/openwrt_config" "/configs/.config"

install_file "sdk_config/feeds.conf" "feeds.conf"

