import threading
import time
from datetime import datetime, timedelta

import pandas
import requests
from requests.auth import HTTPBasicAuth

from common_tools import file_tools
from consts.sys_constants import SysConstants


def getFromBB(url, username, app_password):
    # if this is windows, set verify as False
    if file_tools.is_windows():
        verify = False
        return requests.get(url, auth=HTTPBasicAuth(username, app_password), verify=verify)
    else:
        return requests.get(url, auth=HTTPBasicAuth(username, app_password))


# write a function to get the branches
def get_branches(base_url, project_key, repo_slug):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    username = bb_conf['bb_username']
    app_password = bb_conf['bb_password']
    branch_page_size = bb_conf['branch_page_size']
    # Bitbucket API endpoint to get branches
    branches_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/branches?limit={branch_page_size}'

    # Make the API request to get branches
    branches_response = getFromBB(branches_url, username, app_password)

    if branches_response.status_code == 200:
        return branches_response.json()
    else:
        # error log the branches_response as string
        print(f'Failed to retrieve branches: {branches_response.status_code}, {branches_response.content}')
        # retry maximum 3 times, until branches_response.status_code == 200
        for i in range(3):
            branches_response = getFromBB(branches_url, username, app_password)
            if branches_response.status_code == 200:
                return branches_response.json()
            else:
                print(f'Retry to fetch the branches - time {i}, Failed to retrieve branches: {branches_response.status_code}, {branches_response.content}')
        return {}


# write a function to get the soeids from excel file: /static/bb_contribution_analysis/bb_contribution_analysis_template.xlsx
# there're 2 columns "ID" and "Name", get the list of soeids from column "ID"
def get_soeids():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    soeids = []
    # get the xlsx data from file /static/bb_contribution_analysis/bb_contribution_analysis_template.xlsx
    xlsx_data = file_tools.read_xlsx_as_list(f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['contribution_excel_path']}")
    # inerate xlsx_data to get all the records in xlsx_data and put it into soeids
    for names in xlsx_data:
        soeid = names[0]
        soeids.append(soeid)
    return soeids


# write a function to remove the commit records which commit_time is not within start_time and end_time
def remove_commits_not_in_period(commit_records, start_time, end_time):
    if not commit_records or len(commit_records) == 0:
        return [], set()
    return [commit for commit in commit_records if under_period(commit['commit_time'], start_time, end_time)], set([commit['id'] for commit in commit_records])


