# Election CSV format (open data)

Place official or research extracts here.

## Required columns

| column | description |
|--------|-------------|
| election_id | e.g. `GD-2021` or `PRES-2018` |
| region_code | 2-digit subject code (77=Moscow) |
| turnout_pct | turnout percent |

## Optional

`region_name`, `valid_ballots`, `registered_voters`, `leader_share_pct`, `source`, `note`

## DEMO file

`demo_presidential_structure.csv` is created from the app for UI testing only — **not official results**.

Sources to obtain real data: CIK open publications, academic datasets (e.g. research archives), Golos historical dumps where legally available.
