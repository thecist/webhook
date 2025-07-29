# NOTE: Some rss feeds have tags, maybe create tags in notion and add them if
# they exist

# TODO: Think a bit if it's worth deleting the page during an update instead of individual blocks,
# for performace
from .settings import NotionRSSSettings
from .models import FeedSource, FeedReference, FeedView, UpdateFeed
from .utils import get_links, get_feed_references, generate_feeds, update_page_content, create_page
from notion_client import Client
from typing import List, Dict

import json

JOB_SETTINGS_CLASS = NotionRSSSettings

def run(config: NotionRSSSettings = None, payload: dict = None):
  # In some cases where payload is required
  # We could validate here and raise an error

  notion = Client(auth=config.defaults.notion_token)

  links: List[FeedSource] = get_links(
    notion=notion,
    database_id=config.defaults.origin_database_id,
    url_property=config.defaults.origin_url_title,
    status_property=config.defaults.origin_status_title,
    subscribed_value=config.defaults.origin_status_subscribed
  )

  pages: List[FeedView] = []
  for link in links:
    pages.extend(generate_feeds(
      feed_source=link,
      default_status=config.defaults.view_status_not_read
    ))

  feed_references: Dict[str, FeedReference] = get_feed_references(
    notion=notion,
    database_id=config.defaults.view_database_id,
    id_property=config.defaults.view_id_title,
    hash_property=config.defaults.view_hash_title
  )

  update_pages: List[UpdateFeed] = []

  for page in pages:
    if page.id in feed_references:
      if page.hash != feed_references[page.id].hash:
        page_id = feed_references[page.id].page_id
        update_pages.append(UpdateFeed.model_construct(page_id=page_id, page=page))
      else:
        continue
    else:
      page_id = create_page(
        notion=notion,
        database_id=config.defaults.view_database_id,
        feed_view=page,
        title_placeholder=config.defaults.view_name_title,
        description_placeholder=config.defaults.view_description_title,
        status_placeholder=config.defaults.view_status_title,
        pub_date_placeholder=config.defaults.view_pub_date_title,
        feed_id_placeholder=config.defaults.view_id_title,
        source_placeholder=config.defaults.view_source_title,
        hash_placeholder=config.defaults.view_hash_title,
        href_placeholder=config.defaults.view_href_title
      )
      # Fail silently
      try:
        update_page_content(
          notion=notion,
          page_id=page_id,
          feed_view=page,
          status_placeholder=config.defaults.view_status_title,
          hash_placeholder=config.defaults.view_hash_title,
          default_status=config.defaults.view_status_not_read
        )
        print(f"Created '{page.name}' in Notion")
      except Exception as e:
        print(f"Failed to create '{page.name}' in Notion: {e}")
        continue

  # Deleting existing blocks takes an awfully long time
  # So I decided to create new feeds before updating old ones 
  for page in update_pages:
    try:
      update_page_content(
        notion=notion,
        page_id=page.page_id,
        feed_view=page.page,
        status_placeholder=config.defaults.view_status_title,
        hash_placeholder=config.defaults.view_hash_title,
        default_status=config.defaults.view_status_not_read
      )
      print(f"Updated '{page.page.name}' in Notion")
    except Exception as e:
      print(f"Failed to update '{page.page.name}' in Notion: {e}")
      continue

# TODO: Check out other implementations of markdown to notion for inspiration
# e.g:
# https://github.com/tryfabric/martian?tab=readme-ov-file#working-with-blockquotes
