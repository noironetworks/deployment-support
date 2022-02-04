import argparse
import json
import sys

class FileSplitter(object):

    def __init__(self, input_file, hashtree_type='config'):
        self.input_file = input_file
        self.hashtree_type = hashtree_type
        if hashtree_type == 'config':
            self.hashtree_sentinel = 'ConfigTree'
            self.outfile_suffix = "config"
        elif hashtree_type == 'monitor':
            self.hashtree_sentinel = 'MonitoredTree'
            self.outfile_suffix = "monitor"

    def get_hashtree_data(self):
        fd = open(self.input_file, 'r')
        self.alldata = fd.readlines()

    def split_hashtree_data(self):
        writefd = None
        for linedata in self.alldata:
           if self.hashtree_sentinel in linedata:
               if writefd:
                   writefd.close()
               tenant = linedata.strip().split()[-1][3:-1]
               outfile_name = "%s.%s" % (tenant, self.outfile_suffix)
               writefd = open(outfile_name, 'w')
           writefd.write(linedata)
        writefd.close()


def main():
    parser = argparse.ArgumentParser(description='Hashtree file splitter')

    parser.add_argument("-f", "--input_file", help="AIM Hashtree dump file",
                      dest="input_file")
    parser.add_argument("-t", "--type", help="Type of input file (config or monitor)",
                      dest='hashtree_type', default='config')
    options = parser.parse_args()

    splitter = FileSplitter(options.input_file, hashtree_type=options.hashtree_type)
    splitter.get_hashtree_data()
    splitter.split_hashtree_data()

if __name__ == "__main__":
    sys.exit(main())
