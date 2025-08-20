import json
import os
import shutil
import subprocess
from lxml import etree

import pandas
import zipfile

import common_tools.string_tools as string_tools
from consts.sys_constants import SysConstants


def is_file_exist(file_path):
    return os.path.exists(file_path)


def get_all_files_under_directory(directory_path):
    # exclude .DS_Store file
    return [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f)) and f != ".DS_Store"]


def load_json(path):
    # if the path is not a file
    if not os.path.isfile(path):
        print(f"{path} is not a file")
        return {}
    # if the file doesn't exit
    if not os.path.exists(path):
        print(f"{path} doesn't exist")
        return {}
    with open(path, encoding="utf8") as f:
        # try catch the exception when the file is empty
        try:
            return json.load(f)
        except Exception as e:
            print(f"{path} is empty")
            return {}


def load_module_config(module_name):
    with open(SysConstants.GLOBAL_CONFIG_FILE.value, encoding="utf8") as f:
        return json.load(f)[module_name]


def load_module_config_file(module_name: object) -> object:
    with open(SysConstants.GLOBAL_CONFIG_FILE.value, encoding="utf8") as f:
        file_content = f.read()
        project_base_path = SysConstants.PROJECT_BASE_PATH.value
        module_conf = json.loads(file_content)[module_name]
        module_conf_file_path = module_conf['config_file_path']
        return load_json(f'{project_base_path}/{module_conf_file_path}')


def delete_all_in_folder(folder_path):
    # if the folder exists, remove all the files and folders in the folder
    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                os.system("rm -rf " + file_path)
        print(f"all files and folders in {folder_path} have been removed")


def delete_file(file_path):
    # if the file exists, remove it
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"{file_path} has been removed")


def delete_folder(folder_path):
    # if the folder exists, remove it
    if os.path.exists(folder_path):
        os.system("rm -rf " + folder_path)
        print(f"{folder_path} has been removed")


# remove then create a folder, support both windows and mac
def create_module_directory(directory_path):
    if os.path.exists(directory_path):
        os.system("rm -rf " + directory_path)
    os.makedirs(directory_path)
    print(f"directory {directory_path} has been created")


def create_directory_without_remove(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"directory {directory_path} has been created")


def create_file(file, file_path, file_name):
    write_file = os.path.join(file_path, file_name)
    file.save(write_file)
    print()


def replace_existing_file(file, file_path, file_name):
    write_file = os.path.join(file_path, file_name)
    # if it's a file and exists
    if os.path.isfile(write_file):
        os.remove(write_file)
    file.save(write_file)
    print(f"{write_file} has been replaced")


def load_json_from_string(json_str):
    return json.loads(json_str)


def get_nesting_levels(d, level=0):
    if not isinstance(d, dict) or not d:
        return level
    return max(get_nesting_levels(v, level + 1) for v in d.values())


def check_and_format_json(source_json):
    # check if source_content is empty
    if not source_json:
        print("source content is empty")
        return {"status": SysConstants.STATUS_FAILED.value, "message": "source content is empty"}
    # check if source_content is a valid json
    try:
        target_json = load_json_from_string(source_json)
        return {"status": SysConstants.STATUS_SUCCESS.value, "message": target_json}
    except Exception as e:
        print("source content is not a valid json")
        return {"status": SysConstants.STATUS_FAILED.value, "message": "source content is not a valid json"}


