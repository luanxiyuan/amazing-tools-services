import os
import logging

from common_tools import file_tools, string_tools
from werkzeug.utils import secure_filename
from consts.sys_constants import SysConstants


# Logger setup
logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler("app.log"),
    logging.StreamHandler()
])
log = logging.getLogger(__name__)

def get_applications():
    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    # get all the applications from the configuration file
    applications = ui_marker_conf["applications"]
    return applications


def get_modules_by_application(application_id):
    if application_id is None or application_id == "":
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Please input application name"}

    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    # get all the applications from the configuration file
    applications = ui_marker_conf["applications"]
    # get all the modules from application which has the same id as application_id
    modules = next((application["modules"] for application in applications if application["id"] == application_id), None)
    return modules


def get_functions_by_module(application_id, module_id):
    if application_id is None or application_id == "":
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Please input application name"}

    if module_id is None or module_id == "":
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Please input module name"}

    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    # get all the applications from the configuration file
    applications = ui_marker_conf["applications"]
    # get the modules from application which has the same id as application_id
    modules = next((application["modules"] for application in applications if application["id"] == application_id), None)
    # get all the functions from module which has the same id as module_id
    functions = next((module["functions"] for module in modules if module["id"] == module_id), None)
    return functions


def add_page_image(application_id, module_id, function_id, image_file, image_file_name):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return ''
    original_file_name = secure_filename(image_file.filename)
    extension_name = os.path.splitext(original_file_name)[1]

    image_path = get_function_page_path(application_id, module_id, function_id)
    file_tools.create_directory_without_remove(image_path)

    new_file_name = f"{image_file_name}{extension_name.lower()}"
    file_tools.create_file(image_file, image_path, new_file_name)
    return new_file_name


def replace_page_image(application_id, module_id, function_id, image_file, image_file_name):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return ''
    original_file_name = secure_filename(image_file.filename)
    extension_name = os.path.splitext(original_file_name)[1]

    image_path = get_function_page_path(application_id, module_id, function_id)

    new_file_name = f"{image_file_name}{extension_name.lower()}"
    file_tools.replace_existing_file(image_file, image_path, new_file_name)
    return new_file_name


def delete_page(application_id, module_id, function_id, image_file_name):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    image_path = get_function_page_path(application_id, module_id, function_id)
    # delete the image file
    file_tools.delete_file(os.path.join(image_path, image_file_name))
    # delete the corresponding marker folder
    page_folder_name = image_file_name.split(".")[0]
    file_tools.delete_folder(os.path.join(image_path, page_folder_name))
    return True


def get_function_pages(application_id, module_id, function_id):
    # get all the image file names from folder assets/images/ui_marker/{application_id}/{module_id}/{function_id}
    function_page_path = get_function_page_path(application_id, module_id, function_id)
    if not os.path.exists(function_page_path):
        return {"status": SysConstants.STATUS_FAILED.value, "message": "No image files found"}
    image_files = os.listdir(function_page_path)

    # get the image file path for UI display
    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    image_upload_folder = ui_marker_conf["image_upload_folder"]
    # verify the type of the files in image_files
    # only if the file is not a directory, add prefix image_upload_folder to each one in image_files, using string concatenation
    image_files = [f"{image_upload_folder}/{application_id}/{module_id}/{function_id}/{image_file}" for image_file in image_files if (not os.path.isdir(f"{function_page_path}/{image_file}") and not image_file.startswith('.'))]

    # get the image desc from {image_upload_folder}/{application_id}/{module_id}/{function_id}/{image_file}/page_form_{image_file}.json
    for image_file in image_files:
        page_name = image_file.split("/")[-1].split(".")[0]
        page_details_file = get_page_details_file_path(application_id, module_id, function_id, page_name)
        page_details = file_tools.load_json(page_details_file)
        # if page_details.page-desc is not empty
        page_desc = page_details.get("page-desc") or ''
        page_view_type = page_details.get("page-view-type") or ''
        scope_value= page_details.get("scope-value") or ''
        image_files[image_files.index(image_file)] = {"imageFileUri": image_file, "pageDesc": page_desc, "pageViewType": page_view_type, "scopeValue": scope_value}

    return {"status": SysConstants.STATUS_SUCCESS.value, "image_files": image_files}


def get_function_page_path(application_id, module_id, function_id):
    # get the function image path from the configuration file
    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    app_base_folder = SysConstants.PROJECT_BASE_PATH.value
    image_upload_folder = ui_marker_conf["image_upload_folder"]
    # if image_upload_folder starts with /, remove it
    if image_upload_folder.startswith("/"):
        image_upload_folder = image_upload_folder[1:]
    image_path = f"{app_base_folder}/{image_upload_folder}/{application_id}/{module_id}/{function_id}"
    return image_path


def get_page_details_path(application_id, module_id, function_id, page_name):
    # get the function page path from the configuration file
    function_page_path = get_function_page_path(application_id, module_id, function_id)
    page_details_path = f"{function_page_path}/{page_name}"
    return page_details_path


def pre_verify(application_id, module_id, function_id):
    # check if application exists and in the applications list in configuraiton file
    applications = get_applications()
    if not any(application["id"] == application_id for application in applications):
        log.warning(f"Invalid application name: {application_id}")
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Invalid application name"}

    # check if module exists and in the modules list in configuration file
    modules = get_modules_by_application(application_id)
    if not any(module["id"] == module_id for module in modules):
        log.warning(f"Invalid module name: {module_id}")
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Invalid module name"}

    # check if function exists and in the functions list in configuration file
    functions = get_functions_by_module(application_id, module_id)
    if not any(function["id"] == function_id for function in functions):
        log.warning(f"Invalid function name: {function_id}")
        return {"status": SysConstants.STATUS_FAILED.value, "message": "Invalid function name"}

    return {"status": SysConstants.STATUS_SUCCESS.value, "message": "Successful"}


