from services.database_service import DatabaseService
from services.logger import Logger

logger = Logger.get_logger()


class AiOcrContentDocsRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor = self.connection.cursor(dictionary=True)

    def getAllAiOcrContentDocs(self, filters=None):
        """
        Get all AI OCR content with optional filters
        
        Args:
            filters (dict): Optional filters with keys like 'image_id', 'ai_ocr_prompt_id'
            
        Returns:
            list: List of content records with related image and prompt information
        """
        if filters is None:
            filters = {}
        
        try:
            query = """
                SELECT 
                    aocd.*,
                    i.id as image_id_img,
                    i.nom as image_nom,
                    aocd.content as ai_ocr_content_content
                FROM ai_ocr_content_docs aocd
                LEFT JOIN image i ON i.id = aocd.image_id
            """
            
            where_clauses = []
            params = []
            
            if filters.get('image_id'):
                where_clauses.append("aocd.image_id = %s")
                params.append(int(filters['image_id']))

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY aocd.created_at DESC"
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            # Format results to match expected structure
            formatted_results = []
            for row in rows:
                formatted_row = dict(row)
                # Add image info if available
                if row.get('image_id_img'):
                    formatted_row['image'] = {
                        'id': row.get('image_id_img'),
                        'nom': row.get('image_nom')
                    }
                # Remove the joined fields
                formatted_row.pop('image_id_img', None)
                formatted_row.pop('image_nom', None)
                formatted_row.pop('ai_ocr_content_content', None)
                formatted_results.append(formatted_row)
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error fetching all AI OCR content docs: {e}")
            return []

    def getAiOcrContentDocsById(self, id):
        """
        Get a single AI OCR content docs by ID
        
        Args:
            id: The content ID
            
        Returns:
            dict: Content with related image and prompt information or None if not found
        """
        try:
            query = """
                SELECT 
                    aocd.*,
                    i.id as image_id_img,
                    i.nom as image_nom
                FROM ai_ocr_content_docs aocd
                LEFT JOIN image i ON i.id = aocd.image_id
                WHERE aocd.id = %s
            """
            
            self.cursor.execute(query, [int(id)])
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            # Format result to match expected structure
            formatted_row = dict(row)
            # Add image info if available
            if row.get('image_id_img'):
                formatted_row['image'] = {
                    'id': row.get('image_id_img'),
                    'nom': row.get('image_nom')
                }
            # Remove the joined fields
            formatted_row.pop('image_id_img', None)
            formatted_row.pop('image_nom', None)
            
            return formatted_row
        
        except Exception as e:
            logger.error(f"Error fetching AI OCR content docs by id: {e}")
            return None

    def getAiOcrContentDocsByImageId(self, image_id):
        """
        Get all AI OCR content for a specific image
        
        Args:
            image_id: The image ID
            
        Returns:
            list: List of content records with related prompt information
        """
        try:
            query = """
                SELECT 
                    aoc.*,
                    aop.id as prompt_id_prompt,
                    aop.categorie_id as prompt_categorie_id
                FROM ai_ocr_content aoc
                LEFT JOIN ai_ocr_prompts aop ON aop.id = aoc.ai_ocr_prompt_id
                WHERE aoc.image_id = %s
                ORDER BY aoc.created_at DESC
            """
            
            self.cursor.execute(query, [int(image_id)])
            rows = self.cursor.fetchall()
            
            # Format results to match expected structure
            formatted_results = []
            for row in rows:
                formatted_row = dict(row)
                # Add prompt info if available
                if row.get('prompt_id_prompt'):
                    formatted_row['ai_ocr_prompt'] = {
                        'id': row.get('prompt_id_prompt'),
                        'categorie_id': row.get('prompt_categorie_id')
                    }
                # Remove the joined fields
                formatted_row.pop('prompt_id_prompt', None)
                formatted_row.pop('prompt_categorie_id', None)
                formatted_results.append(formatted_row)
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error fetching AI OCR content by image_id: {e}")
            return []

    def getAiOcrContentByPromptId(self, ai_ocr_prompt_id):
        """
        Get all AI OCR content for a specific prompt
        
        Args:
            ai_ocr_prompt_id: The prompt ID
            
        Returns:
            list: List of content records with related image information
        """
        try:
            query = """
                SELECT 
                    aoc.*,
                    i.id as image_id_img,
                    i.nom as image_nom
                FROM ai_ocr_content aoc
                LEFT JOIN image i ON i.id = aoc.image_id
                WHERE aoc.ai_ocr_prompt_id = %s
                ORDER BY aoc.created_at DESC
            """
            
            self.cursor.execute(query, [int(ai_ocr_prompt_id)])
            rows = self.cursor.fetchall()
            
            # Format results to match expected structure
            formatted_results = []
            for row in rows:
                formatted_row = dict(row)
                # Add image info if available
                if row.get('image_id_img'):
                    formatted_row['image'] = {
                        'id': row.get('image_id_img'),
                        'nom': row.get('image_nom')
                    }
                # Remove the joined fields
                formatted_row.pop('image_id_img', None)
                formatted_row.pop('image_nom', None)
                formatted_results.append(formatted_row)
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error fetching AI OCR content by prompt_id: {e}")
            return []

    def createAiOcrContentDocs(self, data):
        """
        Create a new AI OCR content docs
        
        Args:
            data (dict): Dictionary with keys:
                - image_id: The image ID (required)
                - content: The content text (optional)
                
        Returns:
            dict: Created content with related information
            
        Raises:
            Exception: If image not found or prompt not found (if provided)
        """
        try:
            logger.info(f"Creating AI OCR content docs")
            image_id = data.get('image_id')
            content = data.get('content')
            # Insert the new content
            insert_query = """
                INSERT INTO ai_ocr_content_docs 
                    (content, image_id, created_at, categorie_id, status, json_data)
                VALUES (%s, %s, NOW(), %s, %s, %s)
            """
            
            self.cursor.execute(insert_query, [
                content if content else None,
                int(image_id),
                data.get("categorie_id"),
                data.get("status"),
                data.get("json_data", "{}")
            ])
            self.connection.commit()
            logger.info(f"AI OCR content docs created")
            # Get the created content with related info
            inserted_id = self.cursor.lastrowid
            return inserted_id
        
        except Exception as e:
            logger.error(f"Error creating AI OCR content docs: {e}")
            self.connection.rollback()
            raise

    def updateAiOcrContent(self, id, data):
        """
        Update an existing AI OCR content
        
        Args:
            id: The content ID
            data (dict): Dictionary with keys to update:
                - content: The content text (optional)
                - image_id: The image ID (optional)
                - ai_ocr_prompt_id: The prompt ID (optional)
                
        Returns:
            dict: Updated content with related information
            
        Raises:
            Exception: If content not found, image not found, or prompt not found
        """
        try:
            # Verify that the content exists
            existing_content = self.getAiOcrContentById(id)
            if not existing_content:
                raise Exception('Content not found')
            
            # If image_id is provided, verify it exists
            if 'image_id' in data and data['image_id'] is not None:
                image_check_query = "SELECT id FROM image WHERE id = %s"
                self.cursor.execute(image_check_query, [int(data['image_id'])])
                image = self.cursor.fetchone()
                
                if not image:
                    raise Exception('Image not found')
            
            # If ai_ocr_prompt_id is provided, verify it exists
            if 'ai_ocr_prompt_id' in data and data['ai_ocr_prompt_id'] is not None:
                prompt_check_query = "SELECT id FROM ai_ocr_prompts WHERE id = %s"
                self.cursor.execute(prompt_check_query, [int(data['ai_ocr_prompt_id'])])
                prompt = self.cursor.fetchone()
                
                if not prompt:
                    raise Exception('AI OCR prompt not found')
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            if 'content' in data:
                update_fields.append("content = %s")
                params.append(data['content'] if data['content'] else None)
            
            if 'image_id' in data:
                update_fields.append("image_id = %s")
                params.append(int(data['image_id']))
            
            if 'ai_ocr_prompt_id' in data:
                update_fields.append("ai_ocr_prompt_id = %s")
                params.append(int(data['ai_ocr_prompt_id']) if data['ai_ocr_prompt_id'] else None)
            
            if not update_fields:
                # No fields to update, return existing content
                return existing_content
            
            params.append(int(id))
            
            update_query = f"""
                UPDATE ai_ocr_content 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            self.cursor.execute(update_query, params)
            self.connection.commit()
            
            # Get the updated content with related info
            return self.getAiOcrContentById(id)
        
        except Exception as e:
            logger.error(f"Error updating AI OCR content: {e}")
            self.connection.rollback()
            raise

    def deleteAiOcrContent(self, id):
        """
        Delete an AI OCR content
        
        Args:
            id: The content ID
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            Exception: If content not found
        """
        try:
            # Verify that the content exists
            existing_content = self.getAiOcrContentById(id)
            if not existing_content:
                raise Exception('Content not found')
            
            delete_query = "DELETE FROM ai_ocr_content WHERE id = %s"
            self.cursor.execute(delete_query, [int(id)])
            self.connection.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting AI OCR content: {e}")
            self.connection.rollback()
            raise

