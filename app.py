# TODO: Decide if you want your payload flattened (no nested dict or array) in
# order to enable payload/variable injection through cli,
# either that or use a file as payload

# Remember, payload is meant to be dynamic, static data is stored at
# configs.toml

# TODO: Add middleware security
# JWT with scopes
'''
{
  "jobs": []
}
'''
# TODO: Add a cli script for generating JWT tokens

import os
from fastapi import FastAPI
from core.job_runner import router
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 8000))

app = FastAPI(
  title="TheCist's webhook",
  description="Trigger any background or sync job via HTTP",
  version="0.0.1",
  contact={
    "name": "TheCist",
    "github": "https://github.com/thecist/webhook",
    "email": "me@thecist.dev"
  }
)

app.include_router(router)

# health check
@app.get("/")
def root():
  return {"status": "ok"}
  
if __name__ == "__main__":
  import uvicorn

  # reload=true messes with the venv creation logic and
  # reload_excludes=[".venv/*", ".venvs/*"] doesn't fix it
  uvicorn.run("app:app", host="0.0.0.0", reload=True, port=PORT, reload_includes=["configs.toml", "defaults.toml"], reload_excludes=["*"])
