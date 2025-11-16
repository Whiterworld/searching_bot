from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import re
import textwrap

app = Flask(__name__)
CORS(app, resources={r"/ask": {"origins": "https://searchbywhiter.netlify.app/"}})

# -------------------- GOOGLE SEARCH --------------------
def search_google(query, max_results=5):
    """
    Fetch search results from Google Custom Search API and return text snippets.
    """
    API_KEY = "AIzaSyCiyONO2j5eD2wUw80R14hkJGINX5WDvt0"         # Replace with your Google API key
    CX = "e5fdbcffd54ff47d3"     # Replace with your Custom Search Engine ID
    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        "key": API_KEY,
        "cx": CX,
        "q": query,
        "num": max_results,
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return [f"⚠️ Could not reach Google API. ({e})"]

    snippets = []
    for item in data.get("items", []):
        snippet = item.get("snippet", "")
        # Remove URLs and extra whitespace
        snippet = re.sub(r"http\S+|www\S+", "", snippet)
        snippet = re.sub(r"\s+", " ", snippet).strip()
        if len(snippet.split()) >= 5:
            snippets.append(snippet)

    return snippets if snippets else ["No relevant information found."]

# -------------------- SUMMARIZER --------------------
import re
import textwrap

def summarize_to_ai_style(snippets, query, max_sentences=12):
    """
    Turn snippets into a detailed, readable AI-style summary.
    Works for any query or user request.
    
    Parameters:
        snippets: list of strings (raw text, search results, or headlines)
        query: string (user query)
        max_sentences: maximum number of sentences to include
    Returns:
        A detailed, natural-language summary
    """
    if not snippets or snippets == ["No relevant information found."]:
        return f"I couldn’t find relevant information about '{query}' right now. Try rephrasing your question."

    # Combine snippets and normalize whitespace
    text = " ".join(snippets)
    text = " ".join(text.split())

    # Remove noise: common sources, timestamps, URLs
    text = re.sub(
        r"(India Today|The Indian Express|Hindustan Times|livemint\.com|Reuters|Al Jazeera|Times of India|BBC|CNN)\s*·.*?(?=[A-Z])",
        "", text
    )
    text = re.sub(r"\d{1,2} hours ago|Yesterday|Today", "", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Split into sentences
    sentences = re.split(r"(?<=[.!?]) +", text)

    # Keep sentences with at least 5 words
    filtered = [s.strip() for s in sentences if len(s.split()) >= 5]

    # Deduplicate similar sentences
    unique = []
    for s in filtered:
        if not any(s in u or u in s for u in unique):
            unique.append(s)

    # Convert headlines to natural sentences
    natural_sentences = []
    for s in unique:
        s = s.replace("·", ",").replace(";", ",")
        if s:
            s = s[0].upper() + s[1:]
        natural_sentences.append(s)

    # Limit to max_sentences
    summary_sentences = natural_sentences[:max_sentences]

    # Structure as bullets and short paragraphs
    paragraph = "\n".join(f"- {s}" for s in summary_sentences)

    # Final AI-style summary
    summary = (
        f"Here’s a detailed summary for '{query}':\n\n"
        f"{paragraph}\n\n"
        f"In short, the above points summarize the most important information relevant to your query, presented clearly and understandably."
    )

    return summary

# -------------------- ROUTE --------------------
@app.route("/ask", methods=["POST", "OPTIONS"])
def ask():
    # Handle OPTIONS request (preflight)
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "https://searchbywhiter.netlify.app")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response

    # Handle POST request
    user_message = request.form.get("message", "").strip()
    if not user_message:
        response = jsonify({"response": "Please enter a question."})
        response.headers.add("Access-Control-Allow-Origin", "https://searchbywhiter.netlify.app")
        return response

    snippets = search_google(user_message)
    print("DEBUG: snippets:", snippets)
    ai_response = summarize_to_ai_style(snippets, user_message)

    response = jsonify({"response": ai_response})
    response.headers.add("Access-Control-Allow-Origin", "https://searchbywhiter.netlify.app")
    return response

# -------------------- RUN SERVER --------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
