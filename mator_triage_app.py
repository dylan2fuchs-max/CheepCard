import os
import time
import pandas as pd
import shutil
import tempfile
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
FILE_PATH = "Tools/Mator_Removal_Ranking_Triage.xlsx"

app_cache = {
    "df": None,
    "start_time": None,
    "completed_count": 0
}

def save_to_disk():
    df = app_cache["df"]
    if df is not None:
        directory = os.path.dirname(FILE_PATH)
        os.makedirs(directory, exist_ok=True)
        
        # 1. Automatically keep a rotating backup before overwriting
        bak_path = FILE_PATH + ".bak"
        if os.path.exists(FILE_PATH):
            try:
                shutil.copy(FILE_PATH, bak_path)
            except Exception:
                pass

        # 2. Write to a temporary file first in the same directory (Atomic Write)
        with tempfile.NamedTemporaryFile('w', dir=directory, delete=False, suffix='.xlsx') as tmp:
            temp_path = tmp.name

        try:
            df.to_excel(temp_path, index=False, engine="openpyxl")
            # 3. Atomically replace the target file
            os.replace(temp_path, FILE_PATH)
            print(f"💾 INSTANT AUTO-SAFE-SAVE: Progress written to {FILE_PATH}!")
        except Exception as e:
            print(f"❌ Error during save: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

def load_and_clean_df():
    if not os.path.exists(FILE_PATH):
        return None
    
    df = pd.read_excel(FILE_PATH, engine="openpyxl")
    
    if 'Status' not in df.columns:
        df['Status'] = ""
    
    col_map = {c.strip().lower(): c for c in df.columns}
    class_col = col_map.get('assigned class', 'Assigned Class')
    rank_col = col_map.get('assigned rank') or col_map.get('assigned') or 'Assigned'

    if class_col not in df.columns:
        df[class_col] = ""
    if rank_col not in df.columns:
        df[rank_col] = ""

    for col in [class_col, rank_col, 'Status']:
        if col in df.columns:
            df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', '<NA>'], '')

    print(f"📂 Loaded database from {FILE_PATH} successfully.")
    return df

def get_cached_df():
    if app_cache["df"] is None:
        df = load_and_clean_df()
        if df is not None:
            app_cache["df"] = df
            app_cache["start_time"] = time.time()
            app_cache["completed_count"] = 0
    return app_cache["df"]

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Lightning Triage Sorter</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; text-align: center; padding: 20px; }
        .card-container { display: flex; flex-direction: column; align-items: center; justify-content: center; }
        img { max-width: 280px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); margin-bottom: 10px; }
        .info-box { background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 15px; max-width: 550px; text-align: left; font-size: 14px; }
        .stats-box { background: #2c3e50; padding: 10px; border-radius: 6px; margin-bottom: 15px; max-width: 550px; font-size: 13px; color: #ecf0f1; display: flex; justify-content: space-around; }
        .controls { display: flex; flex-direction: column; gap: 10px; align-items: center; }
        .button-group { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
        button { padding: 9px 14px; font-size: 13px; cursor: pointer; color: white; border: none; border-radius: 5px; font-weight: bold; outline: none; }
        .btn-class { background: #e67e22; }
        .btn-rank { background: #3498db; }
        .btn-na { background: #7f8c8d; }
        .btn-flip { background: #8e44ad; margin-bottom: 10px; display: none; }
        .btn-save { background: #2ecc71; padding: 12px 24px; font-size: 15px; margin-top: 10px; }
        .btn-skip { background: #95a5a6; }
        h3 { margin: 5px 0; color: #1db954; }
    </style>
    <script>
        let currentSelection = { class: 'N/A', rank: 'N/A' };
        let currentCardCleanName = "";
        let isShowingBack = false;
        let cardHasBack = false;

        function selectClass(val, btn) {
            currentSelection.class = val;
            if (val === 'N/A') {
                currentSelection.rank = 'N/A';
            }
            highlightSelections();
            if (btn) btn.blur();
        }

        function selectRank(val, btn) {
            currentSelection.rank = val;
            highlightSelections();
            if (btn) btn.blur();
        }

        function highlightSelections() {
            document.querySelectorAll('.btn-class').forEach(b => b.style.border = "none");
            document.querySelectorAll('.btn-rank').forEach(b => b.style.border = "none");
            
            if (currentSelection.class) {
                let btn = document.getElementById("class_" + currentSelection.class);
                if (btn) btn.style.border = "3px solid #f1c40f";
            }
            if (currentSelection.rank) {
                let btn = document.getElementById("rank_" + currentSelection.rank);
                if (btn) btn.style.border = "3px solid #f1c40f";
            }
        }

        function toggleFlip() {
            if (!cardHasBack) return;
            isShowingBack = !isShowingBack;
            let imgElement = document.getElementById('card_image');
            let flipBtn = document.getElementById('flip_button');
            
            if (isShowingBack) {
                imgElement.src = "https://api.scryfall.com/cards/named?exact=" + encodeURIComponent(currentCardCleanName) + "&format=image&face=back";
                flipBtn.innerText = "🔄 Show Front Face";
                flipBtn.style.background = "#d35400";
            } else {
                imgElement.src = "https://api.scryfall.com/cards/named?exact=" + encodeURIComponent(currentCardCleanName) + "&format=image";
                flipBtn.innerText = "🔄 Flip Card (View Back Face)";
                flipBtn.style.background = "#8e44ad";
            }
        }

        function submitCard(actionType, btn) {
            if (btn) btn.blur();
            let payload = { action: actionType };
            if (actionType === 'submit_card') {
                payload.assigned_class = currentSelection.class || 'N/A';
                payload.assigned_rank = currentSelection.rank || 'N/A';
            }

            fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.finished) {
                    document.body.innerHTML = "<h2 style='color: #2ecc71; text-align:center; margin-top: 50px;'>🎉 All cards reviewed and safely saved!</h2>";
                    return;
                }
                document.getElementById('card_name_heading').innerText = "Mator Triage Review: " + data.card.name;
                document.getElementById('remaining_span').innerText = data.remaining;
                document.getElementById('completed_span').innerText = data.completed;
                document.getElementById('time_left_span').innerText = data.time_left;
                
                document.getElementById('mana_cost').innerText = data.card.mana_cost;
                document.getElementById('card_type').innerText = data.card.card_type;
                document.getElementById('assigned_class_display').innerText = data.card.assigned_class;
                document.getElementById('assigned_rank_display').innerText = data.card.assigned_rank;
                document.getElementById('oracle_text').innerText = data.card.oracle_text;

                currentCardCleanName = data.card.clean_name;
                cardHasBack = data.card.has_back;
                isShowingBack = false;

                let imgElement = document.getElementById('card_image');
                imgElement.src = "https://api.scryfall.com/cards/named?exact=" + encodeURIComponent(currentCardCleanName) + "&format=image";

                let flipBtn = document.getElementById('flip_button');
                if (cardHasBack) {
                    flipBtn.style.display = "inline-block";
                    flipBtn.innerText = "🔄 Flip Card (View Back Face)";
                    flipBtn.style.background = "#8e44ad";
                } else {
                    flipBtn.style.display = "none";
                }

                currentSelection = { class: 'N/A', rank: 'N/A' };
                highlightSelections();
            });
        }

        document.addEventListener("keydown", function(event) {
            if (event.key === "z") {
                event.preventDefault();
                submitCard('submit_card');
            }
        });
    </script>
</head>
<body onload="submitCard('fetch_initial')">
    <h2 id="card_name_heading">Mator Triage Review: Loading...</h2>
    
    <div class="stats-box">
        <span><b>Remaining:</b> <span id="remaining_span">-</span></span>
        <span><b>Completed (Session):</b> <span id="completed_span">0</span></span>
        <span><b>Est. Time Left:</b> <span id="time_left_span">Calculating...</span></span>
    </div>

    <div class="info-box">
        <p><b>Mana Cost:</b> <span id="mana_cost">-</span> | <b>Type:</b> <span id="card_type">-</span></p>
        <p><b>Current Assigned:</b> Class: <span id="assigned_class_display" style="color: #f1c40f;">-</span> | Rank: <span id="assigned_rank_display" style="color: #3498db;">-</span></p>
        <p><b>Oracle Text:</b> <i id="oracle_text">-</i></p>
    </div>
    
    <div class="card-container">
        <button id="flip_button" class="btn-flip" onclick="toggleFlip()">🔄 Flip Card (View Back Face)</button>
        <img id="card_image" src="" alt="Card Image">
        
        <div class="controls">
            <div>
                <p style="margin: 4px; font-size: 12px; color: #aaa;">Select Class:</p>
                <div class="button-group">
                    <button onclick="selectClass('Draw', this)" id="class_Draw" class="btn-class">Draw</button>
                    <button onclick="selectClass('Removal', this)" id="class_Removal" class="btn-class">Removal</button>
                    <button onclick="selectClass('Board Wipe', this)" id="class_Board Wipe" class="btn-class">Board Wipe</button>
                    <button onclick="selectClass('Land', this)" id="class_Land" class="btn-class">Land</button>
                    <button onclick="selectClass('Ramp', this)" id="class_Ramp" class="btn-class">Ramp</button>
                    <button onclick="selectClass('N/A', this)" id="class_N/A" class="btn-na">N/A</button>
                </div>
            </div>

            <div>
                <p style="margin: 4px; font-size: 12px; color: #aaa;">Select Rank:</p>
                <div class="button-group">
                    <button onclick="selectRank('Optimized', this)" id="rank_Optimized" class="btn-rank">Optimized</button>
                    <button onclick="selectRank('Fast', this)" id="rank_Fast" class="btn-rank">Fast</button>
                    <button onclick="selectRank('Average', this)" id="rank_Average" class="btn-rank">Average</button>
                    <button onclick="selectRank('Passive', this)" id="rank_Passive" class="btn-rank">Passive</button>
                    <button onclick="selectRank('Low', this)" id="rank_Low" class="btn-rank">Low</button>
                    <button onclick="selectRank('N/A', this)" id="rank_N/A" class="btn-na">N/A Rank</button>
                </div>
            </div>

            <div class="button-group" style="margin-top: 5px;">
                <button onclick="submitCard('skip', this)" class="btn-skip">Skip</button>
                <button onclick="submitCard('submit_card', this)" class="btn-class" style="background: #27ae60;">Submit Card (Enter)</button>
            </div>
            
            <div>
                <button onclick="submitCard('save_progress', this)" class="btn-save">💾 Save Progress to Excel</button>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def triage_home():
    return render_template_string(TEMPLATE)

@app.route('/process', methods=['POST'])
def process_card():
    df = get_cached_df()
    if df is None:
        return jsonify({"finished": True})

    col_map = {c.strip().lower(): c for c in df.columns}
    name_col = col_map.get('card name', 'Card Name')
    text_col = col_map.get('oracle text', 'Oracle Text')
    class_col = col_map.get('assigned class', 'Assigned Class')
    rank_col = col_map.get('assigned rank') or col_map.get('assigned') or 'Assigned'
    mana_col = col_map.get('mana cost', 'Mana Cost')
    type_col = col_map.get('card type', 'Card Type')

    data = request.get_json() or {}
    action = data.get('action')

    unreviewed = df[df['Status'].astype(str).str.lower() != 'reviewed']

    if not unreviewed.empty and action == "submit_card":
        idx = unreviewed.index[0]
        df.at[idx, class_col] = data.get('assigned_class', 'N/A')
        df.at[idx, rank_col] = data.get('assigned_rank', 'N/A')
        df.at[idx, 'Status'] = 'Reviewed'
        app_cache["completed_count"] += 1
        
        # 🔒 INSTANT DISK WRITE: Saved immediately on every single submission
        save_to_disk()

    if action == "save_progress":
        save_to_disk()

    unreviewed = df[df['Status'].astype(str).str.lower() != 'reviewed']
    if unreviewed.empty:
        save_to_disk()
        return jsonify({"finished": True})

    rem_count = len(unreviewed)
    comp_count = app_cache["completed_count"]
    elapsed = time.time() - app_cache["start_time"] if app_cache["start_time"] else 0
    
    if comp_count > 0 and elapsed > 0:
        sec_per_card = elapsed / comp_count
        total_sec_left = int(sec_per_card * rem_count)
        
        hours, rem_secs = divmod(total_sec_left, 3600)
        mins, secs = divmod(rem_secs, 60)
        
        if hours > 0:
            time_left_str = f"{hours}h {mins}m {secs}s"
        elif mins > 0:
            time_left_str = f"{mins}m {secs}s"
        else:
            time_left_str = f"{secs}s"
    else:
        time_left_str = "Calculating..."

    idx = unreviewed.index[0]
    row = df.loc[idx]
    
    raw_name = str(row.get(name_col, 'Unknown'))
    clean_name = raw_name.split('//')[0].strip()
    has_back = True if '//' in raw_name else False

    card_data = {
        "name": raw_name,
        "clean_name": clean_name,
        "has_back": has_back,
        "mana_cost": str(row.get(mana_col, '')),
        "card_type": str(row.get(type_col, '')),
        "assigned_class": str(row.get(class_col, 'N/A')),
        "assigned_rank": str(row.get(rank_col, 'N/A')),
        "oracle_text": str(row.get(text_col, 'No oracle text found.'))
    }

    return jsonify({
        "finished": False,
        "card": card_data,
        "remaining": rem_count,
        "completed": comp_count,
        "time_left": time_left_str
    })

if __name__ == '__main__':
    print(f"🚀 Starting Lightning Triage Sorter targeting {FILE_PATH} at http://127.0.0.1:5002")
    app.run(port=5002, debug=True)