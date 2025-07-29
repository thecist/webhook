import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import sys

JOBS_DIR = Path("jobs")
VENVS_DIR = Path(".venvs")

def prepare_venv(job_name: str) -> Path:
  venv_path = VENVS_DIR / job_name
  if not venv_path.exists():
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
  if os.name == "nt":
    python_path = venv_path / "Scripts" / "python.exe"
    if not python_path.exists(): # fallback for MSYS2 layout (bash for windows python3 alias)
      python_path = venv_path / "bin" / "python.exe"
  else:
    python_path = venv_path / "bin" / "python"
  req_file = JOBS_DIR / job_name / "requirements.txt"

  if req_file.exists():
    subprocess.run([str(python_path), "-m", "pip", "install", "-r", str(req_file)], check=True)
  return venv_path

def load_env(job_name: str):
  env_path = Path(".env")
  if env_path.exists():
    load_dotenv(dotenv_path=env_path)
  job_env_path = JOBS_DIR / job_name / ".env"
  if job_env_path.exists():
    load_dotenv(dotenv_path=job_env_path)