def get_commits_under_repo_branches(repo_link, base_url, project_key, repo_slug, branches, start_time, end_time, default_branch, only_default_branch=False):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    username = bb_conf['bb_username']
    app_password = bb_conf['bb_password']
    commit_page_size = bb_conf['commit_page_size']
    # if default_branches has displayId, default_branch_name = default_branches['displayId']
    default_branch_name = default_branch['displayId'] if 'displayId' in default_branch else ''
    """
    this is the funtion to get all the commits under a repo and a branch
    1. get the commits under each branch which is under period and the maker soeid is in soeids
    commits format is like below
    {
        "values": [
            {
                "id": "5d399c1c80e40d2b2f3469bbe8ea64e5293ab190", // commit id
                "displayId": "5d399c1c80e", // display id
                "author": {
                    "name": "zw51552",      // maker soeid
                    "emailAddress": "zw51552@163.com",
                    "active": True,
                    "displayName": "Wu, Ziyan Zoey [TECH]",     // maker name
                    "id": 131320,
                    "slug": "zw51552",
                    "type": "NORMAL",
                    "links": {
                        "self": [
                            {
                                "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/zw51552"     // maker link
                            }
                        ]
                    }
                },
                "authorTimestamp": 1741059247000,       // commit time
                "committer": {
                    "name": "hz11172",    
                    "emailAddress": "hz11172@163.com",
                    "active": True,
                    "displayName": "Zhang, Hong Ming Thomas [LF-RB]",  
                    "id": 13963,
                    "slug": "hz11172",
                    "type": "NORMAL",
                    "links": {
                        "self": [
                            {
                                "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/hz11172"    
                            }
                        ]
                    }
                },
                "committerTimestamp": 1741059247000,
                "message": "Pull request #591: Master -> UAT\n\nMerge in GBMO/167407-web-borrow from master to UAT\n\n* commit "bd65122abf673b818351fc9117fa130a4f9d4142":\n  ACM-54538 | Borrow | Add sitecatalyst for PIL Xsell",
                "parents": [
                    {
                        "id": "e1045b61ff22f4c8583c70b68c672657b5e4eb59",
                        "displayId": "e1045b61ff2"
                    },
                    {
                        "id": "bd65122abf673b818351fc9117fa130a4f9d4142",
                        "displayId": "bd65122abf6"
                    }
                ],
                "properties": {
                    "jira-key": [
                        "ACM-54538"     // jira id
                    ]
                }
            }
        ],
        "size": 25,
        "isLastPage": False,        // if next page exists
        "start": 0,
        "limit": 25,
        "nextPageStart": 25         // next page start which is used when get next page of commits
    }
    if not able to filter the commit by soeid, then after we get the API response, filter the commits by each soeid in soeids === maker soeid
    2. combine all the commits in 1 list for all the branches
    3. the object of the list is like below
    {
        "branch": "master",
        "commits": [
            {
                "id": "5d399c1c80e40d2b2f3469bbe8ea64e5293ab190",
                "display_id": "5d399c1c80e",
                "commit_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/commits/5d399c1c80e40d2b2f3469bbe8ea64e5293ab190",
                "author": "Wu, Ziyan Zoey [TECH]",
                "author_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/zw51552",
                "commit_time": 1741059247000,
                "message": "Pull request #591: Master -> UAT\n\nMerge in GBMO/167407-web-borrow from master to UAT\n\n* commit "bd65122abf673b818351fc9117fa130a4f9d4142":\n  ACM-54538 | Borrow | Add sitecatalyst for PIL Xsell",
                "jira_ids": ["ACM-54538"],
                "branch": "master"
            }
        ]
    }
    """
    temp_file_path = ''
    # if only_default_branch,
    if only_default_branch:
        # if is_partial_repos, load the partial repos file, otherwise load all repos file
        is_partial_repos = bb_conf['is_partial_repos']
        temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_partial_contribution_file_path']}/{repo_slug}.json" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_all_contribution_file_path']}/{repo_slug}.json"
    else:
        # if is_partial_repos, load the partial repos file, otherwise load all repos file
        is_partial_repos = bb_conf['is_partial_repos']
        temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_contribution_file_path']}/{repo_slug}.json" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_contribution_file_path']}/{repo_slug}.json"

    all_commits = []

    # if the file exist, get the content and put it in all_commits
    if file_tools.is_file_exist(temp_file_path):
        all_commits = file_tools.load_json(temp_file_path)

    # remove expired commits
    all_commits, unique_commit_ids = remove_commits_not_in_period(all_commits, start_time, end_time)

    for branch in branches['values']:
        branch_name = branch['displayId']
        # Bitbucket API endpoint to get commits for each branch, and filter by period and soeid
        commits_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/commits?merges=exclude&until={branch_name}&limit={commit_page_size}'
        # Make the API request to get commits for the branch
        commits_response = getFromBB(commits_url, username, app_password)
        if commits_response.status_code == 200:
            commits = commits_response.json()
            formatted_commits, is_next_required = filter_and_reformat_commits(repo_link, branch_name, commits, start_time, end_time)
            # flat the formatted_commits in the list, avoid duplicate record by field "id"
            for commit in formatted_commits:
                # find the commit by field "id" in all_commits (existing commits)
                matched_commit = next((item for item in all_commits if item['id'] == commit['id']), None)
                # if matched_commit, and its field branch value != default_branch_name, update the branch value as branch_name
                if default_branch_name and matched_commit and matched_commit['branch'] != default_branch_name:
                    matched_commit['branch'] = branch_name
                    # replace it in all_commits
                    all_commits = [commit if commit['id'] == matched_commit['id'] else commit for commit in all_commits]
                    continue

                if commit['id'] not in unique_commit_ids:
                    unique_commit_ids.add(commit['id'])
                    all_commits.append(commit)

            # if not required to get next page, continue to next branch
            if not is_next_required:
                continue

            # Check if there is a next page of commits
            next_page_start = commits.get('nextPageStart', None)
            while next_page_start:
                # Bitbucket API endpoint to get next page of commits
                next_page_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/commits?exclude&until={branch_name}&limit={commit_page_size}&start={next_page_start}'
                # Make the API request to get the next page of commits
                next_page_response = getFromBB(next_page_url, username, app_password)
                if next_page_response.status_code == 200:
                    next_page_commits = next_page_response.json()
                    formatted_commits, is_next_required = filter_and_reformat_commits(repo_link, branch_name, next_page_commits, start_time, end_time)
                    # flat the formatted_commits in the list, avoid duplicate record by field "id"
                    for commit in formatted_commits:
                        # find the commit by field "id" in all_commits (existing commits)
                        matched_commit = next((item for item in all_commits if item['id'] == commit['id']), None)
                        # if matched_commit, and its field branch value != default_branch_name and != branch_name, update the branch value as branch_name
                        if default_branch_name and matched_commit and matched_commit['branch'] != default_branch_name and matched_commit['branch'] != branch_name:
                            matched_commit['branch'] = branch_name
                            # replace it in all_commits
                            all_commits = [commit if commit['id'] == matched_commit['id'] else commit for commit in all_commits]
                            continue

                        if commit['id'] not in unique_commit_ids:
                            unique_commit_ids.add(commit['id'])
                            all_commits.append(commit)

                    # if not required to get next page, break the loop
                    if not is_next_required:
                        break

                    # Check if there is a next page of commits
                    next_page_start = next_page_commits.get('nextPageStart', None)
                else:
                    print(f'Failed to retrieve next page of commits for branch {branch_name}: {next_page_response.status_code}')
                    break
        else:
            print(f'Failed to retrieve commits for branch {branch_name}: {commits_response.status_code}, {commits_response.content}')
            # Retry for 3 times, until commits_response.status_code == 200
            break

    # before writing the commits to a file: /static/bb_contribution_analysis/{repo_slug}.json, sort the commits by commit_time desc
    all_commits.sort(key=lambda x: x['commit_time'], reverse=True)
    file_tools.write_json_to_file(all_commits, temp_file_path)


