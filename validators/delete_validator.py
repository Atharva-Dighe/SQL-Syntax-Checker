import re
import difflib

def validate_semicolon(query):
    """Checks that the query ends with a semicolon."""
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""

def validate_delete_query(query):
    errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    query_stripped = query.strip().rstrip(";").strip()
    tokens = query_stripped.split()
    corrected_tokens = tokens[:]  # Copy for suggestion
    
    if len(tokens) < 3:
        errors.append("DELETE query must have at least 'DELETE FROM <table_name>'.")
    
    if tokens[0].lower() != "delete":
        errors.append(f"Error: invalid keyword '{tokens[0]}', did you mean 'DELETE'?")
        corrected_tokens[0] = "DELETE"
    
    if len(tokens) > 1 and tokens[1].lower() != "from":
        errors.append("DELETE query must start with 'DELETE FROM'.")
        corrected_tokens[1] = "FROM"
    
    if len(tokens) > 2:
        table_name = tokens[2]
    else:
        errors.append("Missing table name.")
    
    if len(tokens) > 3 and tokens[3].lower() != "where":
        errors.append(f"Unexpected token '{tokens[3]}' after table name.")
        corrected_tokens[3] = "WHERE"
    
    if errors:
        print("Errors found in DELETE query:")
        for err in errors:
            print(" -", err)
        suggestion = " ".join(corrected_tokens) + ";"
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in DELETE query.")

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
    if first_word != "delete":
        candidate = difflib.get_close_matches(first_word, ["delete"], n=1, cutoff=0.7)
        if candidate:
            tokens[0] = candidate[0].upper()
            corrected_query = " ".join(tokens)
            return process_query(corrected_query)
        else:
            print("Unsupported query type.")
            return
    return validate_delete_query(query)

if __name__ == '__main__':
    print("Enter DELETE queries (type 'exit' to quit).")
    while True:
        user_query = input("Enter SQL query: ")
        if user_query.strip().lower() == "exit":
            print("Exiting...")
            break
        process_query(user_query)
