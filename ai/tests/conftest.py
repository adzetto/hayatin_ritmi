"""pytest configuration — add ai/training to sys.path for imports."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "training"))
