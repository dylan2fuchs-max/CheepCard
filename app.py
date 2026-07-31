from flask import Flask, request, render_template_string
import re
from synergy_engine import run_synergy_analysis  # SAFELY IMPORTS THE READ-ONLY MATHEMATICAL ENGINE

app = Flask(__name__)

# --- WEB DASHBOARD FRONTEND LOOK & FEEL WITH CLEAR BUTTON ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>CheepCard Synergy Tool</title>
    <style>
        :root {
            --bg-color: #f4f6f9;
            --box-bg: white;
            --text-color: #333;
            --title-color: #2c3e50;
            --border-color: #bdc3c7;
            --th-bg: #ecf0f1;
            --row-border: #ddd;
            --card-text: #555;
        }

        [data-theme="dark"] {
            --bg-color: #121212;
            --box-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --title-color: #ecf0f1;
            --border-color: #444;
            --th-bg: #2d2d2d;
            --row-border: #333;
            --card-text: #b0b0b0;
        }

        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 40px auto; 
            padding: 20px; 
            background-color: var(--bg-color); 
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
        }
        
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        h1 { color: var(--title-color); margin: 0; }
        
        .theme-btn {
            background-color: #7f8c8d;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: background-color 0.2s;
        }
        .theme-btn:hover { background-color: #95a5a6; }
        
        textarea { 
            width: 100%; 
            height: 150px; 
            padding: 12px; 
            border: 2px solid var(--border-color); 
            border-radius: 6px; 
            box-sizing: border-box; 
            font-size: 14px; 
            background-color: var(--box-bg);
            color: var(--text-color);
        }
        
        /* Flex wrapper to place buttons neatly side-by-side */
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        button[type="submit"] { 
            background-color: #3498db; 
            color: white; 
            padding: 12px 20px; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 16px; 
            flex: 3; /* Takes up 75% of the row width */
            font-weight: bold;
        }
        button[type="submit"]:hover { background-color: #2980b9; }
        
        /* Styled Clear/Reset Button */
        .clear-btn {
            background-color: #e74c3c;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            flex: 1; /* Takes up 25% of the row width */
            font-weight: bold;
            transition: background-color 0.2s;
        }
        .clear-btn:hover { background-color: #c0392b; }

        .result-box { 
            background: var(--box-bg); 
            padding: 20px; 
            margin-top: 20px; 
            border-radius: 8px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.15); 
        }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid var(--row-border); }
        th { background-color: var(--th-bg); color: var(--title-color); }
        small { color: var(--card-text); }
    </style>
</head>
<body>
    <div class="header-container">
        <h1>CheepCard Deck Synergy Evaluator</h1>
        <button class="theme-btn" id="themeToggle" onclick="toggleTheme()">🌓 Dark Mode</button>
    </div>
    
    <div class="result-box">
        <form method="POST" id="deckForm">
            <p><strong>Paste your deck list below (One card name per line):</strong></p>
            <textarea name="decklist" id="deckTextArea" placeholder="1 Timber Gorge&#10;1 Game Trail&#10;8 Selesnya Sanctuary">{{ raw_input }}</textarea>
            
            <div class="btn-group">
                <button type="submit">Evaluate Deck Synergy</button>
                <!-- Dynamic JavaScript button cleans out the input instantly without a page reload -->
                <button type="button" class="clear-btn" onclick="clearInput()">Clear List</button>
            </div>
        </form>
    </div>

    {% if report %}
    <div class="result-box" id="reportSection">
        <h2>Synergy Report (Total Cards: {{ report.deck_size }})</h2>
        <table>
            <tr>
                <th>Identified Theme Variable</th>
                <th>Card Count</th>
                <th>Deck Percentage</th>
                <th>Matching Cards</th>
            </tr>
            {% for item in report.themes %}
            <tr>
                <td><strong>{{ item.theme }}</strong></td>
                <td>{{ item.count }}</td>
                <td>{{ item.percentage }}</td>
                <td><small>{{ item.cards }}</small></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}

    <script>
        // Clears out text field contents smoothly
        function clearInput() {
            document.getElementById('deckTextArea').value = '';
            // Optional: Hides old evaluation report grid instantly when text drops
            const report = document.getElementById('reportSection');
            if (report) report.style.display = 'none';
        }

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            let targetTheme = 'light';
            if (currentTheme === 'light' || !currentTheme) targetTheme = 'dark';
            
            document.documentElement.setAttribute('data-theme', targetTheme);
            localStorage.setItem('theme', targetTheme);
            document.getElementById('themeToggle').innerText = targetTheme === 'dark' ? '☀️ Light Mode' : '🌓 Dark Mode';
        }

        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.getElementById('themeToggle').innerText = savedTheme === 'dark' ? '☀️ Light Mode' : '🌓 Dark Mode';
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    report = None
    raw_input = ""
    if request.method == "POST":
        raw_input = request.form.get("decklist", "")
        
        deck_list = []
        for line in raw_input.split("\n"):
            clean_line = line.strip()
            if not clean_line:
                continue
            clean_name = re.sub(r'^\d+[xX]?\s+', '', clean_line).strip()
            if clean_name:
                deck_list.append(clean_name)
                
        report = run_synergy_analysis(deck_list)
        
    return render_template_string(HTML_PAGE, report=report, raw_input=raw_input)

print("Starting CheepCard Local Web Application Server...")
app.run(debug=True, port=5000)

