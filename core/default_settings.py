from pydantic import BaseModel, Field
from typing import Optional, Optional, Generic, TypeVar

T = TypeVar("T")

def config_field(default=..., user_editable: bool=False, **kwargs):
  return Field(default=default, user_editable=user_editable, **kwargs)

class DefaultSettings(BaseModel, Generic[T]):
  name: str = config_field(..., description="Name of the job")
  module: str = config_field(..., pattern=r'^jobs/[a-zA-Z0-9_/]+\.py$', description="Module path of the job")
  # TODO: Create a way to validate cron expressions
  cron: Optional[str] = config_field(None, True, description="Cron expression for scheduling the job")
  enabled: bool = config_field(False, True, description="Whether the job is enabled or not")
  defaults: Optional[T] = config_field(None, description="Default values for the job")
