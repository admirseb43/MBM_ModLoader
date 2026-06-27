from dataclasses import dataclass


@dataclass
class ModDescriptor:
    name: str
    theme: str
    url_repo: str
    short_description: str
    author: str
    file_name: str
