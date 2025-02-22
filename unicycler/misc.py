"""
Copyright 2017 Ryan Wick (rrwick@gmail.com)
https://github.com/rrwick/Unicycler

This module contains miscellaneous functions used by various parts of Unicycler.

This file is part of Unicycler. Unicycler is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version. Unicycler is distributed in
the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details. You should have received a copy of the GNU General Public License along with Unicycler. If
not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os
import subprocess
import random
import math
import gzip
import argparse
import shutil
import re
import textwrap
import datetime
import multiprocessing
from . import settings
from . import log


REV_COMP_DICT = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G',
                 'a': 't', 't': 'a', 'g': 'c', 'c': 'g',
                 'R': 'Y', 'Y': 'R', 'S': 'S', 'W': 'W',
                 'K': 'M', 'M': 'K', 'B': 'V', 'V': 'B',
                 'D': 'H', 'H': 'D', 'N': 'N',
                 'r': 'y', 'y': 'r', 's': 's', 'w': 'w',
                 'k': 'm', 'm': 'k', 'b': 'v', 'v': 'b',
                 'd': 'h', 'h': 'd', 'n': 'n',
                 '.': '.', '-': '-', '?': '?'}

RANDOM_SEQ_DICT = {0: 'A', 1: 'C', 2: 'G', 3: 'T'}


def float_to_str(num, decimals, max_num=0):
    """
    Converts a number to a string. Will add left padding based on the max value to ensure numbers
    align well. Will also add commas to numbers over 1000.
    """
    if decimals == 0:
        return int_to_str(int(round(num)), max_num=max_num)
    if num is None:
        num_str = 'n/a'
    else:
        num_str = '%.' + str(decimals) + 'f'
        num_str = num_str % num
        parts = num_str.split('.')
        before_decimal = parts[0]
        after_decimal = parts[1]
        num_str = int_to_str(int(before_decimal)) + '.' + after_decimal
    if max_num > 0:
        max_str = float_to_str(max_num, decimals)
        num_str = num_str.rjust(len(max_str))
    return num_str


def int_to_str(num, max_num=0):
    """
    Converts a number to a string. Will add left padding based on the max value to ensure numbers
    align well.
    """
    if num is None:
        num_str = 'n/a'
    else:
        num_str = '{:,}'.format(num)
    max_str = '{:,}'.format(int(max_num))
    return num_str.rjust(len(max_str))


def check_input_files(args):
    """
    Checks to make sure all files in the list are present and either program, as needed.
    """
    if args.short1:
        check_file_exists(args.short1)
    if args.short2:
        check_file_exists(args.short2)
    if args.unpaired:
        check_file_exists(args.unpaired)
    if args.long:
        check_file_exists(args.long)
    if args.existing_long_read_assembly:
        check_file_exists(args.existing_long_read_assembly)
    if args.short1 and args.short2 and args.short1 == args.short2:
        quit_with_error('first and second read pair files cannot be the same file')


def check_file_exists(filename):
    """
    Checks to make sure the single given file exists.
    """
    if not os.path.isfile(filename):
        quit_with_error('could not find ' + filename)


def quit_with_error(message):
    """
    Displays the given message and ends the program's execution.
    """
    log.log('Error: ' + message, 0, stderr=True)
    sys.exit(1)


def check_spades(spades_path):
    """
    Makes sure the SPAdes executable is available.
    """
    if shutil.which(spades_path) is None:
        quit_with_error('could not find SPAdes at ' + spades_path)

    command = [spades_path, '-h']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()

    if not err.decode():
        quit_with_error('SPAdes was found but does not produce output (make sure to use '
                        '"spades.py" location, not "spades")')


def get_nice_header(header):
    """
    For a header with a SPAdes/Velvet format, this function returns a simplified string that is
    just NODE_XX where XX is the contig number.
    For any other format, this function trims off everything following the first whitespace.
    """
    if is_header_spades_format(header):
        return 'NODE_' + header.split('_')[1]
    else:
        return header.split()[0]


def is_header_spades_format(contig_name):
    """
    Returns whether or not the header appears to be in the SPAdes/Velvet format.
    Example: NODE_5_length_150905_cov_4.42519
    """
    contig_name_parts = contig_name.split('_')
    return len(contig_name_parts) > 5 and \
        (contig_name_parts[0] == 'NODE' or contig_name_parts[0] == 'EDGE') and \
        contig_name_parts[2] == 'length' and contig_name_parts[4] == 'cov'


def reverse_complement(seq):
    """
    Given a DNA sequences, this function returns the reverse complement sequence.
    """
    return ''.join([complement_base(x) for x in seq][::-1])


def complement_base(base):
    """
    Given a DNA base, this returns the complement.
    """
    try:
        return REV_COMP_DICT[base]
    except KeyError:
        return 'N'


def get_random_base():
    """
    Returns a random base with 25% probability of each.
    """
    return RANDOM_SEQ_DICT[random.randint(0, 3)]


def get_random_sequence(length):
    """
    Returns a random sequence of the given length.
    """
    return ''.join([get_random_base() for _ in range(length)])


def get_percentile(unsorted_list, percentile):
    """
    Returns a percentile of a list of numbers. Doesn't assume the list has already been sorted.
    Implements the nearest rank method:
    https://en.wikipedia.org/wiki/Percentile#The_Nearest_Rank_method
    """
    return get_percentile_sorted(sorted(unsorted_list), percentile)


def get_percentile_sorted(sorted_list, percentile):
    """
    Same as the above function, but assumes the list is already sorted.
    """
    if not sorted_list:
        return 0.0
    fraction = percentile / 100.0
    rank = int(math.ceil(fraction * len(sorted_list)))
    if rank == 0:
        return sorted_list[0]
    return sorted_list[rank - 1]


def weighted_average(num_1, num_2, weight_1, weight_2):
    """
    A simple weighted mean of two numbers.
    """
    weight_sum = weight_1 + weight_2
    if weight_sum == 0:
        return (num_1 + num_2) / 2.0
    return num_1 * (weight_1 / weight_sum) + num_2 * (weight_2 / weight_sum)


def weighted_average_list(nums, weights):
    """
    A simple weighted mean of a list of numbers.
    """
    weight_sum = sum(weights)
    if weight_sum == 0.0:
        weights = [1.0] * len(nums)
    return sum(num * (weights[i] / weight_sum) for i, num in enumerate(nums))


def round_to_nearest_odd(num):
    return 2 * round((num - 1) / 2) + 1


def get_compression_type(filename):
    """
    Attempts to guess the compression (if any) on a file using the first few bytes.
    http://stackoverflow.com/questions/13044562
    """
    magic_dict = {'gz': (b'\x1f', b'\x8b', b'\x08'),
                  'bz2': (b'\x42', b'\x5a', b'\x68'),
                  'zip': (b'\x50', b'\x4b', b'\x03', b'\x04')}
    max_len = max(len(x) for x in magic_dict)
    with open(filename, 'rb') as unknown_file:
        file_start = unknown_file.read(max_len)
    compression_type = 'plain'
    for file_type, magic_bytes in magic_dict.items():
        if file_start.startswith(magic_bytes):
            compression_type = file_type
    if compression_type == 'bz2':
        quit_with_error('cannot use bzip2 format - use gzip instead')
    if compression_type == 'zip':
        quit_with_error('cannot use zip format - use gzip instead')
    return compression_type


def get_open_function(filename):
    """
    Returns either open or gzip.open, as appropriate for the file.
    """
    if get_compression_type(filename) == 'gz':
        return gzip.open
    else:  # plain text
        return open


def get_sequence_file_type(filename):
    """
    Determines whether a file is FASTA or FASTQ.
    """
    if not os.path.isfile(filename):
        quit_with_error('could not find ' + filename)

    open_func = get_open_function(filename)
    with open_func(filename, 'rt') as seq_file:
        try:
            first_char = seq_file.read(1)
        except UnicodeDecodeError:
            first_char = ''

    if first_char == '>':
        return 'FASTA'
    elif first_char == '@':
        return 'FASTQ'
    else:
        raise ValueError('File is neither FASTA or FASTQ')


def get_num_agreement(num_1, num_2):
    """
    Returns a value between 0.0 and 1.0 describing how well the numbers agree.
    1.0 is perfect agreement and 0.0 is the worst.
    """
    if num_1 == 0.0 and num_2 == 0.0:
        return 1.0
    if num_1 < 0.0 and num_2 < 0.0:
        num_1 *= -1
        num_2 *= -1
    if num_1 * num_2 < 0.0:
        return 0.0
    return min(num_1, num_2) / max(num_1, num_2)


def flip_number_order(num_1, num_2):
    """
    Given two segment numbers, this function possibly flips them around. It returns the new numbers
    (either unchanged or flipped) and whether or not a flip took place. The decision is somewhat
    arbitrary, but it needs to be consistent so when we collect bridging read sequences they are
    always in the same direction.
    """
    if num_1 > 0 and num_2 > 0:
        flip = False
    elif num_1 < 0 and num_2 < 0:
        flip = True
    elif num_1 < 0:  # only num_1 is negative
        flip = abs(num_1) > abs(num_2)
    else:  # only num_2 is negative
        flip = abs(num_2) > abs(num_1)
    if flip:
        return (-num_2, -num_1), True
    else:
        return (num_1, num_2), False


def load_fasta(filename):
    """
    Returns a list of tuples (name, seq) for each record in the fasta file.
    """
    fasta_seqs = []
    open_func = get_open_function(filename)
    with open_func(filename, 'rt') as fasta_file:
        name = ''
        sequence = ''
        for line in fasta_file:
            line = line.strip()
            if not line:
                continue
            if line[0] == '>':  # Header line = start of new contig
                if name:
                    fasta_seqs.append((name.split()[0], sequence))
                    sequence = ''
                name = line[1:]
            else:
                sequence += line
        if name:
            fasta_seqs.append((name.split()[0], sequence))
    return fasta_seqs


def load_fasta_with_full_header(filename):
    """
    Returns a list of tuples (name, header, seq) for each record in the fasta file.
    """
    fasta_seqs = []
    open_func = get_open_function(filename)
    with open_func(filename, 'rt') as fasta_file:
        name = ''
        sequence = ''
        for line in fasta_file:
            line = line.strip()
            if not line:
                continue
            if line[0] == '>':  # Header line = start of new contig
                if name:
                    fasta_seqs.append((name.split()[0], name, sequence))
                    sequence = ''
                name = line[1:]
            else:
                sequence += line
        if name:
            fasta_seqs.append((name.split()[0], name, sequence))
    return fasta_seqs


def score_function(val, half_score_val):
    """
    For inputs of 0.0 and greater, this function returns a value between 0.0 and 1.0, approaching
    1.0 with large values. The half_score_val argument is the point at which the function returns
    0.5. If it's large the function approaches 1.0 more slowly, if it's small the function
    approaches 1.0 more quickly.
    """
    return 1.0 - (half_score_val / (half_score_val + val))


def strip_read_extensions(read_file_name):
    """
    This function removes extensions from a file name.
    """
    base_name = os.path.basename(read_file_name)
    name_parts = base_name.split('.')

    endings_to_trim = ['gz', 'fasta', 'fna', 'fa', 'fas', 'fsa', 'fastq', 'fq']
    while name_parts[-1].lower() in endings_to_trim:
        name_parts = name_parts[:-1]
    return '.'.join(name_parts)


def add_line_breaks_to_sequence(sequence, line_length=0):
    """
    Wraps sequences to the defined length.  All resulting sequences end in a line break.
    """
    if not sequence:
        return '\n'
    if line_length <= 0:
        line_length = settings.BASES_PER_FASTA_LINE
    seq_with_breaks = ''
    pos = 0
    while pos < len(sequence):
        seq_with_breaks += sequence[pos:pos+line_length] + '\n'
        pos += line_length
    return seq_with_breaks


END_FORMATTING = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
RED = '\033[31m'
GREEN = '\033[32m'
MAGENTA = '\033[35m'
YELLOW = '\033[93m'
DIM = '\033[2m'


class MyHelpFormatter(argparse.HelpFormatter):
    """
    This is a custom formatter class for argparse. It allows for some custom formatting,
    in particular for the help texts with multiple options (like bridging mode and verbosity level).
    http://stackoverflow.com/questions/3853722
    """
    def __init__(self, prog):
        terminal_width = shutil.get_terminal_size().columns
        os.environ['COLUMNS'] = str(terminal_width)
        max_help_position = min(max(24, terminal_width // 3), 40)
        try:
            self.colours = int(subprocess.check_output(['tput', 'colors']).decode().strip())
        except (ValueError, subprocess.CalledProcessError, FileNotFoundError, AttributeError):
            self.colours = 1
        super().__init__(prog, max_help_position=max_help_position)

    def _get_help_string(self, action):
        """
        Override this function to add default values, but only when 'default' is not already in the
        help text.
        """
        help_text = action.help
        if action.default != argparse.SUPPRESS and 'default' not in help_text.lower() and \
                action.default is not None:
            help_text += ' (default: ' + str(action.default) + ')'
        return help_text

    def start_section(self, heading):
        """
        Override this method to add bold underlining to section headers.
        """
        if self.colours > 1:
            heading = BOLD + heading + END_FORMATTING
        super().start_section(heading)

    def _split_lines(self, text, width):
        """
        Override this method to add special behaviour for help texts that start with:
          'B|' - loop text to the column of the equals sign
          'R|' - loop text one option per line
        """
        if text.startswith('B|') or text.startswith('R|'):
            text_lines = text[2:].splitlines()
            wrapped_text_lines = []
            for line in text_lines:
                if len(line) <= width:
                    wrapped_text_lines.append(line)
                else:
                    wrap_column = 2
                    if text.startswith('B|'):
                        line_parts = line.split()
                        wrap_column += line.find('=')
                        join = ''
                        current_line = '  ' + line_parts[0]
                    else:  # text.startswith('R|')
                        line_parts = line.split(', ')
                        join = ','
                        current_line = line_parts[0]
                    for part in line_parts[1:]:
                        if len(current_line) + len(join) + 1 + len(part) <= width:
                            current_line += join + ' ' + part
                        else:
                            wrapped_text_lines.append(current_line + join)
                            current_line = ' ' * wrap_column + part
                    wrapped_text_lines.append(current_line)
            return wrapped_text_lines
        else:
            return argparse.HelpFormatter._split_lines(self, text, width)

    def _fill_text(self, text, width, indent):
        if text.startswith('R|'):
            return ''.join(indent + line for line in text[2:].splitlines(keepends=True))
        else:
            return argparse.HelpFormatter._fill_text(self, text, width, indent)

    def _format_action(self, action):
        """
        Override this method to make help descriptions dim.
        """
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2,
                            self._max_help_position)
        help_width = self._width - help_position
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # ho nelp; start on same line and add a final newline
        if not action.help:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = 0

        # short action name; start on the same line and pad two spaces
        elif len(action_header) <= action_width:
            tup = self._current_indent, '', action_width, action_header
            action_header = '%*s%-*s  ' % tup
            indent_first = 0

        # long action name; start on the next line
        else:
            tup = self._current_indent, '', action_header
            action_header = '%*s%s\n' % tup
            indent_first = help_position

        # collect the pieces of the action help
        parts = [action_header]

        # if there was help for the action, add lines of help text
        if action.help:
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)
            first_line = help_lines[0]
            if self.colours > 8:
                first_line = DIM + first_line + END_FORMATTING
            parts.append('%*s%s\n' % (indent_first, '', first_line))
            for line in help_lines[1:]:
                if self.colours > 8:
                    line = DIM + line + END_FORMATTING
                parts.append('%*s%s\n' % (help_position, '', line))

        # or add a newline if the description doesn't end with one
        elif not action_header.endswith('\n'):
            parts.append('\n')

        # if there are any sub-actions, add their help as well
        for subaction in self._iter_indented_subactions(action):
            parts.append(self._format_action(subaction))

        # return a single string
        return self._join_parts(parts)


def print_table(table, alignments='', max_col_width=30, col_separation=3, indent=2,
                row_colour=None, sub_colour=None, row_extra_text=None, leading_newline=False,
                subsequent_indent='', return_str=False, header_format='underline',
                hide_header=False, fixed_col_widths=None, left_align_header=True,
                bottom_align_header=True, verbosity=1):
    """
    Args:
        table: a list of lists of strings (one row is one list, all rows should be the same length)
        alignments: a string of L and R, indicating the alignment for each row
        max_col_width: values longer than this will be wrapped
        col_separation: the number of spaces between columns
        indent: the number of spaces between the table and the left side of the terminal
        row_colour: a dictionary of row indices and their colour names
        sub_colour: a dictionary of values to colour names for which the text colour will be set
        row_extra_text: a dictionary of row indices and extra text to display after the row
        leading_newline: if True, the function will print a blank line above the table
        subsequent_indent: this string will be added to the start of wrapped text lines
        return_str: if True, this function will return a string of the table instead of printing it
        header_format: the formatting (colour, underline, etc) of the header line
        hide_header: if True, the header is not printed
        fixed_col_widths: a list to specify exact column widths (automatic if not used)
        left_align_header: if False, the header will follow the column alignments
        bottom_align_header: if False, the header will align to the top, like other rows
        verbosity: the table will only be logged if the logger verbosity is >= this value
    """
    column_count = len(table[0])
    table = [x[:column_count] for x in table]
    table = [x + [''] * (column_count - len(x)) for x in table]
    if row_colour is None:
        row_colour = {}
    if sub_colour is None:
        sub_colour = {}
    if row_extra_text is None:
        row_extra_text = {}
    if leading_newline:
        log.log('', verbosity)

    # Ensure the alignments string is the same length as the column count
    alignments += 'L' * (column_count - len(alignments))
    alignments = alignments[:column_count]

    if fixed_col_widths is not None:
        col_widths = fixed_col_widths
    else:
        col_widths = [0] * column_count
        for row in table:
            col_widths = [min(max(col_widths[i], len_without_format(x)), max_col_width)
                          for i, x in enumerate(row)]
    separator = ' ' * col_separation
    indenter = ' ' * indent
    full_table_str = ''
    for i, row in enumerate(table):
        row = [str(x) for x in row]
        if hide_header and i == 0:
            continue

        if fixed_col_widths is not None:
            wrapped_row = []
            for col, fixed_width in zip(row, fixed_col_widths):
                wrapper = textwrap.TextWrapper(subsequent_indent=subsequent_indent,
                                               width=fixed_width)
                wrapped_row.append(wrapper.wrap(col))
        else:
            wrapper = textwrap.TextWrapper(subsequent_indent=subsequent_indent, width=max_col_width)
            wrapped_row = [wrapper.wrap(x) for x in row]

        row_rows = max(len(x) for x in wrapped_row)
        if i == 0 and bottom_align_header:
            wrapped_row = [[''] * (row_rows - len(x)) + x for x in wrapped_row]

        for j in range(row_rows):
            row_line = [x[j] if j < len(x) else '' for x in wrapped_row]
            aligned_row = []
            for value, col_width, alignment in zip(row_line, col_widths, alignments):
                if alignment == 'L' or (i == 0 and left_align_header):
                    aligned_row.append(value.ljust(col_width))
                elif alignment == 'C':
                    aligned_row.append(value.center(col_width))
                else:
                    aligned_row.append(value.rjust(col_width))
            row_str = separator.join(aligned_row)
            if i in row_extra_text:
                row_str += row_extra_text[i]
            if i == 0 and header_format:
                row_str = colour(row_str, header_format)
            if i in row_colour:
                row_str = colour(row_str, row_colour[i])
            for text, colour_name in sub_colour.items():
                row_str = row_str.replace(text, colour(text, colour_name))
            if j < row_rows - 1 and UNDERLINE in row_str:
                row_str = re.sub('\033\[4m', '', row_str)
            if return_str:
                full_table_str += indenter + row_str + '\n'
            else:
                log.log(indenter + row_str, verbosity)
    if return_str:
        return full_table_str


def colour(text, text_colour):
    bold_text = 'bold' in text_colour
    text_colour = text_colour.replace('bold', '')
    underline_text = 'underline' in text_colour
    text_colour = text_colour.replace('underline', '')
    text_colour = text_colour.replace('_', '')
    text_colour = text_colour.replace(' ', '')
    text_colour = text_colour.lower()
    if 'red' in text_colour:
        coloured_text = RED
    elif 'green' in text_colour:
        coloured_text = GREEN
    elif 'yellow' in text_colour:
        coloured_text = YELLOW
    elif 'dim' in text_colour:
        coloured_text = DIM
    else:
        coloured_text = ''
    if bold_text:
        coloured_text += BOLD
    if underline_text:
        coloured_text += UNDERLINE
    if not coloured_text:
        return text
    coloured_text += text + END_FORMATTING
    return coloured_text


def green(text):
    return GREEN + text + END_FORMATTING


def bold_green(text):
    return GREEN + BOLD + text + END_FORMATTING


def red(text):
    return RED + text + END_FORMATTING


def magenta(text):
    return MAGENTA + text + END_FORMATTING


def bold_red(text):
    return RED + BOLD + text + END_FORMATTING


def bold(text):
    return BOLD + text + END_FORMATTING


def bold_underline(text):
    return BOLD + UNDERLINE + text + END_FORMATTING


def underline(text):
    return UNDERLINE + text + END_FORMATTING


def dim(text):
    return DIM + text + END_FORMATTING


def dim_underline(text):
    return DIM + UNDERLINE + text + END_FORMATTING


def bold_yellow(text):
    return YELLOW + BOLD + text + END_FORMATTING


def bold_yellow_underline(text):
    return YELLOW + BOLD + UNDERLINE + text + END_FORMATTING


def bold_red_underline(text):
    return RED + BOLD + UNDERLINE + text + END_FORMATTING


def len_without_format(text):
    try:
        return len(remove_formatting(text))
    except TypeError:
        return len(str(text))


def remove_formatting(text):
    return re.sub('\033.*?m', '', text)


def get_ascii_art():
    ascii_art = (bold_red("       __\n") +
                 bold_red("       \ \___\n") +
                 bold_red("        \ ___\\\n") +
                 bold_red("        //\n") +
                 bold_red("   ____//      ") +
                 bold_yellow("_    _         _                     _\n") +
                 bold_red(" //_  //\\\\    ") +
                 bold_yellow("| |  | |       |_|                   | |\n") +
                 bold_red("//  \\//  \\\\   ") +
                 bold_yellow("| |  | | _ __   _   ___  _   _   ___ | |  ___  _ __\n") +
                 bold_red("||  (O)  ||   ") +
                 bold_yellow("| |  | || '_ \ | | / __|| | | | / __|| | / _ \| '__|\n") +
                 bold_red("\\\\    \_ //   ") +
                 bold_yellow("| |__| || | | || || (__ | |_| || (__ | ||  __/| |\n") +
                 bold_red(" \\\\_____//     ") +
                 bold_yellow("\____/ |_| |_||_| \___| \__, | \___||_| \___||_|\n") +
                 bold_yellow("                                        __/ |\n") +
                 bold_yellow("                                       |___/"))
    return ascii_art


def get_timestamp():
    return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())


def get_dim_timestamp():
    return dim('(' + get_timestamp() + ')')


def get_left_arrow():
    """
    This function returns either a Unicode left arrow or '<-', depending on the system encoding.
    """
    try:
        '\u2190'.encode(sys.stdout.encoding)
    except (AttributeError, UnicodeEncodeError):
        return '<-'
    else:
        return '\u2190 '


def get_right_arrow():
    """
    This function returns either a Unicode right arrow or '->', depending on the system encoding.
    """
    try:
        '\u2192'.encode(sys.stdout.encoding)
    except (AttributeError, UnicodeEncodeError):
        return '->'
    else:
        return '\u2192'


def get_default_thread_count():
    return min(multiprocessing.cpu_count(), settings.MAX_AUTO_THREAD_COUNT)


def spades_path_and_version(spades_path):
    found_spades_path = shutil.which(spades_path)
    if found_spades_path is None:
        return spades_path, '', 'not found'
    command = [found_spades_path, '-v']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = process.communicate()
    out = out.decode()

    if not out or 'Verification of expression' in out:
        return found_spades_path, '', 'bad'
    version = spades_version_from_spades_output(out)

    if 'python version' in out and 'is not supported' in out:
        return found_spades_path, '', 'Python problem'

    # Make sure SPAdes is 3.13.1 or later
    try:
        status = spades_status_from_version(version)
    except (ValueError, IndexError):
        version, status = '?', 'too old'

    return found_spades_path, version, status


def spades_version_from_spades_output(spades_output):
    """
    Parses the SPAdes version from the output of spades.py -v
    """
    try:
        return re.search(r'v(\d+\.\d+\.\d+)', spades_output).group(1)
    except (AttributeError, IndexError):
        pass
    try:
        return re.search(r'v\.(\d+\.\d+\.\d+)', spades_output).group(1)
    except (AttributeError, IndexError):
        pass
    try:
        return re.search(r'\d+\.\d+\.\d+', spades_output).group()
    except (AttributeError, IndexError):
        pass
    return ''


def spades_status_from_version(version):
    quit_with_error('Version:' + str(version))
    major_version = int(version.split('.')[0])
    if major_version < 3:
        return 'too old'
    if major_version >= 4:
        return 'too new'
    assert major_version == 3

    minor_version = int(version.split('.')[1])
    if minor_version < 14:
        return 'too old'
    else:
        return 'good'


def racon_path_and_version(racon_path):
    found_racon_path = shutil.which(racon_path)
    if found_racon_path is None:
        return racon_path, '', 'not found'
    command = [found_racon_path]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = process.communicate()
    out = out.decode().lower()
    if 'racon' not in out or 'options' not in out:
        return found_racon_path, '-', 'bad'

    return found_racon_path, racon_version(found_racon_path), 'good'


def racon_version(found_racon_path):
    command = [found_racon_path, '--version']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = process.communicate()
    out = out.decode().lower()
    try:
        return re.search(r'(\d+\.\d+\.\d+)', out).group(1)
    except (AttributeError, IndexError):
        return '-'


def makeblastdb_path_and_version(makeblastdb_path):
    found_makeblastdb_path = shutil.which(makeblastdb_path)
    if found_makeblastdb_path is None:
        return makeblastdb_path, '', 'not found'
    command = [found_makeblastdb_path, '-version']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = process.communicate()
    version = out.decode().split('makeblastdb: ')[-1].split()[0]
    try:
        int(version.split('.')[0]), int(version.split('.')[1])
    except (ValueError, IndexError):
        version, status = '?', 'too old'
    return found_makeblastdb_path, version, 'good'


def tblastn_path_and_version(tblastn_path):
    found_tblastn_path = shutil.which(tblastn_path)
    if found_tblastn_path is None:
        return tblastn_path, '', 'not found'
    command = [found_tblastn_path, '-version']
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = process.communicate()
    version = out.decode().split('tblastn: ')[-1].split()[0]
    try:
        int(version.split('.')[0]), int(version.split('.')[1])
    except (ValueError, IndexError):
        version, status = '?', 'too old'
    return found_tblastn_path, version, 'good'


def line_iterator(string_with_line_breaks):
    """Iterates over a string containing line breaks, one line at a time."""
    prev_newline = -1
    while True:
        next_newline = string_with_line_breaks.find('\n', prev_newline + 1)
        if next_newline < 0:
            break
        yield string_with_line_breaks[prev_newline + 1:next_newline]
        prev_newline = next_newline


def range_overlap(x1, x2, y1, y2):
    """
    Returns true if the range (x1, x2) overlaps with the range (y1, y2).
    """
    return x1 < y2 and y1 < x2


def range_is_contained(test_range, other_ranges):
    """
    Returns True if test_range is entirely contained within any range in other_ranges.
    """
    start, end = test_range
    for other_range in other_ranges:
        if other_range[0] <= start and other_range[1] >= end:
            return True
    return False


def range_overlap_size(test_range, other_ranges):
    start, end = test_range
    max_overlap = 0
    for other_range in other_ranges:
        max_overlap = max(max_overlap, min(end, other_range[1]) - max(start, other_range[0]))
    return max_overlap


def simplify_ranges(ranges):
    """
    Collapses overlapping ranges together. Input ranges are tuples of (start, end) in the normal
    Python manner where the end isn't included.
    """
    fixed_ranges = []
    for int_range in ranges:
        if int_range[0] > int_range[1]:
            fixed_ranges.append((int_range[1], int_range[0]))
        elif int_range[0] < int_range[1]:
            fixed_ranges.append(int_range)
    starts_ends = [(x[0], 1) for x in fixed_ranges]
    starts_ends += [(x[1], -1) for x in fixed_ranges]
    starts_ends.sort(key=lambda x: x[0])
    current_sum = 0
    cumulative_sum = []
    for start_end in starts_ends:
        current_sum += start_end[1]
        cumulative_sum.append((start_end[0], current_sum))
    prev_depth = 0
    start = 0
    combined = []
    for pos, depth in cumulative_sum:
        if prev_depth == 0:
            start = pos
        elif depth == 0:
            combined.append((start, pos))
        prev_depth = depth
    return combined


def remove_dupes_preserve_order(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def gfa_path(out_dir, file_num, name):
    return os.path.join(out_dir, str(file_num).zfill(3) + '_' + name + '.gfa')


def get_first_character_of_file(filename):
    open_func = get_open_function(filename)
    with open_func(filename, 'r') as f:
        first_line = f.readline()
        try:
            return first_line[0]
        except IndexError:
            return ''
