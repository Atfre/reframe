# -*- coding: utf-8 -*-
"""Exercise on-demand opening/seeking of local videos in real Qt4, outside SFM."""
import os, sys, time, types, json
from PySide import QtCore, QtGui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERNAL = os.path.join(ROOT, 'scripts/sfm/mainmenu/aftre/reframe')
app = QtGui.QApplication.instance() or QtGui.QApplication([])
sfm = types.ModuleType('sfmApp')
sfm.GetMainWindow = lambda: None
sfm.HasDocument = lambda: False
sys.modules['sfmApp'] = sfm
viewer = types.ModuleType('viewer')
viewer.__file__ = os.path.join(INTERNAL, 'viewer.rfi')
for name in ('timeline', 'process'):
    module = types.ModuleType(name)
    path = os.path.join(INTERNAL, name + '.rfi')
    with open(path, 'rb') as source:
        eval(compile(source.read(), path, 'exec'), module.__dict__)
    setattr(viewer, 'native' if name == 'process' else name, module)
with open(viewer.__file__, 'rb') as source:
    eval(compile(source.read(), viewer.__file__, 'exec'), viewer.__dict__)


def wait(reader, condition):
    until = time.time() + 90
    while time.time() < until:
        app.processEvents()
        assert reader.phase != 'error', (reader.message, reader.details)
        if condition():
            return
        time.sleep(.005)
    raise AssertionError('Test deadline exceeded: ' + reader.phase)


def numbered(image):
    return sum(1 << bit for bit in range(8) if QtGui.qRed(image.pixel(50 + bit * 76, 40)) > 128)


def benchmark(reader, filename, started, launches):
    assert os.path.basename(filename) == 'frames-30fps.mp4', 'Use the numbered 30 fps fixture for --benchmark.'
    received = []
    reader.frameReady.connect(lambda pts, image: received.append((pts, numbered(image))))
    reader.requestTime(0)
    wait(reader, lambda: reader.shown is not None)
    opening = time.time() - started
    samples = []
    for frame in list(range(1, 31)) + list(reversed(range(31))):
        expected = int(frame * 30 / 24.0 + .000001)
        start = time.time()
        reader.requestTime(frame / 24.0)
        wait(reader, lambda: abs(reader.shown - expected / 30.0) < .0001)
        assert received[-1][1] == expected
        samples.append(time.time() - start)
    samples.sort()
    print(json.dumps(dict(open_seconds=opening, seeks=len(samples),
        seek_mean_seconds=sum(samples) / len(samples), seek_p95_seconds=samples[int(.95 * (len(samples) - 1))],
        decoders=launches.count('ffmpeg.exe'), probes=launches.count('ffprobe.exe'))))
    # Requests keep arriving during playback; the reader must not wait for silence.
    reader.cancelCurrent()
    reader.imageCache.clear()
    reader.cacheBytes = 0
    received[:] = []
    start, frame = time.time(), 0
    while time.time() - start < 1.5:
        elapsed = time.time() - start
        if elapsed >= frame / 24.0:
            reader.requestTime(frame / 24.0)
            frame += 1
        app.processEvents()
        time.sleep(.002)
    during_playback = len(received)
    reader.requestTime(1.5)
    wait(reader, lambda: abs(reader.shown - 1.5) < .0001)
    assert received[-1][1] == 45 and during_playback >= 3, (during_playback, received[-1])
    assert all(a[0] <= b[0] for a, b in zip(received, received[1:])), received
    print('PASS: %d displayed updates while 24 fps requests continued; final pixel frame 45' % during_playback)


benchmarking = '--benchmark' in sys.argv[1:]
nativeCommand = viewer.native.Command
launches = []
def countedCommand(executable, arguments, limit):
    launches.append(os.path.basename(executable))
    return nativeCommand(executable, arguments, limit)
if benchmarking:
    viewer.native.Command = countedCommand

for argument in [value for value in sys.argv[1:] if value != '--benchmark']:
    filename = os.path.abspath(argument.decode(sys.getfilesystemencoding()))
    reader = viewer.VideoReader()
    images = []
    reader.frameReady.connect(lambda seconds, image: images.append((seconds, image)))
    try:
        started = time.time()
        reader.open(filename)
        wait(reader, lambda: reader.ready)
        metadata_time = time.time() - started
        if benchmarking:
            benchmark(reader, filename, started, launches)
            continue
        for seconds in [0, reader.duration / 2, reader.duration, reader.duration / 4, 0]:
            images[:] = []
            # Re-requesting the displayed frame needs no signal.
            reader.shown = None
            reader.requestTime(seconds)
            wait(reader, lambda: bool(images))
            actual, image = images[-1]
            assert not image.isNull() and image.width() <= 1280 and image.height() <= 720
            assert actual <= seconds + .000051 or seconds == 0, (actual, seconds)
            assert len(reader.imageCache) <= 48 and reader.cacheBytes <= 24 * 1024 * 1024
        if os.path.basename(filename) == 'sparse-vfr.mkv':
            for direction, expected in [(1, 1), (1, 5), (-1, 1), (-1, 0)]:
                reader.step(direction)
                wait(reader, lambda: abs(reader.shown - expected) < .000051)
        print('PASS: %s; %s; %.3fs duration; %.3fs metadata; %d timestamps in last window' %
            (os.path.basename(filename).encode('ascii', 'replace'), reader.info['codec'], reader.duration,
             metadata_time, len(reader.times)))
    finally:
        reader.close()
