import os
from dotenv import load_dotenv
from consistency_llm.utils import extract_output_structure, get_inputs, init_folder, log
from openai import AzureOpenAI, OpenAI
import json

# Load environment variables from a .env file
load_dotenv()

class InitialClassification:
    """
    A class to handle the initial classification of inputs using a specified model.
    """

    def __init__(self, input_csv, output_directory):
        """
        Initializes the InitialClassification class by loading the prompt and 
        creating necessary output directories based on the model name from environment variables.
        :param input_csv: Path of the input csv for the classification
        :param output_directory: Output directory of the classification
        """
        self.__prompt = self.__get_prompt()
        self.__output_directory = output_directory
        self.__input_csv = input_csv
        init_folder("./" + output_directory + "/")
        init_folder("./" + output_directory + "/llm_queries/")    
        init_folder("./" + output_directory + "/llm_queries/output_1/")    
        init_folder("./" + output_directory + "/llm_queries/output_2/")

    def run(self):
        """
        Executes the initial classification process for each input.
        For each input, the classification is performed twice (run 1 and run 2),
        and the results are saved to respective directories.
        """
        print("Initial classification")
        inputs = get_inputs(self.__input_csv)
        for i, input in enumerate(inputs, start=1):
            for run_number in range(1, 3):
                print(f"- Input {i}, run {run_number}")
                classification = self.__classify(i, input)
                self.__save_classification(run_number, i, classification)

    def __classify(self, id, input):
        """
        Classifies a single input using the OpenAI API with the specified prompt and input.

        :param id: An integer representing the index of the input.
        :param input: A string representing the input to be classified.
        :return: A string containing the classification result in JSON format.
        """
        full_prompt = """
        """ + self.__prompt + """
        """ + input + """ "
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
            print("Retry classify input")
            attempt_count += 1
        if attempt_count == 3:
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
        file_path = f"./{self.__output_directory}/llm_queries/output_{run_number}/initial_classification_result_{id}.json"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(classification)

    def __get_prompt(self):
        """
        Retrieves the classification prompt from a text file.
        
        :return: A string containing the prompt to be used for classification.
        """
        with open(os.environ.get("INITIAL_CLASSIFICATION_PROMPT_PATH"), 'r', encoding="utf-8") as file:
            return file.read()
