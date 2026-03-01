#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.shortcuts import print_formatted_text


def ui_info(message: str) -> None:
    print_formatted_text(FormattedText([("ansicyan", message)]))


def ui_warn(message: str) -> None:
    print_formatted_text(FormattedText([("ansiyellow", message)]))


def ui_error(message: str) -> None:
    print_formatted_text(FormattedText([("ansired bold", message)]))
