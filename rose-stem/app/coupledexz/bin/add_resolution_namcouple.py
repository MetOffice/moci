#!/usr/bin/env python2.7
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2015 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    add_resolution_namcouple.py
    
SYNOPSIS
    add_resolution_namcouple.py
    
DESCRIPTION
    Unix callable routine to add resolution information to the namcouple file.
    Must be run in the same directory as the following three files:
       * namcouple
       * SIZES
       * namelist_cfg
       
ARGUMENTS
    none     
'''

import sys

# Print out that we are starting
this_exec = sys.argv[0]
print 'Editing namcouple file using executable '+this_exec

# What is the name of the namcouple file
namcouple_file='namcouple'
    
# Get the UM resolution information
f = open('SIZES','r')
for line in f:
  
   # Get the data
   split_line = line.split('=')
   if split_line[0] == 'global_row_length': atm_x = int(split_line[1].split(',')[0])
   if split_line[0] == 'global_rows': atm_y = int(split_line[1].split(',')[0])

f.close()
print 'atm_x = ',atm_x
print 'atm_y = ',atm_y

# Get the ocean resolution information
f = open('namelist_cfg','r')
for line in f:
  
   # Get the data
   split_line = line.split('=')
   if split_line[0] == 'jpiglo': ocean_x = int(split_line[1].split(',')[0])
   if split_line[0] == 'jpjglo': ocean_y = int(split_line[1].split(',')[0])

f.close()
print 'ocean_x = ',ocean_x
print 'ocean_y = ',ocean_y

# Open the file
f = open(namcouple_file,'r')

# Set up some variables
lines_after_transdef=-1   # This counts the number of lines after a transdef
output=[]                 # This contains the output to be written to the namcouple file

# Loop over the contents of the namcouple file
for line in f:

    # Add one to lines_after_transdef
    if lines_after_transdef != -1: lines_after_transdef=lines_after_transdef+1
   
    # Are we at the transdef line
    if line[0:11] == "# TRANSDEF:": lines_after_transdef=0
   
    # Are we two lines after transdef
    if lines_after_transdef == 2:
        split_line = line.split()
       
        # Is there resolution information already in here
        try:
            aint = int(split_line[0])
        except ValueError:
           
	    # No resolution information. Make a string with this information in.
	    resolution_info=''
	    for model_info in split_line:
	        if model_info == 'tor1' or model_info == 'uor1' or model_info == 'vor1':
	            resolution_info="{}{} {} ".format(resolution_info,ocean_x,ocean_y)
	        if model_info == 'atm3' or model_info == 'aum3':
	            resolution_info="{}{} {} ".format(resolution_info,atm_x,atm_y)
	        if model_info == 'avm3':
	            resolution_info="{}{} {} ".format(resolution_info,atm_x,atm_y+1)
	   
	    # Add this string to the start of the original line
	    line = resolution_info + line
	   
    # Copy the line to the output
    output.append(line)

# Close the file
f.close()
    
# Output the new namcouple file
f = open(namcouple_file, 'w')
f.writelines(output)
f.close()

# Print out that we are finishing
print 'Finished editing namcouple file'
