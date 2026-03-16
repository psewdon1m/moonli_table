# TouchDesigner helper scripts

- `td_pipeline_client.py`: saves TOP image to `mac/io/incoming`, triggers pipeline (`/process/local`), stores JSON response.
- `td_layers_loader.py`: reads pipeline JSON response and builds layer table from `vector/layers/*.svg`.

Recommended DAT names in TD:
- `pipeline_log` (Text DAT)
- `pipeline_response_json` (Text DAT)
- `pipeline_master_svg_uri` (Text DAT)
- `layer_table` (Table DAT)
