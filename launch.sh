#!/bin/zsh
set -euo pipefail
resources="${0:A:h}"
app=''
for candidate in /Applications/CrossOver.app "$HOME/Applications/CrossOver.app"; do
    if [[ -x "$candidate/Contents/SharedSupport/CrossOver/bin/wine" ]]; then
        app="$candidate"
        break
    fi
done
if [[ -z "$app" ]]; then
    while IFS= read -r candidate; do
        if [[ -x "$candidate/Contents/SharedSupport/CrossOver/bin/wine" ]]; then
            app="$candidate"
            break
        fi
    done < <(/usr/bin/mdfind 'kMDItemCFBundleIdentifier == "com.codeweavers.CrossOver"' 2>/dev/null)
fi
if [[ -z "$app" ]]; then
    print -u2 '请先安装并激活 CrossOver，再打开 FLAC3D。下载：https://www.codeweavers.com/crossover'
    exit 1
fi
cx="$app/Contents/SharedSupport/CrossOver"
bottle_root="${FLAC3D_CX_BOTTLE_ROOT:-$HOME/Library/Application Support/CrossOver/Bottles}"
bottle="$bottle_root/FLAC3D-CrossOver-Portable"
logdir="$HOME/Library/Logs/FLAC3D-CrossOver-Portable"
mkdir -p "$bottle_root" "$logdir"

cxrun() {
    /usr/bin/env -i HOME="$HOME" USER="${USER:-$(id -un)}" \
        PATH=/usr/bin:/bin:/usr/sbin:/sbin TMPDIR="${TMPDIR:-/tmp}" \
        LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 WINEDEBUG=-all \
        "$@"
}

if [[ ! -f "$bottle/.flac3d-portable-ready" ]]; then
    if [[ -e "$bottle" ]]; then
        print -u2 "容器初始化未完成或名称已被占用：$bottle。原有内容已保留，请查看 $logdir/prepare.log。"
        exit 1
    fi
    lock="$bottle_root/.flac3d-portable-initializing"
    if ! mkdir "$lock" 2>/dev/null; then
        print -u2 'FLAC3D 的首次初始化正在进行，请稍后再打开。'
        exit 1
    fi
    trap 'rmdir "$lock" 2>/dev/null || true' EXIT
    [[ -f "$resources/FLAC3D.cxarchive" ]]
    if ! cxrun "$cx/bin/cxbottle" --bottle "$bottle" --scope private \
        --restore "$resources/FLAC3D.cxarchive" > "$logdir/prepare.log" 2>&1; then
        print -u2 "容器导入失败，详细记录：$logdir/prepare.log。"
        exit 1
    fi
    [[ -f "$bottle/drive_c/FLAC3D600/exe64/flac3d600_gui.exe" ]]
    # Rebind only migration placeholders; never replace a user's real directory.
    for profile in "$bottle/drive_c/users/"*(N/); do
        for folder in Desktop Documents Downloads Music Pictures; do
            if [[ -L "$profile/$folder" || ! -e "$profile/$folder" ]]; then
                ln -sfn "$HOME/$folder" "$profile/$folder"
            fi
        done
        if [[ -L "$profile/Videos" || ! -e "$profile/Videos" ]]; then
            ln -sfn "$HOME/Movies" "$profile/Videos"
        fi
    done
    ln -sfn "$HOME" "$bottle/dosdevices/y:"
    ln -sfn / "$bottle/dosdevices/z:"
    if ! cxrun "$cx/bin/cxbottle" --bottle "$bottle" --install >> "$logdir/prepare.log" 2>&1; then
        print -u2 "容器注册失败，详细记录：$logdir/prepare.log。"
        exit 1
    fi
    touch "$bottle/.flac3d-portable-ready"
    rmdir "$lock"
    trap - EXIT
fi

[[ -f "$bottle/drive_c/FLAC3D600/exe64/flac3d600_gui.exe" ]]
mkdir -p "$bottle/drive_c/flac3d-launcher"
cp "$resources/exporthi.f3dat" "$bottle/drive_c/flac3d-launcher/exporthi.f3dat"
# Install both CJK font weights before Wine/Qt initializes GUI font caches.
mkdir -p "$bottle/drive_c/windows/Fonts"
for font_file in "$resources/fonts/"*.otf(N); do
    cp "$font_file" "$bottle/drive_c/windows/Fonts/${font_file:t}"
done
# Install the opt-in Python compatibility hook before the embedded interpreter starts.
compat_target="$bottle/drive_c/FLAC3D600/exe64/python27/Lib/site-packages/sitecustomize.py"
if [[ -f "$compat_target" ]] && ! /usr/bin/grep -q 'FLAC3D Mac compatibility bootstrap' "$compat_target"; then
    print -u2 '已有自定义 Python 启动配置，请保留它并手动合并兼容设置。'
    exit 1
fi
cp "$resources/sitecustomize.py" "$compat_target"
cp "$resources/flac_mac_layout.py" "${compat_target:h}/flac_mac_layout.py"
cp "$resources/flac_editor_render.py" "${compat_target:h}/flac_editor_render.py"
cp "$resources/flac_gbk_save.py" "${compat_target:h}/flac_gbk_save.py"
# Handle invalid cp0 directly in the legacy input parser, including separate Python shells.
cp "$resources/ipython-compat/inputsplitter.py" "${compat_target:h}/IPython/core/inputsplitter.py"
cp "$resources/ipython-compat/encoding.py" "${compat_target:h}/IPython/utils/encoding.py"
# Migrate the stale application layout once; later user layout changes are preserved.
if [[ ! -f "$bottle/.flac3d-retina-layout-v1" ]]; then
    layout_reg="Z:${resources//\//\\}\\startup-layout.reg"
    cxrun "$cx/bin/wine" --bottle "$bottle" --no-gui \
        --cx-app 'C:\windows\system32\reg.exe' import "$layout_reg" \
        > "$logdir/layout.log" 2>&1
    touch "$bottle/.flac3d-retina-layout-v1"
fi

# Keep Retina and DPI explicit on every target Mac; no program-specific DPI override.
regfile="Z:${resources//\//\\}\\display.reg"
if ! cxrun "$cx/bin/wine" --bottle "$bottle" --no-gui \
    --cx-app 'C:\windows\system32\reg.exe' import "$regfile" \
    > "$logdir/display.log" 2>&1; then
    print -u2 "高分辨率配置未完成，详细记录：$logdir/display.log。"
    exit 1
fi

font_reg="Z:${resources//\//\\}\\fontfix.reg"
cxrun "$cx/bin/wine" --bottle "$bottle" --no-gui \
    --cx-app 'C:\windows\system32\reg.exe' import "$font_reg" \
    > "$logdir/font.log" 2>&1

if [[ "${1:-}" == '--prepare-only' ]]; then
    print -r -- "$bottle"
    exit 0
fi
/usr/bin/nohup /usr/bin/env -i HOME="$HOME" USER="${USER:-$(id -un)}" \
    PATH=/usr/bin:/bin:/usr/sbin:/sbin TMPDIR="${TMPDIR:-/tmp}" \
    LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 WINEDEBUG=-all \
    QT_USE_NATIVE_WINDOWS=1 FLAC3D_MAC_COMPAT=1 \
    "$cx/bin/wine" --bottle "$bottle" --workdir 'C:\FLAC3D600\exe64' \
    --cx-app 'C:\FLAC3D600\exe64\flac3d600_gui.exe' \
    > "$logdir/gui.log" 2>&1 < /dev/null &
