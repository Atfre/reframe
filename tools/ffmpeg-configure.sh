#!/usr/bin/env bash
# Development only. Run from an empty build directory with the MSVC environment.
set -eu
source_dir="$1"
dav1d_prefix=$(realpath --relative-to=. "$(cygpath -u "$2")")
pkg_config=$(realpath --relative-to=. "$(cygpath -u "$3")")
export PKG_CONFIG_PATH="$dav1d_prefix/lib/pkgconfig"
"$source_dir/configure" \
    --toolchain=msvc --arch=x86_64 --target-os=win32 \
    --disable-everything --disable-autodetect --disable-network \
    --disable-doc --disable-debug --disable-x86asm --disable-avdevice \
    --disable-swresample --disable-iconv \
    --enable-static --disable-shared --enable-ffmpeg --enable-ffprobe \
    --enable-protocol=file,pipe --enable-demuxers \
    --enable-decoders --enable-parsers \
    --enable-libdav1d --pkg-config="$pkg_config --define-variable=prefix=$dav1d_prefix" \
    --enable-encoder=bmp --enable-muxer=image2pipe \
    --enable-filter=scale,setsar,format,transpose,hflip,vflip \
    --extra-cflags=-MT --extra-ldflags=-NODEFAULTLIB:MSVCRT
