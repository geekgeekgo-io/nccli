"""MongoDB connection and operations."""

import os
from typing import List, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure


class MongoDBClient:
    """MongoDB client for managing DNS entries."""

    def __init__(self, connection_uri: str = None):
        """
        Initialize MongoDB client.

        Args:
            connection_uri: MongoDB connection string. If None, reads from
                          NCCLI_MONGODB_URI environment variable.
        """
        self.connection_uri = connection_uri or os.getenv('NCCLI_MONGODB_URI')

        if not self.connection_uri:
            raise ValueError(
                "MongoDB URI not provided. Set NCCLI_MONGODB_URI environment "
                "variable or pass connection_uri parameter."
            )

        self.client = None
        self.db = None
        self.collection = None

    def connect(self, database_name: str = "dns_registry", collection_name: str = "hosts"):
        """
        Connect to MongoDB and select database and collection.

        Args:
            database_name: Name of the database to use
            collection_name: Name of the collection to use

        Raises:
            ConnectionFailure: If unable to connect to MongoDB
        """
        try:
            self.client = MongoClient(self.connection_uri, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")

    def upload_entries(self, entries: List[Dict[str, str]], replace: bool = False) -> int:
        """
        Upload DNS entries to MongoDB.

        Args:
            entries: List of DNS entry dictionaries
            replace: If True, clear existing entries before uploading

        Returns:
            Number of entries inserted

        Raises:
            OperationFailure: If database operation fails
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")

        try:
            if replace:
                # Clear existing entries
                self.collection.delete_many({})

            if not entries:
                return 0

            # Insert entries
            result = self.collection.insert_many(entries)
            return len(result.inserted_ids)

        except OperationFailure as e:
            raise OperationFailure(f"Failed to upload entries: {e}")

    def download_entries(self) -> List[Dict[str, str]]:
        """
        Download DNS entries from MongoDB.

        Returns:
            List of DNS entry dictionaries

        Raises:
            OperationFailure: If database operation fails
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")

        try:
            # Retrieve all entries, excluding the MongoDB _id field
            entries = list(self.collection.find({}, {'_id': 0}))
            return entries
        except OperationFailure as e:
            raise OperationFailure(f"Failed to download entries: {e}")

    def close(self):
        """Close MongoDB connection."""
        if self.client is not None:
            self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
