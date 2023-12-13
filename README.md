# Advance Database TP2 Neo4j import optimisation

## How to run
on a machine with docker-compose:

	docker-compose build
	docker-compose up

	# when you are done:
	docker-compose down

## What to expect (Benchmarks)

In its current form the bottleneck is the jq parser that read the JSON stream and convert it into lines of JSON. Capped at 100% single CPU usage, The limit is around 1300 lines/[s] for a total of 5'354'309.
Thus, there is no need to optimize this part unless our python script can run faster than that.

## Benchmarck

Baseline (the time it takes for the pipe `7z` | `jq` | `py` to stream the whole dump without processing the data):

	Number of entries processed: 5354309, total time: 1:07:51.236645
	Average: 0.00076[s] per line

Benchmarking on the completed application:

	current:  TX limit:  200, RAM limit: 2G, 20k lines in  0min 22s  # select explicitly 'neo4j' database
	previous: TX limit:  200, RAM limit: 2G, 20k lines in  0min 28s # unique constrain on ids
	previous: TX limit:  200, RAM limit: 2G, 20k lines in 17min 30s

	Number of entries processed: 5354309, total time: 17:31:38.410965 # TX limit: 1500, RAM limit: 2G
	Average: 0.01178[s] per line

	Number of entries processed: 5354309, total time: 4:01:41.073429  # TX limit: 2000, RAM limit: 4G
	Average: 0.00271[s] per line

	Number of entries processed: 5354309, total time: 4:23:38.101628  # TX limit: 1500, RAM limit: 4G
	Average: 0.00295[s] per line

	Number of entries processed: 5354309, total time: 5:36:04.685036 # TX limit: 10000, RAM limit: 4G
	Average: 0.00377[s] per line

## References

- [Streaming with jq](https://www.reddit.com/r/bash/comments/myoft4/streaming_with_jq/)
- [Neo4j performance](https://neo4j.com/docs/python-manual/current/performance/ )
- [Neo4j python driver](https://neo4j.com/docs/api/python-driver/current/)


A retourner:
 - le nom du pod dans lequel se trouve l'instance neo4j
 - credentials neo4j
 - namespace
 - doit pouvoir voir les logs via rancher
 - le container doit tourner (while True sleep...)