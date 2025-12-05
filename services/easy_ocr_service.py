
import easyocr

class EasyOcrService:
    def __init__(self):
        self.reader = easyocr.Reader(['fr'], gpu=True)

    def extract_text(self, image_path: str) -> str:
        result = self.reader.readtext(image_path, detail=0)
        return "\n".join(result)
