import time, os, uuid, keyring, csv, requests, json, re
import tkinter as tk
from tkinter import filedialog, Tk
from datetime import datetime

import queue


global gui_queue

global input_request_queue
global input_response_queue

def create_request_queue():
    global input_request_queue
    input_request_queue = queue.Queue()
    return input_request_queue
def create_response_queue():
    global input_response_queue
    input_response_queue = queue.Queue()
    return input_response_queue


def fetchFromKeyring():
    tmp = None
    try:
        token = keyring.get_password("EconomicKey", "Token")
        agreementToken = keyring.get_password("EconomicKey", "Agreement")
    except:
        tmp = ""
    if tmp == None:
        tmp = ""

    headers = {
        "x-AppSecretToken": token,
        "x-AgreementGrantToken": agreementToken,
        "cache-control": "no-cache"
    }
    return headers

def set_gui_queue():
    global gui_queue
    gui_queue = queue.Queue()
    return gui_queue
    
    
def ask_for_directory():
    return gui_request("ask_for_directory")

def ask_for_file():
    return gui_request("ask_for_file")

def ask_for_open_file():
    return gui_request("ask_to_open_file")

def gui_request(label, data=None):
    response_queue = queue.Queue()  # This queue will hold the result or status of the GUI operation
    gui_queue.put({'label': label, 'data': data, 'response': response_queue})
    return response_queue.get()  # This will block until we get a response

def test_dir():
    print(ask_for_directory())
    return True

def assembleEnvironment():
    global directory_to_work_with
    foldername = uuid.uuid4().hex
    parent = ask_for_directory()
    pwd = os.path.join(parent, foldername)
    directory_to_work_with = pwd.replace('/','\\')
    print("Setting target for downloads: {}".format(directory_to_work_with))
    if not os.path.exists(directory_to_work_with):
        os.makedirs(directory_to_work_with)    
    gui_request("connection_label_change", "Session activated {}".format(foldername))
    return True

def takeoverEnvironment():
    global directory_to_work_with
    parent = ask_for_directory()
    pwd = os.path.join(parent)
    foldername = os.path.basename(os.path.normpath(pwd))
    directory_to_work_with = pwd.replace('/','\\')
    print("Setting target for downloads: {}".format(directory_to_work_with))
    if not os.path.exists(directory_to_work_with):
        os.makedirs(directory_to_work_with)    
    gui_request("connection_label_change", "Session activated {}".format(foldername))
    return True

def initFileParse():
    global directory_to_work_with
    if FileParser.runtime(directory_to_work_with.replace('\\','/')):
        return True

def startFileTransfer():
    directory_to_work_with
    FileParser.sendtosftp(directory_to_work_with, 'prod')
    return True

def executeWebhook():
    print("Not implemented yet. Runs at 10 UTC. Contact Jee Ann to run after")
    return True

def validate_response(valid_values, setting = "console"):
    while True:
        if setting == "console":
            try:
                print("Valid responses are:", '  '.join(valid_values))
                input_request_queue.put("Please enter your response:")
                response = input_response_queue.get()
            except:
                print("Could not contact queue. Trying root input")
        elif setting == "input":
            input_request_queue.put("Please enter your response:")
            response = input_response_queue.get()
            return response
        if response in valid_values:
            return response
        else:
            print("Invalid response. Please try again.")


def dump_dict_to_file(data_dict, file_name):
    """
    Dumps a dictionary to a file in JSON format.

    :param data_dict: Dictionary to be dumped.
    :param file_name: Name of the file to dump the dictionary into.
    """
    try:
        with open(os.path.join(directory_to_work_with,file_name), 'w') as file:
            json.dump(data_dict, file, indent=4)
        return f"Dictionary successfully written to {file_name}"
    except Exception as e:
        return f"Error occurred: {e}"

def extractExpenseUrlFromEconomic(input):
    return input[-36:]


