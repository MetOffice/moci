PROGRAM mean_nemo

   !-----------------------------------------------------------------------------
   ! A routine to make a mean of NEMO input files over variables which contain a
   ! record dimension
   ! Assumes that the time interval is constant between files (i.e. no weighting is
   ! applied)
   !
   ! Author: Tim Graham. 15/03/2012.
   ! Modifification History:
   !       Tim Graham 06/03/2013  - Fixed bug in dimension coordinate output
   !                                by resetting dimids to zero for each variable
   !       Dave Storkey Feb 2016  - Add support for thickness weighted time-mean variables
   !       Daley Calvert Oct 2024 - Use a more robust approach to missing data
   !                                and resolve issues with thickness-weighting
   !-----------------------------------------------------------------------------
  
   USE netcdf

   IMPLICIT NONE

   INTEGER,PARAMETER :: i1=SELECTED_INT_KIND(2)
   INTEGER,PARAMETER :: i2=SELECTED_INT_KIND(4)
   INTEGER,PARAMETER :: i4=SELECTED_INT_KIND(9)
   INTEGER,PARAMETER :: i8=SELECTED_INT_KIND(14)
   INTEGER,PARAMETER :: sp=SELECTED_REAL_KIND(6,37)
   INTEGER,PARAMETER :: dp=SELECTED_REAL_KIND(12,307)

   LOGICAL, PARAMETER :: l_verbose = .true. 
    
   CHARACTER(LEN=nf90_max_name) :: outfile, attname, dimname, varname, time, date, zone, timestamp
   CHARACTER(LEN=nf90_max_name), ALLOCATABLE :: filenames(:), indimnames(:)
   CHARACTER(LEN=256) :: standard_name,cell_methods 

   LOGICAL :: l_thckwgt, l_doavg, l_ismasked, l_inputdata_ismasked, l_cellthick_ismasked

   INTEGER :: nargs, ifile , iargc, no_fill
   INTEGER :: ncid, outid, iostat, idim, istop, itime
   INTEGER :: natts, attid, xtype, varid
   ! ntimes is total number of time points to average over (for unmasked data)
   ! ntimes_local is number of time points in each file
   INTEGER :: jv, jv_thickness, ndims, nvars, dimlen, dimids(4), ntimes, ntimes_local
   INTEGER :: dimid, unlimitedDimId, unlimitedDimId_local, varunlimitedDimId
   INTEGER :: chunksize = 32000000
   INTEGER, ALLOCATABLE  :: outdimids(:), outdimlens(:), inncids(:)
   INTEGER, ALLOCATABLE  :: indimlens(:), start(:)

   ! Scalars
   INTEGER(i4) :: inputdata_fill_value_i4, outputdata_fill_value_i4
   REAL(sp) :: inputdata_fill_value_sp, outputdata_fill_value_sp, cellthick_fill_value_sp
   REAL(dp) :: inputdata_fill_value_dp, outputdata_fill_value_dp, cellthick_fill_value_dp

   ! Logical data masks (for 4d data only, which may be thickness-weighted and/or masked)
   LOGICAL, ALLOCATABLE, DIMENSION(:,:,:,:) :: l_mask_4d

   ! Time counters (for masked data)
   INTEGER(i2), ALLOCATABLE, DIMENSION(:,:,:) :: ntimes_3d
   INTEGER(i2), ALLOCATABLE, DIMENSION(:,:,:,:) :: ntimes_4d

   !Int 1 versions of the local data arrays
   INTEGER(i1), ALLOCATABLE, SAVE, DIMENSION(:) :: inputdata_1d_i1
   INTEGER(i1), ALLOCATABLE, SAVE, DIMENSION(:,:) :: inputdata_2d_i1
   INTEGER(i1), ALLOCATABLE, SAVE, DIMENSION(:,:,:) :: inputdata_3d_i1
   INTEGER(i1), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: inputdata_4d_i1

   !Int 2 versions of the local data arrays
   INTEGER(i2), ALLOCATABLE, SAVE, DIMENSION(:) :: inputdata_1d_i2
   INTEGER(i2), ALLOCATABLE, SAVE, DIMENSION(:,:) :: inputdata_2d_i2
   INTEGER(i2), ALLOCATABLE, SAVE, DIMENSION(:,:,:) :: inputdata_3d_i2
   INTEGER(i2), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: inputdata_4d_i2

   !Int 4 versions of the local data arrays
   INTEGER(i4), ALLOCATABLE, SAVE, DIMENSION(:) :: inputdata_1d_i4
   INTEGER(i4), ALLOCATABLE, SAVE, DIMENSION(:,:) :: inputdata_2d_i4
   INTEGER(i4), ALLOCATABLE, SAVE, DIMENSION(:,:,:) :: inputdata_3d_i4
   INTEGER(i4), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: inputdata_4d_i4

   !Real 4 versions of the local data arrays
   REAL(sp), ALLOCATABLE, SAVE, DIMENSION(:) :: inputdata_1d_sp
   REAL(sp), ALLOCATABLE, SAVE, DIMENSION(:,:) :: inputdata_2d_sp
   REAL(sp), ALLOCATABLE, SAVE, DIMENSION(:,:,:) :: inputdata_3d_sp
   REAL(sp), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: inputdata_4d_sp
   REAL(sp), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: cellthick_4d_sp

   !Real 8 versions of the local data arrays
   REAL(dp), ALLOCATABLE, SAVE, DIMENSION(:) :: inputdata_1d_dp
   REAL(dp), ALLOCATABLE, SAVE, DIMENSION(:,:) :: inputdata_2d_dp
   REAL(dp), ALLOCATABLE, SAVE, DIMENSION(:,:,:) :: inputdata_3d_dp
   REAL(dp), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: inputdata_4d_dp
   REAL(dp), ALLOCATABLE, SAVE, DIMENSION(:,:,:,:) :: cellthick_4d_dp

   !Int 1 versions of the global data arrays
   INTEGER(i1) :: meandata_0d_i1
   INTEGER(i1), ALLOCATABLE, DIMENSION(:) :: meandata_1d_i1
   INTEGER(i1), ALLOCATABLE, DIMENSION(:,:) :: meandata_2d_i1
   INTEGER(i1), ALLOCATABLE, DIMENSION(:,:,:) :: meandata_3d_i1
   INTEGER(i1), ALLOCATABLE, DIMENSION(:,:,:,:) :: meandata_4d_i1

   !Int 2 versions of the global data arrays
   INTEGER(i2) :: meandata_0d_i2
   INTEGER(i2), ALLOCATABLE, DIMENSION(:) :: meandata_1d_i2
   INTEGER(i2), ALLOCATABLE, DIMENSION(:,:) :: meandata_2d_i2
   INTEGER(i2), ALLOCATABLE, DIMENSION(:,:,:) :: meandata_3d_i2
   INTEGER(i2), ALLOCATABLE, DIMENSION(:,:,:,:) :: meandata_4d_i2

   !Int 4 versions of the global data arrays
   INTEGER(i4) :: meandata_0d_i4
   INTEGER(i4), ALLOCATABLE, DIMENSION(:) :: meandata_1d_i4
   INTEGER(i4), ALLOCATABLE, DIMENSION(:,:) :: meandata_2d_i4
   INTEGER(i4), ALLOCATABLE, DIMENSION(:,:,:) :: meandata_3d_i4
   INTEGER(i4), ALLOCATABLE, DIMENSION(:,:,:,:) :: meandata_4d_i4
 
   !Real 4 versions of the global data arrays
   REAL(sp) :: meandata_0d_sp
   REAL(sp), ALLOCATABLE, DIMENSION(:) :: meandata_1d_sp
   REAL(sp), ALLOCATABLE, DIMENSION(:,:) :: meandata_2d_sp
   REAL(sp), ALLOCATABLE, DIMENSION(:,:,:) :: meandata_3d_sp
   REAL(sp), ALLOCATABLE, DIMENSION(:,:,:,:) :: meandata_4d_sp
   REAL(sp), ALLOCATABLE, DIMENSION(:,:,:,:) :: meancellthick_4d_sp

   !Real 8 versions of the global data arrays
   REAL(dp) :: meandata_0d_dp
   REAL(dp), ALLOCATABLE, DIMENSION(:) :: meandata_1d_dp
   REAL(dp), ALLOCATABLE, DIMENSION(:,:) :: meandata_2d_dp
   REAL(dp), ALLOCATABLE, DIMENSION(:,:,:) :: meandata_3d_dp
   REAL(dp), ALLOCATABLE, DIMENSION(:,:,:,:) :: meandata_4d_dp
   REAL(dp), ALLOCATABLE, DIMENSION(:,:,:,:) :: meancellthick_4d_dp



   !End of definitions

   !--------------------------------------------------------------------------------
   !1. Read in the arguments (input and output filenames)
    
   nargs=iargc()
   IF (nargs .lt. 3) then
      WRITE(6,*) 'USAGE:'
      WRITE(6,*) 'mean_nemo.exe Input_file1.nc Input_file2.nc [Input_file3...] Output_file.nc'
      WRITE(6,*) 'Not enough input arguments:'
      WRITE(6,*) 'Expecting at least 2 input files and 1 output file'
   ENDIF
 
   !1.1 Set up the filenames and fileids

   ALLOCATE(filenames(nargs-1))
   IF (l_verbose) WRITE(6,*)'Meaning the following files:'
   DO ifile = 1, nargs-1
      CALL getarg(ifile, filenames(ifile))
      IF (l_verbose) WRITE(6,*) TRIM(filenames(ifile))
   END DO
   ALLOCATE(inncids(nargs-1))
  
   !---------------------------------------------------------------------------
   !2. Read in the global dimensions from the first input file and set up the output file

   iostat = nf90_open( TRIM(filenames(1)), nf90_share, ncid )
   IF( iostat /= nf90_noerr ) THEN
      WRITE(6,*)'E R R O R opening input file '//TRIM(filenames(1))//':'
      WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
      STOP 11
   ENDIF
   iostat = nf90_inquire( ncid, ndims, nvars, natts )
    
   !2.1 Set up the output file
   CALL getarg(nargs,outfile)
   iostat = nf90_create( TRIM(outfile), nf90_64bit_offset, outid, chunksize=chunksize)

   !2.2 Set up dimensions in output file

   !2.2.1 Copy the dimensions into the output file
   ALLOCATE(indimnames(ndims), outdimlens(ndims))
   iostat = nf90_inquire( ncid, unlimitedDimId = unlimitedDimId )
   DO idim = 1, ndims
      iostat = nf90_inquire_dimension(ncid, idim, dimname, dimlen)
      indimnames(idim) = dimname
      IF( idim == unlimitedDimId ) THEN
         iostat = nf90_def_dim( outid, dimname, nf90_unlimited, dimid)    
         outdimlens(idim) = 1
      ELSE
         iostat = nf90_def_dim( outid, dimname, dimlen, dimid)
         outdimlens(idim) = dimlen
      ENDIF
   END DO

   !2.2.2 Copy the global attributes into the output file, apart from those beginning with DOMAIN_
   !      Also need to change the file_name attribute and the TimeStamp attribute.
   DO attid = 1, natts
      iostat = nf90_inq_attname( ncid, nf90_global, attid, attname )
      IF( INDEX( attname, "file_name") == 1 ) CYCLE
      IF( INDEX( attname, "associate_file") == 1 ) CYCLE
      WRITE(6,*)'Copying attribute '//TRIM(attname)//' into destination file...'
      iostat = nf90_copy_att( ncid, nf90_global, attname, outid, nf90_global )  
   END DO
   iostat = nf90_put_att( outid, nf90_global, "file_name", outfile)
   IF (l_verbose) WRITE(6,*)'Writing new file_name attribute'  
   CALL DATE_AND_TIME ( date=date, time=time, zone=zone )
   timestamp = date(7:8) // "/" // date(5:6) // "/" // date(1:4) // " " // &
               time(1:2) // ":" // time(3:4) // ":" // time(5:6) // " " // &
               zone  
   iostat = nf90_put_att( outid, nf90_global, "TimeStamp", timestamp)
   IF (l_verbose) WRITE(6,*)'Writing new TimeStamp attribute'

   jv_thickness = -1
   l_cellthick_ismasked = .FALSE.

   ! Find out if there is a cell thickness variable in this set of files in case we need to do thickness weighting
   DO jv = 1, nvars
      iostat = nf90_get_att(ncid, jv, "standard_name", standard_name)

      IF( (iostat == nf90_noerr) .AND. (TRIM(standard_name) == "cell_thickness") ) THEN
         jv_thickness = jv
         iostat = nf90_inquire_variable( ncid, jv, xtype=xtype )

         ! Save cell thickness fill value if masked
         SELECT CASE( xtype )
            CASE( NF90_FLOAT )
               iostat = nf90_get_att(ncid, jv, "_FillValue", cellthick_fill_value_sp )
               IF( iostat == nf90_noerr ) cellthick_fill_value_dp = REAL(cellthick_fill_value_sp, dp)
            CASE( NF90_DOUBLE )
               iostat = nf90_get_att(ncid, jv, "_FillValue", cellthick_fill_value_dp )
               IF( iostat == nf90_noerr ) cellthick_fill_value_sp = REAL(cellthick_fill_value_dp, sp)
            CASE DEFAULT
               WRITE(6,*) "ERROR : Cell thickness variable must be single or double precision float"
               STOP 13
         END SELECT

         ! Is the cell thickness data masked?
         l_cellthick_ismasked = (iostat == nf90_noerr)

         ! Exit loop if the cell thickness has been found
         EXIT
      ENDIF
   END DO

   !2.2.3 Copy the variable definitions and attributes into the output file.
   DO jv = 1, nvars
      iostat = nf90_inquire_variable( ncid, jv, varname, xtype, ndims, dimids, natts)
      ALLOCATE(outdimids(ndims))
      DO idim = 1, ndims
         outdimids(idim) = dimids(idim)
      END DO

      iostat = nf90_def_var( outid, varname, xtype, outdimids, varid )
      DEALLOCATE(outdimids)
      IF (l_verbose) WRITE(6,*)'Defining variable '//TRIM(varname)//'...' 
      IF( natts > 0 ) THEN
         DO attid = 1, natts
            iostat = nf90_inq_attname(ncid, varid, attid, attname)
            iostat = nf90_copy_att( ncid, varid, attname, outid, varid )   
         END DO
      ENDIF

      ! For thickness weighting, output data will use the fill value of the cell thickness if the input data is not masked
      IF( jv /= jv_thickness ) THEN
         iostat = nf90_get_att(ncid, jv, "cell_methods", cell_methods)
         l_thckwgt = ( (iostat == nf90_noerr) .AND. (TRIM(cell_methods) == "time: mean (thickness weighted)") )
         iostat = nf90_inquire_attribute(ncid, jv, "_FillValue")
         l_inputdata_ismasked = (iostat == nf90_noerr .AND. ndims >= 3)

         IF( l_thckwgt .AND. l_cellthick_ismasked .AND. (.NOT. l_inputdata_ismasked) ) THEN
            SELECT CASE( xtype )
               CASE( NF90_FLOAT )
                  iostat = nf90_put_att( outid, varid, '_FillValue', cellthick_fill_value_sp )
               CASE( NF90_DOUBLE )
                  iostat = nf90_put_att( outid, varid, '_FillValue', cellthick_fill_value_dp )
            END SELECT
         ENDIF
      ENDIF
   END DO
 
   !2.3 End definitions in output file and copy 1st file ncid to the inncids array

   iostat = nf90_enddef( outid )    
   inncids(1) = ncid
   IF (l_verbose) WRITE(6,*)'Finished defining output file.'

   !---------------------------------------------------------------------------
   !3. Read in data from each file for each variable

   !3.1 Open each file and store the ncid in inncids array

   IF (l_verbose) WRITE(6,*)'Opening input files...'
   DO ifile = 2, nargs-1
      iostat = nf90_open( TRIM(filenames(ifile)), nf90_share, ncid, chunksize=chunksize)
      IF( iostat /= nf90_noerr ) THEN
         WRITE(6,*)'E R R O R opening input file '//TRIM(filenames(ifile))//':'
         WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
         STOP 12
      ELSE
         inncids(ifile) = ncid
      ENDIF
   END DO
   IF (l_verbose) WRITE(6,*)'All input files open.'

   !Loop over all variables in first input file
   DO jv = 1, nvars

      !3.2 Inquire variable to find out name and how many dimensions it has

      ncid = inncids(1)
      !Reset dimids
      dimids=0

      !Get xtype, ndims and dimids for this variable
      iostat = nf90_inquire_variable( ncid, jv, varname, xtype, ndims, dimids, natts)
      iostat = nf90_get_att(ncid, jv, "cell_methods", cell_methods)

      ! Do we need to average over the unlimited dimension?
      l_doavg = ANY(dimids .EQ. unlimitedDimId)

      ! Does averaging need to account for thickness-weighting and masked data?
      l_thckwgt = .FALSE.
      l_inputdata_ismasked = .FALSE.
      l_ismasked = .FALSE.
      IF( l_doavg ) THEN
         ! Thickness-weighting- if an unsupported data type/shape has this attribute, raise an error below
         l_thckwgt = ( iostat == nf90_noerr .AND. TRIM(cell_methods) == "time: mean (thickness weighted)" )

         ! Masked data- get the fill value of the input data and/or cell thickness, and set the fill value of the
         ! output file (that of the input data is prioritised). Unsupported data types/shapes proceed silently using
         ! the unmasked averaging algorithm.
         IF( ndims >= 3 ) THEN
            SELECT CASE( xtype )
               CASE( NF90_INT )
                  iostat = nf90_get_att(ncid, jv, "_FillValue", inputdata_fill_value_i4 )
                  IF( iostat == nf90_noerr ) outputdata_fill_value_i4 = inputdata_fill_value_i4
               CASE( NF90_FLOAT )
                  iostat = nf90_get_att(ncid, jv, "_FillValue", inputdata_fill_value_sp )
                  IF( iostat == nf90_noerr ) THEN
                     outputdata_fill_value_sp = inputdata_fill_value_sp
                  ELSE IF( l_thckwgt .AND. l_cellthick_ismasked ) THEN
                     outputdata_fill_value_sp = cellthick_fill_value_sp
                  ENDIF
               CASE( NF90_DOUBLE )
                  iostat = nf90_get_att(ncid, jv, "_FillValue", inputdata_fill_value_dp )
                  IF( iostat == nf90_noerr ) THEN
                     outputdata_fill_value_dp = inputdata_fill_value_dp
                  ELSE IF( l_thckwgt .AND. l_cellthick_ismasked ) THEN
                     outputdata_fill_value_dp = cellthick_fill_value_dp
                  ENDIF
               CASE DEFAULT
                  iostat = nf90_noerr + 1
            END SELECT
            ! Is the input data masked?
            l_inputdata_ismasked = iostat == nf90_noerr
            ! We need to perform masked averaging if the input data and/or cell thickness data is masked
            l_ismasked = l_inputdata_ismasked .OR. (l_thckwgt .AND. l_cellthick_ismasked)
         ENDIF
      ENDIF

      IF( l_thckwgt .AND. jv_thickness == -1 ) THEN
         WRITE(6,*) "ERROR : Thickness-weighted time-mean variable "//TRIM(varname)//" found in file "//TRIM(filenames(1))
         WRITE(6,*) "        but no cell thickness available."
         WRITE(6,*) "        If you want to go ahead anyway (not recommended) remove cell_methods attribute from variable."
         STOP 13
      ENDIF
      IF( l_thckwgt .AND. ( ( xtype /= NF90_FLOAT .AND. xtype /= NF90_DOUBLE ) .OR. ndims /= 4 ) ) THEN
         WRITE(6,*) "ERROR : Thickness-weighted time-mean variable "//TRIM(varname)//" found in file "//TRIM(filenames(ifile))
         WRITE(6,*) "        This utility currently only takes account of thickness weighting for 4D FLOATS or 4D DOUBLES."
         WRITE(6,*) "       "//TRIM(varname)//" either has a different number of dimensions or is not a FLOAT or a DOUBLE."
         WRITE(6,*) "        If you want to mean the variable without thickness weighting remove cell_methods attribute from variable."
         STOP 13
      ENDIF

      IF( l_verbose .AND. l_doavg ) THEN
         IF( l_ismasked ) THEN
            WRITE(6,*)'Averaging data from masked variable '//TRIM(varname)//'...'
         ELSE
            WRITE(6,*)'Averaging data from variable '//TRIM(varname)//'...'
         ENDIF
         IF( l_thckwgt ) WRITE(6,*)'Applying thickness-weighting.'
      ENDIF

      ! Allocate and initialise arrays used in the calculation of the average

      IF( ndims == 1 ) THEN
         ! Denominator- # of records, always a scalar (no support for masked averages)
         ntimes = 0

         ! Numerator- sum over time of the data
         SELECT CASE( xtype )
            CASE( NF90_BYTE )
               ALLOCATE(meandata_1d_i1(outdimlens(dimids(1))))
               meandata_1d_i1(:)=0
            CASE( NF90_SHORT )
               ALLOCATE(meandata_1d_i2(outdimlens(dimids(1))))
               meandata_1d_i2(:)=0
            CASE( NF90_INT )
               ALLOCATE(meandata_1d_i4(outdimlens(dimids(1))))
               meandata_1d_i4(:)=0
            CASE( NF90_FLOAT )
               ALLOCATE(meandata_1d_sp(outdimlens(dimids(1))))
               meandata_1d_sp(:)=0.0
            CASE( NF90_DOUBLE )
               ALLOCATE(meandata_1d_dp(outdimlens(dimids(1))))
               meandata_1d_dp(:)=0.0
            CASE DEFAULT
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT

      ELSEIF( ndims == 2 ) THEN
         ! Denominator- # of records, always a scalar (no support for masked averages)
         ntimes = 0

         ! Numerator- sum over time of the data
         SELECT CASE( xtype )
            CASE( NF90_BYTE )
               ALLOCATE(meandata_2d_i1(outdimlens(dimids(1)),outdimlens(dimids(2))))
               meandata_2d_i1(:,:)=0
            CASE( NF90_SHORT )
               ALLOCATE(meandata_2d_i2(outdimlens(dimids(1)),outdimlens(dimids(2))))
               meandata_2d_i2(:,:)=0
            CASE( NF90_INT )
               ALLOCATE(meandata_2d_i4(outdimlens(dimids(1)),outdimlens(dimids(2))))
               meandata_2d_i4(:,:)=0
            CASE( NF90_FLOAT )
               ALLOCATE(meandata_2d_sp(outdimlens(dimids(1)),outdimlens(dimids(2))))
               meandata_2d_sp(:,:)=0.0
            CASE( NF90_DOUBLE )
               ALLOCATE(meandata_2d_dp(outdimlens(dimids(1)),outdimlens(dimids(2))))
               meandata_2d_dp(:,:)=0.0
            CASE DEFAULT
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT

      ELSEIF( ndims == 3 ) THEN
         ! Denominator- # of records, either a scalar (normal average) or array (masked average)
         IF( l_ismasked ) THEN
            ALLOCATE( ntimes_3d( outdimlens(dimids(1)), outdimlens(dimids(2)),   &
               &                 outdimlens(dimids(3)) ) )
            ntimes_3d(:,:,:) = 0
         ELSE
            ntimes = 0
         ENDIF

         ! Numerator- sum over time of the data
         SELECT CASE( xtype )
            CASE( NF90_BYTE )
               ALLOCATE(meandata_3d_i1(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3))))
               meandata_3d_i1(:,:,:)=0
            CASE( NF90_SHORT )
               ALLOCATE(meandata_3d_i2(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3))))
               meandata_3d_i2(:,:,:)=0
            CASE( NF90_INT )
               ALLOCATE(meandata_3d_i4(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3))))
               meandata_3d_i4(:,:,:)=0
            CASE( NF90_FLOAT )
               ALLOCATE(meandata_3d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3))))
               meandata_3d_sp(:,:,:)=0.0
            CASE( NF90_DOUBLE )
               ALLOCATE(meandata_3d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3))))
               meandata_3d_dp(:,:,:)=0.0
            CASE DEFAULT
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT

      ELSEIF( ndims == 4 ) THEN

         ! Denominator- either the sum over time of the cell thickness (thickness-weighted average),
         ! or # of records which is either a scalar (normal average) or array (masked average)
         IF( l_thckwgt ) THEN
            SELECT CASE( xtype )
               CASE( NF90_FLOAT )
                  ALLOCATE(meancellthick_4d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                    &                          outdimlens(dimids(3)),outdimlens(dimids(4))))
                  meancellthick_4d_sp(:,:,:,:)=0.0
               CASE( NF90_DOUBLE )
                  ALLOCATE(meancellthick_4d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                    &                          outdimlens(dimids(3)),outdimlens(dimids(4))))
                  meancellthick_4d_dp(:,:,:,:)=0.0
            END SELECT
         ELSE IF( l_ismasked ) THEN
            ALLOCATE( ntimes_4d( outdimlens(dimids(1)), outdimlens(dimids(2)),   &
               &                 outdimlens(dimids(3)), outdimlens(dimids(4)) ) )
            ntimes_4d(:,:,:,:) = 0
         ELSE
            ntimes = 0
         ENDIF

         ! Numerator- sum over time of the data (potentially thickness-weighted)
         SELECT CASE( xtype )
            CASE( NF90_BYTE )
               ALLOCATE(meandata_4d_i1(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
               meandata_4d_i1(:,:,:,:)=0
            CASE( NF90_SHORT )
               ALLOCATE(meandata_4d_i2(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
               meandata_4d_i2(:,:,:,:)=0
            CASE( NF90_INT )
               ALLOCATE(meandata_4d_i4(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
               meandata_4d_i4(:,:,:,:)=0
            CASE( NF90_FLOAT )
               ALLOCATE(meandata_4d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
               meandata_4d_sp(:,:,:,:)=0.0
            CASE( NF90_DOUBLE )
               ALLOCATE(meandata_4d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                 &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
               meandata_4d_dp(:,:,:,:)=0.0
            CASE DEFAULT
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT
      ELSE
         WRITE(6,*)'E R R O R: '
         WRITE(6,*)'The netcdf variable has more than 4 dimensions which is not taken into account'
         STOP 15
      ENDIF

      istop = 0

      ! If this variable is a function of the unlimited dimension then
      ! Average over unlimited dimension
      IF( l_doavg ) THEN

         DO ifile = 1, nargs-1 !Loop through input files

            ncid = inncids(ifile)
            iostat = nf90_inquire_variable( ncid, jv, varname, xtype, ndims, dimids, natts)
            !Check the unlimited dimension ID in this file
            iostat = nf90_inquire( ncid, unlimitedDimId = unlimitedDimId_local )
            ALLOCATE(indimlens(ndims), start(ndims))
            start(:)=1
            DO idim = 1, ndims
               iostat = nf90_inquire_dimension(ncid, dimids(idim), dimname, dimlen)
               IF (dimids(idim) .EQ. unlimitedDimId_local) THEN
                  ntimes_local=dimlen
                  indimlens(idim)=1
                  varunlimitedDimId=idim
               ELSE
                  indimlens(idim)=dimlen
               ENDIF
            END DO

            ! Loop through records in file, accumulate the numerator & denominator of the average
            DO itime = 1, ntimes_local
  
               !start is the offset variable used in call to nf90_get_var
               start(varunlimitedDimId)=itime
          
               IF( ndims == 1 ) THEN
                  ntimes = ntimes + 1

                  SELECT CASE( xtype )
                     CASE( NF90_BYTE )
                        ALLOCATE(inputdata_1d_i1(outdimlens(dimids(1))))
                        inputdata_1d_i1(:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_1d_i1, start, indimlens)
                        meandata_1d_i1(:)=meandata_1d_i1(:)+inputdata_1d_i1(:)
                        DEALLOCATE(inputdata_1d_i1)
                     CASE( NF90_SHORT )
                        ALLOCATE(inputdata_1d_i2(outdimlens(dimids(1))))
                        inputdata_1d_i2(:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_1d_i2, start, indimlens)
                        meandata_1d_i2(:)=meandata_1d_i2(:)+inputdata_1d_i2(:)
                        DEALLOCATE(inputdata_1d_i2)
                     CASE( NF90_INT )
                        ALLOCATE(inputdata_1d_i4(outdimlens(dimids(1))))
                        inputdata_1d_i4(:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_1d_i4, start, indimlens)
                        meandata_1d_i4(:)=meandata_1d_i4(:)+inputdata_1d_i4(:)
                        DEALLOCATE(inputdata_1d_i4)
                     CASE( NF90_FLOAT )
                        ALLOCATE(inputdata_1d_sp(outdimlens(dimids(1))))
                        inputdata_1d_sp(:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_1d_sp, start, indimlens)
                        meandata_1d_sp(:)=meandata_1d_sp(:)+inputdata_1d_sp(:)
                        DEALLOCATE(inputdata_1d_sp)
                     CASE( NF90_DOUBLE )
                        ALLOCATE(inputdata_1d_dp(outdimlens(dimids(1))))
                        inputdata_1d_dp(:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_1d_dp, start, indimlens)
                        meandata_1d_dp(:)=meandata_1d_dp(:)+inputdata_1d_dp(:)
                        DEALLOCATE(inputdata_1d_dp)
                     CASE DEFAULT
                        WRITE(6,*)'Unknown nf90 type: ', xtype
                        STOP 14
                  END SELECT

               ELSEIF( ndims == 2 ) THEN
                  ntimes = ntimes + 1

                  SELECT CASE( xtype )
                     CASE( NF90_BYTE )
                        ALLOCATE(inputdata_2d_i1(outdimlens(dimids(1)),outdimlens(dimids(2))))
                        inputdata_2d_i1(:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_2d_i1, start, indimlens)
                        meandata_2d_i1(:,:)=meandata_2d_i1(:,:)+inputdata_2d_i1(:,:)
                        DEALLOCATE(inputdata_2d_i1)
                     CASE( NF90_SHORT )
                        ALLOCATE(inputdata_2d_i2(outdimlens(dimids(1)),outdimlens(dimids(2))))
                        inputdata_2d_i2(:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_2d_i2, start, indimlens )
                        meandata_2d_i2(:,:)=meandata_2d_i2(:,:)+inputdata_2d_i2(:,:)
                        DEALLOCATE(inputdata_2d_i2)
                     CASE( NF90_INT )
                        ALLOCATE(inputdata_2d_i4(outdimlens(dimids(1)),outdimlens(dimids(2))))
                        inputdata_2d_i4(:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_2d_i4, start, indimlens )
                        meandata_2d_i4(:,:)=meandata_2d_i4(:,:)+inputdata_2d_i4(:,:)
                        DEALLOCATE(inputdata_2d_i4)
                     CASE( NF90_FLOAT )
                        ALLOCATE(inputdata_2d_sp(outdimlens(dimids(1)),outdimlens(dimids(2))))
                        inputdata_2d_sp(:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_2d_sp, start, indimlens )
                        meandata_2d_sp(:,:)=meandata_2d_sp(:,:)+inputdata_2d_sp(:,:)
                        DEALLOCATE(inputdata_2d_sp)
                     CASE( NF90_DOUBLE )
                        ALLOCATE(inputdata_2d_dp(outdimlens(dimids(1)),outdimlens(dimids(2))))
                        inputdata_2d_dp(:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_2d_dp, start, indimlens )
                        meandata_2d_dp(:,:)=meandata_2d_dp(:,:)+inputdata_2d_dp(:,:)
                        DEALLOCATE(inputdata_2d_dp)
                     CASE DEFAULT
                        WRITE(6,*)'Unknown nf90 type: ', xtype
                        STOP 14
                  END SELECT

               ELSEIF( ndims == 3 ) THEN
  
                  SELECT CASE( xtype )
                     CASE( NF90_BYTE )
                        ALLOCATE(inputdata_3d_i1(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3))))
                        inputdata_3d_i1(:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_3d_i1, start, indimlens )
                        meandata_3d_i1(:,:,:)=meandata_3d_i1(:,:,:)+inputdata_3d_i1(:,:,:)
                        DEALLOCATE(inputdata_3d_i1)

                        ntimes = ntimes + 1
                     CASE( NF90_SHORT )
                        ALLOCATE(inputdata_3d_i2(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3))))
                        inputdata_3d_i2(:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_3d_i2, start, indimlens )
                        meandata_3d_i2(:,:,:)=meandata_3d_i2(:,:,:)+inputdata_3d_i2(:,:,:)
                        DEALLOCATE(inputdata_3d_i2)

                        ntimes = ntimes + 1
                     CASE( NF90_INT )
                        ALLOCATE(inputdata_3d_i4(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3))))
                        inputdata_3d_i4(:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_3d_i4, start, indimlens )

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           WHERE( inputdata_3d_i4(:,:,:) /= inputdata_fill_value_i4 )
                              meandata_3d_i4(:,:,:) = meandata_3d_i4(:,:,:) + inputdata_3d_i4(:,:,:)
                              ntimes_3d(:,:,:) = ntimes_3d(:,:,:) + 1
                           ENDWHERE
                        ELSE
                           meandata_3d_i4(:,:,:) = meandata_3d_i4(:,:,:) + inputdata_3d_i4(:,:,:)
                           ntimes = ntimes + 1
                        ENDIF

                        DEALLOCATE(inputdata_3d_i4)
                     CASE( NF90_FLOAT )
                        ALLOCATE(inputdata_3d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3))))
                        inputdata_3d_sp(:,:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_3d_sp, start, indimlens )

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           WHERE( inputdata_3d_sp(:,:,:) /= inputdata_fill_value_sp )
                              meandata_3d_sp(:,:,:) = meandata_3d_sp(:,:,:) + inputdata_3d_sp(:,:,:)
                              ntimes_3d(:,:,:) = ntimes_3d(:,:,:) + 1
                           ENDWHERE
                        ELSE
                           meandata_3d_sp(:,:,:) = meandata_3d_sp(:,:,:) + inputdata_3d_sp(:,:,:)
                           ntimes = ntimes + 1
                        ENDIF

                        DEALLOCATE(inputdata_3d_sp)
                     CASE( NF90_DOUBLE )
                        ALLOCATE(inputdata_3d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3))))
                        inputdata_3d_dp(:,:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_3d_dp, start, indimlens )

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           WHERE( inputdata_3d_dp(:,:,:) /= inputdata_fill_value_dp )
                              meandata_3d_dp(:,:,:) = meandata_3d_dp(:,:,:) + inputdata_3d_dp(:,:,:)
                              ntimes_3d(:,:,:) = ntimes_3d(:,:,:) + 1
                           ENDWHERE
                        ELSE
                           meandata_3d_dp(:,:,:) = meandata_3d_dp(:,:,:) + inputdata_3d_dp(:,:,:)
                           ntimes = ntimes + 1
                        ENDIF

                        DEALLOCATE(inputdata_3d_dp)
                     CASE DEFAULT
                        WRITE(6,*)'Unknown nf90 type: ', xtype
                        STOP 14
                  END SELECT

               ELSEIF( ndims == 4 ) THEN

                  SELECT CASE( xtype )
                     CASE( NF90_BYTE )
                        ALLOCATE(inputdata_4d_i1(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                        inputdata_4d_i1(:,:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_4d_i1, start, indimlens )
                        meandata_4d_i1(:,:,:,:)=meandata_4d_i1(:,:,:,:)+inputdata_4d_i1(:,:,:,:)
                        DEALLOCATE(inputdata_4d_i1)

                        ntimes = ntimes + 1
                     CASE( NF90_SHORT )
                        ALLOCATE(inputdata_4d_i2(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                        inputdata_4d_i2(:,:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_4d_i2, start, indimlens )
                        meandata_4d_i2(:,:,:,:)=meandata_4d_i2(:,:,:,:)+inputdata_4d_i2(:,:,:,:)
                        DEALLOCATE(inputdata_4d_i2)

                        ntimes = ntimes + 1
                     CASE( NF90_INT )
                        ALLOCATE(inputdata_4d_i4(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                        inputdata_4d_i4(:,:,:,:)=0
                        iostat = nf90_get_var( ncid, jv, inputdata_4d_i4, start, indimlens )

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           WHERE( inputdata_4d_i4(:,:,:,:) /= inputdata_fill_value_i4 )
                              meandata_4d_i4(:,:,:,:) = meandata_4d_i4(:,:,:,:) + inputdata_4d_i4(:,:,:,:)
                              ntimes_4d(:,:,:,:) = ntimes_4d(:,:,:,:) + 1
                           ENDWHERE
                        ELSE
                           meandata_4d_i4(:,:,:,:) = meandata_4d_i4(:,:,:,:) + inputdata_4d_i4(:,:,:,:)
                           ntimes = ntimes + 1
                        ENDIF

                        DEALLOCATE(inputdata_4d_i4)
                     CASE( NF90_FLOAT )
                        ALLOCATE(inputdata_4d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                        inputdata_4d_sp(:,:,:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_4d_sp, start, indimlens )

                        ! Thickness-weighting- get cell thickness
                        IF( l_thckwgt ) THEN
                           ALLOCATE(cellthick_4d_sp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                             &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                           cellthick_4d_sp(:,:,:,:)=0.0
                           iostat = nf90_get_var( ncid, jv_thickness, cellthick_4d_sp, start, indimlens )
                        ENDIF

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           ! Use the union of the input data and cell thickness masks
                           ALLOCATE(l_mask_4d(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                             &                outdimlens(dimids(3)),outdimlens(dimids(4))))
                           IF( l_inputdata_ismasked .AND. (l_thckwgt .AND. l_cellthick_ismasked) ) THEN
                              l_mask_4d(:,:,:,:) = (inputdata_4d_sp(:,:,:,:) /= inputdata_fill_value_sp) .AND. &
                                 &                 (cellthick_4d_sp(:,:,:,:) /= cellthick_fill_value_sp)
                           ELSE IF( l_inputdata_ismasked ) THEN
                              l_mask_4d(:,:,:,:) = (inputdata_4d_sp(:,:,:,:) /= inputdata_fill_value_sp)
                           ELSE
                              l_mask_4d(:,:,:,:) = (cellthick_4d_sp(:,:,:,:) /= cellthick_fill_value_sp)
                           ENDIF

                           IF( l_thckwgt ) THEN
                              WHERE( l_mask_4d )
                                 meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) + inputdata_4d_sp(:,:,:,:) * cellthick_4d_sp(:,:,:,:)
                                 meancellthick_4d_sp(:,:,:,:) = meancellthick_4d_sp(:,:,:,:) + cellthick_4d_sp(:,:,:,:)
                              ENDWHERE
                           ELSE
                              WHERE( l_mask_4d )
                                 meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) + inputdata_4d_sp(:,:,:,:)
                                 ntimes_4d(:,:,:,:) = ntimes_4d(:,:,:,:) + 1
                              ENDWHERE
                           ENDIF

                           DEALLOCATE(l_mask_4d)
                        ELSE
                           IF( l_thckwgt ) THEN
                              meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) + inputdata_4d_sp(:,:,:,:) * cellthick_4d_sp(:,:,:,:)
                              meancellthick_4d_sp(:,:,:,:) = meancellthick_4d_sp(:,:,:,:) + cellthick_4d_sp(:,:,:,:)
                           ELSE
                              meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) + inputdata_4d_sp(:,:,:,:)
                              ntimes = ntimes + 1
                           ENDIF
                        ENDIF

                        IF( l_thckwgt ) DEALLOCATE(cellthick_4d_sp)
                        DEALLOCATE(inputdata_4d_sp)
                     CASE( NF90_DOUBLE )
                        ALLOCATE(inputdata_4d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                          &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                        inputdata_4d_dp(:,:,:,:)=0.0
                        iostat = nf90_get_var( ncid, jv, inputdata_4d_dp, start, indimlens )

                        ! Thickness-weighting- get cell thickness
                        IF( l_thckwgt ) THEN
                           ALLOCATE(cellthick_4d_dp(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                             &                      outdimlens(dimids(3)),outdimlens(dimids(4))))
                           cellthick_4d_dp(:,:,:,:)=0.0
                           iostat = nf90_get_var( ncid, jv_thickness, cellthick_4d_dp, start, indimlens )
                        ENDIF

                        ! Do not include masked data in the average
                        IF( l_ismasked ) THEN
                           ! Use the union of the input data and cell thickness masks
                           ALLOCATE(l_mask_4d(outdimlens(dimids(1)),outdimlens(dimids(2)),     &
                             &                outdimlens(dimids(3)),outdimlens(dimids(4))))
                           IF( l_inputdata_ismasked .AND. (l_thckwgt .AND. l_cellthick_ismasked) ) THEN
                              l_mask_4d(:,:,:,:) = (inputdata_4d_dp(:,:,:,:) /= inputdata_fill_value_dp) .AND. &
                                 &                     (cellthick_4d_dp(:,:,:,:) /= cellthick_fill_value_dp)
                           ELSE IF( l_inputdata_ismasked ) THEN
                              l_mask_4d(:,:,:,:) = (inputdata_4d_dp(:,:,:,:) /= inputdata_fill_value_dp)
                           ELSE
                              l_mask_4d(:,:,:,:) = (cellthick_4d_dp(:,:,:,:) /= cellthick_fill_value_dp)
                           ENDIF

                           IF( l_thckwgt ) THEN
                              WHERE( l_mask_4d )
                                 meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) + inputdata_4d_dp(:,:,:,:) * cellthick_4d_dp(:,:,:,:)
                                 meancellthick_4d_dp(:,:,:,:) = meancellthick_4d_dp(:,:,:,:) + cellthick_4d_dp(:,:,:,:)
                              ENDWHERE
                           ELSE
                              WHERE( l_mask_4d )
                                 meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) + inputdata_4d_dp(:,:,:,:)
                                 ntimes_4d(:,:,:,:) = ntimes_4d(:,:,:,:) + 1
                              ENDWHERE
                           ENDIF

                           DEALLOCATE(l_mask_4d)
                        ELSE
                           IF( l_thckwgt ) THEN
                              meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) + inputdata_4d_dp(:,:,:,:) * cellthick_4d_dp(:,:,:,:)
                              meancellthick_4d_dp(:,:,:,:) = meancellthick_4d_dp(:,:,:,:) + cellthick_4d_dp(:,:,:,:)
                           ELSE
                              meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) + inputdata_4d_dp(:,:,:,:)
                              ntimes = ntimes + 1
                           ENDIF
                        ENDIF

                        IF( l_thckwgt ) DEALLOCATE(cellthick_4d_dp)
                        DEALLOCATE(inputdata_4d_dp)
                     CASE DEFAULT
                        WRITE(6,*)'Unknown nf90 type: ', xtype
                        STOP 14
                  END SELECT

               ELSE
                  WRITE(6,*)'E R R O R: '
                  WRITE(6,*)'The netcdf variable has more than 4 dimensions which is not taken into account'
                  STOP 15
               ENDIF  !End of if statement over number of dimensions
 
               IF( iostat /= nf90_noerr ) THEN
                  WRITE(6,*) 'E R R O R reading variable '//TRIM(varname)//' from file '//TRIM(filenames(ifile))//':'
                  WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
                  istop = 1
               ENDIF

               IF( istop /= 0 )  STOP 16

            END DO !loop over records

            DEALLOCATE(start,indimlens)
        
         END DO  !loop over files

         ! Divide numerator (sum of data, possibly thickness-weighted) by denominator (sum of cell thickness
         ! or number of time records) to get the mean, setting masked results to a fill value
         IF( ndims == 1 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  meandata_1d_i1(:)=meandata_1d_i1(:)/ntimes
               CASE( NF90_SHORT )
                  meandata_1d_i2(:)=meandata_1d_i2(:)/ntimes
               CASE( NF90_INT )
                  meandata_1d_i4(:)=meandata_1d_i4(:)/ntimes
               CASE( NF90_FLOAT )
                  meandata_1d_sp(:)=meandata_1d_sp(:)/ntimes
               CASE( NF90_DOUBLE )
                  meandata_1d_dp(:)=meandata_1d_dp(:)/ntimes
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ELSEIF( ndims == 2 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  meandata_2d_i1(:,:)=meandata_2d_i1(:,:)/ntimes
               CASE( NF90_SHORT )
                  meandata_2d_i2(:,:)=meandata_2d_i2(:,:)/ntimes
               CASE( NF90_INT )
                  meandata_2d_i4(:,:)=meandata_2d_i4(:,:)/ntimes
               CASE( NF90_FLOAT )
                  meandata_2d_sp(:,:)=meandata_2d_sp(:,:)/ntimes
               CASE( NF90_DOUBLE )
                  meandata_2d_dp(:,:)=meandata_2d_dp(:,:)/ntimes
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ELSEIF( ndims == 3 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  meandata_3d_i1(:,:,:)=meandata_3d_i1(:,:,:)/ntimes
               CASE( NF90_SHORT )
                  meandata_3d_i2(:,:,:)=meandata_3d_i2(:,:,:)/ntimes
               CASE( NF90_INT )
                  IF( l_ismasked ) THEN
                     WHERE( ntimes_3d(:,:,:) == 0 )
                        meandata_3d_i4(:,:,:) = outputdata_fill_value_i4
                     ELSEWHERE
                        meandata_3d_i4(:,:,:) = meandata_3d_i4(:,:,:) / ntimes_3d(:,:,:)
                     ENDWHERE
                  ELSE
                     meandata_3d_i4(:,:,:) = meandata_3d_i4(:,:,:) / ntimes
                  ENDIF
               CASE( NF90_FLOAT )
                  IF( l_ismasked ) THEN
                     WHERE( ntimes_3d(:,:,:) == 0 )
                        meandata_3d_sp(:,:,:) = outputdata_fill_value_sp
                     ELSEWHERE
                        meandata_3d_sp(:,:,:) = meandata_3d_sp(:,:,:) / ntimes_3d(:,:,:)
                     ENDWHERE
                  ELSE
                     meandata_3d_sp(:,:,:) = meandata_3d_sp(:,:,:) / ntimes
                  ENDIF
               CASE( NF90_DOUBLE )
                  IF( l_ismasked ) THEN
                     WHERE( ntimes_3d(:,:,:) == 0 )
                        meandata_3d_dp(:,:,:) = outputdata_fill_value_dp
                     ELSEWHERE
                        meandata_3d_dp(:,:,:) = meandata_3d_dp(:,:,:) / ntimes_3d(:,:,:)
                     ENDWHERE
                  ELSE
                     meandata_3d_dp(:,:,:) = meandata_3d_dp(:,:,:) / ntimes
                  ENDIF
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT
            IF( l_ismasked ) DEALLOCATE(ntimes_3d)

         ELSEIF( ndims == 4 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  meandata_4d_i1(:,:,:,:)=meandata_4d_i1(:,:,:,:)/ntimes
               CASE( NF90_SHORT )
                  meandata_4d_i2(:,:,:,:)=meandata_4d_i2(:,:,:,:)/ntimes
               CASE( NF90_INT )
                  IF( l_ismasked ) THEN
                     WHERE( ntimes_4d(:,:,:,:) == 0 )
                        meandata_4d_i4(:,:,:,:) = outputdata_fill_value_i4
                     ELSEWHERE
                        meandata_4d_i4(:,:,:,:) = meandata_4d_i4(:,:,:,:) / ntimes_4d(:,:,:,:)
                     ENDWHERE
                  ELSE
                     meandata_4d_i4(:,:,:,:) = meandata_4d_i4(:,:,:,:) / ntimes
                  ENDIF
               CASE( NF90_FLOAT )
                  IF( l_ismasked ) THEN
                     IF( l_thckwgt ) THEN
                        WHERE( meancellthick_4d_sp(:,:,:,:) == 0._sp )
                           meandata_4d_sp(:,:,:,:) = outputdata_fill_value_sp
                        ELSEWHERE
                           meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) / meancellthick_4d_sp(:,:,:,:)
                        ENDWHERE
                     ELSE
                        WHERE( ntimes_4d(:,:,:,:) == 0 )
                           meandata_4d_sp(:,:,:,:) = outputdata_fill_value_sp
                        ELSEWHERE
                           meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) / ntimes_4d(:,:,:,:)
                        ENDWHERE
                     ENDIF
                  ELSE
                     IF( l_thckwgt ) THEN
                        meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) / meancellthick_4d_sp(:,:,:,:)
                     ELSE
                        meandata_4d_sp(:,:,:,:) = meandata_4d_sp(:,:,:,:) / ntimes
                     ENDIF
                  ENDIF
                  IF( l_thckwgt ) DEALLOCATE(meancellthick_4d_sp)
               CASE( NF90_DOUBLE )
                  IF( l_ismasked ) THEN
                     IF( l_thckwgt ) THEN
                        WHERE( meancellthick_4d_dp(:,:,:,:) == 0._dp )
                           meandata_4d_dp(:,:,:,:) = outputdata_fill_value_dp
                        ELSEWHERE
                           meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) / meancellthick_4d_dp(:,:,:,:)
                        ENDWHERE
                     ELSE
                        WHERE( ntimes_4d(:,:,:,:) == 0 )
                           meandata_4d_dp(:,:,:,:) = outputdata_fill_value_dp
                        ELSEWHERE
                           meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) / ntimes_4d(:,:,:,:)
                        ENDWHERE
                     ENDIF
                  ELSE
                     IF( l_thckwgt ) THEN
                        meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) / meancellthick_4d_dp(:,:,:,:)
                     ELSE
                        meandata_4d_dp(:,:,:,:) = meandata_4d_dp(:,:,:,:) / ntimes
                     ENDIF
                  ENDIF
                  IF( l_thckwgt ) DEALLOCATE(meancellthick_4d_dp)
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT
            IF( l_ismasked .AND. .NOT. l_thckwgt ) DEALLOCATE(ntimes_4d)
         ENDIF

      ELSE
         ! Else if the variable does not contain the unlimited dimension just read
         ! in from first file to be copied to outfile as it should be the same in all
         ! files (e.g. coordinates)

         ncid = inncids(1)
         iostat = nf90_inquire_variable( ncid, jv, varname, xtype, ndims, dimids, natts)     

         IF( ndims == 1 ) THEN
  
            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  iostat = nf90_get_var( ncid, jv, meandata_1d_i1 )
               CASE( NF90_SHORT )
                  iostat = nf90_get_var( ncid, jv, meandata_1d_i2 )
               CASE( NF90_INT )
                  iostat = nf90_get_var( ncid, jv, meandata_1d_i4 )
               CASE( NF90_FLOAT )
                  iostat = nf90_get_var( ncid, jv, meandata_1d_sp )
               CASE( NF90_DOUBLE )
                  iostat = nf90_get_var( ncid, jv, meandata_1d_dp )
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ELSEIF( ndims == 2 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  iostat = nf90_get_var( ncid, jv, meandata_2d_i1 )
               CASE( NF90_SHORT )
                  iostat = nf90_get_var( ncid, jv, meandata_2d_i2 )
               CASE( NF90_INT )
                  iostat = nf90_get_var( ncid, jv, meandata_2d_i4 )
               CASE( NF90_FLOAT )
                  iostat = nf90_get_var( ncid, jv, meandata_2d_sp )
               CASE( NF90_DOUBLE )
                  iostat = nf90_get_var( ncid, jv, meandata_2d_dp )
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ELSEIF( ndims == 3 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  iostat = nf90_get_var( ncid, jv, meandata_3d_i1 )
               CASE( NF90_SHORT )
                  iostat = nf90_get_var( ncid, jv, meandata_3d_i2 )
               CASE( NF90_INT )
                  iostat = nf90_get_var( ncid, jv, meandata_3d_i4 )
               CASE( NF90_FLOAT )
                  iostat = nf90_get_var( ncid, jv, meandata_3d_sp )
               CASE( NF90_DOUBLE )
                  iostat = nf90_get_var( ncid, jv, meandata_3d_dp )
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ELSEIF( ndims == 4 ) THEN

            SELECT CASE( xtype )
               CASE( NF90_BYTE )
                  iostat = nf90_get_var( ncid, jv, meandata_4d_i1 )
               CASE( NF90_SHORT )
                  iostat = nf90_get_var( ncid, jv, meandata_4d_i2 )
               CASE( NF90_INT )
                  iostat = nf90_get_var( ncid, jv, meandata_4d_i4 )
               CASE( NF90_FLOAT )
                  iostat = nf90_get_var( ncid, jv, meandata_4d_sp )
               CASE( NF90_DOUBLE )
                  iostat = nf90_get_var( ncid, jv, meandata_4d_dp )
               CASE DEFAULT
                  WRITE(6,*)'Unknown nf90 type: ', xtype
                  STOP 14
            END SELECT

         ENDIF !End of ndims if statements

         IF( iostat /= nf90_noerr ) THEN
            WRITE(6,*) 'E R R O R reading variable '//TRIM(varname)//' from file '//TRIM(filenames(ifile))//':'
            WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
            STOP 16
         ENDIF

      ENDIF !End of check for unlimited dimension

      !---------------------------------------------------------------------------
      !4. Write data to output file and close files

      IF (l_verbose) WRITE(6,*)'Writing variable '//TRIM(varname)//'...'

      !4.1 Write the data to the output file depending on how many dimensions

      IF( ndims == 1 ) THEN

         SELECT CASE( xtype )
            CASE( NF90_BYTE )
               iostat = nf90_put_var( outid, jv, meandata_1d_i1 )
               DEALLOCATE(meandata_1d_i1)
            CASE( NF90_SHORT )
               iostat = nf90_put_var( outid, jv, meandata_1d_i2 )
               DEALLOCATE(meandata_1d_i2)
            CASE( NF90_INT )
               iostat = nf90_put_var( outid, jv, meandata_1d_i4 )
               DEALLOCATE(meandata_1d_i4)
            CASE( NF90_FLOAT )
               iostat = nf90_put_var( outid, jv, meandata_1d_sp )
               DEALLOCATE(meandata_1d_sp)
            CASE( NF90_DOUBLE )
               iostat = nf90_put_var( outid, jv, meandata_1d_dp )
               DEALLOCATE(meandata_1d_dp)
         END SELECT

      ELSEIF( ndims == 2 ) THEN
     
         SELECT CASE( xtype )   
            CASE( NF90_BYTE )                   
               iostat = nf90_put_var( outid, jv, meandata_2d_i1 )
               DEALLOCATE(meandata_2d_i1)
            CASE( NF90_SHORT )                   
               iostat = nf90_put_var( outid, jv, meandata_2d_i2 )
               DEALLOCATE(meandata_2d_i2)
            CASE( NF90_INT )                              
               iostat = nf90_put_var( outid, jv, meandata_2d_i4 )
               DEALLOCATE(meandata_2d_i4)
            CASE( NF90_FLOAT )                              
               iostat = nf90_put_var( outid, jv, meandata_2d_sp )
               DEALLOCATE(meandata_2d_sp)
            CASE( NF90_DOUBLE )                                         
               iostat = nf90_put_var( outid, jv, meandata_2d_dp )
               DEALLOCATE(meandata_2d_dp)
            CASE DEFAULT   
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT     

      ELSEIF( ndims == 3 ) THEN
      
         SELECT CASE( xtype ) 
            CASE( NF90_BYTE )                   
               iostat = nf90_put_var( outid, jv, meandata_3d_i1 )
               DEALLOCATE(meandata_3d_i1)
            CASE( NF90_SHORT )                   
               iostat = nf90_put_var( outid, jv, meandata_3d_i2 )
               DEALLOCATE(meandata_3d_i2)
            CASE( NF90_INT )                              
               iostat = nf90_put_var( outid, jv, meandata_3d_i4 )
               DEALLOCATE(meandata_3d_i4)
            CASE( NF90_FLOAT )                              
               iostat = nf90_put_var( outid, jv, meandata_3d_sp )
               DEALLOCATE(meandata_3d_sp)
            CASE( NF90_DOUBLE )                                         
               iostat = nf90_put_var( outid, jv, meandata_3d_dp )
               DEALLOCATE(meandata_3d_dp)
            CASE DEFAULT   
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT

      ELSEIF( ndims == 4 ) THEN
      
         SELECT CASE( xtype )   
            CASE( NF90_BYTE )                   
               iostat = nf90_put_var( outid, jv, meandata_4d_i1 )
               DEALLOCATE(meandata_4d_i1)
            CASE( NF90_SHORT )                   
               iostat = nf90_put_var( outid, jv, meandata_4d_i2 )
               DEALLOCATE(meandata_4d_i2)
            CASE( NF90_INT )                              
               iostat = nf90_put_var( outid, jv, meandata_4d_i4 )
               DEALLOCATE(meandata_4d_i4)
            CASE( NF90_FLOAT )                              
               iostat = nf90_put_var( outid, jv, meandata_4d_sp )
               DEALLOCATE(meandata_4d_sp)
            CASE( NF90_DOUBLE )                                         
               iostat = nf90_put_var( outid, jv, meandata_4d_dp )
               DEALLOCATE(meandata_4d_dp)
            CASE DEFAULT   
               WRITE(6,*)'Unknown nf90 type: ', xtype
               STOP 14
         END SELECT

      ENDIF

      IF( iostat /= nf90_noerr ) THEN
         WRITE(6,*) 'E R R O R writing variable '//TRIM(varname)//':'
         WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
         STOP 17
      ENDIF

   END DO  !loop over variables

   !4.1 Close all input files

   IF (l_verbose) WRITE(6,*)'Closing input files...'
   DO ifile = 1, nargs-1
      ncid = inncids(ifile)
      iostat = nf90_close( ncid )
      IF( iostat /= nf90_noerr ) THEN
         WRITE(6,*) TRIM(nf90_strerror(iostat))
         WRITE(6,*)'E R R O R closing input file '//TRIM(filenames(ifile))//':'
         WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
         STOP 18
      ENDIF
   END DO

   !4.2 Close output file

   IF (l_verbose) WRITE(6,*)'Closing output file...'
   iostat = nf90_close( outid )
   IF( iostat /= nf90_noerr ) THEN
      WRITE(6,*) TRIM(nf90_strerror(iostat))
      WRITE(6,*)'E R R O R closing output file:'
      WRITE(6,*) '    '//TRIM(nf90_strerror(iostat))
      STOP 19
   ENDIF

END PROGRAM mean_nemo
