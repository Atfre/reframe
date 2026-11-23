# Video runtime provenance

ReFrame's integration, interface and synchronization are original project code.
Keyframe MP by Zurbrigg and msu355's tools are conceptual references; their source,
binaries and archives are not build inputs or runtime dependencies.

## FFmpeg

| Item | Included build |
| --- | --- |
| Upstream | [FFmpeg](https://ffmpeg.org/) |
| Version | **8.0.3**, unmodified release source |
| Source | [ffmpeg-8.0.3.tar.xz](https://ffmpeg.org/releases/ffmpeg-8.0.3.tar.xz) |
| Source SHA-256 | `6136812ea6d4e68bdba27e33c2a94382711cdf4f8602ffef056ff792bd6f9818` |
| License | **LGPL-2.1-or-later**; full text in the runtime's `LICENSE.txt` |
| Compiler observed | MSVC 19.51.36260, x64; static Microsoft CRT (`/MT`) |
| Delivered programs | `ffmpeg.exe`, `ffprobe.exe`, both Windows x86-64 |
| FFmpeg components linked into programs | libavcodec, libavformat, libavfilter, libavutil, libswscale |
| Enabled video paths | Native decoders, parsers and demuxers; BMP encoder, image2pipe muxer, file/pipe protocols; scale, aspect and rotation filters |
| External codec libraries | Static dav1d 1.5.4 for AV1; see below |
| Excluded | Audio playback, network protocols, ffplay, GPU decoding, VLC, Python, compiler and build tools |

The exact configuration and runtime component versions are recorded in the shipped
`runtime/manifest.json`, together with source and executable SHA-256.
This manifest is generated locally and ignored by Git; it is included in both
release packages. The build uses relative paths in binaries and configuration,
and packaging rejects personal build paths without rewriting the recorded data.
The manifest's `compiler_path_policy` records MSVC path trimming for included
headers. The build script supplies `/d1trimfile` through the compiler environment,
following its use in [Microsoft's Windows App SDK build](https://github.com/microsoft/WindowsAppSDK/blob/main/Directory.Build.props).
Windows system DLLs supply standard OS services. The static CRT avoids a separate
Visual C++ redistributable installation. SFM supplies Python/PySide/Qt; none of its
files are copied into the installer.

Builds follow FFmpeg's [MSVC instructions](https://ffmpeg.org/platform.html).

## dav1d

The AV1 decoder is [VideoLAN dav1d 1.5.4](https://code.videolan.org/videolan/dav1d),
from the unmodified [official release archive](https://downloads.videolan.org/pub/videolan/dav1d/1.5.4/dav1d-1.5.4.tar.xz).
SHA-256: `686616b7c69eb88d44459391ab25cac13b6647a3b288835c5784e71c1514a5c5`.
Its **BSD-2-Clause** copyright and license are included as `runtime/dav1d-LICENSE.txt`.
Both 8-bit and high-bit-depth C implementations are linked statically into FFmpeg.
Assembly, CLI tools, examples and tests are disabled; the CRT is static. No dav1d
DLL or separate install is required. The source sidecar includes its exact source
archive, and `build_runtime.ps1` records the build options. The release signature
was checked against the [official VideoLAN release key](https://download.videolan.org/pub/keys/7180713BE58D1ADC.asc),
fingerprint `65F7C6B4206BD057A7EB73787180713BE58D1ADC`.

## Corresponding source and redistribution

`tools/build.py` generates **`ReFrame.zip`**, **`ReFrame-sources.zip`** and
**`SHA256SUMS.txt`** in the local, Git-ignored `dist/` directory. Attach all three to
the same GitHub release, preserving the notices and filenames. Keep the source
sidecar available alongside the installer, as described by
[FFmpeg's licensing guidance](https://ffmpeg.org/legal.html).
The animator only needs `ReFrame.zip`; the source sidecar is for rebuilding and
redistribution.

The source sidecar contains the exact unmodified FFmpeg source archive, the build
scripts, flags, generated configuration, dav1d source, compiler/version output, hashes and
ReFrame source. No proprietary linking layer is needed: FFmpeg's own programs and
libraries are compiled together. ReFrame communicates through process arguments
and stdout and permits replacing the programs with compatible modified builds.

To rebuild from the sidecar, extract it, enter `ReFrame/`, create
`build/`, copy the adjacent FFmpeg and dav1d source archives there and run the
documented prepare/build commands. The prepare step reuses verified downloads and
fetches missing or changed pinned inputs. No patches are applied to FFmpeg source.
Configure and compile in a fresh build directory after changing dependency versions
or toolchains. ZIP assembly is deterministic for the same inputs; cross-compiler binary
reproducibility is not claimed.

## Development only

MSYS2 GNU Make 4.4.1-2 (GPL-3.0-or-later) is downloaded from the
[MSYS2 package repository](https://repo.msys2.org/msys/x86_64/make-4.4.1-2-x86_64.pkg.tar.zst).
Its checksum is pinned in `tools/dependencies.json`. It runs with Git for Windows'
MSYS environment and the installed Visual Studio C++ Build Tools/Windows SDK.
These tools are not distributed with ReFrame. They are used only to compile it.
`prepare_build.py` downloads the pinned Make, Meson and pkgconf inputs into
`build/`; a separate MSYS2 installation is not needed for the documented build.
Meson 1.10.2 (Apache-2.0, [upstream](https://mesonbuild.com/)) and MSYS2 pkgconf
2.3.0-1 (ISC, [upstream](https://github.com/pkgconf/pkgconf)) are pinned development
inputs. Meson runs from extracted source; no pip install is required. Ninja comes
from Visual Studio's C++ CMake tools component. None enters the installer.
Development fixtures require a separate FFmpeg with an H.264 encoder. The generator
defaults to `libopenh264`; pass `--encoder libx264` to use x264 instead. Neither
development encoder is included in the installer.

## Security maintenance

The 8.0.3 archive was verified against FFmpeg's detached signature and release-key
fingerprint `FCF986EA15E6E293A5644F10B4322F04D67658D8`.
The release signing key is published on the [official download page](https://ffmpeg.org/download.html).
The MOV demuxer includes IAMF parsing even though ReFrame does not play audio.
Review [upstream security advisories](https://ffmpeg.org/security.html) for the
enabled components before updating the pinned release. The decoder runs with the
user's Windows permissions; a separate process is not a security sandbox.
