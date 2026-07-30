import profile
from pydoc import html
from pyexpat.errors import messages
from pathlib import Path
from wsgiref import headers
from flask_cors import CORS, cross_origin
from urllib import response
from flask import Flask, request, jsonify, render_template, redirect, url_for,Response
from bs4 import BeautifulSoup
#import asyncio
#from playwright.async_api import async_playwright
from supabase import create_client, Client
import json
import sys
from numpy import rint
from pydantic import BaseModel #between the user and the AI model.
import ollama
import os
import osmnx as ox
import pandas as pd
import requests
import ai


app = Flask(__name__)
cors = CORS(app)
noteslist = []
app.config['CORS_HEADERS'] = 'Content-Type'
if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)


SUPABASE_URL="https://egvksfgiyhysawrkzitn.supabase.co" # The URL of the Supabase project, which is used to connect to the Supabase database. This URL is specific to the user's Supabase project and is required for establishing a connection to the database.
SUPABASE_KEY="sb_publishable_C73oNdD1-L1ehsnRlIdl0w_EHoqX29M" # The API key for the Supabase project, which is used to authenticate requests to the Supabase database. This key is specific to the user's Supabase project and is required for establishing a connection to the database.
databaseClient = create_client((SUPABASE_URL),(SUPABASE_KEY)) # The Supabase client is created using the provided URL and API key, allowing the application to interact with the Supabase database for performing various operations such as querying, inserting, updating, and deleting data.

'''
 async def get_pub_reviews(pub_name, address):
    
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        search_query = f"{pub_name} {address} reviews"
        await page.goto(f"https://www.google.com/search?q={search_query}")
        # Here you would add code to scrape the reviews from the search results page
        # This is a placeholder for demonstration purposes
        try:
            await page.wait_for_selector('.review-content-class', timeout=5000)
            reviews = await page.eval_on_selector_all('.review-content-class', 
                                                     "elements => elements.map(e => e.innerText)")
            return reviews
        except Exception as e:
            print(f"Could not retrieve reviews for {pub_name}: {e}")
            return []
        finally:
            await browser.close()
# Example Usage
# reviews = await get_pub_reviews("The Flask", "Highgate, London")
''' 
@app.route("/ingest", methods=["GET"]) # Creates a route for ingesting data, which takes a JSON payload as input and inserts it into the "SavedPubs" table in the Supabase database.
def ingest(): # Defines the ingest function that handles POST requests to the "/ingest" endpoint. This function retrieves the JSON payload from the request body, which is expected to contain data to be inserted into the "SavedPubs" table in the Supabase database. It then calls the Supabase client to insert the data into the specified table and returns a JSON response indicating the success of the operation along with the inserted data.
    filename= "raw/2026-07-24-historic-pubs-in-london.md" # Specifies the filename of the raw data file that contains information about historic pubs in London. This file is expected to be in Markdown format and is used as the source of data for ingestion into the Supabase database.
    prompt= (
        "You are a helpful assistant that ingests data into a wiki. "
        "Read the file schema.md as the schema for the wiki. "
        "Read the wiki files in the wiki folder. "
        "Use tools to update and save wiki files in the wiki folder. "
        "Read the raw file " + filename + " and ingest the data into the wiki. "
    )
    response = ai.callai(prompt)
    return jsonify({"message": "Data ingested successfully", "ai_response": response}) # Returns a JSON response indicating that the data ingestion was successful, along with the AI's response to the ingestion prompt.

