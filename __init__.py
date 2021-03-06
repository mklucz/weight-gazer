#!/usr/bin/env python3

import os
import argparse
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import psutil
import random
import re
import shutil
import signal
import subprocess

from pyexcel_ods3 import get_data
from PIL import (
    Image,
    ImageFilter,
)
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
        self.df = self.prepare_dataframe()
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
        return df

    def draw_figure(self, dpi, figsize, fontsize):
        plt.figure(dpi=dpi)
        self.set_font_sizes(fontsize)
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
            lw=dpi/10,
            color='pink',
            marker='o',
            markersize=dpi/5,
        )
        return plt.gcf()

    def get_screen_size(self):
        screen_size = str(subprocess.Popen(
            'xrandr | grep "\*" | cut -d" " -f4', shell=True, stdout=subprocess.PIPE
        ).communicate()[0])
        pattern = re.compile('\d+x\d+')
        match = re.search(pattern, screen_size).group()
        return map(int, match.split('x'))

    def set_font_sizes(self, fontsize):
        plt.rcParams.update({
            'legend.fontsize': fontsize,
            'axes.labelsize': fontsize,
            'axes.titlesize': fontsize,
            'xtick.labelsize': fontsize,
            'ytick.labelsize': fontsize
        })


class FileWriter:

    CHART_FILE_TEMPLATE = 'weight-gazer-temp-chart{}.png'
    SET_IMG_SRC = "gsettings set org.cinnamon.desktop.background.slideshow image-source 'directory://{path}'"


    def __init__(self, wg, src_wallpaper_dir, out_wallpaper_dir, appearance_frequency):
        self.wg = wg
        self.src_wallpaper_dir = src_wallpaper_dir
        self.out_wallpaper_dir = out_wallpaper_dir
        src_files = os.listdir(self.src_wallpaper_dir)
        # self.del_old_files()
        self.save_files(src_files, appearance_frequency)

    def make_temp_file_path(self, template):
        timestamp = str(datetime.datetime.utcnow()).replace(" ", "_")
        temp_file_name = template.format(timestamp)
        temp_file_path = os.path.join(self.src_wallpaper_dir, temp_file_name)
        return temp_file_path

    def del_old_files(self):
        for file_name in os.listdir(self.out_wallpaper_dir):
            if 'weight-gazer' in file_name:
                os.remove(os.path.join(self.out_wallpaper_dir, file_name))

    def copy_untouched_images(self, images_to_copy):
        for file_name in images_to_copy:
            shutil.copy2(
                os.path.join(self.src_wallpaper_dir, file_name),
                os.path.join(self.out_wallpaper_dir, file_name)
            )

    def save_files(self, src_files, appearance_frequency):
        images_to_overlay = random.sample(
            src_files,
            int(appearance_frequency/100*len(src_files)),
        )
        images_to_copy_unchanged =\
            [f for f in src_files if f not in images_to_overlay]
        self.slideshow_enabled(False)
        self.copy_untouched_images(images_to_copy_unchanged)
        self.del_old_files()
        for src_file_name in images_to_overlay:
            self.overlay_image(
                os.path.join(self.src_wallpaper_dir, src_file_name),
                self.wg,
                src_file_name,
            )
        self.slideshow_enabled(True)


    def overlay_image(self, background, wg, out_file_name):
        wallpaper = Image.open(background)
        frame_width, frame_height, shift = \
            self.determine_frame_dimensions_and_shift(wallpaper.size)
        dpi = self.get_dpi(frame_width, frame_height, wallpaper.size)
        figsize = (frame_width/dpi, frame_height/dpi)
        fontsize = frame_width / 200
        wg.draw_figure(dpi, figsize, fontsize)
        chart_temp_file = self.make_temp_file_path(self.CHART_FILE_TEMPLATE)
        plt.savefig(chart_temp_file, transparent=True, dpi=dpi)
        plt.close(plt.gcf())
        chart = Image.open(chart_temp_file)
        shadow = self.prepare_shadow(chart.copy(), dpi)
        wallpaper.paste(shadow, shift, shadow)
        wallpaper.paste(chart, shift, chart)
        wallpaper.save(os.path.join(self.out_wallpaper_dir, out_file_name))
        os.remove(chart_temp_file)

    def determine_frame_dimensions_and_shift(self, wallpaper_size):
        src_width, src_height = wallpaper_size
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

    def get_dpi(self, frame_width, frame_height, wallpaper_size):
        src_width, src_height = wallpaper_size
        return int(mean((src_width/frame_width, src_height/frame_height)) * 100)

    def prepare_shadow(self, im, dpi):

        def is_black(color_tuple):
            return color_tuple[0:3] == (0, 0, 0)

        pixel_data = im.load()
        width, height = im.size
        for y in range(height):
            for x in range(width):
                if not is_black(pixel_data[x, y]):
                    pixel_data[x, y] = (255, 255, 255, 0)
                else:
                    pixel_data[x, y] = (255, 255, 255, 255)
        im = im.filter(ImageFilter.GaussianBlur(radius=dpi/50))
        return im

    def signal_process(self, proc_name, sig):
        for p in psutil.process_iter():
            if p.name() == proc_name:
                os.kill(p.pid, sig)

    def slideshow_enabled(self, val):
        val = str(val).lower()
        subprocess.run(
            "gsettings set org.cinnamon.desktop.background.slideshow slideshow-enabled {val}".format(val=val).split(' ')
        )

if __name__ == "__main__":
    main()
