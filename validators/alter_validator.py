import re
import difflib

def validate_semicolon(query):
    """Checks that the query ends with a semicolon."""
    if not query.strip().endswith(";"):
        return False, "Missing semicolon at end of query."
    return True, ""

def correct_keyword(token, possible_keywords, cutoff=0.7):
    """Correct a token using difflib while preserving case based on the provided keywords."""
    if not token:
        return token
    lower_token = token.lower()
    lower_possible = [kw.lower() for kw in possible_keywords]
    matches = difflib.get_close_matches(lower_token, lower_possible, n=1, cutoff=cutoff)
    if matches:
        matched_index = lower_possible.index(matches[0])
        return possible_keywords[matched_index]
    return token

def validate_alter_query(query):
    errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    query_stripped = query.strip().rstrip(';').strip()
    original_tokens = re.split(r'\s+', query_stripped)
    corrected_tokens = original_tokens.copy()
    table_name = None

    # Phase 1: Validate basic structure and correct main keywords
    if len(original_tokens) == 0:
        errors.append("Empty query")
        return {'errors': errors, 'suggestion': "ALTER TABLE <table> <action>;"}

    # Check ALTER keyword
    corrected_alter = correct_keyword(original_tokens[0], ['ALTER'])
    if corrected_alter != original_tokens[0]:
        errors.append(f"'{original_tokens[0]}' you mean '{corrected_alter}'")
        corrected_tokens[0] = corrected_alter

    # Check TABLE keyword
    if len(original_tokens) > 1:
        corrected_table = correct_keyword(original_tokens[1], ['TABLE'])
        if corrected_table != original_tokens[1]:
            errors.append(f"'{original_tokens[1]}' you mean '{corrected_table}'")
            corrected_tokens[1] = corrected_table
    else:
        errors.append("Missing TABLE clause")

    # Validate table name
    if len(original_tokens) > 2:
        table_name = original_tokens[2]
    else:
        errors.append("Missing table name")
        table_name = "<table>"

    # Phase 2: Validate action and sub-clauses
    if len(corrected_tokens) > 3:
        valid_actions = ['ADD', 'DROP', 'MODIFY', 'CHANGE', 'RENAME']
        action = corrected_tokens[3]
        corrected_action = correct_keyword(action, valid_actions)
        if corrected_action != action:
            errors.append(f"'{action}' you mean '{corrected_action}'")
            corrected_tokens[3] = corrected_action
            action = corrected_action

        # Handle specific actions
        if action.upper() == 'DROP':
            if len(corrected_tokens) > 4:
                column_keyword = corrected_tokens[4]
                corrected_column = correct_keyword(column_keyword, ['COLUMN'])
                if corrected_column != column_keyword:
                    errors.append(f"'{column_keyword}' you mean '{corrected_column}'")
                    corrected_tokens[4] = corrected_column
            else:
                errors.append("Missing COLUMN keyword after DROP")
                corrected_tokens.append('COLUMN')
            # Validate column name if provided
            if len(corrected_tokens) > 5:
                if not re.match(r'^[a-zA-Z_][\w$]*$', corrected_tokens[5]):
                    errors.append(f"Invalid column name: {corrected_tokens[5]}")
            else:
                errors.append("Missing column name")
                corrected_tokens.append('<column>')
        elif action.upper() in ['ADD', 'MODIFY']:
            # For simplicity, we'll assume these actions are acceptable as-is.
            pass
        # You can add additional validation for other actions here.
    else:
        errors.append("Missing action clause")

    # Phase 3: Build final suggestion
    corrected_tokens[2] = table_name  # Ensure table name remains unchanged
    suggestion = ' '.join(corrected_tokens) + ';'
    
    if errors:
        print("Errors found in ALTER query:")
        for err in errors:
            print(" -", err)
        print("You mean:", suggestion)
    else:
        print("Correct, no errors in ALTER query.")
        print("You mean:", suggestion)
    
    return {'errors': errors, 'suggestion': suggestion}

def process_query(query):
    query = query.strip()
    if not query:
        return {'errors': ['Empty query'], 'suggestion': ''}
    
    tokens = query.split()
    if not tokens:
        return {'errors': ['Empty query'], 'suggestion': ''}
    
    first_word = query.split()[0].upper()
    if first_word not in ['ALTER']:
        candidates = difflib.get_close_matches(first_word.lower(), ['alter'], cutoff=0.7)
        if candidates:
            corrected = candidates[0].upper()
            return {
                'errors': [f"Invalid keyword '{first_word}', did you mean '{corrected}'?"],
                'suggestion': query.replace(first_word, corrected, 1)
            }
    return validate_alter_query(query)

# Example test
if __name__ == '__main__':
    # Test query: This should print "Correct, no errors" and the same suggestion.
    test_query = "ALTER TABLE Customers DROP COLUMN Email;"
    result = process_query(test_query)
    print("Errors:")
    if result['errors']:
        for e in result['errors']:
            print(f" - {e}")
    else:
        print("None")
    print("\nSuggestion:", result['suggestion'])
