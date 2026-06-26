#include "PetscUtils.hpp"

#include <petsc.h>
#include <petscksp.h>
#include <petscvec.h>
#include <petscmat.h>
#include <petscsys.h>

#include <stdexcept>
#include <string>
#include <vector>

void PetscUtils::Initialise()
{
    if (!PetscUtils::IsInitialised())
    {
#if PETSC_VERSION_GE(3, 19, 0)
        PetscInitialize(PETSC_NULLPTR, PETSC_NULLPTR, PETSC_NULLPTR, PETSC_NULLPTR);
#else
        PetscInitialize(PETSC_NULL, PETSC_NULL, PETSC_NULL, PETSC_NULL);
#endif
    }
}

bool PetscUtils::IsInitialised()
{
    PetscBool isInitialised;
    PetscInitialized(&isInitialised);
    return (bool)isInitialised;
}

int PetscUtils::GetSize()
{
    if (!PetscUtils::IsInitialised())
    {
        PetscUtils::Initialise();
    }

    PetscInt size;
    MPI_Comm_size(PETSC_COMM_WORLD, &size);
    return (unsigned)size;
}

int PetscUtils::GetRank()
{
    if (!PetscUtils::IsInitialised())
    {
        PetscUtils::Initialise();
    }

    PetscInt rank;
    MPI_Comm_rank(PETSC_COMM_WORLD, &rank);
    return (unsigned)rank;
}

Vec PetscUtils::CreateVec(int size)
{
    if (!PetscUtils::IsInitialised())
    {
        PetscUtils::Initialise();
    }

    Vec v;
    VecCreate(PETSC_COMM_WORLD, &v);
    VecSetSizes(v, PETSC_DECIDE, size);
    VecSetFromOptions(v);
    return v;
}

void PetscUtils::ThrowPetscError()
{
    if (!PetscUtils::IsInitialised())
    {
        PetscUtils::Initialise();
    }

    Vec v;
    PetscErrorCode ierr = VecCreate(PETSC_COMM_WORLD, &v);
    if (ierr)
    {
        throw std::runtime_error(
            "VecCreate failed with PETSc error code " + std::to_string(ierr));
    }

    // PETSc reports errors with C return codes, not C++ exceptions, so the
    // wrapper must turn an error code into a C++ exception for it to reach
    // Python.
#ifdef PETSC_CLANGUAGE_CXX
    ierr = VecSetType(v, "no_such_vec_type");
    VecDestroy(&v);
    PetscCallThrow(ierr);
#else
    // Otherwise (the common case, including the standard PETSc packages),
    // PetscCallThrow() is unavailable, so we replicate it: detect the non-zero
    // PetscErrorCode and throw a std::runtime_error. The return error handler
    // keeps PETSc from printing a traceback or aborting.
    PetscPushErrorHandler(PetscReturnErrorHandler, nullptr);
    ierr = VecSetType(v, "no_such_vec_type");
    PetscPopErrorHandler();
    VecDestroy(&v);

    if (ierr)
    {
        throw std::runtime_error(
            "PETSc returned error code " + std::to_string(ierr));
    }
#endif
}
