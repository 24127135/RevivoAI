import os
import uuid
import shutil
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from core.database import supabase_db

logger = logging.getLogger(__name__)

# Base directory for server-side workspaces
BASE_WORKSPACE_DIR = os.getenv("WORKSPACE_BASE_PATH", "/tmp/revivoai_workspaces")

VALID_STATUSES = {"active", "deactivated"}


class SessionHandler:
    """
    Manages session lifecycles, workspace isolation, and state persistence
    backed by Supabase (PostgreSQL).
    """

    def __init__(self):
        self.db = supabase_db
        logger.info("SessionHandler initialized with Supabase persistence.")

    async def _execute_db_call(self, query_builder) -> Any:
        return await asyncio.to_thread(query_builder.execute)

    async def initialize_session(self, user_id: str) -> Optional[str]:
        """
        Generates a new secure UUID, provisions a temporary server-side
        workspace, and persists the session to the database.
        """
        session_id = str(uuid.uuid4())
        workspace_path = os.path.join(BASE_WORKSPACE_DIR, session_id)

        # Provision physical workspace directory
        try:
            await asyncio.to_thread(os.makedirs, workspace_path, exist_ok=True)
            logger.info(f"Workspace provisioned at {workspace_path}")
        except Exception as e:
            logger.error(f"Failed to create workspace directory for {session_id}: {e}")
            raise

        # Prepare DB Payload with explicit timestamps to satisfy NOT NULL constraints
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(hours=2)

        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "is_active": True,
            "created_at": now_utc.isoformat(),
            "expires_at": expires_at.isoformat()
        }

        try:
            query = self.db.table("Session").insert(payload)
            response = await self._execute_db_call(query)

            if not response.data:
                logger.warning(
                    f"Insert query returned empty data. Check Supabase RLS policies for session {session_id}.")
                await self._cleanup_workspace(workspace_path)
                return None

            logger.info(f"Successfully initialized session {session_id} for user {user_id}.")
            return session_id

        except Exception as e:
            logger.error(f"Database error initializing session {session_id}: {e}")
            await self._cleanup_workspace(workspace_path)
            raise

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            query = self.db.table("Session").select("*").eq("session_id", session_id)
            response = await self._execute_db_call(query)

            if not response.data:
                logger.warning(f"Session {session_id} not found or access denied by RLS.")
                return None

            session_data = response.data[0]
            session_data["workspace_path"] = os.path.join(BASE_WORKSPACE_DIR, session_data["session_id"])

            return session_data

        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {e}")
            raise

    async def update_session_status(self, session_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. Must be one of {sorted(VALID_STATUSES)}."
            )

        try:
            is_active = new_status == "active"

            query = self.db.table("Session").update({"is_active": is_active}).eq("session_id", session_id)
            response = await self._execute_db_call(query)

            if not response.data:
                logger.warning(f"Failed to update. Session {session_id} not found or RLS blocked.")
                return None

            logger.info(f"Session {session_id} status updated to '{new_status}' (is_active={is_active}).")

            session_data = response.data[0]
            session_data["workspace_path"] = os.path.join(BASE_WORKSPACE_DIR, session_data["session_id"])
            return session_data

        except Exception as e:
            logger.error(f"Failed to update status for session {session_id}: {e}")
            raise

    async def destroy_session(self, session_id: str) -> bool:
        """
        Cleans up the physical workspace and permanently deletes the session
        record from the database (hard-delete — no 'closed'/soft-delete state).
        """
        session_data = await self.get_session(session_id)
        if not session_data:
            logger.warning(f"Cannot destroy session {session_id}: Not found.")
            return False

        workspace_path = session_data.get("workspace_path")

        # 1. Best-effort cleanup of physical files. Failures here are logged
        #    but do not block the DB delete below — the database row is the
        #    source of truth for whether a session exists.
        if workspace_path:
            await self._cleanup_workspace(workspace_path)

        # 2. Hard-delete the DB record.
        try:
            query = self.db.table("Session").delete().eq("session_id", session_id)
            response = await self._execute_db_call(query)

            if not response.data:
                logger.warning(
                    f"Delete query returned no data for session {session_id}; "
                    f"row may already have been removed."
                )
                return False

            logger.info(f"Session {session_id} permanently destroyed.")
            return True

        except Exception as e:
            logger.error(f"Error deleting DB record during destroy of session {session_id}: {e}")
            return False

    async def _cleanup_workspace(self, workspace_path: str):
        """Helper method to remove the physical directory."""
        if os.path.exists(workspace_path):
            try:
                await asyncio.to_thread(shutil.rmtree, workspace_path)
                logger.info(f"Removed workspace directory: {workspace_path}")
            except Exception as e:
                logger.error(f"Failed to remove workspace {workspace_path}: {e}")

    async def reap_expired_sessions(self) -> int:
        """
        Scans and cleans up sessions that have exceeded their expires_at timestamp,
        regardless of their current is_active flag (a session can be deactivated
        long before it expires, and must still be reaped once expires_at passes).
        Returns the number of successfully reaped sessions.
        """
        now_utc = datetime.now(timezone.utc).isoformat()

        try:
            query = (
                self.db.table("Session")
                .select("session_id")
                .lte("expires_at", now_utc)
            )
            response = await self._execute_db_call(query)

            if not response.data:
                return 0

            reaped_count = 0
            for session in response.data:
                session_id = session["session_id"]
                logger.info(f"[Reaper] Cleaning up expired session: {session_id}")

                success = await self.destroy_session(session_id)
                if success:
                    reaped_count += 1

            return reaped_count

        except Exception as e:
            logger.error(f"[Reaper] Error querying expired sessions: {e}")
            return 0
