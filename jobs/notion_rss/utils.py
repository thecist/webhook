from bs4.element import Tag
from feedparser import parse as feedparse, FeedParserDict
from hashlib import md5
from html_to_markdown import convert_to_markdown
from mistune import create_markdown
from .models import FeedContent, FeedReference, FeedSource, FeedView, NotionLanguage
from notion_client import Client
from typing import List, Dict

# TODO: Look into creating github workflows for your webhooks too
# Make it opt in automation - research about that

# TODO: Check if there's a way to lock notion pages

def get_links(notion: Client, database_id: str, url_property: str, status_property: str, subscribed_value: str) -> List[FeedSource]:
  """
  Fetches all links from a Notion database.
  
  Args:
    notion: The Notion client instance.
    url_property: The property name in the Notion database that contains the URLs.
    database_id: The ID of the Notion database to query.
      
  Returns:
    A list of sources(Sourc) containing the page ID and URL for each link.
  """
  response = notion.databases.query(database_id=database_id)
  links = []
  
  for page in response['results']:
    is_subscribed = (
      page.get('properties', {})
      .get(status_property, {})
      .get("select", {})
      .get("name") == subscribed_value
    )

    if is_subscribed and isinstance(page.get('properties', {}).get(url_property, {}).get("url"), str):
      links.append(FeedSource(
        id=page["id"],
        url=page["properties"][url_property]["url"]
      ))
  
  return links

def get_feed_references(notion: Client, database_id: str, id_property: str, hash_property: str) -> Dict[str, FeedReference]:
  """
  Fetches all feeds from a Notion database.
  
  Args:
    notion: The Notion client instance.
    database_id: The ID of the Notion database to query.
    id_property: The property name in the Notion database that contains the feed ID.
    hash_property: The property name in the Notion database that contains the feed hash.
      
  Returns:
    A dictionary mapping feed IDs to their corresponding FeedReference objects.
  """
  response = notion.databases.query(database_id=database_id)
  feeds: Dict[str, FeedReference] = {}
  
  for page in response['results']:
    page_id = page['id']
    if id_property in page.get('properties', {}) and page['properties'][id_property]['rich_text'] and len(page['properties'][id_property]['rich_text']) > 0:
      feed_id = page['properties'][id_property]['rich_text'][0]['text']['content']
      
      if hash_property in page.get('properties', {}) and page['properties'][hash_property]['rich_text'] and len(page['properties'][hash_property]['rich_text']) > 0:
        feed_hash = page['properties'][hash_property]['rich_text'][0]['text']['content']
      else:
        feed_hash = ""
      
      feeds[feed_id] = FeedReference(
        hash=feed_hash,
        page_id=page_id
      )
  return feeds

# TODO: Check the rate limit(len) of each block to ensure you don't get errors
# when uploading to notion

# Legacy, will delete in the future
def _generate_block(line: str) -> Dict:
  block = {
    "object": "block",
    "type": "paragraph",
    "paragraph": {
      "rich_text": [{"type": "text", "text": {"content": line}}]
    }
  }
  return block


def generate_blocks(feed_content: FeedContent) -> List[Dict]:
  if feed_content.value is None:
    return []
  content = feed_content.value
  if feed_content.type == "text/html" and len(content) > 0:
    content = convert_to_markdown(content, code_language_callback=_detect_lang)

  ast_parser = create_markdown(renderer="ast")
  ast = ast_parser(content)

  if isinstance(ast, str):
    return [_generate_block(line.strip()) for line in content.splitlines()]
  else:
    return walk(ast)


def generate_feeds(feed_source: FeedSource, default_status: str) -> List[FeedView]:
  feed_views: List[FeedView] = []
  mime_type_rank = {
    "text/markdown": 1,
    "text/html": 2,
    "text/plain": 3,
  }

  feed: FeedParserDict = feedparse(feed_source.url)

  if feed.bozo:
    # TODO: Use logging instead of print
    print("Error parsing feed:", feed.bozo_exception)
    return []


  content_list = []
  # Print entries
  if feed.entries and isinstance(feed.entries, list):
    for entry in feed.entries:
      name = entry["title"] or "No Title"
      description = entry["description"] or "No Description"
      status = default_status
      pub_date = entry["published"]
      href = entry["link"] or entry["url"] or entry["permalink"]
      id = entry["id"] or href
      source = feed_source.id
      hash = None
      blocks = []

      content: FeedContent = FeedContent()
      for feed_content in entry.get("content", []):
        type = feed_content["type"]
        value = feed_content["value"]
        if content.type is None or mime_type_rank[type] < mime_type_rank[content.type]:
          content.type = type
          content.value = value
      if content.value is not None:
        hash = md5(content.value.encode('utf-8')).hexdigest()
        content_list.append(convert_to_markdown(content.value, code_language_callback=_detect_lang))
      else:
        hash = "No Content"

      blocks = generate_blocks(content)

      feed_view = FeedView(
        name=name,
        description=description,
        status=status,
        pub_date=pub_date,
        id=id,
        source=source,
        hash=hash,
        href=href,
        blocks=blocks
      )

      feed_views.append(feed_view)
  return feed_views

