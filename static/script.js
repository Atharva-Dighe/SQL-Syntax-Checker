let editor;
let isProcessing = false;

// Object to store query sequences
const querySequences = {
    select: [
        "SELECT * FROM users;",
        "SELECT id, name FROM users WHERE age > 30;",
        "SELECT COUNT (*) FROM table1 WHERE status = 'completed';",
        "SELECT * FROM Products ORDER BY Price;",
        "SELECT ProductID, ProductName, CategoryName FROM Products INNER JOIN Categories ON Products.CategoryID = Categories.CategoryID;",
        "SELECT column_name(s) FROM table_name WHERE condition GROUP BY column_name(s) HAVING condition ORDER BY column_name(s);"
    ],
    createT: [
        "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(255), salary FLOAT);",
        "CREATE TABLE products (id INT PRIMARY KEY, product_name VARCHAR(255), price FLOAT);"
    ],
    createD: [
        "CREATE DATABASE company;",
        "CREATE DATABASE IF NOT EXISTS sales;"
    ],
    delete: [
        "DELETE FROM users WHERE id = 5;",
        "DELETE FROM orders WHERE order_date < '2023-01-01';"
    ],
    drop: [
        "DROP TABLE temp_data;",
        "DROP TABLE IF EXISTS archived_orders;"
    ],
    update: [
        "UPDATE users SET last_login = NOW() WHERE id = 1;",
        "UPDATE orders SET status = 'shipped' WHERE order_id = 1001;"
    ],
    insert: [
        "INSERT INTO employees (id, name, salary) VALUES (1, 'Hufflepuff', 50000000);",
        "INSERT INTO Customers (CustomerName, ContactName, Address, City, PostalCode, Country) VALUES ('Cardinal', 'Tom B. Erichsen', 'Skagen 21', 'Stavanger', '4006', 'Norway'),('Greasy Burger', 'Per Olsen', 'Gateveien 15', 'Sandnes', '4306', 'Norway'), ('Tasty Tee', 'Finn Egan', 'Streetroad 19B', 'Liverpool', 'L1 0AA', 'UK');"
    ],
    alter: [
        "ALTER TABLE users ADD COLUMN phone_number VARCHAR(15);",
        "ALTER TABLE orders MODIFY COLUMN order_date DATETIME;"
    ],
    trunc: [
        "TRUNCATE TABLE logs;",
        "TRUNCATE TABLE temp_data;"
    ]
};

// Object to track the current query index for each type
const queryIndex = {};

document.addEventListener('DOMContentLoaded', () => {
    // Initialize CodeMirror with enhanced options
    editor = CodeMirror.fromTextArea(document.getElementById('sqlEditor'), {
        mode: 'sql',
        theme: 'dracula',
        lineNumbers: true,
        autofocus: true,
        indentWithTabs: true,
        tabSize: 2,
        lineWrapping: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        styleActiveLine: true,
        extraKeys: {
            "Ctrl-Enter": validateQuery,
            "Cmd-Enter": validateQuery,
            "Ctrl-Space": "autocomplete"
        }
    });

    document.getElementById('validateBtn').addEventListener('click', validateQuery);
    document.getElementById('clearBtn').addEventListener('click', clearEditor);
    initializeTooltips();
});

async function validateQuery() {
    if (isProcessing) return;
    
    const query = editor.getValue().trim();
    if (!query) {
        showNotification('Please enter a SQL query', 'error');
        return;
    }
    
    isProcessing = true;
    const validateBtn = document.getElementById('validateBtn');
    validateBtn.classList.add('loading');
    validateBtn.disabled = true;

    const formData = new URLSearchParams();
    formData.append('queryInput', query);

    try {
        const response = await fetch('/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData.toString()
        });
        const data = await response.json();
        console.log(data);
        console.log(data.output.split(" ")[0]);

        displayValidationResult(data.output);
    } catch (error) {
        document.getElementById('resultArea').innerText = 'An error occurred: ' + error;
    } finally {
        isProcessing = false;
        validateBtn.classList.remove('loading');
        validateBtn.disabled = false;
    }
}

function displayValidationResult(result, suggestion = "") {
    const resultArea = document.getElementById('resultArea');

    // Clear previous content (no history)
    resultArea.innerHTML = "";

    let messageType = result.startsWith("Error:") || result.startsWith("Errors") ? "error" : "success";
    let color = messageType === "error" ? "#FF0000" : "lime";

    // Create the result div
    let newLine = document.createElement("div");
    newLine.style.fontFamily = "monospace";
    newLine.style.textAlign = "left";
    newLine.style.color = color;
    newLine.style.fontSize = "18px";
    newLine.style.whiteSpace = "pre-wrap"; // Preserve line breaks like a real terminal

    // Add typing effect
    let i = 0;
    function typeEffect() {
        if (i < result.length) {
            newLine.innerHTML += result.charAt(i);
            i++;
            setTimeout(typeEffect, 50); // Speed of typing effect
        } else {
            // Show suggestion after typing completes
            if (suggestion) {
                let suggestionLine = document.createElement("div");
                suggestionLine.style.fontFamily = "monospace";
                suggestionLine.style.color = "gray";
                suggestionLine.style.fontSize = "16px";
                suggestionLine.style.marginTop = "5px";
                suggestionLine.innerHTML = `💡 Suggestion: ${suggestion}`;
                resultArea.appendChild(suggestionLine);
            }

            // Add blinking cursor
            newLine.innerHTML += '<span class="cursor">█</span>';
        }
    }

    // Append new message to terminal
    resultArea.appendChild(newLine);
    typeEffect();
}

// CSS for terminal and blinking cursor (Add in your CSS file or inside a <style> tag)
const terminalStyles = `
    #resultArea {
        background-color: black;
        color: lime;
        padding: 20px;
        font-family: 'Courier New', monospace;
        font-size: 18px;
        height: 100px;
        overflow: hidden; /* No scrolling, always latest message */
        border: 2px solid lime;
        border-radius: 5px;
    }
    
    .cursor {
        animation: blink 1ms infinite;
    }

    @keyframes blink {
        50% { opacity: 0; }
    }
`;
function clearEditor() {
    editor.setValue('');
    editor.focus();
    document.getElementById('resultArea').innerHTML = `<div class="placeholder-text">Results will appear here after validation</div>`;
    showNotification('Editor cleared', 'info');
}

function loadExample(type) {
    if (!querySequences[type]) return;

    if (!(type in queryIndex)) {
        queryIndex[type] = 0;
    }

    const query = querySequences[type][queryIndex[type]];
    editor.setValue(query);
    editor.focus();
    showNotification(`Loaded ${type.toUpperCase()} example (${queryIndex[type] + 1}/${querySequences[type].length})`, 'info');

    queryIndex[type] = (queryIndex[type] + 1) % querySequences[type].length;
}

function initializeTooltips() {
    const exampleButtons = document.querySelectorAll('.example-buttons button');
    exampleButtons.forEach(button => {
        const typeMatch = button.onclick.toString().match(/loadExample\('(.+?)'\)/);
        if (typeMatch) {
            const type = typeMatch[1];
            button.setAttribute('data-tooltip', `Load ${type.toUpperCase()} example query`);
        }
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
