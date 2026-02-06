import sys
import os
from collections import defaultdict
from proc_analyzer import extract_table_crud

def test_merge_issue():
    # User provided MERGE statement simulation
    # Pre-concatenated string as if extracted by the analyzer
    sql_text = """
     MERGE /*+ SABT00022.pc|uf_tb_k6 */ INTO NHPT.TB_MP_MB_MH_SLCALCUZINF A    
                    USING (                                      
                   	SELECT A.SLCL_DT                          
                   	     , TRIM(B.RMK) AS RMK                 
                   	  FROM NHPT.TB_MP_MB_MH_SLCALCUZINF A     
                   	     , NHPT_CC.T_BUSS_DT                  
                   	 WHERE A.SLCL DT   = B.SOLAR_DT           
                   	   AND A.SLCL DT   >= '%s'                
                   	   AND A.DOW_C     IS NOT NULL            
                   	   AND A.HLDY_DSC  = '0'                  
                   	   AND B.CNTR_CD   = '10'                 
                   	   AND B.HLD_YN    = 'Y'                  
                    ) B                                          
                    ON (A.SLCL_DT = B.SLCL_DT)                   
                    WHEN MATCHED THEN                            
				    UPDATE SET A.HLDY_DSC   = '1'                
                   	, A.RMK        = B.RMK                    
    """
    
    print("\nTesting MERGE Issue:\n", sql_text)
    
    table_ops = defaultdict(set)
    # The analyzer strips comments before processing MERGE? 
    # extract_table_crud does cleaning first.
    extract_table_crud(sql_text, table_ops, source="TEST_MERGE")
    
    print("\nResults (MERGE):")
    for table, ops in table_ops.items():
        print(f"{table}: {sorted(ops)}")
    
    failures = []
    target_table = "TB_MP_MB_MH_SLCALCUZINF"
    ops = table_ops.get(target_table, set())
    
    if 'UPDATE' not in ops:
        failures.append(f"{target_table} missing UPDATE")
    if 'SELECT' not in ops:
        failures.append(f"{target_table} missing SELECT (it is used in USING clause too)")
        
    if failures:
        print("\nFAILURES (MERGE):")
        for f in failures:
            print(f"- {f}")
        sys.exit(1)
    else:
        print("\nSUCCESS (MERGE): Correct operations found")

if __name__ == "__main__":
    test_merge_issue()
