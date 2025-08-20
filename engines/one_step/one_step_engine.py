import os
import subprocess

from common_tools import file_tools
from consts.sys_constants import SysConstants
# from flask_socketio import SocketIO, emit


def get_command_sets():
    # get the json object from file /conf/one_step_config.json
    one_step_conf = file_tools.load_module_config_file(SysConstants.ONE_STEP.value)
    # get location file path from the json object, from field 'data_file_path'
    data_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{one_step_conf['data_file_path']}"
    # get the array from file data_file_path
    command_sets = file_tools.load_json(data_file_path)
    # command is with format as below, loop command_set, check if the port is in use, then add a new field called portStatus, with format [{"port": "4011", "isUseFlag": True/False}]
    # {
    #     "id": "246427eb1-2805-4202-9df3-516f1838f038",
    #     "name": "start web-borrow MBOL",
    #     "ports": ["4011"],
    #     "osType": "MacOS",
    #     "commands": [
    #         "cd /Users/xl52284/Documents/Odyssey/167407-web-borrow",
    #         "npm run start"
    #     ],
    #     "commandFile": "startChrome.sh"
    # }
    for command_set in command_sets:
        # read command file content
        command_file = command_set["commandFile"]
        command_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{SysConstants.ONE_STEP_CMD_FILE_PATH.value}/{command_file}"
        commands = file_tools.get_file_lines(command_file_path)
        command_set["commands"] = commands

        for port in command_set["ports"]:
            port_status = is_port_in_use(port)
            # push the object {"port": port, "isUseFlag": port_status} to command_set["portStatus"]
            curr_port_status = command_set.get("portStatus", [])
            curr_port_status.append({"port": port, "isInUseFlag": port_status})
            command_set["portStatus"] = curr_port_status

    # if not locations, return empty list
    if not command_sets:
        return []
    return command_sets


def is_port_in_use(port):
    try:
        if os.name == "nt":
            command = f"netstat -ano | findstr:{port}"
        else:
            command = f"lsof -i:{port}"
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        output, _ = process.communicate()
        in_use_flag = len(output.strip()) > 0
        if in_use_flag:
            print(f"Port {port} is in use.")
        else:
            print(f"Port {port} is not in use.")
        return in_use_flag
    except Exception as e:
        print(f"Failed to check port {port}: {e}")
        return False


def execute_command_set_via_file(command_set):
    # execute the commandFile
    command_file_name = command_set["commandFile"]
    command_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{SysConstants.ONE_STEP_CMD_FILE_PATH.value}/{command_file_name}"
    command_log_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{SysConstants.ONE_STEP_CMD_LOG_FILE_PATH.value}/{command_file_name}{'.log'}"

    try:
        execute_command_file(command_file_path, command_log_file_path)
    except Exception as e:
        print(f"Error in command: {e}")


# write a function to execute file command_file_path, and write the command log details to command_log_file_path
# for macos, execute the command in terminal with command 'sh command_file_path > command_log_file_path'
# for windows, execute the command in cmd with command 'cmd /c command_file_path > command_log_file_path'
# clear the log file before execute the command
def execute_command_file(command_file_path, command_log_file_path):
    try:
        # clear the log file
        clear_log_files(command_log_file_path)

        if os.name == "nt":
            command = f'cmd /c {command_file_path} > {command_log_file_path}'
        else:
            command = f'sh {command_file_path} > {command_log_file_path}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        process.wait()
    except Exception as e:
        print(f"Error in command: {e}")


# write a function to release some ports
# for macos, execute the command 'kill -9 $(lsof -i :port | grep LISTEN | awk '{print $2}')'
# for windows, execute the command 'taskkill /PID $(netstat -ano | findstr :port | awk '{print $5}') /F'
def release_port(command_set):
    # clear log file
    command_file_name = command_set["commandFile"]
    command_log_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{SysConstants.ONE_STEP_CMD_LOG_FILE_PATH.value}/{command_file_name}{'.log'}"
    clear_log_files(command_log_file_path)

    ports = command_set["ports"]
    for port in ports:
        try:
            if os.name == "nt":
                command = f'taskkill /PID $(netstat -ano | findstr:{port} | awk \'{{print $5}}\') /F'
            else:
                command = f'kill -9 $(lsof -i:{port} | grep LISTEN | awk \'{{print $2}}\')'
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
            process.wait()
        except Exception as e:
            print(f"Failed to release port {port}: {e}")


def get_execution_log(command_set):
    command_file_name = command_set["commandFile"]
    command_log_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{SysConstants.ONE_STEP_CMD_LOG_FILE_PATH.value}/{command_file_name}{'.log'}"
    try:
        with open(command_log_file_path, "r") as file:
            return file.read()
    except Exception as e:
        print(f"Failed to get execution log: {e}")
        return ""


def clear_log_files(command_log_file_path):
    # clear the log file
    with open(command_log_file_path, "w") as file:
        file.write("")