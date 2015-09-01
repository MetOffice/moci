#!/usr/bin/env python2.7
def generateRunfile(runfile,opa,xios,ctasks,iotasks,spacing):
    print 'We generate {0} with commands({1};{2}) \n'.format(runfile,opa,xios)
    print '{0} compute tasks and {1} io tasks equally loaded with spacing of {2} \n'.\
           format(ctasks,iotasks,spacing)

    totaltasks=ctasks+iotasks

    if totaltasks%spacing == 0:
        nnodes=totaltasks/spacing
        print 'nnodes is '+str(nnodes)
    else:
        print 'ERROR:spacing must divide total tasks'

# Fill array of xiosPerNode[nnodes]
    xiosPerNode=[0 for n in range(nnodes)]
    index=0
    
    for counter in range(iotasks, 0, -1):
        xiosPerNode[index] += 1
        index=(index+1)%nnodes

# Now we can write the file
    with open(runfile,"w") as fp:
        for n in range(nnodes):
            for j in range(spacing-xiosPerNode[n]):
                            fp.write(opa+'\n')
            for i in range(xiosPerNode[n]):
                fp.write(xios+'\n')

if __name__ == '__main__':
    XIOS='hpmcount -o hpmserver ./xios_server.exe'
    OPA='./opa'
    RUNFILE='run_file'
    NNODES=5
    SPACING=32
    CTASKS=1024
    IOTASKS=64
    generateRunfile(RUNFILE,OPA,XIOS,CTASKS,IOTASKS,SPACING)
