# P&L Matrix — Build Guide

Builds the hand-drawn P&L structure as a Power BI matrix, where each of the
three visible columns pulls its labels from a **different source table**
depending on which section (Revenue / COGS / OPEX) the row belongs to.

All DAX is in [`PL_Hierarchy.dax`](./PL_Hierarchy.dax).

## The mapping

| Matrix column | Revenue | COGS | OPEX |
|---|---|---|---|
| **Level 1** (Revenue / COGS / OPEX) | `TBData[LineItem]` = `"Revenue"` | `TBData[LineItem]` = `"COGS"` **and** `TBData[Segment]` < 116 | `TBData[Account Desc]` found in `OPEXMap[CTDesc]` |
| **Level 2** (blue) | *driven by `TBData[Cc]` alone — same gates for all three sections (see below)* | | |
| **Level 3** (red) | *driven by three membership gates — see below* | | |
| **Level 4** (green) | *not specified — see open questions* | *(sketch stops at L3)* | *not specified* |

Level 1 runs **four gates in strict order** — first match wins:

| # | Test | Result |
|---|---|---|
| 1 | `TBData[LineItem]` = `"Revenue"` | `Revenue` |
| 2 | `LineItem` = `"COGS"` **and** `Segment` < 116 | `COGS` |
| 3 | `Account Desc` appears in `OPEXMap[CTDesc]` | `OPEX` |
| 4 | otherwise | `LineItem`, or `Unmapped` if that is blank |

Gate 2 is a *release valve*, not a filter: a COGS row with `Segment` ≥ 116
falls through to gate 3 where it can be reclassified as OPEX. If it isn't in
`OPEXMap` either, gate 4 returns `COGS` anyway — its own `LineItem`. No row is
lost by failing the Segment test.

All three inputs — `LineItem`, `Segment`, `Account Desc` — are columns on
`TBData`, and the OPEX test uses `ALL()`, so **Level 1 needs no relationships
at all**.

The `Primary Group` department list no longer classifies Level 1.

### Level 2 gates

Level 2 no longer branches on the section — `TBData[Cc]` alone decides the
label, first match wins:

| # | Test | Result |
|---|---|---|
| 1 | `Cc` = 991 … 995 | `Total Residential / SMB / Enterprise / Wholesale / NFC Revenue` |
| 2 | `Matrix` = 286 | `Bonus` |
| 3 | `Cc` found in `CCMap[CCCode]` | `CCMap[Primary Group]` |
| 4 | `Cc` in the fixed code list | `nnn-Description` (e.g. `078-Pole and Conduit Rentals`) |
| 5 | otherwise | blank |

The fixed list covers `Cc` 1, 2, 11, 21, 22, 24, 25, 27, 31, 32, 78, 79, 97,
106, 116. Codes 22 and 24 carry no description, so their label is just the
padded number.

### Level 3 gates

Also section-independent — three membership tests, first match wins:

| # | Test | Result |
|---|---|---|
| 1 | `InternalRevMap` in `RevMap[RevIndex]` | `LineItem` & `" "` & `RevMap[PLSect_cleaned]` |
| 2 | `Account Desc` in `COGSMap[CTDesc]` | `COGSMap[CTDesc Parent]` |
| 3 | `Cc` in `CCMap[CCCode]` | `CCMap[CostCenter]` |
| 4 | otherwise | blank |

Gate 1's result is wrapped in `TRIM()`: DAX treats a blank operand in `&` as an
empty string, and `" Resi Data"` groups as a different matrix row from
`"Resi Data"`.

## Why calculated columns and not three separate visuals

The three sections have to stack in **one** matrix, so all three need to
resolve to the *same* three physical columns. Materialising `PL Level 1..3`
on `TBData` — the table that holds the amounts — does exactly that: a single
`SWITCH` per level picks the right source, and the matrix then sees one plain
hierarchy. Any approach that keeps the labels in their home tables ends up
needing three visuals stitched together, which breaks subtotals and sorting.

## Build steps

