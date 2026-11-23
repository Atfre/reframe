"""Compare actual sequential/seek BMP bytes using only the packaged decoder."""
import hashlib
import json
import pathlib
import random
import struct
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
INTERNAL = ROOT / 'scripts/sfm/mainmenu/aftre/reframe'
BIN = INTERNAL / 'runtime/bin'
timeline = types.ModuleType('timeline')
exec(compile((INTERNAL / 'timeline.rfi').read_bytes(), 'timeline.rfi', 'exec'), timeline.__dict__)


def probe(video):
    return json.loads(subprocess.check_output([str(BIN / 'ffprobe.exe'), '-v', 'error',
        '-select_streams', 'v:0', '-show_frames', '-show_packets', '-show_format', '-show_streams',
        '-show_entries', 'frame=best_effort_timestamp_time,pict_type:packet=pts_time,dts_time,flags:format=start_time,duration:stream=start_time,duration,avg_frame_rate,r_frame_rate,nb_frames,width,height,codec_name:stream_tags=DURATION',
        '-of', 'json', str(video)]))


def read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise AssertionError('Incomplete BMP stream')
        data.extend(chunk)
    return data


def run(arguments):
    result = subprocess.run(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr.decode('utf-8', 'replace')[-2000:]
    return result.stdout


def check(video):
    info = probe(video)
    entries = info['packets_and_frames']
    frames = [entry for entry in entries if entry['type'] == 'frame']
    timestamps = [float(f['best_effort_timestamp_time']) for f in frames]
    origin = float(info.get('format', {}).get('start_time', 0))
    media = timeline.videoMetadata(info)
    command = [str(BIN / 'ffmpeg.exe')] + timeline.decodeArguments(str(video), timestamps[0])
    at = command.index('-frames:v')
    del command[at:at+2]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    hashes = []
    try:
        while True:
            marker = process.stdout.read(2)
            if not marker:
                break
            assert marker == b'BM', marker
            header = read_exact(process.stdout, 12)
            size = struct.unpack_from('<I', header)[0]
            image = marker + header + read_exact(process.stdout, size - 14)
            hashes.append(hashlib.sha256(image).digest())
        error = process.stderr.read()
        assert process.wait() == 0, error
    finally:
        process.stdout.close()
        process.stderr.close()
        if process.poll() is None:
            process.kill()
            process.wait()
    assert len(hashes) == len(timestamps), (len(hashes), len(timestamps))
    indices = {0, 1, len(hashes)-1, len(hashes)//2, min(30, len(hashes)-1), min(150, len(hashes)-1)}
    indices.update(random.Random(4).sample(range(len(hashes)), min(20, len(hashes))))
    for index in sorted(indices, reverse=True):
        for packets in (False, True):
            data = run([str(BIN / 'ffprobe.exe')] + timeline.windowArguments(
                str(video), media['origin'], timestamps[index] - media['origin'], media['fps'], packetsOnly=packets))
            local, localPts, localDts = timeline.readWindow(data, media['origin'], packets)
            selected = local[timeline.frameAtTime(local, timestamps[index])]
            assert abs(selected - timestamps[index]) < .000051, (video.name, index, selected, packets)
            anchor = timeline.findSeekAnchor(localPts, localDts, selected)
            count = min(12, len(hashes) - index)
            data = run([str(BIN / 'ffmpeg.exe')] + timeline.decodeArguments(
                str(video), timestamps[index], anchor, origin, count))
            actual = [hashlib.sha256(image).digest() for image in timeline.bitmapFrames(data, count)]
            assert actual == hashes[index:index + count], (video.name, index, packets)
    print('PASS:', video.name, len(hashes), 'actual frames;', len(indices), 'seeks in both timing modes, batches up to 12;',
          sum(f.get('pict_type') == 'B' for f in frames), 'B-frames')


if __name__ == '__main__':
    for name in sys.argv[1:]:
        check(pathlib.Path(name).resolve())
