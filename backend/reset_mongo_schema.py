"""Backward-compatible entrypoint — see ``backend.mongo_schema``."""
from backend.mongo_schema import reset_database

if __name__ == "__main__":
    reset_database(drop_all=True)
