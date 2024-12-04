import os
import json
from dotenv import load_dotenv
from consistency_llm.utils import get_filenames_from_pattern, get_id_from_filename, init_folder

# Load environment variables from a .env file
load_dotenv()

class SlcaEvaluation:
    """
    A class to handle the SLCA evaluation by comparing 
    results from two different evaluations (LCA and SCA).
    """

    def __init__(self, output_directory):
        """
        Initializes the SlcaEvaluation class by creating necessary output directories
        based on the model name from environment variables.
        """
        self.__output_directory = output_directory
        init_folder("./" + output_directory + "/")
        init_folder("./" + output_directory + "/evaluations/")    
        init_folder("./" + output_directory + "/evaluations/slca")    

    def run(self):
        """
        Executes the SLCA evaluation process by comparing outputs from two evaluations (LCA and GCA).
        The evaluation results are saved to the appropriate directory.
        """
        print("SLCA Evaluation")
        filenames = get_filenames_from_pattern("./" + self.__output_directory + "/evaluations/lca/output_1", "result_")
        for filename in filenames:
            id = get_id_from_filename(filename)
            print(f"- Input {id}")
            with open("./" + self.__output_directory + "/evaluations/lca/output_1/" + filename, 'r') as file:
                lca1_output = json.load(file)
            with open("./" + self.__output_directory + "/evaluations/lca/output_2/" + filename, 'r') as file:
                lca2_output = json.load(file)
            with open("./" + self.__output_directory + "/evaluations/sca/" + filename, 'r') as file:
                sca_output = json.load(file)
            evaluation = self.__evaluate(lca1_output["output"], lca2_output["output"], sca_output["output"])
            self.__save_evaluation(id, {
                "input" : {
                    "lca": [lca1_output["input"], lca2_output["input"]],
                    "sca": sca_output["input"],
                },
                "output": evaluation
            })

    def __evaluate(self, lca1_output, lca2_output, sca_output):
        """
        Compares two outputs recursively and generates an evaluation result.

        :param lca1_output: The output from the LCA evaluation of the output 1.
        :param lca2_output: The output from the LCA evaluation of the output 2.
        :param sca_output: The output from the SCA evaluation.
        :return: A string containing the evaluation result in JSON format.
        """

        def recursive_compare_and_generate(cat1, cat2, cat3):
            """
            Recursively compares categories and subcategories between two outputs.

            :param cat1: The first category dictionary to compare.
            :param cat2: The second category dictionary to compare.
            :param cat3: The third category dictionary to compare.
            :return: A dictionary with the comparison results.
            """
            result = {}
            for subcat_name, subcat1 in cat1.items():
                subcat2 = cat2.get(subcat_name)
                subcat3 = cat3.get(subcat_name)
                if isinstance(subcat1, dict) and isinstance(subcat2, dict) and isinstance(subcat3, dict):
                    if "positive" in subcat1:  # Terminal category containing the specific keys
                        result[subcat_name] = {
                            key: 1 if self.__check_value(subcat1.get(key)) and (self.__check_value(subcat2.get(key)) or self.__check_value(subcat3.get(key))) else 0
                            for key in ["positive", "negative"]
                        }
                    else:
                        result[subcat_name] = recursive_compare_and_generate(subcat1, subcat2, subcat3)
                else:
                    result[subcat_name] = 1 if subcat1 == subcat2 else 0
            return result

        return recursive_compare_and_generate(lca1_output, lca2_output, sca_output)
    
    def __save_evaluation(self, id, evaluation):
        """
        Saves the GCA evaluation result to a JSON file.

        :param id: The ID associated with the input being evaluated.
        :param evaluation: A string containing the evaluation result in JSON format.
        :return: None.
        """
        file_path = f"./{self.__output_directory}/evaluations/slca/result_{id}.json"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(evaluation, ensure_ascii=False, indent=4))

    def __check_value(self, s):
        """
        Checks whether a given value is equal to 1.

        :param s: The value to be checked.
        :return: True if the value is 1, False otherwise.
        """
        return s == 1
