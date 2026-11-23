"""Fetch pinned source/build tools, never install anything into SFM (Python 3.14+)."""
import hashlib
import json
import pathlib
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / 'build'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    locks = json.loads((ROOT / 'tools/dependencies.json').read_text())
    for key, dependency in locks.items():
        target = WORK / dependency['filename']
        if not target.exists() or digest(target) != dependency['sha256']:
            print('Downloading', dependency['url'])
            temporary = target.with_suffix(target.suffix + '.part')
            urllib.request.urlretrieve(dependency['url'], temporary)
            if digest(temporary) != dependency['sha256']:
                raise SystemExit('SHA-256 mismatch: ' + dependency['filename'])
            temporary.replace(target)
        destinations = {'make_development_only': WORK / 'msys-make',
                        'pkgconf_development_only': WORK / 'msys-pkgconf',
                        'meson_development_only': WORK, 'dav1d_source': WORK}
        if key in destinations:
            with tarfile.open(target) as archive:
                archive.extractall(destinations[key], filter='data')
        print('Verified', target.name)


if __name__ == '__main__':
    main()
