import re
import sys
import os
from collections import defaultdict

def analyze_file(file_path, encoding='euc-kr'):
    """
    Pro*C 파일을 분석하여 TB_로 시작하는 테이블과 CRUD 작업을 추출합니다.
    EXEC SQL 블록과 문자열 리터럴(동적 쿼리)을 모두 분석합니다.
    추가로 '프로그램명 : ...' 패턴을 찾아 설명을 추출합니다.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return {}, ""

    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return {}, ""

    table_ops = defaultdict(set)
    source_desc = ""

    # 0. 프로그램명 추출
    # 패턴: "프로그램(공백)명(공백):(공백)내용"
    desc_pattern = re.compile(r'프로그램\s*명\s*:\s*(.*)', re.IGNORECASE)
    desc_match = desc_pattern.search(content)
    if desc_match:
        source_desc = desc_match.group(1).strip()
    
    # 1. EXEC SQL 블록 분석 (정적 쿼리)
    # exec sql 로 시작하고 ; 로 끝나는 블록을 찾음 (줄바꿈 포함)
    exec_sql_pattern = re.compile(r'EXEC\s+SQL\s+(.*?);', re.DOTALL | re.IGNORECASE)

    for match in exec_sql_pattern.finditer(content):
        sql_block = match.group(1)
        extract_table_crud(sql_block, table_ops, source="STATIC")

    # 2. 문자열 리터럴 분석 (동적 쿼리)
    # 큰따옴표로 묶인 문자열을 찾음
    string_literal_pattern = re.compile(r'"([^"]*)"')

    for match in string_literal_pattern.finditer(content):
        sql_string = match.group(1)
        # 문자열 안에 TB_, ATA_, EM_ 테이블이 있는지 확인
        if any(prefix in sql_string for prefix in ["TB_", "ATA_", "EM_"]):
            extract_table_crud(sql_string, table_ops, source="DYNAMIC")

    return table_ops, source_desc

def extract_table_crud(sql_text, table_ops, source="UNKNOWN"):
    """
    SQL 텍스트(또는 문자열)에서 TB_, ATA_, EM_ 테이블과 CRUD 키워드를 추출하여 table_ops에 저장합니다.
    """
    # 대문자로 변환하여 분석
    sql_upper = sql_text.upper()
    
    # MERGE 문 특수 처리
    if 'MERGE' in sql_upper:
        process_merge_statement(sql_upper, table_ops)
        return

    # 일반적인 "Bag of Words" 방식 처리
    # 테이블 찾기: TB_, ATA_, EM_ 등으로 시작하고 (앞에 스키마명. 이 올 수 있음) 영문자, 숫자, 언더스코어로 구성된 단어
    table_pattern = re.compile(r'\b((?:[A-Z0-9_]+\.)?(?:TB_|ATA_|EM_)[A-Z0-9_]+)\b')
    tables = table_pattern.findall(sql_upper)
    
    if not tables:
        return

    # CRUD 작업 찾기
    ops = set()
    if 'SELECT' in sql_upper:
        ops.add('SELECT')
    if 'INSERT' in sql_upper:
        ops.add('INSERT')
    if 'UPDATE' in sql_upper:
        ops.add('UPDATE')
    if 'DELETE' in sql_upper:
        ops.add('DELETE')
    
    if ops:
        for table in tables:
            # NHPT. 스키마 제거
            if table.startswith("NHPT."):
                table = table.replace("NHPT.", "")
            
            for op in ops:
                table_ops[table].add(op)

def process_merge_statement(sql_upper, table_ops):
    """
    MERGE 문을 상세 분석하여 Target 테이블에는 INSERT/UPDATE를,
    Source 테이블 등에는 SELECT를 부여합니다.
    """
    # Target Table 추출: MERGE INTO [Table]
    target_pattern = re.compile(r'MERGE\s+INTO\s+((?:[A-Z0-9_]+\.)?(?:TB_|ATA_|EM_)[A-Z0-9_]+)')
    target_match = target_pattern.search(sql_upper)
    
    target_table = None
    if target_match:
        target_table = target_match.group(1)
        # NHPT. 스키마 제거
        if target_table.startswith("NHPT."):
            target_table = target_table.replace("NHPT.", "")
        
        # Target Table Operations
        if re.search(r'WHEN\s+MATCHED\s+THEN\s+UPDATE', sql_upper):
            table_ops[target_table].add('UPDATE')
        
        if re.search(r'WHEN\s+NOT\s+MATCHED\s+THEN\s+INSERT', sql_upper):
            table_ops[target_table].add('INSERT')
            
    # 나머지 테이블 추출 (Source Tables) -> SELECT 취급
    # 전체 테이블 찾기
    all_table_pattern = re.compile(r'\b((?:[A-Z0-9_]+\.)?(?:TB_|ATA_|EM_)[A-Z0-9_]+)\b')
    all_tables = set(all_table_pattern.findall(sql_upper))
    
    # Target Table 제외 (Cleaned target table removal might be tricky if original was different)
    # Careful: We need to remove the raw string found in regex, NOT the cleaned one, 
    # to correctly subtract from all_tables which contains raw strings.
    # But wait, all_tables contains strings. 
    
    # Let's clean all_tables first? No, we need to exclude the target match string from the source list.
    if target_match:
        raw_target_table = target_match.group(1)
        if raw_target_table in all_tables:
            all_tables.remove(raw_target_table)
        
    # 나머지는 모두 SELECT (USING 구문 등)
    for table in all_tables:
        # NHPT. 스키마 제거
        if table.startswith("NHPT."):
            table = table.replace("NHPT.", "")
        table_ops[table].add('SELECT')

import argparse
import glob
try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(description="Pro*C Source Analyzer")
    parser.add_argument("-f", "--file", help="Path to a single Pro*C file to analyze")
    parser.add_argument("-d", "--folder", help="Directory path to scan for *.pc files")
    parser.add_argument("-e", "--excel", help="Output Excel filename (e.g., result.xlsx)")
    parser.add_argument("-m", "--merge", action="store_true", help="Merge cells for same Source Name and Source Desc. in Excel")
    parser.add_argument("-c", "--encoding", default="euc-kr", help="File encoding (default: euc-kr)")
    
    args = parser.parse_args()
    
    if args.excel and not OPENPYXL_AVAILABLE:
        print("Error: 'openpyxl' library is not installed. Please install it using 'pip install openpyxl' or 'uv add openpyxl' to use Excel export.")
        sys.exit(1)

    files_to_process = []
    
    if args.file:
        files_to_process.append(args.file)
    elif args.folder:
        if os.path.exists(args.folder):
            search_pattern = os.path.join(args.folder, "*.pc")
            files_to_process = glob.glob(search_pattern)
            if not files_to_process:
                print(f"No *.pc files found in: {args.folder}")
        else:
            print(f"Error: Directory not found - {args.folder}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # Collect all results
    all_results = [] # List of tuples: (filename, source_desc, table, operations)

    for file_path in files_to_process:
        result, source_desc = analyze_file(file_path, encoding=args.encoding)
        file_name = os.path.basename(file_path)

        # Console Output
        print(f"\nAnalysis Report for: {file_path}")
        print(f"Source Desc: {source_desc}")
        print(f"{'Table Name':<30} | {'CRUD Operations'}")
        print("-" * 60)
        
        if not result:
            print("No tables found or file error.")
        else:
            sorted_tables = sorted(result.keys())
            for table in sorted_tables:
                ops = ", ".join(sorted(result[table]))
                print(f"{table:<30} | {ops}")
                # Add to results for Excel
                all_results.append((file_name, source_desc, table, ops))
        print("\n" + "="*60)

    # Excel Export
    if args.excel:
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Analysis Result"
            
            # Header
            from openpyxl.styles import Alignment
            ws.append(["Source Name", "Source Desc.", "Table Name", "CRUD Operations"])
            
            # Data
            # Sort mainly for merging logic (though processing order might be enough, safety first)
            # But here we process file by file, so it's naturally sorted by file processing order.
            
            start_row = 2 # Data starts from row 2
            for row in all_results:
                ws.append(row)
            
            last_row = ws.max_row

            # Merging Logic
            if args.merge and last_row >= start_row:
                # Iterate to find ranges to merge
                # We need to merge Column 1 (Source Name) and Column 2 (Source Desc.)
                
                # Helper to merge a specific column
                def merge_column(col_idx):
                    current_val = ws.cell(row=start_row, column=col_idx).value
                    merge_start = start_row
                    
                    for r in range(start_row + 1, last_row + 2): # Go one past end to handle last block
                        val = ws.cell(row=r, column=col_idx).value if r <= last_row else None
                        
                        if val != current_val:
                            # End of a block
                            if r - 1 > merge_start:
                                ws.merge_cells(start_row=merge_start, start_column=col_idx, end_row=r-1, end_column=col_idx)
                                # Center alignment for merged cells
                                cell = ws.cell(row=merge_start, column=col_idx)
                                cell.alignment = Alignment(vertical='center', horizontal='center')
                            
                            current_val = val
                            merge_start = r

                merge_column(1) # Source Name
                merge_column(2) # Source Desc.

            # Auto-adjust column width (simple approximation)
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter # Get the column name
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column].width = adjusted_width

            wb.save(args.excel)
            print(f"\nExcel file saved successfully to: {args.excel}")
        except Exception as e:
            print(f"\nError saving Excel file: {e}")

if __name__ == "__main__":
    main()