# write a function to combine commit values, filtered by soeid in soeids === maker soeid
def filter_and_reformat_commits(repo_link, branch, commits, start_time, end_time):
    repo_link = repo_link.replace('/browse', '')
    formatted_commits = []
    is_next_required = True
    for commit in commits['values']:
        # if the commit time is not under the period, next page is not required, continue the next one, older commit record always at front
        if not under_period(commit['authorTimestamp'], start_time, end_time):
            is_next_required = False
            continue

        # if commit['author'] has no key 'displayName', that means user doesn't config git properly, ignore the commit
        if 'displayName' not in commit['author']:
            continue

        # if commit has no key 'properties', set jira_ids as []
        if 'properties' not in commit:
            commit['properties'] = {'jira-key': []}

        commit_data = {
            "id": commit['id'],
            "display_id": commit['displayId'],
            "commit_link": f"{repo_link}/commits/{commit['id']}",
            "author": commit['author']['displayName'],
            "author_link": commit['author']['links']['self'][0]['href'],
            "commit_time": datetime.fromtimestamp(commit['authorTimestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            "message": commit['message'],
            "jira_ids": commit['properties'].get('jira-key', []),
            "branch": branch
        }
        print(f'Commit: {commit_data["display_id"]} by {commit_data["author"]} on branch {branch}, commit time: {commit_data["commit_time"]}')
        formatted_commits.append(commit_data)
    return formatted_commits, is_next_required


def under_period(timestamp, start_time, end_time):
    # if timestamp is a number, commit_time = datetime.fromtimestamp(timestamp / 1000)
    # otherwise, commit_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    commit_time = datetime.fromtimestamp(timestamp / 1000) if isinstance(timestamp, int) else datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S') if isinstance(start_time, str) else start_time
    end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S') if isinstance(end_time, str) else end_time

    # Check if the commit_time is within the period
    return start_time <= commit_time <= end_time


def load_repos_from_bb():
    """ get the json object from file /conf/bb_contribution_analysis.json, with format as below
    {
        "repo_spaces": [
            {
                "name": "Consumer Banking - MBOL Repos",
                "base_url": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket",
                "project_key": "GBMO"
            }
        ]
        "bb_username": "xl52284",
        "bb_password": "***",
        "partial_repos_file_path": "/static/bb_contribution_analysis/bb_repo_links_partial.json",
        "all_repos_file_path": "/static/bb_contribution_analysis/bb_repo_links_all.json",
        "partial_contribution_file_path": "/static/bb_contribution_analysis/contribution_partial",
        "all_contribution_file_path": "/static/bb_contribution_analysis/contribution_all",
        "duration_by_days": 90
    }
    """
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    """ define a dict to store the repo links, with format as below
    {
        "project_key": ["repo_link1", "repo_link2", ...]
    }
    """
    bb_repo_links = {}
    username = bb_conf['bb_username']
    app_password = bb_conf['bb_password']
    repo_spaces = bb_conf['repo_spaces']
    # get the array from field 'repo_spaces', iterate each object and get its base_url and project_key
    for repo_space in repo_spaces:
        base_url = repo_space['base_url']
        project_key = repo_space['project_key']
        # Bitbucket API endpoint to get repositories under the specified project
        repos_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos?limit=1000'

        # Make the API request to get repositories
        repos_response = getFromBB(repos_url, username, app_password)

        if repos_response.status_code == 200:
            repos = repos_response.json()
            # get repos[].links.self[].href and put them into an array, then update it into bb_repo_links
            repo_links = [repo['links']['self'][0]['href'] for repo in repos['values']]
            bb_repo_links[project_key] = repo_links
            print(f'Loaded {len(repo_links)} repositories for project {project_key}')
        else:
            print(f'Failed to retrieve repositories: {repos_response.status_code}')
            return []

    # dump bb_repo_links into /static/bb_contribution_analysis/bb_repo_links.json
    # always generate the repos into all_repos_file_path
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_repos_file_path']}"
    file_tools.write_json_to_file(bb_repo_links, temp_file_path)


# write a function to get all the repo links from json file /static/bb_contribution_analysis/bb_repo_links.json
def get_flat_repo_links():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # if is_partial_repos, load the partial repos file, otherwise load all repos file
    is_partial_repos = bb_conf['is_partial_repos']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_repos_file_path']}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_repos_file_path']}"
    repo_links_data = file_tools.load_json(temp_file_path)
    # extract the urls
    return extract_urls(repo_links_data)


def extract_urls(json_data):
    urls = []
    for key, value in json_data.items():
        if isinstance(value, list):
            urls.extend(value)
    return urls


def get_tomorrow_midnight():
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    tomorrow_midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    return tomorrow_midnight


# write a function to get all the json files under /static/bb_contribution_analysis/contribution
def get_contribution_files():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # if is_partial_repos, load the partial repos file, otherwise load all repos file
    is_partial_repos = bb_conf['is_partial_repos']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_contribution_file_path']}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_contribution_file_path']}"
    return file_tools.get_all_files_under_directory(temp_file_path)


