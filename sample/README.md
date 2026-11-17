# sample: a small graph for trying things

`sample.whole.*` is a slice of the final graph: 10 well-known cancer proteins and their neighbours (764 nodes, 12,222 edges, every edge with a verdict). `sample.pruned.*` has only the kept edges. `example_measurements.csv` is a table of your-own-data rows for `python -m bioagent --graph sample/sample.whole ingest-csv sample/example_measurements.csv`. The full graphs are on [Hugging Face](https://huggingface.co/datasets/hamzahanif/bioagent-kg-pharos).
