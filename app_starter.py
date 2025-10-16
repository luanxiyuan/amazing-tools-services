import json
import logging
import threading

from flask import Flask, request, render_template, make_response, send_file, redirect, url_for, jsonify
from flask_cors import CORS

from consts.sys_constants import SysConstants
from engines.abbreviation import abbreviation_engine
from engines.api_tree import api_tree_engine
from engines.bb_contribution_analysis import bb_contribution_analysis_engine
from engines.contacts import contacts_engine
from engines.one_step import one_step_engine
from common_tools import file_tools, image_tools, ip_tools, string_tools
from engines.sql_generator import sql_generator_engine
from engines.ui_marker import ui_marker_engine
from jobs import ui_api_composer, cleaner_tools, bb_contribution_job

app = Flask(__name__)
CORS(app)   # enable CORS for all origins
# Logger setup
logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler("app.log"),
    logging.StreamHandler()
])
log = logging.getLogger(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


"""===========================UI Marker related functions start==========================="""


@app.route('/ui_marker/applications', methods=['GET'])
def ui_marker_appliations():
    # get all the applications from the configuration file
    applications = ui_marker_engine.get_applications()
    # return json format
    return jsonify(applications)


@app.route('/ui_marker/upload_image', methods=['POST'])
def upload_image():
    """This function is to receive the uploaded file and store in a folder, uri is '/ui_marker/upload-image'"""
    # get applicationId from request body
    application_id = request.form.get('applicationId')
    module_id = request.form.get('moduleId')
    function_id = request.form.get('functionId')
    image_file = request.files.get('image')

    image_verify_result = image_tools.verify_image(image_file)
    if image_verify_result:
        return jsonify({"message": image_verify_result}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    if not all([application_id, module_id, function_id]):
        return jsonify(
            {"message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    try:
        # generate unique id as file name
        new_image_file_name = string_tools.generate_image_file_id();
        uploaded_file_name = ui_marker_engine.add_page_image(application_id, module_id, function_id, image_file, new_image_file_name)
        if uploaded_file_name != '':
            log.info(
                f"[Uploaded Successful] Client address: [{ip_tools.get_ip_addr(request)}:{ip_tools.get_port(request)}] Uploaded image [{application_id}/{module_id}/{function_id}/{uploaded_file_name}]")
            return jsonify(
                {"message": SysConstants.MSG_IMAGE_UPLOAD_SUCCESSFUL.value,
                 "pageName": new_image_file_name}), SysConstants.HTTP_STATUS_OK.value
        else:
            log.info(
                f"[Failed to Upload] Client address: [{ip_tools.get_ip_addr(request)}:{ip_tools.get_port(request)}] tried to upload image to an invalid folder [{application_id}/{module_id}/{function_id}]")
            return jsonify({"message": uploaded_file_name}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    except Exception as e:
        log.error(str(e))
        return jsonify({"message": SysConstants.MSG_IMAGE_UPLOAD_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value

    return jsonify({"status": SysConstants.STATUS_SUCCESS.value})


@app.route('/ui_marker/replace_image', methods=['POST'])
def replace_image():
    """This function is to receive the uploaded file and store in a folder, uri is '/ui_marker/replace-image'"""
    # get applicationId from request body
    application_id = request.form.get('applicationId')
    module_id = request.form.get('moduleId')
    function_id = request.form.get('functionId')
    image_file = request.files.get('image')
    page_name = request.form.get('pageName')

    image_verify_result = image_tools.verify_image(image_file)
    if image_verify_result:
        return jsonify({"message": image_verify_result}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    if not all([application_id, module_id, function_id, page_name]):
        return jsonify(
            {"message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    try:
        # generate unique id as file name
        uploaded_file_name = ui_marker_engine.replace_page_image(application_id, module_id, function_id, image_file, page_name)
        if uploaded_file_name != '':
            log.info(
                f"[Replaced Successful] Client address: [{ip_tools.get_ip_addr(request)}:{ip_tools.get_port(request)}] Replaced image [{application_id}/{module_id}/{function_id}/{uploaded_file_name}]")
            return jsonify(
                {"message": SysConstants.MSG_IMAGE_UPLOAD_SUCCESSFUL.value}), SysConstants.HTTP_STATUS_OK.value
        else:
            log.info(
                f"[Replaced Failed] Client address: [{ip_tools.get_ip_addr(request)}:{ip_tools.get_port(request)}] tried to replace image to an invalid folder [{application_id}/{module_id}/{function_id}]")
            return jsonify({"message": uploaded_file_name}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    except Exception as e:
        log.error(str(e))
        return jsonify({"message": SysConstants.MSG_IMAGE_UPLOAD_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value

    return jsonify({"status": SysConstants.STATUS_SUCCESS.value})


@app.route('/ui_marker/pages', methods=['GET'])
def ui_marker_pages():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    if not all([application_id, module_id, function_id]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.get_function_pages(application_id, module_id, function_id)

    if isinstance(result, dict) and result["status"] == "failed":
        return jsonify(result), SysConstants.HTTP_STATUS_NO_CONTENT.value

    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/ui_marker/page', methods=['DELETE'])
def delete_page():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')

    if not all([application_id, module_id, function_id, page_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.delete_page(application_id, module_id, function_id, page_name)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_DELETE_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value


@app.route('/ui_marker/canvas_marker_details', methods=['POST'])
def add_page_canvas_marker_details():
    application_id = request.form.get('applicationId')
    module_id = request.form.get('moduleId')
    function_id = request.form.get('functionId')
    page_name = request.form.get('pageName')
    # get from canvasDetails wihch is json string
    canvas_marker_details = request.form.get('canvasMarkerDetails')

    if not all([application_id, module_id, function_id, page_name, canvas_marker_details]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.add_page_canvas_marker_details(application_id, module_id, function_id, page_name, canvas_marker_details)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_ADD_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value


@app.route('/ui_marker/canvas_marker_details', methods=['GET'])
def get_page_canvas_details():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')

    if not all([application_id, module_id, function_id, page_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.get_page_canvas_marker_details(application_id, module_id, function_id, page_name)

    if isinstance(result, dict) and result["status"] == "failed":
        return jsonify(result), SysConstants.HTTP_STATUS_NO_CONTENT.value

    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/ui_marker/canvas_marker_details', methods=['DELETE'])
def delete_page_canvas_marker_details():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')

    if not all([application_id, module_id, function_id, page_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.delete_page_canvas_marker_details(application_id, module_id, function_id, page_name)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_DELETE_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value


@app.route('/ui_marker/marker_form_details', methods=['POST'])
def add_element_form_details():
    application_id = request.form.get('applicationId')
    module_id = request.form.get('moduleId')
    function_id = request.form.get('functionId')
    page_name = request.form.get('pageName')
    rect_id = request.form.get('rectId')
    # get from formObj wihch is json string
    form_obj = request.form.get('formObj')

    if not all([application_id, module_id, function_id, page_name, rect_id, form_obj]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.add_element_form_details(application_id, module_id, function_id, page_name, rect_id, form_obj)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_ADD_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value


@app.route('/ui_marker/page_form_details', methods=['POST'])
def add_page_form_details():
    application_id = request.form.get('applicationId')
    module_id = request.form.get('moduleId')
    function_id = request.form.get('functionId')
    page_name = request.form.get('pageName')
    # get from formObj wihch is json string
    form_obj = request.form.get('formObj')

    if not all([application_id, module_id, function_id, page_name, form_obj]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.add_page_form_details(application_id, module_id, function_id, page_name, form_obj)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_ADD_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value



@app.route('/ui_marker/marker_form_details', methods=['GET'])
def get_element_form_details():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')
    rect_id = request.args.get('rectId')

    if not all([application_id, module_id, function_id, page_name, rect_id]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.get_element_form_details(application_id, module_id, function_id, page_name, rect_id)

    if isinstance(result, dict) and result["status"] == "failed":
        return jsonify(result), SysConstants.HTTP_STATUS_NO_CONTENT.value

    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/ui_marker/page_form_details', methods=['GET'])
def get_page_form_details():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')

    if not all([application_id, module_id, function_id, page_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.get_page_form_details(application_id, module_id, function_id, page_name)

    if isinstance(result, dict) and result["status"] == "failed":
        return jsonify(result), SysConstants.HTTP_STATUS_NO_CONTENT.value

    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/ui_marker/marker_form_details', methods=['DELETE'])
def delete_page_form_details():
    application_id = request.args.get('applicationId')
    module_id = request.args.get('moduleId')
    function_id = request.args.get('functionId')
    page_name = request.args.get('pageName')
    rect_id = request.args.get('rectId')

    if not all([application_id, module_id, function_id, page_name, rect_id]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    result = ui_marker_engine.delete_page_form_details(application_id, module_id, function_id, page_name, rect_id)

    if result:
        return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value
    else:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_DELETE_FAILED.value}), SysConstants.HTTP_STATUS_INTERNAL_SERVER_ERROR.value


"""===========================UI Marker related functions end==========================="""


"""===========================Contacts related functions start==========================="""
@app.route('/contacts/locations', methods=['GET'])
def get_locations():
    # call contacts_engine.get_locations() to get the locations
    result = contacts_engine.get_locations()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/contacts/persons', methods=['GET'])
def get_persons():
    # call contacts_engine.get_persons() to get the persons
    result = contacts_engine.get_persons()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/contacts/teams', methods=['GET'])
def get_teams():
    # call contacts_engine.get_teams() to get the teams
    result = contacts_engine.get_teams()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/contacts/teams', methods=['POST'])
def update_teams():
    # get the teams from request body
    teams = request.form.get('teams')
    # if teams is string, parst it to json
    if isinstance(teams, str):
        teams = json.loads(teams)
    # call contacts_engine.update_teams(teams) to update the teams
    contacts_engine.update_teams(teams)
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


@app.route('/contacts/persons', methods=['POST'])
def update_persons():
    # get the persons from request body
    persons = request.form.get('persons')
    # if teams is string, parst it to json
    if isinstance(persons, str):
        persons = json.loads(persons)
    # call contacts_engine.update_persons(persons) to update the persons
    contacts_engine.update_persons(persons)
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


@app.route('/contacts/persons/excel', methods=['GET'])
def export_person_info_to_excel():
    # call contacts_engine.export_person_info_to_excel() to export the person info to excel
    contacts_engine.export_person_info_to_excel()
    # download the file
    person_excel_file_path = file_tools.load_module_config_file("contacts")["person_excel_file_path"]
    return send_file(person_excel_file_path, as_attachment=True)


"""===========================Contacts related functions end==========================="""


"""===========================Abbreviation related functions end==========================="""


@app.route('/abbreviations', methods=['GET'])
def get_abbreviations():
    # call abbreviation_engine.get_abbreviations() to get the abbreviations
    result = abbreviation_engine.get_abbreviations()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/abbreviations', methods=['POST'])
def update_abbreviations():
    # get the abbreviations from request body
    abbreviations = request.form.get('abbreviations')
    # if abbreviations is string, parst it to json
    if isinstance(abbreviations, str):
        abbreviations = json.loads(abbreviations)
    # call abbreviation_engine.update_abbreviations(abbreviations) to update the abbreviations
    abbreviation_engine.update_abbreviations(abbreviations)
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


"""===========================Abbreviation related functions end==========================="""


"""===========================xsd converter related functions start==========================="""


@app.route('/convert_xsd_to_java', methods=['POST'])
def convert_xsd_to_java():
    xsd_file = request.files.get('file')
    package_name = request.form.get('packageName')

    xsd_verify_result = file_tools.verify_xsd(xsd_file)
    if xsd_verify_result:
        return jsonify({"message": xsd_verify_result}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    # generate the java file
    temp_dir = SysConstants.XSD_CONVERTER_PATH.value
    # Create a zip file of the generated Java files
    zip_file_name = f"{string_tools.generate_uuid()}.zip"
    file_tools.convert_xsd_to_java(temp_dir, xsd_file, package_name, zip_file_name)

    return jsonify({"message": SysConstants.MSG_XSD_UPLOAD_SUCCESSFUL.value,
                    "downloadFileName": zip_file_name}), SysConstants.HTTP_STATUS_OK.value


@app.route('/download_xsd_java_file', methods=['GET'])
def download_xsd_java_file():
    file_name = request.args.get('fileName')
    temp_dir = SysConstants.XSD_CONVERTER_PATH.value
    # return the zip file for downloading
    zip_path = f"{temp_dir}/{file_name}"
    return send_file(zip_path, as_attachment=True)


"""===========================xsd converter related functions end==========================="""


"""===========================Swagger Viewer related functions start==========================="""


@app.route('/swagger_viewer/vscode_plugin', methods=['GET'])
def download_vscode_plugin():
    # get the swagger_viewer module config
    swagger_viewer_conf = file_tools.load_module_config_file("swagger_viewer")
    # get the config value plugin_file_path
    plugin_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{swagger_viewer_conf['plugin_file_path']}"
    # return for downloading
    return send_file(plugin_file_path, as_attachment=True)


"""===========================Swagger Viewer related functions start==========================="""


"""===========================API Tree related functions start==========================="""


@app.route('/api_tree/open_apis', methods=['GET'])
def get_open_apis():
    # call api_tree_engine.get_open_apis() to get the open apis
    result = api_tree_engine.get_open_apis()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/open_apis', methods=['POST'])
def add_open_apis():
    # get the open_apis from request body
    open_apis = request.form.get('api_entities')
    # if open_apis is string, parst it to json
    if isinstance(open_apis, str):
        open_apis = json.loads(open_apis)
    # call api_tree_engine.add_open_apis(open_apis) to add the open apis
    api_tree_engine.add_open_apis(open_apis)
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/apis', methods=['GET'])
def get_apis():
    result = api_tree_engine.get_apis()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/private_apis', methods=['GET'])
def get_private_api_by_open_api_id():
    # get the open_api_id from request param
    open_api_id = request.args.get('openApiId')
    # if open_api_id is null, return the error message
    if open_api_id is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value


@app.route('/api_tree/api', methods=['POST'])
def add_api():
    # get the api_entity from request body
    api_entity = request.form.get('api_entity')
    # if api_entity is string, parst it to json
    if isinstance(api_entity, str):
        api_entity = json.loads(api_entity)
    # if api_entity is null, return the error message
    if api_entity is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    add_result = api_tree_engine.add_api(api_entity);
    if (add_result["status"] == "failed"):
        return jsonify(add_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(add_result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/api', methods=['DELETE'])
def delete_api():
    # get the param id from query param
    id = request.args.get('id')
    # if id is null, return the error message
    if id is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    delete_result = api_tree_engine.delete_api(id)
    if delete_result["status"] == "failed":
        return jsonify(delete_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(delete_result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/api', methods=['PUT'])
def update_api():
    # get the api_entity from request body
    api_entity = request.form.get('api_entity')
    # if api_entity is string, parst it to json
    if isinstance(api_entity, str):
        api_entity = json.loads(api_entity)
    # if api_entity is null, return the error message
    if api_entity is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    update_result = api_tree_engine.update_api(api_entity);
    if update_result["status"] == "failed":
        return jsonify(update_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(update_result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/sub_api_ids', methods=['PUT'])
def update_sub_apis():
    # get the id and subIds from request body
    id = request.form.get('id')
    sub_ids = request.form.get('subIds')
    # if id is null, return the error message
    if id is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    update_result = api_tree_engine.update_sub_apis(id, sub_ids);
    if update_result["status"] == "failed":
        return jsonify(update_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(update_result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/sub_api', methods=['DELETE'])
def delete_sub_api():
    # get the param id from query param
    id = request.args.get('id')
    sub_id = request.args.get('subId')
    # if id is null, return the error message
    if id is None or sub_id is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    delete_result = api_tree_engine.delete_sub_api(id, sub_id)
    if delete_result["status"] == "failed":
        return jsonify(delete_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(delete_result), SysConstants.HTTP_STATUS_OK.value


@app.route('/api_tree/apis/excel', methods=['GET'])
def export_api_info_to_excel():
    # get the query params uri, httpMethod, classification, belongsToApplication, channel, swaggerTitle, apiName
    uri = request.args.get('uri')
    uriSearchMode = request.args.get('uriSearchMode')
    http_method = request.args.get('httpMethod')
    classification = request.args.get('classification')
    belongs_to_application = request.args.get('belongsToApplication')
    channel = request.args.get('channel')
    swagger_title = request.args.get('swaggerTitle')
    api_name = request.args.get('apiName')
    # export the api info to excel
    apis_excel_file_path = file_tools.load_module_config_file(SysConstants.API_TREE.value)["api_excel_file_path"]
    apis_excel_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{apis_excel_file_path}"
    api_tree_engine.export_api_info_to_excel(apis_excel_file_path, uri, uriSearchMode, http_method, classification, belongs_to_application, channel, swagger_title, api_name)
    # download the Excel file
    return send_file(apis_excel_file_path, as_attachment=True)


@app.route('/ui_marker/ui_api_relation', methods=['GET'])
def get_ui_api_relation():
    # get the request param uri and httpMethod
    uri = request.args.get('uri')
    http_method = request.args.get('httpMethod')
    # if uri or httpMethod is null, return the error message
    if uri is None or http_method is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value, "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    # get the ui api relation
    result = ui_marker_engine.get_ui_api_relation(uri, http_method)
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


"""===========================API Tree related functions end==========================="""


"""===========================BB Contribution related functions start==========================="""


# write a rest function with uri /bb_contribution/commit_list, to get all the commit list
# request params are soeids(devided by comma), start_date, end_date, only_default_branch
@app.route('/bb_contribution/commit_list', methods=['GET'])
def get_commit_list():
    # get the request params soeids, start_date, end_date, remove the blanks in the string
    soeids = request.args.get('soeids')
    soeids = soeids.replace(" ", "") if soeids is not None else None
    # convert soeids to array if not empty, trim for each value after split
    soeids = soeids.split(',') if soeids is not None else []
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    only_default_branch = request.args.get('only_default_branch')
    only_default_branch = True if only_default_branch == "true" else False
    # call bb_contribution_engine.get_commit_list() to get the commit list
    result = bb_contribution_analysis_engine.filter_commits_by_soeid_and_date(soeids, start_date, end_date, only_default_branch)
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


# write a rest function with uri '/bb_contribution/commit_list/excel', to export the commit list to excel
# request params are soeids(devided by comma), start_date, end_date
@app.route('/bb_contribution/commit_list/excel', methods=['GET'])
def export_commit_list_to_excel():
    # get the request params soeids, start_date, end_date, remove the blanks in the string
    soeids = request.args.get('soeids')
    soeids = soeids.replace(" ", "") if soeids is not None else None
    # convert soeids to array if not empty, trim for each value after split
    soeids = soeids.split(',') if soeids is not None else []
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    only_default_branch = request.args.get('only_default_branch')
    only_default_branch = True if only_default_branch == "true" else False
    # export the commit list to excel
    temp_filtered_commits_excel_path = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)["temp_filtered_commits_excel_path"]
    temp_filtered_commits_excel_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{temp_filtered_commits_excel_path}"
    export_result = bb_contribution_analysis_engine.export_commit_list_to_excel(soeids, start_date, end_date, only_default_branch)
    if export_result["status"] == SysConstants.STATUS_FAILED.value:
        return jsonify(export_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    # download the Excel file
    return send_file(temp_filtered_commits_excel_path, as_attachment=True)


# write a function with uri '/bb_contribution/commit_list/refresh', to refresh the commit list
@app.route('/bb_contribution/commit_list/refresh', methods=['GET'])
def refresh_commit_list():
    # no waiting above execution, return directly
    # Start the long-running function in a separate thread
    thread = threading.Thread(target=refresh_commit_list_thread)
    thread.start()

    return jsonify({"status": SysConstants.STATUS_SUCCESS.value, "result": "refreshing, please wait for about 10 minutes"}), SysConstants.HTTP_STATUS_OK.value


def refresh_commit_list_thread():
    # refresh the commit list
    bb_contribution_analysis_engine.load_commits_for_all_repos()


# write a function with uri '/bb_contribution/commit_list/refresh_info', to get the refresh info
@app.route('/bb_contribution/commit_list/refresh_info', methods=['GET'])
def get_refresh_info():
    # get the refresh info
    result = bb_contribution_analysis_engine.get_refresh_info()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


# write a function with uri '/bb_contribution/repo_links', to get the repo links
@app.route('/bb_contribution/repo_links', methods=['GET'])
def get_repo_links():
    # get the repo links
    result = bb_contribution_analysis_engine.get_repo_links()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


"""===========================BB Contribution related functions end==========================="""

"""===========================One Step related functions start==========================="""


# write a rest function with uri '/one_step/command_sets', to get all the command list
@app.route('/one_step/command_sets', methods=['GET'])
def get_command_sets():
    # call one_step_engine.get_command_sets() to get the command sets
    result = one_step_engine.get_command_sets()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value


@app.route('/one_step/execute_command_set', methods=['POST'])
def execute_command_set():
    """Start a new thread to execute commands."""
    command_set = request.form.get('command_set')

    # if command_set is string, parst it to json
    if isinstance(command_set, str):
        command_set = json.loads(command_set)

    # if command_set["commandFile"] is empty, return the error message
    if command_set is None or command_set["commandFile"] is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    thread = threading.Thread(target=one_step_engine.execute_command_set_via_file, args=(command_set,))
    thread.start()
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


# write a rest function with '/one_step/stop_process' to stop the process by ending the port
@app.route('/one_step/stop_process', methods=['POST'])
def stop_process():
    """Start a new thread to execute commands."""
    command_set = request.form.get('command_set')

    # if command_set is string, parst it to json
    if isinstance(command_set, str):
        command_set = json.loads(command_set)

    # get the ports from command_set
    ports = command_set["ports"]
    # if ports is null, return the error message
    if ports is None:
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    thread = threading.Thread(target=one_step_engine.release_port, args=(command_set,))
    thread.start()
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value}), SysConstants.HTTP_STATUS_OK.value


# write a rest function with '/one_step/view_execution_log' to get the execution log
@app.route('/one_step/view_execution_log', methods=['GET'])
def view_execution_log():
    """Get the execution log."""
    command_set = request.args.get('command_set')

    # if command_set is string, parst it to json
    if isinstance(command_set, str):
        command_set = json.loads(command_set)

    # get the log file from command_set
    log_file_content = one_step_engine.get_execution_log(command_set)
    return jsonify({"status": SysConstants.STATUS_SUCCESS.value, "logContent": log_file_content}), SysConstants.HTTP_STATUS_OK.value


"""===========================One Step related functions end==========================="""


"""===========================SQL generator related functions start==========================="""


# The function to get DB types
@app.route('/sql_generator/db_types', methods=['GET'])
def get_db_types():
    return jsonify(sql_generator_engine.get_supported_database_types()), SysConstants.HTTP_STATUS_OK.value


def get_db_param_names(request):
    dbType = request.json.get('dbType')
    host = request.json.get('host')
    port = request.json.get('port')
    database = request.json.get('database')
    username = request.json.get('username')
    password = request.json.get('password')
    return dbType, host, port, database, username, password


# The function to check if the DB connection is valid
@app.route('/sql_generator/check_db_connection', methods=['POST'])
def check_db_connection():
    dbType, host, port, database, username, password = get_db_param_names(request)

    if not all([dbType, host, port, database, username, password]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection_result = sql_generator_engine.check_db_connection(dbType, host, port, database, username, password)
    if connection_result["status"] == SysConstants.STATUS_FAILED.value:
        return jsonify(connection_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value
    else:
        return jsonify(connection_result), SysConstants.HTTP_STATUS_OK.value


# The function to get all the tables in the database
@app.route('/sql_generator/tables', methods=['POST'])
def get_tables():
    dbType, host, port, database, username, password = get_db_param_names(request)

    if not all([dbType, host, port, database, username, password]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection_result = sql_generator_engine.check_db_connection(dbType, host, port, database, username, password)
    if connection_result["status"] == SysConstants.STATUS_FAILED.value:
        return jsonify(connection_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection = sql_generator_engine.build_connection(dbType, host, port, database, username, password)
    tables_result = sql_generator_engine.get_table_list(connection)
    return jsonify(tables_result), SysConstants.HTTP_STATUS_OK.value


# The function to get all the columns in the table
@app.route('/sql_generator/table_columns', methods=['POST'])
def get_columns():
    dbType, host, port, database, username, password = get_db_param_names(request)
    table_name = request.json.get('tableName')

    if not all([dbType, host, port, database, username, password, table_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection_result = sql_generator_engine.check_db_connection(dbType, host, port, database, username, password)
    if connection_result["status"] == SysConstants.STATUS_FAILED.value:
        return jsonify(connection_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection = sql_generator_engine.build_connection(dbType, host, port, database, username, password)
    columns_result = sql_generator_engine.get_table_column_comments(connection, table_name)
    return jsonify(columns_result), SysConstants.HTTP_STATUS_OK.value


# The function to get the db promot information
@app.route('/sql_generator/db_prompts', methods=['POST'])
def get_db_prompts():
    dbType, host, port, database, username, password = get_db_param_names(request)
    table_name = request.json.get('tableNames')
    business_requirement = request.json.get('businessRequirement')
    operation_type = request.json.get('operationType')  # query / optimize
    existing_sql = request.json.get('existingSql')

    if not all([dbType, host, port, database, username, password, table_name]):
        return jsonify({"status": SysConstants.STATUS_FAILED.value,
                        "message": SysConstants.MSG_INVALID_PARAMETERS.value}), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection_result = sql_generator_engine.check_db_connection(dbType, host, port, database, username, password)
    if connection_result["status"] == SysConstants.STATUS_FAILED.value:
        return jsonify(connection_result), SysConstants.HTTP_STATUS_BAD_REQUEST.value

    connection = sql_generator_engine.build_connection(dbType, host, port, database, username, password)
    prompts_result = sql_generator_engine.generate_db_prompt(connection, table_name, operation_type, business_requirement, existing_sql)
    return jsonify(prompts_result), SysConstants.HTTP_STATUS_OK.value


"""===========================SQL generator related functions end==========================="""



"""===========================Common functions start==========================="""


@app.route('/common/os_type', methods=['GET'])
def get_os_type():
    # get the os type
    result = file_tools.get_os_type()
    return jsonify(result), SysConstants.HTTP_STATUS_OK.value

"""===========================Common functions end==========================="""


if __name__ == '__main__':
    with app.app_context():
        # Start the scheduling in a separate thread for cleaning temp files
        # schedule_thread = threading.Thread(target=cleaner_tools.schedule_file_removal)
        # schedule_thread.daemon = True
        # schedule_thread.start()

        # Start the scheduleing in a separate thread for generating ui_api_relation_data.json
        # schedule_thread = threading.Thread(target=ui_api_composer.schedule_generate_ui_api_relation_data)
        # schedule_thread.daemon = True
        # schedule_thread.start()

        # start the scheduler for refreshing commit list
        # schedule_thread = threading.Thread(target=bb_contribution_job.schedule_bb_contribution_refresh)
        # schedule_thread.daemon = True
        # schedule_thread.start()

        app.run(host='0.0.0.0', port=5000, debug=True)
