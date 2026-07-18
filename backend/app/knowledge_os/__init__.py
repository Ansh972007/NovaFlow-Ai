"""
NovaFlow Enterprise Knowledge Operating System (KOS).

Permanent enterprise knowledge layer — all AI retrieval flows through this platform.
"""

from app.knowledge_os.retrieval import cross_collection_search, enterprise_retrieve
from app.knowledge_os.search import enterprise_search
from app.knowledge_os.service import (
    create_collection,
    get_collection,
    list_collections,
)

__all__ = [
    "create_collection",
    "get_collection",
    "list_collections",
    "enterprise_retrieve",
    "enterprise_search",
    "cross_collection_search",
]
