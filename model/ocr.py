"""
OCR Module for Text Extraction from Images
Uses pytesseract to extract text from uploaded answer sheet images
"""

import os
import pytesseract
from PIL import Image
import numpy as np


# Configure tesseract path (Windows users may need to set this)

# Common Tesseract installation paths on Windows
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\ProgramData\chocolatey\bin\tesseract.exe',
]

# Try to find tesseract executable
tesseract_cmd = None
for path in possible_paths:
    if os.path.exists(path):
        tesseract_cmd = path
        break

# If found, configure pytesseract
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    print(f"Tesseract OCR configured: {tesseract_cmd}")
else:
    print("WARNING: Tesseract OCR not found. Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")


class OCRProcessor:
    """
    A class to handle OCR operations for extracting text from images
    """
    
    def __init__(self, tesseract_cmd=None):
        """
        Initialize the OCR processor
        
        Args:
            tesseract_cmd (str): Path to tesseract executable (optional)
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        print("OCR Processor initialized")
    
    def extract_text(self, image_path):
        """
        Extract text from an image file
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Extracted text from the image
        """
        try:
            # Open the image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            
            # Clean up the extracted text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ""
    
    def extract_text_from_PIL(self, image):
        """
        Extract text from a PIL Image object
        
        Args:
            image: PIL Image object
            
        Returns:
            str: Extracted text from the image
        """
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            
            # Clean up the extracted text
            text = self._clean_text(text)
            
            return text
            
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return ""
    
    def _clean_text(self, text):
        """
        Clean up extracted text
        
        Args:
            text (str): Raw extracted text
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        text = '\n'.join(lines)
        
        return text
    
    def get_text_with_confidence(self, image_path):
        """
        Extract text with confidence scores
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            tuple: (extracted_text, confidence_data)
        """
        try:
            # Open the image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get data with confidence
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            text = self._clean_text(text)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text, avg_confidence
            
        except Exception as e:
            print(f"Error extracting text with confidence: {str(e)}")
            return "", 0.0
    
    def preprocess_image(self, image_path, output_path=None):
        """
        Preprocess image for better OCR results
        
        Args:
            image_path (str): Path to input image
            output_path (str): Path to save preprocessed image (optional)
            
        Returns:
            PIL.Image: Preprocessed image
        """
        try:
            # Open image
            image = Image.open(image_path)
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Increase contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Save if output path provided
            if output_path:
                image.save(output_path)
            
            return image
            
        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            return None


# Global OCR instance
ocr_processor = None


def get_ocr_processor():
    """
    Get or initialize the global OCR processor instance
    
    Returns:
        OCRProcessor: The initialized OCR processor
    """
    global ocr_processor
    if ocr_processor is None:
        ocr_processor = OCRProcessor()
    return ocr_processor


def extract_text_from_image(image_path):
    """
    Convenience function to extract text from an image
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted text
    """
    processor = get_ocr_processor()
    return processor.extract_text(image_path)


if __name__ == "__main__":
    # Test the OCR processor
    print("OCR Processor Test")
    print("="*60)
    print("Note: This test requires an image file to work properly.")
    print("You can add a test image path to test the OCR functionality.")
    
    # Create processor
    processor = OCRProcessor()
    
    # Example of what would happen with an image:
    print("\nOCR processor is ready to use!")
    print("Use extract_text_from_image('path/to/image.jpg') to extract text.")
