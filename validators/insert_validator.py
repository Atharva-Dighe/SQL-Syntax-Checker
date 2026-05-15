import re
import difflib
from .common import validate_semicolon

def print_result(errors, corrected_query, original_query):
    if errors:
        result = "Errors found in INSERT query:\n"
        for err in errors:
            result += " - " + err + "\n"
        result += "You mean: " + corrected_query
    else:
        result = "Correct, no errors in INSERT query."
    print(result)
    return result

def preprocess_tokens(query):
    query_no_semicolon = query.rstrip(";").strip()
    tokens = query_no_semicolon.split()
    new_tokens = []
    for token in tokens:
        m = re.match(r'^([A-Za-z]+)(\(.*)$', token)
        if m:
            new_tokens.append(m.group(1))
            new_tokens.append(m.group(2))
        else:
            new_tokens.append(token)
    return new_tokens

def parse_values_clause(values_clause, num_columns=None):
    errors = []
    value_groups = re.findall(r'\([^)]*\)', values_clause)
    if not value_groups:
        errors.append("Missing or malformed values after 'VALUES'.")
        return "(<values>)", errors

    corrected_groups = []
    for group in value_groups:
        inner = group[1:-1]
        value_list = [v.strip() for v in inner.split(",") if v.strip() != ""]
        if num_columns is not None and len(value_list) != num_columns:
            errors.append(f"Column count ({num_columns}) does not match value count ({len(value_list)}) in {group}.")
        corrected_values = []
        for val in value_list:
            # Updated regex: accepts strings in single quotes, integer, or float numbers,
            # as well as NULL and NOW() (case-insensitive)
            if not re.match(r"^(?:'.*?'|\d+(?:\.\d+)?|\bNULL\b|\bNOW\(\)\b)$", val, re.IGNORECASE):
                errors.append(f"Invalid value: '{val}' in {group}")
                corrected_values.append("<value>")
            else:
                corrected_values.append(val)
        corrected_group = "(" + ", ".join(corrected_values) + ")"
        corrected_groups.append(corrected_group)
    corrected_values_clause = ", ".join(corrected_groups)
    return corrected_values_clause, errors

def validate_insert_query(query):
    original_query = query.strip()
    errors = []
    
    semicolon_ok, semicolon_err = validate_semicolon(original_query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    tokens = preprocess_tokens(original_query)
    corrected_tokens = tokens[:]  # Copy for building the normalized query

    if not tokens or tokens[0].lower() != "insert":
        errors.append("Missing or invalid keyword 'INSERT' at the beginning.")
        if tokens:
            corrected_tokens[0] = "insert"
        else:
            corrected_tokens = ["insert"]
    
    if len(tokens) < 2:
        errors.append("Missing 'INTO' keyword after 'INSERT'.")
        if len(corrected_tokens) < 2:
            corrected_tokens.append("into")
        else:
            corrected_tokens[1] = "into"
    else:
        if tokens[1].lower() != "into":
            candidate = difflib.get_close_matches(tokens[1].lower(), ["into"], n=1, cutoff=0.7)
            if candidate:
                errors.append(f"Invalid keyword '{tokens[1]}' after 'INSERT'. Did you mean '{candidate[0]}'?")
                corrected_tokens[1] = candidate[0]
            else:
                errors.append("Missing or invalid keyword 'INTO' after 'INSERT'.")
                corrected_tokens[1] = "into"
    
    if len(tokens) < 3:
        errors.append("Missing table name after 'INTO'.")
        if len(corrected_tokens) < 3:
            corrected_tokens.append("<table_name>")
        else:
            corrected_tokens[2] = "<table_name>"
    else:
        if tokens[2].lower() == "values":
            errors.append("Missing table name after 'INTO'.")
            corrected_tokens.insert(2, "<table_name>")
            tokens.insert(2, "<table_name>")
        else:
            table_name = tokens[2]
            if not re.match(r'^[A-Za-z0-9_]+$', table_name):
                errors.append(f"Invalid table name: '{table_name}'")
                corrected_tokens[2] = "<table_name>"
    
    # --- UPDATED COLUMN LIST EXTRACTION ---
    col_list = ""
    idx = 3
    if len(tokens) > idx and tokens[idx].startswith("("):
        col_tokens = []
        # Combine tokens until a token ends with ')'
        while idx < len(tokens):
            col_tokens.append(tokens[idx])
            if tokens[idx].endswith(")"):
                idx += 1
                break
            idx += 1
        col_list = " ".join(col_tokens)
    # ---------------------------------------
    
    values_index = -1
    for i in range(idx, len(tokens)):
        token = tokens[i]
        token_stripped = re.sub(r'[^a-zA-Z]', '', token)
        if token_stripped.lower() == "values":
            values_index = i
            break
        else:
            candidate = difflib.get_close_matches(token_stripped.lower(), ["values"], n=1, cutoff=0.7)
            if candidate:
                values_index = i
                m = re.match(r'^([A-Za-z]+)(.*)$', token)
                if m:
                    trailing = m.group(2)
                    corrected_tokens[i] = candidate[0] + trailing
                else:
                    corrected_tokens[i] = candidate[0]
                errors.append(f"Invalid keyword '{token}' detected. Did you mean '{candidate[0]}'?")
                break
    if values_index == -1:
        errors.append("Missing 'VALUES' keyword.")
        corrected_query = " ".join(corrected_tokens) + ";"
        return print_result(errors, corrected_query, original_query)
    
    if values_index + 1 >= len(tokens):
        errors.append("Missing values clause after 'VALUES'.")
        corrected_tokens.append("(<values>)")
        corrected_query = " ".join(corrected_tokens) + ";"
        return print_result(errors, corrected_query, original_query)
    
    values_clause = " ".join(tokens[values_index+1:]).strip()
    value_groups = re.findall(r'\([^)]*\)', values_clause)
    num_value_groups = len(value_groups)
    
    if col_list == "" and num_value_groups > 1:
        errors.append("Missing column list in INSERT query.")
        col_list = "(<columns>)"
    
    num_columns = None
    if col_list and col_list != "(<columns>)":
        col_content = col_list.strip()
        if col_content.startswith("(") and col_content.endswith(")"):
            cols_inside = col_content[1:-1]
            columns_list = [c.strip() for c in cols_inside.split(",") if c.strip() != ""]
            num_columns = len(columns_list)
    
    corrected_values_clause, value_errors = parse_values_clause(values_clause, num_columns)
    errors.extend(value_errors)
    
    final_tokens = corrected_tokens[:3]
    if col_list:
        final_tokens.append(col_list)
    final_tokens.append("values")
    final_tokens.append(corrected_values_clause)
    corrected_query = " ".join(final_tokens) + ";"
    return print_result(errors, corrected_query, original_query)

def process_query(query):
    query = query.strip()
    if not query:
        return "Empty query."
    tokens = query.split()
    if not tokens:
        return "Empty query."
    first_word = tokens[0].lower()
    if first_word != "insert":
        candidate = difflib.get_close_matches(first_word, ["insert"], n=1, cutoff=0.7)
        if candidate:
            tokens[0] = candidate[0]
            corrected_query = " ".join(tokens)
            return process_query(corrected_query)
        else:
            return "Unsupported query type."
    return validate_insert_query(query)
