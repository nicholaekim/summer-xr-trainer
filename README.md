# XR Trainer / StretchSense glove pipeline

Real-time pipeline: **glove → XR Trainer → OSC (UDP) → validate → parse → 3D viz → record → CSV export**.

26 joints per hand (OpenXR `XR_HAND_JOINT` layout), each with local position + quaternion, captured at ~60 Hz.

## Install (Windows / PowerShell)

```powershell
cd "C:\Users\nkim2\Desktop\xr trainer"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

If `Activate.ps1` is blocked, run once per machine:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Daily use (real glove)

With XR Trainer running and the glove streaming on `127.0.0.1:9002`:

**One-command record + playback + export** (recommended):
```powershell
.\scripts\record_and_export.ps1               # 10 s default
.\scripts\record_and_export.ps1 -Duration 30  # 30 s
```
Produces `recordings\realglove_YYYYMMDD_HHMMSS.jsonl` and `.csv`.

**Just the live viewer** (no recording):
```powershell
python scripts/run_osc.py
```

**Live viewer + record** (no auto-close, close the window when done):
```powershell
python scripts/run_osc.py --record recordings/my_session.jsonl
```

**Diagnose a stream** (raw packet log, no viewer):
```powershell
python scripts/run_osc.py --dump --no-viz
```

## Without the glove (mock pipeline)

```powershell
python scripts/run_mock.py                                  # animated mock viewer
python scripts/record.py --mock --duration 10               # write mock recording
python scripts/playback.py recordings/<file>.jsonl          # replay any recording
python scripts/export.py recordings/<file>.jsonl            # JSONL → CSV
python scripts/test_faults.py                               # headless fault checks
```

## Tests

```powershell
pytest -q
```

## Layout

```
src/xr_hand/
  joints.py       26 joint names + bone connectivity + dataclasses
  parser.py       187 OSC args → HandFrame (XYZW quaternion, local positions)
  validator.py    per-packet checks (length/NaN/zero/quat) + StreamMonitor
  mock.py         hand-frame generator with toggleable fault modes
  receiver.py     OSC server (port 9002, /v1/animation/kinematic/all)
  recorder.py     JSONL record + load
  viz3d.py        matplotlib 3D viewer (cyan left, red right, palm fill)
  kinematics.py   forward kinematics (local transforms → world positions)
scripts/
  run_osc.py            live viewer (real glove) + optional --record / --duration
  run_mock.py           live viewer (in-process mock)
  record.py             headless recorder (supports --mock)
  playback.py           replay a .jsonl through the viewer
  export.py             .jsonl → .csv (one row per frame, joint columns)
  test_faults.py        headless fault-injection sanity check
  record_and_export.ps1 the one-command pipeline (record + playback + export)
tests/
  test_pipeline.py      parser, validator, StreamMonitor
  test_recorder.py      record/load round-trip
```

## Wire format reference

XR Trainer sends to `127.0.0.1:9002` on address `/v1/animation/kinematic/all` with 187 args:

- **Header (5)**: `[tick_counter, frame_id, status, "Reality Glove (L/R)" str, "Reality Glove" str]`
- **Joints (26 × 7)**: per joint `[x, y, z, qx, qy, qz, qw]`
  - position is **parent-relative** (local space)
  - quaternion is **XYZW**

Hand side is extracted from the device-label string at arg `[3]`. Header string fields are normalised to `0.0` placeholders so the downstream validator/parser see numeric data only.

## CSV format

One row per frame. Columns:
```
wall_time, iso_time, timestamp, packet_counter, hand_side, frame_id, status,
PALM_x, PALM_y, PALM_z, PALM_qw, PALM_qx, PALM_qy, PALM_qz,
WRIST_x, WRIST_y, WRIST_z, WRIST_qw, WRIST_qx, WRIST_qy, WRIST_qz,
THUMB_METACARPAL_x, ... (26 joints × 7 columns)
```
