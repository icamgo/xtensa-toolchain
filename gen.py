#!/usr/bin/env python
# This script will download and extract required tools into the current directory
# Tools list is obtained from tools.json file
# Written by Ivan Grokhotkov, 2015
#
from __future__ import print_function
import urllib
import os
import shutil
import errno
import os.path
import hashlib
import json
import platform
import sys
import tarfile
import zipfile
import re

dist_dir = 'dist/'

def sha256sum(filename, blocksize=65536):
	hash = hashlib.sha256()
	with open(filename, "rb") as f:
		for block in iter(lambda: f.read(blocksize), b""):
			hash.update(block)
	return hash.hexdigest()

def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno != errno.EEXIST or not os.path.isdir(path):
			raise

def report_progress(count, blockSize, totalSize):
	percent = int(count*blockSize*100/totalSize)
	percent = min(100, percent)
	sys.stdout.write("\r%d%%" % percent)
	sys.stdout.flush()

def unpack(filename, destination, arch):
	dirname = ''
	print('Extracting {0}'.format(filename))

	if filename.endswith('tar.gz'):
		tfile = tarfile.open(filename, 'r:gz')
		tfile.extractall(destination)
		dirname= tfile.getnames()[0]
	elif filename.endswith('zip'):
                if arch == 'opencpu':
                    destination = 'arm-none-eabi-opencpu'
		zfile = zipfile.ZipFile(filename)
		dirname = zfile.namelist()[0].split('/')[0]
		zfile.extractall(destination)
	elif filename.endswith('tar.bz2'):
		tfile = tarfile.open(filename, 'r:bz2')
		tfile.extractall(destination)
		dirname= tfile.getnames()[0].split('/')[0]
	else:
		raise NotImplementedError('Unsupported archive type')

	# a little trick to rename tool directories so they don't contain version number
        if arch == 'opencpu':
            rename_to = 'arm-none-eabi-opencpu'
        else:
            rename_to = re.match(r'^([a-z][^\-]*\-*)+', dirname).group(0).encode('ascii').strip('-')

	if rename_to != dirname:
	    print('Renaming {0} to {1}'.format(dirname, rename_to))
	    if os.path.isdir(rename_to):
		shutil.rmtree(rename_to)
	    shutil.move(dirname, rename_to)

def get_tool(tool, arch):
	archive_name = tool['archiveFileName']
	local_path = dist_dir + archive_name
	url = tool['url']
	real_hash = tool['checksum'].split(':')[1]
	if not os.path.isfile(local_path):
		print('Downloading ' + archive_name);
		urllib.urlretrieve(url, local_path, report_progress)
		sys.stdout.write("\rDone\n")
		sys.stdout.flush()
	else:
		print('Tool {0} already downloaded'.format(archive_name))
	local_hash = sha256sum(local_path)
	if local_hash != real_hash:
		print('Hash mismatch for {0}, delete the file and try again'.format(local_path))
		raise RuntimeError()

	if archive_name == 'gcc-arm-none-eabi-7-2017-q4-major-win32.zip':
		tc_dir = 'gcc-arm-none-eabi';
		mkdir_p(tc_dir)
		unpack(local_path, tc_dir, arch)
	else:
		unpack(local_path, '.', arch)

def load_tools_list(filename, platform, arch):

	if arch == 'opencpu':
		tools_info = json.load(open(filename))['packages'][1]['tools']
	elif arch == 'avr':
		tools_info = json.load(open(filename))['packages'][2]['tools']
	elif arch == 'efm32':
		tools_info = json.load(open(filename))['packages'][3]['tools']
	elif arch == 'esp8266' or arch == 'esp32':
		tools_info = json.load(open(filename))['packages'][0]['tools']
	else:
		#esp8266
		tools_info = json.load(open(filename))['packages'][0]['tools']

	tools_to_download = []
	for t in tools_info:
		tool_platform = [p for p in t['systems'] if p['host'] == platform]
		if len(tool_platform) == 0:
			continue
		tools_to_download.append(tool_platform[0])
	return tools_to_download

def identify_platform():
	arduino_platform_names = {'Darwin'  : {32 : 'i386-apple-darwin', 64 : 'x86_64-apple-darwin'},
							  'Linux'   : {32 : 'i686-pc-linux-gnu', 64 : 'x86_64-pc-linux-gnu'},
							  'Windows' : {32 : 'i686-mingw32',	  64 : 'i686-mingw32'}}
	bits = 32
	if sys.maxsize > 2**32:
		bits = 64
	sys_name = platform.system()
	if 'CYGWIN_NT' in sys_name:
		sys_name = 'Windows'
	return arduino_platform_names[sys_name][bits]

def move_p(src, dst):
	try:
		shutil.move(src, dst)
	except shutil.Error as exc:
		if exc.errno == errno.EEXIST:
			raise

if __name__ == '__main__':

	if len(sys.argv) > 1:
		arch = sys.argv[1]
	else:
		arch = 'esp8266'

	print('Current platform is: {0}'.format(identify_platform()))
	mkdir_p(dist_dir)
	tools_to_download = load_tools_list(dist_dir + '/package_list.json', identify_platform(), arch)

	if arch == 'opencpu':
		print("Generate the toolchain of the OpenCPU...")
		for tool in tools_to_download:
			get_tool(tool, arch)
	elif arch == 'efm32':
		print("Generate the toolchain of the EFM32...")
		for tool in tools_to_download:
			get_tool(tool, arch)
	elif arch == 'avr':
		print("Generate the toolchain of the AVR...")
		for tool in tools_to_download:
			get_tool(tool, arch)
	else:
            for tool in tools_to_download:
                get_tool(tool, arch)
            if os.path.isfile('esptool/esptool'):
                move_p('esptool/esptool', 'bin/')
            if os.path.isfile('esptool/esptool.exe'):
                move_p('esptool/esptool.exe', 'bin/')
            if os.path.isfile('mkspiffs/mkspiffs'):
                move_p('mkspiffs/mkspiffs', 'bin/')
            if os.path.isfile('mkspiffs/mkspiffs.exe'):
                move_p('mkspiffs/mkspiffs.exe', 'bin/')
            shutil.rmtree('mkspiffs/')
            shutil.rmtree('esptool/')
