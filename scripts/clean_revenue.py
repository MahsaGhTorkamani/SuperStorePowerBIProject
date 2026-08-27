"""Clean the Ziply Finance Revenue extract.

SegMtx is a CC.Matrix pair where each part is exactly three digits.

Two things have to happen for that to survive:
  1. Read the column as text. Pandas otherwise infers it as a float and
     drops the zeros: "991.010" becomes the number 991.01.
  2. Pad each part back to three digits. CC pads on the left (leading
     zeros) and Matrix pads on the right, because the matrix code is the
     fractional part and .01 and .010 are the same number - a float read
     upstream (Excel, a prior export) truncates its trailing zeros.
"""

import pandas as pd

BASE = r"C:\Users\mgg0951\OneDrive - Northwest Fiber LLC\BI_Reporting-SQL\BI_Reporting-SQL\Ziply_Finance_PL"
SRC = rf"{BASE}\Revenue.csv"
DST = rf"{BASE}\Revenue_cleaned.csv"

WIDTH = 3

# dtype=str keeps every column exactly as written in the file;
# keep_default_na=False stops blanks from turning into the string "nan".
df = pd.read_csv(SRC, dtype=str, keep_default_na=False)

# Trim stray whitespace only - never reformat the code itself.
df['SegMtx'] = df['SegMtx'].str.strip()

# Split SegMtx on the decimal point. partition keeps rows that have no
# decimal point instead of producing NaN.
parts = df['SegMtx'].str.partition('.')
cc_raw, matrix_raw = parts[0], parts[2]

# Restore each part to three digits.
df['CC'] = cc_raw.str.zfill(WIDTH)
df['Matrix'] = matrix_raw.str.ljust(WIDTH, '0')

# Anything wider than three digits means the CC.Matrix assumption is wrong
# for that row - report it rather than silently truncating.
too_wide = df[(df['CC'].str.len() > WIDTH) | (df['Matrix'].str.len() > WIDTH)]
if not too_wide.empty:
    print(f'WARNING: {len(too_wide)} row(s) have a part longer than {WIDTH} digits:')
    print(too_wide[['SegMtx', 'CC', 'Matrix']].drop_duplicates().to_string(index=False))

# Add constant Revenue column
df['Revenue'] = 'Revenue'

# Map CC to Segment_Name
cc_map = {
    '991': 'Residential',
    '992': 'SMB',
    '993': 'Enterprise',
    '994': 'Wholesales',
    '995': 'NFC',
}
df['Segment_Name'] = df['CC'].map(cc_map)

unmapped = sorted(set(df.loc[df['Segment_Name'].isna(), 'CC']))
if unmapped:
    print('WARNING: CC codes with no Segment_Name:', ', '.join(unmapped))

# Keep only the requested columns
df = df[['FPA Mapping', 'PLSect', 'SegMtx', 'CC', 'Matrix', 'Revenue', 'Segment_Name']]

# Remove duplicate rows
df = df.drop_duplicates()

df.to_csv(DST, index=False)

print('Done. Rows:', df.shape[0])
