import os

from consts.sys_constants import SysConstants


def verify_image_type(image_file):
    content_type = image_file.content_type
    return content_type in ["image/jpeg", "image/png"]


def verify_image_size(image_file):
    return len(image_file.read()) <= SysConstants.IMAGE_MAX_SIZE.value


def verify_image(image_file, verify_empty_flg=True, verify_type_flg=True, verify_size_flg=True):
    if verify_empty_flg and image_file.filename == '':
        return SysConstants.MSG_IMAGE_IS_EMPTY.value
    if verify_type_flg and not verify_image_type(image_file):
        return SysConstants.MSG_INVALID_IMAGE_TYPE.value
    if verify_size_flg:
        image_file.seek(0, os.SEEK_END)  # Move to the end of the file to get its size
        if not verify_image_size(image_file):
            return SysConstants.MSG_INVALID_IMAGE_SIZE.value
        image_file.seek(0)  # Reset file pointer after reading
    return ""
