import re
import difflib
from validators.common import validate_semicolon

def validate_database_name(database_name):
    """
    Validates the database name. It should start with a letter or underscore and
    contain only letters, digits, or underscores.
    """
    errors = []
    corrected = database_name
    if not re.match(r'^[A-Za-z_]', database_name):
        errors.append(f"Invalid database name: '{database_name}'. Must not start with a digit.")
        corrected = "<database_name>"
    elif not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', database_name):
        errors.append(f"Invalid database name: '{database_name}'.")
        corrected = "<database_name>"
    return corrected, errors

def validate_create_database_query(query):
    """
    Validates a CREATE DATABASE query.
    Expected formats:
       create database <database_name>;
       create database if not exists <database_name>;
       
    This version captures up to three tokens after "create database" and validates them
    against the expected clause "if not exists".
    """
    all_errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        all_errors.append(semicolon_err)

    # Remove trailing semicolon and extra spaces.
    q = query.strip().rstrip(";").strip()
    # Updated regex: capture an optional clause of up to three tokens after "create database"
    pattern = re.compile(
        r'^create\s+database(?P<if_clause>(?:\s+\S+){0,3})\s+(?P<database_name>[A-Za-z_][A-Za-z0-9_]*)$',
        re.IGNORECASE
    )
    match = pattern.match(q)
    if not match:
        all_errors.append("Query does not match expected CREATE DATABASE syntax.")
        print("Errors found in CREATE DATABASE query:")
        for err in all_errors:
            print(" -", err)
        return

    if_clause = match.group("if_clause").strip()
    database_name = match.group("database_name")
    
    # Validate the database name.
    corrected_database_name, name_errors = validate_database_name(database_name)
    all_errors.extend(name_errors)
    
    expected_clause = "if not exists"
    corrected_if_clause = ""
    if if_clause:
        # Normalize the clause by removing extra spaces and lowercasing.
        if_clause_norm = " ".join(if_clause.lower().split())
        if if_clause_norm != expected_clause:
            candidate = difflib.get_close_matches(if_clause_norm, [expected_clause], n=1, cutoff=0.6)
            if candidate:
                all_errors.append(f"Invalid clause: did you mean '{expected_clause}' instead of '{if_clause_norm}'?")
                corrected_if_clause = expected_clause
            else:
                all_errors.append("Query does not match expected CREATE DATABASE syntax.")
                corrected_if_clause = if_clause_norm
        else:
            corrected_if_clause = expected_clause

    # Build suggestion.
    suggestion = "create database"
    if corrected_if_clause:
        suggestion += " " + corrected_if_clause
    suggestion += " " + corrected_database_name + ";"

    if all_errors:
        print("Errors found in CREATE DATABASE query:")
        for err in all_errors:
            print(" -", err)
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in CREATE DATABASE query.")
