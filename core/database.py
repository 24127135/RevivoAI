import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Configure logging for the database module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Initializes and returns a Supabase Client instance.
    Uses the service_role key to obtain administrative privileges (bypassing RLS).

    Raises:
        ValueError: If SUPABASE_URL or Supabase key variables are missing from environment variables.
        Exception: If Supabase client initialization fails.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )

    if not supabase_url or not supabase_key:
        logger.error(
            "Missing SUPABASE_URL or one of SUPABASE_KEY/SUPABASE_SECRET_KEY/"
            "SUPABASE_SERVICE_ROLE_KEY in environment variables."
        )
        raise ValueError(
            "Environment variables SUPABASE_URL and one of SUPABASE_KEY, "
            "SUPABASE_SECRET_KEY, or SUPABASE_SERVICE_ROLE_KEY must be set."
        )

    try:
        client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise


# Singleton instance for application-wide database access
supabase_db = get_supabase_client()