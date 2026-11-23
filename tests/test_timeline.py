"""Pure time logic tests. Compatible with SFM's Python 2.7 and Python 3."""
import os
import struct
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
timeline = types.ModuleType('timeline')
path = os.path.join(ROOT, 'scripts/sfm/mainmenu/aftre/reframe/timeline.rfi')
with open(path, 'rb') as source:
    eval(compile(source.read(), path, 'exec'), timeline.__dict__)


class TimeTests(unittest.TestCase):
    def setUp(self):
        self.pts = [i / 30.0 for i in range(180)]
        self.mapping = timeline.Alignment()

    def test_24fps_session_30fps_video_at_every_session_frame(self):
        for frame in range(144):
            seconds = frame / 24.0
            self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(seconds, 0)),
                             min(179, int(seconds * 30 + 0.000001)))
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(1, 0)), 30)
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(5, 0)), 150)

    def test_nonzero_shot_start_and_out_of_range(self):
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(11, 10)), 30)
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(15, 10)), 150)
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(9, 10)), 0)
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(50, 10)), 179)

    def test_alignment_backwards_forwards_jumps_reset(self):
        self.mapping.align(12, 10, 3)
        for head in [12, 13, 11, 15, 10, 12 + 1 / 24.0, 12 - 1 / 24.0]:
            self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(head, 10)),
                             max(0, min(179, int((head - 9) * 30 + 0.000001))))
        self.mapping.reset()
        self.assertEqual(timeline.frameAtTime(self.pts, self.mapping.target(12, 10)), 60)

    def test_variable_frame_timestamps_and_sfm_tick_rounding(self):
        pts = [0, .04, .12, .135, .3]
        self.assertEqual(timeline.frameAtTime(pts, .119), 1)
        self.assertEqual(timeline.frameAtTime(pts, .2), 3)
        self.assertEqual(timeline.frameAtTime(self.pts, 1.0333), 31)
        self.assertEqual(timeline.frameAtTime(self.pts, 1.0332), 30)
        with self.assertRaises(ValueError):
            timeline.frameAtTime(pts, float('nan'))

    def test_long_video_metadata_does_not_require_a_frame_index(self):
        info = timeline.videoMetadata({'streams': [{'duration': '360000',
            'avg_frame_rate': '30000/1001', 'start_time': '2'}]})
        self.assertEqual(info['duration'], 360000)
        self.assertAlmostEqual(info['fps'], 29.97002997)
        args = timeline.windowArguments('local.mp4', 2, 359999, info['fps'])
        self.assertIn('359999.000000000%360001.500000000', args)
        self.assertEqual(timeline.timeLabel(360000), '100:00:00.000')

    def test_local_interval_and_invalid_timestamp_records(self):
        data = (b'packet|pts_time=2.1|dts_time=2.0|flags=K__\n'
                b'frame|best_effort_timestamp_time=2.100000\n'
                b'frame|best_effort_timestamp_time=2.133333\n')
        times, pts, dts = timeline.readWindow(data, 2.1)
        self.assertEqual(times, [2.1, 2.133333])
        self.assertEqual(timeline.findSeekAnchor(pts, dts, 2.12), 2.0)
        for invalid in (b'frame|best_effort_timestamp_time=nan', b'x' * 65537,
                        b'frame|best_effort_timestamp_time=3\nframe|best_effort_timestamp_time=2'):
            with self.assertRaises(ValueError):
                timeline.readWindow(invalid, 0)

    def test_video_duration_excludes_leading_audio(self):
        metadata = {'streams': [{'start_time': '2', 'tags': {'DURATION': '00:00:08.000'}}],
                    'format': {'start_time': '0', 'duration': '60'}}
        self.assertEqual(timeline.videoMetadata(metadata)['duration'], 6)
        del metadata['streams'][0]['tags']
        self.assertEqual(timeline.videoMetadata(metadata)['duration'], 58)

    def test_packet_timing_is_sorted_and_does_not_request_decoded_frames(self):
        args = timeline.windowArguments('local.mp4', 0, 1, 30, packetsOnly=True)
        self.assertNotIn('-show_frames', args)
        self.assertNotIn('frame=', args[args.index('-show_entries') + 1])
        records = b'packet|pts_time=.2|dts_time=0|flags=K__\npacket|pts_time=.1|dts_time=.1|flags=___'
        self.assertEqual(timeline.readWindow(records, 0, True)[0], [.1, .2])
        with self.assertRaises(ValueError):
            timeline.readWindow(b'packet|pts_time=N/A|flags=___', 0, True)

    def test_bitmap_batch_sizes_dimensions_and_count_are_bounded(self):
        bmp = bytearray(54)
        bmp[:2] = b'BM'
        struct.pack_into('<I', bmp, 2, 54)
        struct.pack_into('<ii', bmp, 18, 640, 360)
        bmp = bytes(bmp)
        self.assertEqual(len(list(timeline.bitmapFrames(bmp + bmp, 2))), 2)
        for invalid, count in ((bmp[:-1], 1), (bmp + bmp, 1), (b'xx' + bmp[2:], 1)):
            with self.assertRaises(ValueError):
                list(timeline.bitmapFrames(invalid, count))
        bad = bytearray(bmp)
        struct.pack_into('<i', bad, 18, 999999)
        with self.assertRaises(ValueError):
            list(timeline.bitmapFrames(bytes(bad), 1))


if __name__ == '__main__':
    unittest.main()
