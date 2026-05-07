from flask import Flask, request, send_file, jsonify, session, redirect, url_for
import sqlite3
import os
import requests
import json
from datetime import datetime
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus import HRFlowable
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Frame, PageTemplate
from reportlab.platypus import BaseDocTemplate
from reportlab.pdfgen import canvas
from summarizer import generate_summary
from analyzer import extract_keywords, calculate_research_trends,calculate_research_gaps
from flask import jsonify

app = Flask(__name__)
app.secret_key = "raisa_ultra_secret_key"
base_dir = os.path.dirname(os.path.abspath(__file__))  
data_dir = os.path.join(base_dir, "data")
os.makedirs(data_dir, exist_ok=True)
def get_db_connection():
    db_path = os.path.join(data_dir, 'raisa.db')
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE saved_papers ADD COLUMN abstract TEXT")
    except sqlite3.OperationalError:
        pass
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            year INTEGER,
            citations INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pw))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            return "<h3 style='color:white;'>Username already taken! <a href='/signup'>Try again</a></h3>"
            
    return """
    <body style="background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364); height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Poppins', sans-serif; color: white; margin:0;">
        <form method="POST" style="background: rgba(255,255,255,0.1); padding: 50px; border-radius: 20px; backdrop-filter: blur(10px); text-align: center; width: 350px; border: 1px solid rgba(255,255,255,0.2);">
            <h2 style="margin-bottom: 20px;">Join RAISA</h2>
            <input type="text" name="username" placeholder="Choose Username" required style="width:100%; padding:12px; margin-bottom:15px; border-radius:8px; border:none; outline:none;"><br>
            <input type="password" name="password" placeholder="Create Password" required style="width:100%; padding:12px; margin-bottom:15px; border-radius:8px; border:none; outline:none;"><br>
            <button type="submit" style="width:100%; padding:12px; background: linear-gradient(45deg, #00c6ff, #0072ff); color: white; border:none; border-radius:8px; cursor:pointer; font-weight:bold; transition: 0.3s;">Create Account</button>
            <p style="margin-top:15px; font-size:12px; opacity: 0.8;">Already have an account? <a href="/login" style="color:#00c6ff; text-decoration: none;">Login here</a></p>
        </form>
    </body>
    """

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pw = request.form["password"]
        conn = get_db_connection()
        saved = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (user, pw)).fetchone()
        conn.close()
        
        if saved:
            session["user_id"] = saved["id"]
            session["username"] = saved["username"]
            return redirect(url_for('home'))
        return "<h3 style='color:white;'>Invalid Credentials. <a href='/login' style='color:#00c6ff;'>Try again</a></h3>"
    
    return """
<body style="background: radial-gradient(circle at top right, #2c5364, #203a43, #0f2027); height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Poppins', sans-serif; color: white; margin:0;">
    <div style="background: rgba(255, 255, 255, 0.05); padding: 60px; border-radius: 24px; backdrop-filter: blur(20px); text-align: center; width: 400px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 25px 50px rgba(0,0,0,0.3); animation: float 6s ease-in-out infinite;">
        <h1 style="margin-bottom: 10px; font-weight: 700; letter-spacing: 2px;">🤖 RAISA</h1>
        <p style="opacity: 0.7; font-size: 14px; margin-bottom: 30px;">Research Intelligence Portal</p>
        
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required style="width:100%; padding:14px; margin-bottom:20px; border-radius:12px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.1); color: white; outline: none;">
            <input type="password" name="password" placeholder="Password" required style="width:100%; padding:14px; margin-bottom:25px; border-radius:12px; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.1); color: white; outline: none;">
            <button type="submit" style="width:100%; padding:14px; background: linear-gradient(45deg, #00d2ff, #3a7bd5); color: white; border:none; border-radius:12px; cursor:pointer; font-weight:bold; font-size: 16px; box-shadow: 0 10px 20px rgba(58, 123, 213, 0.3);">Login to System</button>
        </form>
        
        <p style="margin-top:25px; font-size:13px; opacity: 0.6;">First time here? <a href="/signup" style="color:#00d2ff; text-decoration: none; font-weight: 500;">Create an account</a></p>
    </div>

    <style>
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-15px); }
            100% { transform: translateY(0px); }
        }
    </style>
</body>
"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for('login'))
    
    # Notice the double {{ }} for CSS in f-strings!
    return f"""
    <html>
    <head>
        <title>RAISA - Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }}
            body {{ height: 100vh; background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #4e54c8); background-size: 400% 400%; animation: gradientBG 12s ease infinite; display: flex; justify-content: center; align-items: center; color: white; }}
            @keyframes gradientBG {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
            .container {{ background: rgba(255,255,255,0.1); padding: 50px; border-radius: 20px; backdrop-filter: blur(15px); text-align: center; width: 50%; box-shadow: 0 15px 40px rgba(0,0,0,0.4); }}
            input {{ width: 70%; padding: 15px; border-radius: 10px; border: none; font-size: 16px; outline: none; margin-bottom: 20px; }}
            button {{ padding: 15px 30px; border: none; border-radius: 10px; background: linear-gradient(45deg, #00c6ff, #0072ff); color: white; font-weight: bold; cursor: pointer; transition: 0.3s; margin: 5px; }}
            button:hover {{ transform: scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }}
        </style>
    </head>
    <body>
        <div class="container">
            <p style="text-align: right; font-size: 12px; opacity: 0.7;">Logged in as: <b>{session['username']}</b> | <a href="/logout" style="color: #ff4b2b; text-decoration: none;">Logout</a></p>
            <h1>🤖 RAISA</h1>
            <h3>Research Assistant Intelligent Software Agent</h3>
            <form method="POST" action="/search">
                <input type="text" name="topic" placeholder="Enter research topic..." required><br>
                <button type="submit">Search Research Papers</button>
            </form>
            <div style="margin-top: 20px;">
                <a href="/history"><button type="button" style="background: rgba(255,255,255,0.2);">📜 History</button></a>
                <a href="/library"><button type="button" style="background: linear-gradient(45deg, #6a11cb, #2575fc);">📚 My Library</button></a>
            </div>
        </div>
    </body>
    </html>
    """   

@app.route("/search", methods=["POST"])
def search():
    if "user_id" not in session:
        return redirect(url_for('login'))
    topic = request.form["topic"]
    sort_option = request.form.get("sort", "citations")
    results_list = []
    gap_data = None
    results_html = """
    <html>
    <head>
        <title>RAISA Results</title>
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap" rel="stylesheet">
        <style>
    body {
       background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
       font-family: 'Poppins', sans-serif;
       padding: 50px;
    }

    /* Research Insight Box */
    .insight-box {
      background: #ffffff;
      padding: 25px;
      border-radius: 15px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.08);
      margin-bottom: 40px;
    }

    /* Paper Card */
    .paper {
     padding: 25px;
     border-radius: 15px;
     margin-bottom: 30px;
     box-shadow: 0 6px 18px rgba(0,0,0,0.08);
     border: 1px solid rgba(0,0,0,0.05);
     transition: all 0.3s ease;
    }

    /* Hover effect */
    .paper:hover {
     transform: translateY(-5px);
     box-shadow: 0 15px 30px rgba(0,0,0,0.15);
    }

    /* Alternating background */
    .paper:nth-child(even) {
     background: #ffffff;
    }

   .paper:nth-child(odd) {
     background: #f9fbff;
    }

   /* Paper badge */
    .badge {
      display: inline-block;
      background: linear-gradient(45deg, #4e73df, #1cc88a);
      color: white;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 12px;
      margin-bottom: 10px;
    }

   /* Subtle separator */
    .separator {
      height: 1px;
      background: rgba(0,0,0,0.08);
      margin: 30px 0;
    }
</style>
    </head>
    <body>
    """


    url = f"https://api.openalex.org/works?search={topic}&per-page=10&sort=cited_by_count:desc"
    response = requests.get(url)
    data = response.json()

    if not data["results"]:
        return "<h2>No research papers found for this topic.</h2><a href='/'>Back</a>"


    # ------------------ EXTRACT DATA ------------------
    current_year = datetime.now().year
    temp_list = []
    for work in data["results"]:

        title = work.get("title", "No Title")
        year = work.get("publication_year", "N/A")
        citations = work.get("cited_by_count", 0)
        source_url = work.get("id", "")
        abstract = work.get("abstract_inverted_index")

        if abstract:
            words = []
            for word, positions in abstract.items():
                for pos in positions:
                    words.append((pos, word))
            words = sorted(words)
            abstract_text = " ".join([word for pos, word in words])
            extracted_kws = extract_keywords(abstract_text)
            
        else:
            abstract_text = "No abstract available."
            extracted_kws = ["N/A"]

        temp_list.append({
            "title": work.get("title", "No Title"),
            "year": work.get("publication_year", "N/A"),
            "abstract": abstract_text,
            "citations": work.get("cited_by_count", 0),
            "source": work.get("id", ""),
            "summary": "Click 'Analyze' to generate...",
            "keywords": extracted_kws, 
        })
    results_list = [
        p for p in temp_list   
        if p["year"] != "N/A" and isinstance(p["year"], int) and p["year"] <= current_year
    ]

    
    # ------------------ SORTING ------------------
    if sort_option == "year":
        results_list = sorted(results_list, key=lambda x: x["year"], reverse=True)
    else:
        results_list = sorted(results_list, key=lambda x: x["citations"], reverse=True)
    
    research_trends = calculate_research_trends(results_list)
    gap_data = calculate_research_gaps(results_list,topic)
    print("DEBUG GAP DATA:", gap_data)

    if gap_data and isinstance(gap_data, dict):
     gap_display = gap_data.get('title', "Analyzing trends...")
    else:
     gap_display = "No specific gaps identified yet."

    # ------------------ INSIGHTS ------------------
    total_papers = len(results_list)
    most_cited = max(results_list, key=lambda x: x["citations"])
    latest_year = max(p["year"] for p in results_list)

    sorted_years = dict(sorted(research_trends.get('yearly_counts', {}).items()))

    # ------------------ BUILD HTML ------------------
    results_html = """
    <html>
    <head>
     <title>RAISA Results</title>

<style>
body {
    background: #f4f7fb;
    padding: 50px;
    font-family: 'Poppins', sans-serif;
}

/* Paper Card */
.paper {
    position: relative;
    padding: 25px;
    border-radius: 12px;
    margin-bottom: 30px;
    border: 1px solid #e0e6ed;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
}

/* Alternating Background */
.paper:nth-child(even) {
    background: #ffffff;
}

.paper:nth-child(odd) {
    background: #f0f6ff;
}

/* Hover Animation */
.paper:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

/* Gradient Badge */
.badge {
    position: absolute;
    top: -12px;
    left: -12px;
    padding: 6px 14px;
    border-radius: 30px;
    font-size: 12px;
    font-weight: bold;
    color: white;
    background: linear-gradient(45deg, #00c6ff, #0072ff);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.year-box:hover {
    background: #00c6ff !important;
    color: white !important;
    transform: scale(1.1);
    transition: 0.3s;
}

/* Separator */
.separator {
    height: 1px;
    background: linear-gradient(to right, transparent, #ccd6dd, transparent);
    margin: 40px 0;
}

h3 {
    margin-top: 15px;
}
</style>

</head>
<body>
"""
    
# Update this line:
    gap_display = gap_data.get('title', "Analyzing papers...") if gap_data else "No specific gaps identified yet."    
    results_html += """<div class="results-container"><html><head><title>RAISA Results</title></head><body style="position: relative;"> <div style="position: absolute; top: 20px; right: 40px; z-index: 1000;">
        <a href="/logout" style="
            text-decoration: none; 
            color: #ff4b2b; 
            font-size: 13px; 
            font-weight: bold; 
            border: 2px solid #ff4b2b; 
            padding: 8px 16px; 
            border-radius: 25px;
            background: white;
            transition: 0.3s;
        " onmouseover="this.style.background='#ff4b2b'; this.style.color='white';" 
           onmouseout="this.style.background='white'; this.style.color='#ff4b2b';">
            🚪 Logout
        </a>
     </div>"""
    results_html += f"<h2>Results for: {topic}</h2>"
    results_html += "<a href='/'>⬅ Back to Search</a><br><br>"
    
    results_html += f"""
    <div class="insight-box" style="padding: 20px; background: #f8f9fa; border-radius: 12px; margin-bottom: 30px; border: 1px solid #dee2e6;">
    <h3 style="color: #1f3c88; margin-bottom: 15px;">Research Intelligence Dashboard</h3>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
      <div>
         <p><b>Total Papers Found:</b> {total_papers}</p>
         <p><b>Peak Research Year:</b> {research_trends.get('peak_year', 'N/A')}</p>
       </div>
       <div>
         <p><b>Most Cited Paper:</b> {most_cited['title']} ({most_cited['citations']} citations)</p>
         <p><b>Latest Publication Year:</b> {latest_year}</p>
       </div>
    </div>
    <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 0;">
    <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 5px solid #ffc107;">
        <p style="margin: 0; font-weight: bold; color: #856404;">🔍 Research Gap Insight:</p>
        <p style="margin: 5px 0 0 0; font-size: 14px;">{gap_display}</p>
   </div>
    <h4 style="color: #333; margin-bottom: 15px;">📅 Publication Timeline</h4>
    <div style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 12px; align-items: center;">
    """

    for year, count in sorted_years.items():
        results_html += f"""
        <div style="background: #f1f3f9; padding: 10px 15px; border-radius: 8px; text-align: center; border: 1px solid #dce2f0; min-width: 70px;">
            <div style="font-size: 11px; color: #718096; font-weight: bold; text-transform: uppercase;">{year}</div>
            <div style="font-size: 18px; color: #2d3748; font-weight: 800;">{count}</div>
        </div>
    """
    
    results_html += """
    </div>
</div>
"""
    results_html += """
    </div>
    <form method="POST" action="/search" style="margin-bottom:30px;">
    <input type="hidden" name="topic" value="{topic}">
    
    <label><b>Sort by:</b></label>
    <select name="sort" onchange="this.form.submit()" 
        style="padding:6px 10px;border-radius:6px;margin-left:10px;">
        
        <option value="citations" {"selected" if sort_option=="citations" else ""}>
            Citations
        </option>
        <option value="year" {"selected" if sort_option=="year" else ""}>
            Year
        </option>
    </select>
</form>
"""
    # 1. THE LOOP (Only for the cards)
    for index, paper in enumerate(results_list, start=1):
        safe_abstract = paper['abstract'].replace('`', '\\`').replace('"', '&quot;')
        escaped_title = paper['title'].replace("'", "\\'")
        trend = paper.get('trend_status', '✅ Stable')
        abstract_for_js = paper['abstract'].replace("'", "\\'").replace("\n", " ")
        escaped_title = paper['title'].replace("'", "\\'")
        results_html += f"""
        <div class="paper">
           <div class="badge">Paper {index} | {trend}</div>

           <h3>{paper['title']}</h3>
           <p><b>Year:</b> {paper['year']} | <b>Citations:</b> {paper['citations']}</p>
           
           <p><b>Source:</b> <a href="{paper['source']}" target="_blank">{paper['source']}</a></p>

           <div class="abstract-section" style="margin-top: 15px; font-size: 13.5px; color: #555;">
               <p><b>Original Abstract:</b> {paper['abstract'][:500]}...</p>
           </div>

           <div class="ai-box" style="display:none; margin:15px 0; padding:15px; background:#eef6ff; border-radius:8px; border-left:4px solid #4e54c8;">
             <p class="summary-text"><i>Thinking...</i></p>
             <div class="keyword-tags" style="margin-top:10px;"></div>
           </div>

           <div style="display: flex; gap: 12px; margin-top: 20px; align-items: center;">
           <button onclick="triggerAI(...)">✨ RAISA AI Insight</button>
           <button onclick="saveToLibrary(...)">⭐ Save to Library</button>
           </div>
        <div class="separator"></div>
    </div>
    """

    # 2. THE JAVASCRIPT (Add this ONCE after the loop finishes)
    results_html += """
    <script>
     async function triggerAI(button, text) {
      const parent = button.parentElement;
      const aiBox = parent.querySelector('.ai-box');

      // Show the box and disable button
      aiBox.style.display = "block";
      button.disabled = true;
      button.innerText = "🤖 Analyzing...";

      try {
        const response = await fetch('/ai_analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: text })
        });
        
        const data = await response.json();

        // Update UI with results
        aiBox.querySelector('.summary-text').innerHTML = "<b>AI Summary:</b> " + data.summary;
        
        // Map keywords to styled spans
        aiBox.querySelector('.keyword-tags').innerHTML = data.keywords.map(kw => 
            `<span style="background:#fff; color:#4e54c8; padding:3px 10px; border-radius:15px; margin-right:5px; font-size:11px; border:1px solid #4e54c8; display:inline-block;">#${kw}</span>`
        ).join('');
    
        button.style.display = "none"; 
    } catch (e) {
        aiBox.querySelector('.summary-text').innerText = "Error generating analysis. Please try again.";
        button.disabled = false;
        button.innerText = "Retry Analysis";
    }
    }
    async function saveToLibrary(btn, title, url, year, citations, abstract) {
    btn.innerText = "⏳ Saving...";
    btn.disabled = true; // Prevent double clicks
    
    try {
        const response = await fetch('/save_paper', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, url, year, citations, abstract})
        });
        const res = await response.json();
        if(res.status === 'success') {
            btn.innerText = "✅ Saved to Library";
            btn.style.background = "#eefaf5";
            btn.style.color = "#13855c";
        } else {
            alert("Error: " + res.message);
            btn.innerText = "⭐ Save to Library";
            btn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        btn.innerText = "❌ Failed";
        btn.disabled = false;
    }
}
    </script>
    """
    
    if gap_data:
        results_html += f"""
     <div class="insight-box" style="border-radius: 15px; border: 1px solid #ffeeba; background: #fffdf5; padding: 25px; margin-bottom: 40px;">
        <h3>{gap_data['title']}</h3>
        <h3 style="color: #856404; display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 24px;">💡</span> RAISA Strategic Research Gap
        </h3>
        
        <div style="margin-top: 15px;">
            <p style="font-size: 18px; font-weight: bold; color: #333;">{gap_data['title']}</p>
            
            <p style="margin-top: 10px; color: #555; line-height: 1.6;">
                <b>The Problem:</b> {gap_data['limitation']}
            </p>
            <p style="margin-top: 15px; color: #2c3e50; background: #eef6ff; padding: 12px; border-radius: 8px;">
            <b>📌 Thesis Statement:</b><b>{gap_data['thesis_statement']}
            </p>
            <div style="margin-top: 20px; background: white; padding: 15px; border-radius: 10px; border: 1px dashed #ccc;">
                <p style="font-weight: bold; color: #4e54c8; margin-bottom: 10px;">🛠️ Proposed Roadmap (How to do it):</p>
                <ul style="padding-left: 20px; font-size: 14px; color: #444; line-height: 1.8;">
        """
        for step in gap_data['roadmap']:
            results_html += f"<li>{step}</li>"
        results_html += """
                </ul>
            </div>
        </div>
    </div>
    """

    # ------------------ SAVE JSON ------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(data_dir, f"results_{timestamp}.json")
    report_data = {
        "topic": topic,
        "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "papers": results_list,
        "trends": research_trends
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)

    # ------------------ SAVE HISTORY ------------------
    history_file = os.path.join(data_dir, "history.json")

    history_entry = {
        "topic": topic,
        "timestamp": timestamp
    }

    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append(history_entry)

    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)

    # ------------------ DOWNLOAD BUTTON ------------------
    results_html += f"""
    <br>
    <a href="/download/{timestamp}">
        <button style="padding:10px 20px;">Download Research PDF</button>
    </a>
    """

    results_html += "</body></html>"
    return results_html



@app.route("/ai_analyze", methods=["POST"])
def ai_analyze():
    data = request.json
    text = data.get("text", "")
    
    if not text or text == "No abstract available.":
        return jsonify({"summary": "No abstract provided.", "keywords": []})

    # Run your heavy models here (only once per click!)
    summary = generate_summary(text)
    keywords = extract_keywords(text)
    
    return jsonify({
        "summary": summary,
        "keywords": keywords
    })

@app.route("/download/<timestamp>")
def download(timestamp):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    json_file = os.path.join(data_dir, f"results_{timestamp}.json")

    with open(json_file, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    topic = report_data["topic"]
    generated_on = report_data["generated_on"]
    results = report_data["papers"]
    for paper in results:
        # Check if the summary is still the placeholder text
        if "Click 'Analyze'" in paper.get('summary', ''):
            # Run the AI models for the PDF
            paper['summary'] = generate_summary(paper['abstract'])
            paper['keywords'] = extract_keywords(paper['abstract'])

    pdf_file = os.path.join(data_dir, f"RAISA_Report_{timestamp}.pdf")

    doc = SimpleDocTemplate(
        pdf_file,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=36,
        alignment=1,
        textColor=colors.HexColor("#1f3c88"),
        spaceAfter=20
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=1,
        textColor=colors.grey
    )

    paper_title_style = ParagraphStyle(
        'PaperTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#0f3057"),
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=15
    )

    # ---------- TITLE PAGE ----------
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph("RAISA", title_style))
    elements.append(Paragraph("Research Assistant Intelligent Software Agent", subtitle_style))
    elements.append(Spacer(1, 0.3*inch))

    elements.append(Paragraph(f"<b>Research Topic:</b> {topic}", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph(f"Generated on: {generated_on}", subtitle_style))
    elements.append(PageBreak())
   
    # ---------- STRATEGIC ROADMAP PAGE (PDF) ----------
    # ---------- STRATEGIC ROADMAP PAGE ----------
    gap_data = calculate_research_gaps(results, topic)

    if gap_data:
     elements.append(Paragraph("RAISA Strategic Research Roadmap", title_style))
     elements.append(Spacer(1, 0.3*inch))

    # --- GAP TITLE ---
     elements.append(Paragraph(
        f"<b>🔍 Research Gap</b><br/>{gap_data['title']}", 
        paper_title_style
     ))
     elements.append(Spacer(1, 0.2*inch))

    # --- RATIONALE ---
     elements.append(Paragraph(
        f"<b>📖 Rationale:</b> {gap_data['limitation']}", 
        normal_style
     ))
     elements.append(Spacer(1, 0.25*inch))

    # --- THESIS ---
     elements.append(Paragraph(
        "<b>📌 Thesis Statement</b>", 
        paper_title_style
     ))
     elements.append(Spacer(1, 0.1*inch))

     elements.append(Paragraph(
        gap_data['thesis_statement'], 
        normal_style
     ))
     elements.append(Spacer(1, 0.3*inch))

    # --- ROADMAP HEADER ---
     elements.append(Paragraph(
        "<b>🛠️ Proposed Implementation Strategy</b>", 
        paper_title_style
    ))
     elements.append(Spacer(1, 0.15*inch))

    # --- BULLET POINTS ---
    for step in gap_data['roadmap']:
        elements.append(Paragraph(f"• {step}", normal_style))
        elements.append(Spacer(1, 0.1*inch))

    elements.append(Spacer(1, 0.4*inch))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1f3c88")))
    elements.append(PageBreak())

    # ---------- CONTENT ----------
    for i, paper in enumerate(results, 1):
        elements.append(Paragraph(f"Paper {i}: {paper['title']}", paper_title_style))
        elements.append(Spacer(1, 0.1*inch))

        elements.append(Paragraph(f"<b>Year:</b> {paper['year']}", normal_style))
        elements.append(Paragraph(f"<b>Citations:</b> {paper['citations']}", normal_style))
        elements.append(Spacer(1, 0.1*inch))

        elements.append(Paragraph(f"<b>Source URL:</b> {paper['source']}", normal_style))
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph(f"<b>Abstract:</b> {paper['abstract']}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

        elements.append(Paragraph(f"<b>AI Summary:</b> {paper['summary']}", normal_style))
        elements.append(Spacer(1, 0.3*inch))

        elements.append(Paragraph(f"<b>Keywords:</b> {', '.join(paper['keywords'])}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.3*inch))

    doc.build(elements)

    return send_file(pdf_file, as_attachment=True)
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for('login'))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    history_file = os.path.join(data_dir, "history.json")

    if not os.path.exists(history_file):
        return "<h2>No search history yet.</h2>"

    with open(history_file, "r") as f:
        history_data = json.load(f)

    html = "<h2>Search History</h2><a href='/'>Back</a><br><br>"

    for item in reversed(history_data):
        html += f"""
        <div>
            <b>Topic:</b> {item['topic']}<br>
            <b>Timestamp:</b> {item['timestamp']}<br>
            <a href="/download/{item['timestamp']}">Download Report</a>
            <hr>
        </div>
        """

    return html

@app.route("/save_paper", methods=["POST"])
def save_paper():
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not logged in"})
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("""
    INSERT INTO saved_papers (user_id, title, url, year, citations, abstract) 
    VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user_id"], data["title"], data["url"], data["year"], data["citations"], data.get("abstract", "")))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        conn.close()

@app.route("/library")
def library():
    if "user_id" not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    saved = conn.execute("SELECT * FROM saved_papers WHERE user_id = ?", (session["user_id"],)).fetchall()
    conn.close()

    html = "<h2>My Library</h2><a href='/'>Back</a><br><br><div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;'>"

    for paper in saved:
        abs_text = paper['abstract'] if paper['abstract'] else "No abstract saved."
        html += f"""
    <div style="background: white; padding: 25px; border-radius: 18px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #eef2f7; display: flex; flex-direction: column; height: 100%;">
        <div style="flex-grow: 1;">
            <h4 style="margin: 0 0 10px 0; color: #2d3748; line-height: 1.4; height: 3em; overflow: hidden;">{paper['title']}</h4>
            
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 11px; background: #eef2ff; color: #4e54c8; padding: 4px 10px; border-radius: 6px; font-weight: bold;">📅 {paper['year']}</span>
                <span style="font-size: 11px; background: #fff7ed; color: #c2410c; padding: 4px 10px; border-radius: 6px; font-weight: bold;">💬 {paper['citations']} Citations</span>
            </div>

            <div style="background: #f8fafc; padding: 12px; border-radius: 10px; border: 1px solid #edf2f7; margin-bottom: 15px;">
                <p style="font-size: 12px; color: #64748b; line-height: 1.6; height: 80px; overflow-y: auto; margin: 0; padding-right: 5px;">
                    <b>Abstract:</b> {abs_text}
                </p>
            </div>
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; border-top: 1px solid #f1f5f9; padding-top: 15px;">
            <a href="{paper['url']}" target="_blank" style="text-decoration: none; color: white; background: #4e54c8; padding: 8px 16px; border-radius: 8px; font-size: 11px; font-weight: bold;">View Source</a>
            <a href="/delete_paper/{paper['id']}" onclick="return confirm('Remove this paper?')" style="text-decoration: none; color: #ff4b2b; font-size: 11px; font-weight: bold; opacity: 0.7;">🗑️ Remove</a>
        </div>
    </div>
    """

    html += "</div>"
    return html


@app.route("/delete_paper/<int:paper_id>")
def delete_paper(paper_id):
    if "user_id" not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM saved_papers WHERE id = ? AND user_id = ?", (paper_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for('library'))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
