FROM ubuntu:20.04 as openwrt-sdk

# Docker environment variables
ENV DEBIAN_FRONTEND noninteractive

# install base system packages for build sdk etc.
RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
    sudo \
    locales \
    wget \
    curl \
    vim \
    git \
    tree \
    expect \
    socat \
    sshpass \
    trickle \
    lua5.1 \
    python2 \
    python3 \
    python3-pip \
    python3-mako \
    python3-yaml \
    build-essential \
    cmake \
    gawk \
    rename \
    gpg gpg-agent ca-certificates \
    unzip \
    libncurses5-dev libncursesw5-dev \
    cpio \
    rsync \
    bc \
    quilt \
	libssh2-1-dev \
	libssh2-1 \
	libidn2-0 \
	openssh-client \
	ncurses-base \ 
	libncurses5-dev \
	libncursesw5-dev \
	file \
    libpam-cap \
	libpam0g-dev \
	libsnmp-dev \
	libcap-dev \
	libcap2 \
	liblzma-dev \
    lua-socket \
    lua-socket-dev \
	libidn2-dev \
	libgnutls28-dev \
    libxml2 \
	libxml2-dev \
	gpg gpg-agent ca-certificates \
	gcc g++ \ 
	mkisofs \
	qemu-utils \
    libelf-dev \
	libldap-2.4-2 \
    libgnutls30 \
    liblzma-dev \
    libnet-snmp-perl \
    libjansson-dev \
    iputils-ping \
    iproute2

# Install front-end required packages: nodejs, npm, html-minifier etc.
ARG NODEJS_VERSION_MAJOR=14
RUN curl -fsSL "https://deb.nodesource.com/setup_${NODEJS_VERSION_MAJOR}.x" | bash - && \
    apt-get install -y nodejs && \
    npm install --global typescript yarn

# Install html-minifier (needed for dumaos-build for frontend minification)
RUN npm --version
RUN npm install html-minifier -g

RUN echo 'debconf debconf/frontend select Noninteractive' | sudo debconf-set-selections && \
    ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime

# 1. Create new unprivileged user "dev" (added to sudoers below)
ARG USER
ARG GROUP
ARG UID
ARG GID

RUN groupadd -g $GID $GROUP
RUN useradd -m -l -s /bin/bash -u$UID -g$GID $USER

# don't require password when running command through sudo
RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/10-$USER

USER $USER:$USER

# Copy ssh keys for ssh access to any internal servers
RUN mkdir -p /home/$USER/.ssh
ADD  --chown=$USER:$USER staging/files/system_config/ssh /home/$USER/.ssh/
COPY --chown=$USER:$USER staging/files/system_config/gitconfig /home/$USER/.gitconfig
ADD  --chown=$USER:$USER staging /home/$USER/base

ENV PATH="$PATH:/home/dev/.local/bin"
ENV BASE_DIR "/home/$USER/base/"
WORKDIR $BASE_DIR
RUN pip3 install -r depends/requirements.txt

# Environment variables and docker build args
ARG TARGET
ARG SDK_DIRNAME
ARG NUM_BUILD_CORES_CLI_FLAG
ARG BUILD_ARTIFACTS_OUTDIR
ARG DEV_BUILD_CLI_FLAG

ENV INSIDE_CONTAINER "Y"
ENV SDK_TOPDIR "/home/$USER/$SDK_DIRNAME"
ENV BUILD_ARTIFACTS_OUTDIR "$BUILD_ARTIFACTS_OUTDIR"

RUN mkdir -p $BUILD_ARTIFACTS_OUTDIR

RUN /bin/bash -c "./builder.py -t $TARGET $DEV_BUILD_CLI_FLAG $NUM_BUILD_CORES_CLI_FLAG "

WORKDIR $SDK_TOPDIR