1. **Dedupe the map tables** — no relationships are needed at all. Every
   cross-table read uses `LOOKUPVALUE` with an explicit key and every
   membership test uses `IN ALL()`, so nothing depends on a relationship
   existing or on which way its arrow points.

   But `LOOKUPVALUE` **errors** on duplicate keys rather than picking one, so
   these four must be unique on their key before any column will evaluate:

   | Table | Key |
   |---|---|
   | `RevMap` | `RevIndex` |
   | `COGSMap` | `CTDesc` |
   | `CCMap` | `CCCode` |
   | `OPEXMap` | `CTDesc` (membership only — duplicates are harmless here) |

   In Power Query: Trim the key column → Group By it filtered to Count > 1 to
   see what's duplicated → Remove Duplicates.

   Add many-to-one relationships and swap `LOOKUPVALUE` for `RELATED()` only
   if you want the speed on a large trial balance.

2. **Add the calculated columns** to `TBData`, in this order (each one
   references the previous): `PL Level 1`, `PL Level 2`, `PL Level 3`,
   then the two `... Sort` columns. Replace every `*** KEY ***` placeholder
   with your real join columns first.

3. **Set the sort order**: select `PL Level 1` → Column tools → *Sort by
   column* → `PL Level 1 Sort`. Repeat for `PL Level 2` → `PL Level 2 Sort`.

4. **Add the measures** (`Amount`, `Total Revenue`, `Total COGS`,
   `Gross Profit`, `Total OPEX`, `Adjusted EBITDA`, `Gross Margin %`,
   `Adjusted EBITDA Margin %`).

   ```dax
   Adjusted EBITDA := [Total Revenue] - [Total COGS] - [Total OPEX]
   ```

5. **Build the matrix**:
   - *Rows*: `PL Level 1`, `PL Level 2`, `PL Level 3` (in that order)
   - *Columns*: your period column (`Date[Month]` or similar) — this is the
     `X` grid in the sketch
   - *Values*: `[Amount]`
   - Format pane → *Row subtotals* **On**, and set *Stepped layout* **Off**
     so each level gets its own indented column like the drawing.

6. **Calculated rows — Total Revenue, Gross Profit, Adjusted EBITDA**: these
   cannot be values of `PL Level 1`. That column is a *calculated column*, so
   every value it produces is a label stamped on a real trial-balance row.
   Adjusted EBITDA is arithmetic **across** three sections, not a set of rows,
   so there is nothing for the column to label. Two ways to get the rows:
   - **Approach A (start here)** — keep the hierarchy matrix and show
     `[Gross Profit]` and `[Adjusted EBITDA]` in cards or a one-row matrix
     beneath it. Nothing to build beyond the measures; always correct.
   - **Approach B** — drive the matrix rows from the disconnected `PL Layout`
     table and use `[PL Value]` instead of `[Amount]`. Gives the exact sketch
     layout, Adjusted EBITDA included. Full setup in the `.dax` file.

## Validation

After step 2, drop `PL Level 1` into a table visual with `[Amount]`. You should
see exactly `Revenue`, `COGS`, `OPEX` and nothing else. Any rows landing under
**"Unmapped"** are trial-balance accounts that are neither an OPEX department
nor resolvable through `BellcorpMap` — chase those before trusting the totals.

Then check each gate separately with two throwaway columns (they're in the
`.dax` file): `Debug Segment` and `Debug InOpex`. Put them beside
`TBData[LineItem]` and `PL Level 1` in a table with `[Amount]`. A row on `Unmapped` has both a
blank `LineItem` **and** no `OPEXMap` match — that's the list for Finance.

Finally check that `[Adjusted EBITDA]` reconciles to the figure Finance
already reports.

## Open questions

1. **Level 4 (green column)** — you specified sources for the first three
   columns only. The sketch shows `FTR Internet` / `Vantage Internet` /
   `Residential` / `Business` under Revenue and `Salaries & Wages` /
   `Payroll Taxes` under OPEX. My guess is the account description off
   `TBData`; the column is stubbed with `TBData[Account Description]` and
   marked `*** CONFIRM ***`.
2. ~~`COGSMap` join key~~ — **resolved**: joins `TBData[Account Desc]` to
   `COGSMap[CTDesc]`.
3. ~~`TBData` → `BellPLMap` join key~~ — **resolved**: `LineItem` is read
   straight off `TBData`, so the bridge is no longer used by this report.
4. ~~`CCMap[Cost Center]`~~ — **resolved**: `CCCode` is the key,
   `CostCenter` is the label fetched at Level 3.
5. **Sign convention** — the DAX assumes costs are stored positive. If your
   TB carries them as negatives, every subtraction becomes an addition:
   `Adjusted EBITDA := [Total Revenue] + [Total COGS] + [Total OPEX]`.
   This one silently produces plausible-looking wrong numbers, so check a
   COGS row in Data view before trusting the output.
