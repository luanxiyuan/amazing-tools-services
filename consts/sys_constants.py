import os
from enum import Enum


class SysConstants(Enum):
        PROJECT_BASE_PATH = "D:\\01.Programming\\temp\\amazing-tools-services"
        GLOBAL_CONFIG_FILE = f"{PROJECT_BASE_PATH}/conf/global_config.json"

        # module names
        UI_MARKER = "ui_marker"
        CONTACTS = "contacts"
        ABBREVIATION = "abbreviation"
        API_TREE = "api_tree"
        BB_CONTRIBUTION_ANALYSIS = "bb_contribution_analysis"
        ONE_STEP = "one_step"

        # Status
        STATUS_SUCCESS = "success"
        STATUS_FAILED = "failed"

        # Message related to image upload
        MSG_INVALID_IMAGE_TYPE = "Invalid image type"
        MSG_INVALID_IMAGE_SIZE = "Invalid image size, maximum 5M"
        MSG_IMAGE_UPLOAD_SUCCESSFUL = "Image uploaded successfully"
        MSG_IMAGE_UPLOAD_FAILED = "Image uploaded failed"
        MSG_IMAGE_IS_EMPTY = "Image file is empty"
        MSG_INVALID_PARAMETERS = "Invalid parameters, application / module / function is empty"
        IMAGE_MAX_SIZE = 5242880 # 5M

        # Message related to xsd converter
        MSG_XSD_IS_EMPTY = "XSD file is empty"
        MSG_INVALID_XSD_CONTENT = "Invalid XSD file content"
        MSG_INVALID_XSD_TYPE = "Invalid XSD file type"
        MSG_INVALID_XSD_SIZE = "Invalid XSD size, maximum 5M"
        MSG_XSD_UPLOAD_SUCCESSFUL = "XSD uploaded successfully"
        XSD_MAX_SIZE = 5242880 # 5M
        XSD_CONVERTER_PATH = "assets/xsd_converter"
        XSD_CLEAR_PATH = "assets/xsd_converter"

        # Message related to API Tree
        API_ALREADY_EXISTS = "The API [{0}] with method [{1}] already exists"
        API_TYPE_OPEN = "Open"
        API_TYPE_PRIVATE = "Private"
        API_TYPE_PARTNER = "Partner"
        API_URI_SEARCH_MODE_EXACT = "Exact Match"

        # HTTP Status Code
        HTTP_STATUS_OK = 200
        HTTP_STATUS_NO_CONTENT = 204
        HTTP_STATUS_BAD_REQUEST = 400
        HTTP_STATUS_NOT_FOUND = 404
        HTTP_STATUS_INTERNAL_SERVER_ERROR = 500

        # UI Marker details prefix
        UI_MARKER_PAGE_PREFIX = "page_"
        UI_MARKER_ELEMENT_PREFIX = "element_"
        UI_MARKER_FORM_PREFIX = "form_"
        UI_MARKER_UI_API_RELATION_FILE = "ui_api_relation_data.json"

        # One step
        ONE_STEP_EXC_WS_OUTPUT = "one_step_exc_ws_output"
        ONE_STEP_CMD_FILE_PATH = "static/one_step/command_files"
        ONE_STEP_CMD_LOG_FILE_PATH = "static/one_step/command_log_files"