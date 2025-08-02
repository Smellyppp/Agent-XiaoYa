import os
import re
from docx import Document
from typing import List
import PyPDF2

class CivilCodePreprocessor:
    """民法典预处理模块（支持分类目录处理）"""
    
    def __init__(self):
        # 结构化标签配置
        self.TAGS = {
            'title': ('[title]', '[/title]'),
            'section0': ('[section0]', '[/section0]'),
            'section1': ('[section1]', '[/section1]'),
            'section2': ('[section2]', '[/section2]'),
            'section3': ('[section3]', '[/section3]'),
            'article': ('[article]', '[/article]')
        }
        
        # 优化后的正则表达式
        self.PATTERNS = {
            '编': re.compile(r'^第[一二三四五六七八九十百]+编\s+.+$'),
            '分编': re.compile(r'^第[一二三四五六七八九十百]+分编\s+.+$'),
            '章': re.compile(r'^第[一二三四五六七八九十百]+章\s+.+$'),
            '节': re.compile(r'^第[一二三四五六七八九十百]+节\s+.+$'),
            '条': re.compile(r'^第[零一二三四五六七八九十百千]+条(\s*|　).+$')
        }

    def read_docx(self, filepath: str) -> List[str]:
        """读取DOCX文件内容"""
        doc = Document(filepath)
        return [para.text.strip() for para in doc.paragraphs if para.text.strip()]

    def read_pdf(self, filepath: str) -> List[str]:
        """读取PDF文件内容"""
        texts = []
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.extend(text.split('\n'))
        return [line.strip() for line in texts if line.strip()]

    def read_txt(self, filepath: str) -> List[str]:
        """读取TXT文件内容"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def process_file(self, input_path: str, output_path: str) -> None:
        """处理单个文件"""
        print(f"正在处理文件: {os.path.basename(input_path)}")
        
        ext = os.path.splitext(input_path)[1].lower()
        if ext == '.docx':
            lines = self.read_docx(input_path)
        elif ext == '.pdf':
            lines = self.read_pdf(input_path)
        elif ext == '.txt':
            lines = self.read_txt(input_path)
        else:
            print(f"跳过不支持的文件格式: {input_path}")
            return

        processed_lines = []
        counters = {k: 0 for k in self.TAGS.keys()}
        counters['other'] = 0
        
        current_article = []
        
        def finalize_article():
            if current_article:
                article_content = ' '.join(line.strip() for line in current_article)
                processed_lines.append(f"{self.TAGS['article'][0]}{article_content}{self.TAGS['article'][1]}")
                counters['article'] += 1
                current_article.clear()
        
        for line in lines:
            if "中华人民共和国民法典" in line:
                finalize_article()
                processed_lines.append(f"{self.TAGS['title'][0]}{line}{self.TAGS['title'][1]}")
                counters['title'] += 1
                continue
                
            matched = False
            for level, pattern in self.PATTERNS.items():
                if level == '条':
                    continue
                if pattern.match(line):
                    finalize_article()
                    tag = f'section{list(self.PATTERNS.keys()).index(level)}'
                    processed_lines.append(f"{self.TAGS[tag][0]}{line}{self.TAGS[tag][1]}")
                    counters[tag] += 1
                    matched = True
                    break
                    
            if not matched:
                if self.PATTERNS['条'].match(line):
                    finalize_article()
                    current_article.append(line)
                elif current_article:
                    current_article.append(line)
                else:
                    processed_lines.append(line)
                    counters['other'] += 1
        
        finalize_article()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(processed_lines))
        
        print(f"处理完成: {os.path.basename(output_path)}")
        print("=== 标记统计 ===")
        for k, v in counters.items():
            print(f"{k}: {v}")
        print(f"总行数: {len(processed_lines)}")
        print("===============")

    def batch_process(self):
        """批量处理分类目录"""
        input_base = "./original_data"
        output_base = "./parsed_document"
        
        # 支持的格式和对应目录
        formats = {
            'docx': 'docx',
            'pdf': 'pdf',
            'txt': 'txt'
        }
        
        total_files = 0
        
        for fmt, dir_name in formats.items():
            input_dir = os.path.join(input_base, dir_name)
            output_dir = os.path.join(output_base, dir_name)
            
            if not os.path.exists(input_dir):
                print(f"警告: 输入目录不存在 {input_dir}")
                continue
                
            print(f"\n处理 {fmt.upper()} 文件: {input_dir}")
            
            for filename in os.listdir(input_dir):
                if filename.lower().endswith(f'.{fmt}'):
                    input_path = os.path.join(input_dir, filename)
                    output_path = os.path.join(
                        output_dir,
                        f"{os.path.splitext(filename)[0]}.txt"
                    )
                    self.process_file(input_path, output_path)
                    total_files += 1
        
        print(f"\n处理完成！共处理 {total_files} 个文件")

if __name__ == "__main__":
    print("民法典文档预处理开始...")
    processor = CivilCodePreprocessor()
    processor.batch_process()
    print("预处理完成！输出保存在 ./parsed_document 对应子目录")