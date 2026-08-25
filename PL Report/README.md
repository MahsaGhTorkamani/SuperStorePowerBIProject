# P&L Matrix — Build Guide

Builds the hand-drawn P&L structure as a Power BI matrix, where each of the
three visible columns pulls its labels from a **different source table**
depending on which section (Revenue / COGS / OPEX) the row belongs to.

All DAX is in [`PL_Hierarchy.dax`](./PL_Hierarchy.dax).

## The mapping

| Matrix column | Revenue | COGS | OPEX |
|---|---|---|---|
| **Level 1** (Revenue / COGS / OPEX) | `TBData[LineItem]` = `"Revenue"` | `TBData[LineItem]` = `"COGS"` **and** `TBData[Segment]` < 116 | `TBData[Account Desc]` found in `OPEXMap[CTDesc]` |
| **Level 2** (blue) | `TBData[Revenue Row Label]` | `TBData[Cc]` | `"Bonus"` if `TBData[Matrix]` = 286, else `TBData[Primary Group]` |
| **Level 3** (red) | `TBData[PL Label]` | `COGSMap[CTDesc Parent]` | `CCMap[Cost Center]` |
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

The `Primary Group` department list no longer classifies Level 1. It is still
used to *label* OPEX rows at Level 2 — see open question 14.

## Why calculated columns and not three separate visuals

The three sections have to stack in **one** matrix, so all three need to
resolve to the *same* three physical columns. Materialising `PL Level 1..3`
on `TBData` — the table that holds the amounts — does exactly that: a single
`SWITCH` per level picks the right source, and the matrix then sees one plain
hierarchy. Any approach that keeps the labels in their home tables ends up
needing three visuals stitched together, which breaks subtotals and sorting.

## Build steps

1. **Create the relationships** — only Level 3 needs any:
   - `TBData[Cc]` → `CCMap[Cost Center]` (many-to-one, single direction)
   - `TBData[Cc]` → `COGSMap[Cc]` (many-to-one, single direction)

   Power BI allows only one active relationship per table pair, and `TBData`
   hits `CCMap` and `COGSMap` on the same `Cc` column — that's fine, they're
   different table pairs. `OPEXMap` needs no relationship (the membership
   test uses `ALL()`), and neither do `BellPLMap` / `BellcorpMap`, which this
   report no longer reads at all.

   The DAX ships with `LOOKUPVALUE` so Level 3 runs even with zero
   relationships; swap to `RELATED()` once they exist.

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
2. **`COGSMap` join key** — I assumed it joins on cost center (`Cc`). If it
   joins on account or on `CTDesc`, change the `LOOKUPVALUE` arguments in
   `PL Level 3`.
3. ~~`TBData` → `BellPLMap` join key~~ — **resolved**: `LineItem` is read
   straight off `TBData`, so the bridge is no longer used by this report.
4. **`CCMap[Cost Center]`** — is this the key itself, or a descriptive label?
   If it's identical to `TBData[Cc]` the lookup is redundant and you should
   use `TBData[Cc]` directly.
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
14. **Level 1 and Level 2 now use different OPEX definitions** — Level 1
    decides OPEX from `OPEXMap[CTDesc]`; Level 2 still labels those rows with
    `TBData[Primary Group]`. A row can be OPEX under the new rule while
    carrying a Primary Group outside the 12 departments, and that stray value
    becomes a Level 2 row header. Diagnostic and a catch-all fix are in the
    `.dax` file.
15. **`Segment` data type and boundary** — `< 116` assumes a numeric column;
    as text it compares alphabetically and misfires silently. Also confirm
    whether 116 itself should be COGS (`<=` rather than `<`).
16. **`Account Desc` ↔ `CTDesc` matching** — exact string equality. Trim both
    in Power Query first; one trailing space drops a row out of OPEX.
17. **Column spelling** — written as `TBData[LineItem]`. If it is actually
    `Line Item` with a space, adjust. DAX errors on this rather than failing
    quietly, so you will know immediately.

## Note on this repo

The `.pbix` in this repo is the Superstore retail model — it contains none of
`TBData`, `CCMap`, `COGSMap`, or `OPEXMap`. This guide targets a separate
model, so nothing here modifies the existing report.
