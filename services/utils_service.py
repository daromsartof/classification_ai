
import os
import asyncio
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from typing import List, Dict, Union
import sys
from repositories.tiers_repository import TiersRepository
from services.opencv_service import OpenCvService
from services.logger import Logger

logger = Logger.get_logger()
class UtilsService:
    async def convert_pdf_to_images(self, pdf_path, output_dir, options=None):
        try:
            if options is None:
                options = {}

            opencv_service = OpenCvService()

            # Default options
            format = options.get('format', 'jpeg')
            quality = options.get('quality', 90)
            density = options.get('density', 300)

            # A4 dimensions in inches
            A4_WIDTH_INCH = 8.27
            A4_HEIGHT_INCH = 11.69

            # Calculate width and height in pixels
            width = round(A4_WIDTH_INCH * density)
            height = round(A4_HEIGHT_INCH * density)

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            base_name = Path(pdf_path).stem

            # ✅ Convert directly to images in memory (no .ppm files)
            images = convert_from_path(pdf_path, dpi=density, size=(width, height))

            if not images:
                logger.warning("No images were created from the PDF.")
                return "", 0

            # Save the first page (you can extend this for multiple pages)
            new_filename = f"{base_name}.ia.{format}"
            new_path = os.path.join(output_dir, new_filename)

            images[0].save(new_path, format=format.upper(), quality=quality)
            images[0].close()

            # Apply rotation or other post-processing
            opencv_service.rotate_image(new_path)

            return new_path, len(images)

        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return "", 0
        
        
        """
        for index, temp_path in enumerate(images):
            page_number = str(index + 1).zfill(3)
            if len(images) == 1:
                new_filename = f"{base_name}.ia.{format}"
            else:
                new_filename = f"{base_name}_{page_number}.ia.{format}"

            new_path = os.path.join(output_dir, new_filename)
            img = Image.open(temp_path)
            img.save(new_path, format=format.upper(), quality=quality)
            img.close()
            
            renamed_files.append(new_path)
            print(temp_path)
            try:
                os.remove(temp_path)
            except OSError as e:
                print(f"Error deleting temporary file {temp_path}: {e}")
        return renamed_files"""
    
    
    def get_images_from_directory(self, directory: str, allowed_extensions: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf']) -> List[Dict[str, Union[str, int, float]]]:
        logger.info(f"Scanning directory: {directory}")
        images = []

        # Check if directory exists
        if not os.path.exists(directory):
            logger.warning(f"Error: Directory does not exist: {directory}", file=sys.stderr)
            return images

        # Get all files in directory
        try:
            items = os.listdir(directory)
        except Exception as e:
            logger.error(f"Error reading directory {directory}: {e}", file=sys.stderr)
            return images

        logger.info(f"Found {len(items)} items in directory")

        # Process each file
        for item in items:
            file_path = os.path.join(directory, item)
            
            try:
                stat = os.stat(file_path)
            except Exception as e:
                logger.error(f"Error accessing {file_path}: {e}", file=sys.stderr)
                continue

            # If it's a directory, recursively scan it
            if os.path.isdir(file_path):
                logger.warning(f"Found subdirectory: {item}")
                sub_dir_images = self.get_images_from_directory(file_path, allowed_extensions)
                images.extend(sub_dir_images)
            
            # If it's a file with an allowed extension, add it to the images list
            elif os.path.isfile(file_path):
                ext = os.path.splitext(item)[1].lower()
                if ext in allowed_extensions:
                    logger.info(f"Found image file: {item}")
                    images.append({
                        'path': file_path,
                        'name': os.path.splitext(item)[0],
                        'size': stat.st_size,
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime,
                        'relative_path': os.path.relpath(file_path, directory),
                        'extension': ext
                    })
                else:
                    logger.warning(f"Skipping non-image file: {item} (extension: {ext})")

        logger.info(f"Found {len(images)} images in directory {directory}")
        return images
    
    def getFournisseurAndClientsList(self, dossier_id) -> dict[str]:
        tiers_repos = TiersRepository()
        tiers = tiers_repos.get_tiers_by_dossier_id(dossier_id)
        clients = '[ '
        fournisseurs = '[ '
        for tier in tiers:
            if tier.get('type', None) == 1:
                clients += f'{tier.get('intitule', '')}, '
            elif tier.get('type', None) == 0:
                fournisseurs += f'{tier.get('intitule', '')}, '
        fournisseurs += ' ]'
        clients += ' ]'
        return fournisseurs, clients