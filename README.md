# runnotate

Tool for quick image annotation.

## Setup

1. Download the repository.
2. Create an environment (optional):

```bash
python -m venv venv
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

4. Run `runnotate` using the following command from the root of the repository:

```bash
python runnotate --config path/to/config.json
```

The command allows optional flags `--data` and `--out` to specify the source data folder and output file. Run `python runnotate -h` for help.

- `--config`: json file
- `--data`: directory with images. The name of the images must be their ID
- `--out`: path and file name of the output csv file

### config
The file `config.json` contains the configuration for the task. It has the following structure:

```json
{
  "labels": {
    "label1": [...],
    "label2": [...]
  },
  "controls": {
    "control1": [...]
  },
  "data": "",
  "out": ""
}
```

Each of the labels contains a list of the keys for each class. The necessary controls are also specified with their corresponding keys.

The data and output paths are specified here. If any of the values is specified when running the command in terminal, the value in `config.json` will be ignored.

## Output

The output csv contains columns `id` and `label` for images that have been labeled. Skipped images should not appear.

A `sav` file will be created in the same directory; it contains save information.

## Example of use

Example command:

```bash
python runnotate --config data/config.json --data data/reduced_coco_1000 --out out/annotations.csv
```

Example `config.json`:

```json
{
  "labels": {
    "young": ["Y"],
    "old": ["O"],
    "none": ["N"]
  },
  "controls": {
    "back": ["BACK"],
    "next": ["SPACE"],
    "quit": ["Q", "ESC"]
  },
  "data": "data/reduced_coco",
  "out": "out/annotations.csv"
}
```

Example output:

```csv
,id, label
1,493022,old
2,301241,old
3,39630,young
```