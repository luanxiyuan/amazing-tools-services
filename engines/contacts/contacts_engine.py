import json
import pandas as pd

from common_tools import file_tools
from consts.sys_constants import SysConstants


def get_locations():
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get location file path from the json object, from field 'location_file_path'
    location_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['location_file_path']}"
    # get the array from file location_file_path
    locations = file_tools.load_json(location_file_path)
    # if not locations, return empty list
    if not locations:
        return []
    return locations


def get_persons():
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get person file path from the json object, from field 'person_file_path'
    person_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['person_file_path']}"
    # get the array from file person_file_path
    persons = file_tools.load_json(person_file_path)
    # if not persons, return empty list
    if not persons:
        return []
    return persons


def get_teams():
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get team file path from the json object, from field 'team_file_path'
    team_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['team_file_path']}"
    # get the array from file team_file_path
    teams = file_tools.load_json(team_file_path)
    # if not teams, return empty list
    if not teams:
        return []
    return teams


def update_teams(teams):
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get team file path from the json object, from field 'team_file_path'
    team_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['team_file_path']}"
    # write the array to file team_file_path
    file_tools.write_json_to_file(teams, team_file_path)


def update_persons(persons):
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get person file path from the json object, from field 'person_file_path'
    person_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['person_file_path']}"
    # write the array to file person_file_path
    file_tools.write_json_to_file(persons, person_file_path)


def export_person_info_to_excel():
    # get the json object from file /conf/contacts_config.json
    contacts_conf = file_tools.load_module_config_file(SysConstants.CONTACTS.value)
    # get person file path from the json object, from field 'person_file_path'
    person_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['person_file_path']}"
    # get location file path from the json object, from field 'location_file_path'
    location_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['location_file_path']}"
    # get team file path from the json object, from field 'team_file_path'
    team_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['team_file_path']}"

    # get the array from file person_file_path
    person_data = file_tools.load_json(person_file_path)
    # get the array from file location_file_path
    location_data = file_tools.load_json(location_file_path)
    # get the array from file team_file_path
    team_data = file_tools.load_json(team_file_path)

    # Convert JSON data to DataFrames
    person_df = pd.DataFrame(person_data)
    location_df = pd.DataFrame(location_data)
    team_df = pd.DataFrame(team_data)

    # Fill missing location and team values with a placeholder
    person_df = person_df.replace({'location': {'': ''}, 'team': {'': ''}})

    # Add placeholder entries to location and team DataFrames
    location_df = pd.concat([location_df, pd.DataFrame([{'id': '', 'name': ''}])], ignore_index=True)
    team_df = pd.concat([team_df, pd.DataFrame([{'id': '', 'name': '', 'remark': '', 'teamDl': ''}])],
                        ignore_index=True)

    # Merge person data with location and team information
    merged_df = person_df.merge(location_df, left_on='location', right_on='id', suffixes=('', '_location'))
    merged_df = merged_df.merge(team_df, left_on='team', right_on='id', suffixes=('', '_team'))

    # Select and rename columns for the final output
    final_df = merged_df[['soeId', 'name', 'name_location', 'remark', 'name_team', 'remark_team', 'teamDl']]
    final_df.columns = ['SOE ID', 'Name', 'Location Name', 'Remark', 'Team Name', 'Team Remark', 'Team DL']

    # Export to Excel
    person_excel_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{contacts_conf['person_excel_file_path']}"
    final_df.to_excel(person_excel_file_path, index=False)