import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Configure logging for the database module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockResponse:
    def __init__(self, data):
        self.data = data

class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data if data is not None else [{"session_id": "mock-session-id"}]
    def execute(self):
        return MockResponse(self._data)
    def eq(self, *args, **kwargs):
        return self
    def lte(self, *args, **kwargs):
        return self

class MockTable:
    def insert(self, payload, *args, **kwargs):
        return MockQueryBuilder([payload] if isinstance(payload, dict) else payload)
    def select(self, *args, **kwargs):
        return MockQueryBuilder([{"session_id": "mock-session-id", "is_active": True}])
    def update(self, *args, **kwargs):
        return MockQueryBuilder([{"session_id": "mock-session-id", "is_active": True}])
    def delete(self, *args, **kwargs):
        return MockQueryBuilder([])

class MockSupabaseClient:
    def table(self, table_name):
        return MockTable()


def get_supabase_client() -> Client:
    """
    Initializes and returns a Supabase Client instance when credentials are available.
    Falls back to the mock client only if initialization fails, so local development
    and tests remain usable even without a configured Supabase project.
    """
    disable_supabase = os.environ.get("DISABLE_SUPABASE", "false").lower() in ("true", "1", "yes")
    if disable_supabase:
        logger.info("Supabase is disabled via DISABLE_SUPABASE flag. Using Mock client.")
        return MockSupabaseClient()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.info("Supabase credentials not configured. Using Mock client.")
        return MockSupabaseClient()

    try:
        client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully.")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}. Falling back to Mock client.")
        return MockSupabaseClient()


# Singleton instance for application-wide database access
supabase_db = get_supabase_client()