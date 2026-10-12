# OP Mainnet revenue: BI Lead case study

Leadership asked: *Who is making money on OP Mainnet, how much is our share, and how can we grow our take over the next 12 months?*

| Folder | Contents |
|---|---|
| [`analysis/`](analysis/) | The work: SQL, Python pipeline, growth model, charts, and the deck (`analysis/deck/OP_Mainnet_Revenue_BI_Lead.pptx`). Start with [`analysis/README.md`](analysis/README.md). |
| `Business Intelligence Lead Take-Home/` | The brief (PDF) and the provided data (`case_study_data/`: CSVs, JSON, source SQL, scripts), unmodified. |

**Answer in brief:** net sequencer revenue was **$1.22M** over the last 12 months (97% margin after L1 costs) and is falling.
Volume grew, but the price of blockspace fell 76%. Apps earned **$41.3M** in fees, and bots pay about two-thirds of OP's fees.
The recommended plan (a staged minimum base fee, payments BD, an L1 data-fee fix, OP Enterprise) gives **$1.19M** next year
vs **$0.90M** with no action (Bear $0.40M, Bull $3.09M).

Reproduce everything: `cd analysis && ./run_all.sh`
