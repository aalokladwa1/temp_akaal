import os
import unittest
import sys

# Inject correct database credentials directly into environment before importing fixtures
os.environ["MYSQL_PASSWORD"] = ""
os.environ["POSTGRES_PORT"] = "5433"
os.environ["MYSQL_DATABASE"] = "akaal_validation"
os.environ["POSTGRES_DATABASE"] = "akaal_validation_target"

# Add current workspace to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Run unit tests
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover("tests/validation", pattern="test_mysql_to_postgres.py")
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
