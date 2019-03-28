#!/usr/bin/env python3

import os
import argparse
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import random
import re
import subprocess

from pyexcel_ods3 import get_data
from PIL import Image
from numpy import mean


def main():
    parser = argparse.ArgumentParser(description='weight-gazer')

    parser.add_argument('file_path', metavar='path to file', type=str, nargs=1,
                        help='path to the ods file')
    parser.add_argument('-sw', metavar='source wallpaper directory', type=str, nargs=1,
                        help='directory where source wallpapers are stored')
    parser.add_argument('-ow', metavar='output wallpaper directory', type=str, nargs=1,
                        help='directory where output wallpapers will be saved')
    parser.add_argument('-af', metavar='appearance frequency in percent', type=float,
                        nargs=1, help='percentage of wallpapers that will be overlaid')
    args = parser.parse_args()

    ods_data = get_data(args.file_path.pop())
    src_wallpaper_dir = args.sw.pop()
    out_wallpaper_dir = args.ow.pop()
    appearance_frequency = args.af.pop()

    WeightGazer(ods_data,
                src_wallpaper_dir,
                out_wallpaper_dir,
                appearance_frequency,
                )


class WeightGazer:

    def __init__(self, ods_data, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency):
        self.ods_data = ods_data
        self.columns = None
        self.meals = None
        self.df = None
        self.prepare_dataframe()
        self.aspect_width = 16
        self.aspect_height = 9
        self.screen_width, self.screen_height = self.get_screen_size()
        FileWriter(self, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency)

    def prepare_dataframe(self):
        df = pd.DataFrame(self.ods_data['Sheet1'][1:])
        self.columns = self.ods_data['Sheet1'][0]
        self.columns += [
            'meal{}'.format(i) for i in range(len(df.columns) - len(self.columns))
        ]
        d = {}
        for i in range(len(self.columns)):
            d[i] = self.columns[i]
        df = df.rename(columns=d)
        df = df.set_index('date')
        df = df.dropna(thresh=3)
        df['weight'] = df['weight'].apply(lambda x: float(x.replace(',', '.')))
        meal_columns = [elem for elem in self.columns if elem.startswith('meal')]
        self.meals = df[meal_columns]
        self.df = df

    def draw_figure(self, dpi, figsize):
        fig = plt.figure(dpi=dpi)
        ax = self.meals.plot.bar(
            figsize=figsize,
            stacked=True,
            legend=False,
            ax=plt.gca()
        )
        plt.xticks(*plt.xticks(), rotation=30)
        ax.xaxis.tick_top()
        ax2 = ax.twinx()
        ax2.plot(
            ax.get_xticks(),
            self.df['weight'],
            ls='--',
            lw=10,
            color='pink',
            marker='o',
            markersize=20,
        )
        return plt.gcf()

    def get_screen_size(self):
        screen_size = str(subprocess.Popen(
            'xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE
        ).communicate()[0])
        pattern = re.compile('\d+x\d+')
        match = re.search(pattern, screen_size).group()
        return map(int, match.split('x'))

class FileWriter:

    def __init__(self, wg, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency):
        self.wg = wg
        self.src_wallpaper_dir = src_wallpaper_dir
        self.out_wallpaper_dir = out_wallpaper_dir
        src_files = os.listdir(self.src_wallpaper_dir)
        self.save_files(src_files, appearance_frequency)

    def get_temp_file_path(self):
        timestamp = str(datetime.datetime.utcnow()).replace(" ", "_")
        temp_file_name = 'weight-gazer-temp-{}.png'.format(timestamp)
        temp_file_path = os.path.join(self.src_wallpaper_dir, temp_file_name)
        return temp_file_path

    def save_files(self, src_files, appearance_frequency):
        images_to_overlay = random.sample(
            src_files,
            int(appearance_frequency/100*len(src_files)),
        )
        for background in images_to_overlay:
            timestamp = str(datetime.datetime.utcnow()).replace(" ", "_")
            filename = '{}-weight-gazer-{}.png'.format(background, timestamp)
            self.overlay_image(
                os.path.join(self.src_wallpaper_dir, background),
                self.wg,
                filename,
            )

    def overlay_image(self, background, wg, filename):
        wallpaper = Image.open(background)
        src_width, src_height = wallpaper.size
        frame_width, frame_height, shift = \
            self.determine_frame_dimensions_and_shift(src_width, src_height)
        dpi = int(mean((src_width/frame_width, src_height/frame_height)) * 100)
        figsize = (frame_width/dpi, frame_height/dpi)
        wg.draw_figure(dpi, figsize)
        temp_file_path = self.get_temp_file_path()
        chart = plt.savefig(temp_file_path, transparent=True, dpi=dpi)
        chart = Image.open(temp_file_path)
        wallpaper.paste(chart, shift, chart)
        wallpaper.save(os.path.join(self.out_wallpaper_dir, filename))
        os.remove(temp_file_path)

    def determine_frame_dimensions_and_shift(self, src_width, src_height):
        src_aspect_ratio = src_width/src_height
        screen_aspect_ratio = self.wg.aspect_width / self.wg.aspect_height
        is_panoramic = None
        fits_perfectly = False
        if src_aspect_ratio > screen_aspect_ratio:
            is_panoramic = True
        elif src_aspect_ratio < screen_aspect_ratio:
            is_panoramic = False
        else:
            fits_perfectly = True
        if fits_perfectly:
            return src_width, src_height, (0, 0)
        if is_panoramic is True:
            frame_width = int(src_height * screen_aspect_ratio)
            shift = (int(0.5 * (src_width - frame_width)), 0)
            return frame_width, src_height, shift
        elif is_panoramic is False:
            frame_height = int(src_width * (1 / screen_aspect_ratio))
            shift = (0, int(0.5 * (src_height - frame_height)))
            return src_width, frame_height, shift


if __name__ == "__main__":
    main()
