import csv
import json
import os
import queue
import re
import uuid
from datetime import datetime

import keyring
import requests


directory_to_work_with = ""
settings = None


def create_request_queue():
    global input_request_queue
    input_request_queue = queue.Queue()
    return input_request_queue
def create_response_queue():
    global input_response_queue
    input_response_queue = queue.Queue()
    return input_response_queue


def fetchFromKeyring():
    token = None
    agreementToken = None
    try:
        token = keyring.get_password("EconomicKey", "Token")
        agreementToken = keyring.get_password("EconomicKey", "Agreement")
    except Exception as e:
        print(f"Could not read credentials from the system keyring: {e}")
    if not token or not agreementToken:
        print("No stored credentials found. Use 'Save credentials' first.")

    headers = {
        "x-AppSecretToken": token or "",
        "x-AgreementGrantToken": agreementToken or "",
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

def require_working_directory():
    """Returns True when a working directory has been selected."""
    if not directory_to_work_with:
        print("No working directory selected. Use 'Open directory' first.")
        return False
    return True

def assembleEnvironment():
    global directory_to_work_with
    foldername = uuid.uuid4().hex
    parent = ask_for_directory()
    if not parent:
        print("No directory selected.")
        return False
    directory_to_work_with = os.path.normpath(os.path.join(parent, foldername))
    print("Setting target for downloads: {}".format(directory_to_work_with))
    if not os.path.exists(directory_to_work_with):
        os.makedirs(directory_to_work_with)
    gui_request("connection_label_change", "Session activated {}".format(foldername))
    return True

def takeoverEnvironment():
    global directory_to_work_with
    parent = ask_for_directory()
    if not parent:
        print("No directory selected.")
        return False
    directory_to_work_with = os.path.normpath(parent)
    foldername = os.path.basename(directory_to_work_with)
    print("Setting target for downloads: {}".format(directory_to_work_with))
    if not os.path.exists(directory_to_work_with):
        os.makedirs(directory_to_work_with)
    gui_request("connection_label_change", "Session activated {}".format(foldername))
    return True

def validate_response(valid_values, setting = "console"):
    while True:
        if setting == "console":
            print("Valid responses are:", '  '.join(valid_values))
        input_request_queue.put("Please enter your response:")
        response = input_response_queue.get()
        if setting == "input":
            return response
        if response in valid_values:
            return response
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
    with open(input_file, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        data = [row for row in reader if row['Transaction status'] == 'COMPLETED']
    if not data:
        print("No COMPLETED transactions found in expenses.csv - nothing to do.")
        return
    # Add 'Has Attachment' column
    for row in data:
        row['Attachment'] = has_attachment(row['Expense ID'])
        row['Import Text'] = join_strings(row['Transaction description'], row['Expense description'], row['Expense ID'])
        amount_raw = float(row['Amount (Payment currency)'] or 0)
        fee = float(row['Fee'] or 0)
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
    with open(input_file, mode='r', encoding='utf-8') as file:
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
                    "year": str(self.accountingYear),
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
        except Exception as e:
            print(f"Error occurred: {e}")
            return None

        print(response.status_code)
        if response.status_code in (200, 201):
            return enrichWithResponse(response.json())
        else:
            print(response.text)
            return f"Error: {response.status_code}"

def submitAttachment(url_input, filename):
    url = f'{url_input}/file'
    headers = fetchFromKeyring()

    with open(os.path.join(directory_to_work_with, filename), 'rb') as file:
        response = requests.post(url, headers=headers, files={'file': file})
    if response.status_code not in (200, 201):
        print(f"Failed to upload attachment {filename}: {response.status_code}")



# REVOLUT RUNTIME FUNCTIONS
def verifyData():
    if not require_working_directory():
        return False
    if settings is None:
        print("No settings loaded. Use 'Read settings file' first.")
        return False
    print(directory_to_work_with)
    process_expenses(directory_to_work_with)
    return True

def getSettings():
    global settings
    path = ask_for_file()
    if not path:
        print("No settings file selected.")
        return False
    with open(path, encoding='utf-8') as f:
        settings = json.load(f)
    print(f"Loaded settings from {path}")
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
    if not require_working_directory():
        return False
    if settings is None:
        print("No settings loaded. Use 'Read settings file' first.")
        return False
    data = readProcessedFiles()
    if not data:
        print("No processed expenses found. Use 'Prepare' first.")
        return False
    print(f'Ready to push {len(data)} rows of data to Economic.')
    selected_journal = selectJournal()
    a = JournalEntry(settings["accountingYear"], selected_journal)
    for line in data:
        a.new_voucher(line["Import Text"], line["Transaction started (UTC)"], line["Final Amount"], line["Expense category code"], line["EconomicContra"], line["Payment currency"], line["EconomicVAT"] )
    print("Starting to push!")
    translation_key = a.send_to_system()
    if not isinstance(translation_key, dict):
        print("Transfer failed - attachments were not uploaded.")
        return False
    #Transmitting attachments
    i = 0
    for line in data:
        i += 1
        if line["Attachment"] != "No":
            url = translation_key.get(line["Expense ID"])
            if url:
                submitAttachment(url, line["Attachment"])
            else:
                print(f"No voucher returned for {line['Expense ID']} - attachment skipped.")
        print(f"{i}/{len(data)}")
        gui_request("update_progress", 1/len(data)*0.995)
    return True

def sanitize_filename(name):
    """Replace characters that are not allowed in Windows filenames."""
    return re.sub(r'[<>:"/\\|?*]', '-', name)

def renameAll():
    if not require_working_directory():
        return False
    input_file = os.path.join(directory_to_work_with, 'processed_expenses.csv')

    try:
        with open(input_file, mode='r', encoding='utf-8') as file:
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

                if not(row['Attachment']) or len(row['Attachment'])<1 or row['Attachment']=="No":
                    continue

                original_file = os.path.join(directory_to_work_with, row['Attachment'])

                # Extracting file extension
                _, file_extension = os.path.splitext(original_file)

                # Constructing new filename with the original file extension
                new_filename = sanitize_filename(f"{account}_{date}_{amount}_{name}_{expense_id}") + file_extension

                # New file path
                new_file_path = os.path.join(directory_to_work_with, new_filename)

                # Renaming the file
                os.rename(original_file, new_file_path)
                print(f"Renamed {original_file} to {new_file_path}")
        return True

    except Exception as e:
        print(f"Error occurred: {e}")
        return False

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

if __name__ == "__main__":
    print("This module is not meant to be run directly. Run Main.py to launch the GUI.")
