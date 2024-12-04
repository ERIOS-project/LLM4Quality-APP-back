import os
import json
from dotenv import load_dotenv
from consistency_llm.utils import extract_output_structure, get_inputs, init_folder, log
from openai import AzureOpenAI, OpenAI
import json

# Load environment variables from a .env file
load_dotenv()

class FewShotCotClassification:
    """
    A class to handle few-shot chain-of-thought (COT) classification for inputs using a specified model.
    """

    def __init__(self, input_csv, output_directory):
        """
        Initializes the FewShotCotClassification class by loading the prompt and categories,
        and creating necessary output directories based on the model name from environment variables.
        :param input_csv: Path of the input csv for the classification
        :param output_directory: Output directory of the classification
        """
        self.__prompt = self.__get_prompt()
        self.__prompt_initial_classification= self.__get_prompt_initial_classification()
        self.__categories = self.__get_categories()
        self.__output_directory = output_directory
        self.__input_csv = input_csv
        init_folder("./" + output_directory + "/")
        init_folder("./" + output_directory + "/llm_queries/")    
        init_folder("./" + output_directory + "/llm_queries/output_1/")    
        init_folder("./" + output_directory + "/llm_queries/output_2/")

    def run(self):
        """
        Executes the few-shot COT classification process for each input.
        For each input, the classification is performed twice (run 1 and run 2),
        and the results are saved to respective directories.
        """
        print("Few shot COT classification")
        inputs = get_inputs(self.__input_csv)
        for i, input in enumerate(inputs, start=1):
            for run_number in range(1, 3):
                print(f"- Input {i}, run {run_number}")
                initial_classification = self.__get_initial_classification(run_number, i)
                classification = self.__classify(input, initial_classification)
                self.__save_classification(run_number, i, classification)

    def __classify(self, input, initial_classification):
        """
        Classifies a single input using the OpenAI API with a few-shot chain-of-thought prompt.

        :param input: A string representing the input to be classified.
        :return: A string containing the classification result in JSON format.
        """
        
        prompt_initial_classification = """
        [INST]
        """ + self.__prompt_initial_classification + """
        """ + input + """ "
        """
        full_prompt = f"""
            {prompt_initial_classification}

            {initial_classification}

            A category can be identified as present only if one of its elements is mentioned. Here is a list of each possible elements for each category in a json format :
            {self.__categories}
            {self.__prompt}
            {input} '. Create the json in totality according to all instructions given. 
            In the case where you identify the presence of the tone 'positive', 'negative' ou 'neutral', it is crucial that the justification contains word for word an element of the given list defining this very category.
        [/INST]
        """ 
        client = OpenAI(
            base_url=os.environ.get("API_ENDPOINT"),
            api_key=os.environ.get("API_KEY"),  
        )
        attempt_count = 0
        while attempt_count < 5:
            response = ""
            for chat_completion in client.chat.completions.create(
                model=os.environ.get("MODEL_NAME"),
                messages=[
                    {"role": "system", "content": full_prompt}
                ],
                stream=True,
            ):
                if chat_completion.choices: 
                    response += (chat_completion.choices[0].delta.content or "")
            output = extract_output_structure(response)
            if output is not None:
                result = {
                    "input": full_prompt,
                    "output": output
                }
                response = json.dumps(result, ensure_ascii=False, indent=4)
                break
            attempt_count += 1
        if attempt_count == 5:
            log(f"Input {id}: Error classify")
        return response

    def __save_classification(self, run_number, id, classification):
        """
        Saves the classification result to a JSON file.

        :param run_number: An integer representing the current run (1 or 2).
        :param id: An integer representing the index of the input.
        :param classification: A string containing the classification result in JSON format.
        :return: None.
        """
        file_path = f"./{self.__output_directory}/llm_queries/output_{run_number}/few_shot_cot_classification_result_{id}.json"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(classification)

    def __get_prompt(self):
        """
        Retrieves the classification prompt from a text file.
        
        :return: A string containing the prompt to be used for classification.
        """
        with open(os.environ.get("FEW_SHOT_COT_CLASSIFICATION_PROMPT_PATH"), 'r', encoding="utf-8") as file:
            return file.read()

    def __get_categories(self):
        """
        Retrieves the categories and their elements from a JSON file.

        :return: A string representation of the JSON object containing categories and their elements.
        """
        with open(os.environ.get("CATEGORIES_PATH"), encoding='utf-8') as json_file:
            return str(json.load(json_file))

    def __get_initial_classification(self, run_number, id):
        with open("./" + self.__output_directory + f"/llm_queries/output_{run_number}/initial_classification_result_{id}.json", 'r', encoding="utf-8") as file:
            return file.read()
            
    def __get_prompt_initial_classification(self):
        """
        Retrieves the classification prompt from a text file.
        
        :return: A string containing the prompt to be used for classification.
        """
        with open(os.environ.get("INITIAL_CLASSIFICATION_PROMPT_PATH"), 'r', encoding="utf-8") as file:
            return file.read()