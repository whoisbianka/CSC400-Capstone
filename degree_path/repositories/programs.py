"""Demo repository: replace this class with PostgreSQL access when the schema is ready."""
import json
from pathlib import Path


class DemoProgramRepository:
    is_demo = True
    tuition_label = 'Annual demo tuition'
    source_note = 'Demo data only · All colleges, programs, and tuition figures are fictional test fixtures.'

    def __init__(self, path=None):
        self.path = path or Path(__file__).resolve().parents[1] / 'data/demo_programs.json'

    def all(self):
        return json.loads(self.path.read_text(encoding='utf-8'))

    def get(self, program_id):
        return next((p for p in self.all() if p['id'] == program_id), None)
