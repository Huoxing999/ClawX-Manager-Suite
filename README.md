# ClawX Manager Suite

## 中文说明

ClawX Manager Suite 是一个基于稳定版 `ClawX_Provider_Manager_Portable` 重建的桌面管理工具，并集成了 ClawX Watchdog。它的目标不是重新发明一套复杂架构，而是在**已经可用的 portable 基底上，继续增强桌面管理能力**，把“供应商管理、提醒、日志、看门狗”统一到一个界面里。

---

## 一、项目目标

这个项目主要解决几个实际问题：

1. **模型供应商太多，不方便统一查看**
   - 需要一个桌面界面统一查看供应商优先级、启用状态、延迟和在线情况。

2. **主用供应商失效时，希望手动或自动切换**
   - 提供优先级管理、检测、自动切换和立即应用能力。

3. **助手回复完成后，希望有明确提示音**
   - 不想盯着聊天窗口，回复完成时响一声就够了。

4. **ClawX / OpenClaw 偶发连接异常时，希望自动兜底**
   - 用 Watchdog 定期检查连接状态，必要时自动恢复。

因此，这个 suite 不是单一工具，而是把多个“已经有价值但分散”的功能整合到一个桌面入口里。

---

## 二、主要功能

### 1. 供应商管理（Providers）

供应商页面负责处理模型供应商相关的可视化管理。

#### 支持内容
- 查看供应商 / 模型列表
- 查看优先级
- 查看在线 / 离线 / 当前主用状态
- 查看延迟
- 启用 / 禁用供应商
- 上移 / 下移优先级
- 手动设为主用
- 保存优先级到配置
- 立即应用主用切换
- 检测当前供应商
- 一键检测全部供应商

#### 实现思路
- 从 OpenClaw 配置文件中读取 provider 和 model 信息
- 从本地状态文件中读取启用状态、失败次数、最近检测结果
- 通过 HTTP 请求探测 provider 的可达性和延迟
- 把当前主用和 fallback 顺序回写到配置里
- 需要时重启 gateway 使切换生效

#### 自动切换逻辑
当启用自动切换时：
- 当前主用连续失败达到阈值
- 且存在下一个在线且已启用的供应商
- 就会自动把它切成新的主用候选

这部分是为了应对主用 provider 不稳定、临时不可达、或接口异常的情况。

---

### 2. 日志页面（Logs）

日志页面是一个应用内日志查看窗口，用来快速确认当前动作有没有执行成功。

#### 支持内容
- 查看运行日志
- 查看配置重载、检测、切换等动作输出
- 清空界面内日志窗口（不会清空所有历史文件，只是清理当前显示）

#### 实现思路
- 应用运行过程中，把关键动作追加写入本地日志文件
- 同时同步显示在 UI 文本框中
- 尽量让用户不需要每次都去命令行看输出

---

### 3. 提醒模块（Reminder）

提醒模块解决的是“助手回复完成后，给我一个可靠提示”的问题。

#### 支持内容
- 启用 / 关闭消息完成提示音
- 测试提示音
- 调整提示音时长
- 调整提示音音量
- 使用固定 `notify.wav` 文件播放提示音

#### 实现思路
这个模块没有继续走系统提示音或临时动态音频那种不稳定路线，而是采用了更稳的设计：

- 项目目录内放一个固定 `notify.wav`
- 点击测试时直接播放这个文件
- 自动提醒时也优先播放这个文件

这样做的好处是：
- 声音表现稳定
- 不依赖系统别名
- 不容易因为环境不同而失效

#### 助手回复完成检测方式
提醒并不是“随便响”，而是监听本地 OpenClaw 会话日志，在检测到最新 assistant 消息完成写入后再触发提示音。

这意味着：
- 响铃更贴近真实“回复完成”事件
- 不依赖旧的 delivery-queue 逻辑
- 更适合当前本地运行模式

---

### 4. 看门狗（Watchdog）

Watchdog 是这次 suite 集成里最重要的新增模块之一。它不再只是一个独立脚本，而是被接成了左侧独立页面。

#### 支持内容
- 左侧导航独立入口
- 查看当前运行状态
- 查看 watchdog 脚本路径
- 查看 watchdog 日志输出
- Start / Stop / Refresh

#### Watchdog 的职责
Watchdog 本身负责：
- 自动检测 ClawX / OpenClaw 是否运行正常
- 检查连接是否可达
- 检测 gateway / 本地端口可用性
- 在必要时尝试恢复

