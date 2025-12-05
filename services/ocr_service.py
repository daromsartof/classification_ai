import cv2
import numpy as np
import pytesseract
import logging
import uuid

from services.logger import Logger

logger = Logger.get_logger()


class OCRService:
    
    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """Apply denoising to reduce image noise"""
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    
    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Deskew image to correct rotation"""
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        if abs(angle) < 0.5:  # Skip if nearly straight
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), 
                                 flags=cv2.INTER_CUBIC, 
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated
    
    @staticmethod
    def enhance_contrast(image: np.ndarray) -> np.ndarray:
        """Apply CLAHE for contrast enhancement"""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    
    @staticmethod
    def remove_borders(image: np.ndarray) -> np.ndarray:
        """Remove black borders around the image"""
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cnt = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(cnt)
            return image[y:y+h, x:x+w]
        return image
    
    @staticmethod
    def sharpen_image(image: np.ndarray) -> np.ndarray:
        """Apply unsharp masking for better text clarity"""
        gaussian = cv2.GaussianBlur(image, (0, 0), 3)
        return cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    
    @staticmethod
    def adaptive_threshold(image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding"""
        return cv2.adaptiveThreshold(
            image, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            10, 1
        )
    
    @staticmethod
    def morphological_operations(image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up text"""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
    
    def preprocess_pipeline(self, image: np.ndarray, strategy: str = 'balanced') -> np.ndarray:
        """
        Apply preprocessing pipeline based on strategy
        
        Args:
            image: Input image
            strategy: 'light', 'balanced', 'aggressive'
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        if strategy == 'light':
            # Minimal processing for clean documents
            return gray
            gray = self.enhance_contrast(gray)
            gray = self.sharpen_image(gray)
           
            
        elif strategy == 'balanced':
            # Standard processing for most documents
            gray = self.denoise(gray)
            gray = self.enhance_contrast(gray)
            gray = self.sharpen_image(gray)
            return self.adaptive_threshold(gray)
            
        elif strategy == 'aggressive':
            # Heavy processing for degraded documents
            gray = self.denoise(gray)
            gray = self.remove_borders(gray)
            gray = self.enhance_contrast(gray)
            gray = self.sharpen_image(gray)
            thresh = self.adaptive_threshold(gray)
            return self.morphological_operations(thresh)
        
        return gray
    
    def extract_text_with_config(self, image: np.ndarray, lang: str = 'eng+fra', 
                                 psm: int = 6, oem: int = 3) -> str:
        """
        Extract text with specific Tesseract configuration
        
        PSM modes:
        0 = Orientation and script detection only
        3 = Fully automatic page segmentation (default)
        6 = Uniform block of text
        11 = Sparse text
        
        OEM modes:
        0 = Legacy engine only
        1 = Neural nets LSTM engine only
        2 = Legacy + LSTM engines
        3 = Default (best available)
        """
        config = f'--oem {oem} --psm {psm}'
        return pytesseract.image_to_string(image, lang=lang, config=config)
    
    def ocr_extraction(self, image, config):
        preprocessed = self.preprocess_pipeline(image, config['strategy'])
        text = self.extract_text_with_config(
            preprocessed, 
            lang=config.get('lang', 'eng+fra'),
            psm=config.get('psm', 6),
            oem=config.get('oem', 3)
        )
        # Save preprocessed image
        #img_file = uuid.uuid4()
        
       # cv2.imwrite(str(f"outputs/{img_file}.png"), preprocessed)
        #with open(str(f"outputs/{img_file}.txt"), 'w', encoding='utf-8') as file:
         #   file.write(text)
        return text
    
    def extract_from_image(self, image_path: str) -> dict:
        """
        Main extraction method with optimized preprocessing
        
        Returns:
            Dictionary containing extraction results from different strategies
        """
        logger.info(f"Reading image: {image_path}")
        image = cv2.imread(image_path)
        
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Define multiple extraction strategies
        config = {
                'name': 'light_psm3',
                'strategy': 'light',
                'psm': 3,  # Uniform block of text
                'oem': 3,
                'lang': 'eng+fra'
        }
        
        
        logger.info("Running parallel OCR extraction...")
        text = self.ocr_extraction(image, config)
        
        return text