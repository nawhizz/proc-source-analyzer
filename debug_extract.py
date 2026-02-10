import re

with open('SC_MOG_COMMON.pc', 'r', encoding='euc-kr') as f:
    lines = f.readlines()

# 함수 정의 패턴과 CASE WHEN 관련 라인 출력
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if any(kw in stripped for kw in ['AL_COM_NEWMCHTMSTR', 'AL_COM_OFFRBRK', 'CASE WHEN LENGTH', 'ELSE', 'void ', 'int ', 'char ']):
        if any(kw in stripped for kw in ['AL_COM_NEWMCHTMSTR', 'AL_COM_OFFRBRK', 'CASE WHEN', 'ELSE']):
            # 앞뒤 2줄 포함
            for j in range(max(1, i-2), min(len(lines)+1, i+3)):
                print(f"{j:4d}: {lines[j-1].rstrip()}")
            print("---")
