import os
import re
import argparse
import sys

def split_proc_functions(file_path, encoding='euc-kr'):
    """
    Pro*C 공통 코드 파일을 읽어서 함수별로 파일을 분리하는 스크립트입니다.
    
    1. 파일명 기반으로 디렉토리를 생성합니다. (예: SC_MOG_COMMON.pc -> SC_MOG_COMMON/)
    2. 파일 내용을 읽어 첫 번째 함수가 나오기 전까지의 내용을 '공통 헤더(Preamble)'로 저장합니다.
    3. 'FUNCTION ID :' 패턴을 기준으로 함수들을 식별합니다.
    4. 각 함수를 추출하여 '공통 헤더 + 함수 내용' 조합으로 개별 파일에 저장합니다.
    """
    
    # 1. 파일명 파싱 및 디렉토리 생성
    base_name = os.path.basename(file_path)
    file_stem = os.path.splitext(base_name)[0] # SC_MOG_COMMON
    output_dir = os.path.join(os.path.dirname(file_path), file_stem)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[Info] 디렉토리 생성: {output_dir}")
    else:
        print(f"[Info] 디렉토리 존재: {output_dir}")

    # 2. 파일 읽기
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
    except UnicodeDecodeError as e:
        print(f"[Error] 파일 인코딩 오류 ({encoding}): {e}")
        return
    except Exception as e:
        print(f"[Error] 파일 읽기 오류: {e}")
        return

    # Regex 설명:
    # ^ : 라인 시작 (MULTILINE 모드)
    # \s* : 공백
    # (?P<type>...) : 반환타입.
    # (?P<name>\w+) : 함수명.
    # \s*\( : 괄호 열기
    # (?P<params>...) : 파라미터. 세미콜론(;)을 포함하지 않음 (단, 주석 내부는 허용).
    # \)\s*\{ : 괄호 닫고 중괄호 열기
    
    # 파라미터 Regex 상세:
    # (?:
    #   [^;/]          : 세미콜론과 슬래시를 제외한 모든 문자
    #   | / (?!\*)     : 주석 시작(/ *)이 아닌 슬래시 (나눗셈 등)
    #   | /\*.*?\*/    : 주석 블록 (내부에 세미콜론 있어도 됨)
    # )*?              : 위 패턴의 0회 이상 반복 (Non-greedy)
    
    # 주의: re.VERBOSE 모드 사용 시 공백이 무시되므로 패턴 내 공백 주의해야 함.
    # 여기서는 VERBOSE 안쓰고 한줄로 작성.
    
    # params_pattern = r'(?:[^;/]|\/(?!\*)|\/\*.*?\*\/)*?'
    
    func_pattern = re.compile(
        r'^\s*(?P<type>(?:[a-zA-Z0-9_]+\s+(?:\*\s*)?)+)(?P<name>[a-zA-Z0-9_]+)\s*\((?P<params>(?:[^;/]|\/(?!\*)|\/\*.*?\*/)*?)\)\s*\{',
        re.MULTILINE | re.DOTALL
    )
    
    # 예약어 필터링 (else if 등을 함수로 오인하는 경우 방지)
    # SQL 키워드(INSERT, UPDATE 등)가 Type이나 Name에 오는 경우도 제외
    # SQL 함수(TO_NUMBER, TO_CHAR 등)도 제외
    RESERVED_WORDS = {
        # C 언어 제어문/키워드
        'if', 'while', 'for', 'switch', 'catch', 'return', 'else', 
        'do', 'case', 'default', 'break', 'continue', 'goto', 'sizeof', 'typedef', 'volatile',
        
        # SQL DML/DDL 키워드
        'EXEC', 'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'FROM', 'WHERE', 'AND', 'OR',
        'CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'MERGE', 'INTO', 'VALUES', 'ELSE',
        
        # SQL 함수 (Oracle 등)
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
    
    def is_real_function(match):
        """
        매칭이 실제 함수 정의인지 판별합니다.
        이름이나 반환 타입의 첫 단어가 예약어이면 False를 반환합니다.
        """
        name = match.group('name')
        type_str = match.group('type').strip()
        
        # 1. 이름이 예약어인지 확인
        if name in RESERVED_WORDS:
            return False
            
        # 2. 반환 타입의 첫 단어가 예약어인지 확인 (예: INSERT INTO ...)
        type_first_word = type_str.split()[0]
        if type_first_word in RESERVED_WORDS:
            return False
            
        return True
    
    # 함수 찾기: search + while 루프 방식
    #
    # 핵심 문제: finditer는 non-overlapping 매칭만 반환합니다.
    # CASE WHEN LENGTH(...) 같은 SQL 구문이 regex에 넓은 범위로 매칭되면,
    # 그 범위 안에 있는 실제 함수 정의(예: AL_COM_OFFRBRK_U01)를 삼킵니다.
    #
    # 해결책: search()로 하나씩 찾으면서,
    # 가짜 매칭(예약어)이면 다음 줄부터 다시 검색합니다.
    func_matches = []
    search_pos = 0
    
    while search_pos < len(content):
        m = func_pattern.search(content, search_pos)
        if m is None:
            break
            
        if is_real_function(m):
            # 실제 함수 → 결과에 추가, 매칭 끝 이후부터 계속 검색
            func_matches.append(m)
            search_pos = m.end()
        else:
            # 가짜 매칭(예약어) → 다음 줄 시작부터 재검색
            # 이렇게 하면 가짜 매칭이 삼킨 영역 안의 실제 함수도 찾을 수 있음
            next_newline = content.find('\n', m.start())
            if next_newline != -1:
                search_pos = next_newline + 1
            else:
                break
            
    if not func_matches:
        print(f"[Warning] 함수 정의를 찾을 수 없습니다.")
        return

    # 각 함수별 시작/끝 지점 계산
    # ... (find_start_with_comment logic is same)
    
    def find_start_with_comment(content, func_start_index):
        """
        함수 정의 시작점 앞에 있는 주석 블록의 시작 위치를 찾습니다.
        
        지원하는 주석 스타일:
        1. 블록 주석: /* ... */ (여러 줄에 걸친 단일 주석)
        2. 반복 단일 줄 주석: /* ... */ \n /* ... */ \n ... (각 줄이 /* */로 감싸짐)
        
        주의: 인라인 주석(코드 뒤에 붙은 주석)은 함수 설명으로 간주하지 않습니다.
        예: time_t sec; /* Time.h */ <- 이것은 인라인 주석이므로 제외
        """
        
        def is_block_comment_start(content, comment_start_idx):
            """
            주석이 라인의 시작 부분에서 시작하는지 확인합니다.
            (인라인 주석이 아닌 블록 주석인지 판별)
            """
            # 주석 시작 위치에서 역방향으로 탐색하여 해당 라인의 시작 찾기
            line_start = comment_start_idx
            while line_start > 0 and content[line_start - 1] != '\n':
                line_start -= 1
            
            # 라인 시작부터 주석 시작까지의 내용 확인
            before_comment = content[line_start:comment_start_idx]
            
            # 공백만 있으면 블록 주석 (함수 설명 주석)
            # 공백 외 다른 문자가 있으면 인라인 주석
            return before_comment.strip() == ''
        
        curr_idx = func_start_index
        
        # 앞쪽의 공백/줄바꿈 스킵
        while curr_idx > 0 and content[curr_idx-1].isspace():
            curr_idx -= 1
            
        # 바로 앞이 '*/' 인지 확인 (주석 끝)
        if curr_idx >= 2 and content[curr_idx-2:curr_idx] == '*/':
            # 주석 끝 위치 저장
            comment_end = curr_idx
            
            # 현재 주석 블록의 시작 찾기
            current_comment_start = content.rfind('/*', 0, comment_end)
            
            if current_comment_start == -1:
                return curr_idx  # 주석 시작을 못 찾으면 함수 시작점 반환
            
            # 인라인 주석인지 확인
            if not is_block_comment_start(content, current_comment_start):
                # 인라인 주석이면 함수 정의 시작점(공백 제외) 사용
                return curr_idx
                
            # 블록 주석인 경우, 앞에 더 연속된 주석이 있는지 확인
            final_start = current_comment_start
            
            search_idx = current_comment_start
            while search_idx > 0:
                # 공백/줄바꿈 스킵
                temp_idx = search_idx
                while temp_idx > 0 and content[temp_idx-1].isspace():
                    temp_idx -= 1
                    
                # 바로 앞이 '*/' 인지 확인
                if temp_idx >= 2 and content[temp_idx-2:temp_idx] == '*/':
                    # 이전 주석 블록 찾기
                    prev_comment_end = temp_idx
                    prev_comment_start = content.rfind('/*', 0, prev_comment_end)
                    
                    if prev_comment_start != -1:
                        # 이전 주석이 블록 주석인지 확인
                        if is_block_comment_start(content, prev_comment_start):
                            # 함수 설명의 일부로 포함
                            final_start = prev_comment_start
                            search_idx = prev_comment_start
                        else:
                            # 인라인 주석이면 여기서 중단
                            break
                    else:
                        break
                else:
                    # 더 이상 주석이 없음
                    break
                    
            return final_start
        
        # 주석이 없으면 함수 정의 시작점(공백 제외) 사용
        return curr_idx

    final_blocks = []
    
    for i, match in enumerate(func_matches):
        func_name = match.group('name')
        match_start = match.start()
        
        # 1. 주석 포함 시작점 찾기
        real_start = find_start_with_comment(content, match_start)
        
        # 2. 끝점 찾기
        if i + 1 < len(func_matches):
            next_match_start = func_matches[i+1].start()
            next_real_start = find_start_with_comment(content, next_match_start)
            real_end = next_real_start
        else:
            real_end = len(content)
            
        # 내용 추출
        block_content = content[real_start:real_end].rstrip() # 뒤 공백 제거
        
        final_blocks.append({
            'name': func_name,
            'content': block_content
        })

    print(f"[Info] 총 {len(final_blocks)}개의 함수를 찾았습니다.")

    # 파일 쓰기
    for block in final_blocks:
        func_name = block['name']
        output_filename = f"{func_name}.pc"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            # 사용자가 지정한 인코딩(encoding)으로 저장
            with open(output_path, 'w', encoding=encoding) as out_f:
                out_f.write(block['content'])
            print(f"[Success] 파일 생성: {output_path}")
        except Exception as e:
            print(f"[Error] 파일 쓰기 오류 ({output_filename}): {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pro*C Function Splitter")
    
    # -f / --file : 필수 입력 (argparse 레벨에서는 optional로 두고, 코드에서 체크)
    parser.add_argument("-f", "--file", help="Target Pro*C file path")
    
    # -c / --encoding : 선택 입력 (기본값 euc-kr)
    parser.add_argument("-c", "--encoding", default="euc-kr", help="File encoding (default: euc-kr)")
    
    args = parser.parse_args()
    
    # 인자가 없으면 도움말 출력
    if not args.file:
        parser.print_help()
        sys.exit(1)
        
    target_file = args.file
    
    if os.path.exists(target_file):
        print(f"[Info] 파일 분석 시작: {target_file} (Encoding: {args.encoding})")
        split_proc_functions(target_file, encoding=args.encoding)
    else:
        print(f"[Error] 파일이 존재하지 않습니다: {target_file}")
        sys.exit(1)
