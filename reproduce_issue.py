import sys
import os
from collections import defaultdict
from proc_analyzer import extract_table_crud

def test_insert_select_issue():
    sql_text = """
    EXEC SQL
        INSERT INTO NHPT_SMS.EM_SMT_LOG_TABLE
             ( MT_PR
             , MT_REFKEY
             , PRIORITY
             , DATE_CLIENT_REQ
             , SUBJECT
             )
        SELECT NHPT_SMS.SQ_MMT_TRAN_01.NEXTVAL
             , NULL
             , 'VF'
             , :in_ifmb0034_rcv_dd.tr_dt || '100101'
             , C.TPL_EXPL
          FROM TB_MP_CO_CM_TPLMSTR
         WHERE C.ANCTOK_TPL_ID = 'MB0001'
           AND C.TPL_CLF_c     = '03'
           AND C.UG_YN         = 'Y'
        ;
    """
    
    print("Testing SQL:\n", sql_text)
    
    table_ops = defaultdict(set)
    extract_table_crud(sql_text, table_ops, source="TEST")
    
    print("\nResults:")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    # Assertions
    failures = []
    
    # Check EM_SMT_LOG_TABLE
    if 'INSERT' not in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should have INSERT")
    if 'SELECT' in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should NOT have SELECT")
        
    # Check TB_MP_CO_CM_TPLMSTR
    if 'SELECT' not in table_ops.get('TB_MP_CO_CM_TPLMSTR', []):
        failures.append("TB_MP_CO_CM_TPLMSTR should have SELECT")
    if 'INSERT' in table_ops.get('TB_MP_CO_CM_TPLMSTR', []):
        failures.append("TB_MP_CO_CM_TPLMSTR should NOT have INSERT")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)
    else:
        print("\nSUCCESS: Logic is correct (or reproduced failure if this script failed to assert)")

def test_dynamic_sql_issue():
    # Dynamic SQL simulation (concatenated strings)
    # Note: The analyzer handles string concatenation before passing to extract_table_crud,
    # so we can test extract_table_crud directly with the resulting string.
    sql_text = """
    "INSERT INTO NHPT_SMS.EM_SMT_LOG_TABLE ( MT_PR , MT_REFKEY , PRIORITY , DATE_CLIENT_REQ , SUBJECT ) "
    "SELECT NHPT_SMS.SQ_MMT_TRAN_01.NEXTVAL , NULL , 'VF' , :in_ifmb0034_rcv_dd.tr_dt || '100101' , C.TPL_EXPL "
    "FROM TB_MP_CO_CM_TPLMSTR "
    "WHERE C.ANCTOK_TPL_ID = 'MB0001' AND C.TPL_CLF_c = '03' AND C.UG_YN = 'Y'"
    """
    
    # Pre-process like the main analyzer does for dynamic SQL
    # Removing quotes and newlines to simulate the stitched query
    processed_sql = sql_text.replace('"\n    "', ' ').replace('"', '').strip()
    
    print("\nTesting Dynamic SQL:\n", processed_sql)
    
    table_ops = defaultdict(set)
    extract_table_crud(processed_sql, table_ops, source="TEST_DYNAMIC")
    
    print("\nResults (Dynamic):")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    failures = []
    # Check EM_SMT_LOG_TABLE
    if 'INSERT' not in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should have INSERT")
    if 'SELECT' in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should NOT have SELECT")
        
    # Check TB_MP_CO_CM_TPLMSTR
    if 'SELECT' not in table_ops.get('TB_MP_CO_CM_TPLMSTR', []):
        failures.append("TB_MP_CO_CM_TPLMSTR should have SELECT")
    if 'INSERT' in table_ops.get('TB_MP_CO_CM_TPLMSTR', []):
        failures.append("TB_MP_CO_CM_TPLMSTR should NOT have INSERT")

    if failures:
        print("\nFAILURES (Dynamic):")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)
    else:
        print("\nSUCCESS (Dynamic): Logic is correct")

