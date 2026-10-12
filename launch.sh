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
if [[ "${1:-}" == '--prepare-only' ]]; then
    print -r -- "$bottle"
    exit 0
fi
/usr/bin/nohup /usr/bin/env -i HOME="$HOME" USER="${USER:-$(id -un)}" \
    PATH=/usr/bin:/bin:/usr/sbin:/sbin TMPDIR="${TMPDIR:-/tmp}" \
    LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 WINEDEBUG=-all \
    "$cx/bin/wine" --bottle "$bottle" --workdir 'C:\FLAC3D600\exe64' \
    --cx-app 'C:\FLAC3D600\exe64\flac3d600_gui.exe' \
    > "$logdir/gui.log" 2>&1 < /dev/null &
