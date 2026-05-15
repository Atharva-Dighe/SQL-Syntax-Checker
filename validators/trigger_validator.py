import re
import difflib
from .common import validate_semicolon  # Reuse semicolon validation

TRIGGER_KEYWORDS = {
    'create', 'trigger', 'before', 'after', 'instead', 'of', 'insert', 
    'update', 'delete', 'on', 'for', 'each', 'row', 'statement', 
    'referencing', 'old', 'new', 'as', 'when', 'begin', 'end'
}

def correct_trigger_keyword(token):
    """Correct trigger-related keywords with case preservation"""
    if not token:
        return token
    
    lower_token = token.lower()
    candidates = difflib.get_close_matches(lower_token, TRIGGER_KEYWORDS, n=1, cutoff=0.7)
    
    if candidates:
        candidate = candidates[0]
        if candidate == 'instead' and lower_token == 'instead':
            return 'INSTEAD'
        return candidate.upper() if candidate in TRIGGER_KEYWORDS else token
    return token

def validate_trigger_query(query):
    errors = []
    suggestion = []
    tokens = re.findall(r'''(?:[^'"\s]+|"[^"]*"|'[^']*')+''', query.strip().rstrip(';'))
    
    if not tokens or tokens[0].lower() != 'create' or len(tokens) < 3:
        errors.append("Invalid trigger syntax. Expected 'CREATE TRIGGER'.")
        return {'errors': errors, 'suggestion': 'CREATE TRIGGER <trigger_name> BEFORE|AFTER|INSTEAD OF INSERT|UPDATE|DELETE ON <table_name>'}
    
    pos = 0
    while pos < len(tokens):
        token = tokens[pos]
        corrected = correct_trigger_keyword(token)
        suggestion.append(corrected)
        pos += 1
    
    semicolon_ok, semicolon_err = validate_semicolon(query)
    if not semicolon_ok:
        errors.append(semicolon_err)
    
    return {'errors': errors, 'suggestion': ' '.join(suggestion) + ';'}

def process_trigger_query(query):
    print("tigger ")
    query = query.strip()
    if not query:
        return {'errors': ['Empty query'], 'suggestion': ''}
    return validate_trigger_query(query)
