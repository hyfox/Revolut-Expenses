import importlib, traceback
import Economic
import tkinter as tk
from tkinter import ttk
import threading, queue
from tkinter import scrolledtext, filedialog, Tk
from functools import partial
import sys
from datetime import datetime
from PIL import Image, ImageTk


result_queue = queue.Queue()  # Create a queue to store function results
gui_queue = queue.Queue()

gui_queue = Economic.set_gui_queue()
input_request_queue = Economic.create_request_queue()
input_response_queue = Economic.create_response_queue()

func_to_btn = {}  # To map function names to buttons
execution_lock = threading.Lock()  # The lock to ensure single function execution

Economic.input_request_queue = input_request_queue
Economic.input_response_queue = input_response_queue
directory_to_work_with =""

# Example imports. Replace these with your actual modules and function names.
# import app1
# import app2

def append_to_text_box(text):
    """Append text to the text box and scroll to the end."""
    text_box.insert(tk.END, text)
    text_box.see(tk.END)  # Scroll to the end

class StdoutRedirector(object):
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.insert(tk.END, string)
        self.text_space.see(tk.END)  # Scroll to the end

    def flush(self):
        pass  # This is a method stub, needed for some functionalities that expect it in sys.stdout.
    
    def readline(self):
        # Send an input request to the main thread
        input_request_queue.put(None)
        # Wait for a response from the main thread
        response = input_response_queue.get()
        # Return the response
        return response

def check_for_input():
    while not input_request_queue.empty():
        prompt = input_request_queue.get()
        append_to_text_box(prompt)  # Show prompt in the text box

        # Wait for the user's response from the input_field
        user_input = input_response_queue.get() 
        append_to_text_box(f"You entered: {user_input}\n")  # Optional: Display entered input
        
def execute_func(func, *args):
    def threaded_function(*args):
        try:
            with execution_lock:
                original_stdout = sys.stdout  # Store the original standard output
                sys.stdout = StdoutRedirector(text_box)  # Redirect standard output
                check_for_input()
                output = func(*args)
                sys.stdout = original_stdout  # Reset standard output to its original value
                result_queue.put((func.__name__, output))  # Put the result into the queue
                check_for_input()

        except ValueError as ve:
            error_message = f"ValueError: {str(ve)}\n"
            traceback_message = traceback.format_exc()
            append_to_text_box(error_message + traceback_message + '\n')
            result_queue.put((func.__name__, 'error'))
        except TypeError as te:
            error_message = f"TypeError: {str(te)}\n"
            traceback_message = traceback.format_exc()
            append_to_text_box(error_message + traceback_message + '\n')
            result_queue.put((func.__name__, 'error'))
        except IOError as ioe:
            error_message = f"IOError: {str(ioe)}\n"
            traceback_message = traceback.format_exc()
            append_to_text_box(error_message + traceback_message + '\n')
            result_queue.put((func.__name__, 'error'))
        except Exception as e:
            # Log the full traceback, including the line number
            error_message = f"Unexpected error: {str(e)}\n"
            traceback_message = traceback.format_exc()
            append_to_text_box(error_message + traceback_message + '\n')
            result_queue.put((func.__name__, 'error'))
        finally:
            for _, button in func_to_btn.items():  # Re-enable all the buttons after execution
                button.config(state=tk.NORMAL)
    
    for _, button in func_to_btn.items():  # Disable all buttons before execution
        button.config(state=tk.DISABLED)
    
    thread = threading.Thread(target=threaded_function, args=args)
    thread.start()


    

