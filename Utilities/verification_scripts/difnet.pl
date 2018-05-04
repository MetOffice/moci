#!/usr/bin/env perl
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file COPYRIGHT.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# Interactive comparison of the contents of two netcdf files for 
# purposes of assessing bit comparison.
#
# You need access to ncdump, ncdiff and ncwa prior to running this
# program (e.g. typically on MO systems via "module load scitools"). 
#
# The process goes as follows:
# 1) ncdiff the two files
# 2) Extract a list of field names from the resulting difference file
# 3) Find the max of each field from the difference file => max.nc
# 4) Find the min of each field from the difference file => min.nc
# 5) Use ncdump to print the contents of these to max.txt and min.txt
# 6) Use tkdiff to compare the max and min values of each field. 
# 7) If the field values are identical then the max and min values 
#    should appear as 0 and tkdiff will detect no differences in the data:
#    section. 
#
# Author: R. Hill
# Date:   April 2018. 
###################################################################
use strict;
use File::Copy qw(move);

my $nargs = $#ARGV + 1;
if ($nargs != 2) {
    print "\nUsage: difnet.pl <netcdf file 1> <netcdf file 2>\n";
    exit;
}

my $file1 = $ARGV[0];
$file1 =~ s/^\s+|\s+$//g ;
my $file2 = $ARGV[1];
$file2 =~ s/^\s+|\s+$//g ;

my $command = "ncdump -k $file1";
my $return = system( "$command" );

if ( $return < 0 ) {
    print "* \n";
    print " NCO utilities appear unavailable!\n";
    print " Have you run: module load scitools (or equivalent\n";
    print " for your platform?) \n";
   
    exit;
}

if ( $return != 0 ) {
    print "* \n";
    print "\n $file1 does not appear to be a netcdf file.\n";
    exit;
}

if (! -f $file1) {
    print "* \n";
    print "\n $file1 is not a readable file.\n";
    exit;
}
   
$command = "ncdump -k $file2";
$return = system( "$command" );

if ( $return != 0 ) {
    print "* \n";
    print "\n $file2 does not appear to be a netcdf file.\n";
    exit;
}

if (! -f $file2) {
    print "* \n";
    print "\n $file2 is not a readable file.\n";
    exit;
}


# output netcdf dif file. 
my $file3 = "dif.nc";

if (-f $file3) {
    move $file3, "old_$file3";
}

$command = "ncdiff -O $file1 $file2 $file3";
print "* \n";
print "* Performing ncdiff on the two input files \n";
print "* \n";

my $result = system( "$command" );

if (! -r $file3) {
    print "* \n";
    print "\n: Difference file $file3 could not be created.\n";
    exit;
}

my $names = "stdnames";

$command = "ncdump -h $file3 | grep -E 'double |float ' > $names";
print "* \n";
print "* Extracting list of field names. \n";
print "* \n";

$result = system( "$command" );

open (my $infile, '<', $names);
my @lines = <$infile>;
close $infile;

my $vars = " ";
my $i = 0;
foreach my $line (@lines) {

  my @bits = split( /[ |(]/, $line );
  my $var = $bits[1];
  $var =~ s/^\s+|\s+$//g;

  $i = $i + 1;
     
  if ( $i > 1 ) {
     $vars = $vars . "," . $var;
  } else { 
     $vars = $var;
  }

}
print "* \n";
print "The following fields will be examined: $vars \n" ;
print "* \n";

print "* \n";
print "Extracting maximum and minimum field values from the difference file. \n" ;
print "* \n";

my $maxnc = "max.nc";
$command = "ncwa -y max -O -C -v  $vars  $file3 $maxnc";
$result = system( $command );
if (! -r $maxnc) {
    print "* \n";
    print "\n: Max file $maxnc could not be created.\n";
    exit;
}

my $maxtxt = "max.txt";
$command = "ncdump $maxnc > $maxtxt";
$result = system( $command );
if (! -r $maxtxt) {
    print "* \n";
    print "\n: Max summary file $maxtxt could not be created.\n";
    exit;
}

my $minnc = "min.nc";
$command = "ncwa -y min -O -C -v  $vars  $file3 $minnc";
$result = system( $command );
if (! -r $minnc) {
    print "* \n";
    print "\n: Min file $minnc could not be created.\n";
    exit;
}

my $mintxt = "min.txt";
$command = "ncdump $minnc > $mintxt";
$result = system( $command );
if (! -r $mintxt) {
    print "* \n";
    print "\n: Min summary file $mintxt could not be created.\n";
    exit;
}

print "* \n";
print "Comparing maximum and minimum field values from the difference file. \n" ;
print "All values are expected to be zero if your two input files contain identical filed values. \n" ;
print "* \n";

$command = "tkdiff $mintxt $maxtxt";
$result = system( $command );



