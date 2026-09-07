from PIL import Image

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from models import Branch


TARGET_PERCENTAGE = 0.6
TATISHEVA_KEYWORDS = ['татищева', '10ат', '10ат', '5ат', '7ат', 'панькова']
KRUPSKOY_KEYWORDS = ['10а', '9а', 'глухова', 'химия153', 'антуфьева', 'гамза', 'куликова', 'гасанова', 'аникина', 'белякова']


def ocr(image) -> str:
    return pytesseract.image_to_string(image, lang='rus')


def is_target(text: str, branch: Branch):
    keywords_set = TATISHEVA_KEYWORDS if branch == Branch.TATISHEVA else KRUPSKOY_KEYWORDS
    matches = sum(1 for kwrd in keywords_set if kwrd in text.lower().replace(' ', ''))
    return matches / len(keywords_set) >= TARGET_PERCENTAGE


if __name__ == '__main__':
    parsed = pytesseract.image_to_string(Image.open('test.jpg'), lang='rus')
    print(is_target(parsed, Branch.TATISHEVA))
