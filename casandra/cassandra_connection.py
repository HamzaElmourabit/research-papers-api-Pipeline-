
from cassandra.cluster import Cluster

class CassandraConnection:
    def __init__(self, contact_points=['localhost'], port=9042,keyspace='arxiv'):
        self.contact_points = contact_points
        self.port = port
        self.keyspace = keyspace
        self.cluster = None
        self.session = None

    def connect(self):
        try:
            self.cluster = Cluster(contact_points=self.contact_points, port=self.port)
            self.session = self.cluster.connect()
            self.session.set_keyspace(self.keyspace)
            print("Connected to Cassandra cluster")
        except Exception as e:
            print(f"Error connecting to Cassandra: {e}")

    def disconnect(self):
        if self.cluster:
            self.cluster.shutdown()
            print("Disconnected from Cassandra cluster")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
