PROGRAM xios_toy
!
!*****************************COPYRIGHT******************************
! (C) Crown copyright 2022 Met Office. All rights reserved.
!
! Use, duplication or disclosure of this code is subject to the restrictions
! as set forth in the licence. If no licence has been raised with this copy
! of the code, the use, duplication or disclosure of it is strictly
! prohibited. Permission to do so must first be obtained in writing from the
! Met Office Information Asset Owner at the following address:
!
! Met Office, FitzRoy Road, Exeter, Devon, EX1 3PB, United Kingdom
!*****************************COPYRIGHT******************************
!NAME
!    xios_toy.F90
!
!DESCRIPTION
!    Minimum functional XIOS test Fortran program, creating a field and
!    writing it out. Requires running with MPI
!
USE xios
IMPLICIT NONE
INCLUDE "mpif.h"
INTEGER :: rank
INTEGER :: comm
INTEGER :: size
INTEGER :: ierr
INTEGER :: ts

CHARACTER(len=*),PARAMETER :: id="client"
TYPE(xios_context) :: ctx_hdl
CHARACTER(len=15) :: calendar_type

INTEGER :: size_i = 100, i
INTEGER :: size_j = 100, j

INTEGER, PARAMETER :: axis_len=1
INTEGER :: l

TYPE(xios_duration) :: dtime
LOGICAL :: ok

DOUBLE PRECISION, ALLOCATABLE :: field_A(:,:,:)
DOUBLE PRECISION :: lval(axis_len)=1

ALLOCATE(field_A(size_i, size_j, axis_len))
DO j=1,size_j
  DO i=1,size_i
    DO l=1,axis_len
      field_A(j,i,l) = i+j
    END DO
  END DO
END DO

CALL MPI_INIT(ierr)

CALL xios_initialize(id,return_comm=comm)

CALL MPI_COMM_RANK(comm,rank,ierr)
CALL MPI_COMM_SIZE(comm,size,ierr)

CALL xios_context_initialize("test",comm)
CALL xios_get_handle("test",ctx_hdl)
CALL xios_set_current_context(ctx_hdl)

CALL xios_get_calendar_type(calendar_type)
PRINT *, "calendar_type = ", calendar_type

CALL xios_set_axis_attr("axis_A", n_glo=axis_len, value=lval)
CALL xios_set_domain_attr("domain_A", data_dim=2, ni_glo=size_i, nj_glo=size_j, ibegin=0, jbegin=0, ni=size_i, nj=size_j, type='rectilinear')
!CALL xios_set_domain_attr("domain_A", ni_glo=size_i, nj_glo=size_j, type='rectilinear')
CALL xios_set_fieldgroup_attr("field_definition",enabled=.TRUE.)

dtime%second = 3600
CALL xios_set_timestep(dtime)

CALL xios_is_defined_field_attr("field_A",enabled=ok)
PRINT *,"field_A : attribute enabled is defined ? ",ok

CALL xios_close_context_definition()


DO ts=1,4
  CALL xios_update_calendar(ts)
! we can check if our field is active this timestep, to stop sending
! too much data to XIOS
  IF (xios_field_is_active('field_A')) THEN
    CALL xios_send_field("field_A", field_A)
  END IF
END DO

CALL xios_context_finalize()

CALL MPI_COMM_FREE(comm, ierr)

CALL xios_finalize()

CALL MPI_FINALIZE(ierr)

END PROGRAM xios_toy
