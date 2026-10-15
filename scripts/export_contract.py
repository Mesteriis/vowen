import json
from pathlib import Path
from vowen.core.config import Settings
from vowen.main import create_app

path = Path(__file__).resolve().parents[1] / 'contracts/openapi.json'
path.write_text(json.dumps(create_app(Settings()).openapi(), indent=2, sort_keys=True) + '\n')
