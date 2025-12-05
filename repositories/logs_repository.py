from services.database_service import DatabaseService
from services.logger import Logger

logger = Logger.get_logger()

class LogsRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def log_action(self, utilisateur_id: int, image_id: int | None = None, lot_id: int | None = None) -> None:
        try:
            if lot_id is None:
                query = """
                    INSERT INTO logs (date_debut, date_fin, etape_traitement_id, remarque, utilisateur_id, image_id)
                    VALUES (NOW(), NOW(), 2, 'SEPARATION AVEC GENZIA', %s, %s);
                """
                params = (utilisateur_id, image_id)
            else:
                query = """
                    INSERT INTO logs (date_debut, date_fin, etape_traitement_id, remarque, utilisateur_id, lot_id)
                    VALUES (NOW(), NOW(), 2, 'SEPARATION AVEC GENZIA', %s, %s);
                """
                params = (utilisateur_id, lot_id)

            self.cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            logger.error(f"Error logging action: {e}")
