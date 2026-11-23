<h1 align="center">ReFrame v1.0.0</h1>

<p align="center">Video references that follow Source Filmmaker's playhead.</p>
<p align="center"><strong>Python 2.7 + PySide / Qt 4 + FFmpeg</strong></p>

Keep a reference video beside SFM's viewport while you animate. ReFrame follows
the playhead and lets you line up a video pose with your shot.

[Get started](#get-started) · [Features](#features) · [Controls](#controls) · [Behavior and limits](#behavior-and-limits) · [Contribute](CONTRIBUTING.md) · [Credits](#credits-and-support)

<a id="get-started"></a>

## ◆ Get started

Use classic **Source Filmmaker on Windows 10/11, 64-bit Windows**. SFM itself remains
32-bit. No separate Python, pip, VLC, codec pack or port configuration is needed.

1. Download **`ReFrame.zip`** from the assets in [GitHub Releases](https://github.com/Atfre/ReFrame/releases).
   If no installer is available yet, follow the [local build instructions](CONTRIBUTING.md#build-the-windows-runtime-and-zip).
   GitHub's **Source code** archives and `ReFrame-sources.zip` are not installers.
2. Extract it into **`SourceFilmmaker/game/usermod/`**, merging `scripts`.
3. Restart SFM and select **Scripts > aftre > reframe**.
4. Open a video with the **folder icon** or by clicking the empty viewer.
   With a session and active shot, **Follow SFM playhead** starts automatically.

When updating an older installation, close SFM and remove the previous
`scripts/sfm/mainmenu/aftre/ReFrame.py` before extracting the new ZIP. Windows can
retain the old filename's capitalization when overwriting a file; the new entry
must be named `reframe.py` for the menu label to appear in lowercase.

The installed layout is:

```text
scripts/sfm/mainmenu/aftre/
  reframe.py
  reframe/
    timeline.rfi
    process.rfi
    viewer.rfi
    runtime/bin/ffmpeg.exe
    runtime/bin/ffprobe.exe
    runtime/...license and provenance notices...
```

The entry script resolves its location from SFM's executing filename or GAME search
paths. It does not assume a Steam drive or working directory. Internal source files
use `.rfi` to keep them out of the `*.py` script menu scan.

<a id="features"></a>

## ◆ Your reference controls

The viewer keeps its dark gray palette and follows SFM's toolbar appearance:
solid shaded symbols, raised buttons and inset fields. Text uses SFM's font family
at 11 px, with a larger 14 px shot counter. Hover over an icon for its title.
The window title is **ReFrame v1.0.0**; the filename appears inside the header.

Synchronization controls sit on the left, frame navigation in the center and view
controls on the right. The header groups Open/Close on the left and Information/Help
on the right. **F1** opens separate Quick start and Shortcuts tabs.

| Feature | What it does |
| --- | --- |
| Resizable viewer | Keeps display aspect ratio, with black bars as needed. |
| Follow SFM playhead | Uses elapsed movie seconds since the current shot starts. Holds the first/last video frame outside its range. |
| Manual alignment | Maps a displayed video pose to the current SFM playhead without typing an offset. |
| Video navigation | Clicking the timeline or stepping a frame pauses following automatically. Previous/Next select exact adjacent frames; First/Last jump to the boundaries. |
| SFM time | The read-only center counter reflects the viewport's Local Shot Time and its seconds/frames format. Video time appears beside the reference timeline. |
| Open / close | Choose a file with the picker; the X beside the folder unloads it and stops pending reads. Drag-and-drop is disabled. |
| Zoom and pan | Wheel over the image to zoom; drag to inspect a pose. Double-click or Fit restores the full image. |
| Mirror | Flips the displayed image horizontally without changing the video or alignment. |
| Focus view | Hides the controls to give the reference more space. Esc or reopening ReFrame restores them. |
| Opacity and click-through | Adjusts window opacity; a separate recovery control remains clickable while the viewer passes clicks to the viewport. |
| Single window | Running the menu entry again focuses the viewer and restores mouse input. |

<a id="controls"></a>

## ◆ Mouse and keyboard

1. Click the video timeline or use **Left / Right** to choose a pose.
   Following pauses automatically; the **chain icon** toggles it manually.
2. Scrub or step to the exact reference frame.
   Wait for the image and displayed video time to update.
3. Place SFM's playhead at the animation pose and click the **target icon** (**A**, Align to playhead).
   Following resumes with that correspondence preserved.
4. The **circular arrow** (**R**, Reset alignment) maps the current shot's start to video time zero again.

| Shortcut | Action |
| --- | --- |
| Ctrl+O / Ctrl+W | Open / close the video. |
| Left / Right | Previous / next frame. |
| Home / End | First / last frame. |
| F / A / R | Follow SFM / align to playhead / reset alignment. |
| M / 0 | Mirror / fit the image. |
| Ctrl+Space / Esc | Focus view / restore controls. |
| Ctrl+I / F1 | Video information / control guide. |

Shortcuts apply while ReFrame has focus. The opacity slider keeps its normal arrow
keys. Zoom and mirror affect the view only. **Close video** unloads the reference
without closing the window.

The center counter reads SFM's native Primary Viewport Shot Time label, with the
Secondary Viewport as a fallback. Changing the native display between seconds,
frames and timecode is reflected without changing SFM's settings or playhead.
If those labels are unavailable, ReFrame displays elapsed shot time as
`HH:MM:SS.mmm`. Synchronization always uses session seconds, independently of the
display format. Switching native formats inside SFM remains a manual check.

Alignments belong to each shot and remain in memory until you close or replace the
video, or close the viewer. They are not saved in the SFM session. ReFrame never
writes animation channels or changes session history.

Use the **pointer icon**, **Pass clicks to viewport**, for an overlay. The separate
**Restore controls** window disables it and exits focus view. Closing that window
or running the menu entry again also restores input.

<a id="behavior-and-limits"></a>

## ◆ Behavior and limits

The bundled FFmpeg reads local video in common containers including **MP4/MOV,
MKV/WebM, AVI, MPEG/TS, WMV and MXF**. Decoders include **H.264, HEVC, AV1 (dav1d),
VP8/VP9, MPEG-2/4, ProRes, DNxHD/HR, MJPEG and FFV1**. Audio is not played.
Corrupt, encrypted or unsupported media may fail to open.

Synchronization uses seconds, so a 24 fps session and a 30 fps video stay aligned:
one second in SFM advances the reference by one second.

FFmpeg runs as a child process; no video DLL is loaded into SFM. ReFrame reads
nearby timestamps and caches previews without indexing the entire video first.
There is no application limit on video duration or total frame count. Files with
sparse keyframes or poor seek indexes can still take longer. Close the reference
or choose another file to stop a slow read.

Only the latest requested position is displayed. The reader prioritizes the correct
image when the playhead stops; playback may skip frames during fast scrubbing.
Previews fit within 1280×720 while preserving display aspect ratio. No proxies or
decoded frames are written to disk.

Without an active shot, the last image remains visible and alignment is disabled.
A newly opened video can still display its first frame. Closing or replacing a
reference stops its pending reads and releases the file. Closing ReFrame also
stops its timers and closes its decoder processes.

For decoder errors, use the **information icon** to see available details and check
that the local copy is complete and readable. If a runtime file is missing,
extract the complete built ZIP again. Decoder details also appear in SFM's console
with `[ReFrame]`.

### ◇ First test inside SFM

First [generate the numbered test clip](CONTRIBUTING.md#run-the-automated-checks):
`tests/fixtures/Reference café/frames-30fps.mp4` (six seconds, 30 fps,
large frame numbers **000–179**). Test videos are not included in the repository
or installer.

1. Open a disposable 24 fps session. Create a shot beginning at movie time **10 s**.
2. Open the fixture. At movie times **10, 11 and 15 s**, expect **000, 030 and 150**.
   One session frame after 10 s shows video frame **001**. Repeat in reverse.
3. Pause following, choose **090**, put the playhead at **12 s** and align. At
   **11, 12 and 13 s**, expect **060, 090 and 120**. Jump between them; reset should
   show **060** at 12 s. After the video range, expect **179**.
4. Check one runnable ReFrame menu entry, resize, open paths containing spaces and
   accents, switch shots and close/reopen the session.
5. Test opacity and click-through over the viewport, then recover input. Close while
   decoding and reopen repeatedly. Task Manager must show no ReFrame child FFmpeg
   processes after closing. Open twice: only one viewer should exist.
6. Change the viewport's Local Shot Time display between seconds, frames and
   timecode. ReFrame's center counter should match it, including while following
   is paused. Verify the primary and secondary viewport/layout cases.

**Validation:** SFM's Python 2.7/Qt 4 and real decoded images were tested outside the
application, including the listed codecs and a 12-hour video with 1,296,000 frames.
The numbered 24/30 fps synchronization check uses simulated session values.
Live playhead behavior, menu discovery, viewport overlays and display scaling still
need the manual pass above. See [verification checks](CONTRIBUTING.md#verify-a-change).

<a id="contribute"></a>

## ◆ Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and the ZIP build. Development
tools and fixtures are excluded from the installer. See [third-party provenance](docs/third-party.md).

<a id="credits-and-support"></a>

## ◆ Credits and support

- **Author:** Aftre. ReFrame source uses the existing [MIT license](LICENSE).
- **Conceptual references:** Keyframe MP by Zurbrigg and msu355's scripts. Their code,
  binaries and original archives are not included or required.
- **Video decoding:** FFmpeg contributors; separately licensed under LGPL.

For reports, include SFM/Windows versions, video codec/rate, session rate, shot start,
alignment steps and relevant `[ReFrame]` console output.
