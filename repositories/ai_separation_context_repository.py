from services.database_service import DatabaseService

from services.logger import Logger

logger = Logger.get_logger()

class AiSeparationContextRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def get_ai_separation_context_by(self, dossier=None, site=None, client=None):
        try:
            query = "select * from ai_separation_context "
            where_clause = " where "
            if dossier: 
                where_clause += f"dossier_id = {dossier} "
            
            if client:
                where_clause += f"or (client_id = {client}) "

            if site: 
                where_clause += f"or ( site_id = {site} and dossier_id is null) "
            where_clause += "or (dossier_id is null and client_id is null and site_id is null) "
            query += where_clause
            query += " order by created_at desc"

            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return rows
        
        except Exception as e:
            logger.error(f"Error fetching ai_separation_context: {e}")
            return []

