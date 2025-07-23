import os
import sys
import yaml
from pathlib import Path
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver
import threading
import time

from pdf_processor import PDFProcessor
from file_manager import FileManager
from alert_manager import AlertManager

class Config:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as file:
            self.config = yaml.safe_load(file)
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

class PDFHandler(FileSystemEventHandler):
    def __init__(self, config: Config):
        self.config = config
        self.pdf_processor = PDFProcessor(config)
        self.file_manager = FileManager(config)
        self.alert_manager = AlertManager(config)
        self.processing_files = set()
        self.lock = threading.Lock()
    
    def on_created(self, event):
        self._handle_file_event(event)
    
    def on_moved(self, event):
        self._handle_file_event(event)
    
    def on_modified(self, event):
        self._handle_file_event(event)
    
    def _handle_file_event(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not file_path.lower().endswith('.pdf'):
            return
        
        with self.lock:
            if file_path in self.processing_files:
                return
            self.processing_files.add(file_path)
        
        try:
            time.sleep(1)
            self.process_pdf(file_path)
        finally:
            with self.lock:
                self.processing_files.discard(file_path)
    
    def process_pdf(self, file_path: str):
        try:
            logger.info(f"Processing PDF: {file_path}")
            
            if not Path(file_path).exists():
                logger.warning(f"File not found: {file_path}")
                return
            
            is_po, content = self.pdf_processor.is_purchase_order(file_path)
            
            if not is_po:
                logger.info(f"Not a purchase order, skipping: {file_path}")
                return
            
            metadata = self.pdf_processor.extract_metadata(content, file_path)
            
            if not all([metadata.get('date'), metadata.get('company'), metadata.get('project_name')]):
                logger.warning(f"Incomplete metadata, skipping: {file_path}")
                logger.debug(f"Metadata: date={metadata.get('date')}, company={metadata.get('company')}, project={metadata.get('project_name')}")
                return
            
            new_filename = self.file_manager.generate_filename(metadata)
            success = self.file_manager.move_to_output(file_path, new_filename)
            
            if success:
                logger.info(f"Successfully processed: {file_path} -> {new_filename}")
            else:
                logger.error(f"Failed to move file: {file_path}")
                self.alert_manager.send_alert(f"Failed to move file: {file_path}")
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            self.alert_manager.send_alert(f"Error processing {file_path}: {str(e)}")
            self.file_manager.move_to_error(file_path, str(e))

def main():
    config_path = "/app/config/config.yaml"
    if not os.path.exists(config_path):
        config_path = "config/config.yaml"
    
    config = Config(config_path)
    
    log_level = config.get('app.log_level', 'INFO')
    log_path = config.get('folders.logs', '/app/logs')
    
    logger.remove()
    logger.add(
        f"{log_path}/app.log",
        rotation="1 day",
        retention="1 year",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level=log_level
    )
    logger.add(sys.stdout, level=log_level)
    
    input_folder = config.get('folders.input', '/app/input')
    
    if not os.path.exists(input_folder):
        logger.error(f"Input folder does not exist: {input_folder}")
        sys.exit(1)
    
    event_handler = PDFHandler(config)
    # Use PollingObserver for better compatibility with mounted volumes
    observer = PollingObserver()
    observer.schedule(event_handler, input_folder, recursive=False)
    
    logger.info(f"Starting PDF Auto Classifier - monitoring {input_folder}")
    observer.start()
    
    # Process existing files in the input folder
    try:
        for file_path in Path(input_folder).glob("*.pdf"):
            if file_path.is_file():
                logger.info(f"Processing existing file: {file_path}")
                event_handler.process_pdf(str(file_path))
    except Exception as e:
        logger.error(f"Error processing existing files: {e}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping PDF Auto Classifier")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()