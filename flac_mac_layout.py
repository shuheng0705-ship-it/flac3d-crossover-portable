# FLAC3D Mac layout controller v1. Python 2.7 / Qt 4 compatible.
# This is an application layout policy, not an input/event automation script.
import json, os, traceback
from PySide import QtCore, QtGui
def direct_central_widget(window):
    # Native FLAC subclasses are exposed by PySide as generic QWidget wrappers.
    # The central content is the direct child that is not a dock or a toolbar.
    excluded = ('QDockWidget', 'QToolBar', 'QMenuBar', 'QStatusBar', 'QSizeGrip')
    candidates = [c for c in window.children()
                  if c.isWidgetType() and hasattr(c, 'width')
                  and not c.isWindow()
                  and not any(c.inherits(name) for name in excluded)]
    return max(candidates, key=lambda c: c.width() * c.height()) if candidates else None

def central_widget(window):
    if hasattr(window, 'centralWidget'):
        return window.centralWidget()
    return direct_central_widget(window)

def dock_widgets(window):
    return [d for d in window.findChildren(QtGui.QWidget) if d.inherits('QDockWidget')]

class FlacMacLayoutController(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.window = None
        self.attempts = 0
        self.waiter = QtCore.QTimer(self)
        self.waiter.setInterval(250)
        self.waiter.timeout.connect(self.discover)
        self.pending = QtCore.QTimer(self)
        self.pending.setSingleShot(True)
        self.pending.timeout.connect(self.apply_policy)
        self.recorder = QtCore.QTimer(self)
        self.recorder.setSingleShot(True)
        self.recorder.timeout.connect(self.record)
        self.status_path = os.environ.get('FLAC3D_LAYOUT_DIAGNOSTIC', 'C:/flac3d-launcher/layout-runtime.json')

    @QtCore.Slot()
    def start(self):
        self.discover()
        if self.window is None:
            self.waiter.start()

    @QtCore.Slot()
    def discover(self):
        self.attempts += 1
        widgets = QtGui.QApplication.allWidgets()
        windows = [w for w in widgets if w.inherits('QMainWindow')]
        if self.attempts == 1 or self.attempts % 20 == 0:
            self.write_status({'phase': 'discovering', 'attempts': self.attempts, 'widget_count': len(widgets), 'main_window_candidates': [{'class': unicode(w.metaObject().className()), 'python_type': type(w).__name__, 'name': unicode(w.objectName()), 'width': w.width(), 'height': w.height()} for w in windows], 'top_level_widgets': [{'class': unicode(w.metaObject().className()), 'python_type': type(w).__name__, 'name': unicode(w.objectName()), 'width': w.width(), 'height': w.height()} for w in QtGui.QApplication.topLevelWidgets()]})
        if windows:
            self.window = max(windows, key=lambda w: w.width() * w.height())
            self.waiter.stop()
            self.window.installEventFilter(self)
            self.pending.start(120)
        elif self.attempts >= 240:
            self.waiter.stop()
            self.record_discovery_failure()

    def record_discovery_failure(self):
        widgets = QtGui.QApplication.allWidgets()
        self.write_status({'error': 'Main window not found within 60 seconds', 'widget_count': len(widgets), 'top_level_widgets': [{'class': unicode(w.metaObject().className()), 'python_type': type(w).__name__, 'name': unicode(w.objectName()), 'width': w.width(), 'height': w.height()} for w in QtGui.QApplication.topLevelWidgets()], 'large_widgets': [{'class': unicode(w.metaObject().className()), 'name': unicode(w.objectName()), 'width': w.width(), 'height': w.height()} for w in widgets if w.width()>500 and w.height()>300]})

    def eventFilter(self, target, event):
        if target is self.window and event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show, QtCore.QEvent.LayoutRequest):
            if not self.pending.isActive():
                self.pending.start(120)
        return False

    @QtCore.Slot()
    def apply_policy(self):
        try:
            w = self.window
            if w is None or w.width() < 600:
                return
            central = central_widget(w)
            if central is not None:
                # Reserve most of the actual client width for the docked plot/editor.
                cap = max(240, int(w.width() * 0.22))
                if central.minimumWidth() > cap:
                    central.setMinimumWidth(cap)
                if central.maximumWidth() != cap:
                    central.setMaximumWidth(cap)
            for dock in dock_widgets(w):
                if unicode(dock.objectName()) == 'Project_Project' and not dock.isWindow():
                    cap = max(180, int(w.width() * 0.15))
                    if dock.minimumWidth() > cap:
                        dock.setMinimumWidth(cap)
                    if dock.maximumWidth() != cap:
                        dock.setMaximumWidth(cap)
            self.recorder.start(180)
        except Exception:
            self.write_status({'error': traceback.format_exc()})

    def write_status(self, status):
        try:
            with open(self.status_path, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception:
            pass

    @QtCore.Slot()
    def record(self):
        try:
            w = self.window
            if w is None:
                return
            c = central_widget(w)
            self.write_status({
                'controller_version': 1,
                'window': {'width': w.width(), 'height': w.height()},
                'central': None if c is None else {'class': unicode(c.metaObject().className()), 'width': c.width(), 'maximum_width': c.maximumWidth(), 'minimum_hint_width': c.minimumSizeHint().width()},
                'docks': [{'name': unicode(d.objectName()), 'width': d.width(), 'height': d.height(), 'maximum_width': d.maximumWidth(), 'floating': d.isWindow(), 'visible': d.isVisible()} for d in dock_widgets(w)],
                'gui_thread': QtCore.QThread.currentThread() == QtGui.QApplication.instance().thread()
            })
        except Exception:
            self.write_status({'error': traceback.format_exc()})

_controller = None

def install():
    global _controller
    app = QtGui.QApplication.instance()
    if app is None:
        raise RuntimeError('QApplication is not available')
    if _controller is None:
        _controller = FlacMacLayoutController()
        _controller.moveToThread(app.thread())
        QtCore.QMetaObject.invokeMethod(_controller, 'start', QtCore.Qt.QueuedConnection)
    return True
