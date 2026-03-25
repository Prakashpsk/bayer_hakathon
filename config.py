"""
Configuration for Autonomous Incident Commander.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM Model Configuration
MODEL_NAME = os.getenv("PYDANTIC_AI_MODEL", "openai:gpt-4o-mini")

# Incident Simulation Timing
INCIDENT_TIME = "2026-03-25T10:00:00Z"
DEPLOY_TIME = "2026-03-25T09:45:00Z"  # 15 minutes before incident
