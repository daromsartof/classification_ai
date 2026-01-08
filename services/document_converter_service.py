"""
Service de conversion de documents vers les formats acceptés par OpenAI Vision.

Ce module gère la conversion de différents formats de documents (PDF, images, etc.)
vers PDF ou JPG, formats acceptés par l'API OpenAI Vision.
"""

import base64
import os
from pathlib import Path
from typing import Optional, Tuple

from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter

from services.logger import Logger

logger = Logger.get_logger()


class DocumentConverterService:
    """
    Service de conversion de documents vers PDF ou JPG.
    
    Convertit différents formats de documents (PDF, images) vers les formats
    acceptés par OpenAI Vision (PDF ou JPG).
    """
    
    # Formats acceptés par OpenAI Vision
    ACCEPTED_FORMATS = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp']
    
    # Formats d'images supportés
    IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp']
    
    def __init__(self, upload_dir: str = "./uploads", converted_dir: str = "./converted"):
        """
        Initialise le service de conversion.
        
        Args:
            upload_dir: Répertoire pour les fichiers uploadés.
            converted_dir: Répertoire pour les fichiers convertis.
        """
        self.upload_dir = upload_dir
        self.converted_dir = converted_dir
        
        # Création des répertoires si nécessaire
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(converted_dir, exist_ok=True)

    def get_file_extension(self, filename: str) -> str:
        """
        Récupère l'extension d'un fichier.
        
        Args:
            filename: Nom du fichier.
            
        Returns:
            Extension du fichier en minuscules (sans le point).
        """
        return Path(filename).suffix.lower().lstrip('.')

    def is_pdf(self, file_path: str) -> bool:
        """
        Vérifie si un fichier est un PDF.
        
        Args:
            file_path: Chemin vers le fichier.
            
        Returns:
            True si le fichier est un PDF.
        """
        return self.get_file_extension(file_path) == 'pdf'

    def is_image(self, file_path: str) -> bool:
        """
        Vérifie si un fichier est une image.
        
        Args:
            file_path: Chemin vers le fichier.
            
        Returns:
            True si le fichier est une image.
        """
        ext = self.get_file_extension(file_path)
        return ext in self.IMAGE_FORMATS

    def get_pdf_page_count(self, file_path: str) -> int:
        """
        Obtient le nombre de pages d'un PDF.
        
        Args:
            file_path: Chemin vers le fichier PDF.
            
        Returns:
            Nombre de pages du PDF.
        """
        try:
            reader = PdfReader(file_path)
            return len(reader.pages)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du PDF: {e}")
            return 0

    def extract_first_and_last_pages_pdf(
        self,
        file_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Extrait la première et la dernière page d'un PDF multipage.
        
        Args:
            file_path: Chemin vers le fichier PDF source.
            output_path: Chemin de sortie (optionnel).
            
        Returns:
            Chemin vers le fichier PDF avec seulement première et dernière page.
        """
        if not output_path:
            base_name = Path(file_path).stem
            output_path = os.path.join(
                self.converted_dir,
                f"{base_name}_first_last.pdf"
            )
        
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            
            # Si le PDF a une seule page, on le copie tel quel
            if num_pages <= 1:
                import shutil
                shutil.copy2(file_path, output_path)
                return output_path
            
            # Création d'un nouveau PDF avec première et dernière page
            writer = PdfWriter()
            
            # Ajout de la première page (index 0)
            writer.add_page(reader.pages[0])
            
            # Ajout de la dernière page (index num_pages - 1)
            writer.add_page(reader.pages[num_pages - 1])
            
            # Sauvegarde du nouveau PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info(f"PDF réduit à première et dernière page: {output_path} (original: {num_pages} pages)")
            return output_path
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des pages: {e}")
            raise ValueError(f"Impossible d'extraire les pages du PDF: {e}")

    def convert_to_pdf(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Convertit un fichier en PDF.
        Pour les PDFs multipages, extrait seulement la première et dernière page.
        
        Args:
            file_path: Chemin vers le fichier source.
            output_path: Chemin de sortie (optionnel).
            
        Returns:
            Chemin vers le fichier PDF converti.
            
        Raises:
            ValueError: Si le format n'est pas supporté.
        """
        if self.is_pdf(file_path):
            # Vérification si le PDF est multipage
            num_pages = self.get_pdf_page_count(file_path)
            
            if num_pages > 1:
                # PDF multipage: extraction de première et dernière page
                return self.extract_first_and_last_pages_pdf(file_path, output_path)
            else:
                # PDF d'une seule page, on le copie
                if output_path:
                    import shutil
                    shutil.copy2(file_path, output_path)
                    return output_path
                return file_path
        
        if self.is_image(file_path):
            # Conversion image -> PDF
            if not output_path:
                base_name = Path(file_path).stem
                output_path = os.path.join(
                    self.converted_dir,
                    f"{base_name}.pdf"
                )
            
            try:
                image = Image.open(file_path)
                # Conversion en RGB si nécessaire
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                image.save(output_path, 'PDF', resolution=300.0)
                image.close()
                
                logger.info(f"Image convertie en PDF: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Erreur lors de la conversion image -> PDF: {e}")
                raise ValueError(f"Impossible de convertir l'image en PDF: {e}")
        
        raise ValueError(f"Format non supporté pour la conversion en PDF: {file_path}")

    def convert_to_jpg(
        self,
        file_path: str,
        output_path: Optional[str] = None,
        quality: int = 90
    ) -> str:
        """
        Convertit un fichier en JPG.
        
        Args:
            file_path: Chemin vers le fichier source.
            output_path: Chemin de sortie (optionnel).
            quality: Qualité de compression JPEG (0-100).
            
        Returns:
            Chemin vers le fichier JPG converti.
            
        Raises:
            ValueError: Si le format n'est pas supporté.
        """
        if self.is_pdf(file_path):
            # Conversion PDF -> JPG (première et dernière page si multipage)
            if not output_path:
                base_name = Path(file_path).stem
                output_path = os.path.join(
                    self.converted_dir,
                    f"{base_name}.jpg"
                )
            
            try:
                num_pages = self.get_pdf_page_count(file_path)
                
                if num_pages > 1:
                    # PDF multipage: extraction de première et dernière page
                    # Conversion de la première page
                    first_page_images = convert_from_path(file_path, dpi=300, first_page=1, last_page=1)
                    # Conversion de la dernière page
                    last_page_images = convert_from_path(file_path, dpi=300, first_page=num_pages, last_page=num_pages)
                    
                    if not first_page_images or not last_page_images:
                        raise ValueError("Impossible d'extraire les pages du PDF")
                    
                    # Conversion en RGB si nécessaire
                    first_image = first_page_images[0]
                    last_image = last_page_images[0]
                    
                    if first_image.mode != 'RGB':
                        first_image = first_image.convert('RGB')
                    if last_image.mode != 'RGB':
                        last_image = last_image.convert('RGB')
                    
                    # Combinaison des deux images verticalement
                    # Calcul de la largeur maximale pour les deux images
                    max_width = max(first_image.width, last_image.width)
                    total_height = first_image.height + last_image.height
                    
                    # Création d'une nouvelle image combinée
                    combined_image = Image.new('RGB', (max_width, total_height))
                    combined_image.paste(first_image, (0, 0))
                    combined_image.paste(last_image, (0, first_image.height))
                    
                    combined_image.save(output_path, 'JPEG', quality=quality)
                    
                    # Nettoyage
                    first_image.close()
                    last_image.close()
                    combined_image.close()
                    
                    logger.info(f"PDF multipage converti en JPG (première et dernière page): {output_path}")
                else:
                    # PDF d'une seule page
                    images = convert_from_path(file_path, dpi=300, first_page=1, last_page=1)
                    
                    if not images:
                        raise ValueError("Aucune page extraite du PDF")
                    
                    # Conversion en RGB si nécessaire
                    image = images[0]
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    image.save(output_path, 'JPEG', quality=quality)
                    image.close()
                    
                    logger.info(f"PDF converti en JPG: {output_path}")
                
                return output_path
            except Exception as e:
                logger.error(f"Erreur lors de la conversion PDF -> JPG: {e}")
                raise ValueError(f"Impossible de convertir le PDF en JPG: {e}")
        
        if self.is_image(file_path):
            # Conversion image -> JPG
            if not output_path:
                base_name = Path(file_path).stem
                output_path = os.path.join(
                    self.converted_dir,
                    f"{base_name}.jpg"
                )
            
            try:
                image = Image.open(file_path)
                # Conversion en RGB si nécessaire
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                image.save(output_path, 'JPEG', quality=quality)
                image.close()
                
                logger.info(f"Image convertie en JPG: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Erreur lors de la conversion image -> JPG: {e}")
                raise ValueError(f"Impossible de convertir l'image en JPG: {e}")
        
        raise ValueError(f"Format non supporté pour la conversion en JPG: {file_path}")

    def convert_for_openai_vision(
        self,
        file_path: str,
        prefer_format: str = 'jpg'
    ) -> Tuple[str, str]:
        """
        Convertit un document pour OpenAI Vision (PDF ou JPG).
        Pour les documents multipages, extrait seulement la première et dernière page.
        
        Args:
            file_path: Chemin vers le fichier source.
            prefer_format: Format préféré ('pdf' ou 'jpg').
            
        Returns:
            Tuple contenant:
                - Chemin vers le fichier converti
                - Format du fichier ('pdf' ou 'jpg')
        """
        ext = self.get_file_extension(file_path)
        
        # Si déjà un PDF, vérifier s'il est multipage et extraire première/dernière page
        if ext == 'pdf':
            num_pages = self.get_pdf_page_count(file_path)
            if num_pages > 1:
                # PDF multipage: extraction de première et dernière page
                if prefer_format == 'pdf':
                    # Garder en PDF mais avec seulement première et dernière page
                    converted_path = self.extract_first_and_last_pages_pdf(file_path)
                    return converted_path, 'pdf'
                else:
                    # Convertir en JPG avec première et dernière page
                    converted_path = self.convert_to_jpg(file_path)
                    return converted_path, 'jpg'
            else:
                # PDF d'une seule page, pas besoin de conversion
                return file_path, 'pdf'
        
        # Si déjà une image JPG/JPEG, pas besoin de conversion
        if ext in ['jpg', 'jpeg']:
            return file_path, 'jpg'
        
        # Conversion selon le format préféré
        if prefer_format == 'pdf':
            converted_path = self.convert_to_pdf(file_path)
            return converted_path, 'pdf'
        else:
            converted_path = self.convert_to_jpg(file_path)
            return converted_path, 'jpg'

    def get_file_base64(self, file_path: str) -> Tuple[str, str]:
        """
        Convertit un fichier en base64 pour l'API OpenAI Vision.
        
        Args:
            file_path: Chemin vers le fichier.
            
        Returns:
            Tuple contenant:
                - Contenu du fichier encodé en base64
                - Type MIME du fichier
        """
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Détermination du type MIME
        ext = self.get_file_extension(file_path)
        if ext == 'pdf':
            mime_type = 'application/pdf'
        elif ext in ['jpg', 'jpeg']:
            mime_type = 'image/jpeg'
        elif ext == 'png':
            mime_type = 'image/png'
        elif ext == 'gif':
            mime_type = 'image/gif'
        elif ext == 'webp':
            mime_type = 'image/webp'
        else:
            mime_type = 'application/octet-stream'
        
        return base64_content, mime_type

