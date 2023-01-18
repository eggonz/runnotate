import argparse
import json
import os
import re

import cv2
import pandas as pd

WINDOW_NAME = 'runnotate'
DEFAULT_CONFIG_PATH = 'config.json'
DEFAULT_LABEL_COLOR = (0, 0, 0)

ASCII = {
    '0': 48,
    '1': 49,
    '2': 50,
    '3': 51,
    '4': 52,
    '5': 53,
    '6': 54,
    '7': 55,
    '8': 56,
    '9': 57,

    'a': 97,
    'b': 98,
    'c': 99,
    'd': 100,
    'e': 101,
    'f': 102,
    'g': 103,
    'h': 104,
    'i': 105,
    'j': 106,
    'k': 107,
    'l': 108,
    'm': 109,
    'n': 110,
    'o': 111,
    'p': 112,
    'q': 113,
    'r': 114,
    's': 115,
    't': 116,
    'u': 117,
    'v': 118,
    'w': 119,
    'x': 120,
    'y': 121,
    'z': 122,

    'Backspace': 8,
    'Tab': 9,
    'Enter': 13,
    'Esc': 27,
    'Spacebar': 32,
    'Delete': 127,
}


def color_hex2bgr(hex_):
    hex_ = hex_.lstrip('#')
    lv = len(hex_)
    rgb = tuple(int(hex_[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    bgr = tuple(reversed(rgb))
    return bgr


class Config:
    def __init__(self, path, *, data='', out=''):
        with open(path, 'r') as file:
            config_file = json.load(file)

        self._control_keys = {}
        for control in config_file['controls']:
            key_codes = config_file['controls'][control]
            self._control_keys[control] = [ASCII.get(code, -1) for code in key_codes]

        self._label_colors = {}
        for label in config_file['labels']:
            color = config_file['labels'][label]['color']
            self._label_colors[label] = color_hex2bgr(color)

        self._int2label = {}
        for label, keys_color in config_file['labels'].items():
            for key in keys_color['keys']:
                self._int2label[ASCII.get(key, -1)] = label

        self._data = config_file['data'] if not data else data
        self._data = self._data.rstrip('/')
        self._out = config_file['out'] if not out else out

    @property
    def data(self):
        return self._data

    @property
    def out(self):
        return self._out

    @property
    def label_keys(self):
        return self._int2label.keys()

    @property
    def quit_keys(self):
        return self._control_keys.get('quit', -1)

    @property
    def delete_keys(self):
        return self._control_keys.get('delete', -1)

    @property
    def next_keys(self):
        return self._control_keys.get('next', -1)

    @property
    def back_keys(self):
        return self._control_keys.get('back', -1)

    def get_key_label(self, key_num):
        return self._int2label[key_num]

    def get_label_color(self, label):
        return self._label_colors.get(label, DEFAULT_LABEL_COLOR)


class SaveFile:
    def __init__(self, config):
        self._filename = re.sub(r'\.[^.]*$', '.sav', config.out)

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
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=str,
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

    img_list = [file for file in sorted(os.listdir(config.data)) if re.match(r'^\d+\.[^.]*$', file)]

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
        m = re.match(r'^(?P<img_id>\d+)\.[^.]*$', filename)
        if not m:
            print('Error, invalid type')
            break
        img_id = int(m.group('img_id'))

        filepath = os.path.join(config.data, filename)

        img = cv2.imread(filepath)

        curr_label = None
        try:
            curr_label = df.loc[img_id]
        except KeyError:
            pass

        if curr_label is not None:
            curr_label = curr_label['label']
            height, width, _ = img.shape
            color = config.get_label_color(curr_label)
            cv2.rectangle(img, (3, 3), (width - 3, height - 3), color, 6)

        cv2.imshow(WINDOW_NAME, img)

        key = cv2.waitKey(1)

        if key in config.quit_keys or cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            print('Quit')
            break

        if key in config.back_keys:
            i -= 1
        elif key in config.next_keys:
            i += 1
        elif key in config.delete_keys:
            df = df.drop(index=img_id)
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
    df.sort_index().to_csv(config.out, index_label='id')

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
