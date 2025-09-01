"""
Background metadata synchronization service

Handles async refresh of D365 metadata with intelligent scheduling and error handling.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
import structlog

from ...repositories.sqlite.database import Database
from ...client.d365_client import D365Client
from ...repositories.sqlite.bulk_parser import BulkMetadataParser

logger = structlog.get_logger(__name__)

class BackgroundMetadataSync:
    """Background service for metadata synchronization"""
    
    def __init__(
        self,
        db: Database,
        d365_client: D365Client,
        sync_interval_hours: int = 12,
        retry_interval_minutes: int = 30,
        max_retries: int = 3
    ):
        self.db = db
        self.client = d365_client
        self.sync_interval = timedelta(hours=sync_interval_hours)
        self.retry_interval = timedelta(minutes=retry_interval_minutes)
        self.max_retries = max_retries
        
        self._sync_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._sync_callbacks: list[Callable[[Dict[str, Any]], None]] = []
        
        # Sync state tracking
        self._last_sync_attempt: Optional[datetime] = None
        self._last_successful_sync: Optional[datetime] = None
        self._consecutive_failures = 0
        self._is_syncing = False
    
    def add_sync_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback to be notified when sync completes"""
        self._sync_callbacks.append(callback)
    
    def remove_sync_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove sync callback"""
        if callback in self._sync_callbacks:
            self._sync_callbacks.remove(callback)
    
    async def start_background_sync(self):
        """Start the background sync service"""
        if self._sync_task and not self._sync_task.done():
            logger.warning("Background sync already running")
            return
            
        logger.info("Starting background metadata sync service",
                   sync_interval_hours=self.sync_interval.total_seconds() / 3600,
                   retry_interval_minutes=self.retry_interval.total_seconds() / 60)
        
        self._shutdown_event.clear()
        self._sync_task = asyncio.create_task(self._sync_loop())
        
        # Trigger initial sync if needed
        if await self._should_sync_now():
            asyncio.create_task(self._trigger_sync())
    
    async def stop_background_sync(self):
        """Stop the background sync service"""
        logger.info("Stopping background metadata sync service")
        
        self._shutdown_event.set()
        
        if self._sync_task and not self._sync_task.done():
            try:
                await asyncio.wait_for(self._sync_task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Background sync task did not stop gracefully, cancelling")
                self._sync_task.cancel()
                try:
                    await self._sync_task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Background sync service stopped")
    
    async def force_sync_now(self) -> Dict[str, Any]:
        """Force an immediate metadata sync (foreground)"""
        logger.info("Forcing immediate metadata sync")
        return await self._perform_sync()
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics"""
        connection = await self.db.get_connection()
        
        # Get latest sync record
        cursor = connection.execute("""
            SELECT last_sync_at, last_sync_duration_ms, sync_status, 
                   entity_count, enum_count, error_message
            FROM metadata_sync
            ORDER BY last_sync_at DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        latest_sync = dict(row) if row else None
        
        # Calculate next sync time
        next_sync_time = None
        if self._last_successful_sync:
            next_sync_time = self._last_successful_sync + self.sync_interval
        elif self._last_sync_attempt and self._consecutive_failures > 0:
            next_sync_time = self._last_sync_attempt + self.retry_interval
        
        return {
            "service_status": "running" if self._sync_task and not self._sync_task.done() else "stopped",
            "is_syncing": self._is_syncing,
            "last_sync_attempt": self._last_sync_attempt.isoformat() if self._last_sync_attempt else None,
            "last_successful_sync": self._last_successful_sync.isoformat() if self._last_successful_sync else None,
            "consecutive_failures": self._consecutive_failures,
            "next_sync_time": next_sync_time.isoformat() if next_sync_time else None,
            "sync_interval_hours": self.sync_interval.total_seconds() / 3600,
            "latest_sync_record": latest_sync,
            "metadata_available": latest_sync is not None and latest_sync.get("sync_status") == "success"
        }
    
    async def _sync_loop(self):
        """Main background sync loop"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    if await self._should_sync_now():
                        await self._trigger_sync()
                    
                    # Sleep for a reasonable check interval (5 minutes)
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=300  # 5 minutes
                    )
                    
                except asyncio.TimeoutError:
                    # Timeout is expected (every 5 minutes), continue loop
                    continue
                except Exception as e:
                    logger.error("Error in sync loop", error=str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retry
                    
        except asyncio.CancelledError:
            logger.info("Background sync loop cancelled")
        except Exception as e:
            logger.error("Fatal error in background sync loop", error=str(e))
    
    async def _should_sync_now(self) -> bool:
        """Determine if sync should run now"""
        if self._is_syncing:
            return False
            
        now = datetime.now()
        
        # Check if we have any metadata at all
        connection = await self.db.get_connection()
        cursor = connection.execute("SELECT COUNT(*) as count FROM entity_types")
        row = cursor.fetchone()
        has_metadata = row and row["count"] > 0
        
        if not has_metadata:
            logger.info("No metadata found, sync needed")
            return True
        
        # Check if enough time has passed since last successful sync
        if self._last_successful_sync:
            if now - self._last_successful_sync >= self.sync_interval:
                logger.info("Sync interval exceeded, sync needed")
                return True
        
        # Check if we should retry after failure
        if (self._consecutive_failures > 0 and 
            self._last_sync_attempt and 
            now - self._last_sync_attempt >= self.retry_interval):
            logger.info("Retry interval exceeded after failure, sync needed")
            return True
        
        return False
    
    async def _trigger_sync(self):
        """Trigger a sync operation (non-blocking)"""
        if self._is_syncing:
            logger.debug("Sync already in progress, skipping trigger")
            return
            
        # Run sync in background to avoid blocking
        asyncio.create_task(self._perform_sync())
    
    async def _perform_sync(self) -> Dict[str, Any]:
        """Perform the actual metadata sync"""
        if self._is_syncing:
            raise RuntimeError("Sync already in progress")
        
        self._is_syncing = True
        self._last_sync_attempt = datetime.now()
        
        try:
            logger.info("Starting metadata synchronization")
            sync_start = time.time()
            
            # Clear existing metadata
            await self._clear_existing_metadata()
            
            # Fetch fresh metadata XML
            metadata_xml = await self.client.list_odata_entities()
            logger.info("Metadata XML fetched", size_bytes=len(metadata_xml))
            
            # Parse and store in SQLite
            connection = await self.db.get_connection()
            parser = BulkMetadataParser(connection)
            
            # Get D365 instance from client or config
            d365_instance = getattr(self.client, 'instance_url', 'unknown')
            
            stats = await parser.parse_and_store_metadata(
                metadata_xml, 
                d365_instance,
                chunk_size=1000
            )
            
            sync_duration = time.time() - sync_start
            stats["total_sync_duration_seconds"] = sync_duration
            stats["total_duration_seconds"] = sync_duration  # For compatibility
            
            # Update sync tracking
            self._last_successful_sync = datetime.now()
            self._consecutive_failures = 0
            
            logger.info("Metadata synchronization completed successfully",
                       duration_seconds=sync_duration,
                       entities_parsed=stats.get("entity_types_parsed", 0),
                       properties_parsed=stats.get("properties_parsed", 0))
            
            # Notify callbacks
            await self._notify_sync_callbacks(stats)
            
            return stats
            
        except Exception as e:
            self._consecutive_failures += 1
            
            logger.error("Metadata synchronization failed",
                        error=str(e),
                        attempt=self._consecutive_failures,
                        max_retries=self.max_retries)
            
            # Record failed sync
            connection = await self.db.get_connection()
            connection.execute("""
                INSERT INTO metadata_sync (
                    last_sync_at, last_sync_duration_ms, xml_size_bytes,
                    entity_count, enum_count, sync_status, error_message, d365_instance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                0,  # duration
                0,  # size
                0,  # entity count  
                0,  # enum count
                "failed",
                str(e),
                getattr(self.client, 'instance_url', 'unknown')
            ))
            connection.commit()
            
            # Notify callbacks of failure
            await self._notify_sync_callbacks({
                "sync_status": "failed",
                "error_message": str(e),
                "consecutive_failures": self._consecutive_failures
            })
            
            raise
            
        finally:
            self._is_syncing = False
    
    async def _clear_existing_metadata(self):
        """Clear existing metadata tables for fresh sync"""
        connection = await self.db.get_connection()
        
        # Clear in dependency order
        tables = [
            "entity_search",
            "enum_members", 
            "navigation_properties",
            "entity_properties",
            "entity_sets",
            "enum_types",
            "entity_types"
        ]
        
        for table in tables:
            connection.execute(f"DELETE FROM {table}")
        
        connection.commit()
        logger.debug("Existing metadata cleared")
    
    async def _notify_sync_callbacks(self, sync_result: Dict[str, Any]):
        """Notify all registered callbacks of sync completion"""
        for callback in self._sync_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(sync_result)
                else:
                    callback(sync_result)
            except Exception as e:
                logger.error("Error in sync callback", error=str(e))


class MetadataAvailabilityWaiter:
    """Helper class to wait for metadata to become available"""
    
    def __init__(self, db: Database, timeout_seconds: int = 300):
        self.db = db
        self.timeout_seconds = timeout_seconds
    
    async def wait_for_metadata(self) -> bool:
        """
        Wait for metadata to become available, with timeout.
        
        Returns:
            True if metadata is available, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout_seconds:
            if await self._is_metadata_available():
                return True
            
            await asyncio.sleep(1)  # Check every second
        
        return False
    
    async def _is_metadata_available(self) -> bool:
        """Check if metadata is available and recent"""
        connection = await self.db.get_connection()
        
        cursor = connection.execute("""
            SELECT COUNT(*) as entity_count,
                   MAX(last_sync_at) as last_sync
            FROM entity_types, metadata_sync  
            WHERE metadata_sync.sync_status = 'success'
        """)
        
        row = cursor.fetchone()
        return row and row["entity_count"] > 0