from pymongo import MongoClient
from threading import Lock
from llm4quality_api.config.config import Config


class MongoDBClient:
    """
    A Singleton class to manage MongoDB connections and collections.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """
        Create or return the singleton instance.
        """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:  # Double-checked locking
                    cls._instance = super(MongoDBClient, cls).__new__(cls)
                    cls._instance._initialize(*args, **kwargs)
        return cls._instance

    def _initialize(
        self, uri: str = Config.MONGO_URI, database_name: str = Config.MONGO_DB_NAME
    ):
        """
        Initialize the MongoDB client and specify the database.

        Args:
            uri (str): MongoDB connection string.
            database_name (str): Name of the database to connect to.
        """
        self.client = MongoClient(uri)
        self.database = self.client[database_name]

    def get_collection(self, collection_name: str):
        """
        Get a collection from the database.

        Args:
            collection_name (str): Name of the collection.

        Returns:
            Collection: The MongoDB collection.
        """
        return self.database[collection_name]

    def close_connection(self):
        """
        Close the MongoDB connection.
        """
        if self.client:
            self.client.close()
    

