import re
import difflib
from validators.common import ALLOWED_TYPES, ALLOWED_CONSTRAINTS, validate_semicolon

def parse_create_query(query):
    """
    Parses a CREATE TABLE query into its parts: table keyword, optional if-not-exists clause,
    table name, and columns string.
    """
    q = query.strip().rstrip(";").strip()
    pattern = re.compile(
        r'^create\s+(?P<table_kw>\S+)(?P<if_clause>(?:\s+\S+){0,3})\s+(?P<table_name>[A-Za-z0-9_]+)\s*(?P<columns>\(.*\))?$',
        re.IGNORECASE
    )
    match = pattern.match(q)
    if not match:
        return None, ["Query does not match expected CREATE TABLE syntax."], None
    table_kw = match.group("table_kw")
    if_clause = match.group("if_clause").strip()
    if if_clause == "":
        if_clause = None
    table_name = match.group("table_name")
    columns = match.group("columns")  # may be None if not provided
    return (table_kw, if_clause, table_name, columns), [], q

def validate_table_keyword(table_kw):
    """
    Validates the table keyword. Should be 'TABLE' (case-insensitive).
    """
    errors = []
    corrected = table_kw
    if table_kw.lower() != "table":
        candidate = difflib.get_close_matches(table_kw.lower(), ["table"], n=1, cutoff=0.6)
        if candidate:
            errors.append(f"Did you mean 'TABLE' instead of '{table_kw}'?")
            corrected = "TABLE"
        else:
            errors.append("Missing or incorrect keyword 'TABLE'.")
            corrected = "TABLE"
    return corrected, errors

def validate_if_clause(if_clause):
    """
    Validates the optional 'if not exists' clause.
    Expected tokens: "if", "not", "exists" (case-insensitive).
    """
    errors = []
    expected_tokens = ["if", "not", "exists"]
    tokens = if_clause.split()
    if len(tokens) != 3:
        errors.append("Invalid 'if not exists' clause. Expected three tokens: 'if not exists'.")
        return "if not exists", errors
    corrected_tokens = []
    for i, token in enumerate(tokens):
        if token.lower() != expected_tokens[i]:
            candidate = difflib.get_close_matches(token.lower(), [expected_tokens[i]], n=1, cutoff=0.6)
            if candidate:
                errors.append(f"Did you mean '{candidate[0]}' instead of '{token}'?")
                corrected_tokens.append(candidate[0])
            else:
                errors.append(f"Invalid token '{token}' in if clause; expected '{expected_tokens[i]}'.")
                corrected_tokens.append(expected_tokens[i])
        else:
            corrected_tokens.append(token.lower())
    return " ".join(corrected_tokens), errors

def validate_table_name(table_name):
    """
    Validates the table name.
    """
    errors = []
    corrected = table_name
    if not re.match(r'^[A-Za-z_]', table_name):
        errors.append(f"Invalid table name: '{table_name}'. Must not start with a digit.")
        corrected = "<table_name>"
    elif not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name):
        errors.append(f"Invalid table name: '{table_name}'.")
        corrected = "<table_name>"
    return corrected, errors

def validate_column_definition(col_def):
    """
    Validates a single column definition.
    Expected format: column_name data_type [constraints ...]
    
    Handles parameterized types (e.g., varchar(50)) and suggests a default size if missing.
    Also validates multi-word constraints such as "not null".
    """
    errors = []
    tokens = col_def.split()
    if len(tokens) < 2:
        errors.append(f"Incomplete column definition: '{col_def}'")
        return "<col_def>", errors

    col_name = tokens[0]
    col_type = tokens[1]
    rest = tokens[2:]  # constraint tokens

    corrected_col_name = col_name
    if not re.match(r'^[A-Za-z_]', col_name):
        errors.append(f"Invalid column name: '{col_name}'")
        corrected_col_name = "<col_name>"

    # Handle parameterized types like varchar(50)
    param_str = ""
    base_type = col_type.lower()
    if "(" in col_type and col_type.endswith(")"):
        index = col_type.index("(")
        base_type = col_type[:index].lower()
        param_str = col_type[index:]
    
    # If the base type is 'varchar' but no size is provided, add a default size.
    if base_type == "varchar" and param_str == "":
        errors.append("Missing size parameter for 'varchar'.")
        param_str = "(50)"
    
    if base_type not in ALLOWED_TYPES:
        candidate = difflib.get_close_matches(base_type, ALLOWED_TYPES, n=1, cutoff=0.6)
        if candidate:
            errors.append(f"Unsupported column type: '{col_type}'")
            if candidate[0] == "varchar" and param_str == "":
                param_str = "(50)"
            corrected_col_type = candidate[0] + param_str
        else:
            errors.append(f"Unsupported column type: '{col_type}'")
            corrected_col_type = "<col_type>"
    else:
        corrected_col_type = base_type + param_str

    # Process constraint tokens with special handling for multi-word constraints.
    corrected_rest = []
    i = 0
    while i < len(rest):
        token = rest[i].lower()
        # Check for "not null"
        if token == "not":
            if i + 1 < len(rest) and rest[i+1].lower() == "null":
                corrected_rest.extend(["not", "null"])
                i += 2
            else:
                errors.append("Incomplete constraint: 'not' must be followed by 'null'.")
                corrected_rest.extend(["not", "null"])
                i += 1
        else:
            if token not in ALLOWED_CONSTRAINTS:
                candidate = difflib.get_close_matches(token, ALLOWED_CONSTRAINTS, n=1, cutoff=0.6)
                if candidate:
                    errors.append(f"Did you mean '{candidate[0]}' instead of '{rest[i]}'?")
                    corrected_rest.append(candidate[0])
                else:
                    errors.append(f"Unknown constraint token: '{rest[i]}'")
                    corrected_rest.append(rest[i])
            else:
                corrected_rest.append(token)
            i += 1

    corrected_def = " ".join([corrected_col_name, corrected_col_type] + corrected_rest)
    return corrected_def, errors

