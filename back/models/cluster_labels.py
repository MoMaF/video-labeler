from typing import List, Optional
from pydantic import BaseModel

class ImageData(BaseModel):
    url: str
    approved: bool

class ClusterLabels(BaseModel):
    """Model for validating post requests that assign labels to clusters and images.
    """
    label: Optional[int]
    images: List[ImageData]
