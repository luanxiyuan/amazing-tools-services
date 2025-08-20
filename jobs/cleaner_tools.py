import os
import shutil

import schedule
import time

from consts.sys_constants import SysConstants


def remove_all_files_and_folders_in_directory(directory_path):
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        print(f"All files and folders in {directory_path} have been removed.")
    except Exception as e:
        print(f"Error removing files and folders: {e}")


def schedule_file_removal():
    directory_path = os.path.join(SysConstants.PROJECT_BASE_PATH.value, SysConstants.XSD_CONVERTER_PATH.value)
    schedule.every(1).hours.do(remove_all_files_and_folders_in_directory, directory_path=directory_path)

    while True:
        schedule.run_pending()
        time.sleep(1)
