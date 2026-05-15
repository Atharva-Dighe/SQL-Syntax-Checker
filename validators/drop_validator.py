import re
import difflib

def validate_semicolon(query):
    """Checks that the query ends with a semicolon."""
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""

def validate_drop_query(query):
    errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    query_stripped = query.strip().rstrip(";").strip()
    tokens = query_stripped.split()
    corrected_tokens = tokens[:]  # Copy for suggestion
    
    if len(tokens) < 3:
        errors.append("DROP query must have at least 'DROP TABLE <table_name>'.")
    
    if tokens[0].lower() != "drop":
        errors.append(f"Error: invalid keyword '{tokens[0]}', did you mean 'DROP'?")
        corrected_tokens[0] = "DROP"
    
    if len(tokens) > 1 and tokens[1].lower() != "table":
        errors.append("DROP query must contain 'DROP TABLE'.")
        corrected_tokens[1] = "TABLE"
    
    # Check for optional "IF EXISTS"
    if len(tokens) > 2 and tokens[2].lower() == "if":
        if len(tokens) > 3 and tokens[3].lower() == "exists":
            if len(tokens) < 5:
                errors.append("DROP TABLE IF EXISTS must include a table name.")
            # Else, table name is tokens[4]
        else:
            errors.append(f"Unexpected token '{tokens[2]}', did you mean 'IF EXISTS'?")
            corrected_tokens[2] = "IF"
            corrected_tokens.insert(3, "EXISTS")
    elif len(tokens) > 2 and tokens[2].lower() not in ["if", "exists"]:
        # Assume tokens[2] is table name.
        pass
    elif len(tokens) < 3:
        errors.append("Missing table name.")
    
    if errors:
        print("Errors found in DROP query:")
        for err in errors:
            print(" -", err)
        suggestion = " ".join(corrected_tokens) + ";"
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in DROP query.")

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
    if first_word != "drop":
        candidate = difflib.get_close_matches(first_word, ["drop"], n=1, cutoff=0.7)
        if candidate:
            tokens[0] = candidate[0].upper()
            corrected_query = " ".join(tokens)
            return process_query(corrected_query)
        else:
            print("Unsupported query type.")
            return
    return validate_drop_query(query)

if __name__ == '__main__':
    print("Enter DROP queries (type 'exit' to quit).")
    while True:
        user_query = input("Enter SQL query: ")
        if user_query.strip().lower() == "exit":
            print("Exiting...")
            break
        process_query(user_query)
