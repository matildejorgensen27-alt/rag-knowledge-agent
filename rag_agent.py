# ─────────────────────────────────────────────────────────────
# MULTI-AGENT RESTAURANT ASSISTANT
# 
# This system uses 3 specialised AI agents that work together:
# Agent 1 (Intake)     → understands what the customer wants
# Agent 2 (Specialist) → handles the request using tools
# Agent 3 (Action)     → logs everything and flags urgent issues
#
# Key concept: instead of one agent doing everything, we split
# responsibilities. Each agent has one job and does it well.
# ─────────────────────────────────────────────────────────────

import anthropic      # Anthropic's Python library to talk to Claude
from dotenv import load_dotenv  # Reads our .env file so we don't hardcode secrets
import json           # For converting between Python dicts and JSON text
import datetime       # For timestamping our logs

# Load the .env file so Python can access ANTHROPIC_API_KEY
# Without this, the API key wouldn't be available to our code
load_dotenv()

# Create the Anthropic client — this is the connection to Claude
# It automatically reads ANTHROPIC_API_KEY from the environment
client = anthropic.Anthropic()

# ─────────────────────────────────────────────────────────────
# AGENT 1: INTAKE AGENT
#
# Purpose: Read and classify every customer message
# Input:   Raw customer message (string)
# Output:  A dictionary with intent, urgency, key details, summary
#
# Why a separate agent for this?
# Classification is a different skill from responding.
# Keeping it separate means we can improve or replace the
# classifier without touching the rest of the system.
# ─────────────────────────────────────────────────────────────

def intake_agent(customer_message):
    print(f"\n[Intake Agent analysing message...]")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512, # Short limit — this agent only needs to output a small JSON object
         # The system prompt defines this agent's identity and job
        # I tell it to return ONLY JSON so the code can parse it reliably
        # If it returned natural language we couldn't process it programmatically

        system="""You are a message classifier for a restaurant.
        Analyse the customer message and return ONLY a JSON object with:
        - intent: one of [reservation, cancellation, info, complaint, other]
        - urgency: one of [high, normal, low]
        - key_details: any details extracted like date, time, party size, name
        - summary: one sentence summary of what they want
        Return only valid JSON, no other text, no code blocks.""",
                # We only send the single customer message — no conversation history needed
        # This agent doesn't need context, it just needs to classify one message
        messages=[{"role": "user", "content": customer_message}]
    )
     # response.content[0].text is the raw JSON string Claude returned
    # json.loads() converts it from a string into a Python dictionary
    # so it can access classification["intent"], classification["urgency"] etc.
    try:
        classification = json.loads(response.content[0].text)
    except:
        classification = {
            "intent": "other",
            "urgency": "normal",
            "key_details": {},
            "summary": "Customer sent a follow-up message."
        }
    # Print what the agent found so we can see it working in the terminal
    print(f"[Intent: {classification['intent']} | Urgency: {classification['urgency']}]")
    print(f"[Summary: {classification['summary']}]")
    return classification
    


# ─────────────────────────────────────────────────────────────
# TOOLS
#
# Tools are Python functions that Claude can choose to call.
# This is what makes this system an AGENT rather than a chatbot.
#
# How tool use works:
# 1. We describe the tools to Claude (name, purpose, inputs)
# 2. Claude reads the customer message and decides which tool to use
# 3. Claude responds with a tool_use block instead of text
# 4. Our code detects this, runs the actual Python function
# 5. We send the result back to Claude
# 6. Claude uses that result to write the final response
#
# Key insight: Claude never directly runs code.
# It decides WHAT to call, our Python actually executes it.
# ─────────────────────────────────────────────────────────────

# This list describes our tools to Claude in a format it understands
# Each tool has: name, description, and input_schema (what inputs it needs)
tools = [
    {
        "name": "check_availability",
        "description": "Check if a table is available for a given date, time and party size",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "party_size": {"type": "integer"}
            },
            "required": ["date", "time", "party_size"]
        }
    },
    {
        "name": "make_reservation",
        "description": "Book a table for a customer",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "party_size": {"type": "integer"},
                "customer_name": {"type": "string"}
            },
            "required": ["date", "time", "party_size", "customer_name"]
        }
    },
    {
        "name": "get_restaurant_info",
        "description": "Get information about the restaurant: menu, hours, location, policies",
        "input_schema": {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "One of: menu, hours, location, policies"
                }
            },
            "required": ["info_type"]
        }
    }
]
# The actual Python functions that run when Claude calls a tool
def check_availability(date, time, party_size):
     # In a real system this would query a database or calendar API
    # For now I return fake data — the agent logic works the same either way
    return {"available": True, "date": date, "time": time, "party_size": party_size}

def make_reservation(date, time, party_size, customer_name):
    reservation = {
        "name": customer_name,
        "date": date,
        "time": time,
        "party_size": party_size,
        "status": "confirmed"
    }
     # Write to a JSON file — this is a real action, not just a response
    # "a" means append — we add to the file without overwriting previous entries
    with open("reservations.json", "a") as f:
        f.write(json.dumps(reservation) + "\n")
    return {"status": "confirmed", "reservation": reservation}

