import re
import difflib
from .common import validate_semicolon

KEYWORDS = {
    'select', 'from', 'where', 'join', 'inner', 'outer', 'left', 'right',
    'on', 'group by', 'order by', 'having', 'as', 'and', 'or', 'between',
    'like', 'in', 'exists', 'asc', 'desc', 'limit', 'offset', 'cast', 'true',
    'false', 'null', 'case', 'when', 'then', 'else', 'end', 'distinct', '*',
    'order', 'by', 'union','GROUP BY','group',
    # Aggregate functions
    'count', 'sum', 'avg', 'min', 'max', 'stddev', 'variance', 'distinct'
}

def correct_star(token):
    # Allowed characters for star variants (digits removed)
    allowed_chars = set("*#$!%^&@")
    if token != "*" and all(char in allowed_chars for char in token):
        return "*"
    return token

def correct_keyword_case(token):
    if not token:
        return token
    lower_token = token.lower()
    if lower_token in KEYWORDS:
        return lower_token.upper()
    candidates = difflib.get_close_matches(lower_token, KEYWORDS, n=1, cutoff=0.8)
    return candidates[0].upper() if candidates else token

def fix_nested(query):
    pattern = re.compile(r'\(([^()]+)\)')
    while True:
        new_query = pattern.sub(
            lambda m: "(" + validate_select_query(m.group(1).strip(), return_values=True)["suggestion"].rstrip(";") + ")"
            if is_near_select(m.group(1).strip()) else m.group(0),
            query
        )
        if new_query == query:
            break
        query = new_query
    return query

def is_near_select(subquery):
    parts = subquery.split()
    return bool(parts) and difflib.get_close_matches(parts[0].lower(), ["select"], n=1, cutoff=0.8)

def validate_select_query(query, return_values=False):
    errors = []
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    query = query.strip().rstrip(";").strip()
    
    # Tokenize: split on parenthesized groups, commas, or non-comma/non-whitespace groups.
    tokens = re.findall(r'\(.*?\)|[^,\s]+|,', query)
    corrected_tokens = []
    i = 0
    n = len(tokens)
    
    while i < n:
        token = tokens[i]
        if token == ',':
            corrected_tokens.append(token)
            i += 1
            continue
        new_token = correct_star(token)
        if new_token == token:
            new_token = correct_keyword_case(token)
        if token.lower() != new_token.lower():
            errors.append(f"'{token}'Do You Mean? => '{new_token.lower()}'")
        corrected_tokens.append(new_token)
        i += 1

    # --- Check the columns section (between SELECT and FROM) ---
    try:
        select_index = corrected_tokens.index("SELECT")
        from_index = corrected_tokens.index("FROM")
        # Extract tokens for columns between SELECT and FROM.
        columns_tokens = corrected_tokens[select_index+1:from_index]
        # Check if there are any non-comma tokens.
        if not any(tok.strip() and tok != ',' for tok in columns_tokens):
            errors.append("Missing columns in SELECT clause.")
            corrected_tokens.insert(select_index+1, "<col or *>")
        else:
            # Look for misplaced clause tokens that belong after FROM.
            reserved_in_columns = {"WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET"}
            misplace_idx = None
            for idx, tok in enumerate(columns_tokens):
                # If a reserved keyword appears in the column list, mark its index.
                if tok.upper() in reserved_in_columns:
                    misplace_idx = idx
                    break
            if misplace_idx is not None:
                # Everything from the first reserved token onward is considered misplaced.
                misplaced_clause = columns_tokens[misplace_idx:]
                new_columns = columns_tokens[:misplace_idx]
                corrected_tokens[select_index+1:from_index] = new_columns
                errors.append("Misplaced clause tokens in column list. They should appear after the table name.")
                # Now, insert the misplaced tokens after the table name.
                # Assume the table name is the first token after FROM.
                table_index = from_index + 1
                corrected_tokens = (
                    corrected_tokens[:table_index+1] +
                    misplaced_clause +
                    corrected_tokens[table_index+1:]
                )
            # Finally, validate that each column token is not a reserved keyword (unless it is "*").
            for idx in range(select_index+1, from_index):
                tok = corrected_tokens[idx]
                if tok == ',':
                    continue
                if tok.upper() in KEYWORDS and tok != "*":
                    errors.append(f"Invalid column name '{tok}', column names cannot be SQL keywords.")
                    corrected_tokens[idx] = "<col>"
    except ValueError:
        # If SELECT or FROM is missing, errors are already reported.
        pass

    # --- Check the condition clause (after WHERE) ---
    if "WHERE" in corrected_tokens:
        where_index = corrected_tokens.index("WHERE")
        # If there is no condition (i.e. no token after WHERE), add a placeholder.
        if where_index == len(corrected_tokens) - 1:
            errors.append("Missing condition in WHERE clause.")
            corrected_tokens.append("<condition>")

    # Rebuild suggestion.
    suggestion = ' '.join(corrected_tokens)
    suggestion = re.sub(r'\s+,', ',', suggestion)
    suggestion = re.sub(r',\s*', ', ', suggestion).strip() + ';'
    suggestion = fix_nested(suggestion)

    # Structural checks.
    if "SELECT" not in corrected_tokens:
        errors.insert(0, "Missing SELECT keyword")
    if "FROM" not in corrected_tokens:
        errors.insert(0, "Missing FROM clause")

    # Check for duplicate WHERE clauses.
    for i, token in enumerate(corrected_tokens):
        if i > 0 and token == 'WHERE' and corrected_tokens[i-1] == 'WHERE':
            errors.append("Duplicate WHERE clause")
            del corrected_tokens[i]

    if return_values:
        return {'errors': errors, 'suggestion': suggestion}
    else:
        if errors:
            print("Errors found in SELECT query:")
            for err in errors:
                print(" -", err)
            print("Do You Mean? => ", suggestion)
        else:
            print("Correct, no errors in SELECT query..")

def process_select_query(query):
    tokens = query.strip().split()
    if not tokens:
        return {'errors': ['Empty query'], 'suggestion': 'SELECT;'}
    first_token = correct_keyword_case(tokens[0])
    if first_token != 'SELECT':
        return {'errors': [f"Invalid starting keyword '{tokens[0]}'"], 'suggestion': 'SELECT ...;'}
    return validate_select_query(query, return_values=True)

# Example usage
if __name__ == '__main__':
    test_queries = [
        "SELECT *,@ FROM users;",                # Expected: invalid; suggestion: SELECT *,* FROM users;
        "SELECT *,* FROM users;",                # Expected: valid query
        "SELECT *,id FROM users;",               # Expected: valid query
        "SELECT ** FROM users;",                 # Expected: invalid; suggestion: SELECT * FROM users;
        "SELECT FROM users;",                    # Expected: invalid; suggestion: SELECT <col or *> FROM users;
        "SELECT id, name WHERE age > 30 FROM users;",  # Expected: invalid; suggestion: SELECT id, name FROM users WHERE age > 30;
        "SELECT *,ame from user where ;"          # Expected: suggestion: SELECT *,ame from user where <condition>;
    ]
    for q in test_queries:
        print(f"Testing query: {q}")
        result = process_select_query(q)
        print("Errors:", result['errors'])
        print("Suggestion:", result['suggestion'])
        print()
