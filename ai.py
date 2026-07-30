from itertools import count
from pathlib import Path
from pyexpat.errors import messages
from urllib import response
import ollama
#from supabase_functions import create_client



client = ollama.Client()

MODEL = "qwen3-coder:30b"

DATA_DIR = "data/" #where all the wiki files live (wiki, raw and schemea (CLAUDE.md) files)

#SUPABASE_URL="https://egvksfgiyhysawrkzitn.supabase.co" # The URL of the Supabase project, which is used to connect to the Supabase database. This URL is specific to the user's Supabase project and is required for establishing a connection to the database.
#SUPABASE_KEY="sb_publishable_C73oNdD1-L1ehsnRlIdl0w_EHoqX29M" # The API key for the Supabase project, which is used to authenticate requests to the Supabase database. This key is specific to the user's Supabase project and is required for establishing a connection to the database.
#databaseClient = create_client((SUPABASE_URL),(SUPABASE_KEY))




#send to Ollama a set of tools that the AI can use to perform specific tasks, such as addition, reading files, or listing files. The AI can call these tools when generating its response to a user prompt.
def read_file(path: str) -> str: # A function that takes a file path as input and returns the contents of the file as a string. This function can be called by the AI model when it needs to read a file from disk. It checks if the file exists and is not a directory before reading its contents, and it handles errors gracefully by returning appropriate error messages.
    p = Path(DATA_DIR + path)
    if not p.exists():
        return f"Error: file not found: {path}"
    if p.is_dir():
        return f"Error: path is a directory: {path}"
    return p.read_text(encoding="utf-8", errors="replace")

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



#A function that lists all the files in a specified directory. 
# It first checks that the folder exists and is actually a directory.
# If either check fails, it returns an error message. 
# Otherwise, it retrieves the filenames, sorts them alphabetically, 
# and returns them as a single string with one filename per line. 
# This allows the LLM to see what files are available before deciding which one to read or update.

def list_files(path: str) -> str: 
    p = Path(DATA_DIR + path)
    if not p.exists():
        return f"Error: path not found: {path}"
    if not p.is_dir():
        return f"Error: not a directory: {path}"
    return "\n".join(sorted(x.name for x in p.iterdir()))

def find_profile(name: str) -> str: # A function that searches for a profile in the database by name. It queries the "Profile" table for entries where the "name" field matches the provided name. If no matching profiles are found, it returns an error message. If matching profiles are found, it returns their data as a string representation of a list of dictionaries. This function can be called by the AI model when it needs to retrieve profile information from the database.
    result = databaseClient.table("Profile").select("*").eq("name", name).execute()
    if not result.data:
        return f"Error: profile not found: {name}"
    return str(result.data)


tools = [ # A list of tools that the AI model can use when generating its response. Each tool is defined with a type of "function" and includes a name, description, and parameters that specify the input required for that tool. The AI model can call these tools when it needs to perform specific actions as part of its response generation.
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
    },
    {
            "type": "function",
            "function": {
                "name": "find_profile",
                "description": "Find a profile in the database",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                }
            }
        }
    ]

def calltools(response, messages):
    tool_map = { # A mapping of tool names to their corresponding functions. This allows the AI model to call the appropriate function when it decides to use a tool as part of its response generation. The keys in this dictionary correspond to the names of the tools defined in the tools list, and the values are the actual Python functions that implement the functionality of those tools.
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "find_profile": find_profile,
    }
    count = 0
    for call in response["message"].get("tool_calls") or []:
        count += 1
        name = call["function"]["name"]
        args = call["function"]["arguments"]
        print(f"Calling tool {name} with args {args}")
        result = tool_map[name](**args)
        messages.append({
         "role": "tool",
         "name": name,
            "content": result,

         })
    return count

def callai(user_prompt: str) -> str: # A function that takes a user prompt as input and calls the AI model with that prompt, along with the defined tools. It constructs a conversation with a system message that instructs the AI to be a careful local assistant and to use tools when needed, and a user message that contains the user's prompt. It then sends this conversation to the AI model and returns the AI's response content as a string. The tools defined in this function can be used by the AI model to perform specific tasks like addition, reading files, or listing files when generating its response.
    
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
    print
    limit = 30 # A limit on the number of tool calls that can be made during the AI's response generation. This is to prevent excessive or infinite tool calls that could lead to performance issues or unintended behavior. The limit is decremented each time a tool is called, and if it reaches zero, a RuntimeError is raised to indicate that the tool call limit has been reached.
    while True: # A loop that continues to call the AI model until a response generated by the AI does not require any further tool calls. The loop constructs the conversation messages, sends them to the AI model, and checks if any tools were called in the response. If no tools were called, it returns the AI's response content. If tools were called, it processes those tool calls and continues the loop until a final response is generated without any further tool calls.
        response = client.chat(  # Calls the chat method of the AI client, passing in the model to use, the conversation messages, and the available tools. The AI model will process this information and generate a response based on the user's prompt and the system instructions, potentially using the tools if it determines that they are needed to generate an appropriate response. The response from the AI model is expected to include a message with content that can be returned to the user.
            model=MODEL, messages=messages, tools=tools
        )
        print("initial response from Ollama:")
        print(response)
        messages.append(response["message"])
        tool_calls_count = calltools(response, messages)
        if tool_calls_count == 0:
            return response["message"]["content"]
        limit -= 1
        if limit == 0:
            raise RuntimeError("Tool call limit reached")