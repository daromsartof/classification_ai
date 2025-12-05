import cv2
import pytesseract
from pytesseract import Output
import imutils 


from services.logger import Logger

logger = Logger.get_logger()

class OpenCvService:
    def get_image_orientation_from_ocr(self, image_path):
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Image not found or cannot be loaded.")

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = pytesseract.image_to_osd(rgb, output_type=Output.DICT)
            return results, image
        except Exception as e:
            logger.error(f"Error inferring orientation with OCR: {e}")
            return None, None
        
    def rotate_image(self, image):
        orientation_info, img = self.get_image_orientation_from_ocr(image)
        if orientation_info and img is not None:
            logger.info(f"Detected orientation: {orientation_info['orientation']}")
            logger.info(f"Rotate by {orientation_info['rotate']} degrees to correct.")

            # Rotate the actual image
            rotated = imutils.rotate_bound(img, angle=orientation_info['rotate'])
            # Save rotated image
            cv2.imwrite(image, rotated)
        else:
            logger.warning("Could not infer orientation from image content.")