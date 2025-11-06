"""
고급 추출기: PDF, 표, 이미지 처리

이 모듈은 HTML 이외의 콘텐츠를 처리합니다:
    1. PDF 텍스트 추출
    2. 표 구조 보존
    3. 이미지 OCR (선택)

사용법:
    # PDF 처리
    extractor = PDFExtractor()
    text = extractor.extract_text("paper.pdf")
    
    # 표 처리
    table_extractor = TableExtractor()
    structured_data = table_extractor.extract_table(html)
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import io


@dataclass
class TableRow:
    """
    표의 한 행
    
    속성:
        cells: 셀 값 리스트
        row_type: 'header' 또는 'data'
    """
    cells: List[str]
    row_type: str = 'data'  # 'header' or 'data'


@dataclass
class ExtractedTable:
    """
    추출된 표 데이터
    
    속성:
        headers: 컬럼 헤더 리스트
        rows: TableRow 리스트
        caption: 표 제목
        metadata: 추가 메타데이터 (venue, year 등)
    """
    headers: List[str]
    rows: List[TableRow]
    caption: Optional[str] = None
    metadata: Dict[str, any] = None
    
    def to_text(self) -> str:
        """표를 텍스트로 변환"""
        lines = []
        
        if self.caption:
            lines.append(f"표: {self.caption}\n")
        
        # 헤더
        if self.headers:
            lines.append(" | ".join(self.headers))
            lines.append("-" * 50)
        
        # 데이터 행
        for row in self.rows:
            lines.append(" | ".join(row.cells))
        
        return "\n".join(lines)
    
    def to_dict_list(self) -> List[Dict[str, str]]:
        """표를 딕셔너리 리스트로 변환 (JSON 친화적)"""
        if not self.headers:
            return []
        
        result = []
        for row in self.rows:
            row_dict = {}
            for i, header in enumerate(self.headers):
                if i < len(row.cells):
                    row_dict[header] = row.cells[i]
            result.append(row_dict)
        
        return result


class PDFExtractor:
    """
    PDF 텍스트 추출기
    
    PyPDF2 또는 pdfplumber 사용
    
    사용법:
        extractor = PDFExtractor()
        text = extractor.extract_text("paper.pdf")
        
    의존성:
        pip install PyPDF2
        또는
        pip install pdfplumber  # 더 정확하지만 느림
    """
    
    def __init__(self, backend: str = 'pypdf2'):
        """
        Args:
            backend: 'pypdf2' 또는 'pdfplumber'
        """
        self.backend = backend
        
        if backend == 'pypdf2':
            try:
                import PyPDF2
                self.PyPDF2 = PyPDF2
            except ImportError:
                raise ImportError("PyPDF2가 설치되지 않았습니다: pip install PyPDF2")
        
        elif backend == 'pdfplumber':
            try:
                import pdfplumber
                self.pdfplumber = pdfplumber
            except ImportError:
                raise ImportError("pdfplumber가 설치되지 않았습니다: pip install pdfplumber")
    
    def extract_text(self, pdf_path_or_bytes) -> str:
        """
        PDF에서 텍스트 추출
        
        Args:
            pdf_path_or_bytes: PDF 파일 경로 또는 바이트 데이터
        
        Returns:
            추출된 텍스트
        """
        if self.backend == 'pypdf2':
            return self._extract_with_pypdf2(pdf_path_or_bytes)
        else:
            return self._extract_with_pdfplumber(pdf_path_or_bytes)
    
    def _extract_with_pypdf2(self, pdf_path_or_bytes) -> str:
        """PyPDF2로 추출"""
        # 파일 경로인지 바이트인지 확인
        if isinstance(pdf_path_or_bytes, str):
            with open(pdf_path_or_bytes, 'rb') as f:
                pdf_data = f.read()
        else:
            pdf_data = pdf_path_or_bytes
        
        # PDF 읽기
        pdf_file = io.BytesIO(pdf_data)
        reader = self.PyPDF2.PdfReader(pdf_file)
        
        # 모든 페이지 텍스트 추출
        texts = []
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text = page.extract_text()
            if text:
                texts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        return "\n\n".join(texts)
    
    def _extract_with_pdfplumber(self, pdf_path_or_bytes) -> str:
        """pdfplumber로 추출 (더 정확)"""
        # 파일 경로인지 바이트인지 확인
        if isinstance(pdf_path_or_bytes, bytes):
            pdf_file = io.BytesIO(pdf_path_or_bytes)
        else:
            pdf_file = pdf_path_or_bytes
        
        texts = []
        with self.pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    texts.append(f"--- Page {page_num} ---\n{text}")
        
        return "\n\n".join(texts)
    
    def extract_metadata(self, pdf_path_or_bytes) -> Dict[str, any]:
        """
        PDF 메타데이터 추출
        
        Returns:
            {'title': ..., 'author': ..., 'pages': ...}
        """
        if isinstance(pdf_path_or_bytes, str):
            with open(pdf_path_or_bytes, 'rb') as f:
                pdf_data = f.read()
        else:
            pdf_data = pdf_path_or_bytes
        
        pdf_file = io.BytesIO(pdf_data)
        reader = self.PyPDF2.PdfReader(pdf_file)
        
        metadata = {
            'pages': len(reader.pages),
            'title': None,
            'author': None,
            'subject': None,
        }
        
        if reader.metadata:
            metadata['title'] = reader.metadata.get('/Title')
            metadata['author'] = reader.metadata.get('/Author')
            metadata['subject'] = reader.metadata.get('/Subject')
        
        return metadata


class TableExtractor:
    """
    HTML 표 추출 및 구조 보존
    
    학회/연도/제목 등의 컬럼을 자동으로 인식하여
    lab_tag(venue/year)로 매핑합니다.
    
    사용법:
        extractor = TableExtractor()
        tables = extractor.extract_tables(html)
        
        for table in tables:
            print(table.to_text())
    """
    
    # 인식할 컬럼 헤더 패턴
    COLUMN_PATTERNS = {
        'venue': r'(venue|conference|journal|학회|저널|발표지)',
        'year': r'(year|date|년도|발표년도)',
        'title': r'(title|paper|제목|논문)',
        'author': r'(author|authors|저자)',
    }
    
    def extract_tables(self, html: str) -> List[ExtractedTable]:
        """
        HTML에서 모든 표 추출
        
        Args:
            html: HTML 소스
        
        Returns:
            ExtractedTable 리스트
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = []
        
        for table_elem in soup.find_all('table'):
            extracted = self._parse_table_element(table_elem)
            if extracted:
                tables.append(extracted)
        
        return tables
    
    def _parse_table_element(self, table_elem) -> Optional[ExtractedTable]:
        """
        단일 table 요소 파싱
        
        Args:
            table_elem: BeautifulSoup table 요소
        
        Returns:
            ExtractedTable 또는 None
        """
        # 캡션 찾기
        caption = None
        caption_elem = table_elem.find('caption')
        if caption_elem:
            caption = caption_elem.get_text(strip=True)
        
        # 헤더 찾기
        headers = []
        thead = table_elem.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # 헤더가 없으면 첫 번째 행을 헤더로 간주
        if not headers:
            first_row = table_elem.find('tr')
            if first_row:
                cells = first_row.find_all(['th', 'td'])
                # th가 많으면 헤더로 간주
                if sum(1 for c in cells if c.name == 'th') > len(cells) / 2:
                    headers = [c.get_text(strip=True) for c in cells]
        
        # 데이터 행 추출
        rows = []
        tbody = table_elem.find('tbody') or table_elem
        
        for tr in tbody.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            
            # 빈 행 건너뛰기
            if not any(cells):
                continue
            
            # 헤더 행 건너뛰기
            if cells == headers:
                continue
            
            rows.append(TableRow(cells=cells))
        
        # 빈 표는 무시
        if not rows:
            return None
        
        # 메타데이터 자동 매핑
        metadata = self._extract_metadata(headers, rows)
        
        return ExtractedTable(
            headers=headers,
            rows=rows,
            caption=caption,
            metadata=metadata
        )
    
    def _extract_metadata(
        self, 
        headers: List[str], 
        rows: List[TableRow]
    ) -> Dict[str, any]:
        """
        헤더와 데이터에서 메타데이터 추출
        
        venue, year 등의 컬럼을 찾아 lab_tag 생성
        """
        metadata = {}
        
        # 컬럼 인덱스 매핑
        column_map = {}
        for i, header in enumerate(headers):
            header_lower = header.lower()
            
            for key, pattern in self.COLUMN_PATTERNS.items():
                if re.search(pattern, header_lower, re.I):
                    column_map[key] = i
        
        metadata['column_map'] = column_map
        
        # lab_tag 생성 (venue + year)
        if 'venue' in column_map and 'year' in column_map:
            venue_idx = column_map['venue']
            year_idx = column_map['year']
            
            lab_tags = []
            for row in rows:
                if venue_idx < len(row.cells) and year_idx < len(row.cells):
                    venue = row.cells[venue_idx]
                    year = row.cells[year_idx]
                    
                    # 연도 추출 (숫자만)
                    year_match = re.search(r'\d{4}', year)
                    if year_match:
                        year = year_match.group()
                    
                    lab_tag = f"{venue}{year}"
                    lab_tags.append(lab_tag)
            
            metadata['lab_tags'] = lab_tags
        
        return metadata


