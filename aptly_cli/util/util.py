#! /usr/bin/env python
# -*- coding: utf-8 -*-

""" Util
Instance for utils and tools.
"""

import re
from os.path import expanduser, exists
from aptly_cli.api.api import AptlyApiRequests


class Util(object):

    """ Util
    Instance for utils and tools.
    """

    def __init__(self):
        """
        Init contstructor
        """
        self.api = AptlyApiRequests()

    @staticmethod
    def _atoi(text):
        """ _atoi
        Converts asci to int
        """
        return int(text) if text.isdigit() else text

    @staticmethod
    def create_init_file():
        """ create_init_file
        Will create a config file at home folder, if it does not exist.
        """
        home = expanduser("~")
        name = home + '/aptly-cli.conf'

        print "Look for already existing file..."

        if not exists(name):
            print 'Create_init_file'
            try:
                conf = open(name, 'a')
                conf.write('[general]\nbasic_url=http://localhost\nport=:9003\nsave_last_snap=3\n')
                conf.close()

            except:
                print('Something went wrong! Can\'t tell what?')

        else:
            print "File already exists! Stop action"
            print name

    def _natural_keys(self, text):
        """ _natural_keys
        Split up string at int.
        """
        return [self._atoi(c) for c in re.split('(\\d+)', text)]

    def _sort_out_last_n_snap(self, snaplist, prefix, nr_of_leftover, postfix=None):
        """ _sort_out_last_n_snap
        Returns n sorted items from given input list by prefix.
        """
        snapstaginglist = []
        for x in snaplist:
            if prefix in x[u'Name']:
                if postfix is None:
                    # end of string contains
                    snapstaginglist.append(x[u'Name'])
                else:
                    if postfix in x[u'Name']:
                        snapstaginglist.append(x[u'Name'])

        slen = len(snapstaginglist)
        snapstaginglist.sort(key=self._natural_keys)
        ret = []
        nr_o = int(nr_of_leftover)
        if slen > (nr_o - 1):
            for a in snapstaginglist[-nr_o:]:
                ret.append(a)
        else:
            ret = snapstaginglist

        return ret

    def get_last_snapshots(self, prefix, nr_of_vers, postfix=None):
        """ get_last_snapshots
        Returns n versions of snapshots, sorted out by a prefix and optional postfix.
        """
        snaplist = self.api.snapshot_list()
        if postfix is None:
            res = self._sort_out_last_n_snap(snaplist, prefix, nr_of_vers)
        else:
            res = self._sort_out_last_n_snap(snaplist, prefix, nr_of_vers, postfix)

        return res

    def clean_last_snapshots(self, prefix, nr_of_vers, postfix=None):
        """ clean_last_snapshots
        Cleans n versions of snapshots, sorted out by a prefix and optional postfix.
        """
        if postfix is None:
            items_to_delete = self.get_last_snapshots(prefix, nr_of_vers)
        else:
            items_to_delete = self.get_last_snapshots(prefix, nr_of_vers, postfix)

        nr_to_left_over = int(self.api.get_config_from_file()['save_last_snap'])

        if len(items_to_delete) > nr_to_left_over:
            for item in items_to_delete[:-nr_to_left_over]:
                if item:
                    # force removal
                    self.api.snapshot_delete(item, '1')

    def diff_both_last_snapshots_mirrors(self):
        """ diff_both_last_snapshots_mirrors
        Fetches out last two versions of snapshots from a given list of mirrors and diffs both.
        Return, if all mirrors have new content to update or not (EMPTY).
        """
        local_cfg = self.api.get_config_from_file()
        prefix_list = local_cfg['prefixes_mirrors'].split(', ')

        snaplist = self.api.snapshot_list()
        results = []
        result = ""

        for x in prefix_list:
            res_list = self._sort_out_last_n_snap(snaplist, x, 2)
            if len(res_list) >= 2:
                res = self.api.snapshot_diff(res_list[0], res_list[1])
                if not res:
                    results.append("EMPTY")
                else:
                    results.append(res)
                    break
            else:
                results.append("EMPTY")

        # print results
        result = ""
        for y in results:
            if y == "EMPTY":
                result = "EMPTY"
            else:
                result = y
                break

        print result

    def list_all_repos_and_packages(self):
        """
        """
        repos = self.api.repo_list()
        # print repos
        for repo in repos:
            print repo[u'Name']
            packs = self.api.repo_show_packages(repo[u'Name'])
            for pack in packs:
                print pack.split(', ')
            # [1] + packs[2]

