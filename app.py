import profile
from pydoc import html
from pyexpat.errors import messages
from pathlib import Path
from unittest import result
from wsgiref import headers
from click import prompt
from flask_cors import CORS, cross_origin
import uuid
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
import supabase
import ai
from werkzeug.utils import secure_filename
import mimetypes
import src.main
from src.core.agent import run_agent_loop, AgentResponse
from src.core.config import Config
from src.core.search import WikiSearch
from src.actions.handlers import ActionRegistry


app = Flask(__name__)
cors = CORS(app)
noteslist = []
app.config['CORS_HEADERS'] = 'Content-Type'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Global State ---

config: Config = None
search: WikiSearch = None
registry: ActionRegistry = None
schema_content: str = ""

 # --- checks that the code his code only runs when the file is executed directly, not when it's imported  ---
if __name__ == '__main__':
  print("Starting Flask server on http://0.0.0.0:5000")
  app.run(host='0.0.0.0', port=5000, debug=True)

SUPABASE_URL="https://egvksfgiyhysawrkzitn.supabase.co" # The URL of the Supabase project, which is used to connect to the Supabase database. This URL is specific to the user's Supabase project and is required for establishing a connection to the database.
SUPABASE_KEY="sb_publishable_C73oNdD1-L1ehsnRlIdl0w_EHoqX29M" # The API key for the Supabase project, which is used to authenticate requests to the Supabase database. This key is specific to the user's Supabase project and is required for establishing a connection to the database.
databaseClient = create_client((SUPABASE_URL),(SUPABASE_KEY)) # The Supabase client is created using the provided URL and API key, allowing the application to interact with the Supabase database for performing various operations such as querying, inserting, updating, and deleting data.


def startup():
    """Startup and shutdown logic."""
    global config, search, registry, schema_content
    print("Starting Archivist server...")
    

    # Load config
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        
        sys.exit(1)

    config = Config.load(config_path)
    print(f"Vault path: {config.vault_path.resolve()}")
    
    # Ensure vault directories exist
    config.wiki_path.mkdir(parents=True, exist_ok=True)
    config.raw_path.mkdir(parents=True, exist_ok=True)
    config.outputs_path.mkdir(parents=True, exist_ok=True)
    config.profiles_path.mkdir(parents=True, exist_ok=True)

    # Load schema
    if config.schema_path.exists():
        schema_content = config.schema_path.read_text(encoding="utf-8")
        
    else:
        schema_content = "No schema file found. Maintain wiki pages with clear structure."
       

    # Initialise search index
    search = WikiSearch(
        db_path=config._raw.get("search", {}).get("db_path", "./archivist-index.db"),
        wiki_path=config.wiki_path,
    )
    if config._raw.get("search", {}).get("rebuild_on_startup", True):
        search.rebuild()

    # Initialise action registry
    registry = ActionRegistry(config=config, search=search)
    

startup()

@app.route("/ingestwiki/<id>", methods=["GET"])
async def ingestwiki(id):
    # Placeholder function for ingesting Wikipedia data
    result = databaseClient.table("SavedThirdPlaces").select("*").eq("id", id).execute()
    if not result.data:
        return jsonify({"error": "Saved third place not found"}), 404

    saved_third_place = result.data[0]
    name=saved_third_place["name"]
    name = name.replace(" ", "_")
    # Need to place the file into the vault folder 
    filename = "raw/" + name + ".json" # part of the file name Ollama can see
    fullfilename= "vault/" + filename # where the file actually need to be stored
    Path(fullfilename).write_text(json.dumps(saved_third_place), encoding="utf-8") # writing the file to disk
    prompt=f"""Ingest the file {filename}. Update the index. Update the log. Update the locations folder. Update the features folder."""
    # Load current wiki index
    wiki_index = ""
    if config.index_path.exists():
        wiki_index = config.index_path.read_text(encoding="utf-8")
    print(f"Calling AI with prompt: {prompt},wiki_index: {wiki_index[:200]}...")  # Print the first 200 characters of the wiki index for debugging
    print(f"Schema content: {schema_content[:400]}...")  # Print the first 200 characters of the schema content for debugging
    # Run the agent loop
    try:
        result: AgentResponse = await run_agent_loop(
            user_message=prompt,
            config= config,
            action_handlers= registry.handlers,
            action_descriptions= registry.descriptions,
            schema= schema_content,
            wiki_index=wiki_index,
            #task_type="default",
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ingestall", methods=["GET"])
async def ingestall():
    # Placeholder function for ingesting Wikipedia data
    result = databaseClient.table("SavedThirdPlaces").select("*").execute()
    if not result.data:
        return jsonify({"error": "No saved third places found"}), 404
    for saved_third_place in result.data:
        name=saved_third_place["name"]
        name = name.replace(" ", "_")
        # Need to place the file into the vault folder 
        filename = "raw/" + name + ".json" # part of the file name Ollama can see
        fullfilename= "vault/" + filename # where the file actually need to be stored
        Path(fullfilename).write_text(json.dumps(saved_third_place), encoding="utf-8") # writing the file to disk
        prompt=f"""Ingest the file {filename}. Update the index. Update the log. Update the locations folder. Update the features folder."""
        # Load current wiki index
        wiki_index = ""
        if config.index_path.exists():
            wiki_index = config.index_path.read_text(encoding="utf-8")
        print(f"Calling AI with prompt: {prompt},wiki_index: {wiki_index[:200]}...")  # Print the first 200 characters of the wiki index for debugging
        print(f"Schema content: {schema_content[:400]}...")  # Print the first 200 characters of the schema content for debugging
        # Run the agent loop
        try:
            result: AgentResponse = await run_agent_loop(
                user_message=prompt,
                config= config,
                action_handlers= registry.handlers,
                action_descriptions= registry.descriptions,
                schema= schema_content,
                wiki_index=wiki_index,
                #task_type="default",
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "Ingested all saved third places"})


