"""
TouchDesigner trigger client for mac pipeline.
Usage in TD Python shell:
    op('td_pipeline_client').module.run_pipeline()
"""

import json
import os
import time
import urllib.request
import urllib.error

API_URL = "http://localhost:8011/process/local"
SOURCE_TOP = "null_out"
INCOMING_DIR = "~/desktop/engine/moonli_table/mac/io/incoming"
LOG_DAT = "pipeline_log"
RAW_JSON_DAT = "pipeline_response_json"
MASTER_URI_DAT = "pipeline_master_svg_uri"
USE_LAYER_COUNT = True
LAYER_COUNT = 6
HTTP_TIMEOUT = 180


def _log(msg):
    d = op(LOG_DAT)
    if d:
        ts = time.strftime("%H:%M:%S")
        d.text += "[{}] {}\n".format(ts, msg)
    else:
        print(msg)


def _set_dat_text(dat_name, text):
    d = op(dat_name)
    if d:
        d.text = text


def _save_input_image(session_id, candidate_id):
    top = op(SOURCE_TOP)
    if top is None:
        raise Exception("SOURCE_TOP not found: {}".format(SOURCE_TOP))

    incoming_dir = os.path.expanduser(INCOMING_DIR)
    if not os.path.exists(incoming_dir):
        os.makedirs(incoming_dir)

    filename = "{}_{}.png".format(session_id, candidate_id)
    abs_path = os.path.join(incoming_dir, filename)
    top.save(abs_path)
    local_path = "incoming/{}".format(filename)
    return abs_path, local_path


def _post_process_local(payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw), raw


def run_pipeline():
    session_id = "sess_td_{}".format(int(time.time()))
    candidate_id = "cand_td_{}".format(int(time.time()))

    try:
        _log("Start pipeline trigger")
        abs_path, local_path = _save_input_image(session_id, candidate_id)
        _log("Saved input image: {}".format(abs_path))

        payload = {
            "local_path": local_path,
            "session_id": session_id,
            "candidate_id": candidate_id,
        }
        if USE_LAYER_COUNT:
            payload["layer_count"] = LAYER_COUNT

        _log("POST {}".format(API_URL))
        result, raw = _post_process_local(payload)
        _set_dat_text(RAW_JSON_DAT, raw)

        status = result.get("status", "")
        master_svg_uri = result.get("master_svg_uri", "")
        master_svg_path = result.get("master_svg_path", "")
        segment_dir = result.get("segment_dir", "")

        _set_dat_text(MASTER_URI_DAT, master_svg_uri)

        _log("Done. status={}".format(status))
        _log("master_svg_uri={}".format(master_svg_uri))
        _log("master_svg_path={}".format(master_svg_path))
        _log("segment_dir={}".format(segment_dir))
        _log("HTTP SVG URL: http://localhost:8011{}".format(master_svg_uri))
        return result

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else str(e)
        _log("HTTPError: {} {}".format(e.code, err_body))
        _set_dat_text(RAW_JSON_DAT, err_body)
        raise
    except Exception as e:
        _log("Error: {}".format(str(e)))
        raise
