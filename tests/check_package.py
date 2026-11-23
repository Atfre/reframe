"""Check the actual distributable and its corresponding-source sidecar."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import struct
import subprocess
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reframe_build', ROOT / 'tools/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def imports(data):
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    machine, sections = struct.unpack_from('<HH', data, pe+4)
    assert machine == 0x8664
    optional_size = struct.unpack_from('<H', data, pe+20)[0]
    optional = pe + 24
    assert struct.unpack_from('<H', data, optional)[0] == 0x20b
    import_rva = struct.unpack_from('<I', data, optional+120)[0]
    section_at = optional + optional_size
    ranges = []
    for i in range(sections):
        start = section_at + i * 40
        virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', data, start+8)
        ranges.append((rva, max(virtual_size, raw_size), raw))

    def offset(rva):
        for base, size, raw in ranges:
            if base <= rva < base + size:
                return raw + rva - base
        raise AssertionError('Bad PE address')

    cursor = offset(import_rva)
    names = []
    while any(data[cursor:cursor+20]):
        name_at = offset(struct.unpack_from('<I', data, cursor+12)[0])
        names.append(data[name_at:data.index(b'\0', name_at)].decode().lower())
        cursor += 20
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sfm-python', help='Also run Qt smoke against the extracted installer')
    args = parser.parse_args()
    for line in (ROOT / 'dist/SHA256SUMS.txt').read_text().splitlines():
        digest, name = line.split('  ')
        assert hashlib.sha256((ROOT / 'dist' / name).read_bytes()).hexdigest() == digest
    with tempfile.TemporaryDirectory(prefix='ReFrame café installation ') as temporary:
        destination = pathlib.Path(temporary)
        with zipfile.ZipFile(ROOT / 'dist/ReFrame.zip') as archive:
            names = archive.namelist()
            for name in names:
                builder.checkReleasePaths(archive.read(name), name)
            assert len(names) == len(set(names))
            assert [n for n in names if n.endswith('.py')] == ['scripts/sfm/mainmenu/aftre/reframe.py']
            assert all(n.startswith('scripts/sfm/mainmenu/aftre/') and '..' not in n for n in names)
            assert not any(n.endswith(('.dll', '.mp4', '.pyc', '.zip', '.7z')) for n in names)
            assert all(not any(part in n for part in ['tests/', 'tools/', '.local-checks/']) for n in names)
            prefix = 'scripts/sfm/mainmenu/aftre/reframe/runtime/'
            manifest = json.loads(archive.read(prefix + 'manifest.json'))
            assert manifest['license'] == 'LGPL-2.1-or-later'
            assert '/d1trimfile:' in manifest['compiler_path_policy']
            for filename, digest in manifest['binaries'].items():
                data = archive.read(prefix + 'bin/' + filename)
                assert hashlib.sha256(data).hexdigest() == digest
                dependencies = imports(data)
                # Static CRT: no VC/UCRT runtime installation or FFmpeg DLLs needed.
                assert set(dependencies) <= {'kernel32.dll', 'user32.dll', 'shell32.dll',
                    'ole32.dll', 'advapi32.dll', 'bcrypt.dll', 'ws2_32.dll', 'secur32.dll', 'psapi.dll'}, dependencies
                print(filename, 'system imports:', ', '.join(dependencies))
            assert b'GNU LESSER GENERAL PUBLIC LICENSE' in archive.read(prefix + 'LICENSE.txt')
            assert b'MIT License' in archive.read('scripts/sfm/mainmenu/aftre/reframe/LICENSE.txt')
            assert 'scripts/sfm/mainmenu/aftre/reframe/process.rfi' in names
            dav1d = manifest['external_codec_libraries'][0]
            assert dav1d['project'] == 'dav1d' and dav1d['license'] == 'BSD-2-Clause'
            assert b'VideoLAN and dav1d authors' in archive.read(prefix + 'dav1d-LICENSE.txt')
            archive.extractall(destination)
        with zipfile.ZipFile(ROOT / 'dist/ReFrame-sources.zip') as archive:
            for name in archive.namelist():
                builder.checkReleasePaths(archive.read(name), name)
            assert hashlib.sha256(archive.read(manifest['source']['filename'])).hexdigest() == manifest['source']['sha256']
            assert 'ReFrame/tools/ffmpeg-configure.sh' in archive.namelist()
            assert hashlib.sha256(archive.read(dav1d['source']['filename'])).hexdigest() == dav1d['source']['sha256']
        runtime = destination / 'scripts/sfm/mainmenu/aftre/reframe/runtime/bin/ffmpeg.exe'
        text = subprocess.check_output([str(runtime), '-version'], stderr=subprocess.STDOUT)
        assert ('ffmpeg version ' + manifest['version']).encode() in text
        decoders = subprocess.check_output([str(runtime), '-hide_banner', '-decoders'], stderr=subprocess.STDOUT)
        for codec in (b'h264 ', b'hevc ', b'vp9 ', b'libdav1d ', b'prores ', b'ffv1 ', b'mpeg4 ', b'dnxhd '):
            assert codec in decoders, codec
        protocols = subprocess.check_output([str(runtime), '-hide_banner', '-protocols'], stderr=subprocess.STDOUT)
        assert set(re.findall(rb'^\s+(\w+)\s*$', protocols, re.M)) == {b'file', b'pipe'}
        if args.sfm_python:
            subprocess.check_call([args.sfm_python, '-u', str(ROOT / 'tests/qt_smoke.py'),
                str(ROOT / 'tests/fixtures/Reference café/frames-30fps.mp4'), str(destination)])
    print('PASS: installer layout, hashes, x64 PE/system dependencies, licenses, source, Unicode extraction and build-path checks')


if __name__ == '__main__':
    main()
