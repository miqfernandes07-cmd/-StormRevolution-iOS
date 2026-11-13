#!/usr/bin/env bash
set -euo pipefail
app_path=${1:?application bundle required}
result_path=${2:?result JSON path required}
device_id=$(xcrun simctl list devices available --json | python3 -c '
import json,sys
data=json.load(sys.stdin)
devices=[d for runtime, ds in data["devices"].items() if "iOS" in runtime
         for d in ds if d.get("isAvailable") and "iPhone" in d["name"]]
if not devices: raise SystemExit("No available iPhone simulator; install an iOS simulator runtime")
print(devices[0]["udid"])
')
device_state=$(xcrun simctl list devices available --json | python3 -c '
import json,sys
print(next(d["state"] for ds in json.load(sys.stdin)["devices"].values() for d in ds if d["udid"]==sys.argv[1]))
' "$device_id")
if [ "$device_state" != Booted ]; then xcrun simctl boot "$device_id"; fi
xcrun simctl bootstatus "$device_id" -b
xcrun simctl install "$device_id" "$app_path"
data_path=$(xcrun simctl get_app_container "$device_id" org.stormrevolution.port data)
output_dir=$(cd "$(dirname "$result_path")" && pwd)
diagnose_failure() {
  local result=$?
  if [ "$result" -ne 0 ]; then
    xcrun simctl spawn "$device_id" log show --last 3m --style compact --predicate 'process == "StormRevolution"' > "$output_dir/app-system-log.txt" 2>&1 || true
    xcrun simctl io "$device_id" screenshot "$output_dir/failure-simulator.png" || true
    python3 - "$output_dir" <<'PY'
from pathlib import Path
import shutil,sys
for root in (Path.home()/'Library/Logs/DiagnosticReports',):
    for report in root.glob('StormRevolution*'):
        if report.is_file(): shutil.copy2(report,Path(sys.argv[1])/(report.name+'.txt'))
PY
    cat "$output_dir"/import-*.txt 2>/dev/null || true
  fi
}
trap diagnose_failure EXIT
rm -f "$data_path/Documents/smoke-result.json"
xcrun simctl launch --terminate-running-process "$device_id" org.stormrevolution.port --smoke-test
for attempt in $(seq 1 60); do
  if [ -f "$data_path/Documents/smoke-result.json" ]; then break; fi
  sleep 1
done
test -f "$data_path/Documents/smoke-result.json"
cp "$data_path/Documents/smoke-result.json" "$result_path"
python3 - "$result_path" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    result=json.load(f)
if result.get("runtime_self_test") is not True:
    raise SystemExit("Runtime infrastructure self-test failed")
if result.get("metal_command_completed") is not True:
    raise SystemExit("Metal diagnostic command failed")
if result.get("game_executed") is not False:
    raise SystemExit("Unexpected game-execution claim in infrastructure smoke test")
print("Simulator runtime and Metal command smoke checks passed; no game or pixel comparison tested")
PY
xcrun simctl terminate "$device_id" org.stormrevolution.port
rm -f "$data_path/Documents/import-smoke-result.json"
xcrun simctl launch --stdout="$output_dir/import-stdout.txt" --stderr="$output_dir/import-stderr.txt" "$device_id" org.stormrevolution.port --import-smoke-test
for attempt in $(seq 1 60); do
  if [ -f "$data_path/Documents/import-smoke-result.json" ]; then break; fi
  sleep 1
done
cp "$data_path/Documents/import-smoke-result.json" "$(dirname "$result_path")/import-smoke.json"
python3 - "$data_path/Documents/import-smoke-result.json" <<'PY'
import json,sys
with open(sys.argv[1]) as stream:
    result=json.load(stream)
assert result.get('passed') is True, result
assert result.get('game_executed') is False, result
print('Actual iOS importer rejected synthetic invalid XEX/traversal/cancellation and preserved previous data.')
PY
xcrun simctl terminate "$device_id" org.stormrevolution.port
# Capture the actual application UI, never a generated representation of gameplay.
xcrun simctl launch "$device_id" org.stormrevolution.port
sleep 3
xcrun simctl io "$device_id" screenshot "$(dirname "$result_path")/library-simulator.png"
xcrun simctl terminate "$device_id" org.stormrevolution.port
xcrun simctl launch "$device_id" org.stormrevolution.port --capture-controls
sleep 3
xcrun simctl io "$device_id" screenshot "$(dirname "$result_path")/controls-simulator.png"
xcrun simctl terminate "$device_id" org.stormrevolution.port
