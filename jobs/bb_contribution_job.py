import schedule
import time

from common_tools import file_tools
from consts.sys_constants import SysConstants
from engines.bb_contribution_analysis import bb_contribution_analysis_engine


def bb_contribution_refresh():
    bb_contribution_analysis_engine.load_commits_for_all_repos()


def schedule_bb_contribution_refresh():
    bb_conf = file_tools.load_module_config_file(SysConstants.BB_CONTRIBUTION_ANALYSIS.value)
    allowed_refresh_interval_in_minute = bb_conf.get("allowed_refresh_interval_in_minute", 60)
    schedule.every(allowed_refresh_interval_in_minute).minutes.do(bb_contribution_refresh)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    bb_contribution_refresh()