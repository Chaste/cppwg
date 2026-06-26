#include "PetscUtils.hpp"

#include <petsc.h>
#include <petscksp.h>
#include <petscvec.h>
#include <petscmat.h>
#include <petscsys.h>

#include <vector>

#include "SimulationException.hpp"

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

void PetscUtils::ThrowException()
{
    throw SimulationException("C++ exception thrown", __FILE__, __LINE__);
}
