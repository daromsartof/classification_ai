from services.database_service import DatabaseService
from services.logger import Logger

logger = Logger.get_logger()

class CategorieRepositorie:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor = self.connection.cursor(dictionary=True)

    def is_valid_categorie_relation(self, categorie_id: int, souscategorie_id: int, soussouscategorie_id: int) -> bool:
        """
        Check if the given ids match the existing relation in the database.
        Returns True if the relation exists, False otherwise.
        """
        try:
            query = """SELECT COUNT(*) as count FROM categorie c 
                JOIN souscategorie sc ON sc.categorie_id = c.id 
                JOIN soussouscategorie ssc ON ssc.souscategorie_id = sc.id 
                WHERE c.id = %s
            """
            if (souscategorie_id):
               query += f" AND sc.id = {souscategorie_id} "
            if (soussouscategorie_id):
                query += f"AND ssc.id = {soussouscategorie_id} "

            self.cursor.execute(query, [categorie_id])
            result = self.cursor.fetchone()
            return result and result.get('count', 0) > 0
        except Exception as e:
            logger.error(f"Error checking categorie relation: {e}")
            return False

    def is_valid_souscategorie_for_categorie(self, categorie_id: int, souscategorie_id: int) -> bool:
        """
        Check if the given souscategorie_id belongs to the given categorie_id.
        Returns True if the relation exists, False otherwise.
        """
        try:
            query = (
                "SELECT COUNT(*) as count FROM souscategorie "
                "WHERE id = %s AND categorie_id = %s"
            )
            self.cursor.execute(query, [souscategorie_id, categorie_id])
            result = self.cursor.fetchone()
            return result and result.get('count', 0) > 0
        except Exception as e:
            logger.error(f"Error checking souscategorie-categorie relation: {e}")
            return False

    def is_valid_soussouscategorie_for_souscategorie(self, souscategorie_id: int, soussouscategorie_id: int) -> bool:
        """
        Check if the given soussouscategorie_id belongs to the given souscategorie_id.
        Returns True if the relation exists, False otherwise.
        """
        try:
            query = (
                "SELECT COUNT(*) as count FROM soussouscategorie "
                "WHERE id = %s AND souscategorie_id = %s"
            )
            self.cursor.execute(query, [soussouscategorie_id, souscategorie_id])
            result = self.cursor.fetchone()
            return result and result.get('count', 0) > 0
        except Exception as e:
            logger.error(f"Error checking soussouscategorie-souscategorie relation: {e}")
            return False
