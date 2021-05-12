#!/usr/bin/env python

from ConfigParser import ConfigParser
import os
import os.path
import subprocess


def read_conf(cfgfile='rose-app-run.conf'):
    '''
    Read rose config file and extract all sections starting "um_ancil:"
    '''
    config = ConfigParser()
    config.read(cfgfile)
    links = {}
    for section in config.sections():
        if section.startswith('um_ancil:'):
            lfile = section.replace('um_ancil:', '')
            adir = config.get(section, 'dir')
            afile = config.get(section, 'file')
            links[lfile] = (adir, afile)
    return links


# Create mapping for links and targets
def read_links(ldir):
    '''
    After reading rose config file, expand links (keys) to fully resolved paths
    '''
    # Read information from rose-app-run.conf file
    links = read_conf()
    # Resolve any environment variables in ldir
    ldir = os.path.expandvars(ldir)
    for (key, value) in links.items():
        # Resolve any environment variables in key
        key = os.path.expandvars(key)
        # If link is a relative path name then prepend link dir
        #  and replace link in dictionary
        if not os.path.isabs(key):
            del links[key]
            links[os.path.join(ldir, key)] = value
    return links


def read_ancilvn(ancilvn_file):
    '''
    Read in ancil versions file and return contents in a dictionary where keys
    are environment variables and values are fully resolved paths
    '''
    ancilvn = {}
    # Read ancil_versions file so variables in bash environment
    command = ['bash', '-c', 'source '+ancilvn_file+' && env']
    proc = subprocess.Popen(command, stdout = subprocess.PIPE)
    for line in proc.stdout:
        (key, _, value) = line.strip().partition("=")
        if key.startswith('UM_'):
            ancilvn[key] = os.path.expandvars(value)
    proc.communicate()
    return ancilvn


def resolve_links(links, ancilvn):
    '''
    Map required ancillaries to a pair of key names, one for the
    directory and one for the file name. If the keys do not exist then it is
    assumed that the entry is a definitive path. The returned dictionary is a
    map from the ancillary link name to a fully resolved target ancillary.
    '''
    for (link, (adir, afile)) in links.items():
        target = os.path.join(ancilvn.get(adir, adir),
                              ancilvn.get(afile, afile))
        # Resolve any environment variables in link and target and replace
        #  existing link in dictionary
        del links[link]
        links[os.path.expandvars(link)] = os.path.expandvars(target)


def create_symlinks(links):
    '''
    Create symbolic links for all existing ancillary files
    '''
    for (link, target) in links.items():
        # Make sure links and targets are fully resolved
        link = os.path.expandvars(link)
        target = os.path.expandvars(target)
        print 'Link {0} to {1}'.format(link, target)

        # Make sure link dir exists
        ldir = os.path.dirname(link)
        if not os.path.isdir(ldir):
            print '>> Creating link directory'
            os.makedirs(ldir)

        # Remove any existing links
        if os.path.exists(link):
            print '>> Removing existing link'
            os.remove(link)

        # If target exists then create link
        if os.path.isfile(target):
            os.symlink(target, link)
        else:
            print '>> Cannot create link as target does not exist'


def main():
    ancilvn_file = os.environ['ANCILVNFILE']
    link_dir = os.environ['ANCILDIR']

    ancilvn = read_ancilvn(ancilvn_file)
    links = read_links(link_dir)

    resolve_links(links, ancilvn)
    create_symlinks(links)

if __name__ == '__main__':
    main()
