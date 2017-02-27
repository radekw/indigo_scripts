This script gets a list of variables and devices from indigo, reads the values
from the sqlite database and outputs every change in json format. It keeps its
internal state in sqlite database to be able to continue from where it left
off.

The script is scheduled to run every 5 minutes and the output is parsed
by Logstash and inserted into Elasticsearch. I use Grafana to create graphs.

