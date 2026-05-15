import re
import difflib

# Allowed SQL data types and constraint keywords.
ALLOWED_TYPES = ["int", "varchar", "text", "boolean", "date", "decimal", "float", "double"]
ALLOWED_CONSTRAINTS = ["primary", "key", "not", "null", "unique", "default", "check", "foreign", "references","auto_increment"]

def validate_semicolon(query):
    """
    Checks that the query ends with a semicolon.
    """
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""
