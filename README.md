# awardsearchtool



Building a custom award availability scraper using AI agents is a fantastic project. Because you are using AI agents, you need to structure your plan to maximize what AI does well (writing parsing code, structuring data, executing boilerplate) while handling what AI fails at (navigating anti-bot systems and reverse-engineering complex network traffic) yourself.
We will use Alaska Airlines (Mileage Plan) as our test case. Why? Alaska has a highly valuable loyalty program, their web layout is clean, and unlike Delta or Air Canada, they don't immediately throw up brutal anti-bot walls (like Akamai or Cloudflare Turnstile) on their front page—making them a perfect playground to test a prototype.
Here is the step-by-step implementation blueprint to give your AI agents.
Phase 1: Human Reconnaissance (The AI Context)
Before you let your AI write code, you must feed it the exact blueprint of the airline’s internal API. AI cannot easily sniff network traffic for you, so you must do this 5-minute task manually.
Open your browser, right-click, and open Developer Tools (F12). Go to the Network tab and check the Fetch/XHR filter.
Go to AlaskaAir.com. Input a flight (e.g., SEA to JFK), select "Use Miles", pick a date, and hit search.
Look closely at the Network tab for a clean JSON response. Look for an API endpoint that handles the flight search request.
Right-click that network request, select Copy -> Copy as cURL.
Paste that cURL block into a text file. This file is the goldmine. It contains the target URL, the exact payload shape (JSON parameters), and your temporary session cookies/headers.
Phase 2: The Step-by-Step AI Prompt Sequence
Do not ask the AI to "build an award scraper" all at once. Break it down into these exact sub-tasks.
Step 1: Write the Payload & Request Generator
Provide your AI with the cURL command you copied and tell it to write a Python script that modularizes the request.
Prompt to AI Agent:
"Using the attached cURL command from Alaska Airlines, write a Python script using the requests library. Abstract the payload parameters into a function generate_search(origin, destination, date, cabin). The function should dynamically construct the JSON payload and headers. Ensure all original headers (like User-Agent and authorization tokens) from the cURL are included as a baseline configuration."
Step 2: Build the Response Parser
Save a sample JSON response from your manual browser search into a file called sample_response.json and feed it to the AI.
Prompt to AI Agent:
"Inspect the attached sample_response.json from the Alaska Airlines flight search API. Write a Python parsing function parse_award_data(json_data) that extracts a clean list of dictionaries. For each flight option, extract: flight number, departure time, arrival time, carrier, cabin class, mileage cost, and partner tax fees. Return an empty list if no award availability exists on that date."
Step 3: Integrate Browser Automation for Cookie Maintenance
Airlines use short-lived session cookies. Hardcoded cURL headers will stop working after 15–30 minutes. To fix this, your AI needs to build an automated browser worker to dynamically fetch fresh cookies.
Prompt to AI Agent:
"Write a Playwright or Selenium script in Python that launches a headless browser, navigates to AlaskaAir.com, waits 3 seconds to ensure cookies are initialized, and extracts the current browser session cookies and headers. Package this into a helper function get_fresh_session() that returns a cookie jar or dict to feed into our primary requests session."
Step 4: Build the Search Grid Controller (The Matrix)
Award space is rarely found on a single day. You need to search a matrix of origins, destinations, and dates.  
GitHub
Prompt to AI Agent:
"Create a orchestrator script run_matrix_search.py. It should accept a list of origins, destinations, and a date range (e.g., next 14 days). Loop through each combination sequentially. To prevent triggering bot detection, implement a random sleep delay between 3 and 7 seconds between every single API call. Save the final results to a structured SQLite database or a daily CSV file inside an /output directory."  
GitHub
+ 1
Phase 3: Mitigating the Defense (The "Cat and Mouse" Layer)
Your script will work beautifully for about 20 searches before Alaska's network protection flags you as a bot. To keep your pipeline alive, instruct your AI agent to apply these specific defensive measures:
User-Agent Rotation: Use the fake-useragent library to dynamically generate realistic browser headers on every request.
The Session Handshake Strategy: Instead of hitting the API endpoint completely blind, your automation script must first mimic a real human landing page visit (GET alaskaair.com), wait for a moment, and then fire the backend search endpoint using those freshly acquired cookies.
Proxy Integration: If you plan on scaling this to scan months of data, instruct your AI to route the requests session through a rotating residential proxy pool (like Bright Data or Oxylabs) so every query originates from a different residential IP address.
