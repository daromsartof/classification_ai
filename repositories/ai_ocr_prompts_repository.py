from services.database_service import DatabaseService
from services.logger import Logger

logger = Logger.get_logger()


class AiOcrPromptsRepository:
    def __init__(self):
        self.databse = DatabaseService()
        self.pool = self.databse.get_pool()
        self.connection = self.pool.get_connection()
        self.cursor = self.connection.cursor(dictionary=True)

    def _format_prompt_with_categorie(self, prompt):
        """Format prompt result to include categorie information"""
        if not prompt:
            return None
        
        # If categorie info is already in the result (from JOIN), format it
        if 'categorie_id' in prompt and 'categorie_id_cat' in prompt:
            prompt['categorie'] = {
                'id': prompt.get('categorie_id_cat'),
                'libelle_new': prompt.get('libelle_new')
            }
            # Remove the joined fields to keep structure clean
            prompt.pop('categorie_id_cat', None)
            prompt.pop('libelle_new', None)
        
        return prompt

    def _format_prompts_with_categorie(self, prompts):
        """Format list of prompts to include categorie information"""
        if not prompts:
            return []
        
        formatted = []
        for prompt in prompts:
            formatted_prompt = self._format_prompt_with_categorie(prompt)
            if formatted_prompt:
                formatted.append(formatted_prompt)
        
        return formatted

    def getAllAiOcrPrompts(self, filters=None):
        """
        Get all AI OCR prompts with optional filters
        
        Args:
            filters (dict): Optional filters with keys like 'categorie_id'
            
        Returns:
            list: List of prompts with categorie information
        """
        if filters is None:
            filters = {}
        
        try:
            query = """
                SELECT 
                    aop.*,
                    c.id as categorie_id_cat,
                    c.libelle_new
                FROM ai_ocr_prompts aop
                LEFT JOIN categorie c ON c.id = aop.categorie_id
            """
            
            where_clauses = []
            params = []
            
            if filters.get('categorie_id'):
                where_clauses.append("aop.categorie_id = %s")
                params.append(int(filters['categorie_id']))
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY aop.created_at DESC"
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            # Format results to match expected structure
            formatted_results = []
            for row in rows:
                formatted_row = dict(row)
                formatted_row['categorie'] = {
                    'id': row.get('categorie_id_cat'),
                    'libelle_new': row.get('libelle_new')
                }
                # Remove the joined fields
                formatted_row.pop('categorie_id_cat', None)
                formatted_row.pop('libelle_new', None)
                formatted_results.append(formatted_row)
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error fetching all AI OCR prompts: {e}")
            return []

    def getAiOcrPromptsByCategorie(self, categorie_id):
        """
        Get all AI OCR prompts for a specific categorie
        
        Args:
            categorie_id: The categorie ID
            
        Returns:
            list: List of prompts with categorie information
        """
        try:
            query = """
                SELECT 
                    aop.*,
                    c.id as categorie_id_cat,
                    c.libelle_new
                FROM ai_ocr_prompts aop
                LEFT JOIN categorie c ON c.id = aop.categorie_id
                WHERE aop.categorie_id = %s
                ORDER BY aop.created_at DESC LIMIT 1
            """
            self.cursor.execute(query, [int(categorie_id)])
            rows = self.cursor.fetchall()
            
            # Format results to match expected structure
            formatted_results = []
            for row in rows:
                formatted_row = dict(row)
                formatted_row['categorie'] = {
                    'id': row.get('categorie_id_cat'),
                    'libelle_new': row.get('libelle_new')
                }
                # Remove the joined fields
                formatted_row.pop('categorie_id_cat', None)
                formatted_row.pop('libelle_new', None)
                formatted_results.append(formatted_row)
            
            if len(formatted_results) > 0:
                return formatted_results[0]
            else:
                return None
        
        except Exception as e:
            logger.error(f"Error fetching AI OCR prompts by categorie: {e}")
            return None

    def getAiOcrPromptById(self, id):
        """
        Get a single AI OCR prompt by ID
        
        Args:
            id: The prompt ID
            
        Returns:
            dict: Prompt with categorie information or None if not found
        """
        try:
            query = """
                SELECT 
                    aop.*,
                    c.id as categorie_id_cat,
                    c.libelle_new
                FROM ai_ocr_prompts aop
                LEFT JOIN categorie c ON c.id = aop.categorie_id
                WHERE aop.id = %s
            """
            
            self.cursor.execute(query, [int(id)])
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            # Format result to match expected structure
            formatted_row = dict(row)
            formatted_row['categorie'] = {
                'id': row.get('categorie_id_cat'),
                'libelle_new': row.get('libelle_new')
            }
            # Remove the joined fields
            formatted_row.pop('categorie_id_cat', None)
            formatted_row.pop('libelle_new', None)
            
            return formatted_row
        
        except Exception as e:
            logger.error(f"Error fetching AI OCR prompt by id: {e}")
            return None

    def createAiOcrPrompt(self, data):
        """
        Create a new AI OCR prompt
        
        Args:
            data (dict): Dictionary with keys:
                - categorie_id: The categorie ID (required)
                - ai_prompt_classification: Classification prompt (optional)
                - ai_prompt_extract_content: Content extraction prompt (optional)
                
        Returns:
            dict: Created prompt with categorie information
            
        Raises:
            Exception: If categorie not found
        """
        try:
            categorie_id = data.get('categorie_id')
            ai_prompt_classification = data.get('ai_prompt_classification')
            ai_prompt_extract_content = data.get('ai_prompt_extract_content')
            
            # Verify that the categorie exists
            categorie_check_query = "SELECT id FROM categorie WHERE id = %s"
            self.cursor.execute(categorie_check_query, [int(categorie_id)])
            categorie = self.cursor.fetchone()
            
            if not categorie:
                raise Exception('Categorie not found')
            
            # Insert the new prompt
            insert_query = """
                INSERT INTO ai_ocr_prompts 
                    (categorie_id, ai_prompt_classification, ai_prompt_extract_content, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
            """
            
            self.cursor.execute(insert_query, [
                int(categorie_id),
                ai_prompt_classification if ai_prompt_classification else None,
                ai_prompt_extract_content if ai_prompt_extract_content else None
            ])
            self.connection.commit()
            
            # Get the created prompt with categorie info
            inserted_id = self.cursor.lastrowid
            return self.getAiOcrPromptById(inserted_id)
        
        except Exception as e:
            logger.error(f"Error creating AI OCR prompt: {e}")
            self.connection.rollback()
            raise

    def updateAiOcrPrompt(self, id, data):
        """
        Update an existing AI OCR prompt
        
        Args:
            id: The prompt ID
            data (dict): Dictionary with keys to update:
                - categorie_id: The categorie ID (optional)
                - ai_prompt_classification: Classification prompt (optional)
                - ai_prompt_extract_content: Content extraction prompt (optional)
                
        Returns:
            dict: Updated prompt with categorie information
            
        Raises:
            Exception: If prompt not found or categorie not found
        """
        try:
            # Verify that the prompt exists
            existing_prompt = self.getAiOcrPromptById(id)
            if not existing_prompt:
                raise Exception('Prompt not found')
            
            # If categorie_id is provided, verify it exists
            if 'categorie_id' in data and data['categorie_id'] is not None:
                categorie_check_query = "SELECT id FROM categorie WHERE id = %s"
                self.cursor.execute(categorie_check_query, [int(data['categorie_id'])])
                categorie = self.cursor.fetchone()
                
                if not categorie:
                    raise Exception('Categorie not found')
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            if 'categorie_id' in data:
                update_fields.append("categorie_id = %s")
                params.append(int(data['categorie_id']))
            
            if 'ai_prompt_classification' in data:
                update_fields.append("ai_prompt_classification = %s")
                params.append(data['ai_prompt_classification'] if data['ai_prompt_classification'] else None)
            
            if 'ai_prompt_extract_content' in data:
                update_fields.append("ai_prompt_extract_content = %s")
                params.append(data['ai_prompt_extract_content'] if data['ai_prompt_extract_content'] else None)
            
            # Always update updated_at
            update_fields.append("updated_at = NOW()")
            
            if not update_fields:
                # No fields to update, return existing prompt
                return existing_prompt
            
            params.append(int(id))
            
            update_query = f"""
                UPDATE ai_ocr_prompts 
                SET {', '.join(update_fields)}
                WHERE id = %s
            """
            
            self.cursor.execute(update_query, params)
            self.connection.commit()
            
            # Get the updated prompt with categorie info
            return self.getAiOcrPromptById(id)
        
        except Exception as e:
            logger.error(f"Error updating AI OCR prompt: {e}")
            self.connection.rollback()
            raise

    def deleteAiOcrPrompt(self, id):
        """
        Delete an AI OCR prompt
        
        Args:
            id: The prompt ID
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            Exception: If prompt not found
        """
        try:
            # Verify that the prompt exists
            existing_prompt = self.getAiOcrPromptById(id)
            if not existing_prompt:
                raise Exception('Prompt not found')
            
            delete_query = "DELETE FROM ai_ocr_prompts WHERE id = %s"
            self.cursor.execute(delete_query, [int(id)])
            self.connection.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting AI OCR prompt: {e}")
            self.connection.rollback()
            raise

