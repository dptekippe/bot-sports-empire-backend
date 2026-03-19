"""
Retention Job for MEMO-pgvector
================================
Background job that runs after each MEMO generation to:
1. Execute the reflection pipeline on new trajectories
2. Commit insights using semantic CRUD operations
3. Clean up deprecated/contradicted insights
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RetentionJob:
    """
    Runs retention/cleanup operations on the MEMO memory bank.
    
    Typical schedule: run after each MEMO optimization generation
    (e.g., via cron every 30 minutes, or triggered by generation completion)
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def run(self, older_than_days: int = 30) -> dict:
        """
        Run all retention operations.
        
        Args:
            older_than_days: Delete insight_embeddings older than this (default 30)
            
        Returns:
            dict with counts of operations performed
        """
        results = {
            "reflections_processed": 0,
            "insights_added": 0,
            "insights_deduplicated": 0,
            "insights_deprecated": 0,
            "embeddings_cleaned": 0,
            "errors": [],
        }
        
        try:
            # 1. Process unreflected trajectories
            results["reflections_processed"] = self._process_unreflected()
            
            # 2. Clean old embeddings (optional - soft delete is preferred)
            results["embeddings_cleaned"] = self._cleanup_old_embeddings(older_than_days)
            
            logger.info(f"Retention job completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Retention job failed: {e}")
            results["errors"].append(str(e))
            return results
    
    def _process_unreflected(self) -> int:
        """
        Find trajectories that haven't been reflected on yet,
        run reflection, and commit insights.
        """
        from api.memo_crud import reflect_on_trajectory
        
        # Find trajectories without insights
        count = 0
        # TODO: Implement actual query to find unreflected trajectories
        # For now, return 0
        return count
    
    def _cleanup_old_embeddings(self, older_than_days: int) -> int:
        """
        Remove embedding records for insights that are old and deprecated.
        Only removes if insight status is 'deprecated' or 'contradicted'.
        """
        # TODO: Implement with proper SQLAlchemy query
        # DELETE FROM insight_embeddings 
        # WHERE insight_id IN (
        #   SELECT id FROM insights 
        #   WHERE status IN ('deprecated', 'contradicted')
        #   AND updated_at < NOW() - INTERVAL '30 days'
        # )
        return 0


def run_retention_job(
    db_url: str,
    older_than_days: int = 30,
    log_level: str = "INFO"
) -> dict:
    """
    Convenience function to run retention job from command line.
    
    Usage:
        python -m integration.retention_job --db-url postgresql://... --older-than-days 30
    """
    import argparse
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    parser = argparse.ArgumentParser(description="MEMO-pgvector Retention Job")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--older-than-days", type=int, default=30)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    engine = create_engine(args.db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        job = RetentionJob(session)
        results = job.run(older_than_days=args.older_than_days)
        return results
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
    else:
        print("Usage: python -m integration.retention_job --db-url postgresql://...")
