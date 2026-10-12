use scripting additions
on run
    set bundlePath to POSIX path of (path to me)
    set launchPath to bundlePath & "Contents/Resources/launch.sh"
    try
        do shell script "/bin/zsh " & quoted form of launchPath
    on error errorMessage
        display alert "FLAC3D 启动失败" message errorMessage as critical
    end try
end run