# write a function to filter the commits by soeid, and convert it into excel file
def convert_commits_to_excel(commit_records):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['temp_filtered_commits_excel_path']}"
    formatted_commit_records = []
    for commit in commit_records:
        repo_name = commit['commit_link'].split('repos/')[1].split('/commits')[0];
        formatted_commit = {
            "author": commit['author'],
            "display_id": commit['display_id'],
            "message": commit['message'],
            "repo_name": repo_name,
            "commit_time": commit['commit_time'],
            "branch": commit['branch'],
            "jira_ids": ', '.join(commit['jira_ids'])
        }
        formatted_commit_records.append(formatted_commit)
    """ write the commit_records into excel file, commit_records is a list with below format:
    [
      {
        "id": "d617c65928709c4a6a540c74f9078168ac1ae46d",
        "display_id": "d617c659287",
        "commit_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-android-capability-bot-protection/commits/d617c65928709c4a6a540c74f9078168ac1ae46d",
        "author": "Ning, Paris [TECH]",
        "author_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/cn58960",
        "commit_time": "2025-03-04 14:48:38",
        "message": "PBWD-14767 | Version 1.0.2",
        "jira_ids": [
          "PBWD-14767"
        ],
        "branch": "master"
      }
    ]
    """

    header = ['Commit', 'Author', 'Message', 'Repository Name', 'Commit Date & Time', 'Branch', 'Jira Link(s)']

    """ excel values should be generated as below:
    Commit: the value of display_id and by clicking on it, open commit_link in browser
    Author: the value of author and by clicking on it, open author_link in browser
    Message: the value of message
    Commit Date & Time: the value of commit_time
    Branch: the value of branch
    Jira Link(s): the value of jira_ids, if there're multiple jira_ids, separate them by comma
    """
    # Convert the list of JSON objects into a DataFrame
    df = pandas.DataFrame(formatted_commit_records)

    # Set the DataFrame's columns to the provided header names
    df.columns = header

    # Create a Pandas Excel writer using XlsxWriter as the engine
    writer = pandas.ExcelWriter(temp_file_path, engine='xlsxwriter')

    # Convert the DataFrame to an XlsxWriter Excel object
    df.to_excel(writer, index=False, header=True, sheet_name='Sheet1')

    # Get the XlsxWriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']

    # Set the column formats
    commit_format = workbook.add_format({'underline': True, 'align': 'left', 'valign': 'top'})
    author_format = workbook.add_format({'underline': True, 'align': 'left', 'valign': 'top'})
    message_format = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'top'})
    datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'align': 'left', 'valign': 'top'})
    branch_format = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'top'})
    jira_format = workbook.add_format({'text_wrap': True, 'align': 'left', 'valign': 'top'})

    # Apply the formats to the columns
    worksheet.set_column('A:A', 20, commit_format)
    worksheet.set_column('B:B', 20, author_format)
    worksheet.set_column('C:C', 50, message_format)
    worksheet.set_column('D:D', 20, datetime_format)
    worksheet.set_column('E:E', 20, branch_format)
    worksheet.set_column('F:F', 50, jira_format)

    # Add hyperlinks to the cells
    for row_num, row_data in enumerate(commit_records, start=1):
        worksheet.write_url(row_num, 0, row_data['commit_link'], commit_format, row_data['display_id'])
        worksheet.write_url(row_num, 1, row_data['author_link'], author_format, row_data['author'])

    # Close the Pandas Excel writer and output the Excel file
    writer.close()


def export_commit_list_to_excel(soeids, start_date, end_date, only_default_branch=False):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)

    # if start_date or end_date is None, set them as the min or max date
    if not start_date or not end_date:
        # set current day as end time, so we need to add 1 day to the end time
        end_date = get_tomorrow_midnight()
        # set start time as end_time - past_days
        start_date = end_date - timedelta(days=bb_conf['duration_by_days'])

    print(f"start to filter the commits by soeid {soeids} with Start time: {start_date}, End time: {end_date}")

    # iterate the files, and filter the commits by soeid
    commit_records = filter_commits(soeids, start_date, end_date, only_default_branch)

    # convert the commit_records into excel file if there're any records
    if commit_records:
        convert_commits_to_excel(commit_records)
        return {"status": SysConstants.STATUS_SUCCESS.value, "result": "excel generated successful"}
    else:
        return {"status": SysConstants.STATUS_FAILED.value, "result": "no record found"}


def filter_commits_by_soeid_and_date(soeids, start_date, end_date, only_default_branch=False):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)

    # if start_date or end_date is None, set them as the min or max date
    if not start_date or not end_date:
        # set current day as end time, so we need to add 1 day to the end time
        end_date = get_tomorrow_midnight()
        # set start time as end_time - past_days
        start_date = end_date - timedelta(days=bb_conf['duration_by_days'])

    print(f"start to filter the commits by soeid {soeids} with Start time: {start_date}, End time: {end_date}")

    # iterate the files, and filter the commits by soeid
    commit_records = filter_commits(soeids, start_date, end_date, only_default_branch)

    if not commit_records:
        return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": []}

    return {"status": SysConstants.STATUS_SUCCESS.value, "formDetails": commit_records}


