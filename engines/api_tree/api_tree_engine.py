import json
import pandas as pd
import logging
from collections import defaultdict

from common_tools import file_tools, string_tools
from werkzeug.utils import secure_filename
from consts.sys_constants import SysConstants

# Logger setup
logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler("app.log"),
    logging.StreamHandler()
])
log = logging.getLogger(__name__)


def get_open_apis():
    # get all apis
    apis = get_apis()
    # filter open APIs by classification
    open_apis = [api for api in apis if api["classification"] == SysConstants.API_TYPE_OPEN.value]
    return open_apis


def get_private_apis():
    # get all apis
    apis = get_apis()
    # filter open APIs by classification
    private_apis = [api for api in apis if api["classification"] == SysConstants.API_TYPE_PRIVATE.value]
    return private_apis


def get_apis():
    # get the api_tree module config
    api_tree_conf = file_tools.load_module_config_file("api_tree")
    # get the apis_file_path for update
    apis_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{api_tree_conf['apis_file_path']}"
    # get the json from apis_file_path, it's an array
    apis = file_tools.load_json(apis_file_path)
    # if not apis, return empty list
    if not apis:
        return []
    return apis


def add_open_apis(api_entities):
    # loop the api_entities, and add each api_entity by calling add_api
    for api_entity in api_entities:
        add_api(api_entity)


def add_api(api_entity):
    # get all open APIs
    apis = get_apis()

    # check if the api_entity is already in the apis identified by its uri and httpMethod
    is_exist = False

    for api in apis:
        if ((string_tools.exact_match_uri_with_variables(api_entity["uri"], api["uri"])) and
                (api["httpMethod"] == api_entity["httpMethod"])):
            is_exist = True
            break
    # if the api_entity is already in the apis, return error message
    if is_exist:
        formatted_message = string_tools.format_message(SysConstants.API_ALREADY_EXISTS.value,
                                                        api_entity["uri"],
                                                        api_entity["httpMethod"])
        return {"status": SysConstants.STATUS_FAILED.value, "message": formatted_message}

    api_entity["id"] = string_tools.generate_uuid()
    api_entity["createTime"] = string_tools.generate_create_time()
    # add the api_entity to the apis
    apis.append(api_entity)
    # save the apis to the apis_file_path
    return save_apis_to_file(apis)


def delete_api(api_id):
    # get all open APIs
    apis = get_apis()
    # filter the api by api_id
    apis = [api for api in apis if api["id"] != api_id]
    # if it's in the subIds, remove it from the subIds
    for api in apis:
        if api_id in api["subIds"]:
            api["subIds"].remove(api_id)
    # save the apis to the apis_file_path
    return save_apis_to_file(apis)


def update_api(api_entity):
    # get all open APIs
    apis = get_apis()
    # filter the api by api_id
    apis = [api for api in apis if api["id"] != api_entity["id"]]

    # add the api_entity to the apis
    apis.append(api_entity)
    # save the apis to the apis_file_path
    return save_apis_to_file(apis)


def update_sub_apis(id, subIds):
    # get all open APIs
    apis = get_apis()
    # convert subIds to array
    subIds = json.loads(subIds)
    # filter the api by api_id
    for api in apis:
        if api["id"] == id:
            api["subIds"] = subIds
            break
    # save the apis to the apis_file_path
    return save_apis_to_file(apis)


def delete_sub_api(id, subId):
    # get all open APIs
    apis = get_apis()
    # filter the api by api_id
    for api in apis:
        if api["id"] == id:
            if subId in api["subIds"]:
                api["subIds"].remove(subId)
            break
    # save the apis to the apis_file_path
    return save_apis_to_file(apis)


def save_apis_to_file(apis):
    # get the api_tree module config
    api_tree_conf = file_tools.load_module_config_file("api_tree")
    # get the apis_file_path for updating
    apis_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{api_tree_conf['apis_file_path']}"
    file_tools.write_json_to_file(apis, apis_file_path)
    return {"status": SysConstants.STATUS_SUCCESS.value}


