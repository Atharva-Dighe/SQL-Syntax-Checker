import difflib
from .create_validator import validate_create_query
from .create_database_validator import validate_create_database_query
from .select_validator import validate_select_query
from .update_validator import process_query as process_update_query
from .insert_validator import process_query as process_insert_query
from .delete_validator import process_query as process_delete_query
from .drop_validator import process_query as process_drop_query
from .alter_validator import process_query as process_alter_query
from .truncate_validator import process_query as process_truncate_query
from .trigger_validator import process_trigger_query

def validate_brackets_and_quotes(query):
    errors = []
    # Check for balanced parentheses.
    stack = []
    for idx, char in enumerate(query):
        if char == '(':
            stack.append(idx)
        elif char == ')':
            if stack:
                stack.pop()
            else:
                errors.append("Unmatched closing parenthesis at position {}".format(idx))
    if stack:
        errors.append("Unmatched opening parenthesis at position(s): " + ", ".join(str(i) for i in stack))
    
    # Check for balanced single quotes.
    # This loop flips the in_quote flag when encountering a single quote.
    # It also skips over escaped quotes (two consecutive single quotes).
    in_quote = False
    quote_start = None
    i = 0
    while i < len(query):
        if query[i] == "'":
            # Check for an escaped quote.
            if in_quote and i + 1 < len(query) and query[i+1] == "'":
                i += 2
                continue
            in_quote = not in_quote
            if in_quote:
                quote_start = i
            else:
                quote_start = None
        i += 1
    if in_quote:
        errors.append("Unmatched single quote starting at position {}".format(quote_start))
    
    return errors

def validate_internal_semicolon(query):
    """
    Validate that any semicolon outside of quotes appears only as a statement terminator at the very end.
    Any semicolon found in the middle of the query (outside of quoted strings) is flagged as an error.
    """
    errors = []
    in_quote = False
    semicolon_positions = []
    i = 0
    while i < len(query):
        char = query[i]
        if char == "'":
            if in_quote and i + 1 < len(query) and query[i+1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif char == ';' and not in_quote:
            semicolon_positions.append(i)
        i += 1
    trimmed = query.rstrip()
    # Allow a single semicolon only at the very end.
    if semicolon_positions:
        if len(semicolon_positions) == 1 and semicolon_positions[0] == len(trimmed) - 1:
            pass
        else:
            for pos in semicolon_positions:
                if pos != len(trimmed) - 1:
                    errors.append("Invalid semicolon found at position {}".format(pos))
    return errors

def process_query(query):
    query = query.strip()
    if not query:
        print("Empty query.")
        return

    # Validate brackets, quotes, and internal semicolons before further processing.
    bracket_quote_errors = validate_brackets_and_quotes(query)
    internal_semicolon_errors = validate_internal_semicolon(query)
    errors = bracket_quote_errors + internal_semicolon_errors
    if errors:
        print("Errors in query:")
        for err in errors:
            print(" -", err)
        return

    tokens = query.split()
    if not tokens:
        print("Empty query.")
        return

    first_word = tokens[0].lower()

    if first_word == 'create':
        if len(tokens) >= 2:
            second_word = tokens[1].lower() 
            if second_word == 'trigger':
                print("triri")
                process_trigger_query(query)
            elif second_word == 'table':
                validate_create_query(query)
            elif second_word == 'database':
                validate_create_database_query(query)
            else:
                candidate = difflib.get_close_matches(second_word, ['table', 'database', 'trigger'], n=1, cutoff=0.7)
                if candidate:
                    print(f"Error: invalid keyword '{second_word}', did you mean '{candidate[0]}'?")
                    tokens[1] = candidate[0]
                    corrected_query = " ".join(tokens)
                    print("You mean:", corrected_query)
                    process_query(corrected_query)
                else:
                    print("Unsupported CREATE query type. Please use 'create table', 'create database', or 'create trigger'.")
        else:
            print("Incomplete CREATE query.")
    elif first_word == 'select':
        validate_select_query(query)
    elif first_word == 'update':
        process_update_query(query)
    elif first_word == 'insert':
        process_insert_query(query)
    elif first_word == 'delete':
        process_delete_query(query)
    elif first_word == 'drop':
        process_drop_query(query)
    elif first_word == 'alter':
        process_alter_query(query)
    elif first_word == 'truncate':
        process_truncate_query(query)
    else:
        candidate = difflib.get_close_matches(first_word, 
            ['create', 'select', 'update', 'insert', 'delete', 'drop', 'alter', 'truncate', 'trigger'], n=1, cutoff=0.7)
        if candidate:
            corrected_keyword = candidate[0]
            print(f"Error: invalid keyword '{first_word}', did you mean '{corrected_keyword}'?")
            tokens[0] = corrected_keyword
            corrected_query = " ".join(tokens)
            print("You mean:", corrected_query)
            process_query(corrected_query)
        else:
            print("Unsupported query type. Please use a valid SQL query type (CREATE, SELECT, UPDATE, INSERT, DELETE, DROP, ALTER, TRUNCATE, or TRIGGER).")

def main():
    print("Enter SQL queries (type 'exit' to quit).")
    while True:
        user_query = input("Enter SQL query: ")
        if user_query.strip().lower() == "exit":
            print("Exiting...")
            break
        process_query(user_query)

if __name__ == '__main__':
    main()