def add_page_canvas_marker_details(application_id, module_id, function_id, page_name, canvas_marker_details):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    # get the function page path from the configuration file
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    page_canvas_marker_details_file = get_page_canvas_file_path(application_id, module_id, function_id, page_name)
    # create a directory for pate_details_path
    file_tools.create_directory_without_remove(page_details_path)
    canvas_marker_details_in_json = file_tools.load_json_from_string(canvas_marker_details)
    file_tools.write_json_to_file(canvas_marker_details_in_json, page_canvas_marker_details_file)
    return True


def get_page_canvas_file_path(application_id, module_id, function_id, page_name):
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    return f"{page_details_path}/{page_name}.json"


def get_element_details_file_path(application_id, module_id, function_id, page_name, rect_id):
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    return f"{page_details_path}/{SysConstants.UI_MARKER_ELEMENT_PREFIX.value}{rect_id}.json"


def get_page_details_file_path(application_id, module_id, function_id, page_name):
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    return f"{page_details_path}/{SysConstants.UI_MARKER_PAGE_PREFIX.value}{SysConstants.UI_MARKER_FORM_PREFIX.value}{page_name}.json"


def get_page_canvas_marker_details(application_id, module_id, function_id, page_name):
    # get the function page path from the configuration file
    page_canvas_marker_details_file = get_page_canvas_file_path(application_id, module_id, function_id, page_name)
    canvas_marker_details = file_tools.load_json(page_canvas_marker_details_file)
    if not canvas_marker_details:
        return {"status": SysConstants.STATUS_FAILED.value, "message": "No page details found"}
    return {"status": SysConstants.STATUS_SUCCESS.value, "canvasMarkerDetails": canvas_marker_details}


def delete_page_canvas_marker_details(application_id, module_id, function_id, page_name):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    # get the function page path from the configuration file
    page_canvas_marker_details_file = get_page_canvas_file_path(application_id, module_id, function_id, page_name)
    file_tools.delete_file(page_canvas_marker_details_file)
    return True


def add_element_form_details(application_id, module_id, function_id, page_name, rect_id, form_obj):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    # get the function page path from the configuration file
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    form_details_file = get_element_details_file_path(application_id, module_id, function_id, page_name, rect_id)
    # create a directory for pate_details_path
    file_tools.create_directory_without_remove(page_details_path)
    canvas_marker_details_in_json = file_tools.load_json_from_string(form_obj)
    file_tools.write_json_to_file(canvas_marker_details_in_json, form_details_file)
    return True


def add_page_form_details(application_id, module_id, function_id, page_name, form_obj):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    # get the function page path from the configuration file
    page_details_path = get_page_details_path(application_id, module_id, function_id, page_name)
    form_details_file = get_page_details_file_path(application_id, module_id, function_id, page_name)
    # create a directory for pate_details_path
    file_tools.create_directory_without_remove(page_details_path)
    canvas_marker_details_in_json = file_tools.load_json_from_string(form_obj)
    file_tools.write_json_to_file(canvas_marker_details_in_json, form_details_file)
    return True


def get_element_form_details(application_id, module_id, function_id, page_name, rect_id):
    # get the function page path from the configuration file
    form_details_file = get_element_details_file_path(application_id, module_id, function_id, page_name, rect_id)
    form_details = file_tools.load_json(form_details_file)
    if not form_details:
        return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": "NO_CONTENT"}
    return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": form_details}


def get_page_form_details(application_id, module_id, function_id, page_name):
    # get the function page form path from the configuration file
    page_details_form_path = get_page_details_file_path(application_id, module_id, function_id, page_name)
    form_details = file_tools.load_json(page_details_form_path)
    if not form_details:
        return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": "NO_CONTENT"}
    return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": form_details}


def delete_page_form_details(application_id, module_id, function_id, page_name, rect_id):
    verify_result = pre_verify(application_id, module_id, function_id)
    if verify_result["status"] == "failed":
        return False
    # get the function page path from the configuration file
    form_details_file = get_element_details_file_path(application_id, module_id, function_id, page_name, rect_id)
    file_tools.delete_file(form_details_file)
    return True


def get_ui_api_relation(uri, http_method):
    # Normalize the input URI
    normalized_input_uri = string_tools.normalize_uri(uri)

    # Get the relation data from ui_api_relation_data.json
    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    app_base_folder = SysConstants.PROJECT_BASE_PATH.value
    image_upload_folder = ui_marker_conf["image_upload_folder"]
    ui_api_relation_date_file = SysConstants.UI_MARKER_UI_API_RELATION_FILE.value
    ui_api_relation_data = file_tools.load_json(f'{app_base_folder}/{image_upload_folder}/{ui_api_relation_date_file}')

    # If no ui_api_relation_data, return empty list
    if not ui_api_relation_data:
        return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": []}

    # Filter the ui_api_relation_data by normalized URI and http_method
    ui_api_relation = [
        relation for relation in ui_api_relation_data
        if string_tools.normalize_uri(relation["uri"]) == normalized_input_uri and relation["httpMethod"].lower() == http_method.lower()
    ]

    if not ui_api_relation:
        return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": []}

    return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": ui_api_relation}