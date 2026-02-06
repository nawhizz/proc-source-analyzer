# Pro*C Source Analyzer

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
- **동적 쿼리**:
    - 소스 코드 내의 `"..."` 문자열 리터럴을 검사하여 테이블명과 SQL 키워드가 함께 존재하는지 확인합니다.
    - **C언어 문자열 연결 지원**: `sprintf` 등에서 여러 줄에 걸쳐 작성된 문자열(`"..." \n "..."`)을 하나로 연결하여 분석합니다. 이를 통해 줄바꿈으로 인해 테이블명이나 키워드가 분리되어도 정확히 인식합니다.
- **MERGE 문**:
    - `WHEN MATCHED THEN UPDATE` 구문이 있으면 **UPDATE**로 분류합니다.
    - `WHEN NOT MATCHED THEN INSERT` 구문이 있으면 **INSERT**로 분류합니다.
    - `USING` 절에 사용된 테이블은 **SELECT**로 분류합니다.
    - **자기 참조 지원**: `MERGE`의 대상(Target) 테이블이 `USING` 절 등에서 다시 참조되는 경우, `UPDATE/INSERT`뿐만 아니라 **SELECT** 권한도 올바르게 추출합니다.

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
