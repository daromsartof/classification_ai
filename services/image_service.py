import os
from dotenv import load_dotenv
from services.document_ai_service import DocumentAI
from typing import Optional
import base64
from datetime import datetime
import shutil
from pathlib import Path
load_dotenv()

from services.logger import Logger

logger = Logger.get_logger()

class ImageService:
    def __init__(self):
        self.IMAGE_A_TRAITER = os.getenv('IMAGE_A_TRAITER', r'//NAS/intranet images/IMAGES_A_TRAITER') 
        self.OLD_IMAGE_A_TRAITER = os.getenv('OLD_IMAGE_A_TRAITER', r'//NAS/intranet images/NS_SU/IMAGES_A_TRAITER')
        self.document_ai = DocumentAI()
        # Add these properties that seem to be used in the JavaScript version
        self.allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tiff', '.tif']
    
    def get_image_path(self, img, ext="pdf", output_path=""):
        """
        Get image paths
        """
        # Parse the scan date
        date_scan = datetime.fromisoformat(img['date_scan'].replace('Z', '+00:00')) if isinstance(img['date_scan'], str) else img['date_scan']
        year = str(date_scan.year)
        month = str(date_scan.month).zfill(2)
        day = str(date_scan.day).zfill(2)
        logger.info(f"IMAGE_A_TRAITER {self.IMAGE_A_TRAITER}")
        # Build the folder source path
        folder_source_path = Path(self.IMAGE_A_TRAITER) / img['client_nom'] / img['dossier_nom'] / str(img['exercice']) / f'{year}-{month}-{day}' / str(img['lot_num'])
        
        # Build the source file path
        source_path = folder_source_path / f"{img['name']}.{ext}"
        output_path = Path(output_path)
        #print("output_path / ", Path(output_path))
        try:
            source_path.stat()
            return source_path
        except Exception as e:
            try: 
                # Try other allowed extensions
                folder_source_path = Path(self.OLD_IMAGE_A_TRAITER) / img['client_nom'] / img['dossier_nom'] / str(img['exercice']) / f'{year}-{month}-{day}' / str(img['lot_num'])
                source_path = folder_source_path / f"{img['name']}.{ext}"
                source_path.stat()
                return source_path
            except Exception as e:
                try:
                    source_path = output_path / f"{img['name']}.{ext}"
                    #print("here ", source_path)
                    source_path.stat()
                    return  source_path
                except Exception as e: 
                    raise Exception(f"File not found: {source_path}") 
                
    
    async def process_pdf(self, source_path: str) -> tuple[Optional[str], Optional[int]]:
        """
        Process a PDF file using Document AI and return the extracted text and number of pages
        
        Args:
            source_path: Path to the PDF file to process
        
        Returns:
            tuple: (extracted_text, page_count) or (None, None) if processing fails
        """
        try:
            # Read the file content as bytes
            with open(source_path, 'rb') as f:
                content = f.read()
            
            # Process the document
            document = await self.document_ai.document_process_request(
                content=content,
                mime_type='application/pdf'
            )
            
            if document:
                text = document.text
                pages_length = len(document.pages) if hasattr(document, 'pages') else 0
                return text, pages_length
        
        except Exception as e:
            logger.error(f"Error processing PDF {source_path}: {str(e)}")
        
        return None, None
    
    async def process_image_file(self, image_path: str) -> dict:
        """
        Process an image file using Document AI
        
        Args:
            image_path: Path to the image file (JPEG, PNG, etc.)
        
        Returns:
            The processed document object or None if processing fails
        """
        try:
            # Read the file content as bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Convert to base64
            base64_encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            logger.info(f"debut traitement {image_path}")
            
            # Process the document
            document = await self.document_ai.document_process_request(
                content=base64_encoded_image,
                mime_type='image/jpeg'  # or appropriate mime type for your image
            )
            
            logger.info(f"fin traitement {image_path}")
            return document
        
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return None
        
    def copy_the_image(self, image, destination_path: str) -> bool:
        """
        Copy an image from source to destination
        
        Args:
            source_path: Path to the source image file
            destination_path: Path to the destination image file
        Returns:
            bool: True if copy is successful, False otherwise
        """
        copy_attempts = 0
        max_attempts = 5
        last_error = None
            
        while copy_attempts < max_attempts:
            try:
                source_path = image["path"]
                shutil.copy2(source_path, destination_path)
                last_error = None
                break
            except PermissionError as e:
                last_error = e
            except OSError as e:
                # Handle WinError 32 (file in use) and similar transient errors
                if getattr(e, 'winerror', None) == 32 or "used by another process" in str(e):
                    last_error = e
                else:
                    raise
            copy_attempts += 1
            time.sleep(0.6)
            
        if last_error is not None:
            logger.error(f"Failed to copy file after {max_attempts} attempts: {last_error}")
            return source_path, False
        Path(destination_path).mkdir(parents=True, exist_ok=True)
        destination_path = Path(destination_path)
        source_path = destination_path / f"{image['name']}.{"pdf"}"
        return source_path, True
    
    def process_child_images(self, child_images: list, output_path: str) -> list:
        """
        Process child images by copying them to the output path
        
        Args:
            child_images: List of child image dictionaries
            output_path: Path to the output directory
        
        Returns:
            List of processed child image dictionaries with updated paths
        """
        processed_images = []
        for child_image in child_images:
            try:
                source_path = self.get_image_path(child_image, ext="pdf", output_path=output_path)
                dest_path, success = self.copy_the_image(child_image, output_path)
                if success:
                    child_image['path'] = str(dest_path)
                    processed_images.append(child_image)
                else:
                    logger.error(f"Failed to copy child image: {child_image['name']}")
            except Exception as e:
                logger.error(f"Error processing child image {child_image['name']}: {str(e)}")
        
        return processed_images