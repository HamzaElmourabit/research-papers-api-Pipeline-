docker run -d --name cassandra ^  -p 9042:9042 ^  -v "C:full path\research papers api\casandra:/scripts" ^  cassandra:5.0


docker exec -it cassandra bash

cqlsh

SOURCE '/scripts/schema.cql';