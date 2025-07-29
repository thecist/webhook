from core.default_settings import DefaultSettings, config_field
from pydantic import BaseModel

class Defaults(BaseModel):
  # Notion secrets
  notion_token: str = config_field(..., description="Notion integration token")
  origin_database_id: str = config_field(..., description="Origin Feed Notion database ID")
  view_database_id: str = config_field(..., description="View Feed Notion database ID")

  # Origin Feed
  origin_name_title: str = config_field(..., True, description="The property name of the `name` of the origin feed")
  origin_url_title: str = config_field(..., True, description="The property name of the `URL` of the origin feed")
  origin_status_title: str = config_field(..., True, description="The property name of the `status` of the origin feed")
  origin_status_subscribed: str = config_field(..., True, description="The status value for subscribed feeds")
  
  # View Feed
  view_name_title: str = config_field(..., True, description="The property name of the `name` of the view feed")
  view_description_title: str = config_field(..., True, description="The property name of the `description` of the view feed")
  view_status_title: str = config_field(..., True, description="The property name of the `status` of the view feed")
  view_pub_date_title: str = config_field(..., True, description="The property name of the `pub_date` of the view feed")
  view_id_title: str = config_field(..., True, description="The property name of the `id` of the view feed")
  view_source_title: str = config_field(..., True, description="The property name of the `source` of the view feed")
  view_hash_title: str = config_field(..., True, description="The property name of the `hash` of the view feed")
  view_href_title: str = config_field(..., True, description="The property name of the `href` of the view feed")
  view_status_not_read: str = config_field(..., True, description="The status value for not read feeds")


class NotionRSSSettings(DefaultSettings[Defaults]):
  name: str = config_field("Notion RSS Job", description="Name of the job")
  module: str = config_field("jobs/notion_rss/job.py", pattern=r'^jobs/[a-zA-Z0-9_/]+\.py$', description="Module path of the job")
  defaults: Defaults = config_field(..., description="Default values for notion rss")