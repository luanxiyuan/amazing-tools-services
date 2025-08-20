"""
given the config file: ui_marker_config.json, pls
1. go through this config file, and iterate to the leaf node, get its applicationid, moduleid and function id
2.get all the folders under path /Users/xl52284/Documents/Tools/amazing-tools-services/static/ui_marker/[applicationid]/[moduleid]/[functionid], each folder is the pageid
3.get all the json files which name start with 'page_form_', read those files are storing json data as below format
{
  "page-desc": "Manage Payee - listing page",
  "page-view-type": "Web",
  "pageCtaControlInstance-0": "Loading",
  "pageUriControlInstance-0": "/config",
  "pageMethodControlInstance-0": "POST",
  "pageCtaControlInstance-1": "Loading",
  "pageUriControlInstance-1": "/ordercapture/applicationdate",
  "pageMethodControlInstance-1": "GET",
  "pageCtaControlInstance-2": "Loading",
  "pageUriControlInstance-2": "/managepayee/payees",
  "pageMethodControlInstance-2": "GET",
  "pageCtaControlInstance-3": "Loading",
  "pageUriControlInstance-3": "/ordercapture/memberdetails",
  "pageMethodControlInstance-3": "GET"
}
4. get the attribute value for field
    "page-desc", "page-view-type" and starts with 'pageUriControlInstance-' and 'pageMethodControlInstance-', then generate a json object with below format:
{
  "markerType": "Page", // hard code
  "appId": "GFT",
  "appName": "GFT",
  "moduleId": "gft-ui-manage-payees",
  "moduleName": "gft-ui-manage-payees",
  "funId": "manage-payees",
  "funName": "Manage Payees",
  "pageId": "page_20241023050104_mBEm2X",
  "pageDesc": "manage payee landing page",
  "pageUri": '/static/ui_marker/GFT/gft-ui-manage-payees/manage-payees/page_20241023050104_mBEm2X.png',
  "pageViewType": "Web",  // Web or Mobile, set to Web in case field "page-view-type" is empty
  "uri": "/common-mfa/token-details",
  "httpMethod": "POST",
  "scenario"： "When the page is [Loading]" // hard code as "When the page is [*]" based on field "pageCtaControlInstance-*" value
}
then put the above formatted data into an object with below format, then put in an array called page_data
{
    "file": json_file_name,
    "data": json data
}
5. get all the json files which name start with 'element_', read those files are storing json data as below format
{
  "ctaControlInstance-0": "Clicked",
  "uriControlInstance-0": "/common-mfa/token-details",
  "methodControlInstance-0": "POST",
  "ctaControlInstance-1": "Clicked",
  "uriControlInstance-1": "/transact/v1/saveMfaData",
  "methodControlInstance-1": "POST",
}
6. get the attribute value for field
    starts with 'pageUriControlInstance-' and 'pageMethodControlInstance-', then generate a json object with below format:
{
  "markerType": "Element", // hard code
  "appId": "GFT",
  "appName": "GFT",
  "moduleId": "gft-ui-manage-payees",
  "moduleName": "gft-ui-manage-payees",
  "funId": "manage-payees",
  "funName": "Manage Payees",
  "pageId": "page_20241023050104_mBEm2X",
  "pageDesc": "manage payee landing page",
  "pageUri": '/static/ui_marker/GFT/gft-ui-manage-payees/manage-payees/page_20241023050104_mBEm2X.png',
  "pageViewType": "Web",  // Web or Mobile, set to Web in case field "page-view-type" is empty
  "rectId": "rect_1728290462726" // current file name, remove prefix 'element_'
  "uri": "/common-mfa/token-details",
  "httpMethod": "POST",
  "scenario"： "When page's element is [Clicked]" // hard code as "When page's element is *" * is the value of field "ctaControlInstance-*"
}
then put the above formatted data into an object with below format, then put in an array called element_data
{
    "file": json_file_name,
    "data": json data
}
7. combine page_data and element_data, write them in a file called 'ui_api_relation_data.json' in the same directory
"""
import os
import json
import re
from datetime import datetime
import schedule
import time

from common_tools import file_tools
from consts.sys_constants import SysConstants
from engines.ui_marker import ui_marker_engine


def get_page_ids(base_path, application_id, module_id, function_id):
    path = os.path.join(base_path, application_id, module_id, function_id)
    if not os.path.exists(path):
        return []
    return [folder for folder in os.listdir(path) if os.path.isdir(os.path.join(path, folder))]


def read_json_files(base_path, application_id, module_id, function_id, page_id, prefix):
    path = os.path.join(base_path, application_id, module_id, function_id, page_id)
    json_files = [file for file in os.listdir(path) if file.startswith(prefix) and file.endswith('.json')]
    data = []
    for json_file in json_files:
        with open(os.path.join(path, json_file), 'r', encoding='utf-8') as file:
            data.append({
                "file": json_file,
                "data": json.load(file)
            })
            # data.append(json.load(file))
    return data