class ImageOCR:
    """
    이미지에서 텍스트 추출 (OCR)
    
    선택적 기능 - 비권장 (후순위)
    
    사용법:
        ocr = ImageOCR()
        text = ocr.extract_text("image.png")
    
    의존성:
        pip install pytesseract pillow
        + Tesseract OCR 엔진 설치 필요
    """
    
    def __init__(self):
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
        except ImportError:
            raise ImportError(
                "pytesseract와 pillow가 필요합니다:\n"
                "pip install pytesseract pillow\n"
                "그리고 Tesseract OCR 엔진을 설치하세요."
            )
    
    def extract_text(
        self, 
        image_path_or_bytes,
        lang: str = 'kor+eng'
    ) -> str:
        """
        이미지에서 텍스트 추출
        
        Args:
            image_path_or_bytes: 이미지 파일 경로 또는 바이트
            lang: OCR 언어 ('kor', 'eng', 'kor+eng')
        
        Returns:
            추출된 텍스트
        """
        # 이미지 로드
        if isinstance(image_path_or_bytes, str):
            image = self.Image.open(image_path_or_bytes)
        else:
            image = self.Image.open(io.BytesIO(image_path_or_bytes))
        
        # OCR 실행
        text = self.pytesseract.image_to_string(image, lang=lang)
        
        return text.strip()


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":
    print("=== 고급 추출기 데모 ===\n")
    
    # 1. 표 추출 데모
    print("1. 표 추출")
    print("-" * 50)
    
    sample_html = """
    <table>
        <caption>최근 논문 목록</caption>
        <thead>
            <tr>
                <th>Year</th>
                <th>Venue</th>
                <th>Title</th>
                <th>Author</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>2024</td>
                <td>CVPR</td>
                <td>Vision Transformer for Image Recognition</td>
                <td>Kim et al.</td>
            </tr>
            <tr>
                <td>2023</td>
                <td>ICCV</td>
                <td>Object Detection with Deep Learning</td>
                <td>Lee et al.</td>
            </tr>
        </tbody>
    </table>
    """
    
    table_extractor = TableExtractor()
    tables = table_extractor.extract_tables(sample_html)
    
    for i, table in enumerate(tables, 1):
        print(f"\n표 {i}:")
        print(table.to_text())
        print(f"\n메타데이터: {table.metadata}")
        print(f"\n딕셔너리 형식:")
        for row_dict in table.to_dict_list():
            print(f"  {row_dict}")
    
    print("\n" + "=" * 50)
    print("\n2. PDF 추출 데모")
    print("-" * 50)
    print("PDF 파일이 필요합니다. 예시:")
    print("""
    extractor = PDFExtractor()
    text = extractor.extract_text("paper.pdf")
    print(text)
    
    metadata = extractor.extract_metadata("paper.pdf")
    print(f"제목: {metadata['title']}")
    print(f"페이지 수: {metadata['pages']}")
    """)
    
    print("\n" + "=" * 50)
    print("\n3. OCR 데모")
    print("-" * 50)
    print("이미지 파일이 필요합니다. 예시:")
    print("""
    ocr = ImageOCR()
    text = ocr.extract_text("screenshot.png", lang='kor+eng')
    print(text)
    """)
