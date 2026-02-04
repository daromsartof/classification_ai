from services.database_service import DatabaseService
from services.logger import Logger
from services.constant import StatusNew, CategorieId, SousCategorieId
logger = Logger.get_logger()

class ImageRepositorie:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor =  self.connection.cursor(dictionary=True)
        
    def set_image_finished(self, image_id: int):
        try:
            query = "UPDATE image SET status_new = 4 WHERE id = %s"
            self.cursor.execute(query, [image_id])
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting image status_new finised : {e}")
            return False
        
    def get_image_to_process_by_lot_id(self, lot_id: int):
        try:
            query = 'select * from image where lot_id = %s'
            
            self.cursor.execute(query, [lot_id])
            rows = self.cursor.fetchall()
            return rows
        
        except Exception as e:
            logger.error(f"Error fetching image by lot_id: {e}")
            return []
    
    def get_image_to_process(self, image_id=None, lot_id=None, for_validation=False, lot_ids=[], client_id=None, dossier_id=None, for_analyse=False):
        try:
            #query = "select i.nom, l.date_scan, l.id lot_id, d.id dossier_id, d.nom dossier_name, d.site from image i join lot l on l.id = i.lot_id join dossier d on d.id = l.dossier_id where (l.status_new = 4 or l.status = 2) and date(l.date_scan) = date('2025-05-13')"
            print(image_id)
            select_clause = """
                SELECT 
                    distinct i.id, 
                    i.nom name, 
                    i.originale originale,
                    i2.nom parent_name,
                    l.date_scan, 
                    i.ext_image ext_image,
                    c.nom client_nom, 
                    i.categorie_id, 
                    i.exercice, 
                    d.nom dossier_nom, 
                    l.lot lot_num, 
                    l.id lot_id,
                    d.id dossier_id, 
                    d.siren_ste, 
                    d.rs_ste, 
                    s.client_id client_id, 
                    d.site_id site_id, 
                    i.status, 
                    i.status_new, 
                    l.status lot_status, 
                    l.status_new lot_status_new,
                    act.code_ape ape,
                    act.libelle activite_3,
                    act_2.libelle activite_2,
                    act_1.libelle activite_1,
                    act_0.libelle activite_0
                FROM image i
            """
            from_clause = """
                JOIN lot l ON i.lot_id = l.id
                JOIN dossier d ON l.dossier_id = d.id
                LEFT JOIN image_image ii ON ii.image_id_autre = i.id
                LEFT JOIN image i2 ON i2.id = ii.image_id
                JOIN site s ON s.id = d.site_id
                JOIN client c ON c.id = s.client_id
                LEFT JOIN activite_com_cat_3 act on act.id = d.activite_com_cat_3_id
                LEFT JOIN activite_com_cat_2 act_2 on act_2.id = act.activite_com_cat_2_id
                LEFT JOIN activite_com_cat_1 act_1 on act_1.id = act_2.activite_com_cat_1_id
                LEFT JOIN activite_com_cat act_0 on act_0.id = act_1.activite_com_cat_id
            """

            if image_id:
                where_clause = f"""
                WHERE i.id = {image_id}"""
            elif lot_id:
                where_clause = f"""
                WHERE l.id = {lot_id}"""
            elif for_validation:
                where_clause = f"""
                LEFT JOIN ai_ocr_content ai_ocr ON ai_ocr.image_id = i.id
                WHERE i.supprimer = 0 and i.source_image_id = 29 and ai_ocr.image_id is null """
                if client_id:
                    where_clause += f"and s.client_id = {client_id} "
                elif dossier_id:
                    where_clause += f"and d.id = {dossier_id} "
                where_clause += " limit 50 """
            elif for_analyse:
                where_clause = f"""
                LEFT JOIN ai_ocr_content_docs ai_ocr ON ai_ocr.image_id = i.id
                WHERE i.supprimer = 0 and i.source_image_id = 29 and ai_ocr.image_id is null and i.categorie_id <> 27 """
                if client_id:
                    where_clause += f"and s.client_id = {client_id} "
                elif dossier_id:
                    where_clause += f"and d.id = {dossier_id} "
                where_clause += " limit 50 """
            elif len(lot_ids) > 0:
                where_clause = f"""
                WHERE l.id IN ({','.join(map(str, lot_ids))})"""
            else:
                where_clause = f"""
                LEFT JOIN decoupage_niveau2 dc ON dc.image_id = i.id
                LEFT JOIN ai_separation ai_s ON ai_s.image_id = i.id
                WHERE ((((l.status_new = 4 or l.status_new = 5))))
                and date(l.date_scan) >= DATE('2026-01-05')  
                and ai_s.image_id is null """
                if client_id:
                    where_clause += f"and s.client_id = {client_id} "
                elif dossier_id:
                    where_clause += f"and d.id = {dossier_id} "
                where_clause += "and i.decouper=0 order by  l.id, l.date_scan asc"
                
            #or (l.status = 2 and EXISTS (SELECT 1 from panier_reception pr where pr.operateur_id is not null and lot_id = l.id))
            query = select_clause + from_clause + where_clause
            print(query)
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return rows
        
        except Exception as e:
            logger.error(f"Error fetching image to process: {e}")
            return []
    
    def get_image_by_id(self, image_id: int) -> dict:
        try:
            query = "select * from image where id = %s"
            self.cursor.execute(query, [image_id])
            res = self.cursor.fetchall() or []
            if len(res) > 0:
                return res[0]
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching image by id: {e}")
            return None
    
    def get_image_by_name(self, name: str) -> list:
        """Retrieve image(s) from database where name matches the search pattern.
        
        Args:
            name: The name or partial name to search for
            
        Returns:
            List of matching image records or empty list if no matches found
        """
        try:
            query = "select i.*, d.nom dossier_name, d.siren_ste, d.rs_ste, d.id dossier_id  from image i join lot l on l.id = i.lot_id join dossier d on d.id = l.dossier_id where i.nom like  %s"
            self.cursor.execute(query, [name])
            res = self.cursor.fetchall() or []
            if len(res) > 0:
                return res[0]
            else:
                return {}
        except Exception as e:
            logger.error(f"Error fetching image by name: {e}")
            return {} 
    
    def update_image(self, image_id: int, data: dict, status: int = 6) -> dict:
        try:
            image = self.get_image_by_id(image_id)
            if not image:
                raise Exception(f"Image not found for id: {image_id}")
            if image.get('categorie_id', None):
                image['explication'] = f"l'image a déjà été classée"
                return image
            if image.get('status_new', None) >= StatusNew.FINISHED:
                status = image.get('status_new', None)
            if data.get('categorie_id', None) == CategorieId.BANQUE:
                data['sous_categorie_id'] = SousCategorieId.RELEVER_BANCAIRE
            else :
                data['souscategorie_id'] = None
                
            query = "UPDATE `image` SET `categorie_id`=%s, `status_new`=%s, `decouper`=%s, `souscategorie_id`=%s WHERE `id`=%s;"
            logger.info(f"query: {query} - data: {data.get('categorie_id', None)} - status: {status} - decouper: {data.get('decouper', 0)} - image_id: {image_id}")
            self.cursor.execute(query, [data.get('categorie_id', None), status, data.get('decouper', 0), data.get('souscategorie_id', None), image_id])
            self.connection.commit()
            image = self.get_image_by_id(image_id)
            return image
        except Exception as e:
            logger.error(f"Error updating image: {e}")
            return None
        
    
    def insert_image(
                self, 
                originale: str, 
                ext_image: str, 
                renommer: str, 
                nbpage: int, 
                lot_id: int, 
                source_image_id: int, 
                status: int, 
                exercice: int,
                supprimer: int = 0, 
                download: str = None, 
                a_remonter: int = 1, 
                numerotation_local: int = 1,
                status_new: int = 4,
    ) -> int:
        """Insert a new image record into the database.
        
        Args:
            originale: Original image name
            ext_image: Image extension
            renommer: Renamed image name
            nbpage: Number of pages
            lot_id: Lot ID
            source_image_id: Source image ID
            status: Image status
            status_new: Status
            download: Date of download
            exercice: Exercise year
            supprimer: Deletion flag (default 0)
            a_remonter: Remontage flag (default 0)
            numerotation_local: Local numbering flag (default 0)
            
        Returns:
            The ID of the inserted image or None if error
        """
        try:
            sql_insert = """
                INSERT INTO image 
                    (
                        originale, 
                        ext_image, 
                        renommer, 
                        nbpage, 
                        lot_id, 
                        source_image_id, 
                        status,
                        exercice, 
                        supprimer, 
                        download, 
                        a_remonter, 
                        numerotation_local,
                        status_new
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql_insert, [
                originale, 
                ext_image,
                renommer, 
                nbpage, 
                lot_id,
                source_image_id, 
                status, 
                exercice, 
                supprimer, 
                download, 
                a_remonter, 
                numerotation_local,
                status_new
            ])
            self.connection.commit()
            inserted_id = self.cursor.lastrowid
            image = self.get_image_by_id(inserted_id)
            logger.info(f"Inserted new image with id: {inserted_id}")
            return image
        except Exception as e:
            logger.error(f"Error inserting image: {e}")
            self.connection.rollback()
            return None
        
    def count_status_finished_by_lot(self, lot_id: int) -> int:
        try:
            query = 'select count(*) lot_num from image where lot_id = %s'
            
            self.cursor.execute(query, [lot_id])
            rows = self.cursor.fetchall()   
            return rows[0].get("lot_num", 0)
        
        except Exception as e:
            logger.error(f"Error count_status_finished_by_lot image by lot_id: {e}")
            return 0
    
    def insert_into_image_image(self, image_id: int, image_id_autre: int) -> int:
        try:
            query = "INSERT INTO image_image (image_id, image_id_autre) VALUES (%s, %s)"
            self.cursor.execute(query, [image_id, image_id_autre])
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting into image_image: {e}")
            return False
    
    def get_image_image_by_image_id(self, image_id: int) -> list:
        try:
            query = """SELECT i.*, i2.nom parent_name, i2.id parent_id FROM image_image ii 
                join image i on i.id = ii.image_id_autre 
                join image i2 on i2.id = ii.image_id 
                WHERE ii.image_id = %s"""
            self.cursor.execute(query, [image_id])
            res = self.cursor.fetchall() or []
            return res
        except Exception as e:
            logger.error(f"Error fetching image_image by image_id: {e}")
            return None

    def set_image_decouper(self, image_id: int) -> bool:
        try:
            query = "UPDATE image SET decouper = 1 WHERE id = %s"
            self.cursor.execute(query, [image_id])
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting image decouper: {e}")
            return False