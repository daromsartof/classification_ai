from services.database_service import DatabaseService
from services.constant import panier_reception_user
from services.logger import Logger

logger = Logger.get_logger()

class PanierReceptionRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    
    def get_panier_reception_by_key(self, lot_id: int):
        try:
            query = "select * from panier_reception where lot_id = %s and etape_traitement_id = 3"
            self.cursor.execute(query, [lot_id])
            rows = self.cursor.fetchall()
            return rows[0] if rows else None
                
        except:
            logger.error("Error fetching panier_reception by key")
            return None
        
    def update_or_create_panier_reception(self, lot_id: int):
        try:
            logger.info(f"Updating or creating panier_reception for lot_id: {lot_id}")
            panier_reception = self.get_panier_reception_by_key(lot_id)
            if panier_reception:
                query = "UPDATE panier_reception SET date_fait = NOW(), status = 1 WHERE id = %s"
                self.cursor.execute(query, [panier_reception["id"]])
                self.connection.commit()
                logger.info("Panier_reception updated successfully.")
                return self.get_panier_reception_by_key(lot_id)
            else:
                query = """
                    INSERT INTO panier_reception 
                    (lot_id, operateur_id,  etape_traitement_id, status, utilisateur_id, utilisateur_partage_id, date_partage, date_fait)
                    VALUES (%s, %s, 3, 1, %s, %s, NOW(), NOW())
                """
                self.cursor.execute(query, [
                    lot_id, 
                    panier_reception_user.get("stephanie", 1307),
                    panier_reception_user.get("HARIVOLATIANA", 6641), 
                    panier_reception_user.get("RAZAFINDRATSIMBA", 2517)
                ])
                self.connection.commit()
                logger.info("Panier_reception created successfully.")
                return {}
        except Exception as e:
            logger.error("Error updating panier_reception:", e)
            return None
