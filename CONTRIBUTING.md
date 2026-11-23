# Contributing to ReFrame

You can help by reporting a bug, testing the tool in SFM, improving the documentation or contributing code. Start with the [README](README.md#get-started) if you want to install and use the tool.

[Report a problem](#report-a-bug-or-suggest-a-change) · [Run locally](#run-locally) · [Code map](#find-the-code) · [Checks](#verify-a-change) · [Pull requests](#open-a-pull-request) · [AI policy](#ai-policy)

<a id="report-a-bug-or-suggest-a-change"></a>

## ◆ Report a bug or suggest a change

Check existing issues and pull requests first. For a larger feature or a change to synchronization or video dependencies, discuss the idea in an issue before implementing it.

A useful bug report includes:

- The ReFrame version shown in the window title, plus FFmpeg, SFM and Windows versions.
- The timeline editor in use: Clip, Motion or Graph.
- Steps to reproduce the problem, the expected result and what actually happened.
- Video codec/frame rate, session frame rate, shot start and any manual alignment.
- Relevant `[ReFrame]` console messages, plus a screenshot or short recording when the issue is visual.

For crashes, say whether it happened during a drag, on release, while seeking or while closing the window or session. Remove private information from logs and captures. A minimal session or reproduction is more useful than an entire project.

<a id="run-locally"></a>

## ◆ Run locally

Use **Source Filmmaker** with its bundled **Python 2.7, PySide and Qt 4** runtime. The `sfm`, `sfmApp` and `vs` bindings require SFM's running session (launching the script with a normal Python interpreter isn't a runtime test).

1. Fork or clone the repository and create a branch for your change.
2. Edit `scripts/sfm/mainmenu/aftre/reframe.py` and its internal `.rfi` source files.
3. Build the runtime and installer as described below. Extract `dist/ReFrame.zip`
   into SFM's `game/usermod` only when you intend to test that build.
4. Restart SFM after updating source, then open a disposable session and launch **Scripts > aftre > reframe**.

Keep dependency archives, extracted sources and compiler outputs in `build/`.
Fresh clones do not include `build/`, `dist/`, runtime executables, the generated
runtime manifest or test videos.
Build the runtime once and generate the fixtures needed for your checks.
Keep reusable videos in `tests/fixtures/` (excluded from Git and release packages).
Use the system temporary directory for disposable checks and clean up after use.
Never add packages to SFM's Python installation. The terminal's modern Python is only for development tools.

<a id="find-the-code"></a>

## ◆ Find the code

| Area | Source |
| --- | --- |
| Menu entry, location and singleton loader | `scripts/sfm/mainmenu/aftre/reframe.py` |
| Seconds mapping, PTS lookup, SFM reads | `reframe/timeline.rfi` |
| Qt4 viewer, on-demand decoding, lifetime and overlay | `reframe/viewer.rfi` |
| Unicode Win32 child processes and bounded pipe readers | `reframe/process.rfi` |
| Runtime compilation and packaging | `tools/build_runtime.ps1`, `tools/ffmpeg-configure.sh`, `tools/build.py` |
| Time/build unit tests | `tests/test_timeline.py`, `tests/test_build.py` |
| Qt and real decoder checks | `tests/qt_smoke.py`, `tests/reader_checks.py`, `tests/media_checks.py` |
| Native process and package checks | `tests/process_checks.py`, `tests/check_package.py` |

Internal `reframe/` paths in the table are relative to `scripts/sfm/mainmenu/aftre/`.
The `.rfi` files are ordinary Python source loaded into isolated module namespaces.
They avoid extra runnable entries in SFM's recursive `*.py` menu scan. There are no
session writes or native animation undo transactions.

### ◇ Keep changes focused

- Preserve Python 2.7 and PySide/Qt 4 compatibility. Python 3-only syntax and PySide2/PySide6 imports won't run in this runtime.
- Follow the surrounding style. Use clear names and short comments for constraints that need explaining. Preserve the author's section comments and credits. Avoid unrelated formatting or renaming passes.
- Keep native SFM and Qt access on the UI thread. Avoid heavy work in mouse handlers, paint events or polling callbacks.
- Preserve session/shot lifetime checks, request cancellation and timer cleanup.
  Keep native element proxies out of persistent state. Store shot/document IDs.
- Map seconds to presentation timestamps; do not multiply session frame numbers by
  the video's frame rate or assume constant video frame duration.
- Keep the current request as the only candidate to display. A canceled decoder
  must never show an obsolete frame or report its expected cancellation as an error.
- Do not introduce animation edits as part of a reference viewer change.
- Include the source and applicable license information when introducing third-party code or assets and retain existing attribution.

<a id="verify-a-change"></a>

## ◆ Verify a change

For documentation-only changes, check wording, local paths and links. For source
changes, compile with SFM's Python 2.7, run the relevant automated checks, then use
[the short SFM walkthrough](README.md#behavior-and-limits). Report exactly which ran.

Time/build unit tests run with development Python and need no compiler, runtime
executables or SFM session:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
```

For runtime source, also check compatibility with SFM's bundled interpreter:

```powershell
git diff --check
$sfmPython = 'YOUR_SFM/game/sdktools/python/2.7/win32/python.exe'
& $sfmPython -c "import os; [compile(open(os.path.join(p,n),'rb').read(),n,'exec') for p,d,f in os.walk('scripts') for n in f if n.endswith(('.py','.rfi'))]"
& $sfmPython tests/test_timeline.py
```

<a id="build-the-windows-runtime-and-zip"></a>

### ◇ Build the Windows runtime and ZIP

Development prerequisites: Python 3.14+ (for Zstandard archive extraction), Git for
Windows/Bash and Visual Studio C++ Build Tools with Windows SDK and the C++ CMake
tools component. The prepare step downloads Make, Meson and pkgconf into `build/`.
These are **not** animator installation requirements. No pip packages are needed.
Use PowerShell 7 from the repository root for the first build:

```powershell
python tools/prepare_build.py
./tools/build_runtime.ps1
python tools/build.py
```

The build script defaults to `C:\Program Files\Git\bin\bash.exe`. If Git is
installed elsewhere, pass its Bash path with `-Bash 'PATH_TO_GIT/bin/bash.exe'`.
Once the dependency build exists, source/UI or documentation changes only need
`python tools/build.py` to refresh the packages. Rebuild the runtime when changing
its dependencies or compilation options; use `-Reconfigure` for FFmpeg flag changes.
Use a fresh build directory after changing dependency versions or compilers.
The build creates a local `src` junction inside the FFmpeg build directory and
uses relative dependency paths. MSVC's `/d1trimfile` also removes the build directory
from embedded header filenames. This policy is recorded in the generated manifest.

`prepare_build.py` downloads the pinned source archives and build helpers listed in
`tools/dependencies.json` into `build/`, checking SHA-256. The runtime is compiled
from unmodified FFmpeg source with the flags in `ffmpeg-configure.sh`, static CRT,
native decoders and demuxers, and BMP pipe output. AV1 uses static dav1d 1.5.4
(BSD-2-Clause).
Meson 1.10.2, pkgconf 2.3.0-1 and Visual Studio's bundled Ninja are development
tools only.

`build.py` assembles `dist/ReFrame.zip`, `dist/ReFrame-sources.zip` and
`dist/SHA256SUMS.txt`. The `dist/` directory is generated locally and ignored by Git.
The installer contains runtime files and notices only. The source sidecar contains
corresponding FFmpeg source and build instructions.
The runtime's `manifest.json`, `NOTICE.txt` and license copies are generated from
the pinned dependency sources and build outputs. Update those inputs and rebuild
instead of editing the generated files or third-party license text.
The manifest is ignored by Git and included in the release packages. Keep the
license copies and `NOTICE.txt` versioned.

Before publishing, run `python tests/check_package.py`. Attach all three files to
the same [GitHub release](https://github.com/Atfre/ReFrame/releases), preserving
their filenames. GitHub's automatic Source code archives do not replace the source
sidecar. Animators only need `ReFrame.zip`.

Rebuilding the ZIP uses fixed member order and timestamps; compiling FFmpeg is not
claimed to be bit-for-bit reproducible across different compiler versions.
See [third-party provenance](docs/third-party.md).

<a id="run-the-automated-checks"></a>

### ◇ Run the automated checks

Run these commands from the repository root after building and packaging. Qt and
process checks use SFM's bundled Python; fixture generation, media comparisons and
package checks use development Python. An existing fixture can be reused.

Generate the fixture using a development FFmpeg that includes an H.264 encoder
(`libopenh264` by default). The minimal shipped decoder intentionally cannot encode
H.264. Pass an existing developer FFmpeg explicitly; it is never packaged.
Fixtures are generated or supplied locally, not downloaded with the repository.
Package checks extract into an automatically cleaned system temporary directory:

```powershell
$sfmPython = 'YOUR_SFM/game/sdktools/python/2.7/win32/python.exe'
python tools/make_test_video.py --ffmpeg 'PATH_TO_DEVELOPMENT_FFMPEG.exe'
& $sfmPython tests/qt_smoke.py 'tests/fixtures/Reference café/frames-30fps.mp4'
& $sfmPython tests/process_checks.py
& $sfmPython tests/reader_checks.py 'PATH_TO_LOCAL_VIDEO'
& $sfmPython tests/reader_checks.py --benchmark 'tests/fixtures/Reference café/frames-30fps.mp4'
python tests/media_checks.py 'tests/fixtures/Reference café/frames-30fps.mp4'
python tests/check_package.py
```

To run the Qt smoke test against the extracted installer, use the following after
generating the numbered clip. It tests a temporary path with spaces and accents:

```powershell
python tests/check_package.py --sfm-python $sfmPython
```

Use `make_test_video.py --suite` with a full developer FFmpeg for the codec suite
and a 12-hour, 30 fps video (1,296,000 frames). `--encoder libx264` selects an
alternative H.264 encoder. The suite needs libx265, libvpx-vp9, libaom-av1 and the native
FFV1, ProRes, DNxHR, MJPEG, MPEG-2/4 and WMV2 encoders. Run `reader_checks.py`
against these files for on-demand open/end/random seeks. Do not run the
full sequential pixel comparison on the long-duration fixture.

| Check | Evidence and limits |
| --- | --- |
| Python 2.7 compilation | Syntax only; does not load SFM's native bindings. |
| Time logic tests | 24/30 fps, nonzero shot, alignment, jumps, boundaries and variable timestamps. |
| Qt smoke | Bundled Qt4 and decoded pixels with simulated session values and viewport labels. Covers parent wrappers, host fonts, controls, tooltips, seeking, view/overlay recovery, singleton and cleanup. |
| Media checks | Sequential pixels versus seeks in both packet and decoded-timestamp modes, including batches, B-frames and container start times. |
| Reader benchmark | Numbered pixels, launch counts and latency during advance/reverse and continuing 24 fps requests. A local comparison, not a live SFM playback benchmark. |
| Package check | Member layout, one `.py` entry, dependency hashes, licenses, source sidecar and personal build-path checks. |
| Security checks | Bounded pipe output, Unicode native launch, restricted handle inheritance, local paths, archive/source integrity, packaging allowlists and generated-path containment. |
| Live SFM walkthrough | Menu routing, native playhead/shot semantics, session lifetime, viewport hit testing and visual scaling. Remains a separate manual check. |

When changing a shared path, check all its callers. Keep failure-path checks focused:
missing dependencies, unreadable videos, replacement during loading, no active shot
and closing while decoding. Never label simulated SFM data as live observations.

### ◇ Security review

Review processes, file access, input limits, dependency provenance and packaging.
The runtime reads the selected local file and SFM time; it does not install tools,
start network services, write animation data or modify media. Fixed `.rfi` files
are executable tool source and must come from a trusted installation.

Run `python -m unittest discover -s tests -p 'test_*.py'` for time/build regression
checks. Process checks run without Qt notifications and exercise Unicode paths,
output limits, stderr, cancellation and handle cleanup. Process output is bounded:
1 MiB for metadata, 4 MiB for timestamp queries and 16 MiB for decoded images.
Nearby images are decoded in batches of up to 12; the batch size adapts to preview
dimensions. The cache holds at most 48 images within 24 MiB. Supported codecs use
packet timing, with decoded timestamps as a fallback. There is no whole-video frame
cap. Development downloads use HTTPS and pinned SHA-256 values. Verify the upstream
release signature when changing the lock. The packager compares extracted source
against the archive and rejects unexpected runtime files without deleting them.
It also rejects local workspace and personal-directory paths in release members,
including executable strings and generated configuration. Rebuild using the
relative-path setup if this check fails; do not edit or hide the recorded options.
FFmpeg runs with the user's Windows permissions; a separate process is not a
security sandbox. Do not claim a complete vulnerability audit or label untested
component exposure as an exploit.

### ◇ Observed validation and pending SFM checks

The installed SFM interpreter was inspected: Python 2.7.5 (32-bit), PySide 1.2.0,
Qt 4.8.3. Valve's `Export_Shot_List.py` verifies FPS and shot-start APIs, and native
module symbols expose `GetHeadTimeInSeconds` and `GetShotAtCurrentTime`.
Read-only inspection of the running interface confirmed Primary/Secondary Viewport
Shot Time control names; native RTTI confirms their QLabel base. Format-copy tests
use simulated labels. Live viewport format switching remains a manual check.

Automated Qt tests use that interpreter with real decoded pixels and simulated SFM
time. Media checks compare sequential decoding with backward/random seeks across
18 short fixtures, including the codec suite, sparse variable timestamps, nonzero
origins, video after audio and H.264/HEVC B-frames. On-demand reads also pass for a
12-hour, 1,296,000-frame file; this test does not scan it sequentially. Fixtures
remain outside the installer.

The automated tests run outside SFM. Use the README walkthrough to validate movie
and shot time coordinates, menu discovery, shot/session changes, viewport input,
focus and Windows display scaling in the application.

<a id="ai-policy"></a>

## ◆ AI policy

AI assistance **doesn't** replace contributor responsibility. These rules apply to code, documentation, tests and contribution messages:

- **No AI slop or unreviewed changes.** If you submit AI-generated code or text **without** human review and cleanup, you'll be blocked from contributing. Examples include overly verbose text, unnecessary comments, overcomplicated code, failure to follow project conventions and other signs of minimal human involvement.
- **Disclose all AI use.** Name the tools you used and explain what they helped produce in your issue or pull request.
- **Understand the change.** You must be able to explain every submitted change and its effect on SFM without relying on the tool to answer for you.
- **Review and verify.** Check generated output against the actual Python 2.7/PySide APIs and run the relevant checks. Don't claim tests or results you didn't observe.
- **Follow the project.** Remove unnecessary abstractions, repetitive prose and redundant comments. Preserve existing credits and the author's section comments.
- **Write your own report.** Keep issues and pull request descriptions concise, specific and based on your observations. Don't paste unreviewed generated text or automated review replies.

Unreviewed generated submissions may be closed. Any violation of this policy may result in a contribution block. Cleaning up wording doesn't remove the disclosure requirement.

<a id="open-a-pull-request"></a>

## ◆ Open a pull request

Keep each pull request about one problem or feature. Write the description and documentation in English, consistent with the project, and include:

1. **The problem and result:** what triggers the issue and how the change behaves.
2. **The scope:** which controls or shared paths changed and why.
3. **Verification:** syntax checks and the SFM scenarios you tested with the relevant versions.
4. **Visual evidence:** before/after captures for layout or interaction changes, using a simple scene.

Update the README when installation, controls or behavior change. For an agreed
release, keep the README title, entry-script header and viewer's `ProductName` and
header on the same version. Leave dependency versions in their own manifest.
Review your diff for unrelated edits and local files before submitting it.

For contributor acknowledgments, see the [project credits](README.md#credits-and-support). Keep applicable credits when redistributing or modifying the documented source.
