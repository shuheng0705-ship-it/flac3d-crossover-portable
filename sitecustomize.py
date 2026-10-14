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
        try:
            awareness = ctypes.c_int(-1)
            dpi_query = ctypes.windll.shcore.GetProcessDpiAwareness
            dpi_query.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
            dpi_query.restype = ctypes.c_long
            status['own_process_dpi_query_result'] = dpi_query(None, ctypes.byref(awareness))
            status['own_process_dpi_awareness'] = awareness.value
        except Exception:
            status['own_process_dpi_query_error'] = traceback.format_exc()
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
            codec = original_locale
            if not codec:
                raise RuntimeError('System text codec unavailable')
            set_codec(codec)
            status['qt_cstrings_use_system_codec'] = current() == codec
            status['locale_codec_unchanged'] = locale() == original_locale
        try:
            import flac_editor_render
            status['editor_render_controller_installed'] = flac_editor_render.install()
        except Exception:
            status['editor_render_controller_error'] = traceback.format_exc()
        status['utf8_save_controller_installed'] = False
        try:
            import flac_gbk_save
            status['gbk_save_controller_installed'] = flac_gbk_save.install()
        except Exception:
            status['gbk_save_controller_error'] = traceback.format_exc()
    except Exception:
        status['error'] = traceback.format_exc()
    try:
        with open('C:/flac3d-launcher/compat-startup.json', 'w') as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass
_flac_mac_bootstrap()
