"""
SC_MOG_COMMON_utf8.pc 파일에서 정규식이 실제로 무엇을 매칭하는지 진단하는 스크립트
"""
import re
import signal
import sys

# 타임아웃 처리 (Windows에서는 signal.alarm 불가, 별도 처리 필요)

with open('SC_MOG_COMMON_utf8.pc', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"파일 길이: {len(content)} 문자")

func_pattern = re.compile(
    r'^\s*(?P<type>(?:[a-zA-Z0-9_]+\s+(?:\*\s*)?)+)(?P<name>[a-zA-Z0-9_]+)\s*\((?P<params>(?:[^;/]|\/(?!\*)|\/\*.*?\*/)*?)\)\s*\{',
    re.MULTILINE | re.DOTALL
)

RESERVED_WORDS = {
    'if', 'while', 'for', 'switch', 'catch', 'return', 'else', 
    'do', 'case', 'default', 'break', 'continue', 'goto', 'sizeof', 'typedef', 'volatile',
    'EXEC', 'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'FROM', 'WHERE', 'AND', 'OR',
    'CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'MERGE', 'INTO', 'VALUES', 'ELSE',
    'TO_NUMBER', 'TO_CHAR', 'TO_DATE', 'TO_TIMESTAMP',
    'NVL', 'NVL2', 'DECODE', 'CASE', 'WHEN', 'THEN', 'END',
    'SUBSTR', 'SUBSTRB', 'INSTR', 'LENGTH', 'LENGTHB', 'REPLACE', 'TRANSLATE',
    'TRIM', 'LTRIM', 'RTRIM', 'LPAD', 'RPAD', 'UPPER', 'LOWER', 'INITCAP',
    'ROUND', 'TRUNC', 'MOD', 'ABS', 'CEIL', 'FLOOR', 'SIGN', 'POWER', 'SQRT',
    'SYSDATE', 'SYSTIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIMESTAMP',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'LISTAGG', 'RANK', 'ROW_NUMBER',
    'COALESCE', 'NULLIF', 'GREATEST', 'LEAST',
    'CAST', 'CONVERT', 'EXTRACT',
}

print("정규식 finditer 실행 중...")
print("(행이 걸리면 catastrophic backtracking 의심)")
sys.stdout.flush()

matches = list(func_pattern.finditer(content))
print(f"\n총 {len(matches)}개 매칭 발견:")

for i, m in enumerate(matches):
    name = m.group('name')
    type_str = m.group('type').strip()
    type_first_word = type_str.split()[0]
    
    # 매칭 위치의 줄 번호 계산
    line_num = content[:m.start()].count('\n') + 1
    
    is_filtered = name in RESERVED_WORDS or type_first_word in RESERVED_WORDS
    status = "FILTERED" if is_filtered else "ACCEPTED"
    
    print(f"\n  [{i+1}] Line {line_num}: {status}")
    print(f"       Type: '{type_str[:80]}{'...' if len(type_str) > 80 else ''}'")
    print(f"       Type First Word: '{type_first_word}'")
    print(f"       Name: '{name}'")
    print(f"       Match span: {m.start()}-{m.end()}")
    
    # 매칭된 전체 텍스트의 처음 100자
    match_text = m.group(0)
    print(f"       Match text (first 100): '{match_text[:100]}...'")
