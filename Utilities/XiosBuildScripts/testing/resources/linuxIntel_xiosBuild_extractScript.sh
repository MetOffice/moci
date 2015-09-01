#!/bin/ksh
fcm co svn://fcm1/xios.xm_svn/XIOS/branchs/xios-1.0@HEAD XIOS
cd XIOS
for i in tools/archive/*.tar.gz; do  tar -xzf $i; done
