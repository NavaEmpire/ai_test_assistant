# === models/outputs.py ===
from pydantic import BaseModel

class TestAnalysisOutput(BaseModel):
    is_test_related: bool
    reasoning:str