#!/bin/bash

sdk_topdir="${SDK_TOPDIR:?}"
saved="configs"

cp "$sdk_topdir/$saved/.config" "$sdk_topdir"/.config || { rc="$?"; echo "failed to restore '.config': (exit code $rc)" ; exit $rc; }
make -C "$sdk_topdir" defconfig

