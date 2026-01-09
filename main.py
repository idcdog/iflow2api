"""Flet 应用入口"""
import flet as ft
from src.iflow2api.gui import IFlow2ApiApp


def main(page: ft.Page):
    IFlow2ApiApp(page)


if __name__ == "__main__":
    ft.run(main)