def filter_commits(soeids, start_date, end_date, only_default_branch=False):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # get the json files under /static/bb_contribution_analysis/contribution
    is_partial_repos = bb_conf['is_partial_repos']
    files = get_contribution_files()

    # iterate the files, and filter the commits by soeid
    commit_records = []
    for file in files:
        file_path = ''
        # if only_default_branch, get the default branch file
        if only_default_branch:
            file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_partial_contribution_file_path']}/{file}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_all_contribution_file_path']}/{file}"
        else:
            file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_contribution_file_path']}/{file}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_contribution_file_path']}/{file}"
        # get the json object from file
        commits = file_tools.load_json(file_path)
        # filter the commits by soeid, author_link string includes soeid ignore case, if trimmed soeid is empty, skip it
        filtered_commits = [commit for commit in commits if any(soeid.lower() in commit['author_link'] for soeid in soeids if soeid.strip())]
        # filtered_commits = [commit for commit in commits if any(soeid.lower() in commit['author_link'] for soeid in soeids)]
        # filter the commits by commit_time
        filtered_commits = [commit for commit in filtered_commits if under_period(commit['commit_time'], start_date, end_date)]
        # update the filtered_commits into commit_records
        commit_records.extend(filtered_commits)
    # order the commit_records by commit_time desc
    commit_records.sort(key=lambda x: x['commit_time'], reverse=True)
    return commit_records


def process_repo_links(repo_links_subset, start_time, end_time):
    for repo_link in repo_links_subset:
        repo_slug = repo_link.split('repos/')[-1].split('/browse')[0]
        project_key = repo_link.split('projects/')[-1].split('/repos')[0]
        base_url = repo_link.split('/projects/')[0]
        branches = get_branches(base_url, project_key, repo_slug)

        # get the default branch for the repo
        default_branch = get_default_branch(base_url, project_key, repo_slug)

        if not default_branch:
            print(f"Default branch not found for repo {repo_slug}, skip to next repo")
            continue

        if default_branch:
            # deep clone branches to default_branches
            default_branches = {'values': [default_branch]}
            get_commits_under_repo_branches(repo_link, base_url, project_key, repo_slug, default_branches, start_time,
                                          end_time, default_branch, True)

        # if branches has no field 'values',continue
        if 'values' not in branches:
            print(f"Branches not found for repo {repo_slug}, skip to next repo")
            continue

        # if default branch is not in branches, add it into branches at the 1st position
        # else reposition the default branch to the 1st position
        if default_branch['displayId'] not in [branch['displayId'] for branch in branches['values']]:
            branches['values'].insert(0, default_branch)
        else:
            for i, branch in enumerate(branches['values']):
                if branch['displayId'] == default_branch['displayId']:
                    branches['values'].insert(0, branches['values'].pop(i))
                    break

        get_commits_under_repo_branches(repo_link, base_url, project_key, repo_slug, branches, start_time, end_time, default_branch, False)

    print(f"Finished loading commits for repo links subset: {repo_links_subset}")


# write a function to get the default branch for a repo
def get_default_branch(base_url, project_key, repo_slug):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    username = bb_conf['bb_username']
    app_password = bb_conf['bb_password']
    # Bitbucket API endpoint to get the default branch
    default_branch_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/branches/default'

    # Make the API request to get the default branch
    default_branch_response = getFromBB(default_branch_url, username, app_password)

    if default_branch_response.status_code == 200:
        default_branch = default_branch_response.json()
        return default_branch
    else:
        print(f'Failed to retrieve default branch: {default_branch_response.status_code}')
        # Retry for 3 times, until default_branch_response.status_code == 200
        for i in range(3):
            default_branch_response = getFromBB(default_branch_url, username, app_password)
            if default_branch_response.status_code == 200:
                return default_branch_response.json()
            else:
                print(f'Retry to fetch the default branch - time {i}, Failed to retrieve default branch: {default_branch_response.status_code}, {default_branch_response.content}')
        return {}


def load_commits_for_all_repos():
    # check and update the refresh info, if false, not allowed to get refresh
    result = update_refresh_info()
    if not result:
        return

    # get the repo links from json file
    repo_links = get_flat_repo_links()

    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    duration_by_days = bb_conf['duration_by_days']
    # set current day as end time, so we need to add 1 day to the end time
    end_time = get_tomorrow_midnight()
    # set start time as end_time - duration_by_days
    start_time = end_time - timedelta(days=duration_by_days)
    print(f"start to analysys the contribution with Start time: {start_time}, End time: {end_time}")

    # Split repo_links into multiple parts, run then in parallel for faster speed
    # if len(repo_links) is greater than 5, set it as 5
    num_threads = min(5, len(repo_links))
    repo_links_parts = [repo_links[i::num_threads] for i in range(num_threads)]

    # Create and start threads, each thread starts 1 second after previous one
    threads = []
    for i in range(num_threads):
        # sleep for 1 second before starting the next thread
        time.sleep(1)
        thread = threading.Thread(target=process_repo_links, args=(repo_links_parts[i], start_time, end_time))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # call update_commit_pr_details once all the commits are loaded
    print("All commits are loaded, start to update commit pr details using: update_commit_pr_details")
    update_commit_pr_details()


