from common_tools import file_tools
from consts.sys_constants import SysConstants


def get_abbreviations():
    # get the json object from file /conf/contacts_config.json
    abbreviation_conf = file_tools.load_module_config_file(SysConstants.ABBREVIATION.value)
    # get location file path from the json object, from field 'location_file_path'
    data_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{abbreviation_conf['data_file_path']}"
    # get the array from file location_file_path
    abbreviations = file_tools.load_json(data_file_path)
    # if not locations, return empty list
    if not abbreviations:
        return []
    return abbreviations


def update_abbreviations(abbreviations):
    # get the json object from file /conf/contacts_config.json
    abbreviation_conf = file_tools.load_module_config_file(SysConstants.ABBREVIATION.value)
    # get team file path from the json object, from field 'team_file_path'
    data_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{abbreviation_conf['data_file_path']}"
    # write the array to file team_file_path
    file_tools.write_json_to_file(abbreviations, data_file_path)