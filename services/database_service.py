import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling
from typing import Dict, List, Optional, Union

load_dotenv()
from services.logger import Logger

logger = Logger.get_logger()
class DatabaseService:
    """
    Database class for MySQL operations
    """
    
    def __init__(self, config: Dict = {}):
        """
        Initialize database connection pool
        
        Args:
            config (Dict): Additional database configuration
        """
        self.config = {
            'host': os.getenv('DB_HOST'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_DATABASE'),
            **config
        }
        
        self.pool = pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=5,
            **self.config
        )

    def get_pool(self) -> pooling.MySQLConnectionPool:
        """
        Get the connection pool
        
        Returns:
            pooling.MySQLConnectionPool: The MySQL connection pool
        """
        return self.pool

    async def insert_data(self, table: str, data: Dict) -> Dict:
        """
        Insert data into a table
        
        Args:
            table (str): Table name
            data (Dict): Data to insert (key-value pairs)
            
        Returns:
            Dict: Result of the operation
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = list(data.values())
            
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, values)
            connection.commit()
            
            return {
                'success': True,
                'insert_id': cursor.lastrowid,
                'affected_rows': cursor.rowcount
            }
        except Exception as error:
            logger.error(f"Error inserting data: {error}")
            return {
                'success': False,
                'error': str(error)
            }
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()

    async def select_data(
        self,
        table: str,
        columns: List[str] = ['*'],
        where: Optional[Dict] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Select data from a table
        
        Args:
            table (str): Table name
            columns (List[str]): Columns to select
            where (Dict): WHERE conditions (key-value pairs)
            options (Dict): Additional options (order_by, limit, offset)
            
        Returns:
            Dict: Result of the operation
        """
        try:
            connection = self.pool.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            columns_str = ', '.join(columns)
            query = f"SELECT {columns_str} FROM {table}"
            values = []
            
            if where and len(where) > 0:
                where_conditions = ' AND '.join([f"{key} = %s" for key in where.keys()])
                values.extend(where.values())
                query += f" WHERE {where_conditions}"
            
            if options:
                if 'order_by' in options:
                    column = options['order_by'].get('column')
                    direction = options['order_by'].get('direction', 'ASC')
                    query += f" ORDER BY {column} {direction}"
                
                if 'limit' in options:
                    query += " LIMIT %s"
                    values.append(options['limit'])
                    
                    if 'offset' in options:
                        query += " OFFSET %s"
                        values.append(options['offset'])
            
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            return {
                'success': True,
                'count': len(rows),
                'data': rows
            }
        except Exception as error:
            logger.error(f"Error selecting data: {error}")
            return {
                'success': False,
                'error': str(error)
            }
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()