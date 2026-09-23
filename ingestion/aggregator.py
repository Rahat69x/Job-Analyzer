import logging
from typing import List, Optional, Dict, Any

from core.models import NormalizedJob
from core.deduplicator import deduplicate_jobs
from ingestion.base_connector import BaseJobConnector
from ingestion.bdjobs_client import BDJobsClient
from ingestion.public_portals import fetch_sample_partner_jobs
from ingestion.global_connectors import (
    RemoteOKConnector, WeWorkRemotelyConnector, IndeedGlobalConnector, CompanyDirectConnector
)

logger = logging.getLogger(__name__)

bdjobs_client = BDJobsClient()

class GlobalJobAggregator:
    def __init__(self):
        self.connectors: List[BaseJobConnector] = [
            RemoteOKConnector(),
            WeWorkRemotelyConnector(),
            IndeedGlobalConnector(),
            CompanyDirectConnector()
        ]

    def register_connector(self, connector: BaseJobConnector):
        """Allow dynamically adding new job sources at runtime."""
        self.connectors.append(connector)

    def fetch_all(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        remote_only: bool = False,
        include_bdjobs: bool = True,
        category_id: int = 8,
        limit_per_source: int = 20
    ) -> List[NormalizedJob]:
        all_jobs: List[NormalizedJob] = []

        # 1. Ingest Bangladesh specific sources when requested or country matches
        if include_bdjobs and (not country or country.lower() in ["bangladesh", "worldwide", "all"]):
            try:
                bd_jobs = bdjobs_client.fetch_jobs_by_category(category_id, page=1, rpp=limit_per_source)
                for j in bd_jobs:
                    j.country = "Bangladesh"
                    j.city = "Dhaka"
                all_jobs.extend(bd_jobs)
            except Exception as e:
                logger.warning(f"Could not fetch live BDJobs: {e}")

            # Partner portals (Skill.jobs, Chakri)
            try:
                partner_jobs = fetch_sample_partner_jobs(category_id, "IT/Telecommunication")
                all_jobs.extend(partner_jobs)
            except Exception as e:
                logger.warning(f"Could not fetch partner jobs: {e}")

        # 2. Ingest all registered global connectors
        for connector in self.connectors:
            try:
                c_jobs = connector.fetch_jobs(
                    query=query, 
                    country=country, 
                    remote_only=remote_only, 
                    limit=limit_per_source
                )
                all_jobs.extend(c_jobs)
            except Exception as e:
                logger.warning(f"Connector {connector.name} failed: {e}")

        # 3. Apply cross-portal deduplication
        deduped = deduplicate_jobs(all_jobs)

        # 4. Optional filtering
        if remote_only:
            deduped = [j for j in deduped if j.workplace_type == "Remote"]
            
        if country and country.lower() not in ["all", "worldwide", "any"]:
            deduped = [j for j in deduped if j.country.lower() == country.lower() or (j.workplace_type == "Remote" and j.remote_eligibility.policy == "Worldwide")]

        return deduped

global_aggregator = GlobalJobAggregator()