6. **`078` / `106`** — I read these as cost-center codes appearing as COGS
   Level 2, which matches `TBData[Cc]` feeding that slot. Confirm.
7. ~~`TBData[Primary Group]` vs `CCMap[Primary Group Label]`~~ — **resolved**:
   Level 2 now reads `TBData[Primary Group]` directly. `CCMap` is no longer
   used at Level 2 at all, though it is still required for Level 3.
8. **OPEX department order** — `PL Level 2 Sort` orders them direct
   operations → commercial → support → overhead, with `Bonus` last.
   Renumber to match how Finance presents the P&L.
9. **`Matrix` data type** — the `= 286` test assumes a numeric column. If
   `Matrix` is text the comparison never matches and every bonus row keeps
   its department name, with no error raised. Check Column tools → Data type
   and quote the literal (`= "286"`) if it is text.
10. **Bonus placement** — pulling Matrix 286 up to Level 2 means bonus is
    reported as its own line and department subtotals **exclude** it. If
    bonus should instead sit under each department, move the override into
    `PL Level 3` (shown inline in the `.dax` file) and leave Level 2 alone.
11. ~~Two routes to Bonus~~ — **resolved**: with the OPEX branch reading
    `IF ( Matrix = 286, "Bonus", Primary Group )`, both routes land on
    `"Bonus"` by construction and cannot disagree.
12. **Is it EBITDA or operating income?** — EBITDA excludes Depreciation and
    Amortisation. `Revenue − COGS − OPEX` is what you specified and is what
    the measure does, but if D&A accounts sit inside any of the 12 OPEX
    departments the result is operating income, not EBITDA. If they do, they
    need filtering out of `Total OPEX` (pattern shown in the `.dax` file).
13. **"Adjusted"** — the name usually implies add-backs (one-off items,
    stock comp, management fees). None are applied here. If Finance's
    Adjusted EBITDA carries add-backs, they need adding to the measure.
14. **Bonus rule retained** — the `Matrix` = 286 → `"Bonus"` override was not
    restated in the Level 2 respec but has not been retracted, so it is kept
    at gate 2 (after the revenue roll-ups, before `CCMap`). Delete the line if
    bonus should now come through `CCMap` like any other cost centre.
15. **Gate 5 returns blank** — as specified. A blank Level 2 renders as an
    empty row header, making those amounts easy to miss in reconciliation.
    `"Unmapped Cc " & _Cc` would surface them instead, matching how Level 1
    handles its misses.
16. **Duplicate `CCCode` in `CCMap`** — `LOOKUPVALUE` *errors* on duplicate
    keys rather than picking one. Dedupe `CCMap` on `CCCode` in Power Query
    (Group By → Count > 1 first, to see what you'd drop).
17. **`Cc` data type** — every literal is written as a number, matching the
    right-aligned codes in your source. If `Cc` is text, nothing matches and
    every row falls to gate 5; quote all the literals and check for leading
    zeros (`"001"` vs `"1"`).
18. **`Segment` data type and boundary** — `< 116` assumes a numeric column;
    as text it compares alphabetically and misfires silently. Also confirm
    whether 116 itself should be COGS (`<=` rather than `<`).
19. **`Account Desc` ↔ `CTDesc` matching** — exact string equality. Trim both
    in Power Query first; one trailing space drops a row out of OPEX.
20. **Column spelling** — written as `TBData[LineItem]` and
    `CCMap[CostCenter]` (no spaces), per your latest spec. DAX errors on a
    wrong column name rather than failing quietly, so paste will tell you.
21. **`Account Desc` does double duty** — Level 1 tests it against
    `OPEXMap[CTDesc]` to decide OPEX; Level 3 tests it against
    `COGSMap[CTDesc]` to fetch the COGS parent. If one `Account Desc` appears
    in **both** map tables, the row is OPEX at Level 1 but carries a COGS
    parent at Level 3 — a visible contradiction in the matrix. Check the
    overlap is empty.
22. **Key data types** — `InternalRevMap` ↔ `RevIndex` and `Cc` ↔ `CCCode`
    must be the same type on both sides. A number matched against text never
    matches and fails silently; the row just falls to the next gate.

## Note on this repo

The `.pbix` in this repo is the Superstore retail model — it contains none of
`TBData`, `CCMap`, `COGSMap`, or `OPEXMap`. This guide targets a separate
model, so nothing here modifies the existing report.