def write_json_to_file(json_data, file_path):
    with open(file_path, 'w', encoding="utf8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"json content has been generated in file {file_path}")



# find the values in 1st column and the column_number column in the Excel file, and return as a dist
def get_excel_whole_column_values(xlsx_data, column_number):
    excel_value = {}
    for row in xlsx_data:
        column1 = string_tools.covert_2space_to_1space(string_tools.replace_invalid_space(row[0]))
        column2 = string_tools.covert_2space_to_1space(string_tools.replace_invalid_space(row[column_number]))
        excel_value.update({"{}".format(column1.strip()): "{}".format(str(column2.strip()))})
    return excel_value


def get_excel_whole_column_array_values(xlsx_data, column_number):
    excel_value = []
    for row in xlsx_data:
        column1 = string_tools.covert_2space_to_1space(string_tools.replace_invalid_space(row[0]))
        column2 = string_tools.covert_2space_to_1space(string_tools.replace_invalid_space(row[column_number]))
        excel_value.append({"source_content": "{}".format(column1.strip()), "target_content": "{}".format(str(column2.strip()))})
    return excel_value


def find_excel_all_eng_formatted_labels(xlsx_data):
    excel_labels = []
    for row in xlsx_data:
        excel_labels.append(string_tools.covert_2space_to_1space(string_tools.replace_invalid_space(row[0])).strip())
    return excel_labels


def read_xlsx_as_list(xlsx_path):
    data = pandas.read_excel(xlsx_path, sheet_name=0, keep_default_na=False)
    return data.values.tolist()


def find_biz_json(json_obj):
    if get_nesting_levels(json_obj) == 2:
        for key in json_obj:
            if key != "GFT_UI_CORE":
                return json_obj.get(key)


def zip_files(locale_file_paths, zip_file_path):
    # if zip_file_path exists, remove it
    if os.path.exists(zip_file_path):
        os.remove(zip_file_path)
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for file_path in locale_file_paths:
            # if this file doesn't exist, continue the next one
            if not os.path.exists(file_path):
                continue
            zipf.write(file_path, arcname=file_path.split('/')[-1])
    return zip_file_path


def verify_xsd(xsd_file, verify_empty_flg=True, verify_type_flg=True, verify_size_flg=False):
    if not is_valid_xsd(xsd_file):
        return SysConstants.MSG_INVALID_XSD_CONTENT.value
    if verify_empty_flg and xsd_file.filename == '':
        return SysConstants.MSG_XSD_IS_EMPTY.value
    if verify_type_flg and not verify_xsd_type(xsd_file):
        return SysConstants.MSG_INVALID_XSD_TYPE.value
    if verify_size_flg:
        xsd_file.seek(0, os.SEEK_END)  # Move to the end of the file to get its size
        if not verify_xsd_size(xsd_file):
            return SysConstants.MSG_INVALID_XSD_SIZE.value
        xsd_file.seek(0)  # Reset file pointer after reading
    return ""


def is_valid_xsd(xsd_file):
    try:
        # Parse the XSD file
        xsd_doc = etree.parse(xsd_file)
        # Try to create an XMLSchema object
        etree.XMLSchema(xsd_doc)
        return True
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
        print(f"XSD validation error: {e}")
        return False


def verify_xsd_type(xsd_file):
    content_type = xsd_file.filename.split('.')[-1]
    return content_type in ["xsd"]


def verify_xsd_size(xsd_file):
    return len(xsd_file.read()) <= SysConstants.XSD_MAX_SIZE.value


def convert_xsd_to_java(temp_dir, xsd_file, package_name, zip_file_name):
    # Check if xjc is installed
    if not shutil.which('xjc'):
        raise FileNotFoundError("The 'xjc' tool is not installed or not found in the system's PATH.")

    # remove all the files in the temp_dir
    delete_all_in_folder(temp_dir)

    # Create a temporary directory to store the XSD and generated Java files
    xsd_path = os.path.join(temp_dir, xsd_file.filename)
    xsd_file.save(xsd_path)

    # Generate Java files from the XSD file using xjc (XML Schema to Java compiler)
    if package_name:
        subprocess.run(['xjc', xsd_path, '-d', temp_dir, '-p', package_name], check=True)
    else:
        subprocess.run(['xjc', xsd_path, '-d', temp_dir], check=True)

    zip_path = os.path.join(temp_dir, zip_file_name)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.java'):
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))


def write_json_list_to_excel(json_list, file_path, header):
    # if json_list is empty, print log and return
    if not json_list:
        print("json_list is empty, not able to write to Excel file")
        return

    # Convert the list of JSON objects into a DataFrame
    df = pandas.DataFrame(json_list)

    # Set the DataFrame's columns to the provided header names
    df.columns = header

    # Write the DataFrame to an Excel file
    df.to_excel(file_path, index=False, header=True)


def is_windows():
    return os.name == 'nt'


def get_os_type():
    if is_windows():
        return {"osType": "Windows"}
    else:
        return {"osType": "MacOS"}


# write a function to get all the line of a file, and return a list of lines
def get_file_lines(file_path):
    with open(file_path, "r") as file:
        return file.readlines()