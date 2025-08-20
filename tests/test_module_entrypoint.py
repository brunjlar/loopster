import sys
import subprocess


def test_python_m_loopster_help_exits_zero_and_shows_commands():
  # Run the package as a module, like users do
  proc = subprocess.run(
      [sys.executable, "-m", "loopster", "--help"],
      capture_output=True,
      text=True,
  )

  # Expect a clean exit and help text that includes subcommands
  assert proc.returncode == 0, proc.stderr
  assert "run" in proc.stdout
  assert "capture" in proc.stdout
  assert "analyze" in proc.stdout
  assert "summarize" in proc.stdout
  assert "config" in proc.stdout