def is_allowed_to_refresh():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    allowed_refresh_interval_in_minute = bb_conf['allowed_refresh_interval_in_minute']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['loading_refresh_info_file_path']}"
    # get the json object from temp_file_path
    refresh_info = file_tools.load_json(temp_file_path)

    # get last update time and get current time, if the period is not greater than allowed_refresh_interval_in_minute, return
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    last_refresh_is_partial_repos = refresh_info['last_refresh_is_partial_repos']
    last_refresh_time = refresh_info['partial_last_refresh_time'] if last_refresh_is_partial_repos else refresh_info[
        'all_last_refresh_time']
    if last_refresh_time:
        last_refresh_time = datetime.strptime(last_refresh_time, '%Y-%m-%d %H:%M:%S')
        if (datetime.now() - last_refresh_time).seconds / 60 < allowed_refresh_interval_in_minute:
            print(f"Last refresh time is {last_refresh_time}, current time is {current_time}, not allowed to refresh")
            return False, refresh_info, current_time

    return True, refresh_info, current_time


# write a function to get current date with yyyy-MM-dd hh:mm:ss format, and write it in file /static/bb_contribution_analysis/loading_refresh_info.json
def update_refresh_info():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    duration_by_days = bb_conf['duration_by_days']
    branch_page_size = bb_conf['branch_page_size']
    allowed_refresh_interval_in_minute = bb_conf['allowed_refresh_interval_in_minute']
    is_allowed, refresh_info, current_time = is_allowed_to_refresh()
    if not is_allowed:
        return False

    is_partial_repos = bb_conf['is_partial_repos']
    refresh_info['duration_by_days'] = duration_by_days
    refresh_info['branch_page_size'] = branch_page_size
    refresh_info['allowed_refresh_interval_in_minute'] = allowed_refresh_interval_in_minute
    if is_partial_repos:
        refresh_info['partial_last_refresh_time'] = current_time
        refresh_info['last_refresh_is_partial_repos'] = True
    else:
        refresh_info['all_last_refresh_time'] = current_time
        refresh_info['last_refresh_is_partial_repos'] = False

    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['loading_refresh_info_file_path']}"
    file_tools.write_json_to_file(refresh_info, temp_file_path)
    return True


# write a function to load json from /static/bb_contribution_analysis/loading_refresh_info.json
def get_refresh_info():
    is_allowed, refresh_info, current_time = is_allowed_to_refresh()
    result = {
        "last_refresh_time": "",
        "is_allowed_to_refresh": is_allowed,
        "duration_by_days": refresh_info['duration_by_days'],
        "branch_page_size": refresh_info['branch_page_size'],
        "allowed_refresh_interval_in_minute": refresh_info['allowed_refresh_interval_in_minute'],
    }
    # if refresh_info.last_refresh_is_partial_repos, get partial_last_refresh_time, otherwise get all_last_refresh_time
    last_refresh_time = refresh_info['partial_last_refresh_time'] if refresh_info['last_refresh_is_partial_repos'] else refresh_info['all_last_refresh_time']
    result['last_refresh_time'] = last_refresh_time

    return {"status": SysConstants.STATUS_SUCCESS.value, "result": result}


# write a function to load json from /static/bb_contribution_analysis/bb_repo_links.json
def get_repo_links():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # if is_partial_repos, load the partial repos file, otherwise load all repos file
    is_partial_repos = bb_conf['is_partial_repos']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_repos_file_path']}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_repos_file_path']}"
    return {"status": SysConstants.STATUS_SUCCESS.value, "result": file_tools.load_json(temp_file_path)}


