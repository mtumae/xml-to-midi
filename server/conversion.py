import os
import time

from app.video.render import VideoRender


def time_conversion():
    stime = time.perf_counter()
    # https://pub-41087431ab634ba8a456c9a62333ea39.r2.dev/Arabesque_L._66_no._1_in_E_Major.xml
    VideoRender(
        file_name="Arabesque_L._66_no._1_in_E_Major.xml",
        file_id="",
        chunk_id="1",
        output_file="Arabesque_L._66_no._1_in_E_Major.mp4",
    ).render()
    etime = time.perf_counter()
    print(f"Time taken: {etime - stime}s")


def write_to_tmp():
    with open(os.path.join("app", "tmp", "text.txt"), "w") as file:
        file.write("Hello Wworsldsdmaskl naskfnaskjnflsandfonglkas giodslkgdsnlg!\n")


time_conversion()