#### 集成方式
这次不是简单把脚本丢进目录，而是：
- 在 UI 左侧加入独立模块页
- 提供状态展示
- 提供日志窗口
- 提供按钮操作
- 用 pid 文件和进程检测来管理 watchdog 生命周期

这样用户就不需要手动开脚本窗口，也不用单独维护另一个工具入口。

---

## 三、项目结构

当前仓库的核心文件大致如下：

- `provider_manager.py`
  - 主桌面程序
  - 包含 Providers / Logs / Reminder / Watchdog / Settings 的 UI 和逻辑

- `clawx_watchdog.py`
  - Watchdog 脚本本体
  - 负责连接检测和恢复策略

- `notify.wav`
  - 固定提示音文件

- `clawx_notify_test.wav`
  - 辅助测试音频文件

- `start.bat`
  - Windows 下快速启动入口

- `.gitignore`
  - 忽略本地缓存、日志、运行时文件

---

## 四、工作原理概览

### Provider Manager 如何工作
1. 读取 OpenClaw 配置
2. 解析 provider / model 信息
3. 结合本地状态文件构建 UI 列表
4. 通过请求探测 provider 健康状态
5. 用户可手动调整优先级和主用
6. 写回配置并可重启 gateway 生效

### Reminder 如何工作
1. 读取本地会话日志最新 `.jsonl`
2. 找到最新 assistant 消息
3. 如果是新的完成事件，就触发播放 `notify.wav`

### Watchdog 如何工作
1. 独立脚本周期性检查连接
2. 检测 ClawX / OpenClaw / gateway 状态
3. 必要时按策略恢复
4. UI 侧负责启动、停止、显示状态和日志

---

## 五、运行方式

### 方式一：直接启动
双击：

- `start.bat`

### 方式二：命令行启动

```bash
py -3 provider_manager.py
```

---

## 六、适用场景

这个项目适合：

- 本地长期运行 ClawX / OpenClaw 的用户
- 有多个 provider，需要做优先级和切换管理的人
- 想要稳定“回复完成提醒”的人
- 希望连接异常时有自动恢复兜底的人

---

## 七、设计原则

这个项目在实现上有几个明确原则：

1. **先保证可用，再做整合**
   - 以可运行的 portable 基底为基础，而不是在损坏版本上硬修。

2. **提醒逻辑以稳定优先**
   - 固定 `notify.wav`，不依赖花哨但不稳定的方案。

3. **Watchdog 必须是 UI 里的独立模块**
   - 不是简单复制脚本，而是作为 suite 的正式一部分存在。

4. **以桌面实际使用体验为中心**
   - 操作路径短
   - 状态清晰
   - 不要求用户频繁切命令行

---

## 八、当前状态

当前仓库保存的是**已经能够运行的集成版**，重点包括：

- Provider 管理可用
- Reminder 可用
- Watchdog 已集成进独立页面
- 项目已清理不必要的运行产物和本地状态文件

---

## English

ClawX Manager Suite is a rebuilt desktop management tool based on the stable `ClawX_Provider_Manager_Portable` version, with ClawX Watchdog integrated into the same UI. The goal is not to redesign everything from scratch, but to take an already working portable base and turn it into a more complete desktop control panel.

---

## 1. Project goals

This project mainly solves a few practical problems:

1. **Too many model providers, no convenient unified view**
   - A desktop UI is needed to inspect provider priority, status, latency, and current primary provider.

2. **Need manual and automatic provider switching**
   - Priority management, checks, failover, and immediate apply are all built into the UI.

3. **Need a reliable notification when the assistant finishes replying**
   - Instead of staring at the chat window, a short sound is enough.

4. **Need automatic recovery when ClawX / OpenClaw becomes unstable**
   - Watchdog continuously checks the connection and attempts recovery when needed.

So this suite is not just a single tool. It combines several already-useful capabilities into one desktop entry point.

---

## 2. Main features

### Providers

The Providers page handles model provider management.

#### Included capabilities
- View provider / model list
- View priority order
- View online / offline / current-primary state
- View latency
- Enable / disable providers
- Move providers up / down
- Mark one as primary
- Save priority back to config
- Apply the current primary immediately
- Check the selected provider
- Test all providers

#### Implementation idea
- Read provider and model data from the OpenClaw config
- Read local state data for enable flags, failures, and recent checks
- Probe provider reachability and latency through HTTP requests
- Write primary and fallback order back into config
- Restart gateway when an immediate switch needs to take effect

