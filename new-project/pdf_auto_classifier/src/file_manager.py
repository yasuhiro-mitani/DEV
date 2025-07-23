import os
import shutil
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
import re

class FileManager:
    def __init__(self, config):
        self.config = config
        self.input_folder = config.get('folders.input', '/app/input')
        self.output_folder = config.get('folders.output', '/app/output')
        self.error_folder = config.get('folders.error', '/app/error')
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        for folder in [self.output_folder, self.error_folder]:
            Path(folder).mkdir(parents=True, exist_ok=True)
    
    def generate_filename(self, metadata: Dict[str, Optional[str]]) -> str:
        date = metadata.get('date', 'UNKNOWN')
        company = metadata.get('company', 'UNKNOWN')
        project_name = metadata.get('project_name', 'UNKNOWN')
        
        # Check if company contains "青山商事", if not use "〇〇"
        if company and '青山商事' in company:
            company_name = '青山商事'
        else:
            company_name = '〇〇'
        
        company_name = self._sanitize_filename(company_name)
        project_name = self._sanitize_filename(project_name)
        
        base_filename = f"{date}_注文書_{company_name}_{project_name}.pdf"
        
        return self._ensure_unique_filename(base_filename)
    
    def _sanitize_filename(self, filename: str) -> str:
        if not filename or filename == 'UNKNOWN':
            return filename
        
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('._')
        
        return filename[:20] if len(filename) > 20 else filename
    
    def _ensure_unique_filename(self, filename: str) -> str:
        base_name = Path(filename).stem
        extension = Path(filename).suffix
        counter = 1
        
        while Path(self.output_folder, filename).exists():
            counter += 1
            filename = f"{base_name}_v{counter}{extension}"
        
        return filename
    
    def move_to_output(self, source_path: str, new_filename: str) -> bool:
        try:
            destination = Path(self.output_folder) / new_filename
            shutil.move(source_path, destination)
            logger.info(f"Moved {source_path} to {destination}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to move {source_path} to output: {str(e)}")
            return False
    
    def move_to_error(self, source_path: str, reason: str) -> bool:
        try:
            filename = Path(source_path).name
            timestamp = self._get_timestamp()
            error_filename = f"{timestamp}_{filename}"
            
            destination = Path(self.error_folder) / error_filename
            shutil.move(source_path, destination)
            
            error_log_path = Path(self.error_folder) / f"{error_filename}.log"
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Error: {reason}\n")
                f.write(f"Original file: {filename}\n")
                f.write(f"Timestamp: {timestamp}\n")
            
            logger.info(f"Moved {source_path} to error folder: {destination}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to move {source_path} to error folder: {str(e)}")
            return False
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")