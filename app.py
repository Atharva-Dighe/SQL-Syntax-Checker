import io
import sys
from flask import Flask, render_template, request, jsonify
from validators.main import process_query  # type: ignore # your console-based process_query function

app = Flask(__name__)

def run_query(query):
    """Redirect stdout to capture the printed output from process_query."""
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        process_query(query)
    finally:
        sys.stdout = old_stdout
    return buffer.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validate', methods=['POST'])
def validate():
    query = request.form.get("queryInput", "").strip()
    if not query:
        return jsonify({"output": "Empty query."})
    
    output = run_query(query)
    return jsonify({"output": output})

if __name__ == '__main__':
    app.run(debug=True)