#### Auto-switch logic
When auto-switch is enabled:
- if the current primary fails repeatedly up to the threshold,
- and another enabled provider is online,
- the suite promotes the next available provider as the new primary candidate.

This is meant to make local usage more resilient when a provider becomes unstable or temporarily unavailable.

---

### Logs

The Logs page is an in-app runtime viewer.

#### Included capabilities
- View runtime logs
- Inspect reload, check, switch, and operational events
- Clear the visible log window inside the app

#### Implementation idea
- Important actions are appended into a local log file
- The same lines are also shown in the UI text view
- This reduces the need to rely on terminal output for normal desktop usage

---

### Reminder

The Reminder module solves the “tell me when the assistant is done” problem.

#### Included capabilities
- Enable / disable completion reminder
- Test reminder sound
- Adjust sound duration
- Adjust sound volume
- Play a fixed `notify.wav` from the project directory

#### Implementation idea
Instead of relying on system beeps or generating a temporary sound each time, this project uses a more stable design:

- keep a fixed `notify.wav` inside the project folder,
- play that file for both test playback and automatic completion reminders.

Benefits:
- more consistent sound behavior,
- fewer environment-dependent failures,
- easier to keep stable across machines.

#### Assistant completion detection
The reminder is not random. It monitors local OpenClaw session logs and plays the sound when a new assistant message completion is detected.

This makes the alert closer to a real “reply completed” event and better aligned with local usage.

---

### Watchdog

Watchdog is one of the most important integrations in this suite. It is not only a standalone script copied into the folder — it is connected into the UI as a dedicated module page.

#### Included capabilities
- Dedicated left-side navigation entry
- Current runtime status
- Watchdog script path
- Watchdog log viewer
- Start / Stop / Refresh controls

#### What Watchdog does
Watchdog itself is responsible for:
- checking whether ClawX / OpenClaw is healthy,
- checking local connectivity,
- verifying gateway / port availability,
- attempting recovery when needed.

#### Integration approach
The suite integration provides:
- a UI page,
- status display,
- log output,
- lifecycle controls,
- basic process tracking via pid file and process checks.

This makes Watchdog part of the suite instead of a separate window or disconnected helper script.

---

## 3. Project structure

Main files in the repository:

- `provider_manager.py`
  - main desktop application
  - contains Providers / Logs / Reminder / Watchdog / Settings UI and logic

- `clawx_watchdog.py`
  - watchdog script itself
  - handles connection checks and recovery strategy

- `notify.wav`
  - fixed reminder sound file

- `clawx_notify_test.wav`
  - helper sound used for testing

- `start.bat`
  - quick Windows launcher

- `.gitignore`
  - excludes local runtime artifacts, logs, and cache files

---

## 4. High-level workflow

### Provider Manager workflow
1. Read OpenClaw config
2. Parse provider / model information
3. Merge config data with local runtime state
4. Probe provider health via HTTP
5. Let the user reorder / switch providers in UI
6. Save back to config and optionally restart gateway

### Reminder workflow
1. Read the newest local session `.jsonl`
2. Find the newest assistant message
3. If it is a newly completed assistant event, play `notify.wav`

### Watchdog workflow
1. Run a separate watchdog script loop
2. Periodically check ClawX / OpenClaw / gateway status
3. Recover when necessary according to its strategy
4. Let the suite UI manage start/stop and log visibility

---

## 5. Running

### Option 1
Double-click:

- `start.bat`

### Option 2
Run manually:

```bash
py -3 provider_manager.py
```

---

## 6. Suitable usage scenarios

This project is useful for people who:

- run ClawX / OpenClaw locally for long periods,
- use multiple providers and want visual priority management,
- want a stable completion reminder,
- want a recovery safety net when connectivity becomes unstable.

---

## 7. Design principles

A few key principles drive this project:

1. **Start from what already works**
   - The suite is built from a working portable base, instead of continuing to patch damaged rebuilds.

2. **Stability first for reminder logic**
   - A fixed `notify.wav` is more reliable than fancy but fragile approaches.

3. **Watchdog must be a first-class UI module**
   - Not just a copied script, but part of the suite itself.

4. **Desktop usability matters**
   - Short action paths
   - Clear status visibility
   - Less dependence on terminal usage

---

## 8. Current status

This repository currently stores the **working integrated version**, including:

- usable provider management,
- usable reminder logic,
- Watchdog integrated into a dedicated page,
- cleaned repository state without local runtime artifacts and personal state files.
