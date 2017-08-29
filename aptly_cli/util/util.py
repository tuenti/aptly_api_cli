#! /usr/bin/env python
# -*- coding: utf-8 -*-

""" Util
Instance for utils and tools.
"""

import re
import time
from os.path import expanduser, exists, basename
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
                conf.write(
                    '[general]\nbasic_url=https://aptly.tuenti.io\nport=:443\nsave_last_snap=3\nsave_last_pkg=10\nprefixes_mirrors=tuenti\npackage_prefixes=tuenti\nrepos_to_clean=tuenti\n\n[3rd_party]\nrepos=tuenti\nstaging_snap_pre_post=tuenti\n\n[auth]\nuser=\npassword=\n')
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
            res = self._sort_out_last_n_snap(
                snaplist, prefix, nr_of_vers, postfix)

        return res

    def clean_last_snapshots(self, prefix, nr_of_vers, postfix=None):
        """ clean_last_snapshots
        Cleans n versions of snapshots, sorted out by a prefix and optional postfix.
        """
        if postfix is None:
            items_to_delete = self.get_last_snapshots(prefix, nr_of_vers)
        else:
            items_to_delete = self.get_last_snapshots(
                prefix, nr_of_vers, postfix)

        nr_to_left_over = int(
            self.api.get_config_from_file()['save_last_snap'])

        if len(items_to_delete) > nr_to_left_over:
            for item in items_to_delete[:-nr_to_left_over]:
                if item:
                    # force removal
                    self.api.snapshot_delete(item, '1')
        else:
            print prefix
            print "Nothing to delete...."

    def repo_add_local_package(self, distro, package, repo=None, dir_name='tuenti'):
        """ repo_add_local_package
        Upload a local package and add it to a published repo
        """
        if repo is None:
            local_cfg = self.api.get_config_from_file()
            repo = local_cfg['repos'].split(', ')[0]
        real_repo = "%s_%s" % (repo, distro)
        package_name = basename(package)
        upload = self.api.file_upload(dir_name, package)
        if upload[0] == "%s/%s" % (dir_name, package_name):
            add = self.api.repo_add_package_from_upload(real_repo, dir_name,
                                                                package_name)
            if package_name.split('.deb')[0] in add['Report']['Added'][0]:
                print "Package uploaded, " + add['Report']['Added'][0]
                snapshot_list = self.api.snapshot_list()
                snapshot_name = real_repo + "_%d"
                current = int(time.strftime("%Y%m%d") + '00')
                while any(snp['Name'] == snapshot_name % (current) for
                                        snp in snapshot_list):
                    current += 1
                real_snapshot_name = snapshot_name % (current)
                snapshot = self.api.snapshot_create_from_local_repo(
                                        real_snapshot_name,
                                        real_repo,
                                        "add package %s" % (package_name))
                if any(snp['Name'] == real_snapshot_name for
                                        snp in self.api.snapshot_list()):
                    print "Snapshot %s created with new package" % (real_snapshot_name)
                    switch = self.api.publish_switch(repo,
                                        real_snapshot_name,
                                        distro, "main", 0)
                    if any(published['Sources'][0]['Name'] == real_snapshot_name for
                                                published in self.api.publish_list()):
                        return "Package uploaded, repo %s updated" % (repo)
                    else:
                        print "Error publishing repo %s " % (repo)
                        return switch
                else:
                  print "Error publishing snapshot"
                  print snapshot
            else:
              print "Error adding package to repo"
              print add
        else:
          print "Error uploading package"
          print upload

    def diff_both_last_snapshots_mirrors(self):
        """ diff_both_last_snapshots_mirrors
        Fetches out last two versions of snapshots from a given list of mirrors and diffs both.
        Return, if all mirrors have new content to update or not (EMPTY).
        """
        local_cfg = self.api.get_config_from_file()
        if local_cfg['prefixes_mirrors']:
            prefix_list = local_cfg['prefixes_mirrors'].split(', ')
        else:
            print "Error: Prefix list is empty: please add prefixes_mirrors to your configfile!"

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
        return result

    def list_all_repos_and_packages(self):
        """ list_all_repos_and_packages
        """
        repos = self.api.repo_list()
        for repo in repos:
            print repo[u'Name']
            packs = self.api.repo_show_packages(repo[u'Name'])
            for pack in packs:
                print pack

    def get_last_packages(self, repo_name, pack_prefix, nr_of_leftover, postfix=None):
        """ get_last_packages
        """
        resp = None
        packs = self.api.repo_show_packages(repo_name)
        if postfix:
            resp = self._sort_out_last_n_packages(packs, pack_prefix, nr_of_leftover, postfix)
        else:
            resp = self._sort_out_last_n_packages(packs, pack_prefix, nr_of_leftover)
        return resp

    def clean_last_packages(self, repo_name, pack_prefix, nr_of_leftover, postfix=None):
        """ clean_last_packages
        """
        items_to_delete = None
        if postfix:
            items_to_delete = self.get_last_packages(repo_name, pack_prefix, nr_of_leftover, postfix)
        else:
            items_to_delete = self.get_last_packages(repo_name, pack_prefix, nr_of_leftover)

        nr_to_left_over = int(
            self.api.get_config_from_file()['save_last_pkg'])

        print nr_to_left_over

        if len(items_to_delete) > nr_to_left_over:
            worklist = []
            for item in items_to_delete[:-nr_to_left_over]:
                if item:
                    print "Will remove..."
                    print item
                    worklist.append(item)

            self.api.repo_delete_packages_by_key(repo_name, worklist)
        else:
            print "Nothing to delete..."

    def _sort_out_last_n_packages(self, packlist, prefix, nr_of_leftover, postfix=None):
        """ _sort_out_last_n_snap
        Returns n sorted items from given input list by prefix.
        """
        # print packlist
        worklist = []
        for pack_blob in packlist:
            pack_tmp = pack_blob.split(' ')
            if pack_tmp[1] in prefix:
                worklist.append(pack_blob)
            # print pack_tmp[1]

        slen = len(worklist)
        worklist.sort(key=self._natural_keys)
        ret = []
        nr_o = int(nr_of_leftover)
        if slen > (nr_o - 1):
            for a in worklist[-nr_o:]:
                ret.append(a)
        else:
            ret = worklist

        return ret

    def clean_mirrored_snapshots(self):
        """ clean_mirrored_snapshots
        Clean out all snapshots that were taken from mirrors. The mirror entries are taken from config file.
        """
        print "clean mirrored snapshots"
        local_cfg = self.api.get_config_from_file()
        if local_cfg['prefixes_mirrors']:
            prefix_list = local_cfg['prefixes_mirrors'].split(', ')
        else:
            print "Error: Prefix list is empty: please add prefixes_mirrors to your configfile!"

        for x in prefix_list:
            self.clean_last_snapshots(x, 100)

    def clean_repo_packages(self):
        """ clean_repo_snapshots
        Clean out all snapshots that were taken from repos. The repo entries are taken from config file.
        """
        print "clean snapshots from repos"
        local_cfg = self.api.get_config_from_file()
        if local_cfg['repos_to_clean']:
            repo_list = local_cfg['repos_to_clean'].split(', ')
        else:
            print "Error: Prefix list is empty: please add repos_to_clean to your configfile!"

        if local_cfg['package_prefixes']:
            pack_pref_list = local_cfg['package_prefixes'].split(', ')
        else:
            print "Error: Prefix list is empty: please add package_prefixes to your configfile!"

        for repo_name in repo_list:
            print repo_name
            for pack_prefix in pack_pref_list:
                print pack_prefix
                self.clean_last_packages(repo_name, pack_prefix, 100)

    def publish_switch_3rdparty_production(self):
        """ publish_switch_s3_3rd_party_production
        Publish the latest 3rd party snapshot from staging to production, only if there is new content available.
        """
        print "publish_switch_s3_3rd_party_production"

        # Get Config
        local_cfg = self.api.get_config_from_file()
        if local_cfg['repos']:
            s3_list = local_cfg['repos'].split(', ')
        else:
            print "Error: Prefix list is empty: please add s3 buckets to your configfile!"

        if local_cfg['staging_snap_pre_post']:
            prefix_postfix = local_cfg['staging_snap_pre_post'].split(', ')
        else:
            print "Error: Prefix list is empty: please add staging_snap_pre_post to your configfile!"

        # Diff snapshots from mirrors
        # Temphack
        res = 'something'  # self.diff_both_last_snapshots_mirrors()

        # Decide if it should be released to production
        if res == "EMPTY":
            print "New snapshot has no new packages. No need to release to production!"
        else:
            print "New packages were found...", res

            # Get most actual snapshot from 3rdparty staging
            last_snap = self.get_last_snapshots(prefix_postfix[0], 1, prefix_postfix[1])
            print "This is the new snapshot: ", last_snap

            # publish snapshots to production on s3
            print ("Publish ", last_snap, s3_list[0])
            self.api.publish_switch(s3_list[0], last_snap, "precise", "main", 0)

            print ("Publish ", last_snap, s3_list[1])
            self.api.publish_switch(s3_list[1], last_snap, "precise", "main", 0)

            # clean out
            self.clean_mirrored_snapshots()