# REVOLUT HELPER FUNCTIONS
def process_expenses(directory):
    """
    Process the 'expenses.csv' file in the given directory.
    - Removes rows where Transaction Status is not 'COMPLETED'.
    - Adds a 'Has Attachment' column based on the presence of files with names containing the Expense ID.
    """
    def join_strings(str1, str2, str3):
        if len(str3) != 36:
            raise ValueError("The third string must be exactly 36 characters long")
        non_empty_strings = [s for s in [str1, str2] if len(s)>=1]
        combined_str1_str2 = " - ".join(non_empty_strings)
        if len(combined_str1_str2) > 210:
            print("NOTE! The combined length of the first and second strings must not exceed 210 characters")
            combined_str1_str2 = combined_str1_str2[0:210]
        return combined_str1_str2 + " - " + str3


    def has_attachment(expense_id):
        """Check for attachment files with the given expense ID."""
        for filename in os.listdir(directory):
            if expense_id in filename:
                return filename
        return "No"

    # File paths
    input_file = os.path.join(directory, 'expenses.csv')
    output_file = os.path.join(directory, 'processed_expenses.csv')

    # Read and process the CSV file
    with open(input_file, mode='r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader if row['Transaction status'] == 'COMPLETED']
    # Add 'Has Attachment' column
    for row in data:
        row['Attachment'] = has_attachment(row['Expense ID'])
        row['Import Text'] = join_strings(row['Transaction description'], row['Expense description'], row['Expense ID'])
        amount_raw = float(row['Amount (Payment currency)'])
        fee = float(row['Fee'])
        amount = amount_raw + fee
        row['Final Amount'] = amount
        row['EconomicContra'] = settings["accountMapping"][row["Account"]]
        if row["Tax name"]:
            row['EconomicVAT'] = settings["vatMapping"][row["Tax name"]]
        else:
            row['EconomicVAT'] = settings["vatMappingOverride"][row["Expense category code"]]

    # Write the processed data to a new CSV file
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    print(f"Processed file saved as: {output_file}")

def readProcessedFiles():
    # File paths
    input_file = os.path.join(directory_to_work_with, 'processed_expenses.csv')
    # Read and process the CSV file
    with open(input_file, mode='r') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader]
    return data

def list_all_journals():
    """
    Lists all journals from the e-conomic REST API.
    No arguments required, but API URL and token are hardcoded.
    """

    api_url = 'https://restapi.e-conomic.com'  # API URL (hardcoded)

    headers = fetchFromKeyring()
    headers["Content-Type"] =  'application/json'

    try:
        response = requests.get(f'{api_url}/journals', headers=headers)
        response.raise_for_status()
        return response.json()['collection']
    except requests.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")

def enrichWithResponse(data):
        print("Wrote file with respond dump")
        dump_dict_to_file(data,"test.json")
        mapping = {}
        for row in data:
            key = extractExpenseUrlFromEconomic(row["entries"]["financeVouchers"][0]["text"])
            economic = row["entries"]["financeVouchers"][0]["voucher"]["attachment"]
            mapping[key] = economic
        return mapping

class JournalEntry:
    def __init__(self, accountingYear, journalNumber):
        self.journalNumber = journalNumber
        self.accountingYear = accountingYear
        self.vouchers = []  

    def new_voucher(self, text, date, amount, account, contraAccountNumber, currencyCode, vatCode):
    # Helper function to create nested dictionary
        def create_nested_dict(key, value, value_type=None):
            if value:
                # Convert the value to the specified type if needed
                try:
                    if value_type:
                        value = value_type(value)
                except ValueError:
                    # If conversion fails, return None
                    return None
                return {key: value}
            else:
                return None
        def change_value_simple(value, value_type):
            if value:
                try:
                    if value_type:
                        value = value_type(value)
                except ValueError:
                    # If conversion fails, return None
                    return None
                return value
            else:
                return None
        def changeDateFormat(date_str):
            # Parse the input date string in 'dd/mm/yyyy' format
            date_obj = datetime.strptime(date_str, str(settings["dateformat"]))
            # Convert the date object to 'YYYY-MM-DD' format
            new_date_str = date_obj.strftime('%Y-%m-%d')
            return new_date_str

        # Creating the voucher dictionary
        voucher = {
            "text": text,
            "date": changeDateFormat(date),
            "amount": change_value_simple(amount, float),
            "contraAccount": create_nested_dict("accountNumber", contraAccountNumber, int),
            "currency": create_nested_dict("code", currencyCode),
            "account": create_nested_dict("accountNumber", account, int),
            "vatAccount": create_nested_dict("vatCode", vatCode)
        }
        # Removing keys with None or empty values, including nested dictionaries
        voucher = {k: v for k, v in voucher.items() if v}
        self.vouchers.append(voucher)

    def send_to_system(self):
        url = 'https://restapi.e-conomic.com'  # API URL (hardcoded)
        headers = fetchFromKeyring()
        headers["Content-Type"] =  'application/json'
        endpoint =url+'/journals/'+str(self.journalNumber)+'/vouchers'
        payload= []
        for row in self.vouchers:
            payload.append( {
                "accountingYear": {
                    "year": str(settings["accountingYear"]),
                },
                "journal": {
                    "journalNumber": int(self.journalNumber),
                },
                "entries": {
                    "financeVouchers": [row]
                }
            })
        data_to_ship = json.dumps(payload)

        try:
            response = requests.post(endpoint, headers=headers, data=data_to_ship)
            print(response.status_code)
        except Exception as e:
            print(f"Error occurred: {e}")

        if response.status_code == 200 or response.status_code == 201:
            print('retrun')
            return enrichWithResponse(response.json())
        else:
            return f"Error: {response.status_code}"

