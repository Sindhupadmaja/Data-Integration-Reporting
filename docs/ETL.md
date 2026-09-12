# ETL design
**Extract:** CSV upload is the source adapter.

**Transform:** normalize alternate column names, trim text, cast numeric values, reject invalid rows.

**Load:** persist canonical `Record` rows.

Next improvements: PostgreSQL, schema versioning, data-quality rules, source connectors, incremental loads, lineage, and report delivery.