"""""
@app.route("/query", methods=["POST"]) # Creates a route for querying the AI model, which takes a user prompt as input and returns the AI's response based on that prompt.
def query(): # Defines the query function that handles POST requests to the "/query" endpoint. This function retrieves the user prompt from the request body, which is expected to be a JSON object containing a "prompt" field. It then calls the callai function with this prompt to get the AI's response, which is expected to be generated based on the user's input. Finally, it returns a JSON response containing the AI's response.
    user_prompt = request.get_json().get("prompt") # Retrieves the user prompt from the request body, which is expected to be a JSON object containing a "prompt" field. This prompt is used as input for the AI model to generate a response.
    ai_response = ai.callai(user_prompt)  # Calls the callai function with the user prompt to get the AI's response. This function handles the interaction with the AI model and returns the generated response based on the user's input.
    return jsonify({"ai_response": ai_response}) # Returns a JSON response containing the AI's response, which can be used by the client application to display or process the generated output.


@app.route("/lint", methods=["POST"]) # Creates a route for linting a file, which takes a file path as input and returns the AI's response after linting the specified file.
def lint(): # Defines the lint function that handles POST requests to the "/lint" endpoint. This function retrieves the file path from the request body, which is expected to be a JSON object containing a "path" field. It then constructs a prompt for the AI model to lint the specified file and calls the callai function with this prompt to get the AI's response. Finally, it returns a JSON response containing the AI's response after linting the file.
    file_path = request.get_json().get("path") # Retrieves the file path from the request body, which is expected to be a JSON object containing a "path" field. This path is used as input for the AI model to perform linting on the specified file.
    prompt = f"Lint the file at {file_path} and return any issues found." # Constructs a prompt for the AI model to lint the specified file. This prompt instructs the AI to analyze the contents of the file and return any issues or suggestions for improvement.
    ai_response = ai.callai(prompt)  # Calls the callai function with the constructed prompt to get the AI's response after linting the specified file. This function handles the interaction with the AI model and returns the generated response based on the linting task.
    return jsonify({"ai_response": ai_response}) # Returns a JSON response containing the AI's response after linting the specified file, which can be used by the client application to display or process any issues found in the file.
"""

@app.route("/chat", methods=["POST"]) # Creates a route for handling chat requests, which takes the conversation history as input and returns the AI's response based on that history.
def chat(): # Defines the chat function that handles POST requests to the "/chat" endpoint. This function retrieves the conversation history from the request body, calls the AI model with that history, and returns the updated conversation history including the AI's response.
    conversation_history = request.get_json() # Retrieves the conversation history from the request body, which is expected to be a JSON array of messages representing the conversation between the user and the AI model.
    response = client.chat(  # Calls the chat method of the AI client, passing in the model to use, the conversation messages, and the available tools. The AI model will process this information and generate a response based on the user's prompt and the system instructions, potentially using the tools if it determines that they are needed to generate an appropriate response. The response from the AI model is expected to include a message with content that can be returned to the user.
    model=MODEL, messages=conversation_history) # Calls the chat method of the AI client, passing in the model to use and the conversation messages. 
    #The AI model will process this information and generate a response based on the user's prompt and the system instructions, 
    #potentially using the tools if it determines that they are needed to generate an appropriate response. 
    # The response from the AI model is expected to include a message with content that can be returned to the user.
    conversation_history.append(response.message.model_dump()) #add the AI's response to the conversation history
    return jsonify(conversation_history)

@app.route("/allsavedpubs")
def allsavedpubs():
    result = databaseClient.table("SavedPubs").select("*").execute()
    return jsonify(result.data)

@app.route("/publist")
def publist():
    allpubs = ox.features_from_place("London, England", tags={"amenity": "pub"})
    return Response(allpubs.to_json(), mimetype="application/json")

@app.route("/createprofile", methods=["POST"])
def createprofile():
    profile = request.get_json()
    profile.pop("id", None)  # Remove the 'id' field if it exists, as it will be auto-generated by the database
    profile.pop("created_at", None)  # Remove the 'created_at' field if it exists, as it will be auto-generated by the database
    result = databaseClient.table("Profile").insert(profile).execute()
    return jsonify(result.data[0])  # Return the first inserted profile data

@app.route("/updateprofile", methods=["PUT"])
def updateprofile():
    update = request.get_json()
    profile= update["profile"]
    profile.pop("created_at", None)  # Remove the 'created_at' field if it exists, as it will be auto-generated by the database
    profile.pop("id", None)  # Remove the 'id' field if it exists, as it will be auto-generated by the database
    result = databaseClient.table("Profile").update(profile).eq("id",update["id"]).execute()
    return jsonify(result.data[0])  # Return the first updated profile data

@app.route("/allprofiles", methods=["GET"]) # Creates a route for retrieving all profiles from the database, which returns a JSON response containing the list of profiles.
def allprofiles():
    result = databaseClient.table("Profile").select("*").execute()
    return jsonify(result.data)

@app.route("/alllocations", methods=["GET"])
def alllocations():
    result = databaseClient.table("Locations").select("*").execute()
    return jsonify(result.data)

