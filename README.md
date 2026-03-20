# ClawX Manager Suite

## 中文说明

ClawX Manager Suite 是一个基于稳定版 `ClawX_Provider_Manager_Portable` 重建的桌面管理工具，并集成了 ClawX Watchdog。

### 功能包含

- **供应商管理（Providers）**
  - 查看供应商 / 模型优先级
  - 检查健康状态和延迟
  - 启用 / 禁用供应商
  - 调整优先级顺序
  - 立即应用主用切换

- **日志（Logs）**
  - 在应用内查看运行日志

- **提醒（Reminder）**
  - 使用固定 `notify.wav` 播放提示音
  - 支持测试提示音
  - 当助手回复完成时自动提醒
  - 回复完成检测来自本地 OpenClaw 会话日志

- **看门狗（Watchdog）**
  - 作为左侧独立模块页集成
  - 显示运行状态
  - 显示脚本路径
  - 查看看门狗日志
  - 支持 Start / Stop / Refresh

### 运行方式

**方式一：**
直接双击：

- `start.bat`

**方式二：**
手动运行：

```bash
py -3 provider_manager.py
```

### 说明

- 这是当前可运行的集成版仓库。
- 该版本是在稳定 portable 基底上重新集成 Watchdog 得到的。
- 提醒逻辑使用项目内固定的 `notify.wav` 文件。

---

## English

ClawX Manager Suite is a rebuilt desktop management tool based on the stable `ClawX_Provider_Manager_Portable` version, with ClawX Watchdog integrated into it.

### Included features

- **Providers**
  - View provider / model priority
  - Check health and latency
  - Enable / disable providers
  - Reorder priority
  - Apply primary switch immediately

- **Logs**
  - View runtime logs inside the app

- **Reminder**
  - Fixed `notify.wav` playback
  - Test reminder sound
  - Auto reminder when an assistant reply is completed
  - Reply completion is detected from local OpenClaw session logs

- **Watchdog**
  - Integrated as a dedicated left-side module page
  - View status
  - View script path
  - View watchdog logs
  - Start / Stop / Refresh

### Run

**Option 1:**
Double-click:

- `start.bat`

**Option 2:**
Run manually:

```bash
py -3 provider_manager.py
```

### Notes

- This repository is the current working integrated suite version.
- The suite was rebuilt from the stable portable provider-manager base and then re-integrated with Watchdog.
- Reminder sound logic uses the local fixed `notify.wav` file bundled in the project.
