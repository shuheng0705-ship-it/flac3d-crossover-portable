# FLAC3D 6 saved command-file compatibility. Python 2.7 / Qt 4 / Windows.
# Stores GBK for the native System-936 reader, preserving Unicode text.
# Enabled only after the user approves this save format. No model/locale changes.
import ctypes as c
from ctypes import wintypes as wt
import hashlib, json, os, stat, tempfile, time, traceback
from PySide import QtCore, QtGui

BOM = '\xef\xbb\xbf'
MAX_BYTES = 2 * 1024 * 1024
BASE = 'C:/flac3d-launcher'
REPORT = BASE + '/gbk-save-runtime.json'
BACKUPS = BASE + '/gbk-save-backups'
EXTENSIONS = ('.f3dat', '.dat', '.f3edat')

def needs_gbk(raw):
    if not raw or len(raw) > MAX_BYTES or '\0' in raw:
        return False
    if not any(ord(ch) >= 128 for ch in raw):
        return False
    try:
        raw.decode('utf-8-sig', 'strict').encode('gbk', 'strict')
    except UnicodeError:
        return False
    return True

def preserve_gbk(path, expected, backup_root=BACKUPS):
    """Back up exact saved bytes; encode matching text losslessly as GBK."""
    result = {'path': path, 'applied': False}
    if os.path.splitext(path)[1].lower() not in EXTENSIONS:
        return result
    if os.path.islink(path) or not os.path.isfile(path):
        return result
    with open(path, 'rb') as source:
        raw = source.read(MAX_BYTES + 4)
    if not needs_gbk(raw) or (raw[3:] if raw.startswith(BOM) else raw) != expected:
        return result
    unicode_text = raw.decode('utf-8-sig', 'strict')
    encoded = unicode_text.encode('gbk', 'strict')
    if encoded.decode('gbk', 'strict') != unicode_text:
        raise UnicodeError('Lossless GBK conversion unavailable; original retained')
    source_stat = os.stat(path)
    digest = hashlib.sha256(raw).hexdigest()
    if not os.path.isdir(backup_root):
        os.makedirs(backup_root)
    backup = os.path.join(backup_root, digest + '.bin')
    if not os.path.exists(backup):
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY, 0600)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    with open(backup, 'rb') as saved:
        if saved.read() != raw:
            raise IOError('Backup verification failed; original left unchanged')
    fd, temporary = tempfile.mkstemp(prefix='.flac-gbk-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, stat.S_IMODE(source_stat.st_mode))
        with open(path, 'rb') as source:
            if source.read(MAX_BYTES + 4) != raw:
                result['skipped'] = 'File changed during verification'
                return result
        move = c.windll.kernel32.MoveFileExW
        move.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.DWORD]
        move.restype = wt.BOOL
        if not move(unicode(temporary), unicode(path), 1 | 8):
            raise c.WinError()
        temporary = None
        with open(path, 'rb') as source:
            after = source.read()
        if after != encoded:
            raise IOError('GBK save verification failed')
        result.update(applied=True, backup=backup, original_sha256=digest,
                      text_unchanged=after.decode('gbk') == unicode_text,
                      ascii_command_lines_unchanged=[line for line in expected.splitlines() if all(ord(ch) < 128 for ch in line) and not line.lstrip().startswith(';')] == [line for line in encoded.splitlines() if all(ord(ch) < 128 for ch in line) and not line.lstrip().startswith(';')],
                      saved_sha256=hashlib.sha256(after).hexdigest())
        return result
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)

