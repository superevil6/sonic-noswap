"""Every module NoSwap's tools import (they run from the kit's data folder, not from the program): imported here only
so PyInstaller bundles them. Keep in step with the tools' imports (tools/make_kit.py checks it)."""
# flake8: noqa
import argparse, ast, base64, collections, colorsys, contextlib, copy, difflib, fnmatch, functools, glob, hashlib
import html, http.server, importlib, importlib.util, inspect, io, json, math, mimetypes, operator, random, re
import secrets, shutil, stat, statistics, string, struct, subprocess, tempfile, textwrap, threading, time, traceback
import typing, urllib.parse, urllib.request, webbrowser, zipfile, zlib, itertools, dataclasses, enum, heapq, bisect
import socketserver, email.utils, http.client, uuid, platform, queue, logging, datetime, codecs, encodings.idna
import numpy
import PIL.Image, PIL.ImageDraw, PIL.ImageFont, PIL.ImageOps, PIL.ImageChops, PIL.ImageFilter, PIL.ImageColor
import PIL.GifImagePlugin, PIL.PngImagePlugin, PIL.BmpImagePlugin, PIL.JpegImagePlugin, PIL.DdsImagePlugin
import sys
if sys.platform == "win32":
    import msvcrt, winreg, ctypes, ctypes.wintypes
    try:
        import webview  # the editor's window (pywebview: Edge WebView2)
    except ImportError:
        pass
else:
    import fcntl
