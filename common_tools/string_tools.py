import random
import string
import uuid
import re
from datetime import datetime
from consts.sys_constants import SysConstants


def replace_invalid_space(input_string):
    try:
        if input_string is None:
            return ""
        return str(input_string).replace(u'\xa0', u' ')
    except:
        # print the error stack
        print(f"Error in replace_invalid_space: {input_string}")


def covert_2space_to_1space(input_string):
    try:
        if input_string is None:
            return ""
        return str(input_string).replace("  ", " ")
    except:
        print(f"Error in covert_2space_to_1space: {input_string}")


def generate_image_file_id():
    # Generate a random string of length 6
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

    # Get the current time in the format yyyyMMdd hhmmss
    current_time = datetime.now().strftime('%Y%m%d%H%M%S')

    # Concatenate the random string with the current time
    result = f"{SysConstants.UI_MARKER_PAGE_PREFIX.value}{current_time}_{random_string}"

    return result


def generate_uuid():
    return str(uuid.uuid4())


def format_message(template, *args):
    return template.format(*args)


def generate_create_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")


def format_uri(uri):
    # if uri includes 'uris.jws', remove all part before 'uris.jws', includes 'uris.jws'
    if uri.find('uris.jws') != -1:
        length = len('uris.jws')
        uri = uri[uri.find('uris.jws') + length:]
    # add / at the beginning of uri, remove / at the end of uri
    if not uri.startswith('/'):
        uri = '/' + uri
    if uri.endswith('/'):
        uri = uri[:-1]
    return uri


def normalize_uri(uri):
    uri = format_uri(uri)
    return re.sub(r'\{[^}]*\}', '[^/]*', uri.lower())


def create_uri_regex(uri: str) -> re.Pattern:
    # Replace placeholders like {0}, {id}, {cardid}, etc., with a pattern that matches any single segment
    uri_pattern = normalize_uri(uri)
    return re.compile(f'^{uri_pattern}', re.IGNORECASE)


def create_uri_full_match_regex(uri: str) -> re.Pattern:
    # Replace placeholders like {0} with a pattern that matches any single segment
    uri_pattern = normalize_uri(uri)
    return re.compile(f'^{uri_pattern}$', re.IGNORECASE)


def partial_match_uri_with_variables(search_uri: str, compared_uri: str, ignore_case_flag: bool = True) -> bool:
    regex = create_uri_regex(search_uri)
    return regex.match(compared_uri.lower() if ignore_case_flag else compared_uri) is not None


def exact_match_uri_with_variables(search_uri: str, compared_uri: str, ignore_case_flag: bool = True) -> bool:
    regex = create_uri_full_match_regex(search_uri)
    return regex.match(compared_uri.lower() if ignore_case_flag else compared_uri) is not None