@app.route("/chat", methods=["POST"]) # Creates a route for handling chat requests, which takes the conversation history as input and returns the AI's response based on that history.
async def chat(): # Defines the chat function that handles POST requests to the "/chat" endpoint. This function retrieves the conversation history from the request body, calls the AI model with that history, and returns the updated conversation history including the AI's response.
    conversation_history = request.get_json() # Retrieves the conversation history from the request body, which is expected to be a JSON array of messages representing the conversation between the user and the AI model.
    print(conversation_history)
   # response = client.chat( 
   # model=MODEL, messages=conversation_history) 
    wiki_index = ""
    if config.index_path.exists():
        wiki_index = config.index_path.read_text(encoding="utf-8")
    try:
        result: AgentResponse = await run_agent_loop(
            user_message= str(conversation_history),
            config= config,
            action_handlers= registry.handlers,
            action_descriptions= registry.descriptions,
            schema= schema_content,
            wiki_index= wiki_index,
            #task_type="default",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    conversation_history.append({"role": "assistant", "content": result.text}) #add the AI's response to the conversation history
    print(conversation_history)
    return jsonify(conversation_history)

@app.route("/allsavedthirdplaces", methods=["GET"]) # Creates a route for retrieving all saved third places from the database, which returns a JSON response containing the list of saved third places.
def allsavedthirdplaces():
    result = databaseClient.table("SavedThirdPlaces").select("*").execute()
    return jsonify(result.data)

@app.route("/thirdplaceslist", methods=["GET"]) # Creates a route for retrieving a list of third places (pubs) in London, which returns a JSON response containing the list of third places.
def thirdplaceslist():
    features_list = extract_third_place_info()
    return Response(json.dumps(features_list), mimetype="application/json")

@app.route("/openstreets", methods=["GET"]) # Creates a route for retrieving a list of third places (pubs) in London, which returns a JSON response containing the list of third places.
def openstreets():
    gdf = ox.features_from_place("London, England", tags={"amenity": "pub"})
    return Response(gdf.to_json(), mimetype="application/json")

def extract_third_place_info() -> dict:
    gdf = ox.features_from_place("London, England", tags={"amenity": "pub"})
    gdf["longitude"] = gdf.geometry.centroid.x
    gdf["latitude"] = gdf.geometry.centroid.y
    for col in ["name","addr:postcode"]:
        if col not in gdf.columns:
            gdf[col] = None
    features_list = gdf[["name", "longitude", "latitude", "addr:postcode"]].to_dict(
         orient="records")
    return features_list

@app.route("/scrapelonlat", methods=["GET"]) # Creates a route for scraping third place reviews based on the provided name and location, which returns a JSON response containing the reviews.
def scrapelonlat():
    features_list = extract_third_place_info()
    result = databaseClient.table("SavedThirdPlaces").select("*").execute()
    list=[]
    notmatchlist=[]
    for place in result.data:
        name = place["name"]
        address = place["address"]
        match=False
        for feature in features_list:
            if type (feature["addr:postcode"]) == str and feature["name"] is not None:
                if feature["name"] == name and feature["addr:postcode"] in address:
                    match=True
                    lat = feature["latitude"]
                    lon = feature["longitude"]
                    databaseClient.table("SavedThirdPlaces").update({"latitude": lat, "longitude": lon}).eq("id", place["id"]).execute()
                    list.append({"name":name,"location":place["location"],"latitude":lat,"longitude":lon})
        if not match:
            notmatchlist.append({"name":name,"location":place["location"]})
    return jsonify({"matched": list, "not_matched": notmatchlist})


@app.route("/createprofile", methods=["POST"])
def createprofile():
    profile = request.get_json()
    profile.pop("id", None)  # Remove the 'id' field if it exists, as it will be auto-generated by the database
    profile.pop("created_at", None)  # Remove the 'created_at' field if it exists, as it will be auto-generated by the database
#TODO: add this to wiki.
    result = databaseClient.table("Profile").insert(profile).execute()
    writeprofileforwiki(result.data[0])  # Write the newly created profile to the wiki
    return jsonify(result.data[0])  # Return the first inserted profile data

@app.route("/updateprofile", methods=["PUT"])
def updateprofile():
    update = request.get_json()
    profile= update["profile"]
    profile.pop("created_at", None)  # Remove the 'created_at' field if it exists, as it will be auto-generated by the database
    profile.pop("id", None)  # Remove the 'id' field if it exists, as it will be auto-generated by the database
#TODO: add this to wiki.
    result = databaseClient.table("Profile").update(profile).eq("id",update["id"]).execute()
    return jsonify(result.data[0])  # Return the first updated profile data

@app.route("/profileuploadphoto", methods=["POST"])
def profileuploadphoto():
    if "file" not in request.files:
       
        return jsonify(
            {
                "error": "No file supplied"
            }
        ), 400

    image = request.files["file"]
    orginal_filename = image.filename
    extension = os.path.splitext(image.filename)[1]
    filename = f"public/{uuid.uuid4()}{extension}"
    contents = image.read()
    
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    print(f"Uploading file to Supabase storage with filename: {filename}, extension: {extension}, mime: {mime}, original filename: {orginal_filename}")
    print(f"File content type: {image.content_type},image: {image}, image.mimetype: {image.mimetype}, type: {type(image)}")
    response = (
        databaseClient
        .storage
        .from_("profilephotos")
        .upload(
            path=filename,
            file=contents,
            file_options={
                "content-type": mime,
                "upsert": False,
            },
        )
    )

    return jsonify(response)




@app.route("/allprofiles", methods=["GET"]) # Creates a route for retrieving all profiles from the database, which returns a JSON response containing the list of profiles.
def allprofiles():
    result = databaseClient.table("Profile").select("*").execute()
    return jsonify(result.data)

def writeprofileforwiki(profile):
    name = profile["name"]
    name = name.replace(" ", "_")
    # Need to place the file into the vault folder 
    filename = "profiles/" + name + ".json" # part of the file name Ollama can see
    fullfilename = "vault/" + filename # where the file actually need to be stored
    Path(fullfilename).write_text(json.dumps(profile), encoding="utf-8") # writing the file to disk


@app.route("/writeprofile", methods=["GET"])
def writeprofile():
    result = databaseClient.table("Profile").select("*").execute()
    for profile in result.data:
        writeprofileforwiki(profile)
    return jsonify({"status": "Written all profiles to vault"})

@app.route("/createsavedthirdplace", methods=["POST"])
def createsavedthirdplace():
    saved_third_place = request.get_json()
    saved_third_place.pop("id", None)  # Remove the 'id' field if it exists, as it will be auto-generated by the database
    saved_third_place.pop("created_at", None)  # Remove the 'created_at' field if it exists, as it will be auto-generated by the database
    result = databaseClient.table("SavedThirdPlaces").insert(saved_third_place).execute()
# TODO: re-injest this third place to the wiki 
    return jsonify(result.data[0])  # Return the first inserted saved third place data

#new version. 
@app.route("/thirdplacephotoupload", methods=["POST"])
def thirdplacephotoupload():
    print("New received request to upload a file")
    if "file" not in request.files:
        print("No file part in the request")
        return jsonify(
            {
                "error": "No file supplied"
            }
        ), 400

    image = request.files["file"]
    orginal_filename = image.filename
    extension = os.path.splitext(image.filename)[1]
    filename = f"public/{uuid.uuid4()}{extension}"
    contents = image.read()
    print(f"File size: {len(contents)} bytes")  # Print the size of the file for debugging purposes
    print(contents[:100])  # Print the first 100 bytes of the file for debugging purposes
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    print(f"Uploading file to Supabase storage with filename: {filename}, extension: {extension}, mime: {mime}, original filename: {orginal_filename}")
    print(f"File content type: {image.content_type},image: {image}, image.mimetype: {image.mimetype}, type: {type(image)}")
    response = (
        databaseClient
        .storage
        .from_("thirdplacephotos")
        .upload(
            path=filename,
            file=contents,
            file_options={
                "content-type": mime,
                "upsert": False,
            },
        )
    )

    return jsonify(response)

@app.route("/alllocations", methods=["GET"])
def alllocations():
    result = databaseClient.table("Locations").select("*").execute()
    return jsonify(result.data)

#scraping locations from Wikipedia and storing them in the database.
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


@app.route("/reviews")
async def reviews():

    reviews = await get_third_place_reviews("The Flask", "Highgate, London")
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

@app.route('/suggestthirdplaces/<profile_id>', methods=['GET']) # Creates a route for suggesting pubs based on the user's profile, which takes the profile ID as a URL parameter and returns a list of suggested pubs.
def suggestthirdplaces(profile_id):
    # Fetch the profile from the database using the provided profile_id
    result = databaseClient.table("Profile").select("*").eq("id", profile_id).execute()
    if not result.data:
        return jsonify({"error": "Profile not found"}), 404

    profile = result.data[0]
    result = databaseClient.table("SavedThirdPlaces").select("*").execute()
    all_saved_third_places = result.data
    prompt = f"Given the user's profile: {profile}, and this list of third places: {all_saved_third_places}, suggest some third places from the list they might like to visit. Provide a list of names and their locations. Also provide the original JSON data for each third place in the list."
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

class ThirdPlaceSuggestion(BaseModel):
    id: int
    name: str
    location: str
    summary: str
    longitude: float
    latitude: float

class ThirdPlaceSuggestionList(BaseModel):
    suggestions: list[ThirdPlaceSuggestion]

@app.route('/structuredsuggestthirdplaces/<profile_id>', methods=['GET']) # Creates a route for suggesting pubs based on the user's profile, which takes the profile ID as a URL parameter and returns a list of suggested pubs.
def structuredsuggestthirdplaces(profile_id):
    # Fetch the profile from the database using the provided profile_id
    result = databaseClient.table("Profile").select("*").eq("id", profile_id).execute()
    if not result.data:
        return jsonify({"error": "Profile not found"}), 404

    profile = result.data[0]
    result = databaseClient.table("SavedThirdPlaces").select("*").execute()
    all_saved_third_places = result.data
    prompt = f"""Given the user's profile: {profile}, 
    and this list of third places: {all_saved_third_places}, 
    suggest three third places from the list they might like to visit."""
    response = client.chat (
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that suggests third places based on user profiles."},
            {"role": "user", "content": prompt}],
        format= ThirdPlaceSuggestionList.model_json_schema(),
    )
    suggestions = ThirdPlaceSuggestionList.model_validate_json(response["message"]["content"])
    return jsonify(suggestions.model_dump())  # Return the list of suggested third places as JSON
   
@app.route('/validatethirdplacename', methods=['POST']) # Creates a route for validating a pub name, which takes the pub name as a URL parameter and returns whether the pub name is valid or not.
def validatethirdplacename():
    req_data = request.get_json()
    third_place_name = req_data.get("third_place_name")
    prompt = f"Validate the third place name: {third_place_name}. Return 'Valid' if the name is valid, otherwise return 'Invalid'."
    response = client.chat(
        model=MODEL,
        messages=[  {
        "role": "system",
        "content": """
You are a helpful assistant that validates existing third places that are located in London, England.
Do not invent information. If you cannot find the third place, return 'exists': false and leave other fields empty.
For each third place, determine:
 - exists (true/false)
 - address
 - postal_code
 - located_in_london (true/false)
 - confidence (high/medium/low)
 - reason


Return only valid JSON.
""",
        },
        {"role": "user", "content": prompt}
    ]
    )
    validation_result = response["message"]["content"]
    return jsonify({"third_place_name": third_place_name, "validation_result": json.loads(validation_result)})


