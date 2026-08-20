# P&L Matrix — Build Guide

Builds the hand-drawn P&L structure as a Power BI matrix, where each of the
three visible columns pulls its labels from a **different source table**
depending on which section (Revenue / COGS / OPEX) the row belongs to.

All DAX is in [`PL_Hierarchy.dax`](./PL_Hierarchy.dax).

## The mapping

| Matrix column | Revenue | COGS | OPEX |
|---|---|---|---|
| **Level 1** (Revenue / COGS / OPEX) | `BellcorpMap[LineItem]` * | `BellcorpMap[LineItem]` * | `TBData[Primary Group]` in the department list ** |
| **Level 2** (blue) | `TBData[Revenue Row Label]` | `TBData[Cc]` | `"Bonus"` if `TBData[Matrix]` = 286, else `CCMap[Primary Group Label]` |
| **Level 3** (red) | `TBData[PL Label]` | `COGSMap[CTDesc Parent]` | `CCMap[Cost Center]` |
| **Level 4** (green) | *not specified — see open questions* | *(sketch stops at L3)* | *not specified* |

\* `BellcorpMap` is not joined directly to `TBData` — it is reached through a
bridge table: `TBData` → `BellPLMap` → `BellcorpMap`, the second hop joining
on `Row`.

\*\* OPEX is decided **first**, before the `BellcorpMap` lookup runs. A row is
OPEX when `TBData[Primary Group]` is one of these 11 operating departments:

`BI/Product` · `Commercial Sales` · `Construction` · `Consumer Sales` ·
`Corporate Marketing` · `Direct Field Operations` · `Direct Legal & Regulatory` ·
`G&A` · `Headquarters Expenses` · `Logistics` · `Technology`

Everything else falls through to `BellcorpMap[LineItem]`, which is what
classifies Revenue and COGS.

## Why calculated columns and not three separate visuals

The three sections have to stack in **one** matrix, so all three need to
resolve to the *same* three physical columns. Materialising `PL Level 1..3`
on `TBData` — the table that holds the amounts — does exactly that: a single
`SWITCH` per level picks the right source, and the matrix then sees one plain
hierarchy. Any approach that keeps the labels in their home tables ends up
needing three visuals stitched together, which breaks subtotals and sorting.

## Build steps

1. **Create the relationships**:
   - `TBData` → `BellPLMap` (many-to-one, single direction)
   - `BellPLMap` → `BellcorpMap` on `Row` (many-to-one, single direction)
   - `TBData[Cc]` → `CCMap[Cost Center]` (many-to-one, single direction)
   - `TBData[Cc]` → `COGSMap[Cc]` (many-to-one, single direction)

   The `BellcorpMap` chain matters most. `RELATED()` walks any number of
   many-to-one hops, so with both arrows pointing **away from** `TBData`,
   Level 1 is a single `RELATED ( BellcorpMap[LineItem] )`. If instead
   `BellPLMap` is the *one* side of both relationships, the path is
   many→one then one→many and `RELATED()` cannot cross it — use the nested
   `LOOKUPVALUE` fallback in the `.dax` file.

   Power BI allows only one active relationship per table pair, and `TBData`
   hits `CCMap` and `COGSMap` on the same `Cc` column — that's fine, they're
   different table pairs.

2. **Add the calculated columns** to `TBData`, in this order (each one
   references the previous): `PL Level 1`, `PL Level 2`, `PL Level 3`,
   then the two `... Sort` columns. Replace every `*** KEY ***` placeholder
   with your real join columns first.

3. **Set the sort order**: select `PL Level 1` → Column tools → *Sort by
   column* → `PL Level 1 Sort`. Repeat for `PL Level 2` → `PL Level 2 Sort`.

4. **Add the measures** (`Amount`, `Total Revenue`, `Total COGS`,
   `Gross Profit`, `Total OPEX`, `Operating Income`, `Gross Margin %`).

5. **Build the matrix**:
   - *Rows*: `PL Level 1`, `PL Level 2`, `PL Level 3` (in that order)
   - *Columns*: your period column (`Date[Month]` or similar) — this is the
     `X` grid in the sketch
   - *Values*: `[Amount]`
   - Format pane → *Row subtotals* **On**, and set *Stepped layout* **Off**
     so each level gets its own indented column like the drawing.

6. **Gross Profit / Total Revenue rows**: a plain matrix can't place these
   between sections (Gross Profit spans two sections, so it isn't a rollup of
   any one of them). Two options, both at the bottom of the `.dax` file:
   - **Simple** — keep the hierarchy matrix and put Gross Profit / Operating
     Income in cards or a small summary matrix underneath. This is what most
     production P&L reports do.
   - **Exact layout** — drive the rows from the disconnected `PL Layout`
     table and swap `[Amount]` for the `[PL Value]` measure. More faithful to
     the sketch, more moving parts; the `TREATAS` caveat is documented inline.

## Validation

After step 2, drop `PL Level 1` into a table visual with `[Amount]`. You should
see exactly `Revenue`, `COGS`, `OPEX` and nothing else. Any rows landing under
**"Unmapped"** are trial-balance accounts that are neither an OPEX department
nor resolvable through `BellcorpMap` — chase those before trusting the totals.

Then cross-check the OPEX test on its own: put `TBData[Primary Group]` and
`PL Level 1` in a table together. Every one of the 11 departments must show
`OPEX`; if one shows `Unmapped`, the string in the DAX does not match the
string in the data (almost always a trailing space, or the `&` / `/` in
`G&A`, `Direct Legal & Regulatory`, `BI/Product`). Finally check that
`[Total Revenue] - [Total COGS] - [Total OPEX]` reconciles to your existing
operating income figure.

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
3. **`TBData` → `BellPLMap` join key** — the bridge hop. I assumed an account
   code on both sides; confirm the actual column.
4. **`CCMap[Cost Center]`** — is this the key itself, or a descriptive label?
   If it's identical to `TBData[Cc]` the lookup is redundant and you should
   use `TBData[Cc]` directly.
5. **Sign convention** — the DAX assumes costs are stored positive. If your
   TB carries them as negatives, flip the subtractions in `Gross Profit` and
   `Operating Income`.
6. **`078` / `106`** — I read these as cost-center codes appearing as COGS
   Level 2, which matches `TBData[Cc]` feeding that slot. Confirm.
7. **`TBData[Primary Group]` vs `CCMap[Primary Group Label]`** — these look
   like the same concept in two places. If `TBData[Primary Group]` already
   carries the department name, the OPEX branch of `PL Level 2` can use it
   directly and the `CCMap` lookup becomes unnecessary. Worth checking: it
   removes a lookup and a relationship dependency. Left as you specified
   (`CCMap`) until confirmed.
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

## Note on this repo

The `.pbix` in this repo is the Superstore retail model — it contains none of
`TBData`, `BellPLMap`, `BellcorpMap`, `CCMap`, or `COGSMap`. This guide targets a separate
model, so nothing here modifies the existing report.
