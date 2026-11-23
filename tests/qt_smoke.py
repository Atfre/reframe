# -*- coding: utf-8 -*-
"""Real Qt4 and decoded pixels; SFM session values are simulated. Use SFM Python."""
import os, sys, types, time, traceback, ctypes
from PySide import QtCore, QtGui

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = QtGui.QApplication.instance() or QtGui.QApplication([])
parent = QtGui.QMainWindow()
nativeParent = QtCore.QObject()
nativeParent.setProperty('font', QtGui.QFont('Tahoma', 9))
applicationFont = QtGui.QFont(app.font())


class Element(object):
    def GetId(self):
        return 'test-shot'

    def GetStartTime(self):
        return self

    def GetSeconds(self):
        return 10.0


sfm = types.ModuleType('sfmApp')
sfm.head, sfm.valid, sfm.mainWindow = 10.0, True, nativeParent
sfm.HasDocument = lambda: sfm.valid
sfm.GetMainWindow = lambda: sfm.mainWindow
sfm.GetShotAtCurrentTime = lambda: Element() if sfm.valid else None
sfm.GetHeadTimeInSeconds = lambda: sfm.head
sfm.GetFramesPerSecond = lambda: 24.0
sfm.GetDocumentRoot = lambda: Element()
sys.modules['sfmApp'] = sfm
errors = []


def callback_error(kind, value, trace):
    errors.append(repr(value))
    traceback.print_exception(kind, value, trace)


sys.excepthook = callback_error
QtGui.QMessageBox.warning = staticmethod(lambda *args: errors.append(args[-1]))
tool_root = os.path.abspath(sys.argv[2].decode(sys.getfilesystemencoding())) if len(sys.argv) > 2 else ROOT
filesystem = types.ModuleType('filesystem')
filesystem.RelativePathToFullPath = lambda relative, search: os.path.join(tool_root, relative)
sys.modules['filesystem'] = filesystem
entry = os.path.join(tool_root, 'scripts/sfm/mainmenu/aftre/reframe.py')
scope = {'__file__': 'unrelated-shared-sfm-script.py'}
with open(entry, 'rb') as source:
    entry_source = source.read()
eval(compile(entry_source, '<SFM menu>', 'exec'), scope)
assert not errors, errors
viewer = sys.modules['_aftre_reframe']
assert viewer._window.parentWidget() is None
assert viewer._window.windowFlags() & QtCore.Qt.WindowStaysOnTopHint
assert viewer._window.font().family() == 'Tahoma' and viewer._window.font().pixelSize() == 11
assert nativeParent.property('font').pointSize() == 9 and app.font() == applicationFont


