"""Package the locally built Windows runtime and corresponding sources (Python 3)."""
import hashlib
import json
import pathlib
import re
import shutil
import struct
import subprocess
import tarfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / 'build'
INTERNAL = ROOT / 'scripts/sfm/mainmenu/aftre/reframe'
RUNTIME = INTERNAL / 'runtime'
DIST = ROOT / 'dist'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checkWorkspacePath(path):
    if not path.resolve().is_relative_to(ROOT):
        raise SystemExit('Generated path leaves the repository: ' + str(path))


def checkRuntimeDirectory(directory):
    checkWorkspacePath(directory)
    if directory.exists():
        unexpected = [path.name for path in directory.iterdir()
                      if path.name not in ('ffmpeg.exe', 'ffprobe.exe') or not path.is_file()]
        if unexpected:
            raise SystemExit('Unexpected runtime files; review them before packaging: ' + ', '.join(unexpected))
    for filename in ('ffmpeg.exe', 'ffprobe.exe'):
        checkWorkspacePath(directory / filename)


def checkSourceTree(sourceArchive, directory):
    with tarfile.open(sourceArchive) as archive:
        for member in archive:
            if member.isfile():
                path = directory.parent / member.name
                if not path.resolve().is_relative_to(directory.resolve()):
                    raise SystemExit('Unexpected FFmpeg source path: ' + member.name)
                with archive.extractfile(member) as original:
                    if not path.is_file() or sha(path) != hashlib.sha256(original.read()).hexdigest():
                        raise SystemExit('FFmpeg source differs from the pinned archive: ' + member.name)


def checkReleasePaths(data, name):
    # Inspect binary strings, UTF-16 strings and escaped JSON paths alike.
    normalized = data.replace(b'\0', b'').replace(b'\\', b'/').lower()
    normalized = re.sub(rb'/+', b'/', normalized)
    home = rb'(?:[a-z]:/|/(?:cygdrive/)?[a-z]/)(?:users|documents and settings)/|/(?:home|users)/'
    roots = [ROOT, pathlib.Path.home()]
    for path in roots:
        root = path.as_posix().lower().encode('utf-8')
        variants = [root]
        if root[1:3] == b':/':
            variants += [b'/' + root[:1] + root[2:], b'/cygdrive/' + root[:1] + root[2:]]
        if any(value in normalized for value in variants):
            raise SystemExit('Local build path found in ' + name + '. Rebuild using portable paths.')
    if re.search(home, normalized):
        raise SystemExit('Personal directory found in ' + name + '. Rebuild using portable paths.')


def add(archive, path, name):
    data = path.read_bytes()
    checkReleasePaths(data, name)
    member = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    member.compress_type = zipfile.ZIP_DEFLATED
    member.external_attr = 0o100644 << 16
    archive.writestr(member, data)