def test_hinted_sql_issue():
    # Helper for hinted SQL
    sql_text = """
    INSERT /*+ MBBT02143 */ INTO NHPT_SMS.EM_SMT_LOG_TABLE
         ( MT_PR
         , MT_REFKEY
         )
    SELECT NHPT_SMS.SQ_MMT_TRAN_01.NEXTVAL
         , NULL
      FROM TB_MP_CO_CM_TPLMSTR
    ;
    """
    
    print("\nTesting Hinted SQL:\n", sql_text)
    
    table_ops = defaultdict(set)
    extract_table_crud(sql_text, table_ops, source="TEST_HINT")
    
    print("\nResults (Hinted):")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    failures = []
    # Check EM_SMT_LOG_TABLE
    if 'INSERT' not in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should have INSERT (failed due to hint?)")
    if 'SELECT' in table_ops.get('EM_SMT_LOG_TABLE', []):
        failures.append("EM_SMT_LOG_TABLE should NOT have SELECT")

    if failures:
        print("\nFAILURES (Hinted):")
        for f in failures:
            print(f"- {f}")
        # Not exiting here to allow seeing all results if needed, but in CI we would.
        # returning False to indicate failure
        return False
    else:
        print("\nSUCCESS (Hinted): Logic is correct")
        return True

def test_string_literal_issue():
    # Simulation of C code error message containing table name
    # But note: analyze_file extracts the string. 
    # Here we test extract_table_crud with that string.
    
    # Case: "NHPT_SMS.EM_SMT_LOG_TABLE insert error"
    # It has "insert" (case insensitive match potential) but not "INSERT INTO" pattern
    # It does NOT have "SELECT"
    
    error_msg = '"NHPT_SMS.EM_SMT_LOG_TABLE insert error"'
    # The analyzer strips outer quotes if they exist in the capture or processes content
    # But extract_table_crud receives the raw text associated with the potential match diff.
    # In analyze_file: `if any(...) extract_table_crud(sql_string ...)`
    
    # Let's test the string content directly as passed to extract_table_crud
    sql_text = "NHPT_SMS.EM_SMT_LOG_TABLE insert error"
    
    print("\nTesting String Literal (Error Message):\n", sql_text)
    
    table_ops = defaultdict(set)
    extract_table_crud(sql_text, table_ops, source="TEST_STRING")
    
    print("\nResults (String Literal):")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    failures = []
    # Check EM_SMT_LOG_TABLE
    # Should NOT have extracted any operations (or at least not SELECT)
    # The user says it shows as "INSERT, SELECT" (or just SELECT if regex fixed INSERT)
    # Actually user says: "해당 테이블이 SELECT 처리된 것 처럼 출력되고 있어" -> It implies it found SELECT.
    
    if table_ops.get('EM_SMT_LOG_TABLE'):
        # If it found operations, verify they are correct (which implies NONE for a log message)
        # But wait, if analysis finds "Table Name", maybe just reporting "Table" without ops is better?
        # But current logic is "Table Name | Operations".
        if 'SELECT' in table_ops['EM_SMT_LOG_TABLE']:
            failures.append("EM_SMT_LOG_TABLE should NOT be marked as SELECT in an error message")
        if 'INSERT' in table_ops['EM_SMT_LOG_TABLE']:
            failures.append("EM_SMT_LOG_TABLE should NOT be marked as INSERT in an error message")

    if failures:
        print("\nFAILURES (String Literal):")
        for f in failures:
            print(f"- {f}")
        return False
    else:
        print("\nSUCCESS (String Literal): Correctly ignored / no false ops")
        return True

