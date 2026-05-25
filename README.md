# XR Trainer / StretchSense glove pipeline

Real-time pipeline: **glove -> XR Trainer -> Open SDK -> Python OSC -> validate -> parse -> 3D viz**.

Phase 1 (this commit) runs the whole downstream pipeline against a mock
generator so you can develop and debug without hardware. Phase 2 adds the OSC
receiver in front; nothing downstream changes.

## Install (Windows / PowerShell)

```powershell
cd "C:\Users\nkim2\Desktop\xr trainer"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

If `Activate.ps1` is blocked, run once per machine:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Run the mock pipeline

```powershell
python scripts/run_mock.py
```

You should see an interactive 3D window with a blue (left) and red (right)
hand skeleton slowly opening and closing. Click-drag rotates, scroll zooms.
Log lines print every 60 frames per hand.

## Inject faults

Open `scripts/run_mock.py` and uncomment any line in the FAULT INJECTION
block. Each one should produce specific log warnings or errors:

| toggle                          | expected log                                 |
| ------------------------------- | -------------------------------------------- |
| `stuck_fingertip = "INDEX_TIP"` | (visual only) tip stops moving               |
| `freeze_counter = True`         | `packet counter frozen at N`                 |
| `zero_joint = "..."`            | `joint ... is all-zero`                      |
| `wrong_length = True`           | `INVALID: length mismatch...`                |
| `random_missing_prob = 0.005`   | `INVALID: non-finite values at indices ...`  |

## Run tests

```powershell
pytest -q
```

## Layout

```
src/xr_hand/
  joints.py     26 joint names, bone connectivity, dataclasses, constants
  parser.py     187 raw floats -> HandFrame
  validator.py  length / NaN / counter / stuck-joint / quaternion checks
  mock.py       fake hand generator with toggleable fault modes
  viz3d.py      matplotlib 3D skeletal viewer
scripts/
  run_mock.py   wires mock -> validator -> parser -> viewer
tests/
  test_pipeline.py
```

## Phase 2: OSC pipeline (no gloves required)

Same downstream pipeline (validator -> parser -> viewer), but the source is a
real UDP/OSC socket instead of the in-process mock generator.

**Two-terminal test (no hardware):**

Terminal A — pretend to be XR Trainer:
```powershell
.\.venv\Scripts\Activate.ps1
python scripts/mock_osc_sender.py
```

Terminal B — run the receiver + viewer:
```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_osc.py
```

You should see the same two hands animating in 3D. Stop with Ctrl+C in
terminal A or close the viewer window.

**Inject faults over the wire** (sender side):
```powershell
python scripts/mock_osc_sender.py --fault wrong_length
python scripts/mock_osc_sender.py --fault freeze_counter
python scripts/mock_osc_sender.py --fault zero_joint
python scripts/mock_osc_sender.py --fault random_missing
```
Watch the receiver terminal — same warnings/errors as the in-process mock.

**Diagnose a real XR Trainer stream** (when gloves arrive):
```powershell
python scripts/run_osc.py --dump --no-viz
```
Prints one log line per OSC packet (address, arg count, first 5 values). Use
this to confirm XR Trainer's actual address pattern and arg count before
trusting the visualization. If the address differs from `/hand/left` and
`/hand/right`, pass `--left-addr` / `--right-addr`. If the port differs from
9000, pass `--port`.

## What's next (not built yet)

- `src/xr_hand/recorder.py` — record validated frames to JSONL, replay through
  the same viewer.
- Unity bridge — the `HandFrame` dataclass is already the natural wire format.
