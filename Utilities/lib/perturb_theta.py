#!/usr/bin/env python
'''
*****************************COPYRIGHT******************************
 (C) Crown copyright 2017-2021 Met Office. All rights reserved.

 Use, duplication or disclosure of this code is subject to the restrictions
 as set forth in the licence. If no licence has been raised with this copy
 of the code, the use, duplication or disclosure of it is strictly
 prohibited. Permission to do so must first be obtained in writing from the
 Met Office Information Asset Owner at the following address:

 Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
*****************************COPYRIGHT******************************
NAME
    perturb_theta.py

DESCRIPTION
    This is for restarting after a grid point instability.

    Perturb at the bit level the atmosphere theta field used by the ENDGame
    model (Section 0, Item 388).
    An option is provided to perturb an alternative STASH item if required.

    The perturbation is deterministic since the random number seed used is
    generated from a hash of the input filename.

AUTHORS
    Malcolm Roberts (Met Office)
    Erica Neininger (Met Office)

REQUIRED ARGUMENTS:
    inputfile: full path and filename of dump to be perturbed

OPTIONAL ARGUMENTS:
    --output, -o: Full path and filename of perturbed dump
                  Default value = "<input filename>_perturbed"
    --stash, -s:  STASH code to be perturbed
                  Default value = Sec 0, Item 388 (thetaVD after timestep)
'''

import sys
import os
import argparse

import numpy as np
import mule

EPSILON = sys.float_info.epsilon


def dummy_mule_validate(*args, **kwargs):
    '''
    Define a dummy Mule validation routine that does nothing.
    Required for dumps containing mixed full and sub-domain fields.
    '''
    pass


class ArgumentsError(Exception):
    '''
    Exception raised when there is an error detected in the argument list.
    '''
    def __init__(self, msg):
        print('[FATAL ERROR] ' + msg)
        raise SystemExit


class LSBPerturbOperator(mule.DataOperator):
    ''' Operator which adds LSB perturbations to a field '''
    def __init__(self, seed):
        self.seed = seed

    def new_field(self, source_field):
        ''' Creates the new field object '''
        field = source_field.copy()
        return field

    def transform(self, source_field, new_field):
        ''' Performs the data manipulation '''
        data = source_field.get_data()

        # Create an array of perturbations and apply them to the data
        gen_seed = False
        while not gen_seed:
            try:
                np.random.seed(seed=self.seed)
                gen_seed = True
            except ValueError:
                # Some versions of numpy limit the value of the seed
                self.seed = int(self.seed / 2)

        np.random.seed(seed=self.seed)
        random_numbers = (2.0 * np.random.random(data.shape) - 1.0) * EPSILON
        new_field = data + data * random_numbers
        # If the field defines MDI, reset missing points from original
        # field back to MDI in the output
        if hasattr(source_field, 'bmdi'):
            mdi = source_field.bmdi
            mask = (data == mdi)
            new_field[mask] = mdi
        return new_field


def main():
    ''' Main function '''
    parser = argparse.ArgumentParser(description=(
        'Add a bit level perturbation to the theta field for an '
        'ENDGame simulation (New Dynamics uses a different variable)'
        ))

    parser.add_argument('inputfile',
                        type=str,
                        help='Path to dump to perturb Dump filename')

    parser.add_argument('--output', '-o',
                        type=str,
                        help='Path to perturbed dump Perturbed dump filename',
                        default='')

    parser.add_argument('--stash', '-s',
                        type=int,
                        help='STASH code to be perturbed',
                        default=388)

    args = parser.parse_args()

    if args.stash == 388:
        print('Perturbing Field - Sec 0, Item 388: ThetaVD After Timestep')
    else:
        item = str(args.stash)
        if args.stash > 1000:
            sec = item[:-3]
            item = item[-3:]
        else:
            sec = '0'
        print('Perturbing Field - Sec {}, Item {}'.format(sec, item))

    dump_in = args.inputfile
    if not os.path.exists(dump_in):
        raise ArgumentsError('Input dump does not exist: ' + dump_in)

    if args.output == '':
        dump_out = os.path.join(os.getcwd(), dump_in + '_perturbed')
        print('Output dump name unspecified\n --> Output file = ' + dump_out)
    else:
        dump_out = args.output

    if os.path.exists(dump_out):
        raise ArgumentsError('Output dump already exists, will not overwrite: '
                             + dump_out)
    else:
        write_dir = os.path.dirname(dump_out)
        if write_dir and not os.path.isdir(write_dir):
            raise ArgumentsError('Directory to write ' + dump_out
                                 + ' does not exist')

    random_seed = abs(hash(dump_in))
    lsb_perturb_operator = LSBPerturbOperator(random_seed)

    dfile = mule.DumpFile.from_file(dump_in)
    for ifield, field in enumerate(dfile.fields):
        if field.lbrel in (2, 3) and field.lbuser4 == args.stash:
            dfile.fields[ifield] = lsb_perturb_operator(field)

    try:
        dfile.to_file(dump_out)
    except mule.validators.ValidateError as err:
        if 'incompatible grid type' in str(err) and 'Field grid: 3' in str(err):
            print(str(err))
            print('[WARN] Mule is unable to validate due to subdomain '
                  'fields present - Skipping Mule validation')
            # Overwrite the validation it would normally use
            dfile.validate = dummy_mule_validate
            dfile.to_file(dump_out)
        else:
            print('\n[ERROR] Mule failed to validate fields writing to file: ')
            print(dump_out)
            raise mule.validators.ValidateError(dump_in, '')


if __name__ == '__main__':
    main()