def main():
    dependencies = json.loads((ROOT / 'tools/dependencies.json').read_text())
    dependency = dependencies['ffmpeg_source']
    dav1d = dependencies['dav1d_source']
    source = WORK / ('ffmpeg-' + dependency['version'])
    build = WORK / ('ffmpeg-' + dependency['version'] + '-build')
    source_archive = WORK / dependency['filename']
    if not source_archive.exists() or sha(source_archive) != dependency['sha256']:
        raise SystemExit('Run prepare_build.py first: missing or changed FFmpeg source.')
    for directory in (WORK, INTERNAL, RUNTIME, DIST):
        checkWorkspacePath(directory)
    for name in ('LICENSE.txt', 'NOTICE.txt', 'manifest.json'):
        checkWorkspacePath(RUNTIME / name)
    for name in ('ReFrame.zip', 'ReFrame-sources.zip', 'SHA256SUMS.txt'):
        checkWorkspacePath(DIST / name)
    checkSourceTree(source_archive, source)
    dav_archive = WORK / dav1d['filename']
    dav_source = WORK / ('dav1d-' + dav1d['version'])
    if not dav_archive.exists() or sha(dav_archive) != dav1d['sha256']:
        raise SystemExit('Missing or changed dav1d source archive.')
    checkSourceTree(dav_archive, dav_source)
    binaries = [build / 'ffmpeg.exe', build / 'ffprobe.exe']
    for binary in binaries:
        if not binary.exists():
            raise SystemExit('Run tools/build_runtime.ps1 first.')
        data = binary.read_bytes()
        checkReleasePaths(data, binary.name)
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[pe:pe+4] != b'PE\0\0' or struct.unpack_from('<H', data, pe + 4)[0] != 0x8664:
            raise SystemExit('Expected an x86-64 Windows runtime: ' + binary.name)
    version = subprocess.check_output([str(binaries[0]), '-version'], stderr=subprocess.STDOUT).decode('utf-8')
    license_text = subprocess.check_output([str(binaries[0]), '-L'], stderr=subprocess.STDOUT).decode('utf-8')
    if ('ffmpeg version ' + dependency['version']) not in version or '--enable-gpl' in version or '--enable-nonfree' in version:
        raise SystemExit('Unexpected FFmpeg version or license configuration.')
    if 'LGPL' not in (build / 'config.h').read_text() and 'Lesser' not in license_text:
        raise SystemExit('Expected an LGPL runtime.')
    configured = next(line.split('=', 1)[1] for line in (build / 'ffbuild/config.mak').read_text().splitlines()
                      if line.startswith('FFMPEG_CONFIGURATION='))
    if 'configuration: ' + configured not in version:
        raise SystemExit('The binaries use an older configuration. Rebuild with -Reconfigure.')
    if not all(flag in version for flag in ('--enable-decoders', '--enable-demuxers', '--enable-libdav1d')):
        raise SystemExit('Rebuild the expanded video runtime with -Reconfigure.')
    runtime_bin = RUNTIME / 'bin'
    checkRuntimeDirectory(runtime_bin)
    runtime_bin.mkdir(parents=True, exist_ok=True)
    for binary in binaries:
        shutil.copyfile(binary, runtime_bin / binary.name)
    RUNTIME.mkdir(exist_ok=True)
    shutil.copyfile(source / 'COPYING.LGPLv2.1', RUNTIME / 'LICENSE.txt')
    checkWorkspacePath(RUNTIME / 'dav1d-LICENSE.txt')
    shutil.copyfile(dav_source / 'COPYING', RUNTIME / 'dav1d-LICENSE.txt')
    manifest = {
        'project': 'FFmpeg', 'version': dependency['version'],
        'source': dependency, 'license': 'LGPL-2.1-or-later',
        'architecture': 'Windows x86-64 (separate process from 32-bit SFM)',
        'build_details': version,
        'compiler_path_policy': 'MSVC /d1trimfile:<build-directory>; relative source and dependency paths',
        'binaries': {binary.name: sha(binary) for binary in binaries},
        'external_codec_libraries': [dict(project='dav1d', version=dav1d['version'],
            license='BSD-2-Clause', source=dav1d, linkage='static')],
        'source_distribution': 'ReFrame-sources.zip, alongside ReFrame.zip',
        'components': ['ffmpeg', 'ffprobe', 'libavcodec', 'libavformat',
                       'libavfilter', 'libavutil', 'libswscale'],
    }
    (RUNTIME / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (RUNTIME / 'NOTICE.txt').write_text(
        ('ReFrame uses FFmpeg %s, Copyright (c) the FFmpeg developers.\n' % dependency['version']) +
        'FFmpeg is free software under LGPL version 2.1 or later; see LICENSE.txt.\n'
        'No FFmpeg source modifications. Includes the static dav1d AV1 decoder\n'
        + ('version %s (BSD-2-Clause); see dav1d-LICENSE.txt and manifest.json.\n' % dav1d['version']) +
        ('Source: %s\n' % dependency['url']) +
        'Corresponding source and build scripts: ReFrame-sources.zip, supplied\n'
        'alongside ReFrame.zip at the same download location. Redistributors must\n'
        'provide this source sidecar with their binary download.\n'
        'Configuration, compiler and library versions: manifest.json, build_details.\n'
        'Exact source and binary SHA-256: manifest.json.\n'
        'The executables can be replaced with compatible modified LGPL builds;\n'
        'ReFrame does not prohibit modification or reverse engineering.\n'
        'Includes Microsoft C runtime code under its redistributable terms.\n'
        'No compiler, development Make, VLC or Keyframe binaries are included.\n', encoding='utf-8')
    DIST.mkdir(exist_ok=True)
    entry = ROOT / 'scripts/sfm/mainmenu/aftre/reframe.py'
    members = [entry, INTERNAL / 'timeline.rfi', INTERNAL / 'process.rfi', INTERNAL / 'viewer.rfi',
               RUNTIME / 'LICENSE.txt', RUNTIME / 'dav1d-LICENSE.txt',
               RUNTIME / 'NOTICE.txt', RUNTIME / 'manifest.json']
    members += [runtime_bin / binary.name for binary in binaries]
    with zipfile.ZipFile(DIST / 'ReFrame.zip', 'w') as archive:
        add(archive, ROOT / 'LICENSE', INTERNAL.relative_to(ROOT).as_posix() + '/LICENSE.txt')
        for path in sorted(members):
            add(archive, path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(DIST / 'ReFrame-sources.zip', 'w') as archive:
        add(archive, source_archive, source_archive.name)
        add(archive, dav_archive, dav_archive.name)
        development = [ROOT / name for name in ('CONTRIBUTING.md', 'LICENSE', 'README.md')]
        for folder in ('tools', 'tests', 'docs'):
            development.extend(path for path in (ROOT / folder).iterdir()
                               if path.is_file() and path.suffix in ('.py', '.ps1', '.sh', '.json', '.md'))
        for path in sorted(development):
            add(archive, path, 'ReFrame/' + path.relative_to(ROOT).as_posix())
        for path in members:
            if path.suffix in ('.py', '.rfi'):
                add(archive, path, 'ReFrame/' + path.relative_to(ROOT).as_posix())
        for path in [build / 'config.h', build / 'config_components.h', build / 'ffbuild/config.mak']:
            add(archive, path, 'build-configuration/' + path.name)
        add(archive, RUNTIME / 'manifest.json', 'build-configuration/manifest.json')
    (DIST / 'SHA256SUMS.txt').write_text(''.join(
        sha(DIST / name) + '  ' + name + '\n' for name in ('ReFrame.zip', 'ReFrame-sources.zip')), encoding='ascii')
    print(DIST / 'ReFrame.zip')
    print(DIST / 'ReFrame-sources.zip')


if __name__ == '__main__':
    main()