def get_pull_request_details(base_url, project_key, repo_slug, commit_id):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    username = bb_conf['bb_username']
    app_password = bb_conf['bb_password']

    # Bitbucket API endpoint to get pull request details for a specific commit
    pull_requests_url = f'{base_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/commits/{commit_id}/pull-requests'

    # Make the API request to get pull request details
    pull_requests_response = getFromBB(pull_requests_url, username, app_password)

    if pull_requests_response.status_code == 200:
        pr_response = pull_requests_response.json()
        """
        pr_response format is as below:
        {
            "size": 3,
            "limit": 25,
            "isLastPage": true,
            "values": [
                {
                    "id": 581,      // id
                    "version": 2,       // title
                    "title": "M2 Code Copy | staging to PROD",
                    "description": "Code copy",
                    "state": "MERGED",
                    "open": false,
                    "closed": true,
                    "draft": false,
                    "createdDate": 1740029482035,
                    "updatedDate": 1740037190895,
                    "closedDate": 1740037190895,
                    "fromRef": {
                        "id": "refs/heads/staging",
                        "displayId": "staging",     // from_branch
                        "latestCommit": "900993bdbafec71c42f7ebb0a1213d070f057344",
                        "type": "BRANCH",
                        "repository": {
                            "slug": "167407-web-borrow",
                            "id": 86505,
                            "name": "167407-web-borrow",
                            "description": "Repo name is changes as per REQU0012087476",
                            "hierarchyId": "907479e31837038b5a64",
                            "scmId": "git",
                            "state": "AVAILABLE",
                            "statusMessage": "Available",
                            "forkable": true,
                            "project": {
                                "key": "GBMO",
                                "id": 1282,
                                "name": "147634-GBMO",
                                "description": "GC Global Mobile",
                                "public": false,
                                "type": "NORMAL",
                                "links": {
                                    "self": [
                                        {
                                            "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO"
                                        }
                                    ]
                                }
                            },
                            "public": false,
                            "archived": false,
                            "links": {
                                "clone": [
                                    {
                                        "href": "ssh://git@cedt-gct-bitbucketcli.nam.nsroot.net:7999/gbmo/167407-web-borrow.git",
                                        "name": "ssh"
                                    },
                                    {
                                        "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/scm/gbmo/167407-web-borrow.git",
                                        "name": "http"
                                    }
                                ],
                                "self": [
                                    {
                                        "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/browse"
                                    }
                                ]
                            }
                        }
                    },
                    "toRef": {
                        "id": "refs/heads/PROD",
                        "displayId": "PROD",        // to_branch
                        "latestCommit": "e7d9cb0353fe111e68a350a2106527393e16660e",
                        "type": "BRANCH",
                        "repository": {
                            "slug": "167407-web-borrow",
                            "id": 86505,
                            "name": "167407-web-borrow",
                            "description": "Repo name is changes as per REQU0012087476",
                            "hierarchyId": "907479e31837038b5a64",
                            "scmId": "git",
                            "state": "AVAILABLE",
                            "statusMessage": "Available",
                            "forkable": true,
                            "project": {
                                "key": "GBMO",
                                "id": 1282,
                                "name": "147634-GBMO",
                                "description": "GC Global Mobile",
                                "public": false,
                                "type": "NORMAL",
                                "links": {
                                    "self": [
                                        {
                                            "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO"
                                        }
                                    ]
                                }
                            },
                            "public": false,
                            "archived": false,
                            "links": {
                                "clone": [
                                    {
                                        "href": "ssh://git@cedt-gct-bitbucketcli.nam.nsroot.net:7999/gbmo/167407-web-borrow.git",
                                        "name": "ssh"
                                    },
                                    {
                                        "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/scm/gbmo/167407-web-borrow.git",
                                        "name": "http"
                                    }
                                ],
                                "self": [
                                    {
                                        "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/browse"
                                    }
                                ]
                            }
                        }
                    },
                    "locked": false,
                    "author": {
                        "user": {
                            "name": "br16860",
                            "emailAddress": "br16860@163.com",
                            "active": true,
                            "displayName": "R, Bala Manjula Devi [TECH NE]",        // author
                            "id": 97357,
                            "slug": "br16860",
                            "type": "NORMAL",
                            "links": {
                                "self": [
                                    {
                                        "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/br16860"
                                    }
                                ]
                            }
                        },
                        "role": "AUTHOR",
                        "approved": false,
                        "status": "UNAPPROVED"
                    },
                    "reviewers": [
                        {
                            "user": {
                                "name": "ss51427",
                                "emailAddress": "ss51427@163.com",
                                "active": true,
                                "displayName": "Sankaran, Subbiah [TECH NE]",       // reviewer
                                "id": 10214,
                                "slug": "ss51427",
                                "type": "NORMAL",
                                "links": {
                                    "self": [
                                        {
                                            "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/users/ss51427"
                                        }
                                    ]
                                }
                            },
                            "lastReviewedCommit": "900993bdbafec71c42f7ebb0a1213d070f057344",
                            "role": "REVIEWER",
                            "approved": true,
                            "status": "APPROVED"
                        }
                    ],
                    "participants": [],
                    "properties": {
                        "qgStatus": "UNKNOWN",
                        "resolvedTaskCount": 0,
                        "commentCount": 0,
                        "openTaskCount": 0
                    },
                    "links": {
                        "self": [
                            {
                                "href": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/pull-requests/581"       // pr_link
                            }
                        ]
                    }
                }
            ],
            "start": 0
        }
        format it to below object:
        [{
            "id": 581,
            "title": "M2 Code Copy | staging to PROD",
            "state"" "MERGED"
            "from_branch": "staging",
            "to_branch": "PROD",
            "author": "R, Bala Manjula Devi [TECH NE]",
            "reviewer": "Sankaran, Subbiah [TECH NE]",
            "pr_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/pull-requests/581"
        }]
        """
        pr_details = []
        # if pr_response has field 'values', iterate it and get the details
        for pr in pr_response['values']:
            from_branch = pr['fromRef']['displayId'] if 'fromRef' in pr and 'displayId' in pr['fromRef'] else ''
            to_branch = pr['toRef']['displayId'] if 'toRef' in pr and 'displayId' in pr['toRef'] else ''
            author = pr['author']['user']['displayName'] if 'author' in pr and 'user' in pr['author'] and 'displayName' in pr['author']['user'] else ''
            reviewer = pr['reviewers'][0]['user']['displayName'] if 'reviewers' in pr and pr['reviewers'] and 'user' in pr['reviewers'][0] and 'displayName' in pr['reviewers'][0]['user'] else ''
            pr_link = pr['links']['self'][0]['href'] if 'links' in pr and 'self' in pr['links'] and pr['links']['self'] else ''
            pr_detail = {
                "id": pr['id'],
                "title": pr['title'],
                "state": pr['state'],
                "from_branch": from_branch,
                "to_branch": to_branch,
                "author": author,
                "reviewer": reviewer,
                "pr_link": pr_link
            }
            pr_details.append(pr_detail)
        return pr_details, True
    else:
        print(f'Failed to retrieve pull request details: {pull_requests_response.content}, {pull_requests_response.status_code}')
        return [], False


