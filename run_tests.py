"""Run pytest and write the summary to a file (avoids PS redirect issues)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
log = ROOT / "logs" / "pytest_full.log"
log.parent.mkdir(parents=True, exist_ok=True)
args = [sys.executable, "-m", "pytest", "tests/", "-q"]
print("Running:", " ".join(args))
result = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=180)
log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
print(f"exit={result.returncode}")
print("=" * 60)
# Print last 30 lines
lines = (result.stdout + result.stderr).strip().splitlines()
for line in lines[-30:]:
    print(line)
