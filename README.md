# ClawX Manager Suite

A rebuilt desktop management suite for ClawX / OpenClaw, based on the stable portable Provider Manager and integrated with ClawX Watchdog.

## What it includes

- **Providers**
  - View provider/model priority
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
  - Reply completion is detected from:
    - `%USERPROFILE%\.openclaw\agents\main\sessions\*.jsonl`

- **Watchdog**
  - Integrated as a dedicated left-side module page
  - View status
  - View script path
  - View watchdog log output
  - Start / Stop / Refresh

## Project location

Current working project directory:

- `C:\Users\HeHesama\Desktop\ClawX_Manager_Suite_Fresh`

## Key bundled files

- `provider_manager.py`
- `clawx_watchdog.py`
- `clawx_watchdog.log`
- `notify.wav`
- `start.bat`

## Notes

- This repository is the **working integrated suite version**, not the earlier broken rebuild attempts.
- The suite was rebuilt from the stable portable provider-manager base and then re-integrated with Watchdog.
- Reminder sound logic keeps using the local fixed `notify.wav` file.

## Running

### Option 1
Double-click:

- `start.bat`

### Option 2
Run manually:

```bash
py -3 provider_manager.py
```

## Recommended future cleanup

Some runtime-generated files should usually be ignored from version control, such as:

- `__pycache__/`
- `provider_manager.log`
- `watchdog.pid`
- temporary local state / runtime caches

These can be moved into `.gitignore` as the project gets cleaned up further.
