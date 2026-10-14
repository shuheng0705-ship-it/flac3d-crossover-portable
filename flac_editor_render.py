# FLAC3D plain-editor render compatibility; Python 2.7 / Qt 4.
# Uses the embedded Scintilla API. Never writes document text or source files.
import ctypes as c
import hashlib, json, os, re, time, traceback
from ctypes import wintypes as wt
from PySide import QtCore, QtGui

REPORT = 'C:/flac3d-launcher/editor-render-runtime.json'
MAX_DOCUMENT = 2 * 1024 * 1024
LITERAL_OR_COMMENT = re.compile(r"'(?:[^'\\\r\n]|\\[^\r\n])*'|\"(?:[^\"\\\r\n]|\\[^\r\n])*\"|;[^\r\n]*")

class CharacterRange(c.Structure):
    _fields_ = [('start', c.c_long), ('end', c.c_long)]

class TextRange(c.Structure):
    _fields_ = [('range', CharacterRange), ('text', c.c_void_p)]

def split_count(text, styles):
    offset = 0
    count = 0
    for char in text:
        size = len(char.encode('utf-8'))
        if size > 1 and len(set(styles[offset:offset + size])) > 1:
            count += 1
        offset += size
    return count

def normalize_plain_editor(get):
    result = {'applied': False}
    size = get(2183)  # GETTEXTLENGTH
    if size <= 0 or size > MAX_DOCUMENT or get(2137) != 65001:
        return result
    buffer = c.create_string_buffer(size * 2 + 2)
    arg = TextRange(CharacterRange(0, size), c.addressof(buffer))
    copied = get(2015, 0, c.addressof(arg))  # GETSTYLEDTEXT
    if copied != size * 2:
        result['skipped'] = 'Unexpected styled snapshot size'
        return result
    raw = buffer.raw[:size * 2:2]
    styles = bytearray(buffer.raw[1:size * 2:2])
    # A disabled FLAC editor uses plain style 18. Default style 0 can remain
    # on Chinese byte ranges after a native load/reformat operation.
    ids = set(styles)
    if ids != set((0, 18)) or all(ord(ch) < 128 for ch in raw):
        return result
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        result['skipped'] = 'Invalid UTF-8; no text conversion attempted'
        return result
    if bool(get(2483, 18)):
        result['skipped'] = 'Plain style is not regular weight'
        return result
    before_modified = bool(get(2159))
    before_caret = get(2008), get(2009)
    result['split_character_count'] = split_count(text, styles)
    get(2032, 0, 255)     # STARTSTYLING: position and count are bytes.
    get(2033, size, 18)   # SETSTYLING: only style bytes, never text.
    after = c.create_string_buffer(size + 1)
    get(2182, size + 1, c.addressof(after))
    result.update(applied=True, byte_length=size,
        text_unchanged=after.raw[:size] == raw,
        modified_flag_unchanged=bool(get(2159)) == before_modified,
        caret_unchanged=(get(2008), get(2009)) == before_caret,
        before_sha256=hashlib.sha256(raw).hexdigest(),
        after_sha256=hashlib.sha256(after.raw[:size]).hexdigest())
    return result

def normalize_coloured_editor(get, comment_style, string_style):
    """Keep native command/FISH colours; repair complete UTF-8 literal spans."""
    result = {'applied': False, 'mode': 'native_colours'}
    size = get(2183)
    if size <= 0 or size > MAX_DOCUMENT or get(2137) != 65001:
        return result
    buffer = c.create_string_buffer(size * 2 + 2)
    arg = TextRange(CharacterRange(0, size), c.addressof(buffer))
    if get(2015, 0, c.addressof(arg)) != size * 2:
        return result
    raw = buffer.raw[:size * 2:2]
    if all(ord(ch) < 128 for ch in raw):
        return result
    try:
        text = raw.decode('utf-8')
    except UnicodeError:
        result['skipped'] = 'Invalid UTF-8; text left unchanged'
        return result
    current = bytearray(buffer.raw[1:size * 2:2])
    desired = bytearray(current)
    offset = 0
    for char in text:
        width = len(char.encode('utf-8'))
        if width > 1:
            desired[offset:offset + width] = bytearray([current[offset]] * width)
        offset += width
    # Work in byte offsets; a semicolon inside a quoted string is not a comment.
    for match in LITERAL_OR_COMMENT.finditer(raw):
        style = comment_style if match.group(0).startswith(';') else string_style
        if style is not None:
            desired[match.start():match.end()] = bytearray([style] * (match.end() - match.start()))
    if desired == current:
        return result
    modified_before = bool(get(2159))
    caret_before = get(2008), get(2009)
    result['split_character_count'] = split_count(text, current)
    style_data = c.create_string_buffer(str(desired))
    get(2032, 0, 255)
    get(2073, size, c.addressof(style_data)) # SETSTYLINGEX: preserve native token styles.
    after = c.create_string_buffer(size + 1)
    get(2182, size + 1, c.addressof(after))
    result.update(applied=True, byte_length=size,
        text_unchanged=after.raw[:size] == raw,
        modified_flag_unchanged=bool(get(2159)) == modified_before,
        caret_unchanged=(get(2008), get(2009)) == caret_before,
        before_sha256=hashlib.sha256(raw).hexdigest(),
        after_sha256=hashlib.sha256(after.raw[:size]).hexdigest())
    return result

