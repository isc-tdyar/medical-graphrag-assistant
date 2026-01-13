"""
Database connection module for IRIS.

Provides environment-aware connection management with sensible defaults
for local Docker IRIS instance (used on EC2 deployment).
"""

import os
import sys
import time
import importlib
from typing import Optional, Any

try:
    from dotenv import load_dotenv
    # Look for .env in project root (two levels up from src/db)
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass


class DatabaseConnection:
    """
    IRIS database connection manager with environment-based configuration.
    """

    # Default configuration (Local Docker IRIS)
    DEFAULT_CONFIG = {
        'hostname': 'localhost',
        'port': 32782,
        'namespace': '%SYS',
        'username': '_SYSTEM',
        'password': 'SYS'
    }
    
    @classmethod
    def get_config(cls) -> dict:
        """
        Get database configuration from environment variables with defaults.
        
        Returns:
            dict: IRIS connection parameters
        """
        return {
            'hostname': os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname']),
            'port': int(os.getenv('IRIS_PORT', cls.DEFAULT_CONFIG['port'])),
            'namespace': os.getenv('IRIS_NAMESPACE', cls.DEFAULT_CONFIG['namespace']),
            'username': os.getenv('IRIS_USERNAME', cls.DEFAULT_CONFIG['username']),
            'password': os.getenv('IRIS_PASSWORD', cls.DEFAULT_CONFIG['password'])
        }
    
    @classmethod
    def get_connection(cls, **kwargs) -> Any:
        """
        Create IRIS database connection with retries.
        
        Args:
            **kwargs: Optional overrides for connection parameters (hostname, port, etc.)
        
        Returns:
            DBAPI connection object
            
        Raises:
            ConnectionError: If all connection attempts fail
        """
        config = cls.get_config()
        # Only override with non-None kwargs
        for k, v in kwargs.items():
            if v is not None:
                config[k] = v
        
        max_retries = 3
        retry_delay = 1
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Use dynamic import to avoid static analysis issues
                # Try intersystems_iris first (modern SDK)
                try:
                    iris_mod = importlib.import_module('intersystems_iris')
                except ImportError:
                    # Fallback to the legacy 'iris' module name
                    try:
                        iris_mod = importlib.import_module('iris')
                    except ImportError:
                        iris_mod = None
                
                if iris_mod:
                    # Use the user-suggested getattr trick for dynamic connection
                    connect_fn = getattr(iris_mod, 'connect', None)
                    if connect_fn:
                        return connect_fn(**config)
                
                # Try irisnative if available
                try:
                    native_mod = importlib.import_module('irisnative')
                    # Connection params vary for irisnative.createConnection
                    return native_mod.createConnection(
                        config['hostname'], 
                        int(config['port']), 
                        config['namespace'], 
                        config['username'], 
                        config['password']
                    )
                except ImportError:
                    pass

                # Deep fallback to iris.dbapi
                try:
                    dbapi_mod = importlib.import_module('iris.dbapi')
                    return dbapi_mod.connect(**config)
                except ImportError:
                    pass

                raise ImportError("No IRIS connection module found (tried intersystems_iris, iris, irisnative, iris.dbapi)")

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"Warning: IRIS connection attempt {attempt+1} failed ({e}). Retrying in {retry_delay}s...", file=sys.stderr)
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                else:
                    # Final attempt failed
                    break
        
        # Add context to error message
        raise ConnectionError(
            f"Failed to connect to IRIS at {config['hostname']}:{config['port']}/{config['namespace']} after {max_retries} attempts. "
            f"Error: {str(last_error)}"
        )
    
    @classmethod
    def is_local(cls) -> bool:
        """Check if configured database is on localhost."""
        hostname = os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname']).lower()
        return hostname in ('localhost', '127.0.0.1', '::1')
    
    @classmethod
    def is_docker(cls) -> bool:
        """Check if configured database is using default Docker config."""
        hostname = os.getenv('IRIS_HOST', cls.DEFAULT_CONFIG['hostname'])
        port = int(os.getenv('IRIS_PORT', cls.DEFAULT_CONFIG['port']))
        return hostname in ('localhost', '127.0.0.1') and port == 32782

    @classmethod
    def get_info(cls) -> str:
        """Get human-readable connection info string."""
        config = cls.get_config()
        env = 'Docker' if cls.is_docker() else ('Local' if cls.is_local() else 'Remote')
        return f"{env} IRIS @ {config['hostname']}:{config['port']}/{config['namespace']}"


def get_connection() -> Any:
    """Create IRIS database connection wrapper."""
    return DatabaseConnection.get_connection()


if __name__ == '__main__':
    # Test connection
    print("Testing IRIS database connection...")
    print(f"Config: {DatabaseConnection.get_info()}")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        print(f"✅ Connected successfully!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
