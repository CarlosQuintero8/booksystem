"""
Database connection utilities for Library Management System
Provides connection management and query execution capabilities
"""

import sqlite3
import logging
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
from database.config.database_config import DatabaseConfig, DatabaseType

# PostgreSQL import
try:
    import psycopg2
    import psycopg2.extras
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    raise ImportError("psycopg2 not installed. Install with: pip install psycopg2-binary")

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection manager"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        
    def connect(self):
        """Establish PostgreSQL database connection"""
        try:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
            logger.info("Connected to PostgreSQL database")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
        if not self._connection:
            self.connect()
            
        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT, UPDATE, DELETE command and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(command, params or ())
            self._connection.commit()
            return cursor.rowcount
    
    def execute_script(self, script: str) -> None:
        """Execute multiple SQL statements"""
        with self.get_cursor() as cursor:
            # Split script into individual statements for PostgreSQL
            statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
            for statement in statements:
                cursor.execute(statement)
            self._connection.commit()
    
    def get_last_insert_id(self) -> Optional[int]:
        """Get the ID of the last inserted row"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT LASTVAL()")
            result = cursor.fetchone()
            return result[0] if result else None
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = "SELECT tablename FROM pg_tables WHERE tablename=%s"
        result = self.execute_query(query, (table_name,))
        return len(result) > 0

# Connection pool for managing multiple connections
class ConnectionPool:
    """Simple connection pool implementation"""
    
    def __init__(self, config: DatabaseConfig, pool_size: int = 5):
        self.config = config
        self.pool_size = pool_size
        self._pool = []
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            conn = DatabaseConnection(self.config)
            self._pool.append(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        if not self._pool:
            # Create new connection if pool is empty
            conn = DatabaseConnection(self.config)
        else:
            conn = self._pool.pop()
        
        try:
            yield conn
        finally:
            # Return connection to pool
            if len(self._pool) < self.pool_size:
                self._pool.append(conn)
            else:
                conn.disconnect()

# Global connection instance
_global_connection: Optional[DatabaseConnection] = None

def get_connection(config: Optional[DatabaseConfig] = None) -> DatabaseConnection:
    """Get global database connection instance"""
    global _global_connection
    
    if _global_connection is None:
        if config is None:
            from database.config.database_config import get_config
            config = get_config()
        _global_connection = DatabaseConnection(config)
    
    return _global_connection

def close_global_connection():
    """Close global database connection"""
    global _global_connection
    if _global_connection:
        _global_connection.disconnect()
        _global_connection = None