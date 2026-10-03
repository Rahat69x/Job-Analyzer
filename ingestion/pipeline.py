"""
Global Job Ingestion & Discovery Pipeline
Orchestrates live retrieval across registered global boards, remote platforms,
and ATS endpoints (Greenhouse, Lever, Ashby, SmartRecruiters).
Performs validation, deduplication, SQLite indexing, and live health status updates.
Strictly excludes Bangladesh sources (Bdjobs) from worldwide results.
"""

import logging
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Any

from core.models import NormalizedJob
from core.db import upsert_jobs, init_db, get_connection
from core.deduplicator import deduplicate_jobs
from core.source_registry import source_registry, SourceMetadata
from ingestion.shared_connectors import (
    ArbeitnowConnector, RemotiveConnector, JobicyConnector, WWRRssConnector,
    GreenhouseConnector, LeverConnector, AshbyConnector, SmartRecruitersConnector
)

logger = logging.getLogger(__name__)

class JobIngestionPipeline:
    """
    Production-grade scalable job ingestion engine.
    Fetches real live data from genuine international endpoints,
    updates source health metrics in real-time, and indexes into SQLite.
    """

    def __init__(self):
        init_db()

    def _get_connector_for_source(self, src: SourceMetadata):
        """Factory returning the appropriate shared connector for a registered source."""
        parser = src.parser.lower()

        if parser == "arbeitnow":
            return ArbeitnowConnector()
        elif parser == "remotive":
            return RemotiveConnector()
        elif parser == "jobicy":
            return JobicyConnector()
        elif parser == "wwr_rss":
            return WWRRssConnector(src.endpoint, src.name)
        elif parser == "greenhouse" and src.company_slug:
            return GreenhouseConnector(src.company_slug, src.name.replace(" Careers", "").replace(" (Greenhouse)", ""), src.company_tier or "MNC")
        elif parser == "lever" and src.company_slug:
            return LeverConnector(src.company_slug, src.name.replace(" Careers", "").replace(" (Lever)", ""), src.company_tier or "MNC")
        elif parser == "ashby" and src.company_slug:
            return AshbyConnector(src.company_slug, src.name.replace(" Careers", "").replace(" (Ashby)", ""), src.company_tier or "Corporate")
        elif parser == "smartrecruiters" and src.company_slug:
            return SmartRecruitersConnector(src.company_slug, src.name.replace(" Global Postings", "").replace(" (SmartRecruiters)", ""), src.company_tier or "Corporate")
        return None

    def _fetch_single_source(self, src: SourceMetadata, limit_per_source: int = 50) -> Any:
        """Worker task executing fetch for a single registered source."""
        connector = self._get_connector_for_source(src)
        if not connector:
            # Source not directly fetchable via automated public API (e.g. manual/workday/bdjobs)
            return src.id, [], "UNAVAILABLE", 0, 404, "No public API adapter available"

        start_time = time.time()
        try:
            jobs = connector.fetch_jobs(limit=limit_per_source)
            duration = time.time() - start_time
            if jobs:
                return src.id, jobs, "ACTIVE", len(jobs), 200, None
            else:
                return src.id, [], "UNAVAILABLE", 0, 204, "Endpoint returned 0 postings"
        except Exception as e:
            return src.id, [], "ERROR", 0, 500, str(e)

    def run_pipeline(
        self,
        target_source_ids: Optional[List[str]] = None,
        limit_per_source: int = 60,
        max_workers: int = 8
    ) -> Dict[str, Any]:
        """
        Executes concurrent discovery pipeline across registered sources.
        Validates, deduplicates, and stores real live postings.
        """
        all_sources = source_registry.get_all_sources()
        if target_source_ids:
            sources_to_run = [s for s in all_sources if s.id in target_source_ids and s.enabled]
        else:
            # Exclude Bangladesh-only sources from global pipeline runs
            sources_to_run = [s for s in all_sources if s.enabled and s.category != "Bangladesh Sources"]

        total_sources = len(sources_to_run)
        logger.info(f"Starting global ingestion pipeline across {total_sources} registered sources...")
        start_time = time.time()

        all_raw_jobs: List[NormalizedJob] = []
        active_count = 0
        unavailable_count = 0
        error_count = 0

        # Concurrent ingestion execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {
                executor.submit(self._fetch_single_source, src, limit_per_source): src
                for src in sources_to_run
            }

            for future in as_completed(future_to_source):
                src = future_to_source[future]
                try:
                    src_id, jobs, status, count, http_code, err_msg = future.result()
                    
                    if status == "ACTIVE":
                        active_count += 1
                        all_raw_jobs.extend(jobs)
                        source_registry.update_source_status(
                            source_id=src_id,
                            status="ACTIVE",
                            jobs_found=count,
                            jobs_deduped=count,
                            http_status=http_code
                        )
                    elif status == "PARTIAL":
                        active_count += 1
                        all_raw_jobs.extend(jobs)
                        source_registry.update_source_status(
                            source_id=src_id,
                            status="PARTIAL",
                            jobs_found=count,
                            jobs_deduped=count,
                            http_status=http_code
                        )
                    elif status == "ERROR":
                        error_count += 1
                        source_registry.update_source_status(
                            source_id=src_id,
                            status="ERROR",
                            jobs_found=0,
                            http_status=http_code,
                            error_message=err_msg
                        )
                    else:
                        unavailable_count += 1
                        source_registry.update_source_status(
                            source_id=src_id,
                            status="UNAVAILABLE",
                            jobs_found=0,
                            http_status=http_code,
                            error_message=err_msg
                        )
                except Exception as ex:
                    error_count += 1
                    source_registry.update_source_status(
                        source_id=src.id,
                        status="ERROR",
                        jobs_found=0,
                        http_status=500,
                        error_message=str(ex)
                    )

        # Deduplication Step
        deduped_jobs = deduplicate_jobs(all_raw_jobs)
        duplicates_removed = len(all_raw_jobs) - len(deduped_jobs)

        # Upsert into SQLite
        if deduped_jobs:
            upsert_jobs(deduped_jobs)

        # Persist updated health metrics
        source_registry.save_state()

        elapsed = round(time.time() - start_time, 2)
        summary = {
            "sources_attempted": total_sources,
            "sources_active": active_count,
            "sources_unavailable": unavailable_count,
            "sources_error": error_count,
            "total_raw_jobs": len(all_raw_jobs),
            "total_deduped_jobs": len(deduped_jobs),
            "duplicates_removed": duplicates_removed,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Ingestion pipeline completed: {summary}")
        return summary

# Tuple type helper
Tuple_Result = Any

# Global Pipeline Singleton
ingestion_pipeline = JobIngestionPipeline()