def get_restaurant_info(info_type):
     # This is the knowledge base — in production this could come from a database
    # The agent pulls from here instead of having everything in the system prompt
    # This makes the knowledge easier to update without touching the agent logic
    info = {
        "menu": {
            "mains": [
                {"name": "Bacalhau à Brás", "price": 14, "vegetarian": False},
                {"name": "Secretos de Porco", "price": 16, "vegetarian": False},
                {"name": "Arroz de Pato", "price": 13, "vegetarian": False},
                {"name": "Risotto de Legumes", "price": 12, "vegetarian": True}
            ],
            "starters": [
                {"name": "Chouriço Assado", "price": 6},
                {"name": "Azeitonas", "price": 3}
            ],
            "drinks": ["Wine from €12", "Beer €3", "Soft drinks €2"]
        },
        "hours": {
            "monday_friday": "12h-15h and 19h-23h",
            "saturday": "12h-16h and 19h-23h30",
            "sunday": "12h-16h only"
        },
        "location": {
            "address": "Rua Augusta 45, Lisboa",
            "metro": "Baixa-Chiado (3 min walk)",
            "parking": "Parklis Chiado, 5 min away"
        },
        "policies": {
            "cancellation": "Please cancel at least 2 hours in advance",
            "dogs": "Not allowed inside, welcome on terrace",
            "dress_code": "Smart casual"
        }
    }
     # .get() returns the matching section, or an error if info_type doesn't exist
    return info.get(info_type, {"error": "Information not found"})


# ─────────────────────────────────────────────────────────────
# AGENT 2: SPECIALIST AGENT
#
# Purpose: Handle the customer request using tools
# Input:   Classification from Agent 1 + original message
# Output:  A response to the customer
#
# This agent runs a TOOL LOOP — it keeps going until Claude
# decides it has all the information it needs to respond.
# Claude might call multiple tools in sequence before finishing.
# ─────────────────────────────────────────────────────────────

def specialist_agent(classification, customer_message, conversation_history):
    print(f"[Specialist Agent handling request...]")
    
    # I give this agent two things:
    # 1. The original customer message
    # 2. The classification from Agent 1 (so it knows the intent and key details)
    # This means Agent 2 starts with more context than if it read the message cold
    # We also pass the full conversation history so the agent remembers
    # everything that was said before in this conversation
    conversation_history.append({
        "role": "user",
        "content": f"""Customer message: {customer_message}
        
Pre-analysis from intake agent:
- Intent: {classification['intent']}
- Urgency: {classification['urgency']}  
- Key details: {json.dumps(classification.get('key_details', {}))}

Handle this request appropriately using your tools."""
    })
    
    system = """You are a specialist assistant for Restaurante Casa Nova in Lisbon.
    Use your tools to handle customer requests accurately.
    For reservations: check availability first, then book, always confirm the name.
    For complaints marked high urgency: be extra apologetic and helpful.
    Remember the full conversation history and maintain context between messages.
    Be warm, professional and concise."""
    
    # THE TOOL LOOP
    # I loop because Claude might need to call multiple tools before it's done
    # Example: for a reservation it calls check_availability THEN make_reservation
    # We only break out of the loop when Claude says stop_reason == "end_turn"
    # meaning it has finished and is ready to give the final response
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            tools=tools, # We pass the tools so Claude knows what it can use
            messages=conversation_history  # Full history so agent remembers context
        )
        
        # stop_reason == "end_turn" means Claude is done
        # It has all the information it needs and is giving the final response
        if response.stop_reason == "end_turn":
            reply = response.content[0].text
            print(f"\nAgent: {reply}")
            # Add agent response to history so the next message has full context
            conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            break
            
        # stop_reason == "tool_use" means Claude wants to call a tool
        # Instead of a text response, Claude is giving us a tool call
        if response.stop_reason == "tool_use":
            # Add Claude's tool call to the message history
            # This is required — Claude needs to see its own tool calls in history
            conversation_history.append({
                "role": "assistant", 
                "content": response.content
            })
            tool_results = []
            
            # Loop through Claude's response blocks
            # There could be multiple tool calls in one response
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[Using tool: {block.name}]")
                    
                    # Call the right Python function based on what Claude asked for
                    # block.input contains the arguments Claude decided to use
                    # **block.input unpacks the dict as keyword arguments
                    if block.name == "check_availability":
                        result = check_availability(**block.input)
                    elif block.name == "make_reservation":
                        result = make_reservation(**block.input)
                    elif block.name == "get_restaurant_info":
                        result = get_restaurant_info(**block.input)
                    
                    # Package the result to send back to Claude
                    # tool_use_id links this result to the specific tool call Claude made
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })
            
            # Send the tool results back to Claude
            # Now Claude reads the results and decides what to do next
            # Either call another tool or give the final response
            conversation_history.append({
                "role": "user", 
                "content": tool_results
            })
# ─────────────────────────────────────────────────────────────
# AGENT 3: ACTION AGENT
#
# Purpose: Log every interaction and flag urgent issues
# Input:   Classification from Agent 1 + original message
# Output:  Log files updated, alerts triggered if needed
#
# Why a separate agent for this?
# Logging and alerting is infrastructure, not customer service.
# Keeping it separate means we can change our logging system
# without touching the customer-facing agents.
# In production this would send real emails or Slack messages.
# ─────────────────────────────────────────────────────────────