def _clear_page_content(notion: Client, page_id: str) -> None:
  blocks = []
  has_more = True
  next_cursor = None
  while has_more:
    if next_cursor:
      response = notion.blocks.children.list(block_id=page_id, start_cursor=next_cursor)
    else:
      response = notion.blocks.children.list(block_id=page_id)
    blocks.extend(response["results"])
    has_more = response["has_more"]
    next_cursor = response["next_cursor"]

  # Takes a long time deleting sequentially, but deleting in parallel returns
  # a 409 error, and using backoff retries miss some blocks or end up slower
  # than sequentially
  for block in blocks:
    block_id = block["id"]
    notion.blocks.delete(block_id=block_id)

def create_page(notion: Client, database_id: str, feed_view: FeedView, title_placeholder: str, description_placeholder: str, status_placeholder: str, pub_date_placeholder: str, feed_id_placeholder: str, source_placeholder: str, hash_placeholder: str, href_placeholder: str) -> str:
  properties = {}
  properties[title_placeholder] = {
    "title": [{"text": {"content": feed_view.name}}]
  }
  properties[description_placeholder] = {
    "rich_text": [{"text": {"content": feed_view.description}}]
  }
  properties[status_placeholder] = {
    "status": {"name": feed_view.status}
  }
  properties[feed_id_placeholder] = {
    "rich_text": [{"text": {"content": feed_view.id}}]
  }
  properties[source_placeholder] = {
    "relation": [{"id": feed_view.source}]
  }
  if feed_view.pub_date:
    properties[pub_date_placeholder] = {
      "date": {"start": feed_view.pub_date.isoformat()}
    }
  if feed_view.hash:
    properties[hash_placeholder] = {
      "rich_text": [{"text": {"content": feed_view.hash}}]
    }
  if feed_view.href:
    properties[href_placeholder] = {
      "url": feed_view.href
    }
  
  new_page = notion.pages.create(
    parent={"database_id": database_id},
    properties=properties
  )
  return new_page["id"]

def update_page_content(notion: Client, page_id: str, feed_view: FeedView, status_placeholder: str, hash_placeholder: str, default_status: str) -> None:
  _clear_page_content(notion=notion, page_id=page_id)
  for i in range(0, len(feed_view.blocks), 100):
    # Notion rate limits block creation -> 100/rq
    notion.blocks.children.append(block_id=page_id, children=feed_view.blocks[i:i+100])
  notion.pages.update(page_id=page_id,
    properties={
      status_placeholder: {
        "status": {
          "name": default_status
        }
      },
      hash_placeholder: {
        "rich_text": [
          {
            "text": {
              "content": feed_view.hash
            }
          }
        ]
      }
    }
  )





# Brace your britches, shit is about to go down

# Felt right to keep it here
def _detect_lang(tag: Tag) -> str | None:
  """
  Detects the programming language of a code block in HTML.
  
  Args:
    tag: The HTML tag containing the code block.
    
  Returns:
    The programming language of the code block, or None if not detected.
  """
  # TODO: Iterate through nested tags for language metadata, some flavors don't
  # keep the language in the top level or code block
  # Reference: https://mdxjs.com/guides/syntax-highlighting/#syntax-highlighting-at-run-time

  # Check top level tag for language
  # Github Flavor
  for cls in tag.get("class", []):
    if cls.startswith(("language-", "lang-")):
      language = cls.split("-", 1)[1]
      return NotionLanguage.get(language).value
  # Astro Flavor
  data_lang = tag.get("data-language")
  if data_lang:
    language = data_lang.strip().lower()
    return NotionLanguage.get(language).value
  
  # If not, find a nested code tag and do the same
  code_tag = tag.find("code")
  if code_tag:
    for cls in code_tag.get("class", []):
      if cls.startswith(("language-", "lang-")):
        language = cls.split("-", 1)[1]
        return NotionLanguage.get(language).value
    
    data_lang = code_tag.get("data-language")
    if data_lang:
      language = data_lang.strip().lower()
      return NotionLanguage.get(language).value
  return None

# Notion has a limit of 2000 characters for each rich_text block
# Error: notion_client.errors.APIResponseError: body failed validation:... should be ≤ `2000`, instead was `2422`.
def _rate_limit_rich_txt(rich_texts: list[dict]) -> list[dict]:
  rated_rich_texts = []
  for rich_text in rich_texts:
    
    if "text" in rich_text and len(rich_text["text"]["content"]) > 2000:
      for i in range(0, len(rich_text["text"]["content"]), 2000):
        rated_rich_texts.append({"type": "text", "text": {"content": rich_text["text"]["content"][i:i+2000]}})
    else:
      rated_rich_texts.append(rich_text)

  return rated_rich_texts

def _txt(content:str, annotations:Dict=None)->Dict:
  return {
    "type":"text",
    "text":{"content":content},
    "annotations": annotations or {
      "bold":False,"italic":False,"strikethrough":False,
      "underline":False,"code":False,"color":"default"
    }
  }

def _create_rich_block(blocks: list[dict], block_type:str, rich_text:List[Dict]):
  rich_text = _rate_limit_rich_txt(rich_text)
  # mistune creates images as inline blocks instead of top level blocks
  # So I have parse through it to get the images out
  rich_text_chunk = []
  for block in rich_text:
    if block.get("type") == "image":
      if len(rich_text_chunk) > 0:
        blocks.append({"object":"block", "type":block_type, block_type:{"rich_text":rich_text_chunk}})
        rich_text_chunk = []
      blocks.append(block)
    else:
      rich_text_chunk.append(block)
  if len(rich_text_chunk) > 0:
    blocks.append({"object":"block", "type":block_type, block_type:{"rich_text":rich_text_chunk}})
    rich_text_chunk = []

def _inline(children) -> List[Dict]:
  """Convert mistune inline nodes to Notion rich_text list."""
  rich:List[Dict] = []

  for node in children:
    node_type = node["type"]

    if node_type == "text":
      rich.append(_txt(node["raw"]))

    elif node_type == "strong": # **bold**
      for r in _inline(node["children"]):
        r["annotations"]["bold"] = True
        rich.append(r)

    elif node_type == "emphasis": # *italic*
      for r in _inline(node["children"]):
        r["annotations"]["italic"] = True
        rich.append(r)

    elif node_type == "codespan": # `code`
      rich.append(_txt(node["raw"], {"code":True}))

    elif node_type == "link": # [txt](url)
      link_children = _inline(node["children"])
      for r in link_children:
        r["text"]["link"] = {"url": node["attrs"]["url"]}
        rich.append(r)
    
    # Images are recognized as an inline property by mistune
    # Testing logic rn to make images block level
    elif node_type == "image": # ![alt](url)
      rich.append({
        "object":"block",
        "type":"image",
        "image":{
          "type":"external",
          "external":{"url": node["attrs"]["url"]},
          "caption": _inline(node["children"])
        }
      })
    
    elif node_type == "softbreak":
      # Looks weird with \n
      rich.append(_txt(" "))

    elif node_type == "blank_line":
      rich.append(_txt("\n\n"))

    else:
      for r in _inline(node.get("children", [])):
        rich.append(r)

  return rich

def _walk_blocks(nodes: list, blocks: list[dict], curr_list: list[str] = None) -> None:
  curr_list = curr_list or []

  for node in nodes:
    node_type = node["type"]

    if node_type == "heading": # # Heading
      level = node["attrs"]["level"]
      # Notion only supports up to 3 levels
      if level > 3:
        _create_rich_block(blocks, "paragraph", _inline(node["children"]))
      else:
        _create_rich_block(blocks, f"heading_{level}", _inline(node["children"]))

    elif node_type == "paragraph":
      _create_rich_block(blocks, "paragraph", _inline(node["children"]))

    elif node_type == "block_quote": # > Quote
      _create_rich_block(blocks, f"quote", _inline(node["children"]))

    elif node_type == "block_code": # ```javascript console.log("hello");
      blocks.append({
        "object":"block",
        "type": "code",
        "code": {
          "rich_text":_rate_limit_rich_txt([{"type": "text", "text": {"content": node["raw"]}}]),
          "language": node.get("attrs",{}).get("info", "plain text")
        }
      })

    # TODO: Check if mistune supports checkboxes -[]
    elif node_type == "list": # * List item
      item_type = "numbered_list_item" if node.get("ordered") else "bulleted_list_item"
      for li in node["children"]:
        li_text = _inline([c for c in li["children"] if c["type"]!="list"])
        _create_rich_block(blocks, item_type, li_text)
        # nested list inside list‑item?
        for sub in [c for c in li["children"] if c["type"]=="list"]:
          _walk_blocks(sub["children"], blocks, curr_list+[item_type])

    elif node_type == "thematic_break": # ---
      blocks.append({"object":"block","type":"divider","divider":{}})

    elif node_type == "blank_line":
      _create_rich_block(blocks, "paragraph", _inline([]))

    else:
      _create_rich_block(blocks, "paragraph", _inline(node.get("children", [])))

def walk(ast: list) -> list[dict]:
  blocks = []

  _walk_blocks(ast, blocks)

  return blocks
