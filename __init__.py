#!/usr/bin/env python3

import argparse
import matplotlib.pyplot as plt
import sys

from pyexcel_ods3 import get_data
from pandas import DataFrame



def main():
    parser = argparse.ArgumentParser(description='weight-gazer')
    parser.add_argument('file_path', metavar='path to file', type=str, nargs=1,
                        help='path to the ods file')
    args = parser.parse_args()

    ods_data = get_data(args.file_path.pop())
    ods_data = ods_data[list(ods_data.keys()).pop()]
    dates = [row[0] for row in ods_data[1:]]
    weights = [row[1] for row in ods_data[1:]]
    total_kcals = [row[2] for row in ods_data[1:]]
    meal_kcals = [row[3:] for row in ods_data[1:]]

    df = DataFrame(meal_kcals)


if __name__ == "__main__":
    main()
