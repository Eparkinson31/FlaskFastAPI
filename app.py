from pyexpat.errors import messages
from pathlib import Path
from flask_cors import CORS, cross_origin
from urllib import response
from flask import Flask, request, jsonify, render_template, redirect, url_for
#from supabase import create_client, Client
import json
import sys
import ollama
import os
 
app = Flask(__name__)
cors = CORS(app)
noteslist = []
app.config['CORS_HEADERS'] = 'Content-Type'
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
@app.route("/test")
def test():
    return "Test route is working!"

@app.route("/")
def home():
    # prompt = "Summarize the following notes: " + json.dumps(noteslist)  #Opens the homepage and creates a prompt asking the AI to summarize the notes.  
    prompt = "You are organising a todo list for the user. Your role is to provide them with an easy, human readable summary of their tasks. Given these tasks, summarise them in a concise, human friendly manner. Use a conversational tone. If there are no tasks, state 'No remaining tasks, hooray!'" + json.dumps(noteslist)  #Opens the homepage and creates a prompt asking the AI to summarize the notes.  
    ai_response = callai(prompt)  # Call the AI function with a prompt
    return render_template("index.html", noteslist=noteslist, ai_response=ai_response)  #Sends the notes and AI response to the index.html page so they can be displayed on the website.

@app.route("/ai_response", methods=["POST"]) #Creates a route for getting the AI response, which takes the current notes list as input and returns the AI's summary of the notes.
def ai_response():
    req_data = request.get_json()
    prompt = "You are organising a todo list for the user. Your role is to provide them with an easy, human readable summary of their tasks. Given these tasks, summarise them in a concise, human friendly manner. Use a conversational tone. If there are no tasks, state 'No remaining tasks, hooray!'" + json.dumps(req_data)  #Opens the homepage and creates a prompt asking the AI to summarize the notes.  
    ai_response = callai(prompt)  # Call the AI function with a prompt
    return ai_response

@app.route("/add", methods=["GET"]) #Creates a route for adding a note, which takes the note as a query parameter and adds it to the notes list.
def add_note():
    item = request.args.get("item", "") # Gets the note from the query parameters, with a default value of an empty string if no note is provided.
    noteslist.append({"item": item, "completed": False})  # Call the add method in the service layer
    # Here you would typically add the note to a database or in-memory list
    # For demonstration, we'll just return the note back as a confirmation
    return redirect(url_for('home'))  # Redirect back to the home page to show the updated notes list

@app.route('/delete/<note>', methods=['POST']) #Creates a route for deleting a note, which takes the note as a URL parameter and deletes it from the notes list.
def delete(note):
    # Call the delete method in the service layer
    noteslist[:] = [d for d in noteslist if d.get('item') != note]
    # Redirect to the list of todos after deletion
    return redirect(url_for('home'))  # Redirect back to the home page to show the updated notes list

@app.route('/completed/<note>', methods=['POST']) #Creates a route for marking a note as completed, which takes the note as a URL parameter and updates its status.
def completed(note):
    # Call the completed method in the service layer
    for d in noteslist: # Iterate through the notes list to find the note that matches the provided note parameter
        if d.get('item') == note: # If a match is found, update the 'completed' status of that note to True
            d['completed'] = True # This line sets the 'completed' key of the matching note to True, indicating that the note has been marked as completed.
    # Redirect to the list of todos after marking as completed
    return redirect(url_for('home'))  # Redirect back to the home page to show the updated notes list

@app.route('/notcompleted/<note>', methods=['POST']) #Creates a route for marking a note as not completed, which takes the note as a URL parameter and updates its status.
def notcompleted(note):
    # Call the notcompleted method in the service layer
    for d in noteslist:
        if d.get('item') == note: # If a match is found, update the 'completed' status of that note to False
            d['completed'] = False
    # Redirect to the list of todos after marking as not completed
    return redirect(url_for('home'))

@app.route('/ai', methods=['GET'])
# Specific function for the website to call the AI model, which can be used in the future for more complex interactions
def ai():
    prompt = request.args.get('prompt', 'The prompt is empty')
    ai_response = callai(prompt)  # This is a placeholder for the actual AI call function
    return jsonify({'ai_response': ai_response})

# function calling example with ollama

client = ollama.Client()

MODEL = "qwen3-coder:30b"

def add(a: float, b: float) -> str: # A simple function that takes two numbers as input and returns their sum as a string. This function can be called by the AI model when it needs to perform addition.
    return str(a + b)

def read_file(path: str) -> str: # A function that takes a file path as input and returns the contents of the file as a string. This function can be called by the AI model when it needs to read a file from disk. It checks if the file exists and is not a directory before reading its contents, and it handles errors gracefully by returning appropriate error messages.
    p = Path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if p.is_dir():
        return f"Error: path is a directory: {path}"
    return p.read_text(encoding="utf-8", errors="replace")[:4000]

def list_files(path: str) -> str: # A function that takes a directory path as input and returns a list of files in that directory as a string. This function can be called by the AI model when it needs to list the files in a directory. It checks if the directory exists and is indeed a directory before listing its contents, and it handles errors gracefully by returning appropriate error messages. It also limits the output to the first 200 files to avoid overwhelming the response.
    p = Path(path)
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

''' 
messages.append(response["message"])
 for call in response["message"].get("tool_calls") or []:
      name = call["function"]["name"] 
      args = call["function"]["arguments"] 
      result = tool_map[name](**args)
       
     messages.append({ 
     "role": "tool", 
     "name": name, 
     "content": result,
       }) 
       final_response = client.chat( 
       model=MODEL, messages=messages,
        ) 
        print(final_response)
          return final_response["message"]["content"] 
'''