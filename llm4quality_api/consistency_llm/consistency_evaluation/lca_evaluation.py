import os
import json
from dotenv import load_dotenv
from consistency_llm.utils import get_filenames_from_pattern, get_id_from_filename, init_folder
import re

# Load environment variables from a .env file
load_dotenv()

class LcaEvaluation:
    """
    A class to handle the LCA evaluation by comparing 
    results from two different runs (output_1 and output_2) of a few-shot chain-of-thought classification.
    """

    def __init__(self, output_directory):
        """
        Initializes the LcaEvaluation class by loading the categories, 
        and creating necessary output directories based on the model name from environment variables.
        """
        self.__categories = self.__get_categories()
        self.__output_directory = output_directory
        init_folder("./" + output_directory + "/")
        init_folder("./" + output_directory + "/evaluations/")    
        init_folder("./" + output_directory + "/evaluations/lca")    
        init_folder("./" + output_directory + "/evaluations/lca/output_1")    
        init_folder("./" + output_directory + "/evaluations/lca/output_2")    

    def run(self):
        """
        Executes the LCA evaluation process by comparing outputs from two different runs (output_1 and output_2).
        The evaluation results are saved to the appropriate directory.
        """
        print("LCA Evaluation")
        filenames = get_filenames_from_pattern("./" + self.__output_directory + "/llm_queries/output_1/", "few_shot_cot_classification_result_")
        for filename in filenames:
            id = get_id_from_filename(filename)
            for run_number in range(1, 3):
                print(f"- Input {id}, run {run_number}")
                with open("./" + self.__output_directory + f"/llm_queries/output_{run_number}/" + filename, 'r') as file:
                    output = json.load(file)
                evaluation = self.__evaluate(output["output"])
                self.__save_evaluation(id, run_number, {
                    "input" : output["input"],
                    "output": evaluation
                })

    def __evaluate(self, output):
        """
        Evaluate output recursively and generates an evaluation result.

        :param output: The output (dictionary) to be evaluate.
        :return: A string containing the evaluation result in JSON format.
        """

        def recursive_evaluate(cat):
            """
            Recursively evaluate categories and subcategories.

            :param cat: The category dictionary to evaluate.
            :return: A dictionary with the evaluation results.
            """
            result = {}
            if cat is not list:
                for subcat_name, subcat in cat.items():
                    if isinstance(subcat, dict):
                        if "positive" in subcat:  # Terminal category containing specific keys
                            result[subcat_name] = {
                                key: 1 if self.__check_value(subcat.get(key),subcat_name) else 0
                                for key in ["positive", "negative"]
                            }
                        else:
                            result[subcat_name] = recursive_evaluate(subcat)
                    else:
                        result[subcat_name] = 0
            return result

        return recursive_evaluate(output)
    
    def __save_evaluation(self, id, run_number, evaluation):
        """
        Saves the LCA evaluation result to a JSON file.

        :param id: The ID associated with the input being evaluated.
        :param run_number: The ID associated with the run number.
        :param evaluation: A string containing the evaluation result in JSON format.
        :return: None.
        """
        file_path = f"./{self.__output_directory}/evaluations/lca/output_{run_number}/result_{id}.json"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(evaluation, ensure_ascii=False, indent=4))

    def __check_value(self, value, categorie):
        """
        Checks if a given value meets specific criteria based on its format and content, 
        and verifies it against a subcategory in the `__categories` dictionary.

        :param value: The string value to be checked. Expected to be in the format 'element|description'.
        :param categorie: The name of the subcategory against which the first part of the value will be checked.
        :return: True if the value meets all criteria; otherwise, False.
        """
        if value is not None:
            if '|' in value:
                parts = value.split('|')
                if len(parts) == 2:
                    elements = self.__get_subcategory_values(categorie)
                    if elements is not None:
                        if self.__is_in_array(parts[0], elements):
                            if len(parts[1]) > 0:
                                return True
        return False

    def __get_categories(self):
        """
        Retrieves the categories and their elements from a JSON file.

        :return: the JSON object containing categories and their elements.
        """
        with open(os.environ.get("CATEGORIES_PATH"), encoding='utf-8') as json_file:
            return json.load(json_file)

    def __get_subcategory_values(self, subcategory_name):
        """
        Retrieves the values of a specified subcategory from the categories dictionary.

        :param subcategory_name: The name of the subcategory for which to retrieve values.
        :return: A list of values for the specified subcategory if found; otherwise, None.
        """
        for _, subcategories in self.__categories.items():
            if subcategory_name in subcategories:
                return list(subcategories[subcategory_name].values())
        return None

    def __clean_string(self, s):
        """
        Cleans a string by stripping leading and trailing whitespace, converting it to lowercase,
        and removing any non-alphanumeric characters except for spaces.

        :param s: The string to be cleaned.
        :return: A cleaned version of the input string.
        """
        s = s.strip()
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)  # Remove all characters that are not word characters or spaces
        return s

    def __is_in_array(self, value, array):
        """
        Checks if a given value is present in an array after cleaning both the value and each element of the array.

        :param value: The value to search for in the array.
        :param array: A list of strings in which to search for the value.
        :return: True if the cleaned value is found in the cleaned array, False otherwise.
        """
        string_cleaned = self.__clean_string(value)
        for elem in array:
            if self.__compare_strings(self.__clean_string(elem), string_cleaned):
                return True
        return False
    
    def __compare_strings(self, string1, string2):
        """
        Compares two strings based on their lengths. If either string is less than 20 characters,
        it checks if they are exactly equal. If both strings are 20 or more characters long,
        it compares the first 20 characters of both strings.

        :param string1: The first string to compare.
        :param string2: The second string to compare.
        :return: True if the strings are considered equal based on the comparison criteria, False otherwise.
        """
        if len(string1) < 20 or len(string2) < 20:
            # If the strings are less than 20 characters long, they must be exactly equal
            return string1 == string2
        else:
            # Compare the first 20 characters of both strings
            return string1[:20] == string2[:20]
