# Pro*C Source Analyzer (proc_analyzer.py)

Pro*C 소스 코드(`*.pc`)를 분석하여 사용된 **테이블(TB_*)**과 해당 테이블에 수행된 **CRUD 작업(Select, Insert, Update, Delete)**을 추출하는 파이썬 도구입니다.

## 주요 기능

1.  **테이블 추출**: `TB_`로 시작하는 테이블 이름을 자동으로 식별합니다.
2.  **CRUD 분석**:
    - `EXEC SQL` 블록 내의 정적 쿼리 분석.
    - 문자열 리터럴(String Literal) 내의 동적 쿼리 분석.
    - `MERGE` 문의 상세 분석 (Insert/Update 작업 구분).
3.  **다중 라인 쿼리 지원**: 줄바꿈이 포함된 복잡한 SQL 문장도 정확히 파싱합니다.
3.  **다중 라인 쿼리 지원**: 줄바꿈이 포함된 복잡한 SQL 문장도 정확히 파싱합니다.
4.  **일괄 처리**: 단일 파일뿐만 아니라 폴더 지정 시 내부(**하위 폴더 포함**)의 모든 `*.pc` 파일을 일괄 분석합니다.

## 요구 사항

- Python 3.x

## 설치 및 실행

별도의 라이브러리 설치가 필요 없습니다. 파이썬이 설치된 환경에서 바로 실행 가능합니다.

```bash
git clone https://github.com/nawhizz/proc-source-analyzer.git
cd source-analysis
```

## 사용 방법

### 1. 단일 파일 분석

특정 Pro*C 파일 하나만 분석하고 싶을 때 사용합니다.

```bash
python proc_analyzer.py -f <파일경로>
# 또는
python proc_analyzer.py --file <파일경로>
```

**예시:**
```bash
python proc_analyzer.py -f test_sample.pc
```

### 2. 폴더 일괄 분석

특정 폴더에 있는 모든 `*.pc` 파일을 한 번에 분석합니다.

```bash
python proc_analyzer.py -d <폴더경로>
# 또는
python proc_analyzer.py --folder <폴더경로>
```

**예시:**
```bash
python proc_analyzer.py -d ./src
```
### 3. 일괄 분석 및 엑셀 저장

폴더 내의 모든 파일을 분석하고 결과를 엑셀 파일로 저장합니다.

```bash
python proc_analyzer.py -d <폴더명> -e <엑셀파일명.xlsx>
# 또는
python proc_analyzer.py --folder <폴더명> --excel <엑셀파일명.xlsx>
```

**예시:**
```bash
python proc_analyzer.py -d ./src -e result.xlsx
```

### 4. 엑셀 셀 병합 (옵션)

엑셀 저장 시 `Source Name`과 `Source Desc.`가 동일한 경우 해당 셀을 병합하여 가독성을 높입니다.

```bash
python proc_analyzer.py -d ./src -e result.xlsx -m
# 또는
python proc_analyzer.py -d ./src -e result.xlsx --merge
```

### 5. 인코딩 지정 (옵션)

기본적으로 `EUC-KR` 인코딩으로 파일을 읽습니다. 만약 `UTF-8` 등 다른 인코딩을 사용하는 경우 `--encoding` (또는 `-c`) 옵션을 사용하세요.

```bash
python proc_analyzer.py -f test_sample.pc --encoding utf-8
# 또는
python proc_analyzer.py -f test_sample.pc -c utf-8
```

## 분석 로직 상세

### 테이블 식별
### 테이블 식별
- 다음 정규표현식 패턴을 사용하여 테이블명을 추출합니다.
    - `\b((?:[A-Z0-9_]+\.)?(?:TB_|ATA_|EM_)[A-Z0-9_]+)\b`
- **지원 패턴**:
    - `TB_`로 시작하는 테이블 (예: `TB_USER`)
    - `ATA_`, `EM_`으로 시작하는 테이블 (예: `ATA_TALK`, `EM_MSG`)
    - 스키마가 포함된 테이블 (예: `NHPT.TB_CUSTOMER`, `NHPT_KATK.ATA_TALK`)

### 테이블명 정제
- **NHPT 스키마 제거**: `NHPT.` 스키마를 사용하는 테이블의 경우, 출력 시 스키마명을 제거합니다.
    - `NHPT.TB_NHPT_LOG` → `TB_NHPT_LOG` 로 출력됩니다.
    - 그 외 스키마(예: `NHPT_OTHER.TB_TEST`)는 그대로 출력됩니다.

