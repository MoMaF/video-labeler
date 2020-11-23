from typing import List, Optional
from pydantic import BaseModel

class ImageData(BaseModel):
    url: str
    status: str  # 'same', 'different', 'invalid'

class ClusterLabels(BaseModel):
    """Model for validating post requests that assign labels to clusters and images.
    """
    label: Optional[int]
    images: List[ImageData]
    time: int
    status: str  # 'labeled', 'discarded', 'postponed', 'mixed'
