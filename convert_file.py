import os

input_file = "test_sample.pc"
output_file = "test_sample_euckr.pc"

try:
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    with open(output_file, "w", encoding="euc-kr") as f:
        f.write(content)

    print(f"Successfully converted {input_file} to {output_file} (EUC-KR).")
    
    os.remove(input_file)
    print(f"Deleted {input_file}.")
    
except Exception as e:
    print(f"Error: {e}")
