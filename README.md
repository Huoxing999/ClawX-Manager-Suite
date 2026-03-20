# ClawX Provider Manager Portable

一个可直接分发给其他人使用的便携版 Provider Manager。

## 特点

- 纯 Python 标准库实现，无需额外 pip 安装
- 默认自动读取当前 Windows 用户目录下的 OpenClaw 配置：
  - `%USERPROFILE%\.openclaw\openclaw.json`
- 状态文件和日志保存在项目目录内：
  - `providers_state.json`
  - `provider_manager.log`
- 双击 `start.bat` 即可启动

## 运行要求

- Windows
- 已安装 Python 3（确保 `py` 命令可用）
- 本机已安装并配置 OpenClaw / ClawX，并且存在：
  - `%USERPROFILE%\.openclaw\openclaw.json`

## 启动方式

### 方式 1：双击启动

直接双击：

- `start.bat`

### 方式 2：命令行启动

```bat
py -3 provider_manager.py
```

## 文件说明

- `provider_manager.py`：主程序
- `start.bat`：启动脚本
- `providers_state.json`：运行状态（首次启动后自动生成）
- `provider_manager.log`：运行日志（首次启动后自动生成）

## 适配说明

当前版本会自动使用当前登录用户的 `%USERPROFILE%`，因此复制到其他 Windows 电脑后，只要对方：

1. 安装了 Python 3
2. 已安装并配置 OpenClaw / ClawX
3. 配置文件位于 `%USERPROFILE%\.openclaw\openclaw.json`

即可直接运行。

## 如果无法启动

请检查：

1. 是否安装 Python 3
   - 在命令行运行：`py -3 --version`
2. 是否存在 OpenClaw 配置文件
   - `%USERPROFILE%\.openclaw\openclaw.json`
3. 是否被安全软件拦截
4. 是否是精简系统导致系统提示音能力异常

## 后续可扩展

如果要进一步做成真正的公开分发版本，建议下一步补充：

- 首次运行向导
- 配置文件路径手动选择
- 打包为 exe
- 多语言 README
- 发布版目录结构（release / docs / screenshots）
