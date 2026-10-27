from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import os
import json
from datetime import datetime
import requests
from config import Config
import google.generativeai as genai
import model 
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

GEMINI_API_KEY = Config.GEMINI_API_KEY
HF_API_KEY = Config.HF_API_KEY

GEMINI_MODEL = "gemini-2.5-flash"
HF_MODEL = "tiiuae/falcon-7b-instruct"

HISTORY_FILE = "history.json"

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are an AI assistant similar to ChatGPT.
Respond in clean Markdown with:
- Headings
- Bullet points
- Code blocks (```language)
- Tables
- Emojis when helpful

Tone: friendly, helpful, structured.
"""

POWERFUL_PROMPT = """ You are an expert Prompt Engineer and AI Optimizer.

Your task is to transform the user’s raw prompt into a clear, detailed, and powerful prompt that fully utilizes the intelligence, reasoning, creativity, and accuracy of the AI model.

Rules:
- Understand the user’s true intent, even if the prompt is vague or poorly written.
- Add missing context, constraints, and clarity.
- Define the AI’s role clearly (expert, teacher, developer, analyst, etc.).
- Specify the desired tone, depth, and output format.
- Encourage step-by-step reasoning where useful.
- Optimize the prompt so it works effectively across advanced AI models.

Do NOT answer the prompt.
Only rewrite it as a powerful, optimized prompt.

Formatting Rules (STRICT):
- DO NOT use Markdown syntax (*, **, -, ##).
- Output must be clean HTML only.
- Use <h1>, <h2>, <h3> for headings.
- Use <p> for paragraphs.
- Use <ul><li> for lists.
- No code fences or markdown symbols.

Return only the optimized powerful prompt.

Raw User Prompt: 
" 
"""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def call_gemini(message):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{SYSTEM_PROMPT}\nUser: {message}\nAssistant:")
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"
    
def call_gemini_for_powerful_prompt(raw_prompt):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(f"{POWERFUL_PROMPT}\n User:{raw_prompt}")
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"
    
def call_huggingface(message):
    try:
        url = "https://router.huggingface.co/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-ai/DeepSeek-R1",   # model with provider support
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]
        }

        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()

        # standard OpenAI‑like output
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"HuggingFace Error: {e}"
    

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user_logged_in'):
        return redirect(url_for('index'))

    if request.method == "GET":
        return render_template("login.html")
    
    if request.method == "POST":
        data = request.form
        user = model.user_model()
        response, status = user.user_login(data)

        if status == 200:
            user_data = response.get_json()['user']
            session['user_logged_in'] = True
            session['user_id'] = user_data['id']
            session['email'] = user_data['email']
            session['username'] = user_data['username']

            return redirect(url_for('index'))
        return response, status
    
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    
    if request.method == "POST":
        data = request.form
        user= model.user_model()
        response = user.user_signup(data)
        return response
    
@app.route("/logout")
@login_required
def logout():
    session.clear() 
    return redirect(url_for("login"))

@app.route("/compare_chat", methods=["POST"])
@login_required
def compare_chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({"error": "Message required"}), 400

    gemini_reply = call_gemini(message)
    hf_reply = call_huggingface(message)

    history = load_history()

    # create conversation if not exists
    conv = next((c for c in history if c["id"] == conversation_id), None)
    if not conv:
        conv = {
            "id": conversation_id or datetime.now().strftime("%Y%m%d%H%M%S"),
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        history.append(conv)

    conv["messages"].append({
        "role": "user",
        "content": message,
        "time": datetime.now().isoformat()
    })

    conv["messages"].append({
        "role": "assistant",
        "bot": "gemini",
        "content": gemini_reply,
        "time": datetime.now().isoformat()
    })

    conv["messages"].append({
        "role": "assistant",
        "bot": "huggingface",
        "content": hf_reply,
        "time": datetime.now().isoformat()
    })

    save_history(history)

    return jsonify({
        "conversation_id": conv["id"],
        "replies": {
            "left": gemini_reply,
            "right": hf_reply
        }
    })

@app.route("/history_api", methods=["GET", "POST"])
@login_required
def history_api():
    history = load_history()

    if request.method == "GET":
        return jsonify({
            "conversations": [
                {
                    "id": c["id"],
                    "created_at": c["created_at"],
                    "message_count": len(c["messages"])
                }
                for c in history
            ]
        })

    data = request.get_json()
    if data.get("action") == "clear":
        save_history([])
        return jsonify({"success": True})

    return jsonify({"error": "Invalid action"}), 400

@app.route("/raw_to_powerful", methods=["GET", "POST"])
@login_required
def raw_to_powerful():
    raw_prompt = request.form.get("raw_prompt")

    if not raw_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    result = call_gemini_for_powerful_prompt(raw_prompt)

    return jsonify({"result": result})



if __name__ == "__main__":
    app.run(debug=True, port=5000)