def wait_until(predicate, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if errors:
            raise AssertionError(repr(errors))
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('Timeout: ' + repr(viewer._window.reader.__dict__))


def image_number(image):
    return sum((1 << bit) for bit in range(8)
               if QtGui.qRed(image.pixel(50 + bit * 76, 40)) > 128)


def mouse_event(widget, kind, point, button, buttons):
    event = QtGui.QMouseEvent(kind, point, button, buttons, QtCore.Qt.NoModifier)
    app.sendEvent(widget, event)
    app.processEvents()


def click(widget, point):
    mouse_event(widget, QtCore.QEvent.MouseButtonPress, point, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
    mouse_event(widget, QtCore.QEvent.MouseButtonRelease, point, QtCore.Qt.LeftButton, QtCore.Qt.NoButton)


def send_key(widget, key, modifiers=QtCore.Qt.NoModifier, text=''):
    for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
        app.sendEvent(widget, QtGui.QKeyEvent(kind, key, modifiers, text))
    app.processEvents()


def check_head(window, head, expected):
    sfm.head = head
    window._pollPlayhead()
    wait_until(lambda: window.displayed is not None and
               abs(window.displayed - expected / 30.0) < .0001)
    assert image_number(window.surface.image) == expected, (expected, image_number(window.surface.image))


video = os.path.abspath(sys.argv[1].decode(sys.getfilesystemencoding()))
try:
    window = viewer._window
    eval(compile(entry_source, '<SFM menu>', 'exec'), scope)
    assert viewer._window is window
    window.loadVideo(video)
    wait_until(lambda: window.reader.ready)
    # Manual time entry remains available if Follow is paused before the first image.
    window.follow.setChecked(False)
    assert window.position.isReadOnly()
    assert QtGui.QFontInfo(window.position.font()).family() == 'Tahoma'
    assert window.position.font().pixelSize() == 14
    assert window.openButton.cursor().shape() == QtCore.Qt.ArrowCursor
    window._seekTime(1)
    wait_until(lambda: window.displayed == 1)
    window.follow.setChecked(True)
    wait_until(lambda: window.displayed is not None)
    assert abs(window.reader.duration - 6) < .01
    check_head(window, 11, 30)
    check_head(window, 15, 150)
    for session_frame in list(range(30)) + list(reversed(range(30))):
        check_head(window, 10 + session_frame / 24.0, int(session_frame * 30 / 24.0))
    window.follow.setChecked(False)
    window._seekTime(3)
    wait_until(lambda: abs(window.displayed - 3) < .0001)
    window.reader.step(1)
    wait_until(lambda: abs(window.displayed - 91 / 30.0) < .0001)
    window.reader.step(-1)
    wait_until(lambda: abs(window.displayed - 3) < .0001)
    sfm.head = 12
    window._alignToPlayhead()
    assert window.follow.isChecked()
    for head, frame in [(13, 120), (11, 60), (15, 179), (10, 30), (12, 90)]:
        check_head(window, head, frame)
    window._resetAlignment()
    check_head(window, 12, 60)
    window.opacity.setValue(60)
    assert abs(window.windowOpacity() - .6) < .01
    window.clicks.setChecked(True)
    assert ctypes.windll.user32.GetWindowLongW(viewer.nativeWindowHandle(window), -20) & 0x20
    assert window.overlayHandle.isVisible() and window.overlayHandle.parentWidget() is None
    window.overlayHandle.close()
    assert not window.clicks.isChecked()
    assert not ctypes.windll.user32.GetWindowLongW(viewer.nativeWindowHandle(window), -20) & 0x20
    window.opacity.setValue(100)
    # Superseded reads, including a return to the frame already on screen.
    window.reader.imageCache.clear()
    window.reader.cacheBytes = 0
    sfm.head = 14
    window._pollPlayhead()
    wait_until(lambda: window.reader.command is not None)
    superseded = window.reader.command
    for head in [11, 15, 10.5, 14, 12]:
        sfm.head = head
        window._pollPlayhead()
    assert superseded.cancelled and superseded.handle is None
    check_head(window, 11.5, 45)
    assert len(window.reader.imageCache) <= 48
    assert window.reader.cacheBytes <= 24 * 1024 * 1024
    assert len(window.reader.times) < 180
    # No elapsed-time cutoff: a pending read stays cancellable after 30 seconds.
    window.reader.imageCache.clear()
    window.reader.cacheBytes = 0
    sfm.head = 14
    window._pollPlayhead()
    wait_until(lambda: window.reader.command is not None)
    window.reader.started = time.time() - 31
    window.reader._pollCommand()
    assert not errors
    old_reader = window.reader
    window.closeButton.click()
    assert window.reader is None and old_reader.closed
    window.loadVideo(video)
    check_head(window, 14, 120)
    sfm.valid = False
    window._pollPlayhead()
    assert window.session is None and not window.align.isEnabled()
    old_reader = window.reader
    window.close()
    app.processEvents()
    assert viewer._window is None and old_reader.closed
    sfm.valid = True
    sfm.mainWindow = parent
    viewer.showReFrame()
    window = viewer._window
    assert window.parentWidget() is parent
    window.loadVideo(video)
    wait_until(lambda: window.displayed is not None)
    window.clicks.setChecked(True)
    assert window.overlayHandle.parentWidget() is parent
    window.clicks.setChecked(False)
    sfm.head = 10 + 160 / 30.0
    window._pollPlayhead()
    wait_until(lambda: window.reader.command is not None)
    command = window.reader.command
    window.close()
    assert command.handle is None and command.cancelled
    # Replacement during metadata and opening without a valid shot.
    sfm.valid = False
    viewer.showReFrame()
    window = viewer._window
    window.loadVideo(video)
    replaced = window.reader
    window.loadVideo(video)
    assert replaced.closed
    wait_until(lambda: window.displayed == 0)
    assert not window.align.isEnabled() and image_number(window.surface.image) == 0
    # A failing native time read must not prevent opening or manual video use.
    sfm.valid = True
    original_head = sfm.GetHeadTimeInSeconds
    def unavailable_head():
        raise RuntimeError('Session time unavailable')
    sfm.GetHeadTimeInSeconds = unavailable_head
    window.loadVideo(video)
    wait_until(lambda: window.displayed == 0)
    window.follow.setChecked(False)
    window._seekTime(3)
    wait_until(lambda: abs(window.displayed - 3) < .0001)
    assert not window.align.isEnabled()
    sfm.GetHeadTimeInSeconds = original_head
    sfm.valid = False
    # Missing dependencies and local-path rejection stay actionable.
    original_root = viewer.ToolDirectory
    viewer.ToolDirectory = os.path.join(ROOT, 'tests/missing-runtime')
    window.loadVideo(video)
    assert window.reader.cancelled and len(errors) == 1
    errors[:] = []
    viewer.ToolDirectory = original_root
    window.loadVideo(video + '.missing')
    assert len(errors) == 1 and window.reader.cancelled
    errors[:] = []
    window.loadVideo(u'https://example.invalid/video.mp4')
    assert len(errors) == 1 and window.reader.command is None
    errors[:] = []
    # Direct seeking and frame buttons pause following automatically.
    sfm.valid, sfm.head = True, 10.0
    window.loadVideo(video)
    wait_until(lambda: window.displayed == 0)
    window.next.click()
    wait_until(lambda: abs(window.displayed - 1 / 30.0) < .0001)
    assert not window.follow.isChecked()
    window.follow.setChecked(True)
    wait_until(lambda: window.displayed == 0)
    point = QtCore.QPoint(window.seek.width() // 2, window.seek.height() // 2)
    target = window.seek._valueAt(point.x()) * 6.0 / window.seek.maximum()
    click(window.seek, point)
    expected = int(target * 30 + .000001)
    wait_until(lambda: abs(window.displayed - expected / 30.0) < .0001)
    assert not window.follow.isChecked()
    assert image_number(window.surface.image) == expected
    # Window-scoped navigation must not intercept the opacity slider's keys.
    QtGui.QApplication.setActiveWindow(window)
    window.surface.setFocus()
    app.processEvents()
    send_key(window.surface, QtCore.Qt.Key_Right)
    wait_until(lambda: abs(window.displayed - (expected + 1) / 30.0) < .0001)
    window._seekTime(.5)
    wait_until(lambda: abs(window.displayed - .5) < .0001)
    window.opacity.setFocus()
    window.opacity.setValue(60)
    app.processEvents()
    send_key(window.opacity, QtCore.Qt.Key_Right)
    assert window.opacity.value() == 61 and abs(window.displayed - .5) < .0001
    window.opacity.setValue(100)
    window.surface.setFocus()
    app.processEvents()
    window._seekTime(31 / 30.0)
    wait_until(lambda: abs(window.displayed - 31 / 30.0) < .0001)
    # Mirror changes rendered pixels only; the original decoded image is preserved.
    area = window.surface.imageRect()
    x = int(area.left() + area.width() * 50 / 640)
    y = int(area.top() + area.height() * 40 / 360)
    before = QtGui.QPixmap.grabWidget(window.surface).toImage()
    assert QtGui.qRed(before.pixel(x, y)) > 128
    window.mirror.click()
    after = QtGui.QPixmap.grabWidget(window.surface).toImage()
    assert QtGui.qRed(after.pixel(x, y)) < 128
    assert image_number(window.surface.image) == 31
    window.mirror.click()
    # Zoom preserves aspect ratio, pan stays bounded, double-click fits again.
    centre = window.surface.rect().center()
    wheel = QtGui.QWheelEvent(centre, 120, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
    window.surface.wheelEvent(wheel)
    assert abs(window.surface.zoom - 1.2) < .00001
    zoomed = window.surface.imageRect()
    assert abs(zoomed.width() / zoomed.height() - 640 / 360.0) < .00001
    mouse_event(window.surface, QtCore.QEvent.MouseButtonPress, centre, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
    mouse_event(window.surface, QtCore.QEvent.MouseMove, centre + QtCore.QPoint(90, 0), QtCore.Qt.NoButton, QtCore.Qt.LeftButton)
    mouse_event(window.surface, QtCore.QEvent.MouseButtonRelease, centre + QtCore.QPoint(90, 0), QtCore.Qt.LeftButton, QtCore.Qt.NoButton)
    assert 0 < window.surface.pan.x() <= (zoomed.width() - window.surface.width()) / 2
    mouse_event(window.surface, QtCore.QEvent.MouseButtonDblClick, centre, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)
    assert window.surface.zoom == 1 and window.surface.pan == QtCore.QPointF()
    send_key(window.surface, QtCore.Qt.Key_Space, QtCore.Qt.ControlModifier)
    assert window.focusView.isChecked() and all(not widget.isVisible() for widget in window.chrome)
    send_key(window.surface, QtCore.Qt.Key_Escape)
    assert not window.focusView.isChecked() and all(widget.isVisible() for widget in window.chrome)
    window.focusView.setChecked(True)
    window.clicks.setChecked(True)
    window.overlayHandle.findChild(QtGui.QPushButton).click()
    assert not window.focusView.isChecked() and not window.clicks.isChecked()
    window.focusView.setChecked(True)
    eval(compile(entry_source, '<SFM menu>', 'exec'), scope)
    assert viewer._window is window and not window.focusView.isChecked()
    # Compact and wide layouts retain equal side groups and a centered transport.
    for width, height in [(500, 320), (720, 548), (1100, 760)]:
        window.resize(width, height)
        app.processEvents()
        assert window.width() == width
        assert window.syncGroup.width() == window.viewGroup.width()
        assert abs(window.transport.geometry().center().x() - window.controls.width() / 2.0) <= 1
        assert abs(window.fileLabel.geometry().center().x() - window.header.width() / 2.0) <= 1
        for control in (window.openButton, window.follow, window.seek, window.align,
                        window.previous, window.next, window.opacity, window.clicks,
                        window.mirror, window.fit, window.focusView, window.infoButton):
            assert control.toolTip() and control.accessibleName()
        for bar in window.chrome:
            for button in bar.findChildren(QtGui.QToolButton):
                assert button.size() == QtCore.QSize(30, 30) and not button.icon().isNull()
                assert button.iconSize() == QtCore.QSize(20, 20)
                assert '<' not in button.toolTip() and '\n' not in button.toolTip()

    assert not window.acceptDrops() and not window.surface.acceptDrops()
    assert not window.surface.toolTip() and not window.fileLabel.toolTip() and not hasattr(window, 'cancel')
    assert window.windowTitle() == viewer.ProductName
    # Copy the native Local Shot Time text instead of inventing a second unit selector.
    native_clock = QtGui.QLabel(parent)
    native_clock.setObjectName('Primary Viewport Shot Time')
    parent.show()
    native_clock.show()
    window.shotClock.label = None
    window.shotClock.lastSearch = -1
    sfm.head = 12.5
    for text in ('2.500', '60', '00:00:02.500', '00:00:02:12'):
        native_clock.setText(text)
        window._pollPlayhead()
        assert window.position.text() == text and native_clock.text() == text
    generic_clock = QtCore.QObject(parent)
    generic_clock.setProperty('visible', True)
    generic_clock.setProperty('text', '00:00:02:12')
    window.shotClock.label = generic_clock
    window._pollPlayhead()
    assert window.position.text() == '00:00:02:12'
    window.shotClock.label = native_clock
    assert window.position.isReadOnly()
    # Title-only tips have enough room for their font and stay inside the screen.
    QtGui.QApplication.setActiveWindow(window)
    window.surface.setFocus()
    screen = QtGui.QApplication.desktop().availableGeometry(window)
    point = screen.bottomRight() - QtCore.QPoint(1, 1)
    event = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(5, 5), point)
    app.sendEvent(window.follow, event)
    assert window.tip.isVisible() and window.tip.text() == 'Follow SFM playhead'
    assert not window.tip.font().bold() and window.tip.textFormat() == QtCore.Qt.PlainText
    assert window.tip.width() >= window.tip.fontMetrics().boundingRect(window.tip.text()).width() + 14
    assert screen.contains(window.tip.geometry())
    app.sendEvent(window.surface, event)
    assert not window.tip.isVisible()
    window._showHelp()
    help_window = window.helpWindow
    tabs = help_window.findChild(QtGui.QTabWidget)
    assert tabs.count() == 2 and tabs.tabText(0) == 'Quick start'
    tabs.setCurrentIndex(1)
    app.processEvents()
    assert help_window.findChild(QtGui.QTreeWidget).topLevelItemCount() == 3
    help_window.close()
    window._showHelp()
    assert window.helpWindow is help_window
    help_window.close()
    window.reader.imageCache.clear()
    window.reader.cacheBytes = 0
    window._seekTime(5)
    wait_until(lambda: window.reader.command is not None)
    unloaded_reader, command = window.reader, window.reader.command
    window._closeVideo()
    assert unloaded_reader.closed and command.cancelled and command.handle is None
    assert window.reader is None and window.surface.image.isNull()
    assert not window.align.isEnabled() and not window.infoButton.isEnabled()
    print('PASS: actual Qt4 + pixels, simulated 24/30 fps, alignment, icon layout, direct seeking, shortcuts, zoom/pan/mirror, focus recovery, shot clock, title tips, help tabs and lifetime')
finally:
    if viewer._window:
        viewer._window.close()
    app.processEvents()
    parent.close()
