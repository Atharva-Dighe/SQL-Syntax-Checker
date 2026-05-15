import re
import difflib

def print_update_errors(errors, corrected_tokens):
    if errors:
        print("Errors found in UPDATE query:")
        for err in errors:
            print(" -", err)
        print("You mean:", " ".join(corrected_tokens) + ";")
    else:
        print("Correct, no errors in UPDATE query.")

def validate_semicolon(query):
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""

def validate_update_query(query):
    errors = []
    
    # Check semicolon.
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    # Remove the trailing semicolon for tokenization.
    query_stripped = query.strip().rstrip(";").strip()
    tokens = query_stripped.split()
    corrected_tokens = tokens[:]  # For building the suggestion
    
    # --- Validate 'UPDATE' keyword ---
    if not tokens or tokens[0].lower() != "update":
        errors.append("Missing or invalid keyword 'UPDATE' at the beginning.")
        corrected_tokens.insert(0, "update")
    else:
        # Correct UPDATE keyword if near-match
        candidate = difflib.get_close_matches(tokens[0].lower(), ["update"], n=1, cutoff=0.8)
        if candidate and tokens[0].lower() != candidate[0]:
            corrected_tokens[0] = candidate[0]
            errors.append(f"you mean update instead of {tokens[0]}")
    
    # --- Validate table name ---
    if len(tokens) < 2 or tokens[1].lower() == "set":
        errors.append("Missing table name after 'UPDATE'.")
        if len(corrected_tokens) < 2:
            corrected_tokens.insert(1, "<table_name>")
        else:
            corrected_tokens.insert(1, "<table_name>")
    else:
        table_name = tokens[1]
        if not re.match(r'^[A-Za-z0-9_]+$', table_name):
            errors.append(f"Invalid table name: '{table_name}'")
            corrected_tokens[1] = "<table_name>"
    
    # --- Find 'SET' clause (allow near-match) ---
    set_index = None
    for i, token in enumerate(tokens):
        if token.lower() == "set":
            set_index = i
            break
        else:
            candidate = difflib.get_close_matches(token.lower(), ["set"], n=1, cutoff=0.8)
            if candidate:
                # Replace near-match token with the correct token "set"
                corrected_tokens[i] = candidate[0]
                set_index = i
                errors.append(f"you mean set instead of {token}")
                break
    if set_index is None:
        errors.append("Missing 'SET' clause.")
    
    # --- Process column assignments if SET clause is found ---
    if set_index is not None:
        # Find WHERE clause using near-match detection
        where_index = None
        for i, token in enumerate(tokens):
            if token.lower() == "where":
                where_index = i
                break
            else:
                candidate = difflib.get_close_matches(token.lower(), ["where"], n=1, cutoff=0.8)
                if candidate:
                    tokens[i] = candidate[0]
                    corrected_tokens[i] = "WHERE"  # Force uppercase
                    where_index = i
                    errors.append(f"you mean WHERE instead of {token}")
                    break
        # Process column assignments from SET clause until WHERE (if present)
        if where_index is None:
            column_tokens = tokens[set_index+1:]
        else:
            column_tokens = tokens[set_index+1:where_index]
        
        if not column_tokens:
            errors.append("No columns specified between 'SET' and 'WHERE'.")
            corrected_tokens.insert(set_index+1, "<col=value>")
        else:
            columns_str = " ".join(column_tokens)
            columns = [col.strip() for col in columns_str.split(",")]
            corrected_columns = []
            for col in columns:
                parts = col.split("=", 1)
                if len(parts) != 2:
                    errors.append(f"Invalid column assignment: '{col}'")
                    corrected_columns.append("<col=value>")
                    continue
                col_name = parts[0].strip()
                value_str = parts[1].strip()
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", col_name):
                    errors.append(f"Invalid column name: '{col_name}'")
                    corrected_columns.append("<col=value>")
                    continue
                valid = False
                if re.match(r"^'.+?'$", value_str) or re.match(r'^".+?"$', value_str):
                    valid = True
                elif re.match(r"^\d+$", value_str):
                    valid = True
                elif re.match(r"^(NULL|NOW\(\))$", value_str, re.IGNORECASE):
                    valid = True
                elif value_str.startswith("(") and "select" in value_str.lower():
                    valid = True
                if not valid:
                    errors.append(f"Invalid column assignment: '{col}'")
                    corrected_columns.append("<col=value>")
                else:
                    corrected_columns.append(col)
            if where_index is None:
                corrected_tokens[set_index+1:] = [", ".join(corrected_columns)]
            else:
                corrected_tokens[set_index+1:where_index] = [", ".join(corrected_columns)]
    
    # --- Validate WHERE condition if present ---
    if set_index is not None:
        # Use the updated tokens list to look for WHERE with near-match detection
        where_index = None
        for i, token in enumerate(tokens):
            if token.lower() == "where":
                where_index = i
                break
            else:
                candidate = difflib.get_close_matches(token.lower(), ["where"], n=1, cutoff=0.8)
                if candidate:
                    tokens[i] = candidate[0]
                    corrected_tokens[i] = "WHERE"
                    where_index = i
                    break
        if where_index is not None:
            if where_index == len(tokens)-1:
                errors.append("Missing condition after 'WHERE'.")
                corrected_tokens.append("<condition>")
            else:
                condition_tokens = tokens[where_index+1:]
                condition_str = " ".join(condition_tokens)
                conditions = re.split(r'\s+and\s+', condition_str, flags=re.IGNORECASE)
                invalid_conditions = []
                single_condition_regex = r"^[A-Za-z_][A-Za-z0-9_]*\s*(=|!=|>|<|>=|<=|in)\s*(?:'.+?'|\".+?\"|\d+|[A-Za-z0-9_]+|\(select\b.*?\))$"
                for cond in conditions:
                    cond = cond.strip()
                    if not re.match(single_condition_regex, cond, re.IGNORECASE):
                        invalid_conditions.append(cond)
                if invalid_conditions:
                    errors.append(f"Invalid condition after 'WHERE': {' and '.join(invalid_conditions)}")
                    corrected_tokens[where_index+1:] = ["<condition>"]
    
    print_update_errors(errors, corrected_tokens)

def process_query(query):
    query = query.strip()
    if not query:
        print("Empty query.")
        return
    
    tokens = query.split()
    if not tokens:
        print("Empty query.")
        return
    
    first_word = tokens[0].lower()
    if first_word != "update":
        candidate = difflib.get_close_matches(first_word, ["update"], n=1, cutoff=0.7)
        if candidate:
            print(f"Error: invalid keyword '{tokens[0]}', did you mean '{candidate[0]}'?")
            tokens[0] = candidate[0]
            corrected_query = " ".join(tokens)
            process_query(corrected_query)
            return
        else:
            print("Unsupported query type.")
            return
    
    validate_update_query(query)

if __name__ == '__main__':
    print("Enter SQL queries (type 'exit' to quit).")
    while True:
        user_query = input("Enter SQL query: ")
        if user_query.strip().lower() == "exit":
            print("Exiting...")
            break
        process_query(user_query)
