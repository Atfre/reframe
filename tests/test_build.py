"""Release packaging checks that do not need the compiler or SFM."""
import importlib.util
import io
import pathlib
import tarfile
import tempfile
import unittest
import zipfile
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reframe_build', ROOT / 'tools/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / 'build'
        work.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='build-check-', dir=work)
        self.directory = pathlib.Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def test_unexpected_runtime_file_is_reported_and_preserved(self):
        sentinel = self.directory / 'keep-me.txt'
        sentinel.write_text('User file')
        with self.assertRaisesRegex(SystemExit, 'Unexpected runtime files'):
            builder.checkRuntimeDirectory(self.directory)
        self.assertEqual(sentinel.read_text(), 'User file')

    def test_only_expected_executables_are_accepted(self):
        for name in ('ffmpeg.exe', 'ffprobe.exe'):
            (self.directory / name).write_bytes(b'placeholder')
        builder.checkRuntimeDirectory(self.directory)

    def test_generated_path_cannot_leave_repository(self):
        with self.assertRaisesRegex(SystemExit, 'leaves the repository'):
            builder.checkWorkspacePath(ROOT / '..' / 'outside-runtime')

    def test_modified_source_cannot_be_packaged_as_upstream_source(self):
        source = self.directory / 'ffmpeg'
        source.mkdir()
        archivePath = self.directory / 'source.tar'
        original = b'Original upstream source\n'
        with tarfile.open(archivePath, 'w') as archive:
            member = tarfile.TarInfo('ffmpeg/source.c')
            member.size = len(original)
            archive.addfile(member, io.BytesIO(original))
        sourceFile = source / 'source.c'
        sourceFile.write_bytes(original)
        builder.checkSourceTree(archivePath, source)
        sourceFile.write_bytes(b'Modified source\n')
        with self.assertRaisesRegex(SystemExit, 'differs from the pinned archive'):
            builder.checkSourceTree(archivePath, source)

    def test_personal_paths_are_rejected_in_text_and_binaries(self):
        profile = 'C:/' + 'Users/Example'
        samples = [profile, profile.replace('/', '\\'), profile.replace('/', '\\\\'),
                   '/c/' + 'Users/Example', '/cygdrive/c/' + 'Users/Example',
                   '/' + 'home/example/project', str(ROOT / 'build' / 'source.c')]
        for value in samples:
            for encoding in ('utf-8', 'utf-16-le'):
                with self.subTest(value=value, encoding=encoding):
                    with self.assertRaises(SystemExit):
                        builder.checkReleasePaths(value.encode(encoding), 'fixture')
        with mock.patch.object(builder, 'ROOT', pathlib.Path('D:/release-work')):
            for prefix in ('D:/release-work', '/d/release-work', '/cygdrive/d/release-work'):
                with self.assertRaises(SystemExit):
                    builder.checkReleasePaths((prefix + '/source.c').encode(), 'fixture')

    def test_package_rejects_personal_paths_without_rewriting_the_input(self):
        path = self.directory / 'config.txt'
        original = ('prefix=C:/' + 'Users/Example/build').encode()
        path.write_bytes(original)
        with zipfile.ZipFile(io.BytesIO(), 'w') as archive:
            with self.assertRaises(SystemExit):
                builder.add(archive, path, 'config.txt')
            self.assertEqual(archive.namelist(), [])
        self.assertEqual(path.read_bytes(), original)

    def test_relative_build_configuration_is_preserved(self):
        path = self.directory / 'config.txt'
        original = b'SRC_PATH=src\nPKG_CONFIG=../msys-pkgconf/usr/bin/pkgconf.exe\n'
        path.write_bytes(original)
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            builder.add(archive, path, 'config.txt')
        with zipfile.ZipFile(data) as archive:
            self.assertEqual(archive.read('config.txt'), original)


if __name__ == '__main__':
    unittest.main()
