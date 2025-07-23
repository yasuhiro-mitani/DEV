import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from src.file_manager import FileManager

class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = Mock()
        self.config.get.side_effect = lambda key, default=None: {
            'folders.input': f"{self.temp_dir}/input",
            'folders.output': f"{self.temp_dir}/output",
            'folders.error': f"{self.temp_dir}/error"
        }.get(key, default)
        
        self.file_manager = FileManager(self.config)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_generate_filename(self):
        metadata = {
            'date': '20240115',
            'company': 'テスト会社',
            'order_number': 'ABC-123'
        }
        
        filename = self.file_manager.generate_filename(metadata)
        self.assertEqual(filename, "20240115_テスト会社_ABC-123.pdf")
    
    def test_generate_filename_with_sanitization(self):
        metadata = {
            'date': '20240115',
            'company': 'テスト/会社',
            'order_number': 'ABC:123'
        }
        
        filename = self.file_manager.generate_filename(metadata)
        self.assertEqual(filename, "20240115_テスト_会社_ABC_123.pdf")
    
    def test_sanitize_filename(self):
        test_cases = [
            ("テスト/会社", "テスト_会社"),
            ("会社<名>", "会社_名_"),
            ("会社名　", "会社名"),
            ("   会社名   ", "会社名"),
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.file_manager._sanitize_filename(input_name)
                self.assertEqual(result, expected)
    
    def test_ensure_unique_filename(self):
        # Create a file to simulate existing file
        existing_file = Path(self.file_manager.output_folder) / "test.pdf"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.touch()
        
        unique_filename = self.file_manager._ensure_unique_filename("test.pdf")
        self.assertEqual(unique_filename, "test_v2.pdf")
    
    def test_move_to_output(self):
        # Create source file
        source_file = Path(self.temp_dir) / "source.pdf"
        source_file.touch()
        
        success = self.file_manager.move_to_output(str(source_file), "output.pdf")
        
        self.assertTrue(success)
        self.assertTrue(Path(self.file_manager.output_folder, "output.pdf").exists())
        self.assertFalse(source_file.exists())
    
    def test_move_to_error(self):
        # Create source file
        source_file = Path(self.temp_dir) / "error.pdf"
        source_file.touch()
        
        with patch.object(self.file_manager, '_get_timestamp', return_value='20240115_120000'):
            success = self.file_manager.move_to_error(str(source_file), "Test error")
        
        self.assertTrue(success)
        self.assertTrue(Path(self.file_manager.error_folder, "20240115_120000_error.pdf").exists())
        self.assertTrue(Path(self.file_manager.error_folder, "20240115_120000_error.pdf.log").exists())
        self.assertFalse(source_file.exists())

if __name__ == '__main__':
    unittest.main()