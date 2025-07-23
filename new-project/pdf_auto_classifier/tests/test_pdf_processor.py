import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.pdf_processor import PDFProcessor

class TestPDFProcessor(unittest.TestCase):
    def setUp(self):
        self.config = Mock()
        self.config.get.side_effect = lambda key, default=None: {
            'po_detection.keywords': ['注文書', 'PURCHASE ORDER'],
            'po_detection.confidence_threshold': 0.5,
            'processing.ocr_language': 'jpn',
            'processing.max_file_size_mb': 50,
            'processing.max_pages': 5,
            'metadata_extraction.date_patterns': [r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})'],
            'metadata_extraction.order_number_patterns': [r'注文番号[:：]\s*([A-Za-z0-9-]+)'],
            'metadata_extraction.company_patterns': [r'株式会社\s*([^\s\n]+)']
        }.get(key, default)
        
        self.processor = PDFProcessor(self.config)
    
    def test_is_purchase_order_positive(self):
        with patch.object(self.processor, 'extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = "これは注文書です PURCHASE ORDER"
            
            is_po, content = self.processor.is_purchase_order("dummy.pdf")
            
            self.assertTrue(is_po)
            self.assertEqual(content, "これは注文書です PURCHASE ORDER")
    
    def test_is_purchase_order_negative(self):
        with patch.object(self.processor, 'extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = "これは請求書です"
            
            is_po, content = self.processor.is_purchase_order("dummy.pdf")
            
            self.assertFalse(is_po)
    
    def test_extract_metadata(self):
        content = """
        株式会社テスト会社
        注文番号：ABC-123
        2024/01/15
        """
        
        metadata = self.processor.extract_metadata(content)
        
        self.assertEqual(metadata['company'], 'テスト会社')
        self.assertEqual(metadata['order_number'], 'ABC-123')
        self.assertEqual(metadata['date'], '20240115')
    
    def test_extract_date_multiple_formats(self):
        test_cases = [
            ("2024/01/15", "20240115"),
            ("2024-01-15", "20240115"),
            ("15/01/2024", "20240115")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.processor._extract_date(input_text)
                self.assertEqual(result, expected)
    
    def test_extract_order_number(self):
        test_cases = [
            ("注文番号：ABC-123", "ABC-123"),
            ("注文番号: XYZ789", "XYZ789"),
            ("ORDER NO: PO-2024-001", "PO-2024-001")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.processor._extract_order_number(input_text)
                self.assertEqual(result, expected)
    
    def test_extract_company(self):
        test_cases = [
            ("株式会社テスト", "テスト"),
            ("有限会社サンプル", "サンプル"),
            ("テスト株式会社", "テスト")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.processor._extract_company(input_text)
                self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()