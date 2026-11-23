# -*- coding: utf-8 -*-
"""Windows pipes without a Qt event loop. Run with SFM's Python 2.7."""
import ctypes, os, shutil, sys, tempfile, time, types
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERNAL = os.path.join(ROOT, 'scripts/sfm/mainmenu/aftre/reframe')
native = types.ModuleType('reframe_process')
with open(os.path.join(INTERNAL, 'process.rfi'), 'rb') as source:
    eval(compile(source.read(), 'process.rfi', 'exec'), native.__dict__)


def result(command):
    try:
        until = time.time() + 15
        while time.time() < until:
            value = command.result()
            if value is not None:
                return value
            time.sleep(.005)
        raise AssertionError('Child did not finish')
    finally:
        command.close()


def handles():
    count = wintypes.DWORD()
    assert ctypes.windll.kernel32.GetProcessHandleCount(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(count))
    return count.value


temporary = tempfile.mkdtemp(prefix='ReFrame-process-').decode(sys.getfilesystemencoding())
try:
    directory = os.path.join(temporary, u'Reference café 漢字 & (local)')
    os.mkdir(directory)
    probe = os.path.join(directory, 'ffprobe.exe')
    shutil.copyfile(os.path.join(INTERNAL, 'runtime/bin/ffprobe.exe'), probe)
    video = os.path.join(directory, u'video café 漢字 & (local).mp4')
    shutil.copyfile(os.path.join(ROOT.decode(sys.getfilesystemencoding()), u'tests/fixtures/Reference café/frames-30fps.mp4'), video)
    code, output, error, failure = result(native.Command(probe,
        ['-v', 'error', '-show_format', '-of', 'json', video], 1048576))
    assert code == 0 and b'format' in output and not failure, (code, error, failure)
    code, output, error, failure = result(native.Command(probe,
        ['-v', 'error', '-show_frames', '-of', 'json', video], 32))
    assert failure and len(output) <= 32, (code, failure)
    code, output, error, failure = result(native.Command(probe,
        ['-v', 'error', video + '.missing'], 1048576))
    assert code != 0 and error
    command = native.Command(probe, ['-show_frames', video], 1048576)
    command.close()
    assert command.cancelled and command.handle is None
    assert not any(thread.is_alive() for thread in command.threads)
    baseline = handles()
    for unused in range(20):
        assert result(native.Command(probe, ['-v', 'error', '-show_format', video], 1048576))[0] == 0
    assert handles() <= baseline + 2, (baseline, handles())
    print('PASS: no Qt event loop; Unicode executable/media paths, bounded output, stderr, cancellation and handle cleanup')
finally:
    shutil.rmtree(temporary)