@app.route("/loadareas")
def loadareas():

    url = "https://en.wikipedia.org/wiki/List_of_areas_of_London"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    html = requests.get(url, headers=headers).text
    print(html[:3000])  # Print the first 3000 characters of the HTML for debugging purposes
    soup = BeautifulSoup(html, "html.parser")

    areas=[]

    table = soup.find_all('table')[0]
    rows = table.find_all('tr')
    for row in rows[1:]:
        alltd = row.find_all('td')
        name = alltd[0].get_text(strip=True)
        postcode = alltd[3].get_text(strip=True)
        print(name)
        areas.append({"location":name,"postal_code":postcode})
    
    print(areas[:5])

    # Remove duplicates
    areas = list({a["location"]: a for a in areas}.values())

    print(len(areas))
    print(areas[:5])

    result = databaseClient.table("Locations").upsert(areas).execute()

    return jsonify({
        "inserted": len(areas),
        "data": areas
    })



    #return Response(locations.to_json(), mimetype="application/json")


@app.route("/reviews")
async def reviews():

    reviews = await get_pub_reviews("The Flask", "Highgate, London")
    return jsonify(reviews)
    
# The home route of the Flask application. When a user accesses the root URL ("/"),
# this function is called. It constructs a prompt for the AI model that includes instructions 
# for summarizing the user's tasks based on the current notes list. It then calls the callai function 
# with this prompt to get the AI's response, which is expected to be a summary of the tasks. Finally,
# it renders the "index.html" template, passing in the current notes list and the AI's response so that they
# can be displayed on the webpage.

@app.route('/aimodel', methods=['GET']) # Specific function for the website to call the AI model, which can be used in the future for more complex interactions
def aimodel():
    prompt = request.args.get('prompt', 'The prompt is empty')
    ai_response = callai(prompt)  # This is a placeholder for the actual AI call function
    return jsonify({'ai_response': ai_response})

@app.route('/suggestpubs/<profile_id>', methods=['GET']) # Creates a route for suggesting pubs based on the user's profile, which takes the profile ID as a URL parameter and returns a list of suggested pubs.
def suggestpubs(profile_id):
    # Fetch the profile from the database using the provided profile_id
    result = databaseClient.table("Profile").select("*").eq("id", profile_id).execute()
    if not result.data:
        return jsonify({"error": "Profile not found"}), 404

    profile = result.data[0]
    result = databaseClient.table("SavedPubs").select("*").execute()
    all_saved_pubs = result.data
    prompt = f"Given the user's profile: {profile}, and this list of pubs: {all_saved_pubs}, suggest some pubs from the list they might like to visit. Provide a list of pub names and their locations. Also provide the original JSON data for each pub in the list."
    ai_response = callai(prompt)  # This is a placeholder for the actual AI call function
    return jsonify({'ai_response': ai_response})







# function calling example with ollama

client = ollama.Client()

MODEL = "qwen3-coder:30b"

DATA_DIR = "data/"


