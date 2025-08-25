"""
Database connection management for PostgreSQL
"""

import sys
import os
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_CONFIG


class DatabaseConnection:
    """
    Database connection manager for PostgreSQL
    """
    
    def __init__(self):
        self.config = DATABASE_CONFIG
        self.engine = None
        self.session_maker = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialize database connection and SQLAlchemy engine"""
        try:
            # Create connection string
            connection_string = (
                f"postgresql://{self.config['user']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['dbname']}"
            )
            
            print(f"🔗 Connecting to database: {self.config['dbname']} at {self.config['host']}")
            
            # Create SQLAlchemy engine
            self.engine = create_engine(
                connection_string,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False  # Set to True for SQL debugging
            )
            
            # Create session maker
            self.session_maker = sessionmaker(bind=self.engine)
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            print("✅ Database connection established successfully")
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dictionaries
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of dictionaries with query results
        """
        try:
            print(f"📊 Executing query: {query[:100]}{'...' if len(query) > 100 else ''}")
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                
                # Convert result to list of dictionaries
                columns = result.keys()
                rows = result.fetchall()
                
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    data.append(row_dict)
                
                print(f"✅ Query executed successfully, returned {len(data)} rows")
                return data
                
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get table schema information
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        ORDER BY ordinal_position
        """
        
        return self.execute_query(query, {"table_name": table_name})
    
    def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            True if connection is working, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT current_timestamp"))
                timestamp = result.fetchone()[0]
                print(f"✅ Database connection test successful. Current time: {timestamp}")
                return True
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            print("🔒 Database connection closed")
    
    def get_connection_string(self) -> str:
        """Get SQLAlchemy connection string for LangChain"""
        return (
            f"postgresql://{self.config['user']}:{self.config['password']}"
            f"@{self.config['host']}:{self.config['port']}/{self.config['dbname']}"
        )
