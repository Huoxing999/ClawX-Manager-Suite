import json
import math
import os
import struct
import threading
import time
import urllib.request
import urllib.error
import subprocess
import sys
import winsound
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

APP_NAME = "ClawX Provider Manager"
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.expandvars(r"%USERPROFILE%\.openclaw\openclaw.json")
STATE_PATH = os.path.join(WORK_DIR, "providers_state.json")
LOG_PATH = os.path.join(WORK_DIR, "provider_manager.log")
WATCHDOG_LOG_PATH = os.path.join(WORK_DIR, "clawx_watchdog.log")
WATCHDOG_SCRIPT_PATH = os.path.join(WORK_DIR, "clawx_watchdog.py")
WATCHDOG_PID_PATH = os.path.join(WORK_DIR, "watchdog.pid")
CHECK_INTERVAL_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = 8
FAIL_THRESHOLD = 3
MODEL_DISPLAY_MAX = 28
MODEL_COLUMN_MIN = 180
MODEL_COLUMN_MAX = 320


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message):
    line = f"[{now_str()}] {message}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    return line


def read_text_tail(path, max_bytes=4096):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_tone_wav(file_path, frequency=880, duration_ms=180, volume=70, sample_rate=22050):
    duration_s = max(duration_ms, 1) / 1000.0
    total_samples = max(1, int(sample_rate * duration_s))
    amplitude = int(32767 * max(0, min(100, volume)) / 100.0)
    frames = bytearray()
    for i in range(total_samples):
        sample = int(amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
        frames.extend(struct.pack('<h', sample))
    data_size = len(frames)
    byte_rate = sample_rate * 2
    block_align = 2
    with open(file_path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, block_align, 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(frames)


def deep_get(d, *keys, default=None):
    cur = d
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def probe_url(url, timeout=REQUEST_TIMEOUT_SECONDS):
    req = urllib.request.Request(url, headers={"User-Agent": "ClawX-Provider-Manager/1.0"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency_ms = int((time.time() - start) * 1000)
            return {"reachable": True, "status_code": resp.status, "latency_ms": latency_ms, "error": ""}
    except urllib.error.HTTPError as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"reachable": True, "status_code": e.code, "latency_ms": latency_ms, "error": f"HTTP {e.code}"}
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        return {"reachable": False, "status_code": None, "latency_ms": latency_ms if latency_ms > 0 else "-", "error": str(e)}

LANG = {
    "zh": {
        "window_title": "ClawX 供应商管理器",
        "app_name": "Provider Manager",
        "app_subtitle": "ClawX / OpenClaw",
        "subtitle": "左侧导航切换功能页面，右侧显示对应内容",
        "nav_dashboard": "概览",
        "nav_providers": "供应商",
        "nav_logs": "日志",
        "nav_notify": "提醒",
        "nav_watchdog": "看门狗",
        "nav_settings": "设置",
        "dashboard_title": "概览",
        "dashboard_subtitle": "查看当前主用模型、健康状态和快速操作",
        "providers_title": "供应商列表",
        "providers_tip": "双击某个模型打开详细设置",
        "logs_title": "运行日志",
        "settings_title": "设置",
        "settings_subtitle": "这里放不需要常驻主界面的内容",
        "current_primary": "当前主用：{value}",
        "summary_total": "总数：{value}",
        "summary_online": "在线：{value}",
        "summary_offline": "离线：{value}",
        "summary_current": "主用：{value}",
        "summary_last_switch": "最近切换：{value}",
        "summary_none": "暂无",
        "btn_reload": "⟳ 读取配置",
        "btn_check": "🩺 检测当前",
        "btn_check_all": "🚀 测全部",
        "btn_move_up": "↑ 上移",
        "btn_move_down": "↓ 下移",
        "btn_set_primary": "★ 设主用",
        "btn_enable": "✅ 启用",
        "btn_disable": "⛔ 禁用",
        "btn_save_priority": "💾 存优先级",
        "btn_apply": "⚡ 立即应用",
        "btn_open": "📂 打开目录",
        "btn_new": "＋ 新增",
        "btn_clear_log": "🧹 清空日志窗口",
        "notify_title": "提醒模块",
        "notify_subtitle": "当助手完成一条消息输出时，响一声提醒你",
        "notify_enable": "完成提醒",
        "notify_enable_hint": "启用消息完成提示音",
        "notify_sound_ms": "提示音时长(ms)",
        "notify_sound_volume": "提示音音量(0-100)",
        "notify_test": "🔔 测试提示音",
        "watchdog_title": "看门狗",
        "watchdog_status": "运行状态：{value}",
        "watchdog_script": "脚本路径：{value}",
        "watchdog_running": "运行中",
        "watchdog_stopped": "未运行",
        "watchdog_start": "启动",
        "watchdog_stop": "停止",
        "watchdog_refresh": "刷新",
        "auto_switch_group": "自动切换",
        "auto_switch_group_hint": "把故障自动切换放到供应商模块管理",
        "auto_switch_enable": "启用自动切换",
        "status_auto_switch": "自动切换",
        "status_auto_switch_hint": "当前主用连续失败后，自动切换到下一个在线供应商",
        "status_config_path": "配置文件路径",
        "status_language": "界面语言",
        "status_interval": "检测间隔（秒）",
        "status_timeout": "请求超时（秒）",
        "status_fail_threshold": "切换阈值（连续失败次数）",
        "columns": {
            "priority": "优先级",
            "model": "模型",
            "status_dot": "●",
            "status": "状态",
            "latency": "延迟(ms)",
        },
        "status": {
            "unknown": "未知",
            "online": "在线",
            "offline": "离线",
            "current": "当前使用中",
            "disabled": "已禁用",
            "reachable": "可达",
        },
        "current_tag": "主用",
        "detail_popup_title": "供应商详细设置",
        "detail_section_basic": "基础信息",
        "detail_section_runtime": "运行状态",
        "field_provider_id": "供应商 ID",
        "field_model_name": "模型名称",
        "field_model_id": "模型 ID",
        "field_base_url": "Base URL",
        "field_api": "API 类型",
        "field_enabled": "启用",
        "field_is_primary": "设为当前主用",
        "field_status": "当前状态",
        "field_latency": "延迟",
        "field_failures": "失败次数",
        "field_last_check": "最后检测",
        "field_last_error": "最近错误",
        "enabled_yes": "是",
        "enabled_no": "否",
        "close": "关闭",
        "save": "保存",
        "delete": "删除",
        "reset": "重置",
        "ui_started": "界面已启动",
        "config_reloaded": "配置已重新读取",
        "reload_failed": "读取配置失败：\n{error}",
        "select_provider_first": "请先选择一个供应商。",
        "priority_saved": "已保存优先级到配置",
        "save_success": "优先级已保存到配置。",
        "save_failed": "保存失败：\n{error}",
        "apply_success": "切换已应用。",
        "apply_failed": "应用切换失败：\n{error}",
        "selected_primary": "已将 {provider} 标记为主用候选",
        "provider_enabled": "已启用供应商：{provider}",
        "provider_disabled": "已禁用供应商：{provider}",
        "config_updated": "配置已更新：primary={primary}, fallbacks={fallbacks}",
        "gateway_restarted": "Gateway 已重启",
        "manual_switch_applied": "已手动应用切换",
        "check_ok": "检测完成",
        "check_all_started": "开始测试全部供应商",
        "auto_switch_skipped": "自动切换已跳过：没有可用的备用供应商",
        "auto_switched": "已自动从 {src} 切换到 {dst}",
        "auto_switch_failed": "自动切换失败：{error}",
        "background_loop_error": "后台检测异常：{error}",
        "missing_base_url": "缺少 baseUrl",
        "no_enabled_providers": "没有可用的已启用供应商。",
        "openclaw_not_found": "未找到 openclaw.cmd",
        "detail_saved": "供应商配置已保存：{provider}",
        "detail_deleted": "供应商已删除：{provider}",
        "detail_delete_confirm": "确定删除供应商 {provider} 吗？",
        "detail_new_created": "已创建新供应商",
        "field_required": "以下字段不能为空：供应商 ID、模型名称、模型 ID、Base URL、API 类型",
        "provider_exists": "供应商 ID 已存在：{provider}",
        "delete_primary_blocked": "当前主用供应商已删除，将自动把第一条可用供应商设为主用。",
        "logs_empty": "这里会显示检测、切换和配置操作日志。",
        "settings_saved": "设置已应用到当前界面（本次运行）。",
        "lang_zh": "中文",
        "lang_en": "English",
    },
    "en": {
        "window_title": "ClawX Provider Manager",
        "app_name": "Provider Manager",
        "app_subtitle": "ClawX / OpenClaw",
        "subtitle": "Use the left navigation to switch pages and manage providers",
        "nav_dashboard": "Dashboard",
        "nav_providers": "Providers",
        "nav_logs": "Logs",
        "nav_notify": "Reminder",
        "nav_watchdog": "Watchdog",
        "nav_settings": "Settings",
        "dashboard_title": "Dashboard",
        "dashboard_subtitle": "View current primary model, health status, and quick actions",
        "providers_title": "Providers",
        "providers_tip": "Double-click a model to open detailed settings",
        "logs_title": "Runtime Logs",
        "settings_title": "Settings",
        "settings_subtitle": "Things that do not need to stay on the main screen",
        "current_primary": "Current primary: {value}",
        "summary_total": "Total: {value}",
        "summary_online": "Online: {value}",
        "summary_offline": "Offline: {value}",
        "summary_current": "Primary: {value}",
        "summary_last_switch": "Last switch: {value}",
        "summary_none": "None",
        "btn_reload": "⟳ Reload",
        "btn_check": "🩺 Check Current",
        "btn_check_all": "🚀 Test All",
        "btn_move_up": "↑ Up",
        "btn_move_down": "↓ Down",
        "btn_set_primary": "★ Set Primary",
        "btn_enable": "✅ Enable",
        "btn_disable": "⛔ Disable",
        "btn_save_priority": "💾 Save Priority",
        "btn_apply": "⚡ Apply Now",
        "btn_open": "📂 Open Folder",
        "btn_new": "＋ New",
        "btn_clear_log": "🧹 Clear Log View",
        "notify_title": "Reminder",
        "notify_subtitle": "Play a short sound when the assistant finishes outputting a message",
        "notify_enable": "Completion reminder",
        "notify_enable_hint": "Enable message completion sound",
        "notify_sound_ms": "Sound duration (ms)",
        "notify_sound_volume": "Sound volume (0-100)",
        "notify_test": "🔔 Test Sound",
        "watchdog_title": "Watchdog",
        "watchdog_status": "Status: {value}",
        "watchdog_script": "Script: {value}",
        "watchdog_running": "Running",
        "watchdog_stopped": "Stopped",
        "watchdog_start": "Start",
        "watchdog_stop": "Stop",
        "watchdog_refresh": "Refresh",
        "auto_switch_group": "Auto Switch",
        "auto_switch_group_hint": "Manage failover behavior inside the Providers page",
        "auto_switch_enable": "Enable auto switch",
        "status_auto_switch": "Auto Switch",
        "status_auto_switch_hint": "Automatically switch to the next online provider after repeated failures",
        "status_config_path": "Config Path",
        "status_language": "UI Language",
        "status_interval": "Check interval (seconds)",
        "status_timeout": "Request timeout (seconds)",
        "status_fail_threshold": "Failover threshold (consecutive failures)",
        "columns": {
            "priority": "Priority",
            "model": "Model",
            "status_dot": "●",
            "status": "Status",
            "latency": "Latency(ms)",
        },
        "status": {
            "unknown": "Unknown",
            "online": "Online",
            "offline": "Offline",
            "current": "Current",
            "disabled": "Disabled",
            "reachable": "Reachable",
        },
        "current_tag": "Primary",
        "detail_popup_title": "Provider Details",
        "detail_section_basic": "Basic Info",
        "detail_section_runtime": "Runtime Status",
        "field_provider_id": "Provider ID",
        "field_model_name": "Model Name",
        "field_model_id": "Model ID",
        "field_base_url": "Base URL",
        "field_api": "API Type",
        "field_enabled": "Enabled",
        "field_is_primary": "Set as current primary",
        "field_status": "Current Status",
        "field_latency": "Latency",
        "field_failures": "Failures",
        "field_last_check": "Last Check",
        "field_last_error": "Last Error",
        "enabled_yes": "Yes",
        "enabled_no": "No",
        "close": "Close",
        "save": "Save",
        "delete": "Delete",
        "reset": "Reset",
        "ui_started": "UI started",
        "config_reloaded": "Config reloaded",
        "reload_failed": "Reload failed:\n{error}",
        "select_provider_first": "Please select a provider first.",
        "priority_saved": "Priority saved to config",
        "save_success": "Priority saved to config.",
        "save_failed": "Save failed:\n{error}",
        "apply_success": "Switch applied.",
        "apply_failed": "Apply switch failed:\n{error}",
        "selected_primary": "Selected {provider} as primary candidate",
        "provider_enabled": "Enabled provider: {provider}",
        "provider_disabled": "Disabled provider: {provider}",
        "config_updated": "Config updated: primary={primary}, fallbacks={fallbacks}",
        "gateway_restarted": "Gateway restarted",
        "manual_switch_applied": "Manual switch applied",
        "check_ok": "Health check finished",
        "check_all_started": "Testing all providers",
        "auto_switch_skipped": "Auto switch skipped: no online fallback provider available",
        "auto_switched": "Auto switched from {src} to {dst}",
        "auto_switch_failed": "Auto switch failed: {error}",
        "background_loop_error": "Background loop error: {error}",
        "missing_base_url": "Missing baseUrl",
        "no_enabled_providers": "No enabled providers available.",
        "openclaw_not_found": "openclaw.cmd not found",
        "detail_saved": "Provider config saved: {provider}",
        "detail_deleted": "Provider deleted: {provider}",
        "detail_delete_confirm": "Delete provider {provider}?",
        "detail_new_created": "New provider created",
        "field_required": "These fields are required: Provider ID, Model Name, Model ID, Base URL, API Type",
        "provider_exists": "Provider ID already exists: {provider}",
        "delete_primary_blocked": "Deleted provider was current primary. The first available provider will become primary automatically.",
        "logs_empty": "Health checks, failover events, and config actions appear here.",
        "settings_saved": "Settings applied to the current runtime UI.",
        "lang_zh": "中文",
        "lang_en": "English",
    },
}


class ProviderManagerApp:
    def __init__(self, root):
        self.root = root
        self.lang = "zh"
        self.check_interval_seconds = CHECK_INTERVAL_SECONDS
        self.request_timeout_seconds = REQUEST_TIMEOUT_SECONDS
        self.fail_threshold = FAIL_THRESHOLD
        self.root.geometry("1120x800")
        self.root.minsize(920, 660)

        self.providers = []
        self.state = self.load_state()
        self.config_cache = None
        self.config_mtime = 0
        self.last_seen_gateway_message = ""
        self.auto_switch_var = tk.BooleanVar(value=bool(self.state.get("auto_switch_enabled", False)))
        self.notify_on_reply_var = tk.BooleanVar(value=bool(self.state.get("notify_on_reply", True)))
        self.running = True
        self.selected_provider_id = None
        self.testing_all = False
        self.current_page = "settings"

        self.current_model_var = tk.StringVar(value="")
        self.subtitle_var = tk.StringVar(value="")
        self.summary_total_var = tk.StringVar(value="")
        self.summary_online_var = tk.StringVar(value="")
        self.summary_offline_var = tk.StringVar(value="")
        self.summary_current_var = tk.StringVar(value="")
        self.summary_last_switch_var = tk.StringVar(value="")

        self.settings_interval_var = tk.StringVar(value=str(self.check_interval_seconds))
        self.settings_timeout_var = tk.StringVar(value=str(self.request_timeout_seconds))
        self.settings_threshold_var = tk.StringVar(value=str(self.fail_threshold))
        self.settings_lang_var = tk.StringVar(value=self.lang)
        self.settings_notify_duration_var = tk.StringVar(value=str(self.state.get("notify_sound_ms", 180)))
        self.settings_notify_volume_var = tk.StringVar(value=str(self.state.get("notify_sound_volume", 70)))

        self.setup_style()
        self.build_ui()
        self.load_config()
        self.refresh_all_views()
        self.apply_language()
        self.append_log(log(self.t("ui_started")))

        self.worker = threading.Thread(target=self.background_loop, daemon=True)
        self.worker.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def t(self, key, **kwargs):
        text = LANG[self.lang][key]
        return text.format(**kwargs) if kwargs else text

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass
        style.configure("Root.TFrame", background="#eef2f7")
        style.configure("Sidebar.TFrame", background="#111827")
        style.configure("SidebarTitle.TLabel", background="#111827", foreground="#f9fafb", font=("Segoe UI", 13, "bold"))
        style.configure("SidebarSub.TLabel", background="#111827", foreground="#9ca3af", font=("Segoe UI", 8))
        style.configure("Nav.TButton", padding=(12, 8), font=("Segoe UI", 9))
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 13, "bold"))
        style.configure("Sub.TLabel", background="#ffffff", foreground="#6b7280", font=("Segoe UI", 9))
        style.configure("StatValue.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 11, "bold"))
        style.configure("Action.TButton", padding=(7, 6), font=("Segoe UI", 8))
        style.configure("Accent.TButton", padding=(9, 7), font=("Segoe UI", 8, "bold"))
        style.configure("Treeview", rowheight=30, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 8, "bold"))

    def build_ui(self):
        self.root.configure(bg="#eef2f7")
        shell = ttk.Frame(self.root, style="Root.TFrame")
        shell.pack(fill="both", expand=True)

        sidebar = ttk.Frame(shell, style="Sidebar.TFrame", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        content = ttk.Frame(shell, style="Root.TFrame", padding=14)
        content.pack(side="left", fill="both", expand=True)

        ttk.Label(sidebar, text="ClawX", style="SidebarTitle.TLabel").pack(anchor="w", padx=18, pady=(18, 2))
        self.sidebar_subtitle = ttk.Label(sidebar, style="SidebarSub.TLabel")
        self.sidebar_subtitle.pack(anchor="w", padx=18, pady=(0, 18))

        self.nav_buttons = {}
        self.nav_buttons["providers"] = ttk.Button(sidebar, style="Nav.TButton", command=lambda: self.show_page("providers"))
        self.nav_buttons["logs"] = ttk.Button(sidebar, style="Nav.TButton", command=lambda: self.show_page("logs"))
        self.nav_buttons["notify"] = ttk.Button(sidebar, style="Nav.TButton", command=lambda: self.show_page("notify"))
        self.nav_buttons["watchdog"] = ttk.Button(sidebar, style="Nav.TButton", command=lambda: self.show_page("watchdog"))
        self.nav_buttons["settings"] = ttk.Button(sidebar, style="Nav.TButton", command=lambda: self.show_page("settings"))
        for btn in self.nav_buttons.values():
            btn.pack(fill="x", padx=12, pady=4)

        self.nav_spacer = ttk.Frame(sidebar, style="Sidebar.TFrame")
        self.nav_spacer.pack(fill="both", expand=True)
        self.nav_buttons["settings"].pack_forget()
        self.nav_buttons["settings"].pack(side="bottom", fill="x", padx=12, pady=12)

        header = ttk.Frame(content, style="Card.TFrame", padding=16)
        header.pack(fill="x", pady=(0, 10))
        self.page_host = ttk.Frame(content, style="Root.TFrame")
        self.page_host.pack(fill="both", expand=True)

        self.pages = {}
        self.build_dashboard_page()
        self.build_providers_page()
        self.build_logs_page()
        self.build_notify_page()
        self.build_watchdog_page()
        self.build_settings_page()
        self.show_page("settings")

    def build_dashboard_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["dashboard"] = page

        stats = ttk.Frame(page, style="Root.TFrame")
        stats.pack(fill="x", pady=(0, 10))
        self.dashboard_cards = []
        for var in [self.summary_total_var, self.summary_online_var, self.summary_offline_var, self.summary_current_var]:
            card = ttk.Frame(stats, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ttk.Label(card, textvariable=var, style="StatValue.TLabel").pack(anchor="w")
            self.dashboard_cards.append(card)
        self.dashboard_cards[-1].pack_configure(padx=(0, 0))

        last_switch_card = ttk.Frame(page, style="Card.TFrame", padding=14)
        last_switch_card.pack(fill="x", pady=(0, 10))
        ttk.Label(last_switch_card, textvariable=self.summary_last_switch_var, style="StatValue.TLabel").pack(anchor="w")

        quick = ttk.Frame(page, style="Card.TFrame", padding=14)
        quick.pack(fill="x")
        self.dashboard_reload = ttk.Button(quick, style="Action.TButton", command=self.manual_reload)
        self.dashboard_reload.pack(side="left", padx=(0, 6))
        self.dashboard_check_all = ttk.Button(quick, style="Accent.TButton", command=self.check_all)
        self.dashboard_check_all.pack(side="left", padx=(0, 6))
        self.dashboard_apply = ttk.Button(quick, style="Action.TButton", command=self.apply_switch_now)
        self.dashboard_apply.pack(side="left", padx=(0, 6))
        self.dashboard_open = ttk.Button(quick, style="Action.TButton", command=self.open_folder)
        self.dashboard_open.pack(side="left", padx=(0, 6))

    def build_providers_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["providers"] = page

        controls = ttk.Frame(page, style="Card.TFrame", padding=12)
        controls.pack(fill="x", pady=(0, 10))
        provider_stats_card = ttk.Frame(page, style="Card.TFrame", padding=14)
        provider_stats_card.pack(fill="x", pady=(0, 10))
        stats = ttk.Frame(provider_stats_card, style="Card.TFrame")
        stats.pack(fill="x")
        self.provider_cards = []
        for var in [self.summary_total_var, self.summary_online_var, self.summary_offline_var]:
            card = ttk.Frame(stats, style="Card.TFrame", padding=14)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ttk.Label(card, textvariable=var, style="StatValue.TLabel").pack(anchor="w")
            self.provider_cards.append(card)
        self.provider_cards[-1].pack_configure(padx=(0, 0))
        row1 = ttk.Frame(controls, style="Card.TFrame")
        row1.pack(fill="x")
        row2 = ttk.Frame(controls, style="Card.TFrame")
        row2.pack(fill="x", pady=(8, 0))

        auto_switch_card = ttk.Frame(page, style="Card.TFrame", padding=12)
        auto_switch_card.pack(fill="x", pady=(0, 10))
        auto_switch_header = ttk.Frame(auto_switch_card, style="Card.TFrame")
        auto_switch_header.pack(fill="x")
        self.auto_switch_title = ttk.Label(auto_switch_header, style="Header.TLabel", font=("Segoe UI", 11, "bold"))
        self.auto_switch_title.pack(side="left", anchor="w")
        self.auto_switch_check = ttk.Checkbutton(auto_switch_header, variable=self.auto_switch_var)
        self.auto_switch_check.pack(side="right", anchor="e")
        self.auto_switch_hint = ttk.Label(auto_switch_card, style="Sub.TLabel", wraplength=760, justify="left")
        self.auto_switch_hint.pack(anchor="w", pady=(6, 0))

        self.reload_button = ttk.Button(row1, style="Action.TButton", command=self.manual_reload)
        self.reload_button.pack(side="left", padx=(0, 6))
        self.check_button = ttk.Button(row1, style="Action.TButton", command=self.check_now)
        self.check_button.pack(side="left", padx=(0, 6))
        self.check_all_button = ttk.Button(row1, style="Accent.TButton", command=self.check_all)
        self.check_all_button.pack(side="left", padx=(0, 6))
        self.move_up_button = ttk.Button(row1, style="Action.TButton", command=self.move_up)
        self.move_up_button.pack(side="left", padx=(10, 6))
        self.move_down_button = ttk.Button(row1, style="Action.TButton", command=self.move_down)
        self.move_down_button.pack(side="left", padx=(0, 6))
        self.set_primary_button = ttk.Button(row1, style="Action.TButton", command=self.set_selected_primary)
        self.set_primary_button.pack(side="left", padx=(0, 6))

        self.enable_button = ttk.Button(row2, style="Action.TButton", command=self.enable_selected)
        self.enable_button.pack(side="left", padx=(0, 6))
        self.disable_button = ttk.Button(row2, style="Action.TButton", command=self.disable_selected)
        self.disable_button.pack(side="left", padx=(0, 6))
        self.save_button = ttk.Button(row2, style="Action.TButton", command=self.save_priority)
        self.save_button.pack(side="left", padx=(10, 6))
        self.apply_button = ttk.Button(row2, style="Accent.TButton", command=self.apply_switch_now)
        self.apply_button.pack(side="left", padx=(0, 6))
        self.open_folder_button = ttk.Button(row2, style="Action.TButton", command=self.open_folder)
        self.open_folder_button.pack(side="left", padx=(10, 6))
        self.new_button = ttk.Button(row2, style="Action.TButton", command=self.new_provider)
        self.new_button.pack(side="left", padx=(10, 6))

        table_card = ttk.Frame(page, style="Card.TFrame", padding=12)
        table_card.pack(fill="both", expand=True)
        top_header = ttk.Frame(table_card, style="Card.TFrame")
        top_header.pack(fill="x", pady=(0, 8))
        left_header = ttk.Frame(top_header, style="Card.TFrame")
        left_header.pack(side="left", fill="x", expand=True)
        self.providers_title = ttk.Label(left_header, style="Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.providers_title.pack(anchor="w")
        self.provider_summary_current = ttk.Label(left_header, style="Sub.TLabel")
        self.provider_summary_current.pack(anchor="w", pady=(4, 0))
        self.provider_summary_last_switch = ttk.Label(left_header, style="Sub.TLabel")
        self.provider_summary_last_switch.pack(anchor="w", pady=(4, 0))
        self.details_tip_label = ttk.Label(top_header, style="Sub.TLabel")
        self.details_tip_label.pack(anchor="e", side="right")

        columns = ("priority", "model", "status", "latency")
        self.columns = columns
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", height=18)
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        widths = {"priority": 80, "model": MODEL_COLUMN_MIN, "status": 220, "latency": 120}
        for col in columns:
            self.tree.column(col, width=widths[col], anchor="center")
        self.tree.column("model", anchor="w")
        self.tree.tag_configure("online", foreground="#15803d")
        self.tree.tag_configure("offline", foreground="#b91c1c")
        self.tree.tag_configure("current", foreground="#1d4ed8")
        self.tree.tag_configure("disabled", foreground="#6b7280")
        self.tree.tag_configure("unknown", foreground="#6b7280")
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def build_logs_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["logs"] = page

        card = ttk.Frame(page, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True)
        self.logs_title = ttk.Label(card, style="Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.logs_title.pack(anchor="w", pady=(0, 6))
        self.logs_hint = ttk.Label(card, style="Sub.TLabel")
        self.logs_hint.pack(anchor="w", pady=(0, 8))
        self.logs_clear_button = ttk.Button(card, style="Action.TButton", command=self.clear_log_view)
        self.logs_clear_button.pack(anchor="w", pady=(0, 8))
        self.log_text = tk.Text(card, wrap="word", bg="#0f172a", fg="#e5e7eb", insertbackground="#e5e7eb", relief="flat", font=("Consolas", 10), padx=10, pady=10)
        self.log_text.pack(fill="both", expand=True)

    def build_notify_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["notify"] = page

        notify_card = ttk.Frame(page, style="Card.TFrame", padding=14)
        notify_card.pack(fill="x")
        self.notify_title = ttk.Label(notify_card, style="Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.notify_title.pack(anchor="w")
        self.notify_subtitle = ttk.Label(notify_card, style="Sub.TLabel")
        self.notify_subtitle.pack(anchor="w", pady=(4, 12))

        notify_grid = ttk.Frame(notify_card, style="Card.TFrame")
        notify_grid.pack(fill="x")
        self.notify_labels = {}

        def add_notify_row(row, key, widget):
            label = ttk.Label(notify_grid, style="Sub.TLabel")
            label.grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            widget.grid(row=row, column=1, sticky="w", pady=6)
            self.notify_labels[key] = label

        self.notify_enable_check = ttk.Checkbutton(notify_grid, variable=self.notify_on_reply_var)
        add_notify_row(0, "notify_enable", self.notify_enable_check)

        self.notify_duration_entry = ttk.Entry(notify_grid, textvariable=self.settings_notify_duration_var, width=12)
        add_notify_row(1, "notify_sound_ms", self.notify_duration_entry)

        self.notify_volume_entry = ttk.Entry(notify_grid, textvariable=self.settings_notify_volume_var, width=12)
        add_notify_row(2, "notify_sound_volume", self.notify_volume_entry)

        buttons = ttk.Frame(notify_card, style="Card.TFrame")
        buttons.pack(fill="x", pady=(12, 0))
        self.notify_test_button = ttk.Button(buttons, style="Action.TButton", command=self.play_notify_sound)
        self.notify_test_button.pack(side="left")
        self.notify_save_button = ttk.Button(buttons, style="Accent.TButton", command=self.apply_runtime_settings)
        self.notify_save_button.pack(side="right")

    def build_watchdog_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["watchdog"] = page

        status_card = ttk.Frame(page, style="Card.TFrame", padding=14)
        status_card.pack(fill="x", pady=(0, 10))
        self.watchdog_title = ttk.Label(status_card, style="Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.watchdog_title.pack(anchor="w")
        self.watchdog_status_label = ttk.Label(status_card, style="Sub.TLabel")
        self.watchdog_status_label.pack(anchor="w", pady=(6, 0))
        self.watchdog_path_label = ttk.Label(status_card, style="Sub.TLabel")
        self.watchdog_path_label.pack(anchor="w", pady=(6, 0))
        btns = ttk.Frame(status_card, style="Card.TFrame")
        btns.pack(fill="x", pady=(12, 0))
        self.watchdog_start_button = ttk.Button(btns, style="Accent.TButton", command=self.start_watchdog)
        self.watchdog_start_button.pack(side="left", padx=(0, 6))
        self.watchdog_stop_button = ttk.Button(btns, style="Action.TButton", command=self.stop_watchdog)
        self.watchdog_stop_button.pack(side="left", padx=(0, 6))
        self.watchdog_refresh_button = ttk.Button(btns, style="Action.TButton", command=self.refresh_watchdog_panel)
        self.watchdog_refresh_button.pack(side="left", padx=(0, 6))

        log_card = ttk.Frame(page, style="Card.TFrame", padding=12)
        log_card.pack(fill="both", expand=True)
        self.watchdog_log_text = tk.Text(log_card, wrap="word", bg="#0f172a", fg="#e5e7eb", insertbackground="#e5e7eb", relief="flat", font=("Consolas", 10), padx=10, pady=10)
        self.watchdog_log_text.pack(fill="both", expand=True)

    def build_settings_page(self):
        page = ttk.Frame(self.page_host, style="Root.TFrame")
        self.pages["settings"] = page

        card = ttk.Frame(page, style="Card.TFrame", padding=14)
        card.pack(fill="x")
        self.settings_title = ttk.Label(card, style="Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.settings_title.pack(anchor="w")
        self.settings_subtitle = ttk.Label(card, style="Sub.TLabel")
        self.settings_subtitle.pack(anchor="w", pady=(4, 12))

        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")
        ttk.Label(grid, style="Sub.TLabel", text="").grid(row=0, column=0)
        self.settings_labels = {}

        def add_setting_row(row, key, widget):
            label = ttk.Label(grid, style="Sub.TLabel")
            label.grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            widget.grid(row=row, column=1, sticky="w", pady=6)
            self.settings_labels[key] = label

        self.settings_lang_combo = ttk.Combobox(grid, textvariable=self.settings_lang_var, values=["zh", "en"], state="readonly", width=12)
        add_setting_row(1, "status_language", self.settings_lang_combo)

        self.settings_interval_entry = ttk.Entry(grid, textvariable=self.settings_interval_var, width=12)
        add_setting_row(2, "status_interval", self.settings_interval_entry)

        self.settings_timeout_entry = ttk.Entry(grid, textvariable=self.settings_timeout_var, width=12)
        add_setting_row(3, "status_timeout", self.settings_timeout_entry)

        self.settings_threshold_entry = ttk.Entry(grid, textvariable=self.settings_threshold_var, width=12)
        add_setting_row(4, "status_fail_threshold", self.settings_threshold_entry)

        self.settings_path_box = tk.Text(grid, height=3, width=44, wrap="word", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        self.settings_path_box.insert("1.0", CONFIG_PATH)
        self.settings_path_box.configure(state="disabled")
        add_setting_row(5, "status_config_path", self.settings_path_box)

        self.settings_apply_button = ttk.Button(card, style="Accent.TButton", command=self.apply_runtime_settings)
        self.settings_apply_button.pack(anchor="e", pady=(12, 0))

    def show_page(self, page_name):
        self.current_page = page_name
        for name, page in self.pages.items():
            if name == page_name:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        self.refresh_nav_styles()
        if page_name == "watchdog":
            self.refresh_watchdog_panel()

    def refresh_nav_styles(self):
        labels = {
            "providers": f"🧩 {self.t('nav_providers')}",
            "logs": f"📜 {self.t('nav_logs')}",
            "notify": f"🔔 {self.t('nav_notify')}",
            "watchdog": f"🛡 {self.t('nav_watchdog')}",
            "settings": f"⚙ {self.t('nav_settings')}",
        }
        for name, btn in self.nav_buttons.items():
            prefix = "▶ " if name == self.current_page else "   "
            btn.configure(text=prefix + labels[name])

    def apply_language(self):
        self.root.title(self.t("window_title"))
        self.sidebar_subtitle.configure(text=self.t("app_subtitle"))

        self.providers_title.configure(text=self.t("providers_title"))
        self.details_tip_label.configure(text=self.t("providers_tip"))
        self.provider_summary_current.configure(text=self.t("current_primary", value=deep_get(self.config_cache or {}, "agents", "defaults", "model", default={}).get("primary", "-") or "-"))
        self.provider_summary_last_switch.configure(text=self.summary_last_switch_var.get())
        self.logs_title.configure(text=self.t("logs_title"))
        self.logs_hint.configure(text=self.t("logs_empty"))
        self.logs_clear_button.configure(text=self.t("btn_clear_log"))
        self.notify_title.configure(text=self.t("notify_title"))
        self.notify_subtitle.configure(text=self.t("notify_subtitle"))
        self.notify_enable_check.configure(text=self.t("notify_enable_hint"))
        self.notify_test_button.configure(text=self.t("notify_test"))
        self.notify_save_button.configure(text=self.t("save"))
        self.watchdog_title.configure(text=self.t("watchdog_title"))
        self.watchdog_start_button.configure(text=self.t("watchdog_start"))
        self.watchdog_stop_button.configure(text=self.t("watchdog_stop"))
        self.watchdog_refresh_button.configure(text=self.t("watchdog_refresh"))
        self.settings_title.configure(text=self.t("settings_title"))
        self.settings_subtitle.configure(text=self.t("settings_subtitle"))
        self.settings_apply_button.configure(text=self.t("save"))

        self.auto_switch_title.configure(text=self.t("auto_switch_group"))
        self.auto_switch_check.configure(text=self.t("auto_switch_enable"))
        self.auto_switch_hint.configure(text=self.t("status_auto_switch_hint"))

        self.reload_button.configure(text=self.t("btn_reload"))
        self.check_button.configure(text=self.t("btn_check"))
        self.check_all_button.configure(text=self.t("btn_check_all"))
        self.move_up_button.configure(text=self.t("btn_move_up"))
        self.move_down_button.configure(text=self.t("btn_move_down"))
        self.set_primary_button.configure(text=self.t("btn_set_primary"))
        self.enable_button.configure(text=self.t("btn_enable"))
        self.disable_button.configure(text=self.t("btn_disable"))
        self.save_button.configure(text=self.t("btn_save_priority"))
        self.apply_button.configure(text=self.t("btn_apply"))
        self.open_folder_button.configure(text=self.t("btn_open"))
        self.new_button.configure(text=self.t("btn_new"))
        self.dashboard_reload.configure(text=self.t("btn_reload"))
        self.dashboard_check_all.configure(text=self.t("btn_check_all"))
        self.dashboard_apply.configure(text=self.t("btn_apply"))
        self.dashboard_open.configure(text=self.t("btn_open"))

        for key, label in self.settings_labels.items():
            label.configure(text=self.t(key))
        for key, label in self.notify_labels.items():
            label.configure(text=self.t(key))

        for col in self.columns:
            self.tree.heading(col, text=LANG[self.lang]["columns"][col])

        self.refresh_nav_styles()
        self.refresh_all_views()

    def toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.settings_lang_var.set(self.lang)
        self.apply_language()

    def apply_runtime_settings(self):
        try:
            self.check_interval_seconds = max(3, int(self.settings_interval_var.get().strip()))
            self.request_timeout_seconds = max(2, int(self.settings_timeout_var.get().strip()))
            self.fail_threshold = max(1, int(self.settings_threshold_var.get().strip()))
            self.lang = self.settings_lang_var.get().strip() or self.lang
            self.state["auto_switch_enabled"] = bool(self.auto_switch_var.get())
            self.state["notify_on_reply"] = bool(self.notify_on_reply_var.get())
            self.state["notify_sound_ms"] = max(60, min(2000, int(self.settings_notify_duration_var.get().strip())))
            self.state["notify_sound_volume"] = max(0, min(100, int(self.settings_notify_volume_var.get().strip())))
            self.save_state()
            self.apply_language()
            messagebox.showinfo(APP_NAME, self.t("settings_saved"))
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def append_log(self, line):
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")

    def clear_log_view(self):
        self.log_text.delete("1.0", "end")

    def load_state(self):
        if os.path.exists(STATE_PATH):
            try:
                return load_json(STATE_PATH)
            except Exception:
                pass
        return {"providers": {}, "priority": [], "last_switch": None, "auto_switch_enabled": False, "notify_on_reply": True, "notify_sound_ms": 180, "notify_sound_volume": 70}

    def save_state(self):
        self.state["auto_switch_enabled"] = bool(self.auto_switch_var.get())
        self.state["notify_on_reply"] = bool(self.notify_on_reply_var.get())
        save_json(STATE_PATH, self.state)

    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")
        cfg = load_json(CONFIG_PATH)
        self.config_cache = cfg
        self.config_mtime = file_mtime(CONFIG_PATH)
        providers_cfg = deep_get(cfg, "models", "providers", default={}) or {}
        primary = deep_get(cfg, "agents", "defaults", "model", default={}).get("primary", "") or ""
        fallbacks = deep_get(cfg, "agents", "defaults", "model", default={}).get("fallbacks", []) or []

        ordered_model_refs = []
        if primary:
            ordered_model_refs.append(primary)
        for item in fallbacks:
            if item not in ordered_model_refs:
                ordered_model_refs.append(item)

        provider_priority_from_config = []
        for model_ref in ordered_model_refs:
            if "/" in model_ref:
                provider_id = model_ref.split("/", 1)[0]
                if provider_id not in provider_priority_from_config:
                    provider_priority_from_config.append(provider_id)

        all_provider_ids = list(providers_cfg.keys())
        saved_priority = self.state.get("priority", [])
        merged_priority = []
        for pid in saved_priority + provider_priority_from_config + all_provider_ids:
            if pid in providers_cfg and pid not in merged_priority:
                merged_priority.append(pid)

        providers = []
        for idx, provider_id in enumerate(merged_priority, start=1):
            p = providers_cfg[provider_id]
            model_id = ""
            model_name = ""
            models = p.get("models", [])
            if models:
                model_id = models[0].get("id", "")
                model_name = models[0].get("name", model_id)
            model_ref = f"{provider_id}/{model_id}" if model_id else provider_id
            provider_state = self.state["providers"].get(provider_id, {})
            providers.append({
                "priority": idx,
                "provider_id": provider_id,
                "base_url": p.get("baseUrl", ""),
                "api": p.get("api", ""),
                "model_id": model_id,
                "model_name": model_name,
                "model_ref": model_ref,
                "enabled": provider_state.get("enabled", True),
                "status": provider_state.get("status", "unknown"),
                "status_code": provider_state.get("status_code"),
                "latency": provider_state.get("latency", "-"),
                "failures": provider_state.get("failures", 0),
                "last_check": provider_state.get("last_check", "-"),
                "last_error": provider_state.get("last_error", ""),
                "is_primary": model_ref == primary,
            })
        self.providers = providers
        self.state["priority"] = [p["provider_id"] for p in providers]
        self.current_model_var.set(self.t("current_primary", value=primary or "-"))
        self.save_state()

    def refresh_summary(self):
        total = len(self.providers)
        online = len([p for p in self.providers if p.get("enabled") and p.get("status") == "online"])
        offline = len([p for p in self.providers if p.get("enabled") and p.get("status") == "offline"])
        current = next((p["provider_id"] for p in self.providers if p.get("is_primary")), "-")
        last_switch = self.state.get("last_switch")
        if last_switch:
            last_switch_text = f"{last_switch.get('from')} → {last_switch.get('to')} @ {last_switch.get('time')}"
        else:
            last_switch_text = self.t("summary_none")
        self.summary_total_var.set(self.t("summary_total", value=total))
        self.summary_online_var.set(self.t("summary_online", value=online))
        self.summary_offline_var.set(self.t("summary_offline", value=offline))
        self.summary_current_var.set(self.t("summary_current", value=current))
        self.summary_last_switch_var.set(self.t("summary_last_switch", value=last_switch_text))

    def get_visual_status(self, provider):
        if not provider["enabled"]:
            return "disabled"
        if provider["is_primary"]:
            return "current"
        if provider["status"] == "online":
            return "online"
        if provider["status"] == "offline":
            return "offline"
        return "unknown"

    def status_dot(self, visual_status):
        return {"current": "🔵", "online": "🟢", "offline": "🔴", "disabled": "⚪", "unknown": "🟡"}.get(visual_status, "🟡")

    def status_text(self, provider, visual_status):
        if visual_status == "disabled":
            return LANG[self.lang]["status"]["disabled"]
        if visual_status == "current":
            return LANG[self.lang]["status"]["current"]
        if provider["status"] == "online" and provider.get("status_code") not in (None, 200):
            return f"{LANG[self.lang]['status']['reachable']} ({provider['status_code']})"
        return LANG[self.lang]["status"].get(provider["status"], provider["status"])

    def shorten(self, text, limit=MODEL_DISPLAY_MAX):
        text = str(text or "")
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def model_label(self, provider):
        base = provider["model_name"] or provider["model_id"] or provider["provider_id"]
        if provider["is_primary"]:
            base = f"{base} · {self.t('current_tag')}"
        return self.shorten(base)

    def refresh_table(self):
        selected = self.selected_provider_id
        model_font = tkfont.nametofont("TkDefaultFont")
        max_model_width = MODEL_COLUMN_MIN
        for p in self.providers:
            text_width = model_font.measure(self.model_label(p)) + 32
            max_model_width = min(MODEL_COLUMN_MAX, max(max_model_width, text_width))
        self.tree.column("model", width=max_model_width, minwidth=MODEL_COLUMN_MIN, anchor="w")
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.providers:
            visual_status = self.get_visual_status(p)
            values = (p["priority"], self.model_label(p), self.status_text(p, visual_status), p["latency"])
            self.tree.insert("", "end", iid=p["provider_id"], values=values, tags=(visual_status,))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)

    def refresh_all_views(self):
        self.refresh_summary()
        self.refresh_table()

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self.selected_provider_id = selection[0]

    def on_double_click(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self.selected_provider_id = selection[0]
            provider = self.get_selected_provider()
            if provider:
                self.open_detail_popup(provider)

    def get_selected_provider(self):
        if not self.selected_provider_id:
            return None
        return next((p for p in self.providers if p["provider_id"] == self.selected_provider_id), None)

    def open_detail_popup(self, provider=None, is_new=False):
        popup = tk.Toplevel(self.root)
        popup.title(self.t("detail_popup_title"))
        popup.geometry("620x720")
        popup.minsize(560, 640)
        popup.configure(bg="#eef2f7")

        var_provider_id = tk.StringVar(value="" if is_new or provider is None else provider["provider_id"])
        var_model_name = tk.StringVar(value="" if is_new or provider is None else provider["model_name"])
        var_model_id = tk.StringVar(value="" if is_new or provider is None else provider["model_id"])
        var_base_url = tk.StringVar(value="" if is_new or provider is None else provider["base_url"])
        var_api = tk.StringVar(value="openai-completions" if is_new or provider is None else provider["api"])
        var_enabled = tk.BooleanVar(value=True if is_new or provider is None else provider["enabled"])
        var_is_primary = tk.BooleanVar(value=False if is_new or provider is None else provider["is_primary"])
        var_status = tk.StringVar(value="-" if is_new or provider is None else self.status_text(provider, self.get_visual_status(provider)))
        var_latency = tk.StringVar(value="-" if is_new or provider is None else str(provider["latency"]))
        var_failures = tk.StringVar(value="0" if is_new or provider is None else str(provider["failures"]))
        var_last_check = tk.StringVar(value="-" if is_new or provider is None else provider["last_check"])
        var_last_error = tk.StringVar(value="-" if is_new or provider is None else (provider["last_error"] or "-"))
        original_provider_id = None if is_new or provider is None else provider["provider_id"]

        card = ttk.Frame(popup, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ttk.Label(card, text=self.t("detail_popup_title"), style="Header.TLabel").pack(anchor="w")

        body = ttk.Frame(card, style="Card.TFrame")
        body.pack(fill="both", expand=True, pady=(12, 0))

        def add_row(row, label_text, widget):
            ttk.Label(body, text=label_text, style="Sub.TLabel").grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            widget.grid(row=row, column=1, sticky="ew", pady=6)

        add_row(0, self.t("field_provider_id"), ttk.Entry(body, textvariable=var_provider_id))
        add_row(1, self.t("field_model_name"), ttk.Entry(body, textvariable=var_model_name))
        add_row(2, self.t("field_model_id"), ttk.Entry(body, textvariable=var_model_id))
        add_row(3, self.t("field_base_url"), ttk.Entry(body, textvariable=var_base_url))
        add_row(4, self.t("field_api"), ttk.Entry(body, textvariable=var_api))
        add_row(5, self.t("field_enabled"), ttk.Checkbutton(body, variable=var_enabled))
        add_row(6, self.t("field_is_primary"), ttk.Checkbutton(body, variable=var_is_primary))
        ttk.Label(body, text=self.t("detail_section_runtime"), style="Header.TLabel", font=("Segoe UI", 11, "bold")).grid(row=7, column=0, columnspan=2, sticky="w", pady=(16, 8))
        add_row(8, self.t("field_status"), ttk.Label(body, textvariable=var_status, style="Sub.TLabel"))
        add_row(9, self.t("field_latency"), ttk.Label(body, textvariable=var_latency, style="Sub.TLabel"))
        add_row(10, self.t("field_failures"), ttk.Label(body, textvariable=var_failures, style="Sub.TLabel"))
        add_row(11, self.t("field_last_check"), ttk.Label(body, textvariable=var_last_check, style="Sub.TLabel"))
        last_error_box = tk.Text(body, height=5, wrap="word", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        last_error_box.insert("1.0", var_last_error.get())
        last_error_box.configure(state="disabled")
        add_row(12, self.t("field_last_error"), last_error_box)
        body.columnconfigure(1, weight=1)

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(14, 0))

        def save_popup():
            if not all([var_provider_id.get().strip(), var_model_name.get().strip(), var_model_id.get().strip(), var_base_url.get().strip(), var_api.get().strip()]):
                messagebox.showerror(APP_NAME, self.t("field_required"), parent=popup)
                return
            new_provider_id = var_provider_id.get().strip()
            model_name = var_model_name.get().strip()
            model_id = var_model_id.get().strip()
            base_url = var_base_url.get().strip()
            api = var_api.get().strip()
            enabled = var_enabled.get()
            is_primary = var_is_primary.get()

            cfg = load_json(CONFIG_PATH)
            providers_cfg = cfg.setdefault("models", {}).setdefault("providers", {})
            model_section = cfg.setdefault("agents", {}).setdefault("defaults", {}).setdefault("model", {})
            primary = model_section.get("primary", "")
            fallbacks = model_section.get("fallbacks", []) or []

            if is_new and new_provider_id in providers_cfg:
                messagebox.showerror(APP_NAME, self.t("provider_exists", provider=new_provider_id), parent=popup)
                return
            if (not is_new) and new_provider_id != original_provider_id and new_provider_id in providers_cfg:
                messagebox.showerror(APP_NAME, self.t("provider_exists", provider=new_provider_id), parent=popup)
                return

            old_model_ref = None
            if original_provider_id:
                old_provider = providers_cfg.get(original_provider_id, {})
                old_models = old_provider.get("models", [])
                old_model_id = old_models[0].get("id", "") if old_models else ""
                old_model_ref = f"{original_provider_id}/{old_model_id}" if old_model_id else original_provider_id

            if original_provider_id and original_provider_id != new_provider_id:
                providers_cfg.pop(original_provider_id, None)
                if original_provider_id in self.state.get("providers", {}):
                    self.state["providers"][new_provider_id] = self.state["providers"].pop(original_provider_id)
                self.state["priority"] = [new_provider_id if x == original_provider_id else x for x in self.state.get("priority", [])]

            providers_cfg[new_provider_id] = {
                "baseUrl": base_url,
                "api": api,
                "models": [{"id": model_id, "name": model_name}],
            }
            new_model_ref = f"{new_provider_id}/{model_id}"
            if old_model_ref:
                if primary == old_model_ref:
                    primary = new_model_ref
                fallbacks = [new_model_ref if x == old_model_ref else x for x in fallbacks]
            if is_primary or not primary:
                primary = new_model_ref

            provider_order = []
            if primary:
                pid = primary.split("/", 1)[0]
                if pid in providers_cfg:
                    provider_order.append(pid)
            for item in fallbacks:
                pid = item.split("/", 1)[0]
                if pid in providers_cfg and pid not in provider_order:
                    provider_order.append(pid)
            for pid in self.state.get("priority", []):
                if pid in providers_cfg and pid not in provider_order:
                    provider_order.append(pid)
            for pid in providers_cfg.keys():
                if pid not in provider_order:
                    provider_order.append(pid)
            if new_provider_id in provider_order:
                provider_order.remove(new_provider_id)
            if is_primary:
                provider_order.insert(0, new_provider_id)
            else:
                provider_order.append(new_provider_id)

            primary_ref = primary or f"{provider_order[0]}/{providers_cfg[provider_order[0]]['models'][0]['id']}"
            if is_primary:
                primary_ref = new_model_ref
            fallback_refs = []
            for pid in provider_order:
                ref = f"{pid}/{providers_cfg[pid]['models'][0]['id']}"
                if ref != primary_ref:
                    fallback_refs.append(ref)
            model_section["primary"] = primary_ref
            model_section["fallbacks"] = fallback_refs
            save_json(CONFIG_PATH, cfg)

            provider_state = self.state.setdefault("providers", {}).setdefault(new_provider_id, {})
            provider_state["enabled"] = enabled
            self.save_state()

            self.load_config()
            saved_provider = next((p for p in self.providers if p["provider_id"] == new_provider_id), None)
            if saved_provider:
                saved_provider["enabled"] = enabled
                self.persist_provider_state(saved_provider)
                if is_primary:
                    for p in self.providers:
                        p["is_primary"] = (p["provider_id"] == new_provider_id)
                self.selected_provider_id = new_provider_id
            self.refresh_all_views()
            self.append_log(log(self.t("detail_saved", provider=new_provider_id)))
            popup.destroy()

        def delete_popup():
            current_provider = next((p for p in self.providers if p["provider_id"] == (original_provider_id or var_provider_id.get().strip())), None)
            if not current_provider:
                popup.destroy()
                return
            if not messagebox.askyesno(APP_NAME, self.t("detail_delete_confirm", provider=current_provider["provider_id"]), parent=popup):
                return
            cfg = load_json(CONFIG_PATH)
            providers_cfg = cfg.setdefault("models", {}).setdefault("providers", {})
            model_section = cfg.setdefault("agents", {}).setdefault("defaults", {}).setdefault("model", {})
            delete_id = current_provider["provider_id"]
            delete_ref = current_provider["model_ref"]
            providers_cfg.pop(delete_id, None)
            self.state.get("providers", {}).pop(delete_id, None)
            self.state["priority"] = [x for x in self.state.get("priority", []) if x != delete_id]
            primary = model_section.get("primary", "")
            fallbacks = [x for x in (model_section.get("fallbacks", []) or []) if x != delete_ref]
            remaining_refs = []
            for pid, p in providers_cfg.items():
                models = p.get("models", [])
                if models:
                    remaining_refs.append(f"{pid}/{models[0].get('id', '')}")
            if primary == delete_ref:
                if remaining_refs:
                    primary = remaining_refs[0]
                    self.append_log(log(self.t("delete_primary_blocked")))
                else:
                    primary = ""
            if primary:
                fallbacks = [x for x in fallbacks if x != primary]
            else:
                fallbacks = []
            model_section["primary"] = primary
            model_section["fallbacks"] = fallbacks
            save_json(CONFIG_PATH, cfg)
            self.save_state()
            self.selected_provider_id = None
            self.load_config()
            self.refresh_all_views()
            self.append_log(log(self.t("detail_deleted", provider=delete_id)))
            popup.destroy()

        def reset_popup():
            popup.destroy()
            if provider:
                self.open_detail_popup(provider, is_new=False)
            else:
                self.open_detail_popup(None, is_new=True)

        ttk.Button(actions, text=self.t("save"), style="Accent.TButton", command=save_popup).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text=self.t("reset"), style="Action.TButton", command=reset_popup).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text=self.t("delete"), style="Action.TButton", command=delete_popup).pack(side="right")

    def new_provider(self):
        self.open_detail_popup(None, is_new=True)
        self.append_log(log(self.t("detail_new_created")))

    def manual_reload(self):
        try:
            self.load_config()
            self.refresh_all_views()
            self.append_log(log(self.t("config_reloaded")))
        except Exception as e:
            self.append_log(log(str(e)))
            messagebox.showerror(APP_NAME, self.t("reload_failed", error=e))

    def check_now(self):
        provider = self.get_selected_provider()
        if provider is None:
            threading.Thread(target=self.run_health_checks, daemon=True).start()
        else:
            threading.Thread(target=self.check_single_provider, args=(provider["provider_id"],), daemon=True).start()

    def check_all(self):
        if self.testing_all:
            return
        self.testing_all = True
        self.append_log(log(self.t("check_all_started")))
        threading.Thread(target=self.run_health_checks, daemon=True).start()

    def reorder_selected(self, delta):
        if not self.selected_provider_id:
            return
        idx = next((i for i, p in enumerate(self.providers) if p["provider_id"] == self.selected_provider_id), None)
        if idx is None:
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.providers):
            return
        self.providers[idx], self.providers[new_idx] = self.providers[new_idx], self.providers[idx]
        for i, p in enumerate(self.providers, start=1):
            p["priority"] = i
        self.state["priority"] = [p["provider_id"] for p in self.providers]
        self.save_state()
        self.refresh_all_views()

    def move_up(self):
        self.reorder_selected(-1)

    def move_down(self):
        self.reorder_selected(1)

    def set_selected_primary(self):
        provider = self.get_selected_provider()
        if not provider:
            messagebox.showinfo(APP_NAME, self.t("select_provider_first"))
            return
        for p in self.providers:
            p["is_primary"] = (p["provider_id"] == provider["provider_id"])
        self.refresh_all_views()
        self.append_log(log(self.t("selected_primary", provider=provider["provider_id"])))

    def enable_selected(self):
        provider = self.get_selected_provider()
        if not provider:
            messagebox.showinfo(APP_NAME, self.t("select_provider_first"))
            return
        provider["enabled"] = True
        self.persist_provider_state(provider)
        self.refresh_all_views()
        self.append_log(log(self.t("provider_enabled", provider=provider["provider_id"])))

    def disable_selected(self):
        provider = self.get_selected_provider()
        if not provider:
            messagebox.showinfo(APP_NAME, self.t("select_provider_first"))
            return
        provider["enabled"] = False
        self.persist_provider_state(provider)
        self.refresh_all_views()
        self.append_log(log(self.t("provider_disabled", provider=provider["provider_id"])))

    def persist_provider_state(self, provider):
        self.state["providers"][provider["provider_id"]] = {
            "enabled": provider["enabled"],
            "status": provider.get("status", "unknown"),
            "status_code": provider.get("status_code"),
            "latency": provider.get("latency", "-"),
            "failures": provider.get("failures", 0),
            "last_check": provider.get("last_check", "-"),
            "last_error": provider.get("last_error", ""),
        }
        self.save_state()

    def save_priority(self):
        try:
            self.write_priority_to_config(apply_selected_primary=False)
            self.append_log(log(self.t("priority_saved")))
            messagebox.showinfo(APP_NAME, self.t("save_success"))
        except Exception as e:
            self.append_log(log(str(e)))
            messagebox.showerror(APP_NAME, self.t("save_failed", error=e))

    def apply_switch_now(self):
        try:
            self.write_priority_to_config(apply_selected_primary=True)
            self.restart_gateway()
            self.append_log(log(self.t("manual_switch_applied")))
            messagebox.showinfo(APP_NAME, self.t("apply_success"))
        except Exception as e:
            self.append_log(log(str(e)))
            messagebox.showerror(APP_NAME, self.t("apply_failed", error=e))

    def open_folder(self):
        os.startfile(WORK_DIR)

    def write_priority_to_config(self, apply_selected_primary=False):
        cfg = load_json(CONFIG_PATH)
        model_section = cfg.setdefault("agents", {}).setdefault("defaults", {}).setdefault("model", {})
        ordered = list(self.providers)
        target_primary = None
        if apply_selected_primary:
            selected = next((p for p in ordered if p["is_primary"]), None)
            if selected is None and ordered:
                selected = ordered[0]
            if selected:
                ordered = [selected] + [p for p in ordered if p["provider_id"] != selected["provider_id"]]
                target_primary = selected["model_ref"]
        if target_primary is None and ordered:
            current_marked = next((p for p in ordered if p["is_primary"]), None)
            target_primary = current_marked["model_ref"] if current_marked else ordered[0]["model_ref"]
        enabled_order = [p for p in ordered if p["enabled"]]
        if not enabled_order:
            raise RuntimeError(self.t("no_enabled_providers"))
        if target_primary not in [p["model_ref"] for p in enabled_order]:
            target_primary = enabled_order[0]["model_ref"]
        fallbacks = [p["model_ref"] for p in enabled_order if p["model_ref"] != target_primary]
        model_section["primary"] = target_primary
        model_section["fallbacks"] = fallbacks
        save_json(CONFIG_PATH, cfg)
        self.load_config()
        self.refresh_all_views()
        self.append_log(log(self.t("config_updated", primary=target_primary, fallbacks=fallbacks)))

    def restart_gateway(self):
        candidates = [r"C:\Program Files (x86)\ClawX\resources\cli\openclaw.cmd", r"C:\Program Files\ClawX\resources\cli\openclaw.cmd"]
        openclaw_cmd = next((p for p in candidates if os.path.exists(p)), None)
        if not openclaw_cmd:
            raise FileNotFoundError(self.t("openclaw_not_found"))
        subprocess.run([openclaw_cmd, "gateway", "restart"], check=True, timeout=60)
        self.append_log(log(self.t("gateway_restarted")))

    def background_loop(self):
        while self.running:
            try:
                current_mtime = file_mtime(CONFIG_PATH)
                if current_mtime and current_mtime != self.config_mtime:
                    self.root.after(0, self.manual_reload)
                self.run_health_checks(silent=True)
                self.check_gateway_reply_completion()
            except Exception as e:
                self.root.after(0, lambda e=e: self.append_log(log(self.t("background_loop_error", error=e))))
            for _ in range(self.check_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

    def provider_health_url(self, provider):
        base = provider.get("base_url", "").rstrip("/")
        return base + "/models" if base else None

    def update_provider_probe(self, provider):
        url = self.provider_health_url(provider)
        if not provider["enabled"]:
            provider["status"] = "disabled"
            provider["status_code"] = None
            provider["latency"] = "-"
            provider["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            provider["last_error"] = "disabled"
            self.persist_provider_state(provider)
            return
        if not url:
            provider["status"] = "offline"
            provider["status_code"] = None
            provider["latency"] = "-"
            provider["failures"] += 1
            provider["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            provider["last_error"] = self.t("missing_base_url")
            self.persist_provider_state(provider)
            return
        result = probe_url(url, timeout=self.request_timeout_seconds)
        provider["last_check"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        provider["status_code"] = result["status_code"]
        provider["latency"] = result["latency_ms"]
        provider["last_error"] = result["error"]
        if result["reachable"]:
            provider["status"] = "online"
            provider["failures"] = 0
        else:
            provider["status"] = "offline"
            provider["failures"] += 1
        self.persist_provider_state(provider)

    def check_single_provider(self, provider_id):
        provider = next((p for p in self.providers if p["provider_id"] == provider_id), None)
        if not provider:
            return
        self.update_provider_probe(provider)
        self.root.after(0, self.refresh_all_views)
        self.root.after(0, lambda: self.append_log(log(f"{provider['provider_id']}: {self.status_text(provider, self.get_visual_status(provider))}, latency={provider['latency']}")))

    def run_health_checks(self, silent=False):
        for provider in self.providers:
            self.update_provider_probe(provider)
        self.root.after(0, self.refresh_all_views)
        if not silent:
            self.root.after(0, lambda: self.append_log(log(self.t("check_ok"))))
        if self.auto_switch_var.get():
            self.try_auto_switch()
        self.testing_all = False

    def try_auto_switch(self):
        current = next((p for p in self.providers if p["is_primary"]), None)
        if not current:
            return
        if current["status"] == "online" and current["failures"] < self.fail_threshold:
            return
        if current["failures"] < self.fail_threshold:
            return
        fallback = next((p for p in self.providers if p["enabled"] and p["provider_id"] != current["provider_id"] and p["status"] == "online"), None)
        if not fallback:
            self.root.after(0, lambda: self.append_log(log(self.t("auto_switch_skipped"))))
            return
        for p in self.providers:
            p["is_primary"] = (p["provider_id"] == fallback["provider_id"])
        try:
            self.write_priority_to_config(apply_selected_primary=True)
            self.restart_gateway()
            self.state["last_switch"] = {"from": current["provider_id"], "to": fallback["provider_id"], "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "reason": f"failure threshold reached ({current['failures']})"}
            self.save_state()
            self.root.after(0, self.refresh_summary)
            self.root.after(0, lambda: self.append_log(log(self.t("auto_switched", src=current["provider_id"], dst=fallback["provider_id"]))))
        except Exception as e:
            self.root.after(0, lambda e=e: self.append_log(log(self.t("auto_switch_failed", error=e))))

    def play_notify_sound(self):
        sound_path = os.path.join(WORK_DIR, "notify.wav")
        try:
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
        except Exception:
            pass
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return
        except Exception:
            pass
        try:
            self.root.bell()
        except Exception:
            pass

    def check_gateway_reply_completion(self):
        if not self.notify_on_reply_var.get():
            return
        sessions_dir = os.path.expandvars(r"%USERPROFILE%\.openclaw\agents\main\sessions")
        if not os.path.isdir(sessions_dir):
            return
        latest = None
        latest_mtime = 0
        for name in os.listdir(sessions_dir):
            if not name.endswith(".jsonl") or name.endswith(".deleted.jsonl") or ".reset." in name:
                continue
            path = os.path.join(sessions_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest = path
        if not latest:
            return
        tail = read_text_tail(latest, max_bytes=8192)
        if not tail or tail == self.last_seen_gateway_message:
            return
        lines = [line for line in tail.splitlines() if line.strip()]
        if not lines:
            return
        last_line = lines[-1]
        if last_line == self.last_seen_gateway_message:
            return
        try:
            event = json.loads(last_line)
        except Exception:
            return
        message = event.get("message", {})
        if event.get("type") != "message" or message.get("role") != "assistant":
            return
        self.last_seen_gateway_message = last_line
        self.root.after(0, self.play_notify_sound)

    def is_watchdog_running(self):
        if os.path.exists(WATCHDOG_PID_PATH):
            try:
                with open(WATCHDOG_PID_PATH, "r", encoding="utf-8") as f:
                    pid = f.read().strip()
                if pid:
                    result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=10)
                    return pid in result.stdout
            except Exception:
                pass
        return False

    def refresh_watchdog_panel(self):
        status = self.t("watchdog_running") if self.is_watchdog_running() else self.t("watchdog_stopped")
        self.watchdog_status_label.configure(text=self.t("watchdog_status", value=status))
        self.watchdog_path_label.configure(text=self.t("watchdog_script", value=WATCHDOG_SCRIPT_PATH))
        self.watchdog_log_text.delete("1.0", "end")
        if os.path.exists(WATCHDOG_LOG_PATH):
            try:
                with open(WATCHDOG_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-300:]
                self.watchdog_log_text.insert("end", "".join(lines))
                self.watchdog_log_text.see("end")
            except Exception as e:
                self.watchdog_log_text.insert("end", str(e))

    def start_watchdog(self):
        try:
            if self.is_watchdog_running():
                self.refresh_watchdog_panel()
                return
            if not os.path.exists(WATCHDOG_SCRIPT_PATH):
                raise FileNotFoundError(WATCHDOG_SCRIPT_PATH)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            python_exe = sys.executable or "py"
            proc = subprocess.Popen(
                [python_exe, WATCHDOG_SCRIPT_PATH],
                cwd=WORK_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            with open(WATCHDOG_PID_PATH, "w", encoding="utf-8") as f:
                f.write(str(proc.pid))
            self.refresh_watchdog_panel()
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def stop_watchdog(self):
        try:
            pid = ""
            if os.path.exists(WATCHDOG_PID_PATH):
                with open(WATCHDOG_PID_PATH, "r", encoding="utf-8") as f:
                    pid = f.read().strip()
            if pid:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=10)
            if os.path.exists(WATCHDOG_PID_PATH):
                os.remove(WATCHDOG_PID_PATH)
            self.refresh_watchdog_panel()
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    ProviderManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
