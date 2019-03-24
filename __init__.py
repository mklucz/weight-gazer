#!/usr/bin/env python3

import argparse
import matplotlib.pyplot as plt
import pandas as pd

from pyexcel_ods3 import get_data


def main():
    parser = argparse.ArgumentParser(description='weight-gazer')

    parser.add_argument('file_path', metavar='path to file', type=str, nargs=1,
                        help='path to the ods file')
    parser.add_argument('-w', metavar='wallpaper folder', type=str, nargs=1,
                        help='directory where wallpapers are stored')
    args = parser.parse_args()

    ods_data = get_data(args.file_path.pop())
    wallpaper_folder = args.w.pop()

    WeightGazer(ods_data, wallpaper_folder)


class WeightGazer:

    def __init__(self, ods_data, wallpaper_folder):
        self.ods_data = ods_data
        self.wallpaper_folder = wallpaper_folder
        self.columns = None
        self.meals = None
        self.df = None
        self.prepare_dataframe()
        self.fig = self.draw_figure()

        plt.savefig('/home/mklucz/Desktop/weight.png', transparent=True)

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
            lw=10,
            color='pink',
        )
        return plt.gcf()


if __name__ == "__main__":
    main()