def submitAttachment(url_input, filename):
    # Create a FormData-like object
    files = {'file': open(os.path.join(directory_to_work_with,filename), 'rb')}

    # Request settings
    url = f'{url_input}/file'
    headers = fetchFromKeyring()

    # Making the POST request
    response = requests.post(url, headers=headers, files=files)



# REVOLUT RUNTIME FUNCTIONS
def verifyData():
    global directory_to_work_with
    print(directory_to_work_with)
    process_expenses(directory_to_work_with)
    return True

def getSettings():
    global settings
    f = open(ask_for_file())
    settings = json.load(f)
    return True



def selectJournal():
    journals = list_all_journals()
    allowedResponses = []
    if journals:
        for j in journals:
            print(f"({j['journalNumber']}): {j['name']}")
            allowedResponses.append(f"{j['journalNumber']}")
    response = validate_response(allowedResponses)
    return str(response)
        
def ship():
    data = readProcessedFiles()
    print(f'Ready to push {len(data)} rows of data to Economic.')
    selected_journal = selectJournal()
    a = JournalEntry("2024", selected_journal)
    for line in data:
        a.new_voucher(line["Import Text"], line["Transaction started (UTC)"], line["Final Amount"], line["Expense category code"], line["EconomicContra"], line["Payment currency"], line["EconomicVAT"] )
    print("Starting to push!")
    translation_key = a.send_to_system()
    #Transmitting attachments
    i= 0 
    for line in data:
        if line["Attachment"] == "No":
            gui_request("update_progress", 1/len(data)*0.995)
            continue
        else:
            url = translation_key[line["Expense ID"]]
            
            if url:
                submitAttachment(url, line["Attachment"])
        print(i/len(data))
        gui_request("update_progress", 1/len(data)*0.995)
    return True

def renameAll():
    global directory_to_work_with
    input_file = os.path.join(directory_to_work_with, 'processed_expenses.csv')

    try:
        with open(input_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Extracting the necessary fields
                account = row['EconomicContra']
                name = re.sub(r'[^0-9a-zA-Z ]+', '', row['Transaction description'])
                date = row['Transaction started (UTC)']
                amount_raw = str(row['Amount (Payment currency)']).replace('.', '-')
                fee = str(row['Fee']).replace('.', '-')
                amount = amount_raw + fee
                expense_id = row['Expense ID']


                original_file = os.path.join(directory_to_work_with, row['Attachment'])
                
                if not(row['Attachment']) or len(row['Attachment'])<1 or row['Attachment']=="No":
                    continue
                # Extracting file extension
                _, file_extension = os.path.splitext(original_file)

                # Constructing new filename with the original file extension
                new_filename = f"{account}_{date}_{amount}_{name}_{expense_id}{file_extension}"
                
                # New file path
                new_file_path = os.path.join(directory_to_work_with, new_filename)

                # Renaming the file
                os.rename(original_file, new_file_path)
                print(f"Renamed {original_file} to {new_file_path}")


    except Exception as e:
        print(f"Error occurred: {e}")

def storePasswords():
    token = []
    print("Note all secrets are stored in your own credential locker (Windows Credentials Mgr or OSX Keychain)")
    print("Please enter your API secret")
    input_token = validate_response([], "input")
    print("Please enter your agreement token")
    input_agreeement = validate_response([], "input")
    keyring.set_password("EconomicKey", "Token", input_token)
    keyring.set_password("EconomicKey", "Agreement", input_agreeement)
    print("Stored credentials")
    return True

def debugFromCli():
    # If you are testing out running this PY file directly from the CLI you can use this.

    pass


if __name__ == "__main__":
    debugFromCli()
