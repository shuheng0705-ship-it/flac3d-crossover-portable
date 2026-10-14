# FLAC3D CrossOver 迁移版 v1.0.4

在安装并激活 CrossOver 的 Apple Silicon Mac 上运行 FLAC3D 6.00.69。双击应用直接进入原版 GUI。每台目标电脑需要自己的 CrossOver 和 FLAC3D 授权；未配置 FLAC3D 许可证时，可进入软件提供的演示模式。

## 在另一台 Mac 上使用

1. 安装并激活 CrossOver；本机验证使用 26.3。按 CrossOver 的提示安装 Rosetta。
2. 解压迁移包，把 `FLAC3D CrossOver Portable.app` 放入“应用程序”。
3. 双击应用。首次启动自动恢复并注册独立容器，以后直接打开 FLAC3D。
4. 工程另行复制整个目录，保留工程、data、state 的相对位置。本包没有包含用户的工程和模型，也不会自动同步文件。

应用会从系统“应用程序”、用户“应用程序”及 Spotlight 中查找 CrossOver。包中包含 FLAC3D 安装文件、中文字体和兼容设置，未包含 CrossOver 引擎或激活信息。

应用采用本地签名，未经过 Apple 公证。若目标 Mac 首次打开时提示无法验证开发者，在确认来自这个私有仓库并校验下载文件后，可按 [Apple 的打开流程](https://support.apple.com/zh-cn/102445)，到“系统设置 → 隐私与安全性”选择“仍要打开”。

## 显示与中文

保留 Retina、192 DPI 和 Qt 原生子窗口。FLAC3D 使用系统 DPI 感知，避免拖大或最大化时出现内容截断和大片留白。编辑器、控制台使用 Noto Sans CJK SC；字体及 SIL OFL 许可证随包提供。

数字蓝色、字符串绿色、注释灰色等原生语法颜色保留。兼容模块修正旧编辑器在一个 UTF-8 中文字符内部切换样式的问题；不改编辑器文字、光标或未保存状态。

旧版 GUI 的文件读取与保存编码路径不一致：UTF-8 中文可能在保存或重新加载后按中文系统编码解释。应用改用 GBK 保存兼容处理，使文件、旧 GUI 和引擎使用一致的 Windows 中文编码。

处理范围为当前已保存工程列出的 `.f3dat`、`.dat`、`.f3edat`，单文件不超过 2 MiB。只有磁盘正文与已保存的 UTF-8 编辑器正文一致、且能无损表示为 GBK 时，才先备份原字节，再转成 GBK。文字、建模命令及数值保持不变。GBK、ASCII、二进制模型、不支持的 Unicode 字符和与编辑器正文不一致的文件不自动转换。

保存通知触发即时检查；定时检查覆盖已打开的已保存文件。原字节备份保存在容器 `drive_c/flac3d-launcher/gbk-save-backups`，文件名为原字节的 SHA-256。新文件需要加入并保存工程，才能进入此处理范围。

已有乱码记录不会追溯重写，应查看修正后重新运行产生的新回显。已经损坏的文字需从原文或备份恢复。请勿再执行旧的 UTF-8 BOM 补标记脚本。

## 容器和软件位置

容器名：`FLAC3D-CrossOver-Portable`。

默认位置：`~/Library/Application Support/CrossOver/Bottles/FLAC3D-CrossOver-Portable`。

软件根目录是容器的 `drive_c/FLAC3D600`，图形程序在 `exe64/flac3d600_gui.exe`。首次恢复会把 Documents 等目录绑定到目标 Mac 当前用户。已有同名但未完成初始化的容器会保留并报错，不会覆盖用户目录。

F2 可隐藏右侧控制面板，释放中间区域。没有启用自动面板限宽，不固定主窗口尺寸。

## 高清图片导出

在图形版选中需要导出的 Plot，然后执行：

```text
program call 'C:/flac3d-launcher/exporthi.f3dat'
```

4800×3200 的 PNG 保存在容器的 `drive_c/flac3d-launcher/plot-4800.png`，再次执行会更新该图片。密集网格在特定缩放比例下仍可能产生摩尔纹；扩大画布、放大局部或提高导出像素有助于减少纹路。

## 验证范围和诊断

本机已验证首次容器恢复、换目录恢复、原安装包核心 DLL 校验和 27 单元小模型求解。用户确认应用重开后中文编辑器、语法颜色、窗口拖大与最大化正常。独立 Qt4/原生 Scintilla 测试验证了中文样式修复、连续保存后 GBK 与 System 解码器的文字一致性，以及 FLAC3D 引擎的中文回显。用户进一步确认：修改 size、保存、运行、关闭并重新打开编辑页后，原有中文注释与新回显均正常。实际 GUI 已记录四次保存兼容处理，文字和 ASCII 命令逐字节校验通过。

其他 Apple Silicon Mac 尚未实机验证，目标电脑的显示效果和许可证需在那里检查。本应用仍调用 CrossOver 的运行引擎，兼容脚本不替代求解器和图形驱动。不会自动上传或更新 GitHub。

启动日志在 `~/Library/Logs/FLAC3D-CrossOver-Portable`。容器的 `drive_c/flac3d-launcher` 还有 `compat-startup.json`、`editor-render-runtime.json` 和 `gbk-save-runtime.json`。

## 参考

- [CodeWeavers：容器归档和恢复](https://support.codeweavers.com/2-common-actions/2-archiving-and-restoring-a-bottle)
- [Noto CJK 字体](https://github.com/notofonts/noto-cjk/tree/Sans2.004)
- [Scintilla：保存状态通知与样式接口](https://www.scintilla.org/ScintillaDoc.html)
- [Microsoft：窗口消息处理](https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-setwindowsubclass)