import urllib.request

def send_to_n8n(classification, customer_message):
    # This function sends interaction data to n8n via HTTP POST
    # n8n receives it and triggers the workflow — Google Sheets logging,
    # email alerts, and any other integrations we've built
    print("[Sending data to n8n...]")
    
    # The webhook URL — this is the live URL after publishing the workflow
    # /webhook/ means it's always listening, unlike /webhook-test/ which
    # only listens for one request after you click Execute workflow
    webhook_url = "http://localhost:5678/webhook/4d053a90-fb5f-44bc-819c-699e7b8035d9"
    
    # For complaints, send the client name instead of the raw message
    # For everything else (e.g. reservations) the name is already stored in key_details
    # so we use that too — falling back to the message only if no name was found
    customer_field = classification.get("key_details", {}).get("name") or customer_message

    # The data we send to n8n — same structure as before
    data = {
        "customer": customer_field,
        "intent": classification["intent"],
        "urgency": classification["urgency"]
    }
    
    # Build the HTTP POST request
    # json.dumps converts our Python dict to a JSON string
    # .encode("utf-8") converts the string to bytes for sending
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    # try/except means if n8n is not running or the request fails
    # the program doesn't crash — it just prints an error message
    try:
        urllib.request.urlopen(req)
        print("[Data sent to n8n successfully]")
    except Exception as e:
        print(f"[n8n connection failed: {e}]")


def action_agent(classification, customer_message):
    print(f"[Action Agent logging interaction...]")
    
    # Build a log entry with everything we know about this interaction
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),  # Exact time of interaction
        "customer_message": customer_message,
        "intent": classification["intent"],
        "urgency": classification["urgency"],
        "summary": classification["summary"]
    }
    
    # Append to our log file — every interaction gets recorded here
    # This gives the business owner a full history of all customer interactions
    with open("interactions_log.json", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"[Interaction logged at {log_entry['timestamp']}]")
    
    # If urgency is high (e.g. a complaint) write a separate urgent alert
    # In a real system this would trigger an email or Slack message to the owner
    if classification["urgency"] == "high":
        alert = {
            "timestamp": datetime.datetime.now().isoformat(),
            "alert": "HIGH URGENCY INTERACTION",
            "message": customer_message,
            "summary": classification["summary"]
        }
        with open("urgent_alerts.json", "a") as f:
            f.write(json.dumps(alert) + "\n")
        print(f"[⚠️  URGENT ALERT saved — owner notification triggered]")
    
    # Send everything to n8n so it can trigger real world integrations
    # Google Sheets logging and email alerts happen automatically from here
    send_to_n8n(classification, customer_message)


# ─────────────────────────────────────────────────────────────
# ROUTER
#
# The router is the orchestrator — it connects all three agents
# and defines the order they run in for every interaction.
#
# Flow:
# Customer message → Agent 1 → Agent 2 → Agent 3 → Done
#
# Agent 1's output (classification) feeds into both Agent 2 and 3
# This is how agents communicate — by passing structured data
# ─────────────────────────────────────────────────────────────

def run_system(customer_message, conversation_history):
    print(f"\nCustomer: {customer_message}")
    print("-" * 50)

    # Step 1: Intake agent classifies the message
    classification = intake_agent(customer_message)
    print("-" * 50)

    # Check before specialist_agent runs, because it will append to conversation_history
    # If history is empty, this is the first message of the session
    is_first_message = len(conversation_history) == 0

    # Step 2: Specialist agent handles the request
    # It receives both the classification AND the original message
    # The classification gives it a head start on understanding the intent
    specialist_agent(classification, customer_message, conversation_history)
    print("-" * 50)

    # Step 3: Action agent logs and sends to n8n — only on the first message of a session
    # so that follow-up messages in the same conversation don't create duplicate log entries
    if is_first_message:
        action_agent(classification, customer_message)
    elif classification["urgency"] == "high":
        # Mid-session urgent messages still get an alert, just no duplicate log row
        alert = {
            "timestamp": datetime.datetime.now().isoformat(),
            "alert": "HIGH URGENCY INTERACTION",
            "message": customer_message,
            "summary": classification["summary"]
        }
        with open("urgent_alerts.json", "a") as f:
            f.write(json.dumps(alert) + "\n")
        print(f"[⚠️  URGENT ALERT saved — owner notification triggered]")
    print("=" * 50)


# ─────────────────────────────────────────────────────────────
# MAIN LOOP
#
# This is the entry point — where the program starts running.
# We loop forever, taking one customer message at a time,
# running it through the full 3-agent system, and waiting
# for the next message.
# ─────────────────────────────────────────────────────────────

print("Restaurante Casa Nova — AI Assistant")
print("Type 'quit' to exit")
print("=" * 50)

# Store conversation history outside the loop
# so the agent remembers previous messages
conversation_history = []

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == "quit":
        break
    run_system(user_input, conversation_history)
    