def test_column_confusion_issue():
    # Case: ATA_ID is a column name, but starts with ATA_ so regex picks it up.
    # It appears in the column list of an INSERT statement.
    sql_text = """
    EXEC SQL
        INSERT /*+ MBBT02143 */ INTO NHPT_KATK.ATA_SMT_LOG_TABLE
             ( MT_PR
             , MT_REFKEY
             , ATA_ID
             , DATE_CLIENT_REQ
             , SUBJECT
             )
        SELECT NHPT_SMS.SQ_MMT_TRAN_01.NEXTVAL
             , NULL
             , 'VF'
             , :in_ifmb0034_rcv_dd.tr_dt || '100101'
             , C.TPL_EXPL
          FROM TB_MP_CO_CM_TPLMSTR
         WHERE C.ANCTOK_TPL_ID = 'MB0001'
           AND C.TPL_CLF_c     = '03'
           AND C.UG_YN         = 'Y'
        ;
    """
    
    print("\nTesting Column Confusion (ATA_ID):\n", sql_text)
    
    table_ops = defaultdict(set)
    extract_table_crud(sql_text, table_ops, source="TEST_COLUMN")
    
    print("\nResults (Column Confusion):")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    failures = []
    # Check ATA_ID
    if 'ATA_ID' in table_ops:
        failures.append(f"ATA_ID should NOT be identified as a table. Found operations: {table_ops['ATA_ID']}")
        
    # Check Real Tables
    if 'INSERT' not in table_ops.get('ATA_SMT_LOG_TABLE', []):
        failures.append("ATA_SMT_LOG_TABLE should have INSERT")
    if 'SELECT' not in table_ops.get('TB_MP_CO_CM_TPLMSTR', []):
        failures.append("TB_MP_CO_CM_TPLMSTR should have SELECT")

    if failures:
        print("\nFAILURES (Column Confusion):")
        for f in failures:
            print(f"- {f}")
        return False
    else:
        print("\nSUCCESS (Column Confusion): ATA_ID ignored")
        return True

def test_context_collision_issue():
    # Case: ATA_ID used in SELECT list, WHERE clause, etc.
    sql_text = """
    EXEC SQL
        SELECT ATA_ID
             , DATE_CLIENT_REQ
             , SUBJECT
          FROM NHPT_KATK.ATA_SMT_LOG_TABLE
         WHERE ATA_ID = :id
    ;
    """
    
    print("\nTesting Context Collision (SELECT):\n", sql_text)
    table_ops = defaultdict(set)
    extract_table_crud(sql_text, table_ops, source="TEST_CTX_SEL")
    
    failures = []
    if 'ATA_ID' in table_ops:
        failures.append(f"[SELECT] ATA_ID should NOT be identified as a table. Found: {table_ops['ATA_ID']}")
    if 'SELECT' not in table_ops.get('ATA_SMT_LOG_TABLE', []):
        failures.append("[SELECT] ATA_SMT_LOG_TABLE should have SELECT")

    # UPDATE Case
    sql_update = """
    EXEC SQL
        UPDATE NHPT_KATK.ATA_SMT_LOG_TABLE
           SET ATA_ID = 'NEW'
         WHERE ATA_ID = 'OLD'
    ;
    """
    print("\nTesting Context Collision (UPDATE):\n", sql_update)
    table_ops_upd = defaultdict(set)
    extract_table_crud(sql_update, table_ops_upd, source="TEST_CTX_UPD")
    
    if 'ATA_ID' in table_ops_upd:
        failures.append(f"[UPDATE] ATA_ID should NOT be identified as a table. Found: {table_ops_upd['ATA_ID']}")
    if 'UPDATE' not in table_ops_upd.get('ATA_SMT_LOG_TABLE', []):
        failures.append("[UPDATE] ATA_SMT_LOG_TABLE should have UPDATE")

    # DELETE Case
    sql_delete = """
    EXEC SQL
        DELETE FROM NHPT_KATK.ATA_SMT_LOG_TABLE
         WHERE ATA_ID = 'DEL'
    ;
    """
    print("\nTesting Context Collision (DELETE):\n", sql_delete)
    table_ops_del = defaultdict(set)
    extract_table_crud(sql_delete, table_ops_del, source="TEST_CTX_DEL")
    
    if 'ATA_ID' in table_ops_del:
        failures.append(f"[DELETE] ATA_ID should NOT be identified as a table. Found: {table_ops_del['ATA_ID']}")
    if 'DELETE' not in table_ops_del.get('ATA_SMT_LOG_TABLE', []):
        failures.append("[DELETE] ATA_SMT_LOG_TABLE should have DELETE")

    if failures:
        print("\nFAILURES (Context Collision):")
        for f in failures:
            print(f"- {f}")
        return False
    else:
        print("\nSUCCESS (Context Collision): ATA_ID consistently ignored in non-table positions")
        return True

if __name__ == "__main__":
    test_insert_select_issue()
    test_dynamic_sql_issue()
    test_hinted_sql_issue()
    test_string_literal_issue()
    test_column_confusion_issue()
    test_context_collision_issue()