def extract_page_data(static_file_path, json_data, application_id, application_name, module_id, module_name, function_id, function_name, page_id):
    extracted_data = []
    for item in json_data:
        data = item['data']
        page_desc = data.get('page-desc', '')
        page_view_type = data.get('page-view-type', 'Web')
        uris = {k: v for k, v in data.items() if k.startswith('pageUriControlInstance-')}
        methods = {k: v for k, v in data.items() if k.startswith('pageMethodControlInstance-')}
        for key in uris:
            index = re.search(r'\d+', key).group()
            uri = uris[key]
            method = methods.get(f'pageMethodControlInstance-{index}', '')
            scenario = f"When the page is [{data.get(f'pageCtaControlInstance-{index}', '')}]"
            extracted_data.append({
                "markerType": "Page",
                "appId": application_id,
                "appName": application_name,
                "moduleId": module_id,
                "moduleName": module_name,
                "funId": function_id,
                "funName": function_name,
                "pageId": page_id,
                "pageDesc": page_desc,
                "pageUri": f"{static_file_path}/{application_id}/{module_id}/{function_id}/{page_id}.png",
                "pageViewType": page_view_type,
                "uri": uri,
                "httpMethod": method,
                "scenario": scenario
            })
    return extracted_data


def extract_element_data(static_file_path, json_data, application_id, application_name, module_id, module_name, function_id, function_name, page_id):
    extracted_data = []
    page_form_json_file_path = ui_marker_engine.get_page_details_file_path(application_id, module_id, function_id, page_id)
    form_details = file_tools.load_json(page_form_json_file_path)
    page_desc = form_details.get('page-desc', '')
    page_view_type = form_details.get('page-view-type', 'Web')

    for item in json_data:
        data = item['data']
        file_name = item['file']
        uris = {k: v for k, v in data.items() if k.startswith('uriControlInstance-')}
        methods = {k: v for k, v in data.items() if k.startswith('methodControlInstance-')}
        for key in uris:
            index = re.search(r'\d+', key).group()
            uri = uris[key]
            method = methods.get(f'methodControlInstance-{index}', '')
            scenario = f"When page's element is [{data.get(f'ctaControlInstance-{index}', '')}]"
            # rectId = file_name remove element prefix and file extension(.json)
            rectId = file_name.replace('element_', '').replace('.json', '')
            extracted_data.append({
                "markerType": "Element",
                "appId": application_id,
                "appName": application_name,
                "moduleId": module_id,
                "moduleName": module_name,
                "funId": function_id,
                "funName": function_name,
                "pageId": page_id,
                "pageDesc": page_desc,
                "pageUri": f"{static_file_path}/{application_id}/{module_id}/{function_id}/{page_id}.png",
                "pageViewType": page_view_type,
                "rectId": rectId,
                "uri": uri,
                "httpMethod": method,
                "scenario": scenario
            })
    return extracted_data


def generate_ui_api_relation_data():
    ui_marker_conf = file_tools.load_module_config_file(SysConstants.UI_MARKER.value)
    app_base_folder = SysConstants.PROJECT_BASE_PATH.value
    static_file_path = ui_marker_conf["image_upload_folder"]
    full_path = f'{app_base_folder}/{static_file_path}'
    applications = ui_marker_conf["applications"]
    page_data = []
    element_data = []

    for app in applications:
        application_id = app['id']
        application_name = app['name']
        for module in app['modules']:
            module_id = module['id']
            module_name = module['name']
            for function in module['functions']:
                function_id = function['id']
                function_name = function['name']
                page_ids = get_page_ids(full_path, application_id, module_id, function_id)
                for page_id in page_ids:
                    page_form_prefix = f"{SysConstants.UI_MARKER_PAGE_PREFIX.value}{SysConstants.UI_MARKER_FORM_PREFIX.value}"
                    json_data = read_json_files(full_path, application_id, module_id, function_id, page_id, page_form_prefix)
                    page_data.extend(extract_page_data(static_file_path, json_data, application_id, application_name, module_id, module_name, function_id, function_name, page_id))
                    element_prefix = SysConstants.UI_MARKER_ELEMENT_PREFIX.value
                    json_data = read_json_files(full_path, application_id, module_id, function_id, page_id, element_prefix)
                    element_data.extend(extract_element_data(static_file_path, json_data, application_id, application_name, module_id, module_name, function_id, function_name, page_id))

    output_data = page_data + element_data
    file_path = f'{full_path}/ui_api_relation_data.json'    # this file should be an existing one
    # write content to file
    with open(file_path, 'w', encoding='utf-8') as output_file:
        json.dump(output_data, output_file, indent=4)
        # print to console
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'ui_api_relation_data.json was generated at [{current_time}]')


def schedule_generate_ui_api_relation_data():
    schedule.every(60).minutes.do(generate_ui_api_relation_data)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    generate_ui_api_relation_data()