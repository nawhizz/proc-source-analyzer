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
    
    # 모든 함수 정의 찾기
    func_matches_raw = list(func_pattern.finditer(content))
    
    # 예약어 필터링 (else if 등을 함수로 오인하는 경우 방지)
    # SQL 키워드(INSERT, UPDATE 등)가 Type이나 Name에 오는 경우도 제외
    RESERVED_WORDS = {
        'if', 'while', 'for', 'switch', 'catch', 'return', 'else', 
        'EXEC', 'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'FROM', 'WHERE', 'AND', 'OR',
        'do', 'case', 'default', 'break', 'continue', 'goto', 'sizeof', 'typedef', 'volatile'
    }
    
    func_matches = []
    
    for m in func_matches_raw:
        name = m.group('name')
        type_str = m.group('type').strip()
        
        # 1. 이름이 예약어인지 확인
        if name in RESERVED_WORDS:
            continue
            
        # 2. 반환 타입의 첫 단어가 예약어인지 확인 (예: INSERT INTO ...)
        # Type은 "int ", "char * " 등이므로 첫 단어만 추출해서 비교
        type_first_word = type_str.split()[0]
        if type_first_word in RESERVED_WORDS:
            continue
            
        func_matches.append(m)
            
    if not func_matches:
        print(f"[Warning] 함수 정의를 찾을 수 없습니다.")
        return

    # 각 함수별 시작/끝 지점 계산
    # ... (find_start_with_comment logic is same)
    
    def find_start_with_comment(content, func_start_index):
        # 역방향으로 한 줄씩 검사
        curr_idx = func_start_index
        
        # 앞쪽의 공백/줄바꿈 스킵
        while curr_idx > 0 and content[curr_idx-1].isspace():
            curr_idx -= 1
            
        # 바로 앞이 '*/' 인지 확인 (주석 끝)
        if curr_idx >= 2 and content[curr_idx-2:curr_idx] == '*/':
            # 주석 시작('/*') 찾기
            comment_end = curr_idx
            comment_start = content.rfind('/*', 0, comment_end)
            if comment_start != -1:
                return comment_start
        
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