#send to Ollama a set of tools that the AI can use to perform specific tasks, such as addition, reading files, or listing files. The AI can call these tools when generating its response to a user prompt.
def read_file(path: str) -> str: # A function that takes a file path as input and returns the contents of the file as a string. This function can be called by the AI model when it needs to read a file from disk. It checks if the file exists and is not a directory before reading its contents, and it handles errors gracefully by returning appropriate error messages.
    p = Path(DATA_DIR + path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if p.is_dir():
        return f"Error: path is a directory: {path}"
    return p.read_text(encoding="utf-8", errors="replace")[:4000]

#Write file function for Ollama to write wiki pages to disk. 
def write_file(path: str, content: str) -> str: # A function that takes a file path and content as input and writes the content to the specified file. This function can be called by the AI model when it needs to write data to a file on disk. It checks if the path is valid and handles errors gracefully by returning appropriate error messages.
    p = Path(DATA_DIR + path)
    if p.exists() and p.is_dir():
        return f"Error: path is a directory: {path}"
    try:
        p.write_text(content, encoding="utf-8", errors="replace")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file: {e}"

def list_files(path: str) -> str: # A function that takes a directory path as input and returns a list of files in that directory as a string. This function can be called by the AI model when it needs to list the files in a directory. It checks if the directory exists and is indeed a directory before listing its contents, and it handles errors gracefully by returning appropriate error messages. It also limits the output to the first 200 files to avoid overwhelming the response.
    p = Path(DATA_DIR + path)
    if not p.exists():
        return f"Error: path not found: {path}"
    if not p.is_dir():
        return f"Error: not a directory: {path}"
    return "\n".join(sorted(x.name for x in p.iterdir())[:200])

def callai(user_prompt: str) -> str: # A function that takes a user prompt as input and calls the AI model with that prompt, along with the defined tools. It constructs a conversation with a system message that instructs the AI to be a careful local assistant and to use tools when needed, and a user message that contains the user's prompt. It then sends this conversation to the AI model and returns the AI's response content as a string. The tools defined in this function can be used by the AI model to perform specific tasks like addition, reading files, or listing files when generating its response.
    tools = [ # A list of tools that the AI model can use when generating its response. Each tool is defined with a type of "function" and includes a name, description, and parameters that specify the input required for that tool. The AI model can call these tools when it needs to perform specific actions as part of its response generation.
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file from disk",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a UTF-8 text file to disk",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            }
        },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    }
    ]

    tool_map = { # A mapping of tool names to their corresponding functions. This allows the AI model to call the appropriate function when it decides to use a tool as part of its response generation. The keys in this dictionary correspond to the names of the tools defined in the tools list, and the values are the actual Python functions that implement the functionality of those tools.
    "add": add,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    }

    messages = [
    {
        "role": "system",
        "content": (
            "You are a careful local assistant. "
            "Use tools when needed. "
            "Never invent file contents."
        ),
    },
    {
        "role": "user",
        "content": user_prompt
    }
    ]

    response = client.chat(  # Calls the chat method of the AI client, passing in the model to use, the conversation messages, and the available tools. The AI model will process this information and generate a response based on the user's prompt and the system instructions, potentially using the tools if it determines that they are needed to generate an appropriate response. The response from the AI model is expected to include a message with content that can be returned to the user.
    model=MODEL, messages=messages, tools=tools, ) 
    print(response) 
    return response["message"]["content"]

class PubSuggestion(BaseModel):
    id: int
    name: str
    location: str
    summary: str

class PubSuggestionList(BaseModel):
    suggestions: list[PubSuggestion]

@app.route('/structuredsuggestpubs/<profile_id>', methods=['GET']) # Creates a route for suggesting pubs based on the user's profile, which takes the profile ID as a URL parameter and returns a list of suggested pubs.
def structuredsuggestpubs(profile_id):
    # Fetch the profile from the database using the provided profile_id
    result = databaseClient.table("Profile").select("*").eq("id", profile_id).execute()
    if not result.data:
        return jsonify({"error": "Profile not found"}), 404

    profile = result.data[0]
    result = databaseClient.table("SavedPubs").select("*").execute()
    all_saved_pubs = result.data
    prompt = f"Given the user's profile: {profile}, and this list of pubs: {all_saved_pubs}, suggest some pubs from the list they might like to visit."
    response = client.chat (
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that suggests pubs based on user profiles."},
            {"role": "user", "content": prompt}],
        format= PubSuggestionList.model_json_schema(),
    )
    suggestions = PubSuggestionList.model_validate_json(response["message"]["content"])
    return jsonify(suggestions.model_dump())  # Return the list of suggested pubs as JSON
   
@app.route('/validatepubname', methods=['POST']) # Creates a route for validating a pub name, which takes the pub name as a URL parameter and returns whether the pub name is valid or not.
def validatepubname():
    req_data = request.get_json()
    pub_name = req_data.get("pub_name")
    prompt = f"Validate the pub name: {pub_name}. Return 'Valid' if the name is valid, otherwise return 'Invalid'."
    response = client.chat(
        model=MODEL,
        messages=[  {
        "role": "system",
        "content": """
You are a helpful assistant that validates existing pubs that are located in London, England.
Do not invent information. If you cannot find the pub, return 'exists': false and leave other fields empty.
For each pub, determine:
- exists (true/false)
- address
- postal_code
- located_in_london (true/false)
- confidence (high/medium/low)
- reason


Return only valid JSON.
""",
    },
            #{"role": "system", "content": "You are a helpful assistant that validates existing pubs that are located in London, England."},
            {"role": "user", "content": prompt}
        ]
    )
    validation_result = response["message"]["content"]
    return jsonify({"pub_name": pub_name, "validation_result": json.loads(validation_result)})