def native_style_for_colour(get, colour):
    if not isinstance(colour, QtGui.QColor):
        return None
    colourref = colour.red() | (colour.green() << 8) | (colour.blue() << 16)
    # 0..17 are FLAC's native syntax styles; 18 is the plain-text style.
    matches = [i for i in range(18) if get(2481, i) == colourref]
    return matches[0] if matches else None

class EditorRenderController(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.tick)
        self.history = []
        self.total_repairs = 0
        self.last_report = 0
        self.failed = False
        self.user = c.windll.user32
        self.user.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, c.c_int]
        self.user.GetWindowThreadProcessId.argtypes = [wt.HWND, c.POINTER(wt.DWORD)]
        self.user.SendMessageW.argtypes = [wt.HWND, wt.UINT, c.c_size_t, c.c_ssize_t]
        self.user.SendMessageW.restype = c.c_ssize_t
        self.callback_type = c.WINFUNCTYPE(wt.BOOL, wt.HWND, c.c_ssize_t)
        self.user.EnumChildWindows.argtypes = [wt.HWND, self.callback_type, c.c_ssize_t]
        self.direct_type = c.CFUNCTYPE(c.c_ssize_t, c.c_ssize_t, c.c_uint,
                                       c.c_size_t, c.c_ssize_t)
        self.convert = c.pythonapi.PyCObject_AsVoidPtr
        self.convert.argtypes = [c.py_object]
        self.convert.restype = c.c_void_p

    def report(self, state):
        state.update(controller_version=2, repair_count=self.total_repairs,
                     recent_repairs=self.history[-8:], failed=self.failed)
        try:
            with open(REPORT, 'w') as output:
                json.dump(state, output, ensure_ascii=True, indent=2)
        except Exception:
            pass
        self.last_report = time.time()

    @QtCore.Slot()
    def start(self):
        self.timer.start()
        self.tick()

    @QtCore.Slot()
    def stop(self):
        self.timer.stop()

    @QtCore.Slot()
    def tick(self):
        try:
            settings = QtCore.QSettings('itasca', 'flac3d600')
            disabled = unicode(settings.value('editor/syntax highlighting')).lower() == 'false'
            windows = [w for w in QtGui.QApplication.allWidgets()
                       if w.inherits('QMainWindow') and w.isVisible()]
            if not windows:
                if time.time() - self.last_report > 10:
                    self.report({'phase': 'waiting_for_main_window'})
                return
            window = max(windows, key=lambda w: w.width() * w.height())
            native = window.winId()
            try:
                hwnd = int(native)
            except TypeError:
                hwnd = self.convert(native)
            found = []
            def child(handle, unused):
                pid = wt.DWORD()
                self.user.GetWindowThreadProcessId(handle, c.byref(pid))
                if pid.value == os.getpid():
                    name = c.create_unicode_buffer(128)
                    self.user.GetClassNameW(handle, name, 128)
                    if name.value.lower().startswith('scintilla'):
                        found.append(handle)
                return True
            callback = self.callback_type(child)
            self.user.EnumChildWindows(hwnd, callback, 0)
            changed = False
            for handle in found:
                fn = self.user.SendMessageW(handle, 2184, 0, 0)
                ptr = self.user.SendMessageW(handle, 2185, 0, 0)
                if not fn or not ptr:
                    continue
                direct = self.direct_type(fn)
                get = lambda message, a=0, b=0: direct(ptr, message, a, b)
                if disabled:
                    result = normalize_plain_editor(get)
                else:
                    comment = native_style_for_colour(get, settings.value('editor/Comment/foreground'))
                    string = native_style_for_colour(get, settings.value('editor/String/foreground'))
                    if comment is None:
                        continue
                    result = normalize_coloured_editor(get, comment, string)
                if result['applied']:
                    self.history.append(result)
                    self.history = self.history[-8:]
                    self.total_repairs += 1
                    changed = True
                    if not all(result[k] for k in ('text_unchanged',
                            'modified_flag_unchanged', 'caret_unchanged')):
                        self.failed = True
                        self.timer.stop()
                        self.report({'phase': 'stopped_invariant_failure'})
                        return
            if changed or time.time() - self.last_report > 10:
                self.report({'phase': 'active', 'editor_count': len(found),
                    'colour_mode': 'plain' if disabled else 'native_highlighting',
                    'gui_thread': QtCore.QThread.currentThread() == QtGui.QApplication.instance().thread()})
        except Exception:
            self.failed = True
            self.timer.stop()
            self.report({'phase': 'stopped_error', 'error': traceback.format_exc()})

_controller = None

def install():
    global _controller
    app = QtGui.QApplication.instance()
    if app is None:
        return False
    if _controller is None:
        _controller = EditorRenderController()
        _controller.moveToThread(app.thread())
        QtCore.QMetaObject.invokeMethod(_controller, 'start', QtCore.Qt.QueuedConnection)
    return True
