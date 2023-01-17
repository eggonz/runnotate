import argparse
import itertools
import json
import os
import re

import cv2
import pandas as pd

WINDOW_NAME = 'runnotate'
IMG_REGEX = r'^(?P<img_id>\d+)\.[^\.]*$'
DEFAULT_CONFIG = 'config.json'


class Config:
    key2int = {
        'Y': 121,
        'O': 111,
        'N': 110,
        'Q': 113,
        'SPACE': 32,
        'BACK': 8,
        'ESC': 27,
    }

    def __init__(self, path, *, data='', out=''):
        with open(path, 'r') as file:
            self.config = json.load(file)

        for field in ('labels', 'controls'):
            for label in self.config[field]:
                key_codes = self.config[field][label]
                self.config[field][label] = [Config.key2int.get(code, -1) for code in key_codes]

        self.int2label = {}
        for label, key_list in self.config['labels'].items():
            for key in key_list:
                self.int2label[key] = label

        self._data = self.config['data'] if not data else data
        self._out = self.config['out'] if not out else out

    @property
    def data(self):
        return self._data

    @property
    def out(self):
        return self._out

    @property
    def label_keys(self):
        return itertools.chain(*self.config['labels'].values())

    @property
    def quit_keys(self):
        return self.config['controls']['quit']

    @property
    def next_keys(self):
        return self.config['controls']['next']

    @property
    def back_keys(self):
        return self.config['controls']['back']

    def get_key_label(self, key_num):
        return self.int2label[key_num]


class SaveFile:
    def __init__(self, config):
        self._filename = re.sub(r'\.[^\.]*$', '.sav', config.out)

        self.stamp = 0
        self.load()

    def save(self):
        save_info = {
            'stamp': self.stamp
        }

        with open(self._filename, 'w') as save_file:
            json.dump(save_info, save_file)

    def load(self):
        try:
            with open(self._filename, 'r') as save_file:
                save_info = json.load(save_file)
        except FileNotFoundError:
            save_info = {}

        self.stamp = int(save_info.get('stamp', 0))


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=str,
                        help='path to config file (default: "./config.json")')
    parser.add_argument("--data", default='', type=str,
                        help='path to directory containing images, overrides value in config')
    parser.add_argument("--out", default='', type=str,
                        help='output csv file, overrides value in config')
    return parser


def load():
    print('Loading...')

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    config = Config(args.config, data=args.data, out=args.out)
    sav = SaveFile(config)

    img_list = [file for file in os.listdir(config.data) if re.match(IMG_REGEX, file)]

    if not os.path.exists(config.out):
        save_dir = config.out.rsplit('/', maxsplit=1)[0]
        if not os.path.exists(save_dir) or not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        df = pd.DataFrame(columns=['label'])
    else:
        df = pd.read_csv(config.out, index_col='id')

    print('Loaded!')
    return config, sav, img_list, df


def run(config, sav, img_list, df):

    cv2.namedWindow(WINDOW_NAME)
    cv2.startWindowThread()

    i = sav.stamp if sav.stamp < len(img_list) else 0
    while True:
        i = i % len(img_list)
        filename = img_list[i]
        m = re.match(IMG_REGEX, filename)
        if not m:
            print('Error, invalid type')
            break
        img_id = int(m.group('img_id'))

        filepath = os.path.join(config.data, filename)

        img = cv2.imread(filepath)
        cv2.imshow(WINDOW_NAME, img)

        key = cv2.waitKey(1)

        if key in config.quit_keys or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            print('Quit')
            break

        if key in config.back_keys:
            i -= 1
        elif key in config.next_keys:
            i += 1
        elif key in config.label_keys:
            label = config.get_key_label(key)
            df.loc[img_id] = label
            i += 1

    cv2.destroyAllWindows()

    sav.stamp = i

    return sav, df


def save(config, sav, df):
    print('Saving...')

    if df is None or df.empty:
        print('Nothing to save')
        return
    df.to_csv(config.out, index_label='id')

    sav.save()

    print('Saved!')


def main():
    config, sav, img_list, df = load()
    try:
        sav, df = run(config, sav, img_list, df)
    finally:
        save(config, sav, df)


if __name__ == '__main__':
    main()
