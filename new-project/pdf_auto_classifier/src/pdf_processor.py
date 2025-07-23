import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import re
import os
from typing import Tuple, Dict, Optional
from loguru import logger

class PDFProcessor:
    def __init__(self, config):
        self.config = config
        self.keywords = config.get('po_detection.keywords', [])
        self.confidence_threshold = config.get('po_detection.confidence_threshold', 0.98)
        self.ocr_language = config.get('processing.ocr_language', 'jpn')
        self.max_file_size = config.get('processing.max_file_size_mb', 50) * 1024 * 1024
        self.max_pages = config.get('processing.max_pages', 5)
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            if os.path.getsize(file_path) > self.max_file_size:
                logger.warning(f"File too large: {file_path}")
                return ""
            
            text = ""
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) > self.max_pages:
                    logger.warning(f"Too many pages in {file_path}, processing first {self.max_pages}")
                
                for i, page in enumerate(pdf.pages[:self.max_pages]):
                    # Try pdfplumber first
                    page_text = page.extract_text()
                    
                    # Always try OCR for the first page to catch title area
                    if i == 0:
                        ocr_text = self._extract_text_with_ocr(file_path, i)
                        # Focus on upper portion of the page for title detection
                        title_text = self._extract_title_area_ocr(file_path, i)
                        
                        # Combine all text sources
                        combined_text = ""
                        if page_text:
                            combined_text += page_text + "\n"
                        if title_text:
                            combined_text += title_text + "\n"
                        if ocr_text:
                            combined_text += ocr_text + "\n"
                        
                        text += combined_text
                    else:
                        # For other pages, use existing logic
                        if page_text:
                            text += page_text + "\n"
                        else:
                            ocr_text = self._extract_text_with_ocr(file_path, i)
                            text += ocr_text + "\n"
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    def _extract_text_with_ocr(self, file_path: str, page_number: int) -> str:
        try:
            images = convert_from_path(file_path, first_page=page_number+1, last_page=page_number+1)
            if not images:
                return ""
            
            image = images[0]
            text = pytesseract.image_to_string(image, lang=self.ocr_language)
            return text.strip()
        
        except Exception as e:
            logger.error(f"OCR error for {file_path} page {page_number}: {str(e)}")
            return ""
    
    def _extract_title_area_ocr(self, file_path: str, page_number: int) -> str:
        """Extract text from the upper portion of the PDF page focusing on title area above 'No.358-'"""
        try:
            images = convert_from_path(file_path, first_page=page_number+1, last_page=page_number+1, dpi=300)
            if not images:
                return ""
            
            image = images[0]
            width, height = image.size
            
            # First, extract all text to find the position of "No.358-" or similar patterns
            full_text = pytesseract.image_to_string(image, lang=self.ocr_language)
            
            # Look for document number patterns like "No.358-" to determine title area
            title_crop_height = height // 4  # Default to upper 25%
            
            # Try to find document number line and adjust crop accordingly
            lines = full_text.split('\n')
            for i, line in enumerate(lines):
                if 'No.' in line and any(char.isdigit() for char in line):
                    # Found document number line - title should be above this
                    # Estimate position based on line number (rough approximation)
                    estimated_y = (i * height) // max(len(lines), 1)
                    title_crop_height = max(estimated_y - 20, height // 8)  # Go above the No. line
                    logger.debug(f"Found document number at line {i}, adjusting title crop to {title_crop_height}")
                    break
                    
            # If no document number found, look for text patterns that indicate we should crop higher
            if title_crop_height == height // 4:
                for i, line in enumerate(lines):
                    if ('株式会社' in line or '行' in line) and i > 0:
                        # Found company name - title should be above this
                        estimated_y = (i * height) // max(len(lines), 1)
                        title_crop_height = max(estimated_y - 20, height // 8)
                        logger.debug(f"Found company name at line {i}, adjusting title crop to {title_crop_height}")
                        break
            
            # Crop to title area (above document number)
            title_area = image.crop((0, 0, width, title_crop_height))
            
            # Use OCR with specific configuration for better Japanese text recognition
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(title_area, lang=self.ocr_language, config=custom_config)
            
            # Also check if "注文書" appears in the full text but not in the cropped area
            # This is a fallback to catch cases where cropping missed the title
            if '注文書' not in text and '注文書' in full_text:
                # Find the line containing "注文書"
                for i, line in enumerate(lines):
                    if '注文書' in line:
                        logger.debug(f"Found '注文書' in full text at line {i}: {line}")
                        text = line + '\n' + text
                        break
            
            logger.debug(f"Title area OCR result for {file_path}: {text[:100]}...")
            return text.strip()
        
        except Exception as e:
            logger.error(f"Title area OCR error for {file_path} page {page_number}: {str(e)}")
            return ""
    
    def is_purchase_order(self, file_path: str) -> Tuple[bool, str]:
        try:
            content = self.extract_text_from_pdf(file_path)
            if not content:
                return False, ""
            
            content_lower = content.lower()
            keyword_matches = 0
            matched_keywords = []
            
            # Check for keywords in content
            for keyword in self.keywords:
                if keyword.lower() in content_lower:
                    keyword_matches += 1
                    matched_keywords.append(keyword)
            
            # Additional check for title area specifically (above document number)
            title_text = self._extract_title_area_ocr(file_path, 0)
            if title_text:
                title_lower = title_text.lower()
                # Remove spaces and check again for better matching
                title_no_spaces = title_lower.replace(' ', '').replace('　', '').replace('\n', '')
                
                logger.debug(f"Title area text: '{title_text}', no spaces: '{title_no_spaces}'")
                
                for keyword in self.keywords:
                    keyword_lower = keyword.lower()
                    keyword_no_spaces = keyword_lower.replace(' ', '').replace('　', '')
                    
                    # Check both original and no-space versions
                    if (keyword_lower in title_lower or keyword_no_spaces in title_no_spaces) and keyword not in matched_keywords:
                        keyword_matches += 1
                        matched_keywords.append(f"{keyword}(title)")
                        
                        # Special bonus for exact title matches - this is very strong indicator
                        if keyword_lower in ["注文書", "purchase order", "発注書"]:
                            keyword_matches += 2  # Higher bonus for title area
                            matched_keywords.append(f"{keyword}(title-strong)")
                            
                            # If we find title in the title area, it's definitely a PO
                            if keyword_no_spaces in title_no_spaces:
                                keyword_matches += 2  # Even higher bonus for clean match
                                matched_keywords.append(f"{keyword}(title-exact)")
            
            confidence = keyword_matches / len(self.keywords) if self.keywords else 0
            is_po = confidence >= self.confidence_threshold
            
            logger.debug(f"PO detection for {file_path}: {confidence:.2f} confidence, {keyword_matches} matches: {matched_keywords}")
            
            return is_po, content
        
        except Exception as e:
            logger.error(f"Error detecting PO in {file_path}: {str(e)}")
            return False, ""
    
    def extract_metadata(self, content: str, file_path: str = None) -> Dict[str, Optional[str]]:
        metadata = {
            'date': None,
            'company': None,
            'project_name': None
        }
        
        try:
            # Extract structured metadata based on PDF layout
            metadata['date'] = self._extract_date_structured(content, file_path)
            metadata['company'] = self._extract_company_structured(content, file_path)
            metadata['project_name'] = self._extract_project_name(content)
            
            # Fallback to original methods if structured extraction fails
            if not metadata['date']:
                metadata['date'] = self._extract_date(content)
            if not metadata['company']:
                metadata['company'] = self._extract_company(content)
        
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
        
        return metadata
    
    def _extract_date(self, content: str) -> Optional[str]:
        date_patterns = self.config.get('metadata_extraction.date_patterns', [])
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    if len(match) == 3:
                        year, month, day = match
                        if len(year) == 4:
                            return f"{year}{month.zfill(2)}{day.zfill(2)}"
                        else:
                            return f"{match[2]}{match[0].zfill(2)}{match[1].zfill(2)}"
                else:
                    return match
        
        return None
    
    def _extract_date_structured(self, content: str, file_path: str = None) -> Optional[str]:
        """Extract date from the line below 見積№ in the upper right area of the PDF"""
        try:
            # PRIORITY 1: Try OCR on upper right area to find date after 見積№
            if file_path:
                try:
                    upper_right_text = self._extract_upper_right_area_ocr(file_path, 0)
                    if upper_right_text:
                        logger.debug(f"Upper right OCR text: {upper_right_text}")
                        
                        # Split into lines and look for 見積№ pattern
                        lines = upper_right_text.split('\n')
                        
                        for i, line in enumerate(lines):
                            # Look for 見積№ or variations (No., 見積No., etc.)
                            if re.search(r'(見積\s*[№No]|No\.|見積\s*No)', line):
                                logger.debug(f"Found 見積№ at line {i}: {line}")
                                
                                # Check the next few lines for date (skip empty lines)
                                for j in range(1, 5):  # Check next 4 lines
                                    if i + j < len(lines):
                                        next_line = lines[i + j].strip()
                                        if not next_line:  # Skip empty lines
                                            continue
                                        
                                        logger.debug(f"Checking line {j} after 見積№: {next_line}")
                                        
                                        # Clean the line for OCR errors
                                        cleaned_line = next_line.replace(')うog2$', '2025').replace('うo2$', '2025').replace('22ち', '2025').replace('/J', '12').replace('/3', '13').replace('/ぅ', '12').replace('し月', '7月').replace('年月', '年7月').replace('*et6', '2017').replace('*e', '20').replace('et6', '2017').replace('[', '1').replace('(', '11').replace(')日', '1日').replace('*eも年', '2017年').replace('| 月', '1月').replace('|', '1')
                                        
                                        # Try to find date in this line
                                        date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', cleaned_line)
                                        if date_match:
                                            year, month, day = date_match.groups()
                                            formatted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                                            logger.debug(f"Found date {j} lines below 見積№: {formatted_date}")
                                            return formatted_date
                                        
                                        # Try alternative date patterns for OCR errors
                                        year_match = re.search(r'(\d{4}|\d{2}o2\$|うo2\$)\s*年', cleaned_line)
                                        month_match = re.search(r'(\d{1,2})\s*月', cleaned_line)
                                        day_match = re.search(r'(\d{1,2})\s*日', cleaned_line)
                                        
                                        if year_match and month_match and day_match:
                                            year_str = year_match.group(1)
                                            # Fix common OCR errors in year
                                            if 'o2$' in year_str or 'o2' in year_str:
                                                year_str = '2025'
                                            elif len(year_str) == 2:
                                                year_str = '20' + year_str
                                            
                                            month_str = month_match.group(1)
                                            day_str = day_match.group(1)
                                            
                                            try:
                                                year = int(year_str)
                                                month = int(month_str)
                                                day = int(day_str)
                                                
                                                # Validate date ranges
                                                if 2015 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                                                    formatted_date = f"{year}{month:02d}{day:02d}"
                                                    logger.debug(f"Found reconstructed date {j} lines below 見積№: {formatted_date}")
                                                    return formatted_date
                                            except ValueError:
                                                pass
                                
                                break  # Found 見積№, processed its following lines
                        
                        # If no 見積№ found, try fallback general search in upper right
                        date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', upper_right_text)
                        if date_match:
                            year, month, day = date_match.groups()
                            formatted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                            logger.debug(f"Found fallback upper right date: {formatted_date}")
                            return formatted_date
                            
                except Exception as e:
                    logger.debug(f"Upper right OCR failed: {e}")
            
            # PRIORITY 2: Try text extraction as fallback, look for 見積№ patterns
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                # Look for 見積№ or variations
                if re.search(r'(見積\s*[№No]|No\.|見積\s*No)', line):
                    logger.debug(f"Found 見積№ in content at line {i}: {line}")
                    
                    # Check the next few lines for date
                    for j in range(1, 4):  # Check next 3 lines
                        if i + j < len(lines):
                            next_line = lines[i + j].strip()
                            if next_line:
                                # Clean the line for better matching
                                cleaned_line = next_line.replace('し月', '7月').replace('年月', '年7月')
                                
                                date_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', cleaned_line)
                                if date_match:
                                    year, month, day = date_match.groups()
                                    
                                    # Skip if this looks like a detail line (contains item info, amounts, etc.)
                                    if any(keyword in next_line for keyword in ['式', '円', '税', '金額', '合計', '作業', '対応', '件', '数量', '単価', '小計', '納期', '完了', '作成']):
                                        logger.debug(f"Skipping detail line date: {next_line}")
                                        continue
                                    
                                    formatted_date = f"{year}{month.zfill(2)}{day.zfill(2)}"
                                    logger.debug(f"Found date {j} lines below 見積№: {formatted_date} from line: {next_line}")
                                    return formatted_date
                    
                    break  # Found 見積№, processed its following lines
            
            return None
        except Exception as e:
            logger.error(f"Error in structured date extraction: {str(e)}")
            return None
    
    def _extract_upper_right_area_ocr(self, file_path: str, page_number: int = 0) -> str:
        """Extract text from upper right area of PDF for date/company extraction"""
        try:
            images = convert_from_path(file_path, first_page=page_number+1, last_page=page_number+1, dpi=300)
            if not images:
                return ""
            
            image = images[0]
            width, height = image.size
            
            # Crop to upper right area (right 35%, upper 25%) - balanced for header area
            left = int(width * 0.65)  # Start from 65% across (balanced right-focused)
            top = 0
            right = width
            bottom = int(height * 0.25)  # Upper 25% (balanced top-focused)
            
            upper_right_area = image.crop((left, top, right, bottom))
            
            # Use OCR with specific configuration for better Japanese text recognition
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(upper_right_area, lang=self.ocr_language, config=custom_config)
            
            logger.debug(f"Upper right area OCR result for {file_path}: {text[:100]}...")
            return text.strip()
        
        except Exception as e:
            logger.error(f"Upper right area OCR error for {file_path} page {page_number}: {str(e)}")
            return ""
    
    def _extract_company(self, content: str) -> Optional[str]:
        company_patterns = self.config.get('metadata_extraction.company_patterns', [])
        
        for pattern in company_patterns:
            matches = re.findall(pattern, content)
            if matches:
                company = matches[0].strip()
                if company and len(company) > 1:
                    return company[:20]
        
        return None
    
    def _extract_company_structured(self, content: str, file_path: str = None) -> Optional[str]:
        """Extract company name from upper right area, excluding アクトシステムズ"""
        try:
            lines = content.split('\n')
            
            # Focus on the first 10 lines (header area) where company names typically appear
            # Prioritize shorter lines as they're more likely to be right-aligned company names
            header_lines = []
            for i in range(min(10, len(lines))):
                line = lines[i].strip()
                if line:
                    header_lines.append((i, line))
            
            # Sort by line length (shorter lines more likely to be right-aligned)
            header_lines.sort(key=lambda x: len(x[1]))
            
            for line_num, line in header_lines:
                # Skip lines containing "アクトシステムズ" as specified
                if 'アクトシステムズ' in line or 'アクトシステム' in line:
                    logger.debug(f"Skipping アクトシステムズ line: {line}")
                    continue
                
                # Skip lines that look like detail items or amounts
                if any(keyword in line for keyword in ['式', '円', '税', '金額', '合計', '作業', '対応', '件', '数量', '単価', '小計', 'No.']):
                    continue
                
                # Look for company patterns - prioritize "青山商事株式会社" pattern
                company_patterns = [
                    r'(青山商事株式会社)',
                    r'([^\s\n]*商事[^\s\n]*株式会社)',
                    r'([^\s\n]+株式会社)',
                    r'([^\s\n]+有限会社)',
                    r'(株式会社[^\s\n]+)',
                    r'(有限会社[^\s\n]+)'
                ]
                
                for pattern in company_patterns:
                    company_match = re.search(pattern, line)
                    if company_match:
                        company_name = company_match.group(1).strip()
                        
                        # Additional filter to exclude アクトシステムズ variations
                        if 'アクト' in company_name and 'システム' in company_name:
                            continue
                        
                        # Remove common suffixes like "行"
                        clean_company = re.sub(r'\s*行\s*$', '', company_name)
                        
                        # Skip very short company names
                        if len(clean_company) < 4:
                            continue
                        
                        logger.debug(f"Found upper right company: {clean_company} from line {line_num}: {line}")
                        return clean_company[:20]
                
                # Look for standalone company names with "行" suffix
                if '行' in line and len(line) > 3 and len(line) < 25:
                    company_match = re.search(r'([^\s\n]+)\s*行', line)
                    if company_match:
                        company_name = company_match.group(1).strip()
                        
                        # Skip if contains アクトシステムズ
                        if 'アクト' in company_name and 'システム' in company_name:
                            continue
                        
                        if len(company_name) > 3:
                            logger.debug(f"Found company with 行: {company_name} from line {line_num}: {line}")
                            return company_name[:20]
            
            # If no company found in regular text, try OCR on upper right area
            if file_path:
                try:
                    upper_right_text = self._extract_upper_right_area_ocr(file_path, 0)
                    if upper_right_text:
                        logger.debug(f"Upper right company OCR text: {upper_right_text}")
                        
                        # Handle OCR errors for "青山商事株式会社"
                        # Common OCR errors: 青山南事株示会社 -> 青山商事株式会社, 疾軸馬 -> 青山商, 山南事 -> 山商事, 青山商事株式会太 -> 青山商事株式会社
                        cleaned_text = upper_right_text.replace('青山南事株示会社', '青山商事株式会社')
                        cleaned_text = cleaned_text.replace('疾軸馬', '青山商')
                        cleaned_text = cleaned_text.replace('山南事', '山商事')
                        cleaned_text = cleaned_text.replace('青山商事株式会太', '青山商事株式会社')
                        cleaned_text = cleaned_text.replace('青山高事株素会在', '青山商事株式会社')
                        
                        # Look for company patterns in the cleaned text
                        company_patterns = [
                            r'(青山商事株式会社)',
                            r'([^\s\n]*商事[^\s\n]*株式会社)',
                            r'([^\s\n]+株式会社)',
                            r'([^\s\n]+有限会社)'
                        ]
                        
                        for pattern in company_patterns:
                            company_match = re.search(pattern, cleaned_text)
                            if company_match:
                                company_name = company_match.group(1).strip()
                                
                                # Skip if contains アクトシステムズ
                                if 'アクト' in company_name and 'システム' in company_name:
                                    continue
                                
                                # Remove common suffixes like "行"
                                clean_company = re.sub(r'\s*行\s*$', '', company_name)
                                
                                if len(clean_company) >= 4:
                                    logger.debug(f"Found upper right company: {clean_company} from OCR")
                                    return clean_company[:20]
                
                except Exception as e:
                    logger.debug(f"Upper right company OCR failed: {e}")
            
            return None
        except Exception as e:
            logger.error(f"Error in structured company extraction: {str(e)}")
            return None
    
    def _extract_project_name(self, content: str) -> Optional[str]:
        """Extract project name that follows '件名：' or similar patterns"""
        try:
            # Look for project name patterns - enhanced for various formats
            project_patterns = [
                r'件\s*名\s*[:：]\s*([^\n]+)',
                r'件名\s*[:：]\s*([^\n]+)',
                r'案\s*件\s*[:：]\s*([^\n]+)',
                r'案件\s*[:：]\s*([^\n]+)',
                r'プロジェクト\s*[:：]\s*([^\n]+)',
                r'業務内容\s*[:：]\s*([^\n]+)',
                # For this specific format: "1) POS資源配布作業"
                r'1\)\s*([^\n\(]+)',
                r'作業内容\s*[:：]\s*([^\n]+)',
                r'作業名\s*[:：]\s*([^\n]+)',
                # More flexible patterns
                r'内容\s*[:：]\s*([^\n]+)',
                r'タイトル\s*[:：]\s*([^\n]+)'
            ]
            
            for pattern in project_patterns:
                match = re.search(pattern, content)
                if match:
                    project_name = match.group(1).strip()
                    # Clean up the project name
                    project_name = re.sub(r'\s+', ' ', project_name)  # Normalize whitespace
                    
                    # Remove common suffixes and unwanted parts
                    project_name = project_name.split('金')[0].strip()  # Remove everything after 金額
                    project_name = project_name.split('(')[0].strip()   # Remove everything after (
                    project_name = project_name.split('（')[0].strip()   # Remove everything after （
                    project_name = project_name.split('\\')[0].strip()  # Remove everything after \
                    project_name = project_name.split('作業費')[0].strip()  # Remove 作業費用
                    
                    # Skip if contains unwanted terms
                    skip_terms = ['金額', '消費税', '合計', '納期', '場所', '条件', '以下余白']
                    if any(term in project_name for term in skip_terms):
                        continue
                    
                    if len(project_name) > 2:
                        logger.debug(f"Found project name: {project_name} (pattern: {pattern})")
                        return project_name[:50]  # Limit length
            
            return None
        except Exception as e:
            logger.error(f"Error in project name extraction: {str(e)}")
            return None
    
    def _extract_order_number(self, content: str) -> Optional[str]:
        order_patterns = self.config.get('metadata_extraction.order_number_patterns', [])
        
        for pattern in order_patterns:
            matches = re.findall(pattern, content)
            if matches:
                order_no = matches[0].strip()
                if order_no and len(order_no) > 0:
                    return order_no[:20]
        
        return None