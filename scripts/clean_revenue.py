"""Clean the Ziply Finance Revenue extract.

SegMtx must be read as text: pandas otherwise infers it as a float and
silently drops the leading zero ("0991" -> 991) and the trailing zeros
of the matrix part ("991.0100" -> 991.01).
"""

import pandas as pd

BASE = r"C:\Users\mgg0951\OneDrive - Northwest Fiber LLC\BI_Reporting-SQL\BI_Reporting-SQL\Ziply_Finance_PL"
SRC = rf"{BASE}\Revenue.csv"
DST = rf"{BASE}\Revenue_cleaned.csv"

# dtype=str keeps every column exactly as written in the file;
# keep_default_na=False stops blanks from turning into the string "nan".
df = pd.read_csv(SRC, dtype=str, keep_default_na=False)

# Trim stray whitespace only - never reformat the code itself.
df['SegMtx'] = df['SegMtx'].str.strip()

# Split SegMtx into CC (before the decimal) and Matrix (after it).
# partition keeps rows that have no decimal point instead of producing NaN.
cc, _, matrix = zip(*df['SegMtx'].str.partition('.').itertuples(index=False))
df['CC'] = list(cc)
df['Matrix'] = list(matrix)

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
# Match on the zero-stripped code so 0991 and 991 both resolve,
# while the CC column itself keeps the digits exactly as in the file.
df['Segment_Name'] = df['CC'].str.lstrip('0').map(cc_map)

# Keep only the requested columns
df = df[['FPA Mapping', 'PLSect', 'SegMtx', 'CC', 'Matrix', 'Revenue', 'Segment_Name']]

# Remove duplicate rows
df = df.drop_duplicates()

df.to_csv(DST, index=False)

print('Done. Rows:', df.shape[0])
