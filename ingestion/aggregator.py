import logging
from typing import List, Optional, Dict, Any

from core.models import NormalizedJob
from core.deduplicator import deduplicate_jobs
from ingestion.base_connector import BaseJobConnector
from ingestion.bdjobs_client import BDJobsClient
from ingestion.public_portals import fetch_sample_partner_jobs, fetch_all_partner_jobs
from ingestion.global_connectors import (
    RemoteOKConnector, WeWorkRemotelyConnector, IndeedGlobalConnector, CompanyDirectConnector,
    CuratedCompaniesConnector
)

logger = logging.getLogger(__name__)

bdjobs_client = BDJobsClient()

class GlobalJobAggregator:
    def __init__(self):
        self.connectors: List[BaseJobConnector] = [
            RemoteOKConnector(),
            WeWorkRemotelyConnector(),
            IndeedGlobalConnector(),
            CompanyDirectConnector(),
            CuratedCompaniesConnector()
        ]
        self.source_health: Dict[str, Dict[str, Any]] = {
            "BDJobs": {"status": "online", "message": "Live API feed active"},
            "CompanyCareerPage": {"status": "online", "message": "Direct career pages & curated companies active"},
            "Indeed": {"status": "online", "message": "Global multi-country connector active"},
            "Remote OK": {"status": "online", "message": "Worldwide remote feed active"},
            "We Work Remotely": {"status": "online", "message": "Global engineering feed active"},
            "Skill.jobs": {"status": "online", "message": "Partner portal active"},
            "Chakri": {"status": "online", "message": "Partner portal active"}
        }
        self.unavailable_sources: List[Dict[str, str]] = []

    def register_connector(self, connector: BaseJobConnector):
        """Allow dynamically adding new job sources at runtime."""
        self.connectors.append(connector)

    def get_source_health(self) -> Dict[str, Dict[str, Any]]:
        return self.source_health

    def get_unavailable_sources(self) -> List[Dict[str, str]]:
        return self.unavailable_sources

    def fetch_all(
        self,
        query: Optional[str] = None,
        country: Optional[str] = None,
        remote_only: bool = False,
        include_bdjobs: bool = True,
        category_id: Optional[int] = None,
        limit_per_source: int = 50
    ) -> List[NormalizedJob]:
        all_jobs: List[NormalizedJob] = []
        self.unavailable_sources = []

        # 1. Ingest Bangladesh specific sources when requested or country matches
        if include_bdjobs and (not country or country.lower() in ["bangladesh", "worldwide", "all"]):
            # Live BDJobs
            try:
                if category_id:
                    bd_jobs = bdjobs_client.fetch_jobs_by_category(category_id, page=1, rpp=limit_per_source)
                else:
                    # Ingest across key primary categories when no specific category is filtered
                    popular_categories = [8, 1, 9, 11, 4, 18, 5, 63]
                    bd_jobs = []
                    for cat in popular_categories[:4]:
                        try:
                            jobs_for_cat = bdjobs_client.fetch_jobs_by_category(cat, page=1, rpp=20)
                            bd_jobs.extend(jobs_for_cat)
                        except Exception:
                            pass

                for j in bd_jobs:
                    j.country = "Bangladesh"
                    j.city = "Dhaka"
                all_jobs.extend(bd_jobs)
                self.source_health["BDJobs"] = {"status": "online", "message": f"Fetched {len(bd_jobs)} live openings"}
            except Exception as e:
                logger.warning(f"Could not fetch live BDJobs: {e}")
                self.source_health["BDJobs"] = {"status": "unavailable", "message": str(e)}
                self.unavailable_sources.append({"source": "BDJobs", "reason": f"Feed temporarily slow or unreachable ({e})"})

            # Partner portals (Skill.jobs, Chakri)
            try:
                if category_id:
                    partner_jobs = fetch_sample_partner_jobs(category_id, "Industry Sector")
                else:
                    partner_jobs = fetch_all_partner_jobs()
                all_jobs.extend(partner_jobs)
                self.source_health["Skill.jobs"] = {"status": "online", "message": "Partner catalog active"}
                self.source_health["Chakri"] = {"status": "online", "message": "Partner catalog active"}
            except Exception as e:
                logger.warning(f"Could not fetch partner jobs: {e}")
                self.source_health["Skill.jobs"] = {"status": "unavailable", "message": str(e)}
                self.source_health["Chakri"] = {"status": "unavailable", "message": str(e)}
                self.unavailable_sources.append({"source": "Partner Portals (Skill.jobs/Chakri)", "reason": str(e)})

        # 2. Ingest all registered global connectors
        for connector in self.connectors:
            try:
                c_jobs = connector.fetch_jobs(
                    query=query, 
                    country=country, 
                    remote_only=remote_only, 
                    limit=limit_per_source
                )
                if category_id:
                    c_jobs = [j for j in c_jobs if j.category_id == category_id]

                all_jobs.extend(c_jobs)
                self.source_health[connector.name] = {"status": "online", "message": f"Connected ({len(c_jobs)} jobs evaluated)"}
            except Exception as e:
                logger.warning(f"Connector {connector.name} failed: {e}")
                self.source_health[connector.name] = {"status": "unavailable", "message": str(e)}
                self.unavailable_sources.append({"source": connector.name, "reason": f"Feed temporarily unavailable ({e})"})

        # 3. Apply cross-portal deduplication
        deduped = deduplicate_jobs(all_jobs)

        # 4. Optional filtering
        if remote_only:
            deduped = [j for j in deduped if j.workplace_type == "Remote"]
            
        if country and country.lower() not in ["all", "worldwide", "any"]:
            deduped = [j for j in deduped if j.country.lower() == country.lower() or (j.workplace_type == "Remote" and j.remote_eligibility.policy == "Worldwide")]

        return deduped

global_aggregator = GlobalJobAggregator()

