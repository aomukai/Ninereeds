import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open("meta/repair_prompt.txt", "r", encoding="utf-8") as f:
    prompt = f.read()

result = subprocess.run(
    ["opencode", "run",
     "-m", "openrouter/deepseek/deepseek-v4-flash",
     "--dangerously-skip-permissions",
     prompt],
    capture_output=False,
)
sys.exit(result.returncode)
