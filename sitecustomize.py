# FLAC3D Mac compatibility bootstrap v1; Python 2.7 compatible.
# Enabled only by this app's launcher. No model or license changes.
def _flac_mac_bootstrap():
    import os
    if os.environ.get('FLAC3D_MAC_COMPAT') != '1':
        return
    import codecs, json, ctypes, traceback
    status = {'bootstrap_version': 1}
    try:
        def cp0_fallback(name):
            if name.replace('-', '').replace('_', '').lower() == 'cp0':
                return codecs.lookup('utf-8')
        codecs.register(cp0_fallback)
        status['cp0_input_codec'] = codecs.lookup('cp0').name
        kernel = ctypes.windll.kernel32
        kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
        kernel.GetModuleHandleW.restype = ctypes.c_void_p
        kernel.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        kernel.GetProcAddress.restype = ctypes.c_void_p
        handle = kernel.GetModuleHandleW(u'QtCore4.dll')
        status['qt_loaded'] = bool(handle)
        status['system_code_page'] = kernel.GetACP()
        if handle and status['system_code_page'] == 936:
            def qtfn(name, result, args):
                address = kernel.GetProcAddress(handle, name)
                if not address:
                    raise RuntimeError('Qt text codec API unavailable')
                return ctypes.CFUNCTYPE(result, *args)(address)
            locale = qtfn(b'?codecForLocale@QTextCodec@@SAPEAV1@XZ', ctypes.c_void_p, [])
            current = qtfn(b'?codecForCStrings@QTextCodec@@SAPEAV1@XZ', ctypes.c_void_p, [])
            set_codec = qtfn(b'?setCodecForCStrings@QTextCodec@@SAXPEAV1@@Z', None, [ctypes.c_void_p])
            original_locale = locale()
            lookup = qtfn(b'?codecForName@QTextCodec@@SAPEAV1@PEBD@Z', ctypes.c_void_p, [ctypes.c_char_p])
            codec = lookup(b'UTF-8')
            if not codec:
                raise RuntimeError('UTF-8 text codec unavailable')
            set_codec(codec)
            status['qt_cstrings_use_utf8'] = current() == codec
            status['locale_codec_unchanged'] = locale() == original_locale
            try:
                import flac_mac_layout
                status['layout_controller_installed'] = flac_mac_layout.install()
            except Exception:
                status['layout_controller_error'] = traceback.format_exc()
    except Exception:
        status['error'] = traceback.format_exc()
    try:
        with open('C:/flac3d-launcher/compat-startup.json', 'w') as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass
_flac_mac_bootstrap()
