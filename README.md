# FLAC3D CrossOver Portable

完整应用位于 Releases 的 `v1.0.0` 附件中。本仓库为私有备份，保存启动器源码、构建说明和验证记录。

这是供你在其他 Apple Silicon Mac 上使用的 FLAC3D 6.00.69 启动应用。运行时调用目标电脑安装的 CrossOver，保留当前已调好的容器配置。双击直接进入 FLAC3D 原版 GUI。

## 在另一台 Mac 上使用

1. 安装并激活 CrossOver。此包的参考版本为 26.3；使用相同版本最便于复现当前环境。Apple Silicon Mac 需要 Rosetta，按 CrossOver 的安装提示完成。
2. 解压迁移包，把 `FLAC3D CrossOver Portable.app` 放到“应用程序”文件夹。
3. 双击应用。首次启动会解压并导入容器，需要等待一段时间；之后直接启动 FLAC3D。无需安装 Python 或自行配置 Wine。
4. 按自己的 FLAC3D 授权进入程序；未配置许可证时可使用软件提供的演示模式。

应用会自动查找 `/Applications`、用户的 `Applications` 或 Spotlight 中的 CrossOver。每台目标 Mac 都需要安装并激活 CrossOver；包中不包含 CrossOver 程序或其激活信息。

## 容器和文件

容器名称：`FLAC3D-CrossOver-Portable`。

默认位置：`~/Library/Application Support/CrossOver/Bottles/FLAC3D-CrossOver-Portable`。

软件根目录：容器中的 `drive_c/FLAC3D600`。图形程序位于 `exe64/flac3d600_gui.exe`。

导入时会把 Documents、Downloads 等目录绑定到新电脑当前用户的目录。192 DPI、Retina 和字体配置随容器迁移。已有同名但未完成初始化的容器会保留并报错，不会被覆盖。

你的工程与模型没有包含在应用包内。迁移工程时请复制整个工程目录，保留工程、data、state 等文件夹的相对位置；仅复制 `.f3prj` 不足以带走关联数据和模型。中文 `.f3dat` 文件仍需使用已验证可读的 GBK 编码，字体配置不会自动修复文件本身的乱码。

此包用于本地运行，两个设备之间不会自动同步工程。可另外复制工程目录或使用你已有的文件同步方式。

## 验证范围

此包调用 CrossOver 本身的运行引擎，没有额外的图形转换层。相同 CrossOver 版本、硬件和设置下，启动入口不增加持续计算或渲染环节。

本机已完成首次自动导入、换目录恢复、原安装包核心 DLL 校验和 27 单元小模型求解；用户已确认 GUI 的布局、中文和操作正常。当前只在这台 Mac 上验证；另一台 Mac 的图形表现和许可证可用性需要在目标设备确认。新版本 CrossOver、不同 macOS 和不同显示器可能产生差异。

日志：`~/Library/Logs/FLAC3D-CrossOver-Portable/prepare.log` 和 `gui.log`。

## 依据

- [CodeWeavers：容器归档和恢复](https://support.codeweavers.com/2-common-actions/2-archiving-and-restoring-a-bottle)
- [CodeWeavers：CrossOver 使用指南与命令行启动](https://www.codeweavers.com/support/docs/crossover-mac/index)
- [CodeWeavers：PortJump 商业移植方案](https://www.codeweavers.com/portjump/)

如需把 CrossOver 运行环境一起嵌入并向其他用户分发，可评估 PortJump。继续开发开源独立引擎也是一条路线，但目前独立 Wine 与 CrossOver 的界面和兼容性仍存在差异。