# write a function to load all the commit files from /static/bb_contribution_analysis/contribution
def load_all_commit_files(default_commit_files=[]):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # if is_partial_repos, load the partial repos file, otherwise load all repos file
    is_partial_repos = bb_conf['is_partial_repos']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['partial_contribution_file_path']}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['all_contribution_file_path']}"
    # if default_commit_files is not empty, return the default_commit_files
    if default_commit_files and len(default_commit_files) > 0:
        return default_commit_files, temp_file_path
    return file_tools.get_all_files_under_directory(temp_file_path), temp_file_path


def load_all_default_commit_files(default_commit_files=[]):
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # if is_partial_repos, load the partial repos file, otherwise load all repos file
    is_partial_repos = bb_conf['is_partial_repos']
    temp_file_path = f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_partial_contribution_file_path']}" if is_partial_repos else f"{SysConstants.PROJECT_BASE_PATH.value}/{bb_conf['default_all_contribution_file_path']}"
    if default_commit_files and len(default_commit_files) > 0:
        return default_commit_files, temp_file_path
    return file_tools.get_all_files_under_directory(temp_file_path), temp_file_path


# write a function to add pr details for each commit
def add_pr_details_for_commits_thread(commit_files, temp_file_path):
    # devide the commit_files into multiple parts, run then in parallel for faster speed
    num_threads = min(5, len(commit_files))
    commit_files_parts = [commit_files[i::num_threads] for i in range(num_threads)]

    # Create and start threads, each thread starts 1 second after previous one
    threads = []
    for i in range(num_threads):
        # sleep for 1 second before starting the next thread
        time.sleep(1)
        thread = threading.Thread(target=add_pr_details_for_commits, args=(commit_files_parts[i], temp_file_path))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()


def add_pr_details_for_commits(commit_files, temp_file_path):
    # iterate the commit files, and get the pr details for each commit
    for commit_file in commit_files:
        commits = file_tools.load_json(temp_file_path + '/' + commit_file)
        for commit in commits:
            # get base_url, project_key, repo_slug from "commit_link": "https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket/projects/GBMO/repos/167407-web-borrow/commits/39065763c2a6421916b5657abace0dbef1bae9ca",
            base_url = commit['commit_link'].split('/projects/')[0]
            project_key = commit['commit_link'].split('projects/')[-1].split('/repos')[0]
            repo_slug = commit['commit_link'].split('repos/')[-1].split('/commits')[0]
            commit_id = commit['id']
            # get the pr details for each commit
            pr_details, result_flag = get_pull_request_details(base_url, project_key, repo_slug, commit_id)
            # only when API success, update the pr details to commit, to avoid overwrite the existing pr details with empty array
            if result_flag:
                commit['pr_details'] = pr_details

        # get the file name from commit_file, including the ext name
        temp_file_full_path = f"{temp_file_path}/{commit_file}"
        # dump the commits with pr details into the same file
        file_tools.write_json_to_file(commits, temp_file_full_path)


# write a function to update the commit pr details for each commit
def update_commit_pr_details(default_commit_files=[]):
    # get all the commit files under /static/bb_contribution_analysis/contribution
    commit_files, temp_file_path = load_all_commit_files(default_commit_files)
    add_pr_details_for_commits_thread(commit_files, temp_file_path)

    # get all the default commit files under /static/bb_contribution_analysis/default_contribution
    default_commit_files, default_temp_file_path = load_all_default_commit_files(default_commit_files)
    add_pr_details_for_commits_thread(default_commit_files, default_temp_file_path)


def main():
    # this function is for loading the repos from different project spaces, which is executed only once or when any repo being added on Bitbucket
    # load_repos_from_bb()

    # get_pull_request_details('https://cedt-gct-bitbucket.nam.nsroot.net/bitbucket', 'GBMO', '167407-web-borrow', '2588bc55186a8a80afe185da98de45d88f966744')

    update_commit_pr_details()

    # update_refresh_info()

    # filter_commits_by_soeid(['zw51552'])

    # bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    # end_date = get_tomorrow_midnight()
    # # set start time as end_time - past_days
    # start_date = end_date - timedelta(days=bb_conf['duration_by_days'])
    # process_repo_links(['https://cedt-icg-bitbucket.nam.nsroot.net/bitbucket/projects/CONSUMER/repos/gft-ui-mcd/browse'], start_date, end_date)

    # load commits for all repos
    # load_commits_for_all_repos();



if __name__ == "__main__":
    main()
