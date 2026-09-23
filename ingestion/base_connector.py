from abc import ABC, abstractmethod
from typing import List, Optional
from core.models import NormalizedJob

class BaseJobConnector(ABC):
    """Abstract base class for modular, plug-and-play job platform connectors."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the job source / platform."""
        pass
        
    @property
    @abstractmethod
    def is_global(self) -> bool:
        """True if the platform has global / multi-country reach."""
        pass

    @abstractmethod
    def fetch_jobs(
        self, 
        query: Optional[str] = None, 
        country: Optional[str] = None, 
        remote_only: bool = False,
        limit: int = 50
    ) -> List[NormalizedJob]:
        """Fetch and normalize jobs from this source."""
        pass

    def health_check(self) -> bool:
        """Verify connector connectivity and availability."""
        return True
