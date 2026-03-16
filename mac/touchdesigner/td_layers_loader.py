"""
TouchDesigner loader for segmented SVG layers.
Usage in TD Python shell:
    op('td_layers_loader').module.load_layers_table()
"""

import json
import os
from pathlib import Path

RESPONSE_DAT = "pipeline_response_json"
LAYER_TABLE_DAT = "layer_table"
HOST_IO_ROOT = "~/desktop/engine/moonli_table/mac/io"
HTTP_BASE = "http://localhost:8011"


def _log(msg):
    print("[layers_loader] {}".format(msg))


def _read_response():
    d = op(RESPONSE_DAT)
    if not d or not d.text.strip():
        raise Exception("Empty response DAT: {}".format(RESPONSE_DAT))
    return json.loads(d.text)


def _container_to_host_path(container_path):
    prefix = "/app/data/"
    p = container_path.replace("\\", "/")
    if not p.startswith(prefix):
        raise Exception("Unexpected container path: {}".format(container_path))
    rel = p[len(prefix):]
    return str((Path(os.path.expanduser(HOST_IO_ROOT)) / rel).resolve())


def _build_http_layer_base(master_svg_uri):
    if not master_svg_uri.endswith("/master.svg"):
        raise Exception("Unexpected master_svg_uri: {}".format(master_svg_uri))
    return master_svg_uri[:-len("/master.svg")] + "/layers"


def load_layers_table():
    body = _read_response()

    master_svg_path = body.get("master_svg_path")
    master_svg_uri = body.get("master_svg_uri")
    if not master_svg_path or not master_svg_uri:
        raise Exception("Response missing master_svg_path/master_svg_uri")

    layers_container_dir = master_svg_path.replace("\\", "/").rsplit("/", 1)[0] + "/layers"
    layers_host_dir = Path(_container_to_host_path(layers_container_dir))
    if not layers_host_dir.exists():
        raise Exception("Layers dir not found: {}".format(layers_host_dir))

    layer_base_uri = _build_http_layer_base(master_svg_uri)
    svg_files = sorted([p for p in layers_host_dir.glob("*.svg") if p.is_file()])
    if not svg_files:
        raise Exception("No SVG layers found in: {}".format(layers_host_dir))

    table = op(LAYER_TABLE_DAT)
    if not table:
        raise Exception("Missing DAT: {}".format(LAYER_TABLE_DAT))

    table.clear()
    table.appendRow(["order", "file", "local_path", "http_url"])

    for idx, f in enumerate(svg_files, start=1):
        http_url = "{}{}{}".format(HTTP_BASE, layer_base_uri, "/" + f.name)
        table.appendRow([str(idx), f.name, str(f), http_url])

    _log("Loaded {} layers into '{}'".format(len(svg_files), LAYER_TABLE_DAT))
    return len(svg_files)
