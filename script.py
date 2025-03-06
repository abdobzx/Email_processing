from flask import Flask, request, jsonify
from crewai import Agent, Task, Crew
import ollama
import sqlite3
import yaml
import re
app = Flask(__name__)

# Load agent configuration from config.yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Initialize CrewAI agent
agent = Agent(
    name=config["agent"]["name"],
    role=config["agent"]["role"],
    goal=config["agent"]["goal"],
    backstory=config["agent"]["backstory"],
    verbose=config["agent"].get("verbose", True),
    allow_delegation=config["agent"].get("allow_delegation", False)
)

# Create database if it does not exist
def init_db():
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        subject TEXT,
        category TEXT,
        content TEXT
    )
    """)
    conn.commit()
    conn.close()

@app.route("/process_email", methods=["POST"])
def process_email():
    data = request.json
    sender = data.get("sender", "Unknown Sender")
    subject = data.get("subject", "No Subject")
    email_content = data.get("body")
    
    if not email_content:
        return jsonify({"error": "No content provided"}), 400
    
    # Ask Ollama to analyze the email with explicit instructions
    instructions = config["agent"]["instructions"]

    response = ollama.chat("llama3", [
        {"role": "user", "content": f"{instructions}\n\nEmail: {email_content}"}
    ])
    print(response)  # Debug pour voir la structure de la réponse

    category_text = response.get("message", {}).get("content", "Unknown")

    # Extraire la catégorie précise si elle est présente
    match = re.search(r"(Finance|Human Resources|Marketing|Sales|Operations|Customer Service|Information Technology)", category_text, re.IGNORECASE)
    category = match.group(0) if match else "Unknown"

    
    # Print categorization result to console
    if category.lower() not in ["unknown", "uncategorized"]:
        print(f"Email from {sender} categorized as: {category}")
        conn = sqlite3.connect("emails.db")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO emails (sender, subject, category, content) VALUES (?, ?, ?, ?)",
                (sender, subject, category, email_content)
            )
            conn.commit()
            print("Email details saved.")
        except Exception as e:
            print("Error saving email details:", e)
        finally:
            conn.close()
    else:
        print(f"Email from {sender} could not be categorized.")
    
    return jsonify({"category": category, "status": "Processed"})

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)