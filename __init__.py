#!/usr/bin/env python3

import os
import argparse
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import random

from pyexcel_ods3 import get_data
from PIL import Image


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
        self.fig = self.draw_figure()
        FileWriter(self.fig, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency)


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

    def draw_figure(self):
        ax = self.meals.plot.bar(
            figsize=(19.2, 10.8),
            stacked=True,
            legend=False,
        )
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

class FileWriter:

    def __init__(self, fig, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency):
        self.fig = fig
        self.src_wallpaper_dir = src_wallpaper_dir
        self.out_wallpaper_dir = out_wallpaper_dir
        src_files = os.listdir(self.src_wallpaper_dir)
        self.temp_file = self.save_temp_file()
        self.save_files(src_files, appearance_frequency)

    def save_temp_file(self):
        timestamp = str(datetime.datetime.utcnow()).replace(" ", "_")
        temp_file_name = 'weight-gazer-temp-{}.png'.format(timestamp)
        temp_file_path = os.path.join(self.src_wallpaper_dir, temp_file_name)
        plt.savefig(temp_file_path, transparent=True)
        return temp_file_path

    def save_files(self, src_files, appearance_frequency):
        images_to_overlay = random.sample(
            src_files,
            int(appearance_frequency/100*len(src_files)),
        )
        for background in images_to_overlay:
            timestamp = str(datetime.datetime.utcnow()).replace(" ", "_")
            filename = '{}-weight-gazer-{}.png'.format(background, timestamp)
            try:
                self.overlay_image(
                    os.path.join(self.src_wallpaper_dir, background),
                    self.temp_file,
                    filename,
                )
            except Exception:
                continue

    def overlay_image(self, background, foreground, filename):
        wallpaper = Image.open(background)
        chart = Image.open(foreground)
        wallpaper.paste(chart, (0, 0), chart)
        wallpaper.save(os.path.join(self.out_wallpaper_dir, filename))

if __name__ == "__main__":
    main()
