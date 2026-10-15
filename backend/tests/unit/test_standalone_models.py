import subprocess
import sys


def test_standalone_worker_and_cli_can_resolve_all_model_dependencies():
    for module in ("vowen.modules.rituals.worker", "vowen.cli.main"):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import {module}; from vowen.core.database import Base; "
                "assert Base.metadata.sorted_tables",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