def validate_table_constraint(constraint_def):
    """
    Validates a table-level constraint (PRIMARY KEY, FOREIGN KEY).
    """
    errors = []
    constraint_def = constraint_def.strip()
    # Check PRIMARY KEY
    primary_key_pattern = re.compile(r'^primary\s+key\s*\((.+)\)\s*$', re.IGNORECASE)
    primary_match = primary_key_pattern.match(constraint_def)
    if primary_match:
        columns = primary_match.group(1).strip()
        if not columns:
            errors.append("PRIMARY KEY constraint must specify columns.")
            return "PRIMARY KEY (column)", errors
        corrected_columns = []
        for col in re.split(r'\s*,\s*', columns):
            col = col.strip()
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', col):
                errors.append(f"Invalid column name '{col}' in PRIMARY KEY.")
                corrected_columns.append("<column>")
            else:
                corrected_columns.append(col)
        corrected = "PRIMARY KEY ({})".format(", ".join(corrected_columns))
        return corrected, errors
    
    # Check FOREIGN KEY
    foreign_key_pattern = re.compile(
        r'^foreign\s+key\s*\((.+?)\)\s+references\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.+?)\)\s*$', 
        re.IGNORECASE
    )
    foreign_match = foreign_key_pattern.match(constraint_def)
    if foreign_match:
        fk_columns = foreign_match.group(1).strip()
        ref_table = foreign_match.group(2).strip()
        ref_columns = foreign_match.group(3).strip()
        
        # Validate foreign key columns
        fk_cols = []
        for col in re.split(r'\s*,\s*', fk_columns):
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', col):
                errors.append(f"Invalid foreign key column '{col}'.")
                fk_cols.append("<column>")
            else:
                fk_cols.append(col)
        
        # Validate referenced table
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', ref_table):
            errors.append(f"Invalid referenced table name '{ref_table}'.")
            ref_table = "<table>"
        
        # Validate referenced columns
        ref_cols = []
        for col in re.split(r'\s*,\s*', ref_columns):
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', col):
                errors.append(f"Invalid referenced column '{col}'.")
                ref_cols.append("<column>")
            else:
                ref_cols.append(col)
        
        corrected = "FOREIGN KEY ({}) REFERENCES {}({})".format(
            ", ".join(fk_cols), ref_table, ", ".join(ref_cols)
        )
        return corrected, errors
    
    errors.append(f"Unknown constraint: '{constraint_def}'")
    return "<constraint>", errors

def validate_columns(columns_str):
    """
    Validates the column definitions and table constraints (should be enclosed in parentheses).
    """
    errors = []
    if not columns_str:
        errors.append("Missing column definitions. Expected definitions in parentheses.")
        return "", errors
    columns_str = columns_str.strip()
    if not (columns_str.startswith("(") and columns_str.endswith(")")):
        errors.append("Incorrect column definition format. Expected (column1 type, column2 type, ...).")
        return columns_str, errors

    inner = columns_str[1:-1].strip()
    if not inner:
        errors.append("Empty column definitions.")
        return columns_str, errors

    col_defs = [col.strip() for col in inner.split(",")]
    corrected_col_defs = []
    for col in col_defs:
        if re.match(r'^\s*(PRIMARY\s+KEY|FOREIGN\s+KEY)\s*', col, re.IGNORECASE):
            corr_def, errs = validate_table_constraint(col)
        else:
            corr_def, errs = validate_column_definition(col)
        errors.extend(errs)
        corrected_col_defs.append(corr_def)
    corrected = "(" + ", ".join(corrected_col_defs) + ")"
    return corrected, errors

def validate_create_query(query):
    """
    Main function for validating a CREATE TABLE query.
    """
    all_errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        all_errors.append(semicolon_err)

    parts, parse_errors, raw_query = parse_create_query(query)
    if parse_errors:
        all_errors.extend(parse_errors)
        print("Errors found in CREATE TABLE query:")
        for err in all_errors:
            print(" -", err)
        return

    table_kw, if_clause, table_name, columns = parts

    corrected_table_kw, err = validate_table_keyword(table_kw)
    all_errors.extend(err)
    
    corrected_if_clause = None
    if if_clause is not None:
        corrected_if_clause, err = validate_if_clause(if_clause)
        all_errors.extend(err)
    
    corrected_table_name, err = validate_table_name(table_name)
    all_errors.extend(err)
    
    corrected_columns = ""
    if columns is None:
        all_errors.append("Missing column definitions. Expected column definitions in parentheses.")
    else:
        corrected_columns, col_errors = validate_columns(columns)
        all_errors.extend(col_errors)

    suggestion = "CREATE " + corrected_table_kw
    if corrected_if_clause:
        suggestion += " " + corrected_if_clause
    suggestion += " " + corrected_table_name
    if corrected_columns:
        suggestion += " " + corrected_columns
    suggestion += ";"

    if all_errors:
        print("Errors found in CREATE TABLE query:")
        for err in all_errors:
            print(" -", err)
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in CREATE TABLE query.")