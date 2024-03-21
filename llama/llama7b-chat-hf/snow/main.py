#!/usr/bin/env python3

import click

from cleanup import cleanup
from setup import run_setup


@click.group()
def main():
    pass


main.add_command(run_setup)
main.add_command(cleanup)

if __name__ == "__main__":
    main()
