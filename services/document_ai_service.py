import os
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_v1 import DocumentProcessorServiceAsyncClient
from typing import Dict, List, Optional, Union
from services.logger import Logger

class DocumentAI(documentai.DocumentProcessorServiceClient):
    def __init__(self):
        # Initialize the client with credentials from environment variable
        super().__init__(
            client_options={
                "credentials_file": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            }
        )
        
        self.project_id = os.getenv("GOOGLE_PROJECT_ID")
        self.location = os.getenv("GOOGLE_LOCATION")  # Note: Typo in original JS code (LOCATION vs LOCATION)
        self.processor_id = os.getenv("GOOGLE_PROCESSOR_ID")
        
        if not self.project_id or not self.location or not self.processor_id:
            raise ValueError("Missing Document AI configuration. Check environment variables.")
        
        # Initialize logger (you'll need to implement or replace with your preferred logging)
        self.logger = Logger.get_logger()
    
    
    async def document_process_request(self, content: bytes, mime_type: str) -> Optional[dict]: 
        try:
            async_client = DocumentProcessorServiceAsyncClient()
            name = f"projects/{self.project_id}/locations/{self.location}/processors/{self.processor_id}"
            
            request = documentai.ProcessRequest(
                name=name,
                raw_document=documentai.RawDocument(
                    content=content,
                    mime_type=mime_type
                )
            )
            
            self.logger.info("debut extraction des données avec google document ai")
            result = await async_client.process_document(request=request)
            document = result.document
            self.logger.info("fin extraction des données avec google document ai")
            return document
        except Exception as error:
            self.logger.error(f"Error processing document: {error}")
            return None
    
    def extract_form_fields(self, document: dict) -> Dict[str, str]:
        try:
            self.logger.info("debut extraction des fields avec google document ai")
            fields = {}
            
            if not document or "pages" not in document:
                return fields
            
            for page in document.pages:
                if "formFields" not in page:
                    continue
                
                for field in page.formFields:
                    field_name = self.get_text(field.fieldName.textAnchor, document.text)
                    field_value = self.get_text(field.fieldValue.textAnchor, document.text)
                    
                    if field_name and field_value:
                        fields[field_name] = field_value
            
            self.logger.info("fin extraction des fields avec google document ai")
            return fields
        except Exception as error:
            self.logger.error(f"Error extracting form fields: {error}")
            return {}
    
    def get_table_data(self, table: dict, text: str) -> List[dict]:
        headers = []
        rows = []
        
        # Get headers
        if "headerRows" in table and table.headerRows:
            for header_cell in table.headerRows[0].cells:
                header_cell_text = self.get_text(header_cell.layout.textAnchor, text).strip()
                headers.append(header_cell_text)
        
        # Get all rows data
        if "bodyRows" in table and table.bodyRows:
            for body_row in table.bodyRows:
                row_data = {}
                if "cells" in body_row:
                    for index, cell in enumerate(body_row.cells):
                        if index >= len(headers):
                            continue
                        cell_text = self.get_text(cell.layout.textAnchor, text).strip()
                        row_data[headers[index]] = cell_text
                rows.append(row_data)
        
        return rows
    
    def get_text(self, text_anchor: dict, text: str) -> str:
        if not text_anchor or "textSegments" not in text_anchor or not text_anchor.textSegments:
            return "NAN"
        
        # First shard in document doesn't have startIndex property
        first_segment = text_anchor.textSegments[0]
        start_index = first_segment.get("startIndex", 0)
        end_index = first_segment.get("endIndex", 0)
        
        return text[start_index:end_index]
    
    def get_text_from_text_anchor(self, page: dict, document: dict) -> str:
        page_text = ""
        if "paragraphs" not in page:
            return page_text
        
        for paragraph in page.paragraphs:
            if "layout" not in paragraph or "textAnchor" not in paragraph.layout:
                continue
            
            text_anchor = paragraph.layout.textAnchor
            if "textSegments" not in text_anchor or not text_anchor.textSegments:
                continue
            
            # Extract text for this paragraph
            first_segment = text_anchor.textSegments[0]
            start_index = first_segment.get("startIndex", 0)
            end_index = first_segment.get("endIndex", 0)
            page_text += f"{document.text[start_index:end_index]}\n"
        
        return page_text.strip()
    
    def extract_data_table(self, document: dict) -> List[dict]:
        data_table = []
        self.logger.info("debut extraction des données table avec google document ai")
        
        if not document or "pages" not in document:
            return data_table
        
        self.logger.info(f"document.pages length {len(document.pages)}")
        
        for page in document.pages:
            if "tables" not in page:
                continue
            
            page_data = {
                "data": [],
                "pageText": ""
            }
            
            for table in page.tables:
                table_data = self.get_table_data(table, document.text)
                page_data["data"].extend(table_data)
            
            page_text = self.get_text_from_text_anchor(page, document)
            page_data["pageText"] = page_text
            
            data_table.append(page_data)
        
        self.logger.info("fin extraction des données table avec google document ai")
        return data_table