### CRUD 식별
- **정적 쿼리**: `EXEC SQL ... ;` 블록 내부를 검사합니다.
- **동작 방식 개선 (Context-Aware)**:
    - 단순 키워드 매칭이 아니라, 문맥을 분석하여 정확도를 높였습니다.
    - `INSERT INTO`, `UPDATE`, `DELETE [FROM]`의 대상 테이블을 정확히 식별합니다.
    - **SELECT 식별 강화**: 
        - 테이블이 `FROM` 절이나 `JOIN` 절에 위치하는 경우에만 SELECT로 분류합니다.
        - 이를 통해 `SELECT List` 내의 컬럼명, `WHERE` 절, `UPDATE SET` 절 등에 포함된 테이블 유사 명칭(`ATA_ID` 등)이 오탐지되는 것을 방지합니다.
- **동적 쿼리**:
    - 소스 코드 내의 `"..."` 문자열 리터럴을 검사합니다.
    - **C언어 문자열 연결 지원**: `sprintf` 등에서 여러 줄(`"..." \n "..."`)로 작성된 쿼리를 하나로 연결하여 분석합니다.
    - **이스케이프 시퀀스 처리**: `\n`, `\t` 등 C언어 포맷팅 문자를 공백으로 치환하여 분석 정확도를 보장합니다.
- **MERGE 문**:
    - `WHEN MATCHED THEN UPDATE` → **UPDATE**
    - `WHEN NOT MATCHED THEN INSERT` → **INSERT**
    - `USING` 절 및 기타 참조 → **SELECT**
    - `re.DOTALL`을 적용하여 줄바꿈이 포함된 복잡한 MERGE 문도 정확히 파싱합니다.
- **SQL 힌트/주석 처리**: 
    - 쿼리 분석 전 `/* ... */` 주석과 힌트를 제거하여, 힌트 사이에 낀 키워드(`INSERT /*+ hint */ INTO`)도 정상 인식합니다.

### 소스 설명 추출
소스 파일 상단의 주석에서 다음 순서대로 키워드를 찾아 설명을 추출합니다.
1. `프로그램명 : ...`
2. `파일명(한글) : ...`
3. `Description : ...`
4. `Descritpion : ...` (오타 대응)

## 출력 예시

```text
Analysis Report for: test_sample.pc
Table Name                     | CRUD Operations
------------------------------------------------------------
TB_ACCOUNT                     | SELECT
TB_LOG                         | INSERT, UPDATE
TB_USER                        | SELECT, UPDATE
...
============================================================
```


# Pro*C 함수 분리 도구 (split_proc_functions.py)

하나의 거대한 Pro*C 공통 모듈 파일(예: `SC_MOG_COMMON.pc`)을 개별 함수 단위의 파일로 분리해주는 도구입니다.

## 1. 주요 기능
- **자동 분리**: 원본 파일에서 C 함수 정의를 찾아 개별 `.pc` 파일로 저장합니다.
- **주석 포함**: 함수 정의 바로 위에 있는 설명 주석(`/* ... */`)을 함께 추출합니다.
- **공통 헤더 제외**: 파일 상단의 공통 선언부(Preamble)는 제외하고, 순수 함수 내용만 추출합니다.
- **오탐지 필터**: 함수 파싱 시 `INSERT`, `if` 등 SQL 구문이나 제어문을 함수로 오인하지 않도록 필터링합니다.

## 2. 사용 방법

```bash
python split_proc_functions.py -f <원본파일> [-c <인코딩>]
```

- `-f, --file`: (필수) 분리할 대상 Pro*C 파일 경로.
- `-c, --encoding`: (선택) 파일 인코딩 (기본값: `euc-kr`).

## 3. 실행 예시

**기본 실행 (euc-kr):**
```bash
python split_proc_functions.py -f SC_MOG_COMMON.pc
```
명령을 실행하면 원본 파일명과 동일한 폴더(`SC_MOG_COMMON`)가 생성되고, 그 안에 `CF_START_SERVICE.pc`, `CF_END_SERVICE.pc` 등의 파일이 생성됩니다.

**UTF-8 파일 실행:**
```bash
python split_proc_functions.py -f MyFunctions.pc -c utf-8
```

## 4. 주의 사항
- 생성되는 파일의 인코딩은 원본 파일의 인코딩 설정(`-c`)을 따릅니다.
- `if (...) { ... }` 제어문이나 `EXEC SQL ...` 블록은 함수로 인식하지 않습니다.
