"""Development-only numbered H.264 fixture; no packages required (Python 3)."""
import argparse
import pathlib
import subprocess

DIGITS = ["111101101101111", "010110010010111", "111001111100111",
          "111001111001111", "101101111001001", "111100111001111",
          "111100111101111", "111001001001001", "111101111101111",
          "111101111001111"]


def frame(number):
    width, height = 640, 360
    pixels = bytearray(bytes([32, 40, 48]) * width * height)

    def rect(x, y, w, h, value):
        row = bytes([value] * 3) * w
        for line in range(y, y + h):
            start = (line * width + x) * 3
            pixels[start:start + len(row)] = row

    for bit in range(8):
        rect(20 + bit * 76, 20, 60, 40, 240 if number & (1 << bit) else 12)
    for column, digit in enumerate("%03d" % number):
        for i, value in enumerate(DIGITS[int(digit)]):
            if value == "1":
                rect(120 + column * 140 + (i % 3) * 34,
                     100 + (i // 3) * 34, 30, 30, 240)
    return pixels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", required=True, help="Developer FFmpeg with the libopenh264 encoder")
    parser.add_argument("--output", default="tests/fixtures/Reference café/frames-30fps.mp4")
    parser.add_argument("--encoder", default="libopenh264", help="Development H.264 encoder name")
    parser.add_argument("--suite", action="store_true", help="Also generate codec and long-duration regressions")
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(pathlib.Path(args.ffmpeg).resolve()), "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", "640x360", "-framerate", "30", "-i", "pipe:0", "-an",
               "-c:v", args.encoder, "-b:v", "2M", "-g", "60", "-pix_fmt", "yuv420p", str(output)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for number in range(180):
            process.stdin.write(frame(number))
    finally:
        process.stdin.close()
    if process.wait():
        raise SystemExit("Could not encode the fixture")
    print(output)
    if args.suite:
        makeSuite(pathlib.Path(args.ffmpeg).resolve(), output.resolve())


def makeSuite(ffmpeg, source):
    directory = source.parent.parent / 'formats'
    directory.mkdir(parents=True, exist_ok=True)
    formats = [
        ('mpeg4.avi', ['-c:v', 'mpeg4', '-q:v', '3']),
        ('ffv1.mkv', ['-c:v', 'ffv1']),
        ('prores.mov', ['-c:v', 'prores_ks', '-profile:v', '0', '-pix_fmt', 'yuv422p10le']),
        ('hevc.mp4', ['-c:v', 'libx265', '-preset', 'ultrafast', '-x265-params', 'pools=1:frame-threads=1:log-level=error']),
        ('vp9.webm', ['-c:v', 'libvpx-vp9', '-cpu-used', '8', '-row-mt', '1']),
        ('av1.mkv', ['-c:v', 'libaom-av1', '-cpu-used', '8', '-row-mt', '1', '-crf', '40']),
        ('mjpeg.avi', ['-c:v', 'mjpeg', '-q:v', '3', '-pix_fmt', 'yuvj420p']),
        ('mpeg2.ts', ['-c:v', 'mpeg2video', '-q:v', '3']),
        ('wmv.wmv', ['-c:v', 'wmv2', '-b:v', '2M']),
        ('dnxhr.mov', ['-c:v', 'dnxhd', '-profile:v', 'dnxhr_lb', '-pix_fmt', 'yuv422p']),
    ]
    for name, options in formats:
        subprocess.check_call([str(ffmpeg), '-v', 'error', '-y', '-i', str(source),
            '-an', '-threads', '2'] + options + [str(directory / name)])
        print(directory / name, flush=True)
    subprocess.check_call([str(ffmpeg), '-v', 'error', '-y', '-i', str(source),
        '-vf', r'select=eq(n\,0)+eq(n\,30)+eq(n\,150)', '-fps_mode', 'passthrough',
        '-c:v', 'ffv1', str(directory / 'sparse-vfr.mkv')])
    # 12 hours, 1,296,000 frames: regression for whole-file indexing and frame caps.
    subprocess.check_call([str(ffmpeg), '-v', 'error', '-y', '-f', 'lavfi', '-i',
        'testsrc2=size=64x36:rate=30:duration=43200', '-an', '-c:v', 'mpeg4',
        '-g', '60', '-q:v', '8', '-threads', '2', str(directory / 'long-12h.mp4')])
    # Exercise duration metadata when video starts after another stream.
    subprocess.check_call([str(ffmpeg), '-v', 'error', '-y', '-itsoffset', '2', '-i', str(source),
        '-f', 'lavfi', '-i', 'anullsrc=r=8000:cl=mono', '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'pcm_s16le', '-t', '8', str(directory / 'video-after-audio.mkv')])


if __name__ == "__main__":
    main()
