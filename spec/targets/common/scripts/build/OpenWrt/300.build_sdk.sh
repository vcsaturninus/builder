#!/bin/bash

topdir="${SDK_TOPDIR:?}"
cd $topdir

cmd="make ${VERBOSE:+V=sc} -j${NUM_BUILD_CORES:-1}"
printf " ~ Building SDK; Command='$cmd'\n"
$cmd