# Check the queue periodically and update the UI accordingly
def check_queue_update_ui():
    # Process the result_queue first
    while not result_queue.empty():
        func_name, status = result_queue.get()
        btn = func_to_btn.get(func_name)
        if btn:
            if status == True:
                btn.config(bg="green")
                append_to_text_box(f"{datetime.now()}: Success\n")
            elif status == 'error':
                btn.config(bg="red")
                append_to_text_box(f"{datetime.now()}: Failed\n")
            else:
                # Handle other statuses or leave as default
                pass

    # Process gui_queue
    while not gui_queue.empty():
        request = gui_queue.get()  # This is the dictionary containing the GUI request

        if request['label'] == 'ask_for_directory':
            try:
                directory = tk.filedialog.askdirectory()
                request['response'].put(directory)
            except Exception as e:
                request['response'].put(e)  # Send the exception back if necessary
                append_to_text_box(str(e) + '\n')
        elif request['label'] == 'ask_for_file':
            try:
                directory = tk.filedialog.askopenfilename()
                request['response'].put(directory)
            except Exception as e:
                request['response'].put(e)  # Send the exception back if necessary
                append_to_text_box(str(e) + '\n')
        elif request['label'] == 'ask_to_open_file':
            try:
                directory = tk.filedialog.askopenfile()
                request['response'].put(directory)
            except Exception as e:
                request['response'].put(e)  # Send the exception back if necessary
                append_to_text_box(str(e) + '\n')
        elif request['label'] == 'make_button_green':
            # Get the button's function name or ID from the request data, then find and modify the button
            btn_name = request['data']  # Assuming the data contains the button's function name or some identifier
            button = func_to_btn.get(btn_name)
            if button:
                button.config(bg="green")
                request['response'].put(True)  # Indicate success
            else:
                request['response'].put(False)  # Indicate failure if button not found
        elif request['label'] == 'connection_label_change':
            new_text = request.get('data', "NO SESSION IN PROGRESS")  # Default text if no data provided
            session_label.config(text=new_text)  # Update the session_label's text
            request['response'].put(True)  # Indicate success of the operation
        elif request['label'] == 'update_progress':
            # Get the button's function name or ID from the request data, then find and modify the button
            value = request['data']  # Assuming the data contains the button's function name or some identifier
            progressbar.step(value*100)
            request['response'].put(True)
            
    root.after(1000, check_queue_update_ui)  # Check every second TODO: hcek om dette er rigtigt

    
def execute():
    user_input = input_field.get()
    input_response_queue.put(user_input)  # Place the user's input into the input_response_queue
    #try:
        #output = eval(user_input)
        #append_to_text_box(str(user_input) + '\n' + str(output) + '\n')
    #except Exception as e:
        #append_to_text_box(str(e) + '\n')
    input_field.delete(0, tk.END)
    
def execute_func_with_logging(func, btn):
    btn.config(bg="yellow")
    append_to_text_box(f"{datetime.now()}: Executing {func.__name__}\n")
    result = execute_func(func)
    #if result is True:
    #    btn.config(bg="green")
    #    append_to_text_box(f"{datetime.now()}: Success\n")
    #else:
    #    btn.config(bg="red")
    #    append_to_text_box(f"{datetime.now()}: Failed\n")

root = tk.Tk()
root.title('Revolut to Economic')

# Left column for buttons
left_frame = tk.Frame(root, width=45)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)


# Right column for text box and input
right_frame = tk.Frame(root, width=55)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# Label at the top of the right_frame
session_label = tk.Label(right_frame, text="NO SESSION IN PROGRESS", font=("Arial", 12))
session_label.pack(pady=5)  # Pads the label vertically

# Add buttons to left column

def create_button_command(func, btn):
    return lambda: execute_func_with_logging(func, btn)

def justMakeAText():
    return True

def ReloadFileParser():
    importlib.reload(Economic)
    return True 

buttons_text_funcs = [
    ("Save credentials", Economic.storePasswords),
    ("Step 1 Gather Data", justMakeAText),
    ("Read settings file", Economic.getSettings), 
    ("Open directory", Economic.takeoverEnvironment), 
    ("Step 2 Analyze data", justMakeAText),
    ("Prepare", Economic.verifyData),
    ("Step 3 transmit", justMakeAText),
    ("!Run transfer!", Economic.ship), 
    ("Split files", Economic.renameAll), 
    ("Reload", ReloadFileParser),  # Modify accordingly
]

for btn_text, func in buttons_text_funcs:
    if func == justMakeAText:
        btn = tk.Label(left_frame, text=btn_text, height=2, width=15)
        btn.pack(pady=2)
    else:
        btn = tk.Button(left_frame, text=btn_text, height=2, width=15)
        btn['command'] = create_button_command(func, btn)
        btn.pack(pady=5)
        func_to_btn[func.__name__] = btn  # Store the function-button mapping

# Add text box and input field to right column
text_box = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD)
text_box.pack(pady=10, fill=tk.BOTH, expand=True)



input_field = tk.Entry(right_frame)
input_field.pack(pady=10, fill=tk.X)
input_field.bind('<Return>', lambda event=None: execute())

progressbar = ttk.Progressbar(right_frame)
progressbar.pack(pady=10, fill=tk.X)

root.after(1000, check_queue_update_ui)  # Start the periodic check after a second
root.mainloop() 