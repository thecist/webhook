from enum import Enum
from pydantic import Field, BaseModel, field_validator, field_serializer
from typing import List, Optional, Dict
from datetime import datetime
from dateutil import parser as dateutil_parser

# TODO: Add docstrings and module strings in all files

NOTION_LANGUAGES_LIST = [
  "abc",
  "abap",
  "agda",
  "arduino",
  "ascii art",
  "assembly",
  "bash",
  "basic",
  "bnf",
  "c",
  "c#",
  "c++",
  "clojure",
  "coffeescript",
  "coq",
  "css",
  "dart",
  "dhall",
  "diff",
  "docker",
  "ebnf",
  "elixir",
  "elm",
  "erlang",
  "f#",
  "flow",
  "fortran",
  "gherkin",
  "glsl",
  "go",
  "graphql",
  "groovy",
  "haskell",
  "hcl",
  "html",
  "idris",
  "java",
  "javascript",
  "json",
  "julia",
  "kotlin",
  "latex",
  "less",
  "lisp",
  "livescript",
  "llvm ir",
  "lua",
  "makefile",
  "markdown",
  "markup",
  "matlab",
  "mathematica",
  "mermaid",
  "nix",
  "notion formula",
  "objective-c",
  "ocaml",
  "pascal",
  "perl",
  "php",
  "plain text",
  "powershell",
  "prolog",
  "protobuf",
  "purescript",
  "python",
  "r",
  "racket",
  "reason",
  "ruby",
  "rust",
  "sass",
  "scala",
  "scheme",
  "scss",
  "shell",
  "smalltalk",
  "solidity",
  "sql",
  "swift",
  "toml",
  "typescript",
  "vb.net",
  "verilog",
  "vhdl",
  "visual basic",
  "webassembly",
  "xml",
  "yaml",
  "java/c/c++/c#",
  "notionscript"
]

def safe(name: str) -> str:
  return (
    name.upper()
    .replace("++", "_PLUSPLUS_")
    .replace("+", "_PLUS_")
    .replace("#", "_SHARP_")
    .replace(".", "_DOT_")
    .replace("-", "_DASH_")
    .replace("/", "_SLASH_")
    .replace(" ", "_")
  )

CanonicalNotionLanguage = Enum(
  "CanonicalNotionLanguage",
  {safe(name): name for name in NOTION_LANGUAGES_LIST}
)

ALIAS_MAP = {
  "ps1": CanonicalNotionLanguage.POWERSHELL,
  "pwsh": CanonicalNotionLanguage.POWERSHELL,
  "sh": CanonicalNotionLanguage.BASH,
  "js": CanonicalNotionLanguage.JAVASCRIPT,
  "ts": CanonicalNotionLanguage.TYPESCRIPT,
  "py": CanonicalNotionLanguage.PYTHON,
  "notion": CanonicalNotionLanguage.NOTION_FORMULA
}

merged_map = {
  member.name: member.value  # keep all canonical members
  for member in CanonicalNotionLanguage
}


for alias, canonical_enum in ALIAS_MAP.items():
  key = safe(alias)
  if key in merged_map:
    continue
  merged_map[key] = canonical_enum.value

NotionLanguageEnum = Enum("NotionLanguageEnum", merged_map)

class NotionLanguage:
  _enum = NotionLanguageEnum

  @classmethod
  def get(cls, key: str) -> NotionLanguageEnum:
    try:
      return cls._enum[safe(key)]
    except KeyError:
      return cls._enum["PLAIN_TEXT"]
  
  def __getattribute__(self, name):
    return getattr(self._enum, name)

class FeedSource(BaseModel):
  id: str = Field(..., description="The unique identifier for the source")
  url: str = Field(..., description="The URL of the source")

class FeedReference(BaseModel):
  hash: str = Field(..., description="The URL of the source")
  page_id: str = Field(..., description="The unique identifier for the source")

class FeedView(BaseModel):
  name: str = Field(..., description="The name of the feed")
  description: str = Field(..., description="A brief description of the feed")
  status: str = Field(..., description="The read status of the feed")
  pub_date: Optional[datetime] = Field(None, description="The publication date of the feed")
  id: str = Field(..., description="The unique identifier for the feed")
  source: str = Field(..., description="The identifier for the source of the feed")
  hash: Optional[str] = Field(None, description="A hash representing the content of the feed")
  href: Optional[str] = Field(None, description="The permalink to the feed in Notion")
  blocks: List[Dict] = Field(default_factory=list, description="The content blocks of the feed in Notion format")

  @field_validator('pub_date', mode='before')
  def parse_pub_date(cls, value):
    if isinstance(value, str):
      try:
        return dateutil_parser.parse(value)
      except Exception:
        raise ValueError(f"Invalid date format: {value}")
    return value

class FeedContent(BaseModel):
  type: str = Field("text/plain", description="The MIME type of the content")
  value: Optional[str] = Field(None, description="The content value in the specified MIME type")

class UpdateFeed(BaseModel):
  page_id: str = Field(..., description="The unique identifier for the feed page")
  page: FeedView = Field(..., description="The metadata for the feed page")
