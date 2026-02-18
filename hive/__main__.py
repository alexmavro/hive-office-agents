"""
Entry point for running hive as a module: python -m hive
"""

from hive.cli.commands import app

if __name__ == "__main__":
    app()
