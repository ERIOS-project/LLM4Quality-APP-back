import csv
import os
import json
import re
from jsonschema import validate, ValidationError, SchemaError
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

def get_inputs(input_csv):
    """
    Reads inputs from a CSV file and returns them as a list.

    :return: A list of strings, where each string is the first column from each row in 'inputs.csv'.
    """
    with open(input_csv, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        return [row[0] for row in reader]

def init_folder(directory_path):
    """
    Creates a directory if it does not already exist.

    :param directory_path: A string representing the path of the directory to be created.
    :return: None, but creates the directory if it doesn't exist; prints an error message if creation fails.
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
        except OSError as e:
            print(f"Error: {directory_path} : {e.strerror}")

def extract_output_structure(json_string):
    """
    Extracts a JSON object from a string and validates it against a predefined schema.

    :param json_string: A string that may contain a JSON object.
    :return: A validated JSON object (dict) if successful; None if validation fails or an error occurs.
    """
    try:
        match = re.search(r'{.*}', json_string, re.DOTALL)
        if not match:
            return None
        json_string = match.group(0)
        json_string = regex_errors(json_string)
        with open(os.environ.get("OUTPUT_STRUCTURE_PATH"), 'r') as file:
            json_schema = json.load(file)

        json_data = json.loads(json_string)

        validate(instance=json_data, schema=json_schema)
        return json_data

    except (ValueError, json.JSONDecodeError, ValidationError, SchemaError):
        return None
    except Exception as err:
        print(f"Unexpected error: {err}")
        return None

def get_filenames_from_pattern(directory, pattern):
    """
    Retrieves a list of filenames from a specified directory that start with a given pattern.

    :param directory: The path to the directory where the files are located.
    :param pattern: A string pattern that the filenames should start with.
    :return: A list of filenames that match the pattern.
    """
    names = []
    for filename in os.listdir(directory):
        if filename.startswith(pattern):
            names.append(filename)
    return names

def get_id_from_filename(string):
    """
    Extracts an ID from a filename that matches the pattern '_<id>.json'.

    :param string: The filename from which to extract the ID.
    :return: A string representing the extracted ID.
    :raises Exception: If the filename does not contain an ID matching the pattern.
    """
    match = re.search(r'_(\d+)\.json$', string)
    if match:
        return match.group(1)
    else:
        raise Exception("No ID found in the filename")
    
def log(text_to_append):
    """
    Appends a line of text to a log file specific to the model being used.

    :param text_to_append: The text string to append to the log file.
    """
    # Open the file in append mode, creating it if it doesn't exist
    with open("./log.txt", 'a') as file:
        # Append the line of text followed by a newline character
        file.write(text_to_append + '\n')

def regex_errors(string):
    """
    Cleans and corrects specific formatting issues in the given string by replacing certain encoded characters
    and incorrect punctuation with their proper forms.

    :param string: The input string to clean and correct.
    :return: A cleaned string with specific errors replaced.
    """
    string = string.replace("\\u00e9", "é")
    string = string.replace("\\u2019", "'")
    string = string.replace("'", "’")
    string = string.replace("\\xa0;", "")
    string = string.replace('"":', '":')
    return string

