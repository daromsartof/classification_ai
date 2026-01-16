from services.database_service import DatabaseService
from services.logger import Logger
from services import constant

logger = Logger.get_logger()
class LotRepositorie:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)

    def get_lot_to_process(self):
        try:
            query = """
                SELECT * FROM lot 
                WHERE (status_new = 4 OR status = 2) 
                AND DATE(date_scan) = DATE('2025-05-13')
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return rows

        except Exception as e:
            logger.error(f"Error fetching lots to process: {e}")
            return []
        
    def update_lot(self, lot_id: int, data: dict):
        try:
            if 'status_new' not in data:
                raise ValueError("Missing 'status_new' in data")
            query = "UPDATE lot SET status_new = %s WHERE id = %s"
            self.cursor.execute(query, [data.get('status_new', 6), lot_id])
            self.connection.commit()
            logger.info(f"Lot {lot_id} updated successfully with status_new = {data.get('status_new', 6)}")
            return True

        except Exception as e:
            logger.error(f"Error updating lot {lot_id}: {e}")
            return False
