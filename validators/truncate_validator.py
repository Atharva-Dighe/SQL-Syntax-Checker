import re
import difflib

def validate_semicolon(query):
    """Checks that the query ends with a semicolon."""
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""

def validate_truncate_query(query):
    errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    query_stripped = query.strip().rstrip(";").strip()
    tokens = query_stripped.split()
    corrected_tokens = tokens[:]
    
    if len(tokens) < 3:
        errors.append("TRUNCATE query must have at least 'TRUNCATE TABLE <table_name>'.")
    
    if tokens[0].lower() != "truncate":
        errors.append(f"Error: invalid keyword '{tokens[0]}', did you mean 'TRUNCATE'?")
        corrected_tokens[0] = "TRUNCATE"
    
    if len(tokens) > 1 and tokens[1].lower() != "table":
        errors.append("TRUNCATE query must contain 'TRUNCATE TABLE'.")
        corrected_tokens[1] = "TABLE"
    
    if len(tokens) > 2:
        table_name = tokens[2]
    else:
        errors.append("Missing table name.")
        table_name = "<table_name>"
        corrected_tokens.append(table_name)
    
    if errors:
        print("Errors found in TRUNCATE query:")
        for err in errors:
            print(" -", err)
        suggestion = " ".join(corrected_tokens) + ";"
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in TRUNCATE query.")

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
    
    if first_word not in ['truncate']:
        candidate = difflib.get_close_matches(first_word, ['truncate'], n=1, cutoff=0.7)
        if candidate:
            print(f"Error: invalid keyword '{first_word}', did you mean '{candidate[0]}'?")
            tokens[0] = candidate[0]
            corrected_query = " ".join(tokens)
            process_query(corrected_query)
            return
        else:
            print("Unsupported query type. Please use a TRUNCATE query.")
            return
    
    validate_truncate_query(" ".join(tokens))

if __name__ == '__main__':
    print("Enter TRUNCATE queries (type 'exit' to quit).")
    while True:
        user_query = input("Enter SQL query: ")
        if user_query.strip().lower() == "exit":
            print("Exiting...")
            break
        process_query(user_query)
