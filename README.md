# Advance Database TP2 Neo4j import optimisation

## How to run

## What to expect (Benchmarks)

In its current form the bottleneck is the jq parser that read the JSON stream and convert it into lines of JSON. Capped at 100% single CPU usage, The limit is around 1300 lines/[s] for a total of ...
Thus, there is no need to optimize this part unless our python script can run faster than that.

Baseline:
	Number of entries processed: 5354309, total time: 1:07:51.236645
	Average: 0.00076[s] per line


## References

- [Streaming with jq](https://www.reddit.com/r/bash/comments/myoft4/streaming_with_jq/)
- [Neo4j performance](https://neo4j.com/docs/python-manual/current/performance/ )
