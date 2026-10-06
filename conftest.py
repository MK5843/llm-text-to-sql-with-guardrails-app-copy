import os
import sys

# Ensures the project root is on sys.path so `from guardrails import ...`
# works when pytest is run from anywhere in the project.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))