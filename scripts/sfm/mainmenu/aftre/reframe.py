# -*- coding: utf-8 -*-
#===================================================================================== #
# [SFM] ReFrame v1.0.0
#
# This script opens a video reference window in Source Filmmaker that follows
# the current shot and playhead with manual alignment to match reference poses.
#
# Credits:
# Script based off Keyframe MP by Zurbrigg and msu355's scripts.
# FFmpeg contributors for video decoding.
# VideoLAN and dav1d authors for the AV1 decoder.
#
# Author: Aftre
# ===================================================================================== #

import os, sys, types


# -- Script entry and tool location --- #

def showReFrame(entryFilename):
    from PySide import QtGui
    try:
        module = sys.modules.get('_aftre_reframe')
        if module is None:
            # SFM executes menu scripts in a shared scope; __file__ is not reliable.
            def _localFile(value):
                if not value:
                    return None
                candidates = [value]
                if isinstance(value, bytes):
                    candidates = []
                    for encoding in ('utf-8', sys.getfilesystemencoding()):
                        try:
                            candidates.append(value.decode(encoding))
                        except UnicodeError:
                            pass
                return next((p for p in candidates
                             if os.path.isabs(p) and os.path.isfile(p)), None)
            filename = _localFile(entryFilename)
            if filename is None:
                import filesystem
                filename = _localFile(filesystem.RelativePathToFullPath(
                    'scripts/sfm/mainmenu/aftre/reframe.py', 'GAME'))
            if not filename or not os.path.isfile(filename):
                raise IOError('reframe.py was not found in SFM search paths.')
            folder = os.path.join(os.path.dirname(filename), 'reframe')
            timeline = types.ModuleType('_aftre_reframe_timeline')
            timelinePath = os.path.join(folder, 'timeline.rfi')
            with open(timelinePath, 'rb') as source:
                eval(compile(source.read(), timelinePath.encode('utf-8'), 'exec'), timeline.__dict__)
            module = types.ModuleType('_aftre_reframe')
            module.__file__ = os.path.join(folder, 'viewer.rfi')
            module.timeline = timeline
            native = types.ModuleType('_aftre_reframe_process')
            nativePath = os.path.join(folder, 'process.rfi')
            with open(nativePath, 'rb') as source:
                eval(compile(source.read(), nativePath.encode('utf-8'), 'exec'), native.__dict__)
            module.native = native
            with open(module.__file__, 'rb') as source:
                eval(compile(source.read(), module.__file__.encode('utf-8'), 'exec'), module.__dict__)
            sys.modules['_aftre_reframe'] = module
        module.showReFrame()
    except Exception as error:
        import traceback
        traceback.print_exc()
        QtGui.QMessageBox.warning(None, 'ReFrame',
            u'Could not open ReFrame. Extract the complete ZIP again into '
            u'game/usermod. Details: %s' % error)

showReFrame(sys._getframe().f_code.co_filename)