def project_files(project):
    """Only files explicitly listed in the current project's Editor entry."""
    if not project or not os.path.isfile(project):
        return []
    with open(project, 'rb') as source:
        data = json.loads(source.read().decode('utf-8-sig'))
    paths = []
    for module in data.get('GuiModuleList', []):
        if module.get('Name') != 'Editor':
            continue
        entry = module.get('Entry', {})
        files = entry.get('DataFiles', {}).get('Files', []) + entry.get('OpenFiles', [])
        for filename in files:
            if not isinstance(filename, basestring):
                continue
            path = os.path.normpath(os.path.join(os.path.dirname(project), filename))
            if os.path.splitext(path)[1].lower() in EXTENSIONS and path not in paths:
                paths.append(path)
    return paths

class NMHDR(c.Structure):
    _fields_ = [('hwndFrom', wt.HWND), ('idFrom', c.c_size_t), ('code', wt.UINT)]

class GbkSaveController(QtCore.QObject):
    SUBCLASS_ID = 0x464C4143

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.tick)
        self.user = c.windll.user32
        self.common = c.windll.comctl32
        self.user.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, c.c_int]
        self.user.GetParent.argtypes = [wt.HWND]
        self.user.GetParent.restype = wt.HWND
        self.user.IsWindow.argtypes = [wt.HWND]
        self.user.GetWindowThreadProcessId.argtypes = [wt.HWND, c.POINTER(wt.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wt.DWORD
        self.user.SendMessageW.argtypes = [wt.HWND, wt.UINT, c.c_size_t, c.c_ssize_t]
        self.user.SendMessageW.restype = c.c_ssize_t
        self.enum_type = c.WINFUNCTYPE(wt.BOOL, wt.HWND, c.c_ssize_t)
        self.user.EnumChildWindows.argtypes = [wt.HWND, self.enum_type, c.c_ssize_t]
        self.subclass_type = c.WINFUNCTYPE(c.c_ssize_t, wt.HWND, wt.UINT,
            c.c_size_t, c.c_ssize_t, c.c_size_t, c.c_size_t)
        self.callback = self.subclass_type(self.window_proc)
        self.common.SetWindowSubclass.argtypes = [wt.HWND, self.subclass_type, c.c_size_t, c.c_size_t]
        self.common.SetWindowSubclass.restype = wt.BOOL
        self.common.RemoveWindowSubclass.argtypes = [wt.HWND, self.subclass_type, c.c_size_t]
        self.common.DefSubclassProc.argtypes = [wt.HWND, wt.UINT, c.c_size_t, c.c_ssize_t]
        self.common.DefSubclassProc.restype = c.c_ssize_t
        self.convert = c.pythonapi.PyCObject_AsVoidPtr
        self.convert.argtypes = [c.py_object]
        self.convert.restype = c.c_void_p
        self.editors = set()
        self.parents = set()
        self.busy = False
        self.events = []
        self.errors = []
        self.total = 0
        self.save_notifications = 0
        self.last_report = 0
        self.project = None
        self.paths = []

    def report(self, phase='active'):
        try:
            with open(REPORT, 'w') as output:
                json.dump({'version': 1, 'phase': phase, 'repairs': self.total,
                    'save_notifications': self.save_notifications,
                    'editor_count': len(self.editors), 'parent_hooks': len(self.parents),
                    'project': self.project, 'project_file_count': len(self.paths),
                    'recent_events': self.events[-8:], 'errors': self.errors[-8:]},
                    output, indent=2, ensure_ascii=True)
        except Exception:
            pass
        self.last_report = time.time()

    def refresh_paths(self):
        settings = QtCore.QSettings('itasca', 'flac3d600')
        self.project = unicode(settings.value('Project/last project') or '')
        self.paths = project_files(self.project)

    def repair_editor(self, handle, trigger):
        if self.busy or not self.user.IsWindow(handle):
            return
        self.busy = True
        try:
            send = lambda msg, a=0, b=0: self.user.SendMessageW(handle, msg, a, b)
            if send(2137) != 65001 or send(2159):
                return
            length = send(2183)
            if length <= 0 or length > MAX_BYTES:
                return
            buffer = c.create_string_buffer(length + 1)
            send(2182, length + 1, c.addressof(buffer))
            raw = buffer.raw[:length]
            if not needs_gbk(raw):
                return
            self.refresh_paths()
            for path in self.paths:
                result = preserve_gbk(path, raw)
                if result['applied']:
                    result['trigger'] = trigger
                    self.events.append(result)
                    self.events = self.events[-8:]
                    self.total += 1
                    self.report()
        except Exception:
            self.errors.append(traceback.format_exc())
            self.report('recoverable_error')
        finally:
            self.busy = False

    def window_proc(self, hwnd, message, wparam, lparam, ident, refdata):
        # Forward every original message. Native save-point notification handling
        # remains intact; GBK save handling finishes before this notification returns.
        result = self.common.DefSubclassProc(hwnd, message, wparam, lparam)
        try:
            if message == 0x4e and lparam:  # WM_NOTIFY
                header = c.cast(lparam, c.POINTER(NMHDR)).contents
                if header.code == 2002 and header.hwndFrom in self.editors:
                    self.save_notifications += 1
                    self.repair_editor(header.hwndFrom, 'savepoint_notification')
            elif message == 0x82:  # WM_NCDESTROY
                self.common.RemoveWindowSubclass(hwnd, self.callback, self.SUBCLASS_ID)
                self.parents.discard(hwnd)
        except Exception:
            self.errors.append(traceback.format_exc())
        return result

    def attach_editor(self, handle):
        pid = wt.DWORD()
        thread = self.user.GetWindowThreadProcessId(handle, c.byref(pid))
        if pid.value != os.getpid() or thread != c.windll.kernel32.GetCurrentThreadId():
            return False
        parent = self.user.GetParent(handle)
        if not parent:
            return False
        if parent not in self.parents:
            if not self.common.SetWindowSubclass(parent, self.callback, self.SUBCLASS_ID, 0):
                raise RuntimeError('Save notification handler could not be installed')
            self.parents.add(parent)
        self.editors.add(handle)
        return True

    @QtCore.Slot()
    def start(self):
        self.timer.start()
        self.tick()

    @QtCore.Slot()
    def stop(self):
        self.timer.stop()
        for parent in list(self.parents):
            self.common.RemoveWindowSubclass(parent, self.callback, self.SUBCLASS_ID)
        self.parents.clear()
        self.editors.clear()
        self.report('stopped')

    @QtCore.Slot()
    def tick(self):
        try:
            windows = [w for w in QtGui.QApplication.allWidgets()
                       if w.inherits('QMainWindow') and w.isVisible()]
            if not windows:
                if time.time() - self.last_report > 10:
                    self.report('waiting_for_main_window')
                return
            main = max(windows, key=lambda w: w.width() * w.height())
            native = main.winId()
            try:
                hwnd = int(native)
            except TypeError:
                hwnd = self.convert(native)
            found = []
            def child(handle, unused):
                name = c.create_unicode_buffer(128)
                self.user.GetClassNameW(handle, name, 128)
                if name.value.lower().startswith('scintilla'):
                    found.append(handle)
                return True
            callback = self.enum_type(child)
            self.user.EnumChildWindows(hwnd, callback, 0)
            self.editors.intersection_update(found)
            for handle in found:
                if self.attach_editor(handle):
                    # Also covers a clean file loaded before the save handler.
                    self.repair_editor(handle, 'clean_document_check')
            if time.time() - self.last_report > 10:
                self.report()
        except Exception:
            self.errors.append(traceback.format_exc())
            self.report('recoverable_error')

_controller = None

def install():
    global _controller
    app = QtGui.QApplication.instance()
    if app is None:
        return False
    if _controller is None:
        _controller = GbkSaveController()
        _controller.moveToThread(app.thread())
        app.aboutToQuit.connect(_controller.stop)
        QtCore.QMetaObject.invokeMethod(_controller, 'start', QtCore.Qt.QueuedConnection)
    return True
