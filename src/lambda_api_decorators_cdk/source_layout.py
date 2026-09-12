from enum import Enum


class SourceLayout(Enum):
    """The source boundary used to package discovered Lambda handlers."""

    ROOT = "root"
    SERVICE = "service"
