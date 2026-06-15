# FitFindr 🛍️

FitFindr is an AI-powered styling agent that helps users find secondhand clothing and generates personalized outfit recommendations based on their existing wardrobe. It features a robust Python backend with a custom planning loop, integrated Groq LLM capabilities (Llama 3.3 70B), and a Gradio web interface.

## ⚙️ Setup & Installation

To run this agent locally, clone the repository and install the required dependencies:

`pip install -r requirements.txt`

You will need a free Groq API key to power the LLM. Get your key at [console.groq.com](https://console.groq.com) and set it in a `.env` file in the root directory:

`GROQ_API_KEY=your_key_here`

To launch the Gradio web interface, run:

`python app.py`

---

## 🧰 Tool Inventory

The agent utilizes three primary tools to execute user requests:

### 1. `search_listings`
* **Purpose:** Searches a mock database of thrifted items based on parsed user criteria.
* **Inputs:** * `description` (str): Keywords describing the desired item.
    * `size` (str | None): Optional size filter (case-insensitive).
    * `max_price` (float | None): Optional price ceiling filter.
* **Outputs:** Returns a `list[dict]` of matching items sorted by relevance. Returns an empty list `[]` if no matches are found.

### 2. `suggest_outfit`
* **Purpose:** Calls the Groq LLM to generate 1–2 complete outfit ideas combining the newly found item with the user's existing wardrobe.
* **Inputs:** * `new_item` (dict): The selected item from `search_listings`.
    * `wardrobe` (dict): The user's current wardrobe data.
* **Outputs:** Returns a `str` containing the stylized outfit recommendations.

### 3. `create_fit_card`
* **Purpose:** Uses the Groq LLM to transform the generated outfit suggestion into an engaging, authentic social media caption (OOTD style).
* **Inputs:** * `outfit` (str): The text output from `suggest_outfit`.
    * `new_item` (dict): The item dictionary to extract price/platform details.
* **Outputs:** Returns a `str` containing the final fit card caption.

---

## 🧠 The Planning Loop & State Management

FitFindr uses a planning loop governed by a central state object. 

**State Management:** State is passed between tools using a single `session` dictionary (`{"query": str, "parsed": dict, "search_results": list, "selected_item": dict, "outfit_suggestion": str, "fit_card": str, "error": str}`). 

**The Loop:**
1.  **Initialize & Parse:** The agent initializes the session and extracts the search parameters (`description`, `size`, `max_price`) from the user query using regex.
2.  **Search & Branch:** The parsed parameters are fed to `search_listings`. 
    * *Critical Branch:* If the search returns an empty list, the loop intercepts this, sets `session["error"]` to a friendly message, and aborts the loop immediately. This prevents downstream LLM tools from crashing due to missing data.
3.  **Execute LLMs:** If items are found, the top result is saved to the session and passed to `suggest_outfit`, followed by `create_fit_card`.
4.  **UI Handoff:** The completed `session` dictionary is returned to the Gradio frontend, which maps the populated fields to the corresponding UI panels.

---

## 🛡️ Error Handling & Edge Cases


* **`search_listings` Failure:** Tested with an impossible query ("designer ballgown size XXS under $5"). The tool safely returned `[]`. The planning loop caught this and passed the error to the UI without raising a Python exception.
* **`suggest_outfit` Failure:** Tested with an empty wardrobe dictionary. Instead of crashing, the tool executed a fallback LLM prompt to provide *general* styling advice based purely on the newly found item (e.g., suggesting basic color pairings).
* **`create_fit_card` Failure:** Tested by passing an empty string as the `outfit` parameter. A guard clause (`if not outfit or not outfit.strip():`) intercepted the request before making an API call. It then returned a hardcoded error string: *"Could not generate a fit card: outfit data was lost or empty..."*

---

## 🤖 AI Usage & Overrides

I leveraged Claude to assist with writing the some Python logic for my tools and planning loop based on my predefined specifications and ASCII architecture diagrams. However, I intervened and overrode the AI-generated code at times to ensure it met my design needs:

1.  **The Null Type Bug in `search_listings`:**
    * *Input:* I asked Claude to implement the search logic with keyword scoring.
    * *Output:* Claude generated code that assumed missing dictionary values would default to an empty string (`listing.get("brand", "")`). 
    * *Override:* During `pytest` execution, the suite crashed with a `TypeError` because the mock data contained `brand: null` (Python `None`), which cannot be joined to a string. I overrode Claude's logic and added string casting and null-safe fallbacks (`str(part) or ""`) to fix the error.
2.  **Missing API Fallbacks in `suggest_outfit`:**
    * *Input:* I provided the spec to build the LLM styling tool using the Groq API.
    * *Output:* Claude provided a functional API call but it was vulnerable.
    * *Override:* Knowing that network requests to LLMs can timeout or hit rate limits, I wrapped the call to Groq network in a `try...except` block so that a temporary API outage wouldn't crash the entire Gradio web interface.

---

## 📝 Spec Reflection

Building FitFindr reinforced the importance of strict management and defensive programming in AI applications. By mapping out the architecture and failure branches *before* writing the code, I was able to make a system where tools only passed information to each other when needed. I also realized that the hard part of building an AI agent is handling what happens when the data or the API unexpectedly fails.