def export_api_info_to_excel(excel_file_path, uri, uriSearchMode, httpMethod, classification, belongs_to_application,
                             channel, swagger_title, api_name):
    # get all open APIs
    all_apis = get_apis()
    # filter the api by
    #   uri(partially match ignore case, also need to consider the variables in uri),
    #   uriSearchMode (exact match or partial match),
    #   httpMethod(partially match ignore case),
    #   classification(partially match ignore case),
    #   belongs_to_application(partially match ignore case),
    #   channel(partially match ignore case),
    #   swagger_title(partially match ignore case),
    #   api_name(partially match ignore case),
    # if the parameter is empty, it will not be used to filter
    filtered_apis = []
    for api in all_apis:
        # exact match
        if uriSearchMode == SysConstants.API_URI_SEARCH_MODE_EXACT.value:
            # call string_tools.exact_match_uri_with_variables to check if the uri is exactly matched
            if ((string_tools.exact_match_uri_with_variables(uri, api["uri"])) and
                    (httpMethod.lower() in api["httpMethod"].lower() if httpMethod else True) and
                    (classification.lower() in api["classification"].lower() if classification else True) and
                    (belongs_to_application.lower() in api["belongsToApplication"].lower() if belongs_to_application else True) and
                    (channel.lower() in api["channel"].lower() if channel else True) and
                    (swagger_title.lower() in api["swaggerTitle"].lower() if swagger_title else True) and
                    (api_name.lower() in api["apiName"].lower() if api_name else True)):
                filtered_apis.append(api)
        # partial match
        else:
            # call string_tools.partial_match_uri_with_variables to check if the uri is partially matched
            if ((string_tools.partial_match_uri_with_variables(uri, api["uri"])) and
                    (httpMethod.lower() in api["httpMethod"].lower() if httpMethod else True) and
                    (classification.lower() in api["classification"].lower() if classification else True) and
                    (belongs_to_application.lower() in api["belongsToApplication"].lower() if belongs_to_application else True) and
                    (channel.lower() in api["channel"].lower() if channel else True) and
                    (swagger_title.lower() in api["swaggerTitle"].lower() if swagger_title else True) and
                    (api_name.lower() in api["apiName"].lower() if api_name else True)):
                filtered_apis.append(api)

    # sort the apis by createTime desc, make it align with UI
    filtered_apis = sorted(filtered_apis, key=lambda x: x["createTime"], reverse=True)
    # start to write apis into Excel
    # get the json object from file /conf/api_tree_config.json
    with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('APIs')

        # Add formats for the rows
        main_format = workbook.add_format({'bg_color': '#D7E4BC'})
        header_format = workbook.add_format({'bg_color': '#A9A9A9', 'bold': True})

        genarate_api_expended_excel(all_apis, filtered_apis, worksheet, main_format, header_format)


def genarate_api_expended_excel(all_apis, filtered_apis, worksheet, main_format, header_format):
    columns_order = [
        'uri', 'httpMethod', 'classification', 'belongsToApplication', 'channel',
        'swaggerTitle', 'serviceName', 'apiName', 'bianBehaviorQualifier', 'subQualifier',
        'bianAdoptionLevel', 'apiStatus', 'remark'
    ]

    column_headers = [
        'NO.', 'URI', 'Http Method', 'Classification', 'Belogs to Application', 'Channel',
        'Swagger Title', 'Service Name', 'API Name', 'BIAN Behavior Qualifier', 'Sub Qualifier',
        'BIAN Adoption Level', 'Status', 'Remark'
    ]

    column_widths = [
        5, 100, 15, 20, 25, 10, 30, 30, 30, 25, 20, 20, 10, 50
    ]

    # Write the header
    for col_num, (column, width) in enumerate(zip(column_headers, column_widths)):
        worksheet.write(0, col_num, column, header_format)
        worksheet.set_column(col_num, col_num, width)

    row_num = 1
    no_counter = 1
    for record in filtered_apis:
        # Write main record
        worksheet.write(row_num, 0, no_counter, main_format)
        for col_num, column in enumerate(columns_order, start=1):
            worksheet.write(row_num, col_num, record.get(column, ''), main_format)
        row_num += 1
        no_counter += 1

        # Write sub-records
        for sub_id in record.get('subIds', []):
            # get the subapi details
            sub_record = next((item for item in all_apis if item['id'] == sub_id), None)
            if sub_record:
                # clone the sub_record to avoid changing the original record
                temp_sub_record = sub_record.copy()
                # append 4 blanks before uri
                temp_sub_record['uri'] = '    ' + temp_sub_record['uri']
                for col_num, column in enumerate(columns_order, start=1):
                    worksheet.write(row_num, col_num, temp_sub_record.get(column, ''))
                # group the sub-records rows
                worksheet.set_row(row_num, None, None, {'level': 1, 'hidden': True})
                row_num += 1


def get_http_methods_by_uri(input_uri):
    # get all apis
    api_data = get_apis()

    uri_methods = defaultdict(list)
    normalized_input_uri = string_tools.normalize_uri(input_uri)

    for api in api_data:
        uri = api.get('uri')
        http_method = api.get('httpMethod')
        if uri and http_method:

            normalized_uri = string_tools.normalize_uri(uri)
            uri_methods[normalized_uri].append(http_method)

    return uri_methods.get(normalized_input_uri